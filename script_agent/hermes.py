"""Hermes-facing task construction for the LearnFlow Script Agent."""

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
from pedagogy_agent import require_script_ready, validate_pedagogy_plan

from .gate import selected_pedagogy_claim_ids


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
        claim.model_dump(mode="json")
        for claim in pack.claims
        if claim.claim_id in selected_ids
    ]

    payload = {
        "learning_brief": json.loads(brief.to_canonical_json()),
        "pedagogy_plan": json.loads(pedagogy.to_canonical_json()),
        "selected_fact_claims": selected_claims,
        "required_ids": {
            "pedagogy_plan_id": pedagogy.plan_id,
        },
        "instructions": [
            "Return one LessonScript and no prose outside the structured result.",
            "Preserve the PedagogyPlan claim_ids exactly: do not drop a selected claim_id and do not add a new claim_id.",
            "Every factual assertion must be attached to the relevant approved claim_id.",
            "Cover every learning objective in at least one segment via objective_ids.",
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
        "output_schema": LessonScript.model_json_schema(),
    }
