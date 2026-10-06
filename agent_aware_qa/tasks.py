"""Hermes repair-task construction after deterministic Agent-Aware routing."""

from __future__ import annotations

import json

from agent_contracts import (
    AgentContractError,
    EvidenceGraph,
    LearningBrief,
    LessonScript,
    PedagogyPlan,
    ResearchPack,
)
from fact_verification import FactVerificationReport
from pedagogy_agent import build_pedagogy_agent_task
from research_orchestration import build_director_delegate_task
from script_agent import build_script_agent_task
from visual_director import VisualDirectorOutput, build_visual_director_task

from .models import RepairIntent, RepairOwner


def _augment(
    base: dict,
    intent: RepairIntent,
    instruction: str,
    *,
    current_artifact_key: str | None = None,
    current_artifact=None,
) -> dict:
    payload = json.loads(base["context"])
    payload["agent_aware_qa_repair_intent"] = intent.model_dump(mode="json")
    if current_artifact_key is not None:
        if current_artifact is None:
            raise AgentContractError(
                f"{current_artifact_key} is required for selective repair"
            )
        payload[current_artifact_key] = current_artifact.model_dump(mode="json")
    payload["repair_mode"] = {
        "instruction": instruction,
        "preserve_unaffected_content": True,
        "return_structured_output_only": True,
    }
    return {
        **base,
        "goal": base["goal"] + " Repair only the routed Agent-Aware QA issue.",
        "context": json.dumps(payload, ensure_ascii=False, sort_keys=True),
    }


def build_agent_repair_task(
    intent: RepairIntent,
    *,
    brief: LearningBrief,
    pack: ResearchPack,
    graph: EvidenceGraph,
    fact_report: FactVerificationReport,
    pedagogy: PedagogyPlan,
    script: LessonScript,
    visual: VisualDirectorOutput,
) -> dict:
    """Build a bounded owner-specific Hermes task; Core intents are never delegated."""

    intent = RepairIntent.model_validate(intent.model_dump(mode="json"))
    if intent.owner == RepairOwner.CORE_REPAIR:
        raise AgentContractError(
            "Core repair intents must stay deterministic and cannot become Hermes tasks"
        )

    if intent.owner == RepairOwner.RESEARCH_ORCHESTRATION:
        base = build_director_delegate_task(brief)
        payload = json.loads(base["context"])
        payload["current_research_pack"] = pack.model_dump(mode="json")
        payload["current_evidence_graph"] = graph.model_dump(mode="json")
        base = {**base, "context": json.dumps(payload, ensure_ascii=False, sort_keys=True)}
        return _augment(
            base,
            intent,
            "Repair evidence/provenance for only the routed claim_ids. Keep unrelated research stable and preserve source provenance.",
        )

    if intent.owner == RepairOwner.SCRIPT_AGENT:
        return _augment(
            build_script_agent_task(
                brief,
                pack,
                graph,
                fact_report,
                pedagogy,
            ),
            intent,
            "Repair only the routed narration/factual/pacing problem. Preserve every unaffected segment and ID. Do not make visual, geometry, motion, or renderer decisions.",
            current_artifact_key="current_lesson_script",
            current_artifact=script,
        )

    if intent.owner == RepairOwner.PEDAGOGY_AGENT:
        return _augment(
            build_pedagogy_agent_task(
                brief,
                pack,
                graph,
                fact_report,
            ),
            intent,
            "Repair only the routed pedagogical structure problem. Preserve unaffected objectives, concept order, examples, misconceptions, and assessment probes. Do not write narration or visual implementation.",
            current_artifact_key="current_pedagogy_plan",
            current_artifact=pedagogy,
        )

    if intent.owner == RepairOwner.VISUAL_DIRECTOR:
        return _augment(
            build_visual_director_task(
                brief,
                pack,
                graph,
                fact_report,
                pedagogy,
                script,
            ),
            intent,
            "Repair only the routed semantic visual problem in the affected scenes. Preserve unaffected storyboard scenes and SceneGraphs exactly. Keep output semantic-only; Core owns geometry, motion compilation, and pixels.",
            current_artifact_key="current_visual_director_output",
            current_artifact=visual,
        )

    raise AgentContractError(f"unsupported repair owner {intent.owner.value!r}")
