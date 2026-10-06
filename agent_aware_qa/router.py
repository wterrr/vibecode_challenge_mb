"""Deterministic ownership router for Agent-Aware QA."""

from __future__ import annotations

import hashlib
import json

from agent_contracts import (
    AgentContractError,
    LessonScript,
    PedagogyPlan,
    ResearchPack,
)
from learnflow_v2.qa import (
    CriticGateState,
    CriticTargetKind,
    QAIssueSeverity,
)
from learnflow_v2.repair import (
    RepairChangeKind,
    RepairLevel,
    build_repair_plan,
)
from learnflow_v2.videoqa import (
    VideoCriticGateState,
    VideoCriticStatus,
    VideoRecommendationOp,
)
from visual_director import VisualDirectorOutput

from .models import (
    AgentAwareQAReport,
    AgentAwareRoutingPlan,
    QABlocker,
    QABlockerKind,
    QARoutingContext,
    RepairActionKind,
    RepairIntent,
    RepairOwner,
    RepairSourceKind,
    SceneObjectScope,
    SemanticFindingKind,
    SemanticQAFinding,
)


_SEMANTIC_ROUTE = {
    SemanticFindingKind.EVIDENCE_UNSUPPORTED: (
        RepairOwner.RESEARCH_ORCHESTRATION,
        RepairActionKind.RESEARCH_EVIDENCE_REPAIR,
    ),
    SemanticFindingKind.EVIDENCE_CONTRADICTED: (
        RepairOwner.RESEARCH_ORCHESTRATION,
        RepairActionKind.RESEARCH_EVIDENCE_REPAIR,
    ),
    SemanticFindingKind.EVIDENCE_UNCERTAIN: (
        RepairOwner.RESEARCH_ORCHESTRATION,
        RepairActionKind.RESEARCH_EVIDENCE_REPAIR,
    ),
    SemanticFindingKind.NARRATION_FACT_MISMATCH: (
        RepairOwner.SCRIPT_AGENT,
        RepairActionKind.SCRIPT_FACT_REWRITE,
    ),
    SemanticFindingKind.SEMANTIC_VISUAL_MISMATCH: (
        RepairOwner.VISUAL_DIRECTOR,
        RepairActionKind.VISUAL_SEMANTIC_REGENERATION,
    ),
    SemanticFindingKind.PEDAGOGICAL_STRUCTURE: (
        RepairOwner.PEDAGOGY_AGENT,
        RepairActionKind.PEDAGOGY_REPLAN,
    ),
}

_VIDEO_ROUTE = {
    VideoRecommendationOp.VARY_VISUAL_MODALITY: (
        RepairOwner.VISUAL_DIRECTOR,
        RepairActionKind.VISUAL_SEMANTIC_REGENERATION,
    ),
    VideoRecommendationOp.CHANGE_VISUAL_MODALITY: (
        RepairOwner.VISUAL_DIRECTOR,
        RepairActionKind.VISUAL_SEMANTIC_REGENERATION,
    ),
    VideoRecommendationOp.ALIGN_STYLE: (
        RepairOwner.VISUAL_DIRECTOR,
        RepairActionKind.VISUAL_SEMANTIC_REGENERATION,
    ),
    VideoRecommendationOp.FIX_CONTINUITY: (
        RepairOwner.CORE_REPAIR,
        RepairActionKind.CORE_TEMPORAL_REPAIR,
    ),
    VideoRecommendationOp.ADJUST_PACING: (
        RepairOwner.CORE_REPAIR,
        RepairActionKind.CORE_TEMPORAL_REPAIR,
    ),
    VideoRecommendationOp.REDUCE_NARRATION_REDUNDANCY: (
        RepairOwner.SCRIPT_AGENT,
        RepairActionKind.SCRIPT_PACING_REWRITE,
    ),
    VideoRecommendationOp.IMPROVE_CONCEPT_PROGRESSION: (
        RepairOwner.PEDAGOGY_AGENT,
        RepairActionKind.PEDAGOGY_REPLAN,
    ),
    VideoRecommendationOp.IMPROVE_PEDAGOGICAL_ALIGNMENT: (
        RepairOwner.PEDAGOGY_AGENT,
        RepairActionKind.PEDAGOGY_REPLAN,
    ),
}

