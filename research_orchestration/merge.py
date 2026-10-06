"""Deterministic merge of specialist outputs into LearnFlow research artifacts."""

from __future__ import annotations

from agent_contracts import AgentContractError, EvidenceGraph, ResearchPack

from .models import (
    ConceptResearchFindings,
    EvidenceResearchFindings,
    MisconceptionResearchFindings,
    ResearchOrchestrationResult,
    ResearchRole,
)


def merge_specialist_findings(
    *,
    pack_id: str,
    graph_id: str,
    topic: str,
    concept_findings: ConceptResearchFindings,
    evidence_findings: EvidenceResearchFindings,
    misconception_findings: MisconceptionResearchFindings,
) -> ResearchOrchestrationResult:
    """Merge without rewriting source locators, source IDs, claim IDs, or edge references."""

    claim_ids = {claim.claim_id for claim in evidence_findings.claims}
    for item in (*misconception_findings.misconceptions, *misconception_findings.examples):
        unknown = sorted(set(item.claim_ids) - claim_ids)
        if unknown:
            raise AgentContractError(
                f"misconception/example output references unknown claims {unknown!r}"
            )

    pack = ResearchPack(
        pack_id=pack_id,
        topic=topic,
        concepts=concept_findings.concepts,
        sources=evidence_findings.sources,
        claims=evidence_findings.claims,
        misconceptions=misconception_findings.misconceptions,
        examples=misconception_findings.examples,
        open_questions=concept_findings.open_questions,
    )
    graph = EvidenceGraph(
        graph_id=graph_id,
        research_pack_id=pack.pack_id,
        source_ids=tuple(source.source_id for source in evidence_findings.sources),
        claim_ids=tuple(claim.claim_id for claim in evidence_findings.claims),
        edges=evidence_findings.evidence_edges,
    )
    graph.validate_against_research_pack(pack)

    return ResearchOrchestrationResult(
        research_pack=pack,
        evidence_graph=graph,
        specialist_roles=(
            ResearchRole.CONCEPT,
            ResearchRole.EVIDENCE,
            ResearchRole.MISCONCEPTION,
        ),
    )
