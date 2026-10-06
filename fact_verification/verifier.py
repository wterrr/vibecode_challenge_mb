"""Deterministic claim/evidence gate for LearnFlow factual narration."""

from __future__ import annotations

from collections import defaultdict, deque
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


def _assert_structural_alignment(pack: ResearchPack, graph: EvidenceGraph) -> None:
    if graph.research_pack_id != pack.pack_id:
        raise AgentContractError("EvidenceGraph research_pack_id does not match ResearchPack")
    pack_sources = {item.source_id for item in pack.sources}
    pack_claims = {item.claim_id for item in pack.claims}
    if set(graph.source_ids) != pack_sources:
        raise AgentContractError("EvidenceGraph source_ids must exactly match ResearchPack sources")
    if set(graph.claim_ids) != pack_claims:
        raise AgentContractError("EvidenceGraph claim_ids must exactly match ResearchPack claims")


def _compute_grounding(
    *,
    claim_ids: set[str],
    source_ids: set[str],
    support_edges: list,
) -> dict[str, _Grounding]:
    """Propagate provenance to a fixed point; claim-only cycles never self-ground."""

    grounded_sources: dict[str, set[str]] = {claim_id: set() for claim_id in claim_ids}

    # Seed only from real source nodes.
    for edge in support_edges:
        if edge.from_kind == EvidenceNodeKind.SOURCE and edge.from_id in source_ids:
            grounded_sources[edge.to_claim_id].add(edge.from_id)

    # Then propagate source provenance through claim -> claim support/derivation.
    changed = True
    while changed:
        changed = False
        for edge in support_edges:
            if edge.from_kind != EvidenceNodeKind.CLAIM:
                continue
            parent_sources = grounded_sources.get(edge.from_id, set())
            if not parent_sources:
                continue

            before_sources = len(grounded_sources[edge.to_claim_id])
            grounded_sources[edge.to_claim_id].update(parent_sources)
            if len(grounded_sources[edge.to_claim_id]) != before_sources:
                changed = True

    return {
        claim_id: _Grounding(
            grounded_source_ids=frozenset(grounded_sources[claim_id]),
        )
        for claim_id in claim_ids
    }



def _shortest_source_witness_edges(
    claim_id: str,
    source_id: str,
    *,
    incoming_support: dict[str, list],
) -> tuple[str, ...]:
    """Return one deterministic shortest acyclic support path from source to claim."""

    queue = deque([(claim_id, tuple())])
    visited = {claim_id}

    while queue:
        current_claim, reversed_path = queue.popleft()
        for edge in sorted(
            incoming_support.get(current_claim, ()),
            key=lambda item: item.edge_id,
        ):
            next_path = reversed_path + (edge.edge_id,)
            if edge.from_kind == EvidenceNodeKind.SOURCE:
                if edge.from_id == source_id:
                    return tuple(reversed(next_path))
                continue

            parent_claim = edge.from_id
            if parent_claim in visited:
                continue
            visited.add(parent_claim)
            queue.append((parent_claim, next_path))

    return tuple()


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

    grounding_by_claim = _compute_grounding(
        claim_ids=claim_ids,
        source_ids=source_ids,
        support_edges=[
            edge
            for edges in incoming_support.values()
            for edge in edges
        ],
    )
    results: list[ClaimVerification] = []

    for claim in pack.claims:
        grounding = grounding_by_claim[claim.claim_id]
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

        witness_edge_ids: set[str] = set()
        for grounded_source_id in sorted(grounding.grounded_source_ids):
            witness_edge_ids.update(
                _shortest_source_witness_edges(
                    claim.claim_id,
                    grounded_source_id,
                    incoming_support=incoming_support,
                )
            )

        results.append(
            ClaimVerification(
                claim_id=claim.claim_id,
                issues=tuple(issues),
                grounded_source_ids=tuple(sorted(grounding.grounded_source_ids)),
                support_edge_ids=tuple(sorted(witness_edge_ids)),
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
