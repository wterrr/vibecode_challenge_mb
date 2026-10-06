"""Hermes-facing task construction for the LearnFlow Pedagogy Agent."""

from __future__ import annotations

import json

from agent_contracts import EvidenceGraph, LearningBrief, PedagogyPlan, ResearchPack
from fact_verification import FactVerificationReport

from .gate import approved_claim_ids_from_safe_report


def _approved_research_view(
    pack: ResearchPack,
    fact_report: FactVerificationReport,
) -> dict:
    approved = set(fact_report.approved_claim_ids)
    return {
        "concepts": list(pack.concepts),
        "claims": [
            claim.model_dump(mode="json")
            for claim in pack.claims
            if claim.claim_id in approved
        ],
        "examples": [
            item.model_dump(mode="json")
            for item in pack.examples
            if set(item.claim_ids).issubset(approved)
        ],
        "misconceptions": [
            item.model_dump(mode="json")
            for item in pack.misconceptions
            if set(item.claim_ids).issubset(approved)
        ],
        "open_questions": list(pack.open_questions),
    }


def build_pedagogy_agent_task(
    brief: LearningBrief,
    pack: ResearchPack,
    graph: EvidenceGraph,
    fact_report: FactVerificationReport,
) -> dict:
    """Give Hermes only fact-approved claim material for pedagogy planning."""

    approved_claim_ids_from_safe_report(
        pack=pack,
        graph=graph,
        fact_report=fact_report,
    )

    payload = {
        "learning_brief": json.loads(brief.to_canonical_json()),
        "research": _approved_research_view(pack, fact_report),
        "fact_verification": {
            "report_id": fact_report.report_id,
            "approved_claim_ids": list(fact_report.approved_claim_ids),
            "blocked_claim_ids": list(fact_report.blocked_claim_ids),
        },
        "required_ids": {
            "brief_id": brief.brief_id,
            "research_pack_id": pack.pack_id,
            "evidence_graph_id": graph.graph_id,
        },
        "instructions": [
            "Return one PedagogyPlan and no prose outside the structured result.",
            "Create clear learning objectives with measurable assessment criteria.",
            "Identify only prerequisites needed by this learner.",
            "concept_order may use only concepts supplied in research.concepts.",
            "Use worked examples and/or analogies to make abstract ideas concrete.",
            "Preserve approved claim_ids exactly when an example, analogy, or misconception depends on a fact.",
            "Never reference a blocked claim_id.",
            "Include assessment probes so every learning objective is assessed at least once.",
            "Do not write lesson-script narration.",
            "Do not produce visual coordinates, SceneGraph objects, renderer instructions, or code.",
        ],
    }
    return {
        "goal": (
            "Act as LearnFlow Pedagogy Agent. Convert the fact-verified research into a "
            "teaching plan appropriate for the learner and target duration."
        ),
        "context": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        "output_schema": PedagogyPlan.model_json_schema(),
    }
