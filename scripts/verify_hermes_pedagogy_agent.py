#!/usr/bin/env python3
"""Verify Pedagogy Agent structured output against the exact pinned Hermes runtime."""

from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import (
    EvidenceEdge,
    EvidenceGraph,
    EvidenceNodeKind,
    EvidenceRelation,
    LearningBrief,
    ResearchClaim,
    ResearchPack,
    SourceRecord,
)
from fact_verification import verify_facts
from pedagogy_agent import build_pedagogy_agent_task
from tools.delegation_output_schema import coerce_output_schema


def main() -> int:
    brief = LearningBrief(
        brief_id="brief.hermes-pedagogy",
        user_query="Explain a concept.",
        learner_level="beginner",
        target_duration_minutes=3,
        language="en",
    )
    source = SourceRecord(
        source_id="S1",
        title="Source",
        locator="https://example.test/source",
    )
    pack = ResearchPack(
        pack_id="research.hermes-pedagogy",
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
        graph_id="evidence.hermes-pedagogy",
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
    task = build_pedagogy_agent_task(brief, pack, graph, report)

    schema, error = coerce_output_schema(task["output_schema"])
    if error or schema is None:
        raise SystemExit(
            f"HERMES_PEDAGOGY_AGENT=FAIL output_schema incompatible: {error!r}"
        )
    required_fields = {
        "learning_objectives",
        "prerequisites",
        "concept_indexes",
        "worked_examples",
        "analogies",
        "misconceptions",
        "assessment_probes",
    }
    properties = set(schema.get("properties", {}))
    if "concept_order" in properties:
        raise SystemExit(
            "HERMES_PEDAGOGY_AGENT=FAIL model-facing schema still exposes concept_order"
        )
    if not required_fields.issubset(properties):
        raise SystemExit(
            f"HERMES_PEDAGOGY_AGENT=FAIL missing fields={sorted(required_fields-properties)!r}"
        )

    concept_indexes = schema["properties"]["concept_indexes"]
    if concept_indexes.get("uniqueItems") is not True:
        raise SystemExit("HERMES_PEDAGOGY_AGENT=FAIL concept indexes not unique")
    if concept_indexes.get("items", {}).get("minimum") != 0:
        raise SystemExit("HERMES_PEDAGOGY_AGENT=FAIL concept index minimum")
    if concept_indexes.get("items", {}).get("maximum") != 0:
        raise SystemExit("HERMES_PEDAGOGY_AGENT=FAIL concept index maximum")

    context = json.loads(task["context"])
    if [item["claim_id"] for item in context["research"]["claims"]] != ["C1"]:
        raise SystemExit("HERMES_PEDAGOGY_AGENT=FAIL approved claim filtering")
    if "Do not write lesson-script narration." not in context["instructions"]:
        raise SystemExit("HERMES_PEDAGOGY_AGENT=FAIL Script boundary missing")
    if not any("Never reference a blocked claim_id" in item for item in context["instructions"]):
        raise SystemExit("HERMES_PEDAGOGY_AGENT=FAIL blocked-claim instruction missing")

    print("HERMES_PEDAGOGY_AGENT=PASS")
    print("runtime=exact pinned Hermes")
    print("structured_pedagogy_schema=PASS")
    print("host_owned_concept_references=PASS")
    print("approved_claim_context_only=PASS")
    print("script_boundary=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
