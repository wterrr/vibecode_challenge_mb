"""Critic request contract for LearnFlow V2 CP2.12."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.motion.beats import TimingMode
from learnflow_v2.motion.enums import MotionTargetKind, MotionVerb
from learnflow_v2.qa.errors import QAInvalidInputError
from learnflow_v2.qa.schema import DeterministicQAReport
from learnflow_v2.qa._critic_context import (
    V2_CRITIC_SCHEMA_VERSION,
    CriticFrameInput, CriticLayoutBoxSummary, CriticMotionEventSummary,
    CriticSceneGroupSummary, CriticSceneNodeSummary, CriticSceneRelationSummary,
    CriticFrameReason, _finite,
)

class CriticRequest(BaseModel):
    """Fully structured critic context. It is legal only after deterministic QA PASS."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.1"] = V2_CRITIC_SCHEMA_VERSION
    scene_id: str = Field(..., min_length=1)
    narration: str = Field(..., min_length=1, max_length=20000)
    scene_duration: float = Field(..., gt=0.0)
    before_exit_lead_seconds: float = Field(default=0.05, ge=0.0)
    nodes: tuple[CriticSceneNodeSummary, ...]
    relations: tuple[CriticSceneRelationSummary, ...] = Field(default_factory=tuple)
    groups: tuple[CriticSceneGroupSummary, ...] = Field(default_factory=tuple)
    layout_boxes: tuple[CriticLayoutBoxSummary, ...]
    motion_events: tuple[CriticMotionEventSummary, ...] = Field(default_factory=tuple)
    timing_mode: TimingMode | None = None
    frames: tuple[CriticFrameInput, ...] = Field(..., min_length=1)
    deterministic_report: DeterministicQAReport

    @field_validator("scene_duration", mode="before")
    @classmethod
    def _validate_scene_duration(cls, value: Any) -> float:
        result = _finite(value, "scene_duration", minimum=0.0)
        if result <= 0.0:
            raise QAInvalidInputError("scene_duration must be > 0")
        return result

    @field_validator("before_exit_lead_seconds", mode="before")
    @classmethod
    def _validate_sampling_lead(cls, value: Any) -> float:
        return _finite(value, "before_exit_lead_seconds", minimum=0.0)

    @field_validator("nodes", "relations", "groups", "layout_boxes", "motion_events", "frames", mode="before")
    @classmethod
    def _tupleize(cls, value: Any) -> tuple[Any, ...]:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _validate_request(self) -> "CriticRequest":
        if not self.deterministic_report.passed:
            raise QAInvalidInputError("critic request cannot be created from a deterministic QA failure")
        if self.deterministic_report.scene_id != self.scene_id:
            raise QAInvalidInputError("critic request scene_id must match deterministic QA report")
        if not self.narration.strip():
            raise QAInvalidInputError("critic narration cannot be whitespace-only")

        node_ids = [item.node_id for item in self.nodes]
        relation_ids = [item.relation_id for item in self.relations]
        group_ids = [item.group_id for item in self.groups]
        box_ids = [item.node_id for item in self.layout_boxes]
        motion_event_ids = [item.event_id for item in self.motion_events]
        frame_ids = [item.selection.sample_id for item in self.frames]
        for name, values in (("node", node_ids), ("relation", relation_ids), ("group", group_ids), ("layout box", box_ids), ("motion event", motion_event_ids), ("frame sample", frame_ids)):
            if len(values) != len(set(values)):
                raise QAInvalidInputError(f"critic request {name} IDs must be unique")
        if set(box_ids) != set(node_ids):
            missing = sorted(set(node_ids) - set(box_ids))
            extra = sorted(set(box_ids) - set(node_ids))
            raise QAInvalidInputError(
                f"critic layout summary must exactly cover scene nodes; missing={missing}, extra={extra}"
            )
        if not node_ids:
            raise QAInvalidInputError("critic request requires at least one scene node")
        node_set = set(node_ids)
        relation_set = set(relation_ids)
        for relation in self.relations:
            if relation.source not in node_set or relation.target not in node_set:
                raise QAInvalidInputError(f"critic relation '{relation.relation_id}' references unknown node")
        for group in self.groups:
            if any(member_id not in node_set for member_id in group.member_ids):
                raise QAInvalidInputError(f"critic group '{group.group_id}' references unknown node")
        for event in self.motion_events:
            if event.end_time > self.scene_duration + 1e-6:
                raise QAInvalidInputError(f"critic motion event '{event.event_id}' exceeds scene duration")
            if event.target_kind == MotionTargetKind.NODE and event.target not in node_set:
                raise QAInvalidInputError(f"critic motion event '{event.event_id}' references unknown node target")
            if event.target_kind == MotionTargetKind.RELATION and event.target not in relation_set:
                raise QAInvalidInputError(f"critic motion event '{event.event_id}' references unknown relation target")
        if any(event.trigger_beat is not None for event in self.motion_events) and self.timing_mode is None:
            raise QAInvalidInputError("triggered critic motion summaries require timing provenance")

        box_map = {item.node_id: item for item in self.layout_boxes}
        for frame in self.frames:
            if frame.selection.timestamp > self.scene_duration + 1e-6:
                raise QAInvalidInputError(f"critic frame '{frame.selection.sample_id}' exceeds scene duration")
            overlay_map = {item.element_id: item for item in frame.overlay.elements}
            if set(overlay_map) != set(box_map):
                raise QAInvalidInputError("critic frame overlay must exactly cover layout-box IDs")
            for node_id, box in box_map.items():
                overlay_item = overlay_map[node_id]
                if (overlay_item.anchor_cell != box.anchor_cell or overlay_item.semantic_region != box.semantic_region or overlay_item.rect != box.rect):
                    raise QAInvalidInputError("critic frame overlay contradicts canonical layout summary")
        expected: dict[float, set[str]] = {}
        def add_expected(timestamp: float, reason: str) -> None:
            timestamp = min(max(timestamp, 0.0), self.scene_duration)
            expected.setdefault(round(timestamp, 6), set()).add(reason)

        add_expected(0.0, CriticFrameReason.SCENE_START.value)
        for event in self.motion_events:
            if event.verb == MotionVerb.ENTER:
                add_expected(event.end_time, f"{CriticFrameReason.AFTER_ENTER.value}:{event.event_id}")
            elif event.verb == MotionVerb.TRANSFORM:
                add_expected(event.end_time, f"{CriticFrameReason.AFTER_TRANSFORM.value}:{event.event_id}")
            elif event.verb == MotionVerb.EXIT:
                add_expected(max(0.0, event.start_time - self.before_exit_lead_seconds), f"{CriticFrameReason.BEFORE_EXIT.value}:{event.event_id}")
        add_expected(self.scene_duration, CriticFrameReason.SCENE_END.value)

        actual: dict[float, set[str]] = {}
        for frame in self.frames:
            key = round(frame.selection.timestamp, 6)
            if key in actual:
                raise QAInvalidInputError("critic event-aware sampling must merge reasons at identical timestamps")
            actual[key] = set(frame.selection.reasons)
        if actual != expected:
            raise QAInvalidInputError("critic frame samples do not match deterministic event-aware sampling contract")
        ordered_frames = tuple(sorted(self.frames, key=lambda item: (item.selection.timestamp, item.selection.sample_id)))
        for index, frame in enumerate(ordered_frames):
            expected_sample_id = f"sample_{index:03d}"
            if frame.selection.sample_id != expected_sample_id:
                raise QAInvalidInputError(
                    f"critic frame sample IDs must use deterministic sequence; expected '{expected_sample_id}', "
                    f"got '{frame.selection.sample_id}'"
                )

        object.__setattr__(self, "narration", self.narration.strip())
        object.__setattr__(self, "nodes", tuple(sorted(self.nodes, key=lambda item: item.node_id)))
        object.__setattr__(self, "relations", tuple(sorted(self.relations, key=lambda item: item.relation_id)))
        object.__setattr__(self, "groups", tuple(sorted(self.groups, key=lambda item: item.group_id)))
        object.__setattr__(self, "layout_boxes", tuple(sorted(self.layout_boxes, key=lambda item: item.node_id)))
        object.__setattr__(self, "motion_events", tuple(sorted(self.motion_events, key=lambda item: (item.start_time, item.event_id))))
        object.__setattr__(self, "frames", ordered_frames)
        return self

    def to_canonical_json(self) -> str:
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, payload: str) -> "CriticRequest":
        return cls.model_validate_json(payload)