_SCENE_CRITIC_FAILURES = {
    CriticGateState.UNAVAILABLE,
    CriticGateState.TIMEOUT,
    CriticGateState.QUOTA_EXCEEDED,
    CriticGateState.PROVIDER_ERROR,
    CriticGateState.INVALID_RESPONSE,
}

_VIDEO_CRITIC_FAILURES = {
    VideoCriticGateState.UNAVAILABLE,
    VideoCriticGateState.TIMEOUT,
    VideoCriticGateState.QUOTA_EXCEEDED,
    VideoCriticGateState.PROVIDER_ERROR,
    VideoCriticGateState.INVALID_RESPONSE,
}


def build_routing_context(
    *,
    pack: ResearchPack,
    pedagogy: PedagogyPlan,
    script: LessonScript,
    visual: VisualDirectorOutput,
) -> QARoutingContext:
    graphs = {graph.scene_id: graph for graph in visual.scenegraphs}
    scene_ids = tuple(scene.scene_id for scene in visual.storyboard.scenes)
    if set(graphs) != set(scene_ids):
        raise AgentContractError(
            "Agent-Aware QA requires exact Storyboard/SceneGraph scene coverage"
        )
    scopes = tuple(
        SceneObjectScope(
            scene_id=scene_id,
            node_ids=tuple(node.id for node in graphs[scene_id].nodes),
            relation_ids=tuple(relation.id for relation in graphs[scene_id].relations),
            group_ids=tuple(group.id for group in graphs[scene_id].groups),
        )
        for scene_id in scene_ids
    )
    return QARoutingContext(
        scene_ids=scene_ids,
        claim_ids=tuple(claim.claim_id for claim in pack.claims),
        segment_ids=tuple(segment.segment_id for segment in script.segments),
        objective_ids=tuple(
            objective.objective_id for objective in pedagogy.learning_objectives
        ),
        scene_objects=scopes,
    )


def _require_known(values: tuple[str, ...], known: tuple[str, ...], label: str) -> None:
    unknown = sorted(set(values) - set(known))
    if unknown:
        raise AgentContractError(f"Agent-Aware QA references unknown {label}: {unknown!r}")


def _validate_semantic_finding(
    finding: SemanticQAFinding,
    context: QARoutingContext,
) -> None:
    _require_known(finding.scene_ids, context.scene_ids, "scene_ids")
    _require_known(finding.claim_ids, context.claim_ids, "claim_ids")
    _require_known(finding.segment_ids, context.segment_ids, "segment_ids")
    _require_known(finding.objective_ids, context.objective_ids, "objective_ids")


def _scene_scope(context: QARoutingContext, scene_id: str) -> SceneObjectScope:
    for scope in context.scene_objects:
        if scope.scene_id == scene_id:
            return scope
    raise AgentContractError(
        f"Agent-Aware QA has no object scope for scene {scene_id!r}"
    )


def _validate_critic_targets(scene_id: str, response, context: QARoutingContext) -> None:
    scope = _scene_scope(context, scene_id)
    allowed = {
        CriticTargetKind.NODE: set(scope.node_ids),
        CriticTargetKind.RELATION: set(scope.relation_ids),
        CriticTargetKind.GROUP: set(scope.group_ids),
    }
    targets = [
        target
        for issue in response.issues
        for target in issue.targets
    ] + [
        target
        for patch in response.patches
        for target in patch.targets
    ]
    for target in targets:
        if target.kind == CriticTargetKind.SCENE:
            continue
        if target.target_id not in allowed[target.kind]:
            raise AgentContractError(
                "Agent-Aware QA critic response references unknown "
                f"{target.kind.value} {target.target_id!r} in scene {scene_id!r}"
            )


def _intent_id(source_kind: RepairSourceKind, scope: str, source_id: str) -> str:
    return f"qa-route:{source_kind.value.lower()}:{scope}:{source_id}"


