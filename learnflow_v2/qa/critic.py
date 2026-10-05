"""Optional VLM critic orchestration for LearnFlow V2 CP2.12.

This module never calls a concrete provider directly. A provider implements the
small CriticProvider protocol and receives a strict CriticRequest. The quality
gate always consumes deterministic QA first and therefore cannot use a critic to
override deterministic failures.
"""

from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any, Protocol

from pydantic import ValidationError

from learnflow_v2.layout.schema import LayoutGraph
from learnflow_v2.motion.enums import MotionTargetKind, MotionVerb
from learnflow_v2.motion.scheduler import MotionSchedule
from learnflow_v2.qa.critic_schema import (
    CriticFailurePolicy,
    CriticFrameInput,
    CriticFrameReason,
    CriticFrameSelection,
    CriticGateState,
    CriticLayoutBoxSummary,
    CriticMotionEventSummary,
    CriticOverlayElement,
    CriticOverlaySpec,
    CriticRequest,
    CriticResponse,
    CriticSceneNodeSummary,
    CriticSceneRelationSummary,
    CriticSceneGroupSummary,
    CriticStatus,
    CriticTargetKind,
    NormalizedRect,
    QualityGateResult,
    QualityMode,
)
from learnflow_v2.qa.errors import (
    CriticProviderError,
    CriticProviderQuotaError,
    CriticProviderUnavailableError,
    QAInvalidInputError,
)
from learnflow_v2.qa.schema import DeterministicQAReport
from learnflow_v2.scenegraph.schema import SceneGraph


class CriticProvider(Protocol):
    """Minimal provider boundary; adapters may wrap any VLM implementation."""

    def critique(self, request: CriticRequest) -> CriticResponse | Mapping[str, Any]: ...


def _anchor_cell(center_x: float, center_y: float, frame_width: float, frame_height: float) -> str:
    col = min(5, max(0, int((center_x / frame_width) * 6.0)))
    row = min(5, max(0, int((center_y / frame_height) * 6.0)))
    return f"{chr(ord('A') + row)}{col + 1:02d}"


def _normalized_rect(x: float, y: float, width: float, height: float, frame_width: float, frame_height: float) -> NormalizedRect:
    return NormalizedRect(
        left=x / frame_width,
        top=y / frame_height,
        right=(x + width) / frame_width,
        bottom=(y + height) / frame_height,
    )


def build_critic_overlay(layout_graph: LayoutGraph) -> CriticOverlaySpec:
    """Build deterministic ID + 6x6 anchor overlay metadata from solved geometry."""
    elements: list[CriticOverlayElement] = []
    for box in sorted(layout_graph.boxes, key=lambda item: item.node_id):
        elements.append(
            CriticOverlayElement(
                element_id=box.node_id,
                anchor_cell=_anchor_cell(
                    box.rect.center_x,
                    box.rect.center_y,
                    layout_graph.frame_width,
                    layout_graph.frame_height,
                ),
                semantic_region=box.zone,
                rect=_normalized_rect(
                    box.rect.x,
                    box.rect.y,
                    box.rect.width,
                    box.rect.height,
                    layout_graph.frame_width,
                    layout_graph.frame_height,
                ),
            )
        )
    return CriticOverlaySpec(elements=tuple(elements))


