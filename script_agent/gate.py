"""Deterministic gate for Hermes-generated lesson scripts."""

from __future__ import annotations

import re

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

from .models import ScriptIssue, ScriptValidation


_FACT_BEARING_FUNCTIONS = {
    TeachingFunction.EXPLAIN,
    TeachingFunction.COMPARE,
    TeachingFunction.DEMONSTRATE,
    TeachingFunction.SUMMARIZE,
}

_BOUNDARY_PATTERNS = (
    re.compile(r"\`\`\`"),
    re.compile(r"\bscenegraph\b", re.IGNORECASE),
    re.compile(r"\brender_scene_video\b", re.IGNORECASE),
    re.compile(r"\bdeterministicpillowrenderer\b", re.IGNORECASE),
    re.compile(r"\bffmpeg\b", re.IGNORECASE),
    re.compile(r"\b(?:left|top|right|bottom)\s*:\s*-?\d+(?:\.\d+)?\s*px\b", re.IGNORECASE),
    re.compile(r"\b(?:x_px|y_px|pixel_x|pixel_y)\s*[:=]\s*-?\d+(?:\.\d+)?\b", re.IGNORECASE),
    re.compile(r"\bposition\s*:\s*(?:absolute|fixed)\b", re.IGNORECASE),
)


def selected_pedagogy_claim_ids(plan: PedagogyPlan) -> set[str]:
    return {
        claim_id
        for item in (*plan.worked_examples, *plan.analogies, *plan.misconceptions)
        for claim_id in item.claim_ids
    }


def _segment_has_boundary_directive(segment) -> bool:
    text = "\n".join(
        (
            segment.spoken_text,
            segment.subtitle_text,
            *segment.emphasis,
        )
    )
    return any(pattern.search(text) for pattern in _BOUNDARY_PATTERNS)


def validate_lesson_script(
    script: LessonScript,
    *,
    brief: LearningBrief,
    pack: ResearchPack,
    graph: EvidenceGraph,
    fact_report: FactVerificationReport,
    pedagogy: PedagogyPlan,
) -> ScriptValidation:
    """Validate claim preservation, objective coverage, and Script/Visual boundary."""

    pedagogy_validation = validate_pedagogy_plan(
        pedagogy,
        brief=brief,
        pack=pack,
        graph=graph,
        fact_report=fact_report,
    )
    require_script_ready(pedagogy_validation)
    script.validate_against(graph, pedagogy)

    expected_claim_ids = selected_pedagogy_claim_ids(pedagogy)
    actual_claim_ids = {
        claim_id
        for segment in script.segments
        for claim_id in segment.claim_ids
    }
    missing_claim_ids = tuple(sorted(expected_claim_ids - actual_claim_ids))
    unexpected_claim_ids = tuple(sorted(actual_claim_ids - expected_claim_ids))

    expected_objective_ids = {
        objective.objective_id for objective in pedagogy.learning_objectives
    }
    actual_objective_ids = {
        objective_id
        for segment in script.segments
        for objective_id in segment.objective_ids
    }
    uncovered_objective_ids = tuple(
        sorted(expected_objective_ids - actual_objective_ids)
    )

    ungrounded_segment_ids = tuple(
        segment.segment_id
        for segment in script.segments
        if expected_claim_ids
        and segment.teaching_function in _FACT_BEARING_FUNCTIONS
        and not segment.claim_ids
    )

    boundary_violation_segment_ids = tuple(
        segment.segment_id
        for segment in script.segments
        if _segment_has_boundary_directive(segment)
    )

    issues: list[ScriptIssue] = []
    if missing_claim_ids or unexpected_claim_ids:
        issues.append(ScriptIssue.CLAIM_SET_MISMATCH)
    if uncovered_objective_ids:
        issues.append(ScriptIssue.OBJECTIVE_NOT_COVERED)
    if ungrounded_segment_ids:
        issues.append(ScriptIssue.FACT_BEARING_SEGMENT_WITHOUT_CLAIM)
    if boundary_violation_segment_ids:
        issues.append(ScriptIssue.VISUAL_OR_IMPLEMENTATION_DIRECTIVE)

    return ScriptValidation(
        script_id=script.script_id,
        issues=tuple(issues),
        missing_claim_ids=missing_claim_ids,
        unexpected_claim_ids=unexpected_claim_ids,
        uncovered_objective_ids=uncovered_objective_ids,
        ungrounded_segment_ids=ungrounded_segment_ids,
        boundary_violation_segment_ids=boundary_violation_segment_ids,
    )


def require_visual_director_ready(validation: ScriptValidation) -> None:
    if validation.ready_for_visual_director:
        return
    raise AgentContractError(
        "LessonScript is not ready for Visual Director: "
        f"issues={[issue.value for issue in validation.issues]!r}, "
        f"missing_claim_ids={validation.missing_claim_ids!r}, "
        f"unexpected_claim_ids={validation.unexpected_claim_ids!r}, "
        f"uncovered_objective_ids={validation.uncovered_objective_ids!r}, "
        f"ungrounded_segment_ids={validation.ungrounded_segment_ids!r}, "
        f"boundary_violation_segment_ids={validation.boundary_violation_segment_ids!r}"
    )
