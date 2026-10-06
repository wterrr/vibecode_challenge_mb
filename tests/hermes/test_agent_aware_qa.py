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
    RepairActionKind,
    RepairOwner,
    SemanticFindingKind,
    SemanticQAFinding,
    build_agent_repair_task,
    build_routing_context,
    route_agent_aware_qa,
)
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
    QualityGateResult,
    QualityMode,
)
from learnflow_v2.scenegraph import PreferredRegion
from learnflow_v2.videoqa import (
    VideoCriticDimension,
    VideoCriticFailurePolicy,
    VideoCriticGateState,
    VideoCriticIssue,
    VideoCriticRecommendation,
    VideoCriticResponse,
    VideoCriticResult,
    VideoCriticStatus,
    VideoDimensionAssessment,
    VideoIssueSeverity,
    VideoIssueType,
    VideoRecommendationOp,
    compute_video_critic_request_hash,
)
from scripts.verify_agent_aware_qa import build_video_request
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


def pass_report(scene_id):
    return DeterministicQAReport(scene_id=scene_id, passed=True, issues=())


def deterministic_gate(report):
    return QualityGateResult(
        scene_id=report.scene_id,
        quality_mode=QualityMode.CRITIC,
        failure_policy=CriticFailurePolicy.STRICT,
        deterministic_report=report,
        critic_state=CriticGateState.SKIPPED_DETERMINISTIC_FAIL,
        critic_response=None,
        approved=False,
        warnings=(),
    )


def critic_repair_gate(scene_id, response):
    return QualityGateResult(
        scene_id=scene_id,
        quality_mode=QualityMode.CRITIC,
        failure_policy=CriticFailurePolicy.STRICT,
        deterministic_report=pass_report(scene_id),
        critic_state=CriticGateState.REPAIR_REQUIRED,
        critic_response=response,
        approved=False,
        warnings=(),
    )


def video_result(context, issue_type, op, dimension, *, scene_ids=None):
    request = build_video_request(context)
    selected = tuple(scene_ids or (request.scenes[0].scene_id,))
    response = VideoCriticResponse(
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
                issue_id="video-issue",
                issue_type=issue_type,
                severity=VideoIssueSeverity.MEDIUM,
                scene_ids=selected,
                transition_ids=(
                    ("transition:0",)
                    if issue_type == VideoIssueType.TRANSITION_CONTINUITY
                    else ()
                ),
                reason="video issue",
            ),
        ),
        recommendations=(
            VideoCriticRecommendation(
                recommendation_id="video-repair",
                op=op,
                scene_ids=selected,
                rationale="repair recommendation",
            ),
        ),
    )
    return VideoCriticResult(
        video_id=request.video_id,
        request=request,
        request_hash=compute_video_critic_request_hash(request),
        failure_policy=VideoCriticFailurePolicy.STRICT,
        state=VideoCriticGateState.REVIEW_REQUIRED,
        response=response,
        approved=False,
        warnings=(),
    )


def test_routing_context_preserves_storyboard_order():
    *_, visual, context = fixture()
    assert context.scene_ids == tuple(
        scene.scene_id for scene in visual.storyboard.scenes
    )


def test_factual_evidence_routes_to_research():
    *_, context = fixture()
    finding = SemanticQAFinding(
        finding_id="f",
        kind=SemanticFindingKind.EVIDENCE_CONTRADICTED,
        reason="Evidence contradicts claim.",
        claim_ids=(context.claim_ids[0],),
    )
    plan = route(
        AgentAwareQAReport(report_id="r", semantic_findings=(finding,)),
        context,
    )
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
    plan = route(
        AgentAwareQAReport(report_id="r", semantic_findings=(finding,)),
        context,
    )
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
    plan = route(
        AgentAwareQAReport(report_id="r", semantic_findings=(finding,)),
        context,
    )
    assert plan.intents[0].owner == RepairOwner.VISUAL_DIRECTOR


