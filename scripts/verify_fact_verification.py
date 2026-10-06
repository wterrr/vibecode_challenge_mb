#!/usr/bin/env python3
"""Deterministic acceptance verifier for LearnFlow Fact Verification."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import (
    AgentContractError,
    EvidenceEdge,
    EvidenceGraph,
    EvidenceNodeKind,
    EvidenceRelation,
    ResearchClaim,
    ResearchPack,
    SourceRecord,
)
from fact_verification import (
    VerificationIssue,
    require_narration_claims,
    verify_facts,
)


def build_fixture():
    s1 = SourceRecord(
        source_id="source.primary",
        title="Primary source",
        locator="https://example.test/primary",
    )
    s2 = SourceRecord(
        source_id="source.counter",
        title="Counter source",
        locator="https://example.test/counter",
    )
    pack = ResearchPack(
        pack_id="research.fact-verification",
        topic="fact verification",
        sources=(s1, s2),
        claims=(
            ResearchClaim(
                claim_id="claim.supported",
                statement="This claim has grounded support.",
                source_ids=(s1.source_id,),
                confidence=0.95,
            ),
            ResearchClaim(
                claim_id="claim.contradicted",
                statement="This claim has support and counter-evidence.",
                source_ids=(s1.source_id, s2.source_id),
                confidence=0.70,
            ),
            ResearchClaim(
                claim_id="claim.cycle-a",
                statement="Cycle A claims derivation without a source path.",
                source_ids=(s1.source_id,),
                confidence=0.40,
            ),
            ResearchClaim(
                claim_id="claim.cycle-b",
                statement="Cycle B claims derivation without a source path.",
                source_ids=(s1.source_id,),
                confidence=0.40,
            ),
        ),
    )
    graph = EvidenceGraph(
        graph_id="evidence.fact-verification",
        research_pack_id=pack.pack_id,
        source_ids=(s1.source_id, s2.source_id),
        claim_ids=tuple(claim.claim_id for claim in pack.claims),
        edges=(
            EvidenceEdge(
                edge_id="edge.supported",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id=s1.source_id,
                to_claim_id="claim.supported",
                relation=EvidenceRelation.SUPPORTS,
            ),
            EvidenceEdge(
                edge_id="edge.support-contradicted",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id=s1.source_id,
                to_claim_id="claim.contradicted",
                relation=EvidenceRelation.SUPPORTS,
            ),
            EvidenceEdge(
                edge_id="edge.counter-contradicted",
                from_kind=EvidenceNodeKind.SOURCE,
                from_id=s2.source_id,
                to_claim_id="claim.contradicted",
                relation=EvidenceRelation.CONTRADICTS,
            ),
            EvidenceEdge(
                edge_id="edge.cycle-a",
                from_kind=EvidenceNodeKind.CLAIM,
                from_id="claim.cycle-b",
                to_claim_id="claim.cycle-a",
                relation=EvidenceRelation.DERIVES,
            ),
            EvidenceEdge(
                edge_id="edge.cycle-b",
                from_kind=EvidenceNodeKind.CLAIM,
                from_id="claim.cycle-a",
                to_claim_id="claim.cycle-b",
                relation=EvidenceRelation.DERIVES,
            ),
        ),
    )
    return pack, graph


def main() -> int:
    pack, graph = build_fixture()
    report = verify_facts(pack, graph)
    by_id = {item.claim_id: item for item in report.claims}

    if report.approved_claim_ids != ("claim.supported",):
        raise SystemExit(
            f"FACT_VERIFICATION=FAIL approved={report.approved_claim_ids!r}"
        )
    if VerificationIssue.CONTRADICTION not in by_id["claim.contradicted"].issues:
        raise SystemExit("FACT_VERIFICATION=FAIL contradiction not flagged")
    if by_id["claim.contradicted"].eligible_for_narration:
        raise SystemExit("FACT_VERIFICATION=FAIL contradicted claim was narratable")
    for claim_id in ("claim.cycle-a", "claim.cycle-b"):
        if VerificationIssue.UNSUPPORTED not in by_id[claim_id].issues:
            raise SystemExit(f"FACT_VERIFICATION=FAIL cycle grounded: {claim_id}")

    require_narration_claims(report, ("claim.supported",))
    try:
        require_narration_claims(report, ("claim.contradicted",))
    except AgentContractError:
        pass
    else:
        raise SystemExit("FACT_VERIFICATION=FAIL contradiction narration not blocked")

    print("FACT_VERIFICATION=PASS")
    print("source_grounded_support=PASS")
    print("claim_only_cycle_blocked=PASS")
    print("contradiction_flagged=PASS")
    print("unsupported_claim_blocked=PASS")
    print("factual_narration_claim_gate=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
