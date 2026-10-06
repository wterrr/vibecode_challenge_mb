#!/usr/bin/env python3
"""Static acceptance verifier for LearnFlow Kanban Durability."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from durable_jobs import install_worker_profiles, load_lesson_job_template, load_worker_profiles

EXPECTED_TASKS = (
    "research-evidence",
    "pedagogy",
    "script",
    "visual-direction",
    "render",
    "review",
)
EXPECTED_PROFILES = {
    "research": "learnflow-research",
    "production": "learnflow-production",
    "review": "learnflow-review",
}


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(item.name.split(".")[0] for item in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def main() -> int:
    if not (ROOT / "lesson_pipeline").is_dir():
        raise SystemExit("KANBAN_DURABILITY=FAIL lesson_pipeline package missing")
    if (ROOT / "end_to_end_orchestration").exists():
        raise SystemExit("KANBAN_DURABILITY=FAIL old end_to_end_orchestration folder remains")

    template = load_lesson_job_template()
    keys = tuple(task.key for task in template.tasks)
    if keys != EXPECTED_TASKS:
        raise SystemExit(f"KANBAN_DURABILITY=FAIL task order={keys!r}")

    by_key = {task.key: task for task in template.tasks}
    expected_parents = {
        "research-evidence": (),
        "pedagogy": ("research-evidence",),
        "script": ("pedagogy",),
        "visual-direction": ("script",),
        "render": ("visual-direction",),
        "review": ("render",),
    }
    for key, parents in expected_parents.items():
        if by_key[key].parents != parents:
            raise SystemExit(
                f"KANBAN_DURABILITY=FAIL parents {key}={by_key[key].parents!r}"
            )
        if by_key[key].max_retries > 2:
            raise SystemExit(f"KANBAN_DURABILITY=FAIL unbounded retries on {key}")

    profiles = load_worker_profiles()
    mapping = {profile.role.value: profile.profile_name for profile in profiles}
    if mapping != EXPECTED_PROFILES:
        raise SystemExit(f"KANBAN_DURABILITY=FAIL profiles={mapping!r}")

    adapter_imports = imported_roots(ROOT / "durable_jobs" / "native_kanban.py")
    if "sqlite3" in adapter_imports:
        raise SystemExit("KANBAN_DURABILITY=FAIL custom sqlite task store detected")

    pipeline_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "lesson_pipeline").glob("*.py")
    )
    if "hermes_cli.kanban" in pipeline_source or "durable_jobs" in pipeline_source:
        raise SystemExit(
            "KANBAN_DURABILITY=FAIL synchronous Lesson Pipeline depends on Kanban"
        )

    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "hermes"
        created = install_worker_profiles(
            hermes_home=home,
            repo_root=ROOT,
            trust_project_skills=False,
        )
        if len(created) != 3:
            raise SystemExit("KANBAN_DURABILITY=FAIL three profiles not installed")
        for profile_dir in created:
            cfg = yaml.safe_load(
                (profile_dir / "config.yaml").read_text(encoding="utf-8")
            )
            if cfg.get("toolsets") != ["kanban"]:
                raise SystemExit("KANBAN_DURABILITY=FAIL kanban toolset missing")
            skills = cfg.get("skills") or {}
            if skills.get("trusted_project_dirs"):
                raise SystemExit(
                    "KANBAN_DURABILITY=FAIL project skills trusted without operator opt-in"
                )
            if skills.get("always_load"):
                raise SystemExit(
                    "KANBAN_DURABILITY=FAIL project skills loaded without operator opt-in"
                )
            if (profile_dir / ".env").exists() or (profile_dir / "auth.json").exists():
                raise SystemExit("KANBAN_DURABILITY=FAIL secrets copied into profile")

    print("KANBAN_DURABILITY=PASS")
    print("lesson_pipeline_rename=PASS")
    print("native_kanban_only=PASS")
    print("durable_dependency_dag=PASS")
    print("bounded_task_retries=PASS")
    print("three_worker_profiles=PASS")
    print("default_skill_trust_off=PASS")
    print("synchronous_pipeline_independent=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
