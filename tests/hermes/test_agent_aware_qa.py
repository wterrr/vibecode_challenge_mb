from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import AgentContractError
from agent_aware_qa import (
    AgentAwareQAReport,
    QARoutingContext,
    RepairActionKind,
    RepairOwner,
    SceneCriticRepairReport,
    SemanticFindingKind,
    SemanticQAFinding,
    build_agent_repair_task,
    build_routing_context,
    route_agent_aware_qa,
)
from learnflow_v2.qa import (
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
from learnflow_v2.scenegraph import PreferredRegion
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


def fixture():
    brief, pack, graph, fact_report, pedagogy = build_fixture()
    script = build_script(pedagogy)
    registry = build_visual_concept_registry(pedagogy)
    visual = build_visual_output(script, registry)
    context = build_routing_context(
        pack=pack, pedagogy=pedagogy, script=script, visual=visual
    )
    return brief, pack, graph, fact_report, pedagogy, script, visual, context


def route(report, context):
    return route_agent_aware_qa(report, context=context)


def test_factual_evidence_routes_to_research():
    *_, context = fixture()
    finding = SemanticQAFinding(
        finding_id="f",
        kind=SemanticFindingKind.EVIDENCE_CONTRADICTED,
        reason="Evidence contradicts claim.",
        claim_ids=(context.claim_ids[0],),
    )
    plan = route(AgentAwareQAReport(report_id="r", semantic_findings=(finding,)), context)
    assert plan.intents[0].owner == RepairOwner.RESEARCH_ORCHESTRATION
    assert plan.intents[0].action == RepairActionKind.RESEARCH_EVIDENCE_REPAIR


def test_factual_narration_routes_to_script():
    *_, context = fixture()
    finding = SemanticQAFinding(
        finding_id="f",
        kind=SemanticFindingKind.NARRATION_FACT_MISMATCH,
        reason="Narration overstates claim.",
        claim_ids=(context.claim_ids[0],),
        segment_ids=(context.segment_ids[0],),
    )
    plan = route(AgentAwareQAReport(report_id="r", semantic_findings=(finding,)), context)
    assert plan.intents[0].owner == RepairOwner.SCRIPT_AGENT
    assert plan.intents[0].action == RepairActionKind.SCRIPT_FACT_REWRITE


def test_semantic_visual_routes_to_visual_director():
    *_, context = fixture()
    finding = SemanticQAFinding(
        finding_id="f",
        kind=SemanticFindingKind.SEMANTIC_VISUAL_MISMATCH,
        reason="Visual metaphor is wrong.",
        scene_ids=(context.scene_ids[0],),
    )
    plan = route(AgentAwareQAReport(report_id="r", semantic_findings=(finding,)), context)
    assert plan.intents[0].owner == RepairOwner.VISUAL_DIRECTOR


def test_pedagogical_structure_routes_to_pedagogy():
    *_, context = fixture()
    finding = SemanticQAFinding(
        finding_id="f",
        kind=SemanticFindingKind.PEDAGOGICAL_STRUCTURE,
        reason="Concept progression is confusing.",
        objective_ids=(context.objective_ids[0],),
    )
    plan = route(AgentAwareQAReport(report_id="r", semantic_findings=(finding,)), context)
    assert plan.intents[0].owner == RepairOwner.PEDAGOGY_AGENT


def test_deterministic_geometry_stays_in_core():
    *_, context = fixture()
    report = DeterministicQAReport(
        scene_id=context.scene_ids[0],
        passed=False,
        issues=(
            QAIssue(
                issue_id="BBOX_OVERLAP:a",
                code=QAIssueCode.BBOX_OVERLAP,
                severity=QAIssueSeverity.ERROR,
                message="overlap",
                object_ids=("n1", "n2"),
                evidence={},
            ),
        ),
    )
    plan = route(AgentAwareQAReport(report_id="r", deterministic_reports=(report,)), context)
    assert plan.intents[0].owner == RepairOwner.CORE_REPAIR
    assert plan.intents[0].action == RepairActionKind.CORE_DETERMINISTIC_REPAIR


def _scene_repair(scene_id, node_id, *, semantic=False):
    issue = CriticIssue(
        issue_id="i",
        issue_type=(
            CriticIssueType.PEDAGOGICAL_ALIGNMENT
            if semantic
            else CriticIssueType.READABILITY
        ),
        severity=CriticIssueSeverity.MEDIUM,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id=node_id),),
        reason="needs repair",
    )
    patch = (
        CriticPatchSuggestion(
            patch_id="p",
            op=CriticPatchOp.CHANGE_VISUAL_INTENT,
            targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id=node_id),),
            semantic_value="comparison",
        )
        if semantic
        else CriticPatchSuggestion(
            patch_id="p",
            op=CriticPatchOp.SET_REGION,
            targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id=node_id),),
            region=PreferredRegion.RIGHT,
        )
    )
    return SceneCriticRepairReport(
        scene_id=scene_id,
        response=CriticResponse(
            status=CriticStatus.REPAIR,
            issues=(issue,),
            patches=(patch,),
        ),
    )


