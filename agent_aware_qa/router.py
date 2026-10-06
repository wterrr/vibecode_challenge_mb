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
from learnflow_v2.qa import CriticTargetKind
from learnflow_v2.repair import (
    RepairChangeKind,
    RepairLevel,
    build_repair_plan,
)
from learnflow_v2.videoqa import (
    VideoCriticStatus,
    VideoRecommendationOp,
)
from visual_director import VisualDirectorOutput

from .models import (
    AgentAwareQAReport,
    AgentAwareRoutingPlan,
    QARoutingContext,
    RepairActionKind,
    RepairIntent,
    RepairOwner,
    RepairSourceKind,
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
        RepairOwner.VISUAL_DIRECTOR,
        RepairActionKind.VISUAL_SEMANTIC_REGENERATION,
    ),
    VideoRecommendationOp.ADJUST_PACING: (
        RepairOwner.SCRIPT_AGENT,
        RepairActionKind.SCRIPT_PACING_REWRITE,
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


def build_routing_context(
    *,
    pack: ResearchPack,
    pedagogy: PedagogyPlan,
    script: LessonScript,
    visual: VisualDirectorOutput,
) -> QARoutingContext:
    return QARoutingContext(
        scene_ids=tuple(scene.scene_id for scene in visual.storyboard.scenes),
        claim_ids=tuple(claim.claim_id for claim in pack.claims),
        segment_ids=tuple(segment.segment_id for segment in script.segments),
        objective_ids=tuple(
            objective.objective_id for objective in pedagogy.learning_objectives
        ),
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


def _intent_id(source_kind: RepairSourceKind, scope: str, source_id: str) -> str:
    return f"qa-route:{source_kind.value.lower()}:{scope}:{source_id}"


def _semantic_intent(
    finding: SemanticQAFinding,
) -> RepairIntent:
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
        scene_scope = any(kind == CriticTargetKind.SCENE for kind, _ in patch_targets)
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


def route_agent_aware_qa(
    report: AgentAwareQAReport,
    *,
    context: QARoutingContext,
) -> AgentAwareRoutingPlan:
    """Route QA failures to the layer that is allowed to repair them."""

    report = AgentAwareQAReport.model_validate(report.model_dump(mode="json"))
    context = QARoutingContext.model_validate(context.model_dump(mode="json"))
    intents: list[RepairIntent] = []

    for finding in report.semantic_findings:
        _validate_semantic_finding(finding, context)
        intents.append(_semantic_intent(finding))

    for deterministic in report.deterministic_reports:
        _require_known((deterministic.scene_id,), context.scene_ids, "scene_ids")
        for issue in deterministic.issues:
            intents.append(
                RepairIntent(
                    intent_id=_intent_id(
                        RepairSourceKind.DETERMINISTIC_QA,
                        deterministic.scene_id,
                        issue.issue_id,
                    ),
                    source_kind=RepairSourceKind.DETERMINISTIC_QA,
                    source_id=issue.issue_id,
                    owner=RepairOwner.CORE_REPAIR,
                    action=RepairActionKind.CORE_DETERMINISTIC_REPAIR,
                    reason=issue.message,
                    scene_ids=(deterministic.scene_id,),
                    object_ids=issue.object_ids,
                )
            )

    for scene_report in report.scene_critic_repairs:
        _require_known((scene_report.scene_id,), context.scene_ids, "scene_ids")
        repair_plan = build_repair_plan(scene_report.scene_id, scene_report.response)
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
                        scene_report.scene_id,
                        action.patch_id,
                    ),
                    source_kind=RepairSourceKind.SCENE_CRITIC,
                    source_id=action.patch_id,
                    owner=owner,
                    action=route_action,
                    reason=_matching_critic_reason(
                        scene_report.response, action.patch
                    ),
                    scene_ids=(scene_report.scene_id,),
                    object_ids=action.target_ids,
                    core_patch_ids=core_patch_ids,
                )
            )

    video_response = report.video_critic_response
    if video_response is not None:
        if video_response.status == VideoCriticStatus.REVIEW_REQUIRED:
            issue_reasons = {
                scene_id: []
                for issue in video_response.issues
                for scene_id in issue.scene_ids
            }
            for issue in video_response.issues:
                for scene_id in issue.scene_ids:
                    issue_reasons.setdefault(scene_id, []).append(issue.reason)
            for recommendation in video_response.recommendations:
                _require_known(recommendation.scene_ids, context.scene_ids, "scene_ids")
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

    return AgentAwareRoutingPlan(
        plan_id=_stable_plan_id(report, context),
        report_id=report.report_id,
        intents=tuple(intents),
        publication_blocked=bool(intents),
    )
