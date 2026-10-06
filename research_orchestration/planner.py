"""Build the bounded Hermes delegation plan for LearnFlow research."""

from __future__ import annotations

import json

from agent_contracts import LearningBrief

from .models import (
    MAX_DELEGATION_DEPTH,
    MAX_SPECIALIST_RESEARCHERS,
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


def _index_array(*, min_items: int = 1) -> dict:
    return {
        "type": "array",
        "minItems": min_items,
        "uniqueItems": True,
        "items": {"type": "integer", "minimum": 0},
    }


def _source_wire_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "source_type": {
                "type": "string",
                "enum": ["WEB", "PAPER", "BOOK", "DATASET", "DOCUMENT", "OTHER"],
            },
            "title": {"type": "string", "minLength": 1},
            "locator": {"type": "string", "minLength": 1},
            "publisher": {"type": ["string", "null"]},
            "authors": _string_array(),
        },
        "required": ["title", "locator"],
    }


def _claim_wire_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "statement": {"type": "string", "minLength": 1},
            "source_indexes": _index_array(),
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
        "required": ["statement", "source_indexes", "confidence"],
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
            "sources": {
                "type": "array",
                "minItems": 1,
                "items": _source_wire_schema(),
            },
            "claims": {
                "type": "array",
                "minItems": 1,
                "items": _claim_wire_schema(),
            },
        },
        "required": ["sources", "claims"],
    }


def _misconception_wire_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "sources": {
                "type": "array",
                "minItems": 1,
                "items": _source_wire_schema(),
            },
            "claims": {
                "type": "array",
                "minItems": 1,
                "items": _claim_wire_schema(),
            },
            "misconceptions": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "statement": {"type": "string", "minLength": 1},
                        "correction": {"type": "string", "minLength": 1},
                        "claim_indexes": _index_array(),
                    },
                    "required": ["statement", "correction", "claim_indexes"],
                },
            },
            "examples": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "description": {"type": "string", "minLength": 1},
                        "claim_indexes": _index_array(),
                    },
                    "required": ["description", "claim_indexes"],
                },
            },
        },
        "required": ["sources", "claims", "misconceptions", "examples"],
    }


def build_research_orchestration_plan(brief: LearningBrief) -> ResearchOrchestrationPlan:
    """Create the exact three-role research fan-out passed to Hermes."""

    shared = {
        "brief_id": brief.brief_id,
        "user_query": brief.user_query,
        "learner_level": brief.learner_level,
        "language": brief.language,
        "constraints": list(brief.constraints),
        "rules": [
            "Do not invent sources.",
            "Return only JSON matching the supplied output schema.",
            "Do not render, publish, or modify LearnFlow Core.",
            (
                "Do not create source IDs, claim IDs, edge IDs, concept IDs, or graph edges. "
                "The host owns all identifiers and referential integrity."
            ),
        ],
    }

    tasks = (
        SpecialistTask(
            role=ResearchRole.CONCEPT,
            goal="Map the concepts and unresolved questions needed to teach this topic accurately.",
            context=json.dumps(
                {
                    **shared,
                    "focus": (
                        "concept definitions, terminology, prerequisite distinctions, "
                        "and open questions"
                    ),
                    "provenance_rule": (
                        "Do not make factual claims that require source records in this role."
                    ),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            output_schema=_concept_wire_schema(),
        ),
        SpecialistTask(
            role=ResearchRole.EVIDENCE,
            goal="Collect source-grounded factual claims for the lesson.",
            context=json.dumps(
                {
                    **shared,
                    "focus": (
                        "authoritative source locators, factual claim statements, "
                        "confidence, and which source entries support each claim"
                    ),
                    "provenance_rule": (
                        "Return sources in an array. Each claim references those sources only "
                        "through zero-based source_indexes. Preserve each locator exactly. "
                        "The host deterministically assigns evidence.* IDs and support edges."
                    ),
                    "retrieval_rule": (
                        "If a web-search capability is actually available, use it before the final "
                        "JSON. If no retrieval capability is available, do not fabricate placeholder "
                        "domains such as example.com; return only stable source locators you can identify."
                    ),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            output_schema=_evidence_wire_schema(),
        ),
        SpecialistTask(
            role=ResearchRole.MISCONCEPTION,
            goal="Identify learner misconceptions and useful examples with local supporting claims.",
            context=json.dumps(
                {
                    **shared,
                    "focus": (
                        "common misconceptions, corrections, useful examples, and the local "
                        "sources/claims needed to support those corrections"
                    ),
                    "provenance_rule": (
                        "This child is isolated from Evidence Researcher. Return local sources and "
                        "claims only. Claims use zero-based source_indexes; misconceptions/examples "
                        "use zero-based claim_indexes. The host deterministically assigns all "
                        "misconception.* IDs and evidence edges."
                    ),
                    "retrieval_rule": (
                        "If a web-search capability is actually available, use it before the final "
                        "JSON. If no retrieval capability is available, do not fabricate placeholder "
                        "domains such as example.com; return only stable source locators you can identify."
                    ),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            output_schema=_misconception_wire_schema(),
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
            "Specialists return content and index references, never stable IDs or graph edges.",
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
