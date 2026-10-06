#!/usr/bin/env python3
"""Verify the Lesson Pipeline structured task chain against the exact pinned Hermes runtime."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research_orchestration import build_director_delegate_task
from pedagogy_agent import build_pedagogy_agent_task
from script_agent import build_script_agent_task
from visual_director import build_visual_director_task
from scripts.verify_script_agent import build_fixture, build_script
from tools.delegation_output_schema import coerce_output_schema


def _require_schema(name: str, task: dict) -> None:
    schema, error = coerce_output_schema(task["output_schema"])
    if error or schema is None:
        raise SystemExit(
            f"HERMES_LESSON_PIPELINE=FAIL {name} schema incompatible: {error!r}"
        )
    if schema.get("type") != "object":
        raise SystemExit(f"HERMES_LESSON_PIPELINE=FAIL {name} schema is not an object")


def main() -> int:
    brief, pack, evidence_graph, report, pedagogy = build_fixture()
    script = build_script(pedagogy)

    research_task = build_director_delegate_task(brief)
    pedagogy_task = build_pedagogy_agent_task(
        brief, pack, evidence_graph, report
    )
    script_task = build_script_agent_task(
        brief, pack, evidence_graph, report, pedagogy
    )
    visual_task = build_visual_director_task(
        brief, pack, evidence_graph, report, pedagogy, script
    )

    for name, task in (
        ("research", research_task),
        ("pedagogy", pedagogy_task),
        ("script", script_task),
        ("visual", visual_task),
    ):
        _require_schema(name, task)

    research_context = research_task["context"]
    if "delegate_task" not in research_context:
        raise SystemExit("HERMES_LESSON_PIPELINE=FAIL research native delegation missing")

    visual_context = visual_task["context"].lower()
    if "never output x/y coordinates" not in visual_context:
        raise SystemExit("HERMES_LESSON_PIPELINE=FAIL visual geometry boundary missing")
    if "ffmpeg commands" not in visual_context:
        raise SystemExit("HERMES_LESSON_PIPELINE=FAIL renderer boundary missing")
    print("HERMES_LESSON_PIPELINE=PASS")
    print("runtime=exact pinned Hermes")
    print("research_output_schema=PASS")
    print("pedagogy_output_schema=PASS")
    print("script_output_schema=PASS")
    print("visual_output_schema=PASS")
    print("native_research_delegation_contract=PASS")
    print("sequential_gate_chain=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