def _semantic_intent(finding: SemanticQAFinding) -> RepairIntent:
    owner, action = _SEMANTIC_ROUTE[finding.kind]
    return RepairIntent(
        intent_id=_intent_id(
            RepairSourceKind.SEMANTIC_FINDING, "semantic", finding.finding_id
        ),
        source_kind=RepairSourceKind.SEMANTIC_FINDING,
        source_id=finding.finding_id,
        owner=owner,
        action=action,
        reason=finding.reason,
        scene_ids=finding.scene_ids,
        claim_ids=finding.claim_ids,
        segment_ids=finding.segment_ids,
        objective_ids=finding.objective_ids,
    )


def _matching_critic_reason(response, patch) -> str:
    patch_targets = {(target.kind, target.target_id) for target in patch.targets}
    reasons: list[str] = []
    for issue in response.issues:
        issue_targets = {(target.kind, target.target_id) for target in issue.targets}
        scene_scope = any(
            kind == CriticTargetKind.SCENE for kind, _ in patch_targets
        )
        if scene_scope or not patch_targets.isdisjoint(issue_targets):
            reasons.append(issue.reason)
    if reasons:
        return " | ".join(sorted(set(reasons)))
    return f"Scene critic requested {patch.op.value}"


def _stable_plan_id(report: AgentAwareQAReport, context: QARoutingContext) -> str:
    payload = {
        "report": report.model_dump(mode="json", exclude_none=True),
        "context": context.model_dump(mode="json", exclude_none=True),
    }
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "qa-routing:" + hashlib.sha256(raw).hexdigest()[:16]


def _failure_reason(warnings: tuple[str, ...], fallback: str) -> str:
    return " | ".join(warnings) if warnings else fallback


