"""Hermes task construction for semantic visual direction."""

from __future__ import annotations

import json

from agent_contracts import (
    EvidenceGraph,
    LearningBrief,
    LessonScript,
    PedagogyPlan,
    ResearchPack,
)
from fact_verification import FactVerificationReport
from script_agent import require_visual_director_ready, validate_lesson_script

from .models import VisualDirectorOutput
from .registry import build_visual_concept_registry


def build_visual_director_task(
    brief: LearningBrief,
    pack: ResearchPack,
    graph: EvidenceGraph,
    fact_report: FactVerificationReport,
    pedagogy: PedagogyPlan,
    script: LessonScript,
) -> dict:
    """Build a semantic-only Hermes task from a deterministically valid script."""

    script_validation = validate_lesson_script(
        script,
        brief=brief,
        pack=pack,
        graph=graph,
        fact_report=fact_report,
        pedagogy=pedagogy,
    )
    require_visual_director_ready(script_validation)

    registry = build_visual_concept_registry(pedagogy)
    payload = {
        "lesson_script": json.loads(script.to_canonical_json()),
        "concept_registry": registry.to_schema().model_dump(mode="json"),
        "concept_order": list(pedagogy.concept_order),
        "required_ids": {"script_id": script.script_id},
        "instructions": [
            "Return one VisualDirectorOutput and no prose outside the structured result.",
            "Create a Storyboard plus exactly one SceneGraph for each storyboard scene.",
            "Cover every LessonScript segment exactly once and in original order; only group adjacent segments that share the same teaching_function.",
            "Storyboard scene teaching_function must match every ScriptSegment assigned to that scene.",
            "Use only concept_ref and semantic_key pairs from the provided deterministic ConceptRegistry. Do not invent concept IDs or canonical keys.",
            "Storyboard concept_refs must equal the concept_ref set used by its SceneGraph; continuity_keys must be the canonical semantic keys for those same concepts.",
            "Use semantic SceneGraph structure only: nodes, relations, groups, symbolic style_refs, LayoutIntent, ReadingDirection, PortHint, and semantic LayoutHint fields.",
            "Layout hints may express preferred_region, relative importance, keep_near, keep_apart, and preferred_order only.",
            "Never output x/y coordinates, pixel values, width/height geometry, absolute font sizes, CSS positioning, renderer commands, FFmpeg commands, Manim/Pillow implementation instructions, or arbitrary rendering code.",
            "Do not decide motion, camera paths, timeline arithmetic, typography sizes, edge coordinates, or final pixels; Core V2 owns those decisions.",
            "Use visual rhythm and diversity when useful, while preserving concept continuity and keeping cognitive load appropriate for the script.",
            "Do not introduce new factual claims. Visual labels/content must stay within the supplied script and canonical concept labels.",
        ],
    }
    return {
        "goal": (
            "Act as LearnFlow Visual Director. Convert the validated LessonScript into "
            "a semantic Storyboard and schema-valid SceneGraph sequence without geometry "
            "or renderer implementation details."
        ),
        "context": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        "output_schema": VisualDirectorOutput.model_json_schema(),
    }
