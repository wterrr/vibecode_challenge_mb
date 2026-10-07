"""Hermes-facing task construction for the LearnFlow Script Agent."""

from __future__ import annotations

import json
from typing import Any

from agent_contracts import (
    AgentContractError,
    EvidenceGraph,
    LearningBrief,
    LessonScript,
    PedagogyPlan,
    ResearchPack,
    TeachingFunction,
)
from fact_verification import FactVerificationReport
from pedagogy_agent import require_script_ready, validate_pedagogy_plan

from .gate import selected_pedagogy_claim_ids


_FACT_BEARING_FUNCTIONS = {
    TeachingFunction.EXPLAIN,
    TeachingFunction.COMPARE,
    TeachingFunction.DEMONSTRATE,
    TeachingFunction.SUMMARIZE,
}


def _indexed_array_schema(count: int, *, description: str) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "array",
        "uniqueItems": True,
        "items": {
            "type": "integer",
            "minimum": 0,
        },
        "description": description,
    }
    if count:
        schema["items"]["maximum"] = count - 1
    else:
        schema["maxItems"] = 0
    return schema


def _script_wire_schema(
    *,
    claim_count: int,
    objective_count: int,
) -> dict[str, Any]:
    """Model-facing script schema with dynamic references owned by the host."""

    schema = json.loads(json.dumps(LessonScript.model_json_schema()))
    segment_schema = dict((schema.get("$defs") or {}).get("ScriptSegment") or {})
    properties = dict(segment_schema.get("properties") or {})
    if "claim_ids" not in properties or "objective_ids" not in properties:
        raise AgentContractError(
            "LessonScript schema is missing dynamic reference fields"
        )

    properties.pop("claim_ids", None)
    properties.pop("objective_ids", None)
    properties["claim_indexes"] = _indexed_array_schema(
        claim_count,
        description=(
            "Unique zero-based indexes into context.selected_fact_claim_catalog "
            "for factual claims used by this segment."
        ),
    )
    properties["objective_indexes"] = _indexed_array_schema(
        objective_count,
        description=(
            "Unique zero-based indexes into context.objective_catalog "
            "for learning objectives covered by this segment."
        ),
    )
    segment_schema["properties"] = properties

    required = list(segment_schema.get("required") or [])
    required = [
        "claim_indexes" if field == "claim_ids"
        else "objective_indexes" if field == "objective_ids"
        else field
        for field in required
    ]
    segment_schema["required"] = required
    schema["$defs"]["ScriptSegment"] = segment_schema
    return schema


def _validate_indexes(
    value: Any,
    *,
    count: int,
    field_name: str,
) -> list[int]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise AgentContractError(f"{field_name} must be an array")

    indexes: list[int] = []
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool):
            raise AgentContractError(f"{field_name} entries must be integers")
        if item < 0 or item >= count:
            upper = count - 1
            raise AgentContractError(
                f"{field_name} index {item} is outside 0..{upper}"
            )
        indexes.append(item)
    if len(indexes) != len(set(indexes)):
        raise AgentContractError(f"{field_name} must be unique")
    return indexes


def assemble_lesson_script_wire(
    payload: dict[str, Any],
    *,
    claim_ids: tuple[str, ...],
    objective_ids: tuple[str, ...],
) -> LessonScript:
    """Map indexes to exact IDs and enforce full semantic coverage before gating."""

    if not isinstance(payload, dict):
        raise AgentContractError("LessonScript wire output must be an object")

    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list) or not raw_segments:
        raise AgentContractError("LessonScript segments must be a non-empty array")

    canonical = dict(payload)
    segments: list[dict[str, Any]] = []
    used_claim_indexes: set[int] = set()
    used_objective_indexes: set[int] = set()

    for position, raw_segment in enumerate(raw_segments):
        if not isinstance(raw_segment, dict):
            raise AgentContractError(
                f"segments[{position}] must be an object"
            )
        if "claim_ids" in raw_segment or "objective_ids" in raw_segment:
            raise AgentContractError(
                "Script wire output must use claim_indexes/objective_indexes, "
                "not claim_ids/objective_ids"
            )

        segment = dict(raw_segment)
        claim_indexes = _validate_indexes(
            segment.pop("claim_indexes", []),
            count=len(claim_ids),
            field_name=f"segments[{position}].claim_indexes",
        )
        objective_indexes = _validate_indexes(
            segment.pop("objective_indexes", []),
            count=len(objective_ids),
            field_name=f"segments[{position}].objective_indexes",
        )
        used_claim_indexes.update(claim_indexes)
        used_objective_indexes.update(objective_indexes)
        segment["claim_ids"] = [claim_ids[index] for index in claim_indexes]
        segment["objective_ids"] = [
            objective_ids[index] for index in objective_indexes
        ]
        segments.append(segment)

    missing_claim_indexes = sorted(
        set(range(len(claim_ids))) - used_claim_indexes
    )
    if missing_claim_indexes:
        missing_claim_ids = tuple(claim_ids[index] for index in missing_claim_indexes)
        raise AgentContractError(
            "LessonScript must cover every selected factual claim; "
            f"missing claim_ids={missing_claim_ids!r}"
        )

    missing_objective_indexes = sorted(
        set(range(len(objective_ids))) - used_objective_indexes
    )
    if missing_objective_indexes:
        missing_objective_ids = tuple(
            objective_ids[index] for index in missing_objective_indexes
        )
        raise AgentContractError(
            "LessonScript must cover every learning objective; "
            f"missing objective_ids={missing_objective_ids!r}"
        )

    canonical["segments"] = segments
    script = LessonScript.model_validate(canonical)

    if claim_ids:
        ungrounded = tuple(
            segment.segment_id
            for segment in script.segments
            if segment.teaching_function in _FACT_BEARING_FUNCTIONS
            and not segment.claim_ids
        )
        if ungrounded:
            raise AgentContractError(
                "Fact-bearing Script segments require claim coverage; "
                f"ungrounded_segment_ids={ungrounded!r}"
            )

    return script