def select_event_aware_frames(
    schedule: MotionSchedule,
    *,
    before_exit_lead_seconds: float = 0.05,
    tolerance: float = 1e-6,
) -> tuple[CriticFrameSelection, ...]:
    """Select deterministic critic frames from motion events; never samples randomly."""
    if isinstance(before_exit_lead_seconds, bool) or not isinstance(before_exit_lead_seconds, (int, float)):
        raise QAInvalidInputError("before_exit_lead_seconds must be a non-negative finite number")
    lead = float(before_exit_lead_seconds)
    if lead < 0.0 or not math.isfinite(lead):
        raise QAInvalidInputError("before_exit_lead_seconds must be finite and >= 0")
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)):
        raise QAInvalidInputError("sampling tolerance must be a finite non-negative number")
    tolerance = float(tolerance)
    if not math.isfinite(tolerance) or tolerance < 0.0 or tolerance > 1e-3:
        raise QAInvalidInputError("sampling tolerance must be finite and within [0, 0.001]")

    candidates: list[tuple[float, str]] = [(0.0, CriticFrameReason.SCENE_START.value)]
    for event in schedule.scheduled_events:
        if event.verb == MotionVerb.ENTER:
            candidates.append((event.end_time, f"{CriticFrameReason.AFTER_ENTER.value}:{event.event_id}"))
        elif event.verb == MotionVerb.TRANSFORM:
            candidates.append((event.end_time, f"{CriticFrameReason.AFTER_TRANSFORM.value}:{event.event_id}"))
        elif event.verb == MotionVerb.EXIT:
            candidates.append((max(0.0, event.start_time - lead), f"{CriticFrameReason.BEFORE_EXIT.value}:{event.event_id}"))
    candidates.append((schedule.scene_duration, CriticFrameReason.SCENE_END.value))
    candidates.sort(key=lambda item: (item[0], item[1]))

    groups: list[tuple[float, list[str]]] = []
    for timestamp, reason in candidates:
        timestamp = min(max(timestamp, 0.0), schedule.scene_duration)
        if groups and abs(groups[-1][0] - timestamp) <= tolerance:
            groups[-1][1].append(reason)
        else:
            groups.append((timestamp, [reason]))

    return tuple(
        CriticFrameSelection(
            sample_id=f"sample_{index:03d}",
            timestamp=timestamp,
            reasons=tuple(sorted(set(reasons))),
        )
        for index, (timestamp, reasons) in enumerate(groups)
    )


def build_critic_request(
    *,
    narration: str,
    scene_graph: SceneGraph,
    layout_graph: LayoutGraph,
    motion_schedule: MotionSchedule,
    deterministic_report: DeterministicQAReport,
    frame_refs: Mapping[str, str],
) -> CriticRequest:
    """Build the strict structured context consumed by a critic provider."""
    scene_id = scene_graph.scene_id
    if layout_graph.scene_id != scene_id or motion_schedule.scene_id != scene_id or deterministic_report.scene_id != scene_id:
        raise QAInvalidInputError("scene, layout, motion schedule, and deterministic QA report must share scene_id")
    if not deterministic_report.passed:
        raise QAInvalidInputError("cannot build critic request until deterministic QA passes")
    if not isinstance(frame_refs, Mapping):
        raise QAInvalidInputError("frame_refs must map sample_id to opaque image reference")

    node_ids = {node.id for node in scene_graph.nodes}
    relation_ids = {relation.id for relation in scene_graph.relations}
    layout_ids = {box.node_id for box in layout_graph.boxes}
    if not layout_graph.feasible:
        raise QAInvalidInputError("cannot build critic request from an infeasible LayoutGraph")
    if layout_ids != node_ids:
        missing = sorted(node_ids - layout_ids)
        extra = sorted(layout_ids - node_ids)
        raise QAInvalidInputError(
            f"LayoutGraph must exactly cover SceneGraph nodes for critic context; missing={missing}, extra={extra}"
        )
    for event in motion_schedule.scheduled_events:
        if event.target_kind == MotionTargetKind.NODE and event.target not in node_ids:
            raise QAInvalidInputError(f"motion event '{event.event_id}' references unknown node '{event.target}'")
        if event.target_kind == MotionTargetKind.RELATION and event.target not in relation_ids:
            raise QAInvalidInputError(f"motion event '{event.event_id}' references unknown relation '{event.target}'")

    overlay = build_critic_overlay(layout_graph)
    selections = select_event_aware_frames(motion_schedule)
    selection_ids = {item.sample_id for item in selections}
    ref_ids = set(frame_refs.keys())
    if selection_ids != ref_ids:
        missing = sorted(selection_ids - ref_ids)
        extra = sorted(ref_ids - selection_ids)
        raise QAInvalidInputError(f"frame_refs must exactly cover event-aware selections; missing={missing}, extra={extra}")
    if any(not isinstance(ref, str) or not ref.strip() for ref in frame_refs.values()):
        raise QAInvalidInputError("frame_refs values must be non-empty opaque strings")

    overlay_by_id = {item.element_id: item for item in overlay.elements}
    frames = tuple(
        CriticFrameInput(
            selection=selection,
            image_ref=frame_refs[selection.sample_id].strip(),
            overlay=overlay,
        )
        for selection in selections
    )
    nodes = tuple(
        CriticSceneNodeSummary(
            node_id=node.id,
            kind=node.kind,
            label=node.label,
            semantic_key=node.semantic_key,
            semantic_role=node.semantic_role,
        )
        for node in scene_graph.nodes
    )
    relations = tuple(
        CriticSceneRelationSummary(
            relation_id=relation.id,
            source=relation.source,
            target=relation.target,
            kind=relation.kind,
            label=relation.label,
        )
        for relation in scene_graph.relations
    )
    groups = tuple(
        CriticSceneGroupSummary(
            group_id=group.id,
            member_ids=tuple(group.member_ids),
            label=group.label,
            semantic_role=group.semantic_role,
        )
        for group in scene_graph.groups
    )
    boxes = tuple(
        CriticLayoutBoxSummary(
            node_id=box.node_id,
            semantic_region=overlay_by_id[box.node_id].semantic_region,
            anchor_cell=overlay_by_id[box.node_id].anchor_cell,
            rect=overlay_by_id[box.node_id].rect,
        )
        for box in layout_graph.boxes
    )
    motion_events = tuple(
        CriticMotionEventSummary(
            event_id=event.event_id,
            target=event.target,
            target_kind=event.target_kind,
            verb=event.verb,
            style=event.style,
            start_time=event.start_time,
            end_time=event.end_time,
            trigger_beat=event.trigger_beat,
        )
        for event in motion_schedule.scheduled_events
    )
    return CriticRequest(
        scene_id=scene_id,
        narration=narration,
        scene_duration=motion_schedule.scene_duration,
        before_exit_lead_seconds=0.05,
        nodes=nodes,
        relations=relations,
        groups=groups,
        layout_boxes=boxes,
        motion_events=motion_events,
        timing_mode=motion_schedule.timing_mode,
        frames=frames,
        deterministic_report=deterministic_report,
    )


