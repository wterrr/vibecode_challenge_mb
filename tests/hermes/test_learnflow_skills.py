from __future__ import annotations

import json
import re
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SKILLS = ROOT / ".hermes" / "skills"
EXPECTED = {
    "build-evidenced-lesson",
    "investigate-lesson-facts",
    "repair-failed-lesson",
    "review-lesson-before-publication",
}


def parse_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", text, re.S)
    assert match, path
    return yaml.safe_load(match.group(1)), match.group(2)


def test_exact_stable_skill_set():
    assert {p.name for p in SKILLS.iterdir() if p.is_dir()} == EXPECTED


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_skill_frontmatter_name_matches_directory(name):
    meta, _ = parse_frontmatter(SKILLS / name / "SKILL.md")
    assert meta["name"] == name
    assert meta["version"] == "1.0.0"
    assert meta["description"].strip()
    assert meta["platforms"] == ["linux", "macos", "windows"]


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_skill_is_procedure_not_executable_package(name):
    root = SKILLS / name
    assert {p.name for p in root.iterdir() if p.is_dir()} <= {"references"}
    assert not any(
        p.suffix in {".py", ".sh", ".js", ".ts", ".mjs"}
        for p in root.rglob("*")
    )


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_skill_has_hard_rules_and_completion_gate(name):
    _, body = parse_frontmatter(SKILLS / name / "SKILL.md")
    assert "## Hard Rules" in body
    assert "## Completion Criteria" in body


def test_build_skill_preserves_full_typed_stage_order():
    text = (SKILLS / "build-evidenced-lesson" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    order = [
        "Research Orchestration",
        "Fact Verification",
        "Pedagogy Agent",
        "Script Agent",
        "Visual Director",
        "Agent-Aware QA",
    ]
    positions = [text.index(item) for item in order]
    assert positions == sorted(positions)
    assert "learnflow_create" in text
    assert "learnflow_run" in text
    assert "learnflow_render" in text


def test_fact_skill_cannot_override_deterministic_evidence_gate():
    text = (SKILLS / "investigate-lesson-facts" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "does not override missing deterministic evidence" in text
    assert "Claim cycles cannot self-ground" in text


def test_repair_skill_preserves_owner_boundaries():
    text = (SKILLS / "repair-failed-lesson" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "Never turn a Core repair intent into a Hermes task." in text
    assert "Agent-Aware QA" in text
    assert "QualityGateResult" in text
    assert "VideoCriticResult" in text


def test_publication_review_cannot_self_authorize():
    text = (
        SKILLS / "review-lesson-before-publication" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "does not grant publication authorization" in text
    assert "A model-facing tool argument cannot grant it" in (
        SKILLS
        / "review-lesson-before-publication"
        / "references"
        / "publication-gates.md"
    ).read_text(encoding="utf-8")


def test_all_references_resolve_and_stay_inside_skill():
    for skill_dir in (p for p in SKILLS.iterdir() if p.is_dir()):
        _, body = parse_frontmatter(skill_dir / "SKILL.md")
        refs = re.findall(r"`(references/[A-Za-z0-9._/-]+\.md)`", body)
        assert refs
        for rel in refs:
            target = (skill_dir / rel).resolve()
            assert target.is_relative_to(skill_dir.resolve())
            assert target.is_file()


def test_skills_have_no_pixel_renderer_or_inline_shell_instructions():
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(SKILLS.rglob("*.md"))
    )
    assert not re.search(r"(?i)\b(?:x|y)\s*=\s*-?\d+", text)
    assert not re.search(r"(?i)\b\d+(?:\.\d+)?\s*px\b", text)
    assert "!`" not in text
    lower = text.lower()
    for forbidden in ("ffmpeg", "manim", "deterministicpillowrenderer"):
        assert forbidden not in lower


def test_production_trust_is_not_enabled_by_repo_config():
    config = (ROOT / "hermes" / "bootstrap" / "config.yaml").read_text(
        encoding="utf-8"
    )
    assert "trusted_project_dirs" not in config
    review = json.loads(
        (ROOT / "hermes" / "skills" / "review.json").read_text(encoding="utf-8")
    )
    assert review["production_activation"]["manual_review_required_before_production"]
    assert not review["production_activation"]["repo_config_auto_trusts_project_skills"]


def test_no_kanban_runtime_is_added_by_skills_checkpoint():
    paths = [str(p.relative_to(ROOT)) for p in SKILLS.rglob("*") if p.is_file()]
    assert not any("kanban" in path.lower() for path in paths)
    assert not any("/scripts/" in path.replace("\\", "/") for path in paths)
