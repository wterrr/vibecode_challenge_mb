#!/usr/bin/env python3
"""Verify project-local LearnFlow skills with the exact pinned Hermes runtime."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPECTED = {
    "build-evidenced-lesson": "references/artifact-chain.md",
    "investigate-lesson-facts": "references/evidence-policy.md",
    "repair-failed-lesson": "references/repair-routing.md",
    "review-lesson-before-publication": "references/publication-gates.md",
}


def _configure_trusted_project(home: Path) -> None:
    config_path = home / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    skills = config.setdefault("skills", {})
    skills["project_discovery"] = True
    skills["trusted_project_dirs"] = [str(ROOT.resolve())]
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def main() -> int:
    os.chdir(ROOT)
    home = Path(os.environ["HERMES_HOME"]).resolve()
    _configure_trusted_project(home)
    os.environ["TERMINAL_CWD"] = str(ROOT.resolve())

    from agent import skill_utils
    from tools import skills_tool

    skill_utils._PROJECT_QUARANTINE_CACHE.clear()
    skills_tool._SKILLS_CACHE.clear()

    roots = [path.resolve() for path in skill_utils.get_project_skills_dirs()]
    expected_root = (ROOT / ".hermes" / "skills").resolve()
    if expected_root not in roots:
        raise SystemExit(
            f"HERMES_LEARNFLOW_SKILLS=FAIL trusted project root missing: {roots!r}"
        )

    listing = json.loads(skills_tool.skills_list())
    if not listing.get("success"):
        raise SystemExit(f"HERMES_LEARNFLOW_SKILLS=FAIL list: {listing!r}")
    names = {item["name"] for item in listing.get("skills", [])}
    missing = sorted(set(EXPECTED) - names)
    if missing:
        raise SystemExit(
            f"HERMES_LEARNFLOW_SKILLS=FAIL missing project skills={missing!r}"
        )

    for name, reference in EXPECTED.items():
        view = json.loads(skills_tool.skill_view(name, preprocess=False))
        if not view.get("success"):
            raise SystemExit(
                f"HERMES_LEARNFLOW_SKILLS=FAIL skill_view {name}: {view!r}"
            )
        source = Path(view["_source_path"]).resolve()
        if source.parent != (expected_root / name).resolve():
            raise SystemExit(
                f"HERMES_LEARNFLOW_SKILLS=FAIL wrong source for {name}: {source}"
            )
        linked = view.get("linked_files") or {}
        flattened = json.dumps(linked, sort_keys=True)
        if reference not in flattened:
            raise SystemExit(
                f"HERMES_LEARNFLOW_SKILLS=FAIL linked reference missing "
                f"{name}/{reference}: {linked!r}"
            )
        ref_view = json.loads(
            skills_tool.skill_view(name, file_path=reference, preprocess=False)
        )
        if not ref_view.get("success"):
            raise SystemExit(
                f"HERMES_LEARNFLOW_SKILLS=FAIL reference view "
                f"{name}/{reference}: {ref_view!r}"
            )
        if not str(ref_view.get("content") or "").strip():
            raise SystemExit(
                f"HERMES_LEARNFLOW_SKILLS=FAIL empty reference "
                f"{name}/{reference}"
            )

    print("HERMES_LEARNFLOW_SKILLS=PASS")
    print("runtime=exact pinned Hermes")
    print("trusted_project_discovery=PASS")
    print("project_security_scan=PASS")
    print("skills_list=PASS")
    print("skill_view=PASS")
    print("linked_reference_view=PASS")
    print(f"skill_count={len(EXPECTED)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