def _validate_response_targets(response: CriticResponse, request: CriticRequest) -> None:
    allowed = {(CriticTargetKind.SCENE, "__scene__")}
    allowed.update((CriticTargetKind.NODE, item.node_id) for item in request.nodes)
    allowed.update((CriticTargetKind.RELATION, item.relation_id) for item in request.relations)
    allowed.update((CriticTargetKind.GROUP, item.group_id) for item in request.groups)
    for issue in response.issues:
        identities = {(target.kind, target.target_id) for target in issue.targets}
        unknown = identities - allowed
        if unknown:
            rendered = sorted(f"{kind.value}:{target_id}" for kind, target_id in unknown)
            raise QAInvalidInputError(f"critic issue '{issue.issue_id}' references unknown targets {rendered}")
    for patch in response.patches:
        identities = {(target.kind, target.target_id) for target in patch.targets}
        unknown = identities - allowed
        if unknown:
            rendered = sorted(f"{kind.value}:{target_id}" for kind, target_id in unknown)
            raise QAInvalidInputError(f"critic patch '{patch.patch_id}' references unknown targets {rendered}")


def _failure_result(
    *,
    deterministic_report: DeterministicQAReport,
    failure_policy: CriticFailurePolicy,
    state: CriticGateState,
    warning: str,
) -> QualityGateResult:
    return QualityGateResult(
        scene_id=deterministic_report.scene_id,
        quality_mode=QualityMode.CRITIC,
        failure_policy=failure_policy,
        deterministic_report=deterministic_report,
        critic_state=state,
        critic_response=None,
        approved=failure_policy == CriticFailurePolicy.CONTINUE,
        warnings=(warning,),
    )


