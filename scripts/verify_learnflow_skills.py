#!/usr/bin/env python3
"""Static acceptance verifier for LearnFlow native Hermes project skills."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / ".hermes" / "skills"
REVIEW = ROOT / "hermes" / "skills" / "review.json"

EXPECTED = {
    "build-evidenced-lesson",
    "investigate-lesson-facts",
    "repair-failed-lesson",
    "review-lesson-before-publication",
}
REQUIRED_SECTIONS = (
    "## Procedure",
    "## Hard Rules",
    "## Completion Criteria",
)


def parse_skill(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", text, re.S)
    if not match:
        raise SystemExit(f"LEARNFLOW_SKILLS=FAIL invalid frontmatter: {path}")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise SystemExit(f"LEARNFLOW_SKILLS=FAIL frontmatter is not mapping: {path}")
    return data, match.group(2)


def linked_references(body: str) -> set[str]:
    return set(re.findall(r"`(references/[A-Za-z0-9._/-]+\.md)`", body))


def main() -> int:
    if not SKILLS_ROOT.is_dir():
        raise SystemExit("LEARNFLOW_SKILLS=FAIL .hermes/skills missing")

    dirs = {p.name: p for p in SKILLS_ROOT.iterdir() if p.is_dir()}
    if set(dirs) != EXPECTED:
        raise SystemExit(
            f"LEARNFLOW_SKILLS=FAIL skill set={sorted(dirs)!r}"
        )

    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    reviewed = {item["name"] for item in review["skills"]}
    if reviewed != EXPECTED:
        raise SystemExit("LEARNFLOW_SKILLS=FAIL review manifest mismatch")
    if review["production_activation"]["repo_config_auto_trusts_project_skills"]:
        raise SystemExit("LEARNFLOW_SKILLS=FAIL repository must not auto-trust skills")
    if not review["production_activation"]["manual_review_required_before_production"]:
        raise SystemExit("LEARNFLOW_SKILLS=FAIL manual production review gate missing")

    config_text = (ROOT / "hermes" / "bootstrap" / "config.yaml").read_text(
        encoding="utf-8"
    )
    if "trusted_project_dirs" in config_text:
        raise SystemExit("LEARNFLOW_SKILLS=FAIL bootstrap config auto-trusts project skills")

    for name, skill_dir in sorted(dirs.items()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            raise SystemExit(f"LEARNFLOW_SKILLS=FAIL missing SKILL.md: {name}")
        frontmatter, body = parse_skill(skill_md)
        if frontmatter.get("name") != name:
            raise SystemExit(f"LEARNFLOW_SKILLS=FAIL name mismatch: {name}")
        if not str(frontmatter.get("description") or "").strip():
            raise SystemExit(f"LEARNFLOW_SKILLS=FAIL description missing: {name}")
        if frontmatter.get("version") != "1.0.0":
            raise SystemExit(f"LEARNFLOW_SKILLS=FAIL version mismatch: {name}")

        for section in REQUIRED_SECTIONS:
            if section not in body:
                raise SystemExit(
                    f"LEARNFLOW_SKILLS=FAIL {name} missing section {section!r}"
                )

        child_dirs = {p.name for p in skill_dir.iterdir() if p.is_dir()}
        if child_dirs - {"references"}:
            raise SystemExit(
                f"LEARNFLOW_SKILLS=FAIL executable/support dirs not allowed: "
                f"{name} {sorted(child_dirs)!r}"
            )
        if any(
            p.suffix in {".py", ".sh", ".js", ".ts", ".mjs"}
            for p in skill_dir.rglob("*")
        ):
            raise SystemExit(f"LEARNFLOW_SKILLS=FAIL executable helper found: {name}")

        refs = linked_references(body)
        if not refs:
            raise SystemExit(f"LEARNFLOW_SKILLS=FAIL no linked reference: {name}")
        for rel in refs:
            path = skill_dir / rel
            if not path.is_file():
                raise SystemExit(
                    f"LEARNFLOW_SKILLS=FAIL broken reference: {name}/{rel}"
                )

        if re.search(r"(?i)\b(?:x|y)\s*=\s*-?\d+", body):
            raise SystemExit(f"LEARNFLOW_SKILLS=FAIL pixel-like coordinate: {name}")
        if re.search(r"(?i)\b\d+(?:\.\d+)?\s*px\b", body):
            raise SystemExit(f"LEARNFLOW_SKILLS=FAIL pixel value: {name}")
        if "!`" in body:
            raise SystemExit(f"LEARNFLOW_SKILLS=FAIL inline shell expansion: {name}")
        for forbidden in ("ffmpeg", "manim", "deterministicpillowrenderer"):
            if forbidden in body.lower():
                raise SystemExit(
                    f"LEARNFLOW_SKILLS=FAIL renderer implementation leaked: "
                    f"{name} -> {forbidden}"
                )

    all_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(SKILLS_ROOT.rglob("*.md"))
    ).lower()
    required_phrases = (
        "fact verification",
        "agent-aware qa",
        "runtime governance",
        "core freeze",
        "do not use durable kanban",
    )
    for phrase in required_phrases:
        if phrase not in all_text:
            raise SystemExit(
                f"LEARNFLOW_SKILLS=FAIL architecture invariant missing: {phrase}"
            )

    print("LEARNFLOW_SKILLS=PASS")
    print("native_folder_structure=PASS")
    print("frontmatter_and_versions=PASS")
    print("reference_resolution=PASS")
    print("no_executable_skill_helpers=PASS")
    print("no_pixel_or_renderer_implementation=PASS")
    print("production_manual_review_gate=PASS")
    print("repo_auto_trust_disabled=PASS")
    print(f"skill_count={len(EXPECTED)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
