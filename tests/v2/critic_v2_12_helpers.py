from __future__ import annotations

from typing import Any

from learnflow_v2.layout.schema import LayoutBox, LayoutGraph, LayoutStrategy, Rect
from learnflow_v2.motion.enums import MotionStyle, MotionTargetKind, MotionVerb
from learnflow_v2.motion.scheduler import MotionSchedule, ScheduledMotionEvent
from learnflow_v2.qa import (
    CriticIssue,
    CriticIssueSeverity,
    CriticIssueType,
    CriticPatchOp,
    CriticPatchSuggestion,
    CriticResponse,
    CriticStatus, CriticTargetKind, CriticTargetRef,
    DeterministicQAReport,
    QAIssue,
    QAIssueCode,
    QAIssueSeverity,
    build_critic_request,
    select_event_aware_frames,
)
from learnflow_v2.scenegraph.enums import NodeKind, RelationKind
from learnflow_v2.scenegraph.schema import SceneGraph, SceneGroup, SceneNode, SceneRelation


def good_scene(scene_id: str = "scene_critic") -> SceneGraph:
    return SceneGraph(
        scene_id=scene_id,
        nodes=[
            SceneNode(id="n1", kind=NodeKind.CONCEPT, label="Input"),
            SceneNode(id="n2", kind=NodeKind.CONCEPT, label="Output"),
        ],
        relations=[
            SceneRelation(id="r1", source="n1", target="n2", kind=RelationKind.FLOW, label="flow")
        ],
        groups=[
            SceneGroup(id="g1", member_ids=["n1", "n2"], label="Input/output pair", semantic_role="pair")
        ],
    )


def good_layout(scene_id: str = "scene_critic", *, reverse: bool = False) -> LayoutGraph:
    boxes = [
        LayoutBox(node_id="n1", rect=Rect(x=160, y=180, width=240, height=120), zone="CONTENT"),
        LayoutBox(node_id="n2", rect=Rect(x=760, y=380, width=240, height=120), zone="CONTENT"),
    ]
    if reverse:
        boxes.reverse()
    return LayoutGraph(
        scene_id=scene_id,
        frame_profile_id="16:9_1280x720",
        frame_width=1280,
        frame_height=720,
        boxes=boxes,
        routed_edges=[],
        strategy=LayoutStrategy.CONCEPT_CARD,
        feasible=True,
        metadata={},
    )


def _event(
    event_id: str,
    target: str,
    verb: MotionVerb,
    style: MotionStyle,
    start: float,
    end: float,
    *,
    target_kind: MotionTargetKind = MotionTargetKind.NODE,
    dependencies: tuple[str, ...] = (),
) -> ScheduledMotionEvent:
    return ScheduledMotionEvent(
        event_id=event_id,
        target=target,
        target_kind=target_kind,
        verb=verb,
        style=style,
        start_time=start,
        end_time=end,
        duration=round(end - start, 4),
        dependencies=dependencies,
    )


def good_schedule(scene_id: str = "scene_critic") -> MotionSchedule:
    return MotionSchedule(
        scene_id=scene_id,
        scene_duration=5.0,
        scheduled_events=(
            _event("e_enter", "n1", MotionVerb.ENTER, MotionStyle.FADE, 0.0, 0.4),
            _event("e_move", "n1", MotionVerb.TRANSFORM, MotionStyle.MOVE, 1.0, 1.5, dependencies=("e_enter",)),
            _event("e_rel", "r1", MotionVerb.RELATION, MotionStyle.DRAW_EDGE, 2.0, 2.5, target_kind=MotionTargetKind.RELATION),
            _event("e_exit", "n1", MotionVerb.EXIT, MotionStyle.FADE, 4.5, 4.9, dependencies=("e_move",)),
        ),
        timing_mode=None,
    )


def pass_report(scene_id: str = "scene_critic") -> DeterministicQAReport:
    return DeterministicQAReport(scene_id=scene_id, passed=True, issues=())


def fail_report(scene_id: str = "scene_critic") -> DeterministicQAReport:
    issue = QAIssue(
        issue_id="BBOX_OVERLAP:n1__n2",
        code=QAIssueCode.BBOX_OVERLAP,
        severity=QAIssueSeverity.ERROR,
        message="overlap",
        object_ids=("n1", "n2"),
        evidence={"count": 1},
    )
    return DeterministicQAReport(scene_id=scene_id, passed=False, issues=(issue,))


def good_request(*, reverse_layout: bool = False):
    schedule = good_schedule()
    selections = select_event_aware_frames(schedule)
    refs = {item.sample_id: f"frame://{item.sample_id}" for item in selections}
    return build_critic_request(
        narration="Explain how the input becomes the output.",
        scene_graph=good_scene(),
        layout_graph=good_layout(reverse=reverse_layout),
        motion_schedule=schedule,
        deterministic_report=pass_report(),
        frame_refs=refs,
    )


def pass_response() -> CriticResponse:
    return CriticResponse(status=CriticStatus.PASS)


def repair_response(**patch_updates: Any) -> CriticResponse:
    patch_data = dict(
        patch_id="p1",
        op=CriticPatchOp.ADD_EMPHASIS,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n2"),),
    )
    patch_data.update(patch_updates)
    return CriticResponse(
        status=CriticStatus.REPAIR,
        issues=(
            CriticIssue(
                issue_id="i1",
                issue_type=CriticIssueType.VISUAL_HIERARCHY,
                severity=CriticIssueSeverity.MEDIUM,
                targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n2"),),
                reason="The output is visually weaker than the supporting input.",
            ),
        ),
        patches=(CriticPatchSuggestion(**patch_data),),
    )


class FakeProvider:
    def __init__(self, result: Any = None, exc: Exception | None = None):
        self.result = pass_response() if result is None and exc is None else result
        self.exc = exc
        self.calls = 0
        self.requests = []

    def critique(self, request):
        self.calls += 1
        self.requests.append(request)
        if self.exc is not None:
            raise self.exc
        return self.result
