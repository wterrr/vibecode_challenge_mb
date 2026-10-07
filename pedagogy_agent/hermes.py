"""Hermes-facing task construction for the LearnFlow Pedagogy Agent."""

from __future__ import annotations

import json
from typing import Any

from agent_contracts import (
    AgentContractError,
    EvidenceGraph,
    LearningBrief,
    PedagogyPlan,
    ResearchPack,
)
from fact_verification import FactVerificationReport

from .gate import approved_claim_ids_from_safe_report


def _approved_research_view(
    pack: ResearchPack,
    fact_report: FactVerificationReport,
) -> dict:
    approved = set(fact_report.approved_claim_ids)
    return {
        "concepts": list(pack.concepts),
        "concept_catalog": [
            {"index": index, "concept": concept}
            for index, concept in enumerate(pack.concepts)
        ],
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


def _pedagogy_wire_schema(concepts: tuple[str, ...]) -> dict[str, Any]:
    """Model-facing schema with dynamic concept references owned by the host."""

    if not concepts:
        raise AgentContractError(
            "Pedagogy Agent requires at least one research concept"
        )

    schema = json.loads(json.dumps(PedagogyPlan.model_json_schema()))
    properties = dict(schema.get("properties") or {})
    if "concept_order" not in properties:
        raise AgentContractError("PedagogyPlan schema is missing concept_order")

    properties.pop("concept_order", None)
    properties["concept_indexes"] = {
        "type": "array",
        "minItems": 1,
        "uniqueItems": True,
        "items": {
            "type": "integer",
            "minimum": 0,
            "maximum": len(concepts) - 1,
        },
        "description": (
            "Unique zero-based indexes into context.research.concept_catalog, "
            "in the intended teaching order."
        ),
    }
    schema["properties"] = properties

    required = list(schema.get("required") or [])
    if "concept_order" in required:
        required[required.index("concept_order")] = "concept_indexes"
    elif "concept_indexes" not in required:
        required.append("concept_indexes")
    schema["required"] = required
    return schema


def assemble_pedagogy_plan_wire(
    payload: dict[str, Any],
    *,
    concepts: tuple[str, ...],
) -> PedagogyPlan:
    """Deterministically replace model-generated references with exact concepts."""

    if not isinstance(payload, dict):
        raise AgentContractError("Pedagogy wire output must be an object")
    if not concepts:
        raise AgentContractError(
            "Pedagogy Agent requires at least one research concept"
        )
    if "concept_order" in payload:
        raise AgentContractError(
            "Pedagogy wire output must use concept_indexes, not concept_order"
        )

    raw_indexes = payload.get("concept_indexes")
    if not isinstance(raw_indexes, list) or not raw_indexes:
        raise AgentContractError(
            "concept_indexes must be a non-empty array of zero-based integers"
        )

    indexes: list[int] = []
    for item in raw_indexes:
        if not isinstance(item, int) or isinstance(item, bool):
            raise AgentContractError("concept_indexes entries must be integers")
        if item < 0 or item >= len(concepts):
            raise AgentContractError(
                f"concept_indexes index {item} is outside 0..{len(concepts) - 1}"
            )
        indexes.append(item)
    if len(indexes) != len(set(indexes)):
        raise AgentContractError("concept_indexes must be unique")

    canonical = dict(payload)
    canonical.pop("concept_indexes", None)
    canonical["concept_order"] = [concepts[index] for index in indexes]
    return PedagogyPlan.model_validate(canonical)


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

    research_view = _approved_research_view(pack, fact_report)
    payload = {
        "learning_brief": json.loads(brief.to_canonical_json()),
        "research": research_view,
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
            "Return one PedagogyPlan-shaped JSON object and no prose outside the structured result.",
            "Create clear learning objectives with measurable assessment criteria.",
            "Identify only prerequisites needed by this learner.",
            (
                "Return concept_indexes, not concept_order. concept_indexes must be "
                "unique zero-based indexes from research.concept_catalog in teaching order. "
                "The host will reconstruct the exact canonical concept strings."
            ),
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
        "output_schema": _pedagogy_wire_schema(tuple(pack.concepts)),
    }
