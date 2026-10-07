#!/usr/bin/env python3
"""Verify Script Agent structured output against the exact pinned Hermes runtime."""

from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import (
    AssessmentProbe,
    EvidenceEdge,
    EvidenceGraph,
    EvidenceNodeKind,
    EvidenceRelation,
    LearningBrief,
    LearningObjective,
    PedagogyExample,
    PedagogyPlan,
    ResearchClaim,
    ResearchPack,
    SourceRecord,
)
from fact_verification import verify_facts
from script_agent import build_script_agent_task
from tools.delegation_output_schema import coerce_output_schema


def main() -> int:
    brief = LearningBrief(
        brief_id="brief.hermes-script",
        user_query="Explain one supported idea.",
        learner_level="beginner",
        target_duration_minutes=2,
        language="en",
    )
    source = SourceRecord(
        source_id="S1",
        title="Source",
        locator="https://example.test/source",
    )
    pack = ResearchPack(
        pack_id="research.hermes-script",
        topic="test",
        concepts=("concept-a",),
        sources=(source,),
        claims=(
            ResearchClaim(
                claim_id="C1",
                statement="Supported fact.",
                source_ids=("S1",),
                confidence=0.9,
            ),
        ),
    )
    graph = EvidenceGraph(
        graph_id="evidence.hermes-script",
        research_pack_id=pack.pack_id,
        source_ids=("S1",),
        claim_ids=("C1",),
        edges=(
            EvidenceEdge(
                edge_id="E1",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id="S1",
                to_claim_id="C1",
                relation=EvidenceRelation.SUPPORTS,
            ),
        ),
    )
    report = verify_facts(pack, graph)
    pedagogy = PedagogyPlan(
        plan_id="pedagogy.hermes-script",
        brief_id=brief.brief_id,
        research_pack_id=pack.pack_id,
        evidence_graph_id=graph.graph_id,
        learning_objectives=(
            LearningObjective(
                objective_id="O1",
                description="Understand concept-a.",
                assessment_criterion="Explain concept-a.",
            ),
        ),
        concept_order=("concept-a",),
        worked_examples=(
            PedagogyExample(
                example_id="X1",
                concept="concept-a",
                description="One concrete example.",
                claim_ids=("C1",),
            ),
        ),
        assessment_probes=(
            AssessmentProbe(
                probe_id="P1",
                prompt="Explain it.",
                expected_outcome="Correct explanation.",
                objective_ids=("O1",),
            ),
        ),
    )

    task = build_script_agent_task(brief, pack, graph, report, pedagogy)
    schema, error = coerce_output_schema(task["output_schema"])
    if error or schema is None:
        raise SystemExit(
            f"HERMES_SCRIPT_AGENT=FAIL output_schema incompatible: {error!r}"
        )

    if "segments" not in schema.get("properties", {}):
        raise SystemExit("HERMES_SCRIPT_AGENT=FAIL segments field missing")

    defs = schema.get("$defs", {})
    segment_schema = defs.get("ScriptSegment", {})
    segment_properties = set(segment_schema.get("properties", {}))
    required_segment_fields = {
        "segment_id",
        "spoken_text",
        "subtitle_text",
        "spoken_language",
        "subtitle_language",
        "claim_indexes",
        "objective_indexes",
        "teaching_function",
        "emphasis",
    }
    if not required_segment_fields.issubset(segment_properties):
        raise SystemExit("HERMES_SCRIPT_AGENT=FAIL ScriptSegment schema incomplete")

    if "claim_ids" in segment_properties or "objective_ids" in segment_properties:
        raise SystemExit("HERMES_SCRIPT_AGENT=FAIL dynamic IDs exposed on wire")

    forbidden_fields = {
        "x", "y", "width", "height", "pixel_x", "pixel_y",
        "renderer", "code", "scenegraph",
    }
    leaked = segment_properties & forbidden_fields
    if leaked:
        raise SystemExit(
            f"HERMES_SCRIPT_AGENT=FAIL visual/code fields leaked: {sorted(leaked)!r}"
        )

    context = json.loads(task["context"])
    if [item["claim_id"] for item in context["selected_fact_claims"]] != ["C1"]:
        raise SystemExit("HERMES_SCRIPT_AGENT=FAIL claim preservation context")
    if not any(
        "cover every selected claim at least once" in item.lower()
        for item in context["instructions"]
    ):
        raise SystemExit(
            "HERMES_SCRIPT_AGENT=FAIL full claim coverage instruction missing"
        )
    if not any("visual coordinates" in item.lower() for item in context["instructions"]):
        raise SystemExit("HERMES_SCRIPT_AGENT=FAIL visual boundary missing")

    print("HERMES_SCRIPT_AGENT=PASS")
    print("runtime=exact pinned Hermes")
    print("structured_lesson_script_schema=PASS")
    print("claim_preservation_context=PASS")
    print("host_owned_claim_objective_references=PASS")
    print("teaching_function_field=PASS")
    print("no_visual_or_code_fields=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