def test_pedagogical_structure_routes_to_pedagogy():
    *_, context = fixture()
    finding = SemanticQAFinding(
        finding_id="f",
        kind=SemanticFindingKind.PEDAGOGICAL_STRUCTURE,
        reason="Concept progression is confusing.",
        objective_ids=(context.objective_ids[0],),
    )
    plan = route(
        AgentAwareQAReport(report_id="r", semantic_findings=(finding,)),
        context,
    )
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
    plan = route(
        AgentAwareQAReport(
            report_id="r", scene_quality_results=(deterministic_gate(report),)
        ),
        context,
    )
    assert plan.intents[0].owner == RepairOwner.CORE_REPAIR
    assert plan.intents[0].action == RepairActionKind.CORE_DETERMINISTIC_REPAIR


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
    gate = QualityGateResult(
        scene_id=report.scene_id,
        quality_mode=QualityMode.DETERMINISTIC,
        failure_policy=CriticFailurePolicy.CONTINUE,
        deterministic_report=report,
        critic_state=CriticGateState.NOT_REQUESTED,
        critic_response=None,
        approved=True,
        warnings=(),
    )
    plan = route(
        AgentAwareQAReport(report_id="r", scene_quality_results=(gate,)),
        context,
    )
    assert plan.intents == ()
    assert plan.blockers == ()
    assert not plan.publication_blocked


def scene_repair(scene_id, node_id, *, semantic=False):
    issue = CriticIssue(
        issue_id="i",
        issue_type=(
            CriticIssueType.PEDAGOGICAL_ALIGNMENT
            if semantic
            else CriticIssueType.READABILITY
        ),
        severity=CriticIssueSeverity.MEDIUM,
        targets=(
            CriticTargetRef(kind=CriticTargetKind.NODE, target_id=node_id),
        ),
        reason="needs repair",
    )
    patch = (
        CriticPatchSuggestion(
            patch_id="p",
            op=CriticPatchOp.CHANGE_VISUAL_INTENT,
            targets=(
                CriticTargetRef(kind=CriticTargetKind.NODE, target_id=node_id),
            ),
            semantic_value="comparison",
        )
        if semantic
        else CriticPatchSuggestion(
            patch_id="p",
            op=CriticPatchOp.SET_REGION,
            targets=(
                CriticTargetRef(kind=CriticTargetKind.NODE, target_id=node_id),
            ),
            region=PreferredRegion.RIGHT,
        )
    )
    response = CriticResponse(
        status=CriticStatus.REPAIR,
        issues=(issue,),
        patches=(patch,),
    )
    return critic_repair_gate(scene_id, response)


def test_supported_scene_critic_patch_stays_in_core():
    *_, visual, context = fixture()
    scene_id = context.scene_ids[0]
    node_id = next(
        scope.node_ids[0]
        for scope in context.scene_objects
        if scope.scene_id == scene_id
    )
    gate = scene_repair(scene_id, node_id, semantic=False)
    plan = route(
        AgentAwareQAReport(report_id="r", scene_quality_results=(gate,)),
        context,
    )
    assert plan.intents[0].owner == RepairOwner.CORE_REPAIR
    assert plan.intents[0].action == RepairActionKind.CORE_SELECTIVE_REPAIR
    assert plan.intents[0].core_patch_ids == ("p",)


def test_semantic_scene_regeneration_routes_to_visual_director():
    *_, visual, context = fixture()
    scene_id = context.scene_ids[0]
    node_id = next(
        scope.node_ids[0]
        for scope in context.scene_objects
        if scope.scene_id == scene_id
    )
    gate = scene_repair(scene_id, node_id, semantic=True)
    plan = route(
        AgentAwareQAReport(report_id="r", scene_quality_results=(gate,)),
        context,
    )
    assert plan.intents[0].owner == RepairOwner.VISUAL_DIRECTOR
    assert plan.intents[0].core_patch_ids == ()


def test_scene_critic_unknown_node_fails_closed():
    *_, context = fixture()
    gate = scene_repair(context.scene_ids[0], "n404", semantic=False)
    with pytest.raises(AgentContractError, match="unknown NODE"):
        route(
            AgentAwareQAReport(report_id="r", scene_quality_results=(gate,)),
            context,
        )


def test_video_narration_redundancy_routes_to_script():
    *_, context = fixture()
    result = video_result(
        context,
        VideoIssueType.NARRATION_REDUNDANCY,
        VideoRecommendationOp.REDUCE_NARRATION_REDUNDANCY,
        VideoCriticDimension.PEDAGOGICAL_ALIGNMENT,
    )
    plan = route(
        AgentAwareQAReport(report_id="r", video_critic_result=result),
        context,
    )
    assert plan.intents[0].owner == RepairOwner.SCRIPT_AGENT