def run_quality_gate(
    *,
    deterministic_report: DeterministicQAReport,
    quality_mode: QualityMode = QualityMode.DETERMINISTIC,
    critic_request: CriticRequest | None = None,
    provider: CriticProvider | None = None,
    failure_policy: CriticFailurePolicy = CriticFailurePolicy.CONTINUE,
) -> QualityGateResult:
    """Apply deterministic-first quality policy and optionally call one critic provider."""
    if not isinstance(deterministic_report, DeterministicQAReport):
        raise QAInvalidInputError("deterministic_report must be a DeterministicQAReport")
    if not isinstance(quality_mode, QualityMode):
        raise QAInvalidInputError("quality_mode must be a QualityMode")
    if not isinstance(failure_policy, CriticFailurePolicy):
        raise QAInvalidInputError("failure_policy must be a CriticFailurePolicy")

    if not deterministic_report.passed:
        return QualityGateResult(
            scene_id=deterministic_report.scene_id,
            quality_mode=quality_mode,
            failure_policy=failure_policy,
            deterministic_report=deterministic_report,
            critic_state=CriticGateState.SKIPPED_DETERMINISTIC_FAIL,
            critic_response=None,
            approved=False,
            warnings=(),
        )

    if quality_mode == QualityMode.DETERMINISTIC:
        return QualityGateResult(
            scene_id=deterministic_report.scene_id,
            quality_mode=quality_mode,
            failure_policy=failure_policy,
            deterministic_report=deterministic_report,
            critic_state=CriticGateState.NOT_REQUESTED,
            critic_response=None,
            approved=True,
            warnings=(),
        )

    if critic_request is not None and not isinstance(critic_request, CriticRequest):
        raise QAInvalidInputError("critic_request must be a CriticRequest in critic quality mode")
    if critic_request is None:
        return _failure_result(
            deterministic_report=deterministic_report,
            failure_policy=failure_policy,
            state=CriticGateState.UNAVAILABLE,
            warning="critic_unavailable: critic request was not provided",
        )
    if critic_request.scene_id != deterministic_report.scene_id or critic_request.deterministic_report != deterministic_report:
        raise QAInvalidInputError("critic_request must be derived from the exact deterministic report passed to quality gate")
    if provider is None:
        return _failure_result(
            deterministic_report=deterministic_report,
            failure_policy=failure_policy,
            state=CriticGateState.UNAVAILABLE,
            warning="critic_unavailable: provider is not configured",
        )

    try:
        raw_response = provider.critique(critic_request)
    except CriticProviderQuotaError:
        return _failure_result(
            deterministic_report=deterministic_report,
            failure_policy=failure_policy,
            state=CriticGateState.QUOTA_EXCEEDED,
            warning="critic_unavailable: quota_exceeded",
        )
    except CriticProviderUnavailableError:
        return _failure_result(
            deterministic_report=deterministic_report,
            failure_policy=failure_policy,
            state=CriticGateState.UNAVAILABLE,
            warning="critic_unavailable: provider_unavailable",
        )
    except TimeoutError:
        return _failure_result(
            deterministic_report=deterministic_report,
            failure_policy=failure_policy,
            state=CriticGateState.TIMEOUT,
            warning="critic_unavailable: timeout",
        )
    except CriticProviderError:
        return _failure_result(
            deterministic_report=deterministic_report,
            failure_policy=failure_policy,
            state=CriticGateState.PROVIDER_ERROR,
            warning="critic_unavailable: provider_error",
        )
    except Exception as exc:
        return _failure_result(
            deterministic_report=deterministic_report,
            failure_policy=failure_policy,
            state=CriticGateState.PROVIDER_ERROR,
            warning=f"critic_unavailable: unexpected_provider_error:{type(exc).__name__}",
        )

    try:
        if isinstance(raw_response, CriticResponse):
            response = CriticResponse.model_validate(raw_response.model_dump(mode="json"))
        elif isinstance(raw_response, Mapping):
            response = CriticResponse.model_validate(dict(raw_response))
        else:
            raise QAInvalidInputError("critic provider must return structured mapping/CriticResponse; prose strings are not accepted")
        _validate_response_targets(response, critic_request)
    except (ValidationError, QAInvalidInputError, ValueError, TypeError):
        return _failure_result(
            deterministic_report=deterministic_report,
            failure_policy=failure_policy,
            state=CriticGateState.INVALID_RESPONSE,
            warning="critic_unavailable: invalid_structured_response",
        )

    if response.status == CriticStatus.PASS:
        return QualityGateResult(
            scene_id=deterministic_report.scene_id,
            quality_mode=quality_mode,
            failure_policy=failure_policy,
            deterministic_report=deterministic_report,
            critic_state=CriticGateState.PASS,
            critic_response=response,
            approved=True,
            warnings=(),
        )
    return QualityGateResult(
        scene_id=deterministic_report.scene_id,
        quality_mode=quality_mode,
        failure_policy=failure_policy,
        deterministic_report=deterministic_report,
        critic_state=CriticGateState.REPAIR_REQUIRED,
        critic_response=response,
        approved=False,
        warnings=(),
    )
