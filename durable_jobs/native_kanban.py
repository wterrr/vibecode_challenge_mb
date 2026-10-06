"""Thin adapter from reviewed LearnFlow job templates to native Hermes Kanban."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from agent_contracts import AgentContractError

from .models import SeededLessonJob, WorkerRole
from .profiles import load_worker_profiles
from .template import load_lesson_job_template


def _safe_job_id(value: str) -> str:
    value = str(value).strip()
    if not value or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for ch in value):
        raise AgentContractError("job_id must be lowercase alphanumeric/hyphen/underscore")
    return value


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _native_modules():
    try:
        from hermes_cli import kanban_db as kb
        from hermes_cli import kanban_db_connect as kbc
    except ImportError as exc:
        raise RuntimeError(
            "Hermes native Kanban is unavailable. Run this adapter inside the pinned "
            "Hermes runtime installed by scripts/install_hermes_bootstrap.sh."
        ) from exc
    return kb, kbc


def seed_lesson_job(
    job_id: str,
    *,
    workspace_root: str | Path,
    board: str | None = None,
) -> SeededLessonJob:
    """Idempotently seed the reviewed lesson DAG into the native Hermes board.

    The returned manifest records only semantic-key -> native task-id mapping.
    Native Kanban remains authoritative for all mutable task state.
    """

    job_id = _safe_job_id(job_id)
    root = Path(workspace_root).expanduser().resolve()
    workspace = root / job_id
    workspace.mkdir(parents=True, exist_ok=True)

    template = load_lesson_job_template()
    profiles = {spec.role: spec for spec in load_worker_profiles()}
    kb, kbc = _native_modules()
    kbc.init_db(board=board)

    ids: dict[str, str] = {}
    with kbc.connect_closing(board=board) as conn:
        for task in template.tasks:
            parent_ids = tuple(ids[key] for key in task.parents)
            profile = profiles[task.role]
            native_id = kb.create_task(
                conn,
                title=task.title,
                body=task.body,
                assignee=profile.profile_name,
                created_by="learnflow-durable-jobs",
                workspace_kind="dir",
                workspace_path=str(workspace),
                priority=task.priority,
                parents=parent_ids,
                idempotency_key=f"learnflow:{job_id}:{task.key}",
                max_runtime_seconds=task.max_runtime_seconds,
                max_retries=task.max_retries,
                skills=task.skills,
                initial_status="running",
                board=board,
            )
            ids[task.key] = native_id

    seeded = SeededLessonJob(
        job_id=job_id,
        template_id=template.template_id,
        workspace_path=str(workspace),
        task_ids=ids,
    )
    _atomic_json(
        workspace / "durable_job.json",
        {
            "schema_version": "learnflow-durable-job-v1",
            "job_id": seeded.job_id,
            "template_id": seeded.template_id,
            "workspace_path": seeded.workspace_path,
            "task_ids": dict(sorted(seeded.task_ids.items())),
            "state_authority": "hermes-native-kanban",
        },
    )
    return seeded


def snapshot_lesson_job(
    seeded: SeededLessonJob,
    *,
    board: str | None = None,
) -> dict[str, Any]:
    """Read a durable job snapshot from native Kanban without copying its state."""

    seeded = SeededLessonJob.model_validate(seeded.model_dump(mode="json"))
    kb, kbc = _native_modules()
    rows: dict[str, dict[str, Any]] = {}
    with kbc.connect_closing(board=board) as conn:
        for key, task_id in seeded.task_ids.items():
            task = kb.get_task(conn, task_id)
            if task is None:
                raise RuntimeError(f"native Kanban task missing for {key!r}: {task_id}")
            rows[key] = {
                "task_id": task.id,
                "title": task.title,
                "assignee": task.assignee,
                "status": task.status,
                "workspace_kind": task.workspace_kind,
                "workspace_path": task.workspace_path,
                "idempotency_key": task.idempotency_key,
                "max_runtime_seconds": task.max_runtime_seconds,
                "max_retries": task.max_retries,
                "current_run_id": task.current_run_id,
                "consecutive_failures": task.consecutive_failures,
            }
    return {
        "job_id": seeded.job_id,
        "template_id": seeded.template_id,
        "state_authority": "hermes-native-kanban",
        "tasks": rows,
    }