def test_video_concept_progression_routes_to_pedagogy():
    *_, context = fixture()
    result = video_result(
        context,
        VideoIssueType.CONCEPT_PROGRESSION,
        VideoRecommendationOp.IMPROVE_CONCEPT_PROGRESSION,
        VideoCriticDimension.PEDAGOGICAL_ALIGNMENT,
    )
    plan = route(
        AgentAwareQAReport(report_id="r", video_critic_result=result),
        context,
    )
    assert plan.intents[0].owner == RepairOwner.PEDAGOGY_AGENT


def test_video_visual_modality_routes_to_visual_director():
    *_, context = fixture()
    result = video_result(
        context,
        VideoIssueType.VISUAL_MODALITY_DIVERSITY,
        VideoRecommendationOp.VARY_VISUAL_MODALITY,
        VideoCriticDimension.VISUAL_VARIETY,
        scene_ids=context.scene_ids[:2],
    )
    plan = route(
        AgentAwareQAReport(report_id="r", video_critic_result=result),
        context,
    )
    assert plan.intents[0].owner == RepairOwner.VISUAL_DIRECTOR


def test_video_pacing_routes_to_deterministic_core():
    *_, context = fixture()
    result = video_result(
        context,
        VideoIssueType.PACING,
        VideoRecommendationOp.ADJUST_PACING,
        VideoCriticDimension.PACING,
    )
    plan = route(
        AgentAwareQAReport(report_id="r", video_critic_result=result),
        context,
    )
    assert plan.intents[0].owner == RepairOwner.CORE_REPAIR
    assert plan.intents[0].action == RepairActionKind.CORE_TEMPORAL_REPAIR


def test_video_transition_continuity_routes_to_deterministic_core():
    *_, context = fixture()
    result = video_result(
        context,
        VideoIssueType.TRANSITION_CONTINUITY,
        VideoRecommendationOp.FIX_CONTINUITY,
        VideoCriticDimension.CONTINUITY,
        scene_ids=context.scene_ids[:2],
    )
    plan = route(
        AgentAwareQAReport(report_id="r", video_critic_result=result),
        context,
    )
    assert plan.intents[0].owner == RepairOwner.CORE_REPAIR
    assert plan.intents[0].action == RepairActionKind.CORE_TEMPORAL_REPAIR


def test_video_result_scope_mismatch_fails_closed():
    *_, context = fixture()
    request = build_video_request(context)
    payload = request.model_dump(mode="json")
    payload["lesson_objective_ids"] = ["other-objective"]
    for scene in payload["scenes"]:
        scene["learning_objective_ids"] = ["other-objective"]
    from learnflow_v2.videoqa import VideoCriticRequest
    other_request = VideoCriticRequest.model_validate(payload)
    response = VideoCriticResponse(
        status=VideoCriticStatus.REVIEW_REQUIRED,
        dimension_assessments=tuple(
            VideoDimensionAssessment(
                dimension=item,
                passed=item != VideoCriticDimension.PACING,
                summary="repair" if item == VideoCriticDimension.PACING else "pass",
            )
            for item in VideoCriticDimension
        ),
        issues=(
            VideoCriticIssue(
                issue_id="i",
                issue_type=VideoIssueType.PACING,
                severity=VideoIssueSeverity.MEDIUM,
                scene_ids=(other_request.scenes[0].scene_id,),
                reason="pace",
            ),
        ),
        recommendations=(
            VideoCriticRecommendation(
                recommendation_id="r",
                op=VideoRecommendationOp.ADJUST_PACING,
                scene_ids=(other_request.scenes[0].scene_id,),
                rationale="pace",
            ),
        ),
    )
    result = VideoCriticResult(
        video_id=other_request.video_id,
        request=other_request,
        request_hash=compute_video_critic_request_hash(other_request),
        failure_policy=VideoCriticFailurePolicy.STRICT,
        state=VideoCriticGateState.REVIEW_REQUIRED,
        response=response,
        approved=False,
        warnings=(),
    )
    with pytest.raises(AgentContractError, match="objective scope"):
        route(
            AgentAwareQAReport(report_id="r", video_critic_result=result),
            context,
        )


