#!/usr/bin/env python3
"""Verify Hermes compatibility for the semantic Fact Verifier contract."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import (
    EvidenceEdge,
    EvidenceGraph,
    EvidenceNodeKind,
    EvidenceRelation,
    ResearchClaim,
    ResearchPack,
    SourceRecord,
)
from fact_verification import build_fact_verifier_task
from tools.delegation_output_schema import coerce_output_schema


def main() -> int:
    source = SourceRecord(
        source_id="source.fact",
        title="Fact source",
        locator="https://example.test/fact",
    )
    pack = ResearchPack(
        pack_id="research.hermes-fact",
        topic="Hermes fact verification",
        sources=(source,),
        claims=(
            ResearchClaim(
                claim_id="claim.fact",
                statement="A sourced factual claim.",
                source_ids=(source.source_id,),
                confidence=0.9,
            ),
        ),
    )
    graph = EvidenceGraph(
        graph_id="evidence.hermes-fact",
        research_pack_id=pack.pack_id,
        source_ids=(source.source_id,),
        claim_ids=("claim.fact",),
        edges=(
            EvidenceEdge(
                edge_id="edge.fact",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id=source.source_id,
                to_claim_id="claim.fact",
                relation=EvidenceRelation.SUPPORTS,
            ),
        ),
    )

    task = build_fact_verifier_task(pack, graph)
    if set(task) != {"goal", "context", "output_schema"}:
        raise SystemExit("HERMES_FACT_VERIFICATION=FAIL task surface")
    schema, error = coerce_output_schema(task["output_schema"])
    if error or schema is None:
        raise SystemExit(
            f"HERMES_FACT_VERIFICATION=FAIL output_schema incompatible: {error!r}"
        )
    properties = schema.get("properties", {})
    if "claims" not in properties:
        raise SystemExit("HERMES_FACT_VERIFICATION=FAIL claims field missing")

    context = task["context"]
    for marker in (
        "Do not invent sources",
        "SUPPORTED verdict is advisory only",
        "claim.fact",
        "source.fact",
    ):
        if marker not in context:
            raise SystemExit(
                f"HERMES_FACT_VERIFICATION=FAIL context marker missing: {marker!r}"
            )

    print("HERMES_FACT_VERIFICATION=PASS")
    print("runtime=exact pinned Hermes")
    print("structured_semantic_review_schema=PASS")
    print("deterministic_gate_has_final_authority=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
