"""Build the bounded Hermes delegation plan for LearnFlow research."""

from __future__ import annotations

import json

from agent_contracts import LearningBrief, ResearchPack, EvidenceGraph

from .models import (
    ConceptResearchFindings,
    EvidenceResearchFindings,
    MAX_DELEGATION_DEPTH,
    MAX_SPECIALIST_RESEARCHERS,
    MisconceptionResearchFindings,
    ResearchOrchestrationPlan,
    ResearchOrchestrationResult,
    ResearchRole,
    SpecialistTask,
)


def _string_array(*, min_items: int = 0) -> dict:
    schema = {
        "type": "array",
        "items": {"type": "string", "minLength": 1},
    }
    if min_items:
        schema["minItems"] = min_items
    return schema


def _source_wire_schema(prefix: str) -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "source_id": {"type": "string", "pattern": f"^{prefix}\\."},
            "source_type": {
                "type": "string",
                "enum": ["WEB", "PAPER", "BOOK", "DATASET", "DOCUMENT", "OTHER"],
            },
            "title": {"type": "string", "minLength": 1},
            "locator": {"type": "string", "minLength": 1},
            "publisher": {"type": ["string", "null"]},
            "authors": _string_array(),
        },
        "required": ["source_id", "title", "locator"],
    }


def _claim_wire_schema(prefix: str) -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "claim_id": {"type": "string", "pattern": f"^{prefix}\\."},
            "statement": {"type": "string", "minLength": 1},
            "source_ids": _string_array(min_items=1),
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "concept_ids": _string_array(),
        },
        "required": ["claim_id", "statement", "source_ids", "confidence"],
    }


def _edge_wire_schema(prefix: str) -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "edge_id": {"type": "string", "pattern": f"^{prefix}\\."},
            "from_kind": {"type": "string", "enum": ["SOURCE", "CLAIM"]},
            "from_id": {"type": "string", "minLength": 1},
            "to_claim_id": {"type": "string", "minLength": 1},
            "relation": {
                "type": "string",
                "enum": ["SUPPORTS", "CONTRADICTS", "DERIVES"],
            },
        },
        "required": ["edge_id", "from_kind", "from_id", "to_claim_id", "relation"],
    }


def _concept_wire_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "concepts": _string_array(min_items=1),
            "open_questions": _string_array(),
        },
        "required": ["concepts"],
    }


def _evidence_wire_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "sources": {"type": "array", "minItems": 1, "items": _source_wire_schema("evidence")},
            "claims": {"type": "array", "minItems": 1, "items": _claim_wire_schema("evidence")},
            "evidence_edges": {"type": "array", "minItems": 1, "items": _edge_wire_schema("evidence")},
        },
        "required": ["sources", "claims", "evidence_edges"],
    }


def _misconception_wire_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "sources": {"type": "array", "minItems": 1, "items": _source_wire_schema("misconception")},
            "claims": {"type": "array", "minItems": 1, "items": _claim_wire_schema("misconception")},
            "evidence_edges": {"type": "array", "minItems": 1, "items": _edge_wire_schema("misconception")},
            "misconceptions": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "misconception_id": {"type": "string", "minLength": 1},
                        "statement": {"type": "string", "minLength": 1},
                        "correction": {"type": "string", "minLength": 1},
                        "claim_ids": _string_array(min_items=1),
                    },
                    "required": ["misconception_id", "statement", "correction", "claim_ids"],
                },
            },
            "examples": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "example_id": {"type": "string", "minLength": 1},
                        "description": {"type": "string", "minLength": 1},
                        "claim_ids": _string_array(min_items=1),
                    },
                    "required": ["example_id", "description", "claim_ids"],
                },
            },
        },
        "required": ["sources", "claims", "evidence_edges", "misconceptions", "examples"],
    }


def _wire_schema(model_type) -> dict:
    if model_type is ConceptResearchFindings:
        return _concept_wire_schema()
    if model_type is EvidenceResearchFindings:
        return _evidence_wire_schema()
    if model_type is MisconceptionResearchFindings:
        return _misconception_wire_schema()
    raise TypeError(f"unsupported research specialist model: {model_type!r}")


