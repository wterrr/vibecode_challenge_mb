from __future__ import annotations

import ast
import json
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import AgentContractError
from durable_jobs import (
    DurableJobTemplate,
    DurableTaskSpec,
    WorkerRole,
    install_worker_profiles,
    load_lesson_job_template,
    load_worker_profiles,
)


def test_semantic_pipeline_package_replaces_old_folder():
    assert (ROOT / "lesson_pipeline").is_dir()
    assert not (ROOT / "end_to_end_orchestration").exists()


def test_lesson_pipeline_remains_synchronous_source_of_truth():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "lesson_pipeline").glob("*.py")
    ).lower()
    assert "hermes_cli.kanban" not in source
    assert "durable_jobs" not in source


def test_exact_durable_task_order():
    template = load_lesson_job_template()
    assert tuple(task.key for task in template.tasks) == (
        "research-evidence",
        "pedagogy",
        "script",
        "visual-direction",
        "render",
        "review",
    )


def test_dependency_chain_is_parent_gated():
    template = load_lesson_job_template()
    assert {task.key: task.parents for task in template.tasks} == {
        "research-evidence": (),
        "pedagogy": ("research-evidence",),
        "script": ("pedagogy",),
        "visual-direction": ("script",),
        "render": ("visual-direction",),
        "review": ("render",),
    }


def test_template_uses_exact_three_roles():
    template = load_lesson_job_template()
    assert {task.role for task in template.tasks} == {
        WorkerRole.RESEARCH,
        WorkerRole.PRODUCTION,
        WorkerRole.REVIEW,
    }


def test_all_task_retries_are_bounded():
    template = load_lesson_job_template()
    assert all(1 <= task.max_retries <= 2 for task in template.tasks)


def test_each_task_has_runtime_cap():
    template = load_lesson_job_template()
    assert all(60 <= task.max_runtime_seconds <= 3600 for task in template.tasks)


def test_unknown_or_forward_parent_is_rejected():
    with pytest.raises(AgentContractError, match="unknown/forward parents"):
        DurableJobTemplate(
            template_id="bad",
            version="1",
            tasks=(
                DurableTaskSpec(
                    key="child",
                    title="child",
                    role=WorkerRole.PRODUCTION,
                    body="child",
                    parents=("future",),
                ),
                DurableTaskSpec(
                    key="future",
                    title="future",
                    role=WorkerRole.RESEARCH,
                    body="future",
                ),
                DurableTaskSpec(
                    key="review",
                    title="review",
                    role=WorkerRole.REVIEW,
                    body="review",
                    parents=("child",),
                ),
            ),
        )


def test_worker_profiles_are_semantic_and_exact():
    profiles = load_worker_profiles()
    assert {p.role.value: p.profile_name for p in profiles} == {
        "research": "learnflow-research",
        "production": "learnflow-production",
        "review": "learnflow-review",
    }


def test_research_profile_loads_fact_skill():
    profile = next(p for p in load_worker_profiles() if p.role == WorkerRole.RESEARCH)
    assert profile.always_load_skills == ("investigate-lesson-facts",)


def test_review_profile_loads_review_and_repair_skills():
    profile = next(p for p in load_worker_profiles() if p.role == WorkerRole.REVIEW)
    assert set(profile.always_load_skills) == {
        "review-lesson-before-publication",
        "repair-failed-lesson",
    }


def test_production_profile_does_not_auto_restart_whole_lesson_skill():
    profile = next(p for p in load_worker_profiles() if p.role == WorkerRole.PRODUCTION)
    assert "build-evidenced-lesson" not in profile.always_load_skills
    assert profile.always_load_skills == ()


def test_profile_install_does_not_copy_secrets(tmp_path):
    paths = install_worker_profiles(
        hermes_home=tmp_path / "home",
        repo_root=ROOT,
        trust_project_skills=False,
    )
    for path in paths:
        assert not (path / ".env").exists()
        assert not (path / "auth.json").exists()


def test_profile_install_requires_explicit_project_skill_trust(tmp_path):
    paths = install_worker_profiles(
        hermes_home=tmp_path / "home",
        repo_root=ROOT,
        trust_project_skills=False,
    )
    for path in paths:
        config = yaml.safe_load((path / "config.yaml").read_text(encoding="utf-8"))
        assert not (config.get("skills") or {}).get("trusted_project_dirs")
        assert (config.get("skills") or {}).get("always_load") == []


def test_explicit_trust_loads_role_skills(tmp_path):
    paths = install_worker_profiles(
        hermes_home=tmp_path / "home",
        repo_root=ROOT,
        trust_project_skills=True,
    )
    by_name = {path.name: path for path in paths}
    research = yaml.safe_load(
        (by_name["learnflow-research"] / "config.yaml").read_text(encoding="utf-8")
    )
    assert research["skills"]["trusted_project_dirs"] == [str(ROOT.resolve())]
    assert research["skills"]["always_load"] == ["investigate-lesson-facts"]


def test_profile_install_enables_native_kanban_toolset(tmp_path):
    paths = install_worker_profiles(
        hermes_home=tmp_path / "home",
        repo_root=ROOT,
    )
    for path in paths:
        config = yaml.safe_load((path / "config.yaml").read_text(encoding="utf-8"))
        assert config["toolsets"] == ["kanban"]


def test_native_adapter_does_not_implement_sqlite_store():
    path = ROOT / "durable_jobs" / "native_kanban.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    assert not any(name == "sqlite3" or name.startswith("sqlite3.") for name in imports)
    source = path.read_text(encoding="utf-8")
    assert "CREATE TABLE" not in source
    assert "UPDATE tasks SET" not in source


def test_seed_adapter_uses_native_idempotency_key_convention():
    source = (ROOT / "durable_jobs" / "native_kanban.py").read_text(encoding="utf-8")
    assert 'f"learnflow:{job_id}:{task.key}"' in source
    assert "kb.create_task(" in source


def test_manifest_declares_native_state_authority_only():
    source = (ROOT / "durable_jobs" / "native_kanban.py").read_text(encoding="utf-8")
    assert '"state_authority": "hermes-native-kanban"' in source


def test_durable_layer_does_not_import_core_renderer_internals():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "durable_jobs").glob("*.py")
    ).lower()
    assert "learnflow_v2.render.backend" not in source
    assert "deterministicpillowrenderer" not in source


def test_kanban_durability_does_not_change_skill_production_trust():
    review = json.loads(
        (ROOT / "hermes" / "skills" / "review.json").read_text(encoding="utf-8")
    )
    assert review["production_activation"]["status"] == (
        "REQUIRES_MANUAL_OPERATOR_REVIEW_AND_EXPLICIT_TRUST"
    )