def test_deterministic_warning_does_not_block_publication():
    *_, context = fixture()
    report = DeterministicQAReport(
        scene_id=context.scene_ids[0],
        passed=True,
        issues=(
            QAIssue(
                issue_id="MIN_FONT_SIZE:warning",
                code=QAIssueCode.MIN_FONT_SIZE,
                severity=QAIssueSeverity.WARNING,
                message="borderline readable",
                object_ids=("n1",),
                evidence={},
            ),
        ),
    )
    plan = route(
        AgentAwareQAReport(report_id="r", deterministic_reports=(report,)),
        context,
    )
    assert plan.intents == ()
    assert not plan.publication_blocked


def test_supported_scene_critic_patch_stays_in_core():
    *_, visual, context = fixture()
    repair = _scene_repair(
        context.scene_ids[0], visual.scenegraphs[0].nodes[0].id, semantic=False
    )
    plan = route(AgentAwareQAReport(report_id="r", scene_critic_repairs=(repair,)), context)
    assert plan.intents[0].owner == RepairOwner.CORE_REPAIR
    assert plan.intents[0].action == RepairActionKind.CORE_SELECTIVE_REPAIR
    assert plan.intents[0].core_patch_ids == ("p",)


def test_semantic_scene_regeneration_routes_to_visual_director():
    *_, visual, context = fixture()
    repair = _scene_repair(
        context.scene_ids[0], visual.scenegraphs[0].nodes[0].id, semantic=True
    )
    plan = route(AgentAwareQAReport(report_id="r", scene_critic_repairs=(repair,)), context)
    assert plan.intents[0].owner == RepairOwner.VISUAL_DIRECTOR
    assert plan.intents[0].core_patch_ids == ()


def _video_response(scene_ids, issue_type, op, dimension):
    if isinstance(scene_ids, str):
        scene_ids = (scene_ids,)
    return VideoCriticResponse(
        status=VideoCriticStatus.REVIEW_REQUIRED,
        dimension_assessments=tuple(
            VideoDimensionAssessment(
                dimension=item,
                passed=item != dimension,
                summary="repair" if item == dimension else "pass",
            )
            for item in VideoCriticDimension
        ),
        issues=(
            VideoCriticIssue(
                issue_id="vi",
                issue_type=issue_type,
                severity=VideoIssueSeverity.MEDIUM,
                scene_ids=scene_ids,
                reason="video issue",
            ),
        ),
        recommendations=(
            VideoCriticRecommendation(
                recommendation_id="vr",
                op=op,
                scene_ids=scene_ids,
                rationale="repair recommendation",
            ),
        ),
    )


def test_video_pacing_routes_to_deterministic_core():
    *_, context = fixture()
    response = _video_response(
        context.scene_ids[0],
        VideoIssueType.PACING,
        VideoRecommendationOp.ADJUST_PACING,
        VideoCriticDimension.PACING,
    )
    plan = route(AgentAwareQAReport(report_id="r", video_critic_response=response), context)
    assert plan.intents[0].owner == RepairOwner.CORE_REPAIR
    assert plan.intents[0].action == RepairActionKind.CORE_TEMPORAL_REPAIR


def test_video_transition_continuity_routes_to_deterministic_core():
    *_, context = fixture()
    scene_ids = context.scene_ids[:2]
    issue = VideoCriticIssue(
        issue_id="continuity",
        issue_type=VideoIssueType.TRANSITION_CONTINUITY,
        severity=VideoIssueSeverity.HIGH,
        scene_ids=scene_ids,
        transition_ids=("transition:test",),
        reason="continuity breaks",
    )
    response = VideoCriticResponse(
        status=VideoCriticStatus.REVIEW_REQUIRED,
        dimension_assessments=tuple(
            VideoDimensionAssessment(
                dimension=item,
                passed=item != VideoCriticDimension.CONTINUITY,
                summary="repair" if item == VideoCriticDimension.CONTINUITY else "pass",
            )
            for item in VideoCriticDimension
        ),
        issues=(issue,),
        recommendations=(
            VideoCriticRecommendation(
                recommendation_id="fix",
                op=VideoRecommendationOp.FIX_CONTINUITY,
                scene_ids=scene_ids,
                rationale="preserve continuity",
            ),
        ),
    )
    plan = route(AgentAwareQAReport(report_id="r", video_critic_response=response), context)
    assert plan.intents[0].owner == RepairOwner.CORE_REPAIR
    assert plan.intents[0].action == RepairActionKind.CORE_TEMPORAL_REPAIR


