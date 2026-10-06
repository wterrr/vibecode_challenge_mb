"""Deterministic gate for Hermes-generated pedagogy plans."""

from __future__ import annotations

from agent_contracts import (
    AgentContractError,
    EvidenceGraph,
    LearningBrief,
    PedagogyPlan,
    ResearchPack,
)
from fact_verification import FactVerificationReport

from .models import PedagogyIssue, PedagogyValidation


def validate_pedagogy_plan(
    plan: PedagogyPlan,
    *,
    brief: LearningBrief,
    pack: ResearchPack,
    graph: EvidenceGraph,
    fact_report: FactVerificationReport,
) -> PedagogyValidation:
    """Validate pedagogy without re-deciding research evidence semantics."""

    plan.validate_against(brief, pack, graph)

    if fact_report.research_pack_id != pack.pack_id:
        raise AgentContractError(
            "FactVerificationReport research_pack_id does not match ResearchPack"
        )
    if fact_report.evidence_graph_id != graph.graph_id:
        raise AgentContractError(
            "FactVerificationReport evidence_graph_id does not match EvidenceGraph"
        )

    pack_claim_ids = {claim.claim_id for claim in pack.claims}
    report_claim_ids = {claim.claim_id for claim in fact_report.claims}
    if report_claim_ids != pack_claim_ids:
        raise AgentContractError(
            "FactVerificationReport must cover every ResearchPack claim exactly once"
        )

    approved_claim_ids = set(fact_report.approved_claim_ids)
    referenced_claim_ids = {
        claim_id
        for item in (*plan.worked_examples, *plan.analogies, *plan.misconceptions)
        for claim_id in item.claim_ids
    }
    blocked_claim_ids = tuple(sorted(referenced_claim_ids - approved_claim_ids))

    known_concepts = set(pack.concepts)
    unknown_concepts = tuple(
        concept for concept in plan.concept_order if concept not in known_concepts
    )

    assessed_objective_ids = {
        objective_id
        for probe in plan.assessment_probes
        for objective_id in probe.objective_ids
    }
    unassessed_objective_ids = tuple(
        objective.objective_id
        for objective in plan.learning_objectives
        if objective.objective_id not in assessed_objective_ids
    )

    issues: list[PedagogyIssue] = []
    if blocked_claim_ids:
        issues.append(PedagogyIssue.BLOCKED_CLAIM_REFERENCE)
    if unknown_concepts:
        issues.append(PedagogyIssue.UNKNOWN_CONCEPT)
    if unassessed_objective_ids:
        issues.append(PedagogyIssue.OBJECTIVE_WITHOUT_ASSESSMENT)
    if not plan.worked_examples and not plan.analogies:
        issues.append(PedagogyIssue.MISSING_EXAMPLE)

    return PedagogyValidation(
        plan_id=plan.plan_id,
        issues=tuple(issues),
        blocked_claim_ids=blocked_claim_ids,
        unknown_concepts=unknown_concepts,
        unassessed_objective_ids=unassessed_objective_ids,
    )


def require_script_ready(validation: PedagogyValidation) -> None:
    if validation.ready_for_script:
        return
    raise AgentContractError(
        "PedagogyPlan is not ready for Script Agent: "
        f"issues={[issue.value for issue in validation.issues]!r}, "
        f"blocked_claim_ids={validation.blocked_claim_ids!r}, "
        f"unknown_concepts={validation.unknown_concepts!r}, "
        f"unassessed_objective_ids={validation.unassessed_objective_ids!r}"
    )
