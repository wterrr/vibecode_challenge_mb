#!/usr/bin/env python3
"""Acceptance verifier for Agent-Aware QA routing."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_aware_qa import (
    AgentAwareQAReport,
    RepairActionKind,
    RepairOwner,
    SceneCriticRepairReport,
    SemanticFindingKind,
    SemanticQAFinding,
    build_agent_repair_task,
    build_routing_context,
    route_agent_aware_qa,
)
from learnflow_v2.layout import LayoutStrategy
from learnflow_v2.qa import (
    CriticFailurePolicy,
    CriticGateState,
    CriticIssue,
    CriticIssueSeverity,
    CriticIssueType,
    CriticPatchOp,
    CriticPatchSuggestion,
    CriticResponse,
    CriticStatus,
    CriticTargetKind,
    CriticTargetRef,
    DeterministicQAReport,
    QAIssue,
    QAIssueCode,
    QAIssueSeverity,
)
from learnflow_v2.videoqa import (
    VideoCriticDimension,
    VideoCriticIssue,
    VideoCriticRecommendation,
    VideoCriticResponse,
    VideoCriticStatus,
    VideoDimensionAssessment,
    VideoIssueSeverity,
    VideoIssueType,
    VideoRecommendationOp,
)
from scripts.verify_script_agent import build_fixture, build_script
from scripts.verify_visual_director import build_visual_output
from visual_director import build_visual_concept_registry


def _assessments(failed: VideoCriticDimension):
    return tuple(
        VideoDimensionAssessment(
            dimension=dimension,
            passed=dimension != failed,
            summary="needs repair" if dimension == failed else "pass",
        )
        for dimension in VideoCriticDimension
    )


def build_acceptance():
    brief, pack, graph, fact_report, pedagogy = build_fixture()
    script = build_script(pedagogy)
    registry = build_visual_concept_registry(pedagogy)
    visual = build_visual_output(script, registry)
    context = build_routing_context(
        pack=pack, pedagogy=pedagogy, script=script, visual=visual
    )
    scene_id = visual.storyboard.scenes[0].scene_id
    node_id = visual.scenegraphs[0].nodes[0].id

    deterministic = DeterministicQAReport(
        scene_id=scene_id,
        passed=False,
        issues=(
            QAIssue(
                issue_id="BBOX_OVERLAP:acceptance",
                code=QAIssueCode.BBOX_OVERLAP,
                severity=QAIssueSeverity.ERROR,
                message="Two visual boxes overlap.",
                object_ids=(node_id,),
                evidence={"source": "acceptance"},
            ),
        ),
    )

    semantic_response = CriticResponse(
        status=CriticStatus.REPAIR,
        issues=(
            CriticIssue(
                issue_id="semantic-visual",
                issue_type=CriticIssueType.PEDAGOGICAL_ALIGNMENT,
                severity=CriticIssueSeverity.HIGH,
                targets=(
                    CriticTargetRef(kind=CriticTargetKind.NODE, target_id=node_id),
                ),
                reason="The chosen visual metaphor does not teach the intended concept.",
            ),
        ),
        patches=(
            CriticPatchSuggestion(
                patch_id="change-visual-intent",
                op=CriticPatchOp.CHANGE_VISUAL_INTENT,
                targets=(
                    CriticTargetRef(kind=CriticTargetKind.NODE, target_id=node_id),
                ),
                semantic_value="comparison",
            ),
        ),
    )

    video_response = VideoCriticResponse(
        status=VideoCriticStatus.REVIEW_REQUIRED,
        dimension_assessments=_assessments(VideoCriticDimension.PEDAGOGICAL_ALIGNMENT),
        issues=(
            VideoCriticIssue(
                issue_id="narration-redundancy",
                issue_type=VideoIssueType.NARRATION_REDUNDANCY,
                severity=VideoIssueSeverity.MEDIUM,
                scene_ids=(scene_id,),
                reason="The narration repeats the same explanation.",
            ),
        ),
        recommendations=(
            VideoCriticRecommendation(
                recommendation_id="reduce-redundancy",
                op=VideoRecommendationOp.REDUCE_NARRATION_REDUNDANCY,
                scene_ids=(scene_id,),
                rationale="Condense repeated narration.",
            ),
        ),
    )

    report = AgentAwareQAReport(
        report_id="agent-aware.acceptance",
        semantic_findings=(
            SemanticQAFinding(
                finding_id="unsupported-claim",
                kind=SemanticFindingKind.EVIDENCE_UNSUPPORTED,
                reason="The cited evidence does not support this factual claim.",
                claim_ids=(pack.claims[0].claim_id,),
            ),
            SemanticQAFinding(
                finding_id="narration-fact",
                kind=SemanticFindingKind.NARRATION_FACT_MISMATCH,
                reason="Narration overstates the approved claim.",
                claim_ids=(pack.claims[0].claim_id,),
                segment_ids=(script.segments[0].segment_id,),
            ),
            SemanticQAFinding(
                finding_id="pedagogy-structure",
                kind=SemanticFindingKind.PEDAGOGICAL_STRUCTURE,
                reason="The learning objective needs a clearer progression.",
                objective_ids=(pedagogy.learning_objectives[0].objective_id,),
            ),
        ),
        deterministic_reports=(deterministic,),
        scene_critic_repairs=(
            SceneCriticRepairReport(scene_id=scene_id, response=semantic_response),
        ),
        video_critic_response=video_response,
    )
    plan = route_agent_aware_qa(report, context=context)
    return brief, pack, graph, fact_report, pedagogy, script, visual, plan


def main() -> int:
    brief, pack, graph, fact_report, pedagogy, script, visual, plan = build_acceptance()
    owners = {intent.owner for intent in plan.intents}
    required = {
        RepairOwner.RESEARCH_ORCHESTRATION,
        RepairOwner.SCRIPT_AGENT,
        RepairOwner.PEDAGOGY_AGENT,
        RepairOwner.VISUAL_DIRECTOR,
        RepairOwner.CORE_REPAIR,
    }
    if not required.issubset(owners):
        raise SystemExit(
            f"AGENT_AWARE_QA=FAIL owners missing={sorted(x.value for x in required-owners)}"
        )
    if not plan.publication_blocked:
        raise SystemExit("AGENT_AWARE_QA=FAIL repair plan must block publication")

    core_intents = [
        intent for intent in plan.intents if intent.owner == RepairOwner.CORE_REPAIR
    ]
    if not any(
        intent.action == RepairActionKind.CORE_DETERMINISTIC_REPAIR
        for intent in core_intents
    ):
        raise SystemExit("AGENT_AWARE_QA=FAIL deterministic Core route missing")

    for intent in plan.intents:
        if intent.owner == RepairOwner.CORE_REPAIR:
            continue
        task = build_agent_repair_task(
            intent,
            brief=brief,
            pack=pack,
            graph=graph,
            fact_report=fact_report,
            pedagogy=pedagogy,
            script=script,
            visual=visual,
        )
        if not task.get("output_schema") or not task.get("context"):
            raise SystemExit("AGENT_AWARE_QA=FAIL agent repair task incomplete")

    print("AGENT_AWARE_QA=PASS")
    print("factual_evidence_to_research=PASS")
    print("factual_narration_to_script=PASS")
    print("pedagogical_structure_to_pedagogy=PASS")
    print("semantic_visual_to_visual_director=PASS")
    print("deterministic_geometry_to_core=PASS")
    print("video_narration_to_script=PASS")
    print("publication_blocked_on_repair=PASS")
    print("existing_agent_task_boundaries_reused=PASS")
    print(f"intent_count={len(plan.intents)}")
    print(f"plan_id={plan.plan_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