def test_video_narration_redundancy_routes_to_script():
    *_, context = fixture()
    response = _video_response(
        context.scene_ids[0],
        VideoIssueType.NARRATION_REDUNDANCY,
        VideoRecommendationOp.REDUCE_NARRATION_REDUNDANCY,
        VideoCriticDimension.PEDAGOGICAL_ALIGNMENT,
    )
    plan = route(AgentAwareQAReport(report_id="r", video_critic_response=response), context)
    assert plan.intents[0].owner == RepairOwner.SCRIPT_AGENT


def test_video_concept_progression_routes_to_pedagogy():
    *_, context = fixture()
    response = _video_response(
        context.scene_ids[0],
        VideoIssueType.CONCEPT_PROGRESSION,
        VideoRecommendationOp.IMPROVE_CONCEPT_PROGRESSION,
        VideoCriticDimension.PEDAGOGICAL_ALIGNMENT,
    )
    plan = route(AgentAwareQAReport(report_id="r", video_critic_response=response), context)
    assert plan.intents[0].owner == RepairOwner.PEDAGOGY_AGENT


def test_video_visual_modality_routes_to_visual_director():
    *_, context = fixture()
    response = _video_response(
        context.scene_ids[:2],
        VideoIssueType.VISUAL_MODALITY_DIVERSITY,
        VideoRecommendationOp.VARY_VISUAL_MODALITY,
        VideoCriticDimension.VISUAL_VARIETY,
    )
    plan = route(AgentAwareQAReport(report_id="r", video_critic_response=response), context)
    assert plan.intents[0].owner == RepairOwner.VISUAL_DIRECTOR


def test_unknown_references_fail_closed():
    *_, context = fixture()
    finding = SemanticQAFinding(
        finding_id="f",
        kind=SemanticFindingKind.EVIDENCE_UNSUPPORTED,
        reason="bad",
        claim_ids=("unknown-claim",),
    )
    with pytest.raises(AgentContractError, match="unknown claim_ids"):
        route(AgentAwareQAReport(report_id="r", semantic_findings=(finding,)), context)


def test_core_repair_cannot_become_hermes_task():
    brief, pack, graph, fact_report, pedagogy, script, visual, context = fixture()
    deterministic = DeterministicQAReport(
        scene_id=context.scene_ids[0],
        passed=False,
        issues=(
            QAIssue(
                issue_id="FRAME_OVERFLOW:x",
                code=QAIssueCode.FRAME_OVERFLOW,
                severity=QAIssueSeverity.ERROR,
                message="overflow",
                object_ids=(),
                evidence={},
            ),
        ),
    )
    intent = route(
        AgentAwareQAReport(report_id="r", deterministic_reports=(deterministic,)),
        context,
    ).intents[0]
    with pytest.raises(AgentContractError, match="stay deterministic"):
        build_agent_repair_task(
            intent,
            brief=brief,
            pack=pack,
            graph=graph,
            fact_report=fact_report,
            pedagogy=pedagogy,
            script=script,
            visual=visual,
        )


def test_agent_repair_tasks_reuse_existing_boundaries():
    brief, pack, graph, fact_report, pedagogy, script, visual, context = fixture()
    findings = (
        SemanticQAFinding(
            finding_id="research",
            kind=SemanticFindingKind.EVIDENCE_UNSUPPORTED,
            reason="unsupported",
            claim_ids=(context.claim_ids[0],),
        ),
        SemanticQAFinding(
            finding_id="script",
            kind=SemanticFindingKind.NARRATION_FACT_MISMATCH,
            reason="misstated",
            claim_ids=(context.claim_ids[0],),
            segment_ids=(context.segment_ids[0],),
        ),
        SemanticQAFinding(
            finding_id="visual",
            kind=SemanticFindingKind.SEMANTIC_VISUAL_MISMATCH,
            reason="wrong visual",
            scene_ids=(context.scene_ids[0],),
        ),
    )
    plan = route(AgentAwareQAReport(report_id="r", semantic_findings=findings), context)
    for intent in plan.intents:
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
        payload = json.loads(task["context"])
        assert payload["agent_aware_qa_repair_intent"]["owner"] == intent.owner.value
        assert task["output_schema"]["type"] == "object"


def test_empty_report_allows_publication():
    *_, context = fixture()
    plan = route(AgentAwareQAReport(report_id="r"), context)
    assert plan.intents == ()
    assert not plan.publication_blocked


def test_routing_plan_is_deterministic():
    *_, context = fixture()
    finding = SemanticQAFinding(
        finding_id="f",
        kind=SemanticFindingKind.SEMANTIC_VISUAL_MISMATCH,
        reason="visual",
        scene_ids=(context.scene_ids[0],),
    )
    report = AgentAwareQAReport(report_id="r", semantic_findings=(finding,))
    assert route(report, context).plan_id == route(report, context).plan_id


def test_agent_aware_qa_does_not_implement_later_stages():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "agent_aware_qa").glob("*.py")
    ).lower()
    for forbidden in (
        "pre_tool_call",
        "post_tool_call",
        "budgetledger(",
        "kanban",
        "skills/",
    ):
        assert forbidden not in source
