#!/usr/bin/env python3
"""Seed one reviewed LearnFlow lesson job into native Hermes Kanban."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from durable_jobs import seed_lesson_job, snapshot_lesson_job


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job_id")
    parser.add_argument(
        "--workspace-root",
        default=str(ROOT / ".hermes_runtime" / "lesson-jobs"),
    )
    parser.add_argument("--board", default=None)
    args = parser.parse_args()

    seeded = seed_lesson_job(
        args.job_id,
        workspace_root=args.workspace_root,
        board=args.board,
    )
    print(
        json.dumps(
            {
                "seed": seeded.model_dump(mode="json"),
                "snapshot": snapshot_lesson_job(seeded, board=args.board),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
