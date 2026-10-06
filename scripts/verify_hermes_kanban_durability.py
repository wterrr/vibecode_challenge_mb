#!/usr/bin/env python3
"""Acceptance proof against exact pinned Hermes native Kanban persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from durable_jobs import (
    install_worker_profiles,
    seed_lesson_job,
    snapshot_lesson_job,
)


def main() -> int:
    home = Path(os.environ["HERMES_HOME"]).resolve()
    runtime = ROOT / ".hermes_runtime" / "kanban-durability"
    db = runtime / "kanban.db"
    workspace_root = runtime / "lesson-jobs"
    runtime.mkdir(parents=True, exist_ok=True)
    if db.exists():
        db.unlink()
    for sidecar in (Path(str(db) + "-wal"), Path(str(db) + "-shm")):
        if sidecar.exists():
            sidecar.unlink()

    os.environ["HERMES_KANBAN_DB"] = str(db)
    os.environ["HERMES_KANBAN_WORKSPACES_ROOT"] = str(runtime / "workspaces")
    os.environ["TERMINAL_CWD"] = str(ROOT)

    profiles = install_worker_profiles(
        hermes_home=home,
        repo_root=ROOT,
        trust_project_skills=True,
        overwrite=True,
    )
    if len(profiles) != 3:
        raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL profile install")

    from hermes_constants import named_profile_has_identity
    for profile in profiles:
        if not named_profile_has_identity(profile):
            raise SystemExit(
                f"HERMES_KANBAN_DURABILITY=FAIL invalid native profile {profile}"
            )

    first = seed_lesson_job("acceptance-job", workspace_root=workspace_root)
    second = seed_lesson_job("acceptance-job", workspace_root=workspace_root)
    if first.task_ids != second.task_ids:
        raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL idempotent seed mismatch")

    snapshot = snapshot_lesson_job(first)
    tasks = snapshot["tasks"]
    if tasks["research-evidence"]["status"] != "ready":
        raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL research not ready")
    for key in ("pedagogy", "script", "visual-direction", "render", "review"):
        if tasks[key]["status"] != "todo":
            raise SystemExit(
                f"HERMES_KANBAN_DURABILITY=FAIL {key} should be parent-gated todo"
            )

    workspace = first.workspace_path
    if {item["workspace_path"] for item in tasks.values()} != {workspace}:
        raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL shared workspace mismatch")
    if any(item["max_retries"] != 2 for item in tasks.values()):
        raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL retry cap mismatch")

    from hermes_cli import kanban_db as kb
    from hermes_cli import kanban_db_connect as kbc

    research_id = first.task_ids["research-evidence"]
    pedagogy_id = first.task_ids["pedagogy"]
    script_id = first.task_ids["script"]

    with kbc.connect_closing() as conn:
        if not kb.complete_task(
            conn,
            research_id,
            result="verified research artifacts persisted",
            force=True,
        ):
            raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL research completion")
        if kb.get_task(conn, pedagogy_id).status != "ready":
            raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL dependency promotion")
        claimed = kb.claim_task(conn, pedagogy_id, claimer="acceptance-worker")
        if claimed is None or claimed.status != "running":
            raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL native claim")

    # Re-open the same SQLite board: simulates a fresh process observing persisted state.
    after_restart = snapshot_lesson_job(first)["tasks"]
    if after_restart["research-evidence"]["status"] != "done":
        raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL completed work lost")
    if after_restart["pedagogy"]["status"] != "running":
        raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL running claim not persisted")
    if after_restart["script"]["status"] != "todo":
        raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL downstream gate lost")

    with kbc.connect_closing() as conn:
        if not kb.reclaim_task(
            conn,
            pedagogy_id,
            reason="simulated restart recovery",
        ):
            raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL native reclaim")
        if kb.get_task(conn, pedagogy_id).status != "ready":
            raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL reclaimed task not retry-ready")
        if kb.get_task(conn, research_id).status != "done":
            raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL completed parent repeated")
        if not kb.complete_task(
            conn,
            pedagogy_id,
            result="pedagogy plan persisted",
            force=True,
        ):
            raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL pedagogy completion")
        if kb.get_task(conn, script_id).status != "ready":
            raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL resume did not promote script")
        rows = kb.list_tasks(conn, include_archived=True)
        if len(rows) != 6:
            raise SystemExit(
                f"HERMES_KANBAN_DURABILITY=FAIL duplicate cards after reseed: {len(rows)}"
            )

    manifest = json.loads(
        (Path(first.workspace_path) / "durable_job.json").read_text(encoding="utf-8")
    )
    if "status" in json.dumps(manifest).lower():
        raise SystemExit(
            "HERMES_KANBAN_DURABILITY=FAIL mutable status copied outside native Kanban"
        )
    if manifest.get("state_authority") != "hermes-native-kanban":
        raise SystemExit("HERMES_KANBAN_DURABILITY=FAIL wrong state authority")

    print("HERMES_KANBAN_DURABILITY=PASS")
    print("runtime=exact pinned Hermes")
    print("native_sqlite_board=PASS")
    print("idempotent_seed=PASS")
    print("dependency_gating=PASS")
    print("restart_state_persisted=PASS")
    print("native_reclaim_resume=PASS")
    print("completed_work_not_repeated=PASS")
    print("bounded_retries=PASS")
    print("shared_durable_workspace=PASS")
    print("three_worker_profiles=PASS")
    print("native_state_authority=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
