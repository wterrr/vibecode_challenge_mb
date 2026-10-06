"""Deterministic claim/evidence gate for LearnFlow factual narration."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from agent_contracts import (
    AgentContractError,
    EvidenceGraph,
    EvidenceNodeKind,
    EvidenceRelation,
    ResearchPack,
)

from .models import (
    ClaimVerification,
    FactVerificationReport,
    SemanticFactReview,
    SemanticVerdict,
    VerificationIssue,
)


@dataclass(frozen=True)
class _Grounding:
    grounded_source_ids: frozenset[str]
    support_edge_ids: frozenset[str]


def _assert_structural_alignment(pack: ResearchPack, graph: EvidenceGraph) -> None:
    if graph.research_pack_id != pack.pack_id:
        raise AgentContractError("EvidenceGraph research_pack_id does not match ResearchPack")
    pack_sources = {item.source_id for item in pack.sources}
    pack_claims = {item.claim_id for item in pack.claims}
    if set(graph.source_ids) != pack_sources:
        raise AgentContractError("EvidenceGraph source_ids must exactly match ResearchPack sources")
    if set(graph.claim_ids) != pack_claims:
        raise AgentContractError("EvidenceGraph claim_ids must exactly match ResearchPack claims")


def _ground_claim(
    claim_id: str,
    *,
    incoming_support: dict[str, list],
    source_ids: set[str],
    memo: dict[str, _Grounding],
    visiting: set[str],
) -> _Grounding:
    cached = memo.get(claim_id)
    if cached is not None:
        return cached
    if claim_id in visiting:
        # A claim-only cycle is not provenance.
        return _Grounding(frozenset(), frozenset())

    visiting.add(claim_id)
    sources: set[str] = set()
    edges: set[str] = set()

    for edge in incoming_support.get(claim_id, ()):
        if edge.from_kind == EvidenceNodeKind.SOURCE:
            if edge.from_id in source_ids:
                sources.add(edge.from_id)
                edges.add(edge.edge_id)
            continue

        parent = _ground_claim(
            edge.from_id,
            incoming_support=incoming_support,
            source_ids=source_ids,
            memo=memo,
            visiting=visiting,
        )
        if parent.grounded_source_ids:
            sources.update(parent.grounded_source_ids)
            edges.update(parent.support_edge_ids)
            edges.add(edge.edge_id)

    visiting.remove(claim_id)
    result = _Grounding(frozenset(sources), frozenset(edges))
    memo[claim_id] = result
    return result


def verify_facts(
    pack: ResearchPack,
    graph: EvidenceGraph,
    semantic_review: SemanticFactReview | None = None,
) -> FactVerificationReport:
    """Return a fail-closed narration gate for every research claim."""

    _assert_structural_alignment(pack, graph)

    source_ids = {item.source_id for item in pack.sources}
    claim_ids = {item.claim_id for item in pack.claims}

    incoming_support: dict[str, list] = defaultdict(list)
    incoming_contradictions: dict[str, list] = defaultdict(list)
    for edge in graph.edges:
        if edge.relation in {EvidenceRelation.SUPPORTS, EvidenceRelation.DERIVES}:
            incoming_support[edge.to_claim_id].append(edge)
        elif edge.relation == EvidenceRelation.CONTRADICTS:
            incoming_contradictions[edge.to_claim_id].append(edge)

    semantic_by_claim = {}
    if semantic_review is not None:
        if semantic_review.research_pack_id != pack.pack_id:
            raise AgentContractError("SemanticFactReview research_pack_id does not match ResearchPack")
        if semantic_review.evidence_graph_id != graph.graph_id:
            raise AgentContractError("SemanticFactReview evidence_graph_id does not match EvidenceGraph")
        semantic_ids = {item.claim_id for item in semantic_review.claims}
        if semantic_ids != claim_ids:
            raise AgentContractError(
                "SemanticFactReview must cover every ResearchPack claim exactly once"
            )
        for item in semantic_review.claims:
            unknown_sources = sorted(set(item.cited_source_ids) - source_ids)
            if unknown_sources:
                raise AgentContractError(
                    f"semantic review for {item.claim_id!r} cites unknown sources "
                    f"{unknown_sources!r}"
                )
            semantic_by_claim[item.claim_id] = item

    memo: dict[str, _Grounding] = {}
    results: list[ClaimVerification] = []

    for claim in pack.claims:
        grounding = _ground_claim(
            claim.claim_id,
            incoming_support=incoming_support,
            source_ids=source_ids,
            memo=memo,
            visiting=set(),
        )
        contradiction_edges = incoming_contradictions.get(claim.claim_id, ())
        issues: list[VerificationIssue] = []

        if not grounding.grounded_source_ids:
            issues.append(VerificationIssue.UNSUPPORTED)
        if contradiction_edges:
            issues.append(VerificationIssue.CONTRADICTION)

        semantic = semantic_by_claim.get(claim.claim_id)
        semantic_verdict = semantic.verdict if semantic is not None else None
        if semantic_verdict == SemanticVerdict.CONTRADICTED:
            if VerificationIssue.CONTRADICTION not in issues:
                issues.append(VerificationIssue.CONTRADICTION)
        elif semantic_verdict == SemanticVerdict.UNCERTAIN:
            issues.append(VerificationIssue.SEMANTIC_UNCERTAINTY)

        results.append(
            ClaimVerification(
                claim_id=claim.claim_id,
                issues=tuple(issues),
                grounded_source_ids=tuple(sorted(grounding.grounded_source_ids)),
                support_edge_ids=tuple(sorted(grounding.support_edge_ids)),
                contradiction_edge_ids=tuple(
                    sorted(edge.edge_id for edge in contradiction_edges)
                ),
                semantic_verdict=semantic_verdict,
            )
        )

    return FactVerificationReport(
        report_id=f"fact-verification:{pack.pack_id}",
        research_pack_id=pack.pack_id,
        evidence_graph_id=graph.graph_id,
        claims=tuple(results),
    )


def require_narration_claims(
    report: FactVerificationReport,
    claim_ids: tuple[str, ...] | list[str],
) -> None:
    """Fail closed unless every factual narration claim is explicitly approved."""

    requested = tuple(claim_ids)
    if not requested:
        raise AgentContractError("factual narration must map to at least one claim_id")
    if len(requested) != len(set(requested)):
        raise AgentContractError("factual narration claim_ids must be unique")

    known = {item.claim_id for item in report.claims}
    unknown = sorted(set(requested) - known)
    if unknown:
        raise AgentContractError(f"narration references unknown claim_ids {unknown!r}")

    approved = set(report.approved_claim_ids)
    blocked = sorted(set(requested) - approved)
    if blocked:
        reasons = {
            item.claim_id: [issue.value for issue in item.issues]
            for item in report.claims
            if item.claim_id in blocked
        }
        raise AgentContractError(
            f"narration references blocked claim_ids {blocked!r}; reasons={reasons!r}"
        )