def build_research_orchestration_plan(brief: LearningBrief) -> ResearchOrchestrationPlan:
    """Create the exact three-role research fan-out passed to a Hermes orchestrator child."""

    shared = {
        "brief_id": brief.brief_id,
        "user_query": brief.user_query,
        "learner_level": brief.learner_level,
        "language": brief.language,
        "constraints": list(brief.constraints),
        "rules": [
            "Do not invent sources.",
            "Preserve stable source identifiers and locators.",
            "Return only JSON matching the supplied output schema.",
            "Do not render, publish, or modify LearnFlow Core.",
        ],
    }

    tasks = (
        SpecialistTask(
            role=ResearchRole.CONCEPT,
            goal="Map the concepts and unresolved questions needed to teach this topic accurately.",
            context=json.dumps(
                {
                    **shared,
                    "focus": "concept definitions, terminology, prerequisite distinctions, open questions",
                    "provenance_rule": "Do not make factual claims that require sources in this role.",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            output_schema=_wire_schema(ConceptResearchFindings),
        ),
        SpecialistTask(
            role=ResearchRole.EVIDENCE,
            goal="Collect source-grounded factual claims and explicit evidence links for the lesson.",
            context=json.dumps(
                {
                    **shared,
                    "focus": "authoritative sources, claim statements, confidence, source-to-claim evidence edges",
                    "provenance_rule": (
                        "Every claim must reference declared source_ids; every source keeps its original locator. "
                        "Namespace source_id and claim_id values with the prefix 'evidence.' so sibling outputs cannot collide."
                    ),
                    "tool_rule": (
                        "Before the final JSON, you MUST use the available web tool to find real authoritative sources. "
                        "Copy stable locators from tool results exactly. Never fabricate a source or use example.com."
                    ),
                    "output_shape_hint": {
                        "sources": ["source objects"],
                        "claims": ["claim objects"],
                        "evidence_edges": ["edge objects"],
                    },
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            output_schema=_wire_schema(EvidenceResearchFindings),
        ),
        SpecialistTask(
            role=ResearchRole.MISCONCEPTION,
            goal="Identify learner misconceptions and useful examples tied to evidence-backed claims.",
            context=json.dumps(
                {
                    **shared,
                    "focus": (
                        "common misconceptions, corrections, examples, plus the sources and factual claims "
                        "needed to support those corrections/examples"
                    ),
                    "provenance_rule": (
                        "This child is isolated from Evidence Researcher. Create only LOCAL source_ids/claim_ids "
                        "backed by your own sources; namespace them with prefix 'misconception.'. "
                        "Misconceptions/examples may reference only those local claim_ids."
                    ),
                    "tool_rule": (
                        "Before the final JSON, you MUST use the available web tool to find real sources supporting "
                        "the correction claims. Copy stable locators from tool results exactly. Never fabricate a "
                        "source or use example.com."
                    ),
                    "output_shape_hint": {
                        "sources": ["source objects"],
                        "claims": ["claim objects"],
                        "evidence_edges": ["edge objects"],
                        "misconceptions": ["misconception objects"],
                        "examples": ["example objects"],
                    },
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            output_schema=_wire_schema(MisconceptionResearchFindings),
        ),
    )

    return ResearchOrchestrationPlan(
        plan_id=f"research-plan:{brief.brief_id}",
        brief_id=brief.brief_id,
        max_delegation_depth=MAX_DELEGATION_DEPTH,
        max_specialists=MAX_SPECIALIST_RESEARCHERS,
        specialist_tasks=tasks,
    )


def build_director_delegate_task(brief: LearningBrief) -> dict:
    """Return the single native Hermes delegate_task entry for the Research Orchestrator."""

    plan = build_research_orchestration_plan(brief)
    specialist_payload = [
        {
            "role": task.role.value,
            "goal": task.goal,
            "context": task.context,
            "output_schema": task.output_schema,
        }
        for task in plan.specialist_tasks
    ]
    context = {
        "learning_brief": json.loads(brief.to_canonical_json()),
        "research_plan": {
            "plan_id": plan.plan_id,
            "brief_id": plan.brief_id,
            "max_delegation_depth": plan.max_delegation_depth,
            "max_specialists": plan.max_specialists,
            "specialist_tasks": specialist_payload,
        },
        "execution_contract": [
            "Use native Hermes delegate_task exactly once for the specialist fan-out.",
            "Dispatch no more than the three supplied specialist tasks.",
            "Each specialist receives only its own goal/context/output_schema.",
            "No specialist may depend on a sibling specialist's IDs or output.",
            "Do not ask a specialist to delegate further.",
            "Preserve source_id, locator, claim_id and evidence-edge provenance exactly.",
            "Do not synthesize or rewrite ResearchPack/EvidenceGraph in the LLM.",
            "The host validates each specialist result and assembles final research artifacts deterministically.",
        ],
    }
    return {
        "goal": (
            "Act as LearnFlow Research Orchestrator. Fan out the supplied specialist research tasks "
            "through Hermes native delegation. Host code assembles the typed research artifacts deterministically."
        ),
        "context": json.dumps(context, ensure_ascii=False, sort_keys=True),
        "output_schema": ResearchOrchestrationResult.model_json_schema(),
    }


def expected_hermes_limits() -> dict[str, int | bool]:
    return {
        "max_spawn_depth": MAX_DELEGATION_DEPTH,
        "max_concurrent_children": MAX_SPECIALIST_RESEARCHERS,
        "oneshot_max_children": MAX_SPECIALIST_RESEARCHERS,
        "orchestrator_enabled": True,
    }
