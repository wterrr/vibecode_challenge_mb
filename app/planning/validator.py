"""Semantic validator for LessonPlan domain models."""

import re
from typing import Literal
from pydantic import BaseModel
from app.domain.enums import VisualIntent
from app.domain.lesson import (
    ComparisonSpec,
    ConceptCardSpec,
    LearningRequest,
    LessonPlan,
    ProcessDiagramSpec,
)

STOPWORDS: set[str] = {
    # English generic / meta words
    "what",
    "is",
    "how",
    "does",
    "the",
    "a",
    "an",
    "to",
    "for",
    "in",
    "of",
    "and",
    "or",
    "on",
    "with",
    "at",
    "by",
    "from",
    "about",
    "explain",
    "process",
    "overview",
    "introduction",
    "intro",
    "guide",
    "steps",
    # Vietnamese generic / meta words
    "la",
    "gi",
    "nhu",
    "the",
    "nao",
    "cach",
    "cua",
    "cho",
    "va",
    "trong",
    "ve",
    "mot",
    "cac",
    "nhung",
    "giai",
    "thich",
    "qua",
    "quá",
    "trinh",
    "trình",
    "buoc",
    "bước",
    "bai",
    "bài",
    "hoc",
    "học",
    "tong",
    "tổng",
    "quan",
}


class PlanIssue(BaseModel):
    """A semantic issue discovered during lesson plan validation."""

    code: str
    message: str
    scene_id: str | None = None
    severity: Literal["error", "warning"]