def build_script_agent_task(
    brief: LearningBrief,
    pack: ResearchPack,
    graph: EvidenceGraph,
    fact_report: FactVerificationReport,
    pedagogy: PedagogyPlan,
) -> dict:
    """Build a narration-only Hermes task from a validated PedagogyPlan."""

    pedagogy_validation = validate_pedagogy_plan(
        pedagogy,
        brief=brief,
        pack=pack,
        graph=graph,
        fact_report=fact_report,
    )
    require_script_ready(pedagogy_validation)

    selected_ids = selected_pedagogy_claim_ids(pedagogy)
    selected_claims = [
        claim
        for claim in pack.claims
        if claim.claim_id in selected_ids
    ]
    claim_ids = tuple(claim.claim_id for claim in selected_claims)
    objective_ids = tuple(
        objective.objective_id for objective in pedagogy.learning_objectives
    )

    payload = {
        "learning_brief": json.loads(brief.to_canonical_json()),
        "pedagogy_plan": json.loads(pedagogy.to_canonical_json()),
        "selected_fact_claims": [
            claim.model_dump(mode="json") for claim in selected_claims
        ],
        "selected_fact_claim_catalog": [
            {
                "index": index,
                "claim_id": claim.claim_id,
                "statement": claim.statement,
            }
            for index, claim in enumerate(selected_claims)
        ],
        "objective_catalog": [
            {
                "index": index,
                "objective_id": objective.objective_id,
                "description": objective.description,
            }
            for index, objective in enumerate(pedagogy.learning_objectives)
        ],
        "required_ids": {
            "pedagogy_plan_id": pedagogy.plan_id,
        },
        "instructions": [
            "Return one LessonScript-shaped JSON object and no prose outside the structured result.",
            (
                "For each segment return claim_indexes, not claim_ids. claim_indexes "
                "must reference selected_fact_claim_catalog. Across all segments, cover "
                "every selected claim at least once; the host reconstructs exact claim_ids."
            ),
            (
                "For each segment return objective_indexes, not objective_ids. "
                "objective_indexes must reference objective_catalog. Across all segments, "
                "cover every learning objective at least once."
            ),
            "Every factual assertion must be attached to the relevant selected claim index.",
            "Assign exactly one teaching_function to every segment using the LessonScript schema.",
            "Use INTRODUCE for framing, EXPLAIN for concepts, COMPARE for contrasts, DEMONSTRATE for worked examples, PRACTICE/CHECK for learner activity, and SUMMARIZE for synthesis when appropriate.",
            "Write narration and subtitle text only. Keep spoken_text natural for voiceover.",
            "Do not output visual coordinates, pixel values, SceneGraph objects, renderer instructions, FFmpeg commands, implementation code, or fenced code blocks.",
            "Do not make layout, motion, camera, typography, or rendering decisions; those belong to Visual Director and Core.",
        ],
    }
    return {
        "goal": (
            "Act as LearnFlow Script Agent. Turn the validated PedagogyPlan into a "
            "claim-preserving educational LessonScript without visual implementation details."
        ),
        "context": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        "output_schema": _script_wire_schema(
            claim_count=len(claim_ids),
            objective_count=len(objective_ids),
        ),
    }
