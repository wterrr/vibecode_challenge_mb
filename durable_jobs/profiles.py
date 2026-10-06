"""Install reviewed Hermes worker profiles without copying secrets."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Iterable

import yaml

from .models import WorkerProfileSpec, WorkerRole

ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / "hermes" / "kanban" / "profiles"
BASE_CONFIG = ROOT / "hermes" / "bootstrap" / "config.yaml"


def load_worker_profiles() -> tuple[WorkerProfileSpec, ...]:
    specs = []
    for path in sorted(PROFILE_DIR.glob("*.json")):
        specs.append(WorkerProfileSpec.model_validate_json(path.read_text(encoding="utf-8")))
    roles = {spec.role for spec in specs}
    if roles != {WorkerRole.RESEARCH, WorkerRole.PRODUCTION, WorkerRole.REVIEW}:
        raise ValueError("worker profile set must contain research, production, and review")
    return tuple(specs)


def _profile_soul(spec: WorkerProfileSpec) -> str:
    rules = {
        WorkerRole.RESEARCH: (
            "Own research/evidence work only. Use accepted Research Orchestration and deterministic "
            "Fact Verification. Never write final narration, geometry, or publication policy."
        ),
        WorkerRole.PRODUCTION: (
            "Own accepted Pedagogy, Script, Visual Director, capability handoff, and Core render tasks "
            "only when their declared parents are done. Preserve typed IDs and deterministic gates. "
            "Do not redo accepted research unless a routed repair explicitly requires it."
        ),
        WorkerRole.REVIEW: (
            "Own authoritative QA, Agent-Aware routing, and pre-publication readiness review. "
            "Never repair Core geometry in Hermes and never grant publication authorization."
        ),
    }
    return (
        f"# LearnFlow {spec.role.value.title()} Worker\n\n"
        f"{spec.description.strip()}\n\n"
        f"{rules[spec.role]}\n\n"
        "Kanban state is durable coordination only; accepted LearnFlow stages remain the source of truth.\n"
    )


def install_worker_profiles(
    *,
    hermes_home: str | Path,
    repo_root: str | Path = ROOT,
    trust_project_skills: bool = False,
    overwrite: bool = False,
) -> tuple[Path, ...]:
    """Materialize three Hermes profiles from the reviewed templates.

    No .env/auth files are copied. Project skill trust is added only when the
    operator explicitly opts in after reviewing the accepted Skills files.
    """

    home = Path(hermes_home).expanduser().resolve()
    repo = Path(repo_root).expanduser().resolve()
    base = yaml.safe_load(BASE_CONFIG.read_text(encoding="utf-8")) or {}
    created: list[Path] = []

    for spec in load_worker_profiles():
        profile_home = home / "profiles" / spec.profile_name
        config_path = profile_home / "config.yaml"
        if profile_home.exists() and not overwrite:
            raise FileExistsError(
                f"profile {spec.profile_name!r} already exists; pass overwrite=True to replace config/SOUL"
            )
        profile_home.mkdir(parents=True, exist_ok=True)
        cfg = copy.deepcopy(base)
        cfg["toolsets"] = ["kanban"]
        cfg.setdefault("terminal", {})["cwd"] = str(repo)
        cfg.setdefault("kanban", {})["max_in_progress_per_profile"] = spec.max_in_progress
        skill_cfg = cfg.setdefault("skills", {})
        skill_cfg["project_discovery"] = True
        if trust_project_skills:
            skill_cfg["trusted_project_dirs"] = [str(repo)]
            skill_cfg["always_load"] = list(spec.always_load_skills)
        else:
            skill_cfg.pop("trusted_project_dirs", None)
            skill_cfg["always_load"] = []

        config_path.write_text(
            yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        (profile_home / "SOUL.md").write_text(_profile_soul(spec), encoding="utf-8")
        created.append(profile_home)
    return tuple(created)