def validate_lesson_plan(
    request: LearningRequest,
    plan: LessonPlan,
) -> list[PlanIssue]:
    """Perform semantic and pedagogical validation on a LessonPlan.

    Checks language alignment, topic relevance, scene structure, visual spec
    consistency, and word-budget duration warnings.
    """
    issues: list[PlanIssue] = []

    # 1. Language alignment check
    if plan.language != request.language:
        issues.append(
            PlanIssue(
                code="plan_language_mismatch",
                message=(
                    f"Plan language '{plan.language}' does not match "
                    f"requested language '{request.language}'."
                ),
                severity="error",
            )
        )

    # 2. Scene count boundary (defensive check)
    scene_count = len(plan.scenes)
    if scene_count < 3 or scene_count > 6:
        issues.append(
            PlanIssue(
                code="invalid_scene_count",
                message=f"Lesson plan must contain 3 to 6 scenes, found {scene_count}.",
                severity="error",
            )
        )

    # 3. Duplicate scene IDs
    seen_ids: set[str] = set()
    for scene in plan.scenes:
        if scene.scene_id in seen_ids:
            issues.append(
                PlanIssue(
                    code="duplicate_scene_id",
                    message=f"Duplicate scene id '{scene.scene_id}'.",
                    scene_id=scene.scene_id,
                    severity="error",
                )
            )
        seen_ids.add(scene.scene_id)

    # 4. Per-scene content integrity
    for scene in plan.scenes:
        if not scene.narration.strip():
            issues.append(
                PlanIssue(
                    code="empty_narration",
                    message="Scene narration cannot be empty.",
                    scene_id=scene.scene_id,
                    severity="error",
                )
            )

        if not scene.key_points or all(not p.strip() for p in scene.key_points):
            issues.append(
                PlanIssue(
                    code="empty_key_points",
                    message="Scene must provide at least one non-empty key point.",
                    scene_id=scene.scene_id,
                    severity="error",
                )
            )

        # Visual intent vs spec consistency
        if scene.visual_intent.value != scene.visual_spec.type:
            issues.append(
                PlanIssue(
                    code="visual_intent_mismatch",
                    message=(
                        f"visual_intent '{scene.visual_intent.value}' does not match "
                        f"spec type '{scene.visual_spec.type}'."
                    ),
                    scene_id=scene.scene_id,
                    severity="error",
                )
            )

        # Process diagram actor reference check
        if (
            scene.visual_intent == VisualIntent.PROCESS_DIAGRAM
            and isinstance(scene.visual_spec, ProcessDiagramSpec)
        ):
            actor_ids = {a.id for a in scene.visual_spec.actors}
            for step in scene.visual_spec.steps:
                if step.from_actor and step.from_actor not in actor_ids:
                    issues.append(
                        PlanIssue(
                            code="missing_actor_reference",
                            message=f"Step {step.order} references undefined from_actor '{step.from_actor}'.",
                            scene_id=scene.scene_id,
                            severity="error",
                        )
                    )
                if step.to_actor and step.to_actor not in actor_ids:
                    issues.append(
                        PlanIssue(
                            code="missing_actor_reference",
                            message=f"Step {step.order} references undefined to_actor '{step.to_actor}'.",
                            scene_id=scene.scene_id,
                            severity="error",
                        )
                    )

        # Comparison column check
        if (
            scene.visual_intent == VisualIntent.COMPARISON
            and isinstance(scene.visual_spec, ComparisonSpec)
        ):
            if len(scene.visual_spec.columns) < 2:
                issues.append(
                    PlanIssue(
                        code="invalid_comparison_columns",
                        message="Comparison visual must have at least 2 columns.",
                        scene_id=scene.scene_id,
                        severity="error",
                    )
                )

    # 5. Topic relevance heuristic
    raw_topic_tokens = re.findall(r"[\w]+", request.topic.lower())
    meaningful_topic_keywords = [
        t for t in raw_topic_tokens if t not in STOPWORDS and len(t) > 1
    ]

    if meaningful_topic_keywords:
        plan_corpus_parts = [
            plan.title,
            plan.topic,
            plan.summary,
            plan.learning_objective,
        ]
        for s in plan.scenes:
            plan_corpus_parts.extend([s.title, s.concept, s.narration])
        plan_corpus_text = " ".join(plan_corpus_parts).lower()
        plan_corpus_tokens = set(re.findall(r"[\w]+", plan_corpus_text))

        matching_keywords = [
            k for k in meaningful_topic_keywords if k in plan_corpus_tokens
        ]
        if not matching_keywords:
            issues.append(
                PlanIssue(
                    code="plan_topic_mismatch",
                    message="The generated plan appears completely unrelated to the requested topic.",
                    severity="error",
                )
            )

    # 6. Warnings (do not block execution or trigger repair)
    # Repeated scene titles
    scene_titles = [s.title.strip().lower() for s in plan.scenes if s.title.strip()]
    if len(scene_titles) != len(set(scene_titles)):
        issues.append(
            PlanIssue(
                code="repeated_scene_titles",
                message="Multiple scenes share the exact same title.",
                severity="warning",
            )
        )

    # Too many content points in a scene
    for scene in plan.scenes:
        if isinstance(scene.visual_spec, ConceptCardSpec) and len(scene.visual_spec.points) > 4:
            issues.append(
                PlanIssue(
                    code="too_many_scene_points",
                    message="Concept card has more than 4 points; consider consolidating for viewer readability.",
                    scene_id=scene.scene_id,
                    severity="warning",
                )
            )

    # Narration duration budget warning
    total_spoken_words = sum(len(s.narration.split()) for s in plan.scenes)
    duration = request.target_duration_seconds
    if duration == 60:
        if total_spoken_words < 60:
            issues.append(
                PlanIssue(
                    code="narration_likely_too_short",
                    message=f"Total spoken words ({total_spoken_words}) is likely too short for a 60s video.",
                    severity="warning",
                )
            )
        elif total_spoken_words > 180:
            issues.append(
                PlanIssue(
                    code="narration_likely_too_long",
                    message=f"Total spoken words ({total_spoken_words}) is likely too long for a 60s video.",
                    severity="warning",
                )
            )
    elif duration == 90:
        if total_spoken_words < 100:
            issues.append(
                PlanIssue(
                    code="narration_likely_too_short",
                    message=f"Total spoken words ({total_spoken_words}) is likely too short for a 90s video.",
                    severity="warning",
                )
            )
        elif total_spoken_words > 260:
            issues.append(
                PlanIssue(
                    code="narration_likely_too_long",
                    message=f"Total spoken words ({total_spoken_words}) is likely too long for a 90s video.",
                    severity="warning",
                )
            )
    elif duration == 120:
        if total_spoken_words < 140:
            issues.append(
                PlanIssue(
                    code="narration_likely_too_short",
                    message=f"Total spoken words ({total_spoken_words}) is likely too short for a 120s video.",
                    severity="warning",
                )
            )
        elif total_spoken_words > 340:
            issues.append(
                PlanIssue(
                    code="narration_likely_too_long",
                    message=f"Total spoken words ({total_spoken_words}) is likely too long for a 120s video.",
                    severity="warning",
                )
            )

    return issues