def route_agent_aware_qa(
    report: AgentAwareQAReport,
    *,
    context: QARoutingContext,
) -> AgentAwareRoutingPlan:
    """Route validated QA failures to the layer that is allowed to repair them."""

    report = AgentAwareQAReport.model_validate(report.model_dump(mode="json"))
    context = QARoutingContext.model_validate(context.model_dump(mode="json"))
    intents: list[RepairIntent] = []
    blockers: list[QABlocker] = []

    for finding in report.semantic_findings:
        _validate_semantic_finding(finding, context)
        intents.append(_semantic_intent(finding))

    for quality in report.scene_quality_results:
        _require_known((quality.scene_id,), context.scene_ids, "scene_ids")

        error_count_before = len(intents)
        for issue in quality.deterministic_report.issues:
            if issue.severity != QAIssueSeverity.ERROR:
                continue
            intents.append(
                RepairIntent(
                    intent_id=_intent_id(
                        RepairSourceKind.DETERMINISTIC_QA,
                        quality.scene_id,
                        issue.issue_id,
                    ),
                    source_kind=RepairSourceKind.DETERMINISTIC_QA,
                    source_id=issue.issue_id,
                    owner=RepairOwner.CORE_REPAIR,
                    action=RepairActionKind.CORE_DETERMINISTIC_REPAIR,
                    reason=issue.message,
                    scene_ids=(quality.scene_id,),
                    object_ids=issue.object_ids,
                )
            )

        if not quality.deterministic_report.passed:
            if len(intents) == error_count_before:
                blockers.append(
                    QABlocker(
                        blocker_id=f"qa-blocker:scene:{quality.scene_id}:deterministic",
                        kind=QABlockerKind.SCENE_QUALITY_GATE,
                        state="DETERMINISTIC_FAIL",
                        reason="Deterministic QA failed without a routable ERROR issue.",
                        scene_ids=(quality.scene_id,),
                    )
                )
            continue

        if quality.critic_state == CriticGateState.REPAIR_REQUIRED:
            assert quality.critic_response is not None
            _validate_critic_targets(
                quality.scene_id, quality.critic_response, context
            )
            repair_plan = build_repair_plan(
                quality.scene_id, quality.critic_response
            )
            for action in repair_plan.actions:
                semantic_regeneration = (
                    action.change_kind == RepairChangeKind.SCENEGRAPH_STRUCTURE
                    or action.level >= RepairLevel.SCENE_REGENERATION_REQUEST
                )
                if semantic_regeneration:
                    owner = RepairOwner.VISUAL_DIRECTOR
                    route_action = RepairActionKind.VISUAL_SEMANTIC_REGENERATION
                    core_patch_ids: tuple[str, ...] = ()
                else:
                    owner = RepairOwner.CORE_REPAIR
                    route_action = RepairActionKind.CORE_SELECTIVE_REPAIR
                    core_patch_ids = (action.patch_id,)
                intents.append(
                    RepairIntent(
                        intent_id=_intent_id(
                            RepairSourceKind.SCENE_CRITIC,
                            quality.scene_id,
                            action.patch_id,
                        ),
                        source_kind=RepairSourceKind.SCENE_CRITIC,
                        source_id=action.patch_id,
                        owner=owner,
                        action=route_action,
                        reason=_matching_critic_reason(
                            quality.critic_response, action.patch
                        ),
                        scene_ids=(quality.scene_id,),
                        object_ids=action.target_ids,
                        core_patch_ids=core_patch_ids,
                    )
                )
        elif (
            not quality.approved
            and quality.critic_state in _SCENE_CRITIC_FAILURES
        ):
            blockers.append(
                QABlocker(
                    blocker_id=(
                        f"qa-blocker:scene:{quality.scene_id}:"
                        f"{quality.critic_state.value.lower()}"
                    ),
                    kind=QABlockerKind.SCENE_QUALITY_GATE,
                    state=quality.critic_state.value,
                    reason=_failure_reason(
                        quality.warnings,
                        "Strict scene critic failure blocks publication.",
                    ),
                    scene_ids=(quality.scene_id,),
                )
            )

    video_result = report.video_critic_result
    if video_result is not None:
        request_scene_ids = tuple(scene.scene_id for scene in video_result.request.scenes)
        if set(request_scene_ids) != set(context.scene_ids):
            raise AgentContractError(
                "Agent-Aware QA VideoCriticResult scene scope does not match current lesson"
            )
        if set(video_result.request.lesson_objective_ids) != set(context.objective_ids):
            raise AgentContractError(
                "Agent-Aware QA VideoCriticResult objective scope does not match current lesson"
            )

        if video_result.state == VideoCriticGateState.REVIEW_REQUIRED:
            assert video_result.response is not None
            response = video_result.response
            if response.status != VideoCriticStatus.REVIEW_REQUIRED:
                raise AgentContractError(
                    "video critic REVIEW_REQUIRED state must carry review response"
                )
            issue_reasons = {
                scene_id: []
                for issue in response.issues
                for scene_id in issue.scene_ids
            }
            for issue in response.issues:
                _require_known(issue.scene_ids, context.scene_ids, "scene_ids")
                for scene_id in issue.scene_ids:
                    issue_reasons.setdefault(scene_id, []).append(issue.reason)
            for recommendation in response.recommendations:
                _require_known(
                    recommendation.scene_ids, context.scene_ids, "scene_ids"
                )
                owner, route_action = _VIDEO_ROUTE[recommendation.op]
                reasons = [
                    reason
                    for scene_id in recommendation.scene_ids
                    for reason in issue_reasons.get(scene_id, ())
                ]
                reason = recommendation.rationale
                if reasons:
                    reason = reason + " | " + " | ".join(sorted(set(reasons)))
                intents.append(
                    RepairIntent(
                        intent_id=_intent_id(
                            RepairSourceKind.VIDEO_CRITIC,
                            "video",
                            recommendation.recommendation_id,
                        ),
                        source_kind=RepairSourceKind.VIDEO_CRITIC,
                        source_id=recommendation.recommendation_id,
                        owner=owner,
                        action=route_action,
                        reason=reason,
                        scene_ids=recommendation.scene_ids,
                    )
                )
        elif (
            not video_result.approved
            and video_result.state in _VIDEO_CRITIC_FAILURES
        ):
            blockers.append(
                QABlocker(
                    blocker_id=(
                        "qa-blocker:video:"
                        f"{video_result.state.value.lower()}"
                    ),
                    kind=QABlockerKind.VIDEO_QUALITY_GATE,
                    state=video_result.state.value,
                    reason=_failure_reason(
                        video_result.warnings,
                        "Strict video critic failure blocks publication.",
                    ),
                    scene_ids=context.scene_ids,
                )
            )

    return AgentAwareRoutingPlan(
        plan_id=_stable_plan_id(report, context),
        report_id=report.report_id,
        intents=tuple(intents),
        blockers=tuple(blockers),
        publication_blocked=bool(intents or blockers),
    )
