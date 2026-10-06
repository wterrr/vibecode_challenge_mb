#!/usr/bin/env python3
"""Install reviewed LearnFlow Hermes worker profiles."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from durable_jobs import install_worker_profiles


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--hermes-home",
        default=os.environ.get("HERMES_HOME"),
        help="Hermes home that will receive profiles/<name>/",
    )
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument(
        "--trust-project-skills",
        action="store_true",
        help="Explicitly trust this reviewed repository for project-local Skills.",
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if not args.hermes_home:
        parser.error("--hermes-home or HERMES_HOME is required")

    paths = install_worker_profiles(
        hermes_home=args.hermes_home,
        repo_root=args.repo_root,
        trust_project_skills=args.trust_project_skills,
        overwrite=args.overwrite,
    )
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