def test_strict_scene_critic_outage_blocks_without_agent_repair():
    *_, context = fixture()
    scene_id = context.scene_ids[0]
    gate = QualityGateResult(
        scene_id=scene_id,
        quality_mode=QualityMode.CRITIC,
        failure_policy=CriticFailurePolicy.STRICT,
        deterministic_report=pass_report(scene_id),
        critic_state=CriticGateState.PROVIDER_ERROR,
        critic_response=None,
        approved=False,
        warnings=("critic provider failed",),
    )
    plan = route(
        AgentAwareQAReport(report_id="r", scene_quality_results=(gate,)),
        context,
    )
    assert plan.intents == ()
    assert len(plan.blockers) == 1
    assert plan.publication_blocked


def test_strict_video_critic_outage_blocks_without_agent_repair():
    *_, context = fixture()
    request = build_video_request(context)
    result = VideoCriticResult(
        video_id=request.video_id,
        request=request,
        request_hash=compute_video_critic_request_hash(request),
        failure_policy=VideoCriticFailurePolicy.STRICT,
        state=VideoCriticGateState.PROVIDER_ERROR,
        response=None,
        approved=False,
        warnings=("video critic provider failed",),
    )
    plan = route(
        AgentAwareQAReport(report_id="r", video_critic_result=result),
        context,
    )
    assert plan.intents == ()
    assert len(plan.blockers) == 1
    assert plan.publication_blocked


def test_continue_video_critic_outage_does_not_block():
    *_, context = fixture()
    request = build_video_request(context)
    result = VideoCriticResult(
        video_id=request.video_id,
        request=request,
        request_hash=compute_video_critic_request_hash(request),
        failure_policy=VideoCriticFailurePolicy.CONTINUE,
        state=VideoCriticGateState.PROVIDER_ERROR,
        response=None,
        approved=True,
        warnings=("video critic provider failed",),
    )
    plan = route(
        AgentAwareQAReport(report_id="r", video_critic_result=result),
        context,
    )
    assert plan.intents == ()
    assert plan.blockers == ()
    assert not plan.publication_blocked


def test_unknown_semantic_references_fail_closed():
    *_, context = fixture()
    finding = SemanticQAFinding(
        finding_id="f",
        kind=SemanticFindingKind.EVIDENCE_UNSUPPORTED,
        reason="bad",
        claim_ids=("unknown-claim",),
    )
    with pytest.raises(AgentContractError, match="unknown claim_ids"):
        route(
            AgentAwareQAReport(report_id="r", semantic_findings=(finding,)),
            context,
        )


def test_core_repair_cannot_become_hermes_task():
    brief, pack, graph, fact_report, pedagogy, script, visual, context = fixture()
    report = DeterministicQAReport(
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
        AgentAwareQAReport(
            report_id="r", scene_quality_results=(deterministic_gate(report),)
        ),
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


def test_agent_repair_tasks_include_current_artifact_for_selective_repair():
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
            finding_id="pedagogy",
            kind=SemanticFindingKind.PEDAGOGICAL_STRUCTURE,
            reason="weak progression",
            objective_ids=(context.objective_ids[0],),
        ),
        SemanticQAFinding(
            finding_id="visual",
            kind=SemanticFindingKind.SEMANTIC_VISUAL_MISMATCH,
            reason="wrong visual",
            scene_ids=(context.scene_ids[0],),
        ),
    )
    plan = route(
        AgentAwareQAReport(report_id="r", semantic_findings=findings),
        context,
    )
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
        if intent.owner == RepairOwner.RESEARCH_ORCHESTRATION:
            assert payload["current_research_pack"]["pack_id"] == pack.pack_id
        elif intent.owner == RepairOwner.SCRIPT_AGENT:
            assert payload["current_lesson_script"]["script_id"] == script.script_id
        elif intent.owner == RepairOwner.PEDAGOGY_AGENT:
            assert payload["current_pedagogy_plan"]["plan_id"] == pedagogy.plan_id
        elif intent.owner == RepairOwner.VISUAL_DIRECTOR:
            assert (
                payload["current_visual_director_output"]["storyboard"]["storyboard_id"]
                == visual.storyboard.storyboard_id
            )
        assert task["output_schema"]["type"] == "object"


def test_empty_report_allows_publication():
    *_, context = fixture()
    plan = route(AgentAwareQAReport(report_id="r"), context)
    assert plan.intents == ()
    assert plan.blockers == ()
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
