"""Strict public contracts for LearnFlow V2 CP2.12 optional VLM critic."""

from __future__ import annotations

from enum import Enum
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.layout.schema import LayoutStrategy
from learnflow_v2.motion.enums import (
    MotionStyle, MotionTargetKind, MotionVerb, TIER_1_MOTION_GRAMMAR,
    TIER_2_3_RESERVED_STYLES, TIER_2_3_RESERVED_VERBS, VERB_TARGET_KIND_MAP,
)
from learnflow_v2.motion.beats import TimingMode
from learnflow_v2.qa.errors import QAInvalidInputError
from learnflow_v2.qa.schema import DeterministicQAReport
from learnflow_v2.scenegraph.enums import NodeKind, PreferredRegion, RelationKind

V2_CRITIC_SCHEMA_VERSION = "2.1"


def _finite(value: Any, field: str, *, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise QAInvalidInputError(f"{field} must be a finite real number")
    result = float(value)
    if not math.isfinite(result):
        raise QAInvalidInputError(f"{field} must be finite")
    if minimum is not None and result < minimum:
        raise QAInvalidInputError(f"{field} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise QAInvalidInputError(f"{field} must be <= {maximum}")
    return result


class QualityMode(str, Enum):
    DETERMINISTIC = "deterministic"
    CRITIC = "critic"


class CriticFailurePolicy(str, Enum):
    CONTINUE = "CONTINUE"
    STRICT = "STRICT"


class CriticStatus(str, Enum):
    PASS = "PASS"
    REPAIR = "REPAIR"


class CriticGateState(str, Enum):
    SKIPPED_DETERMINISTIC_FAIL = "SKIPPED_DETERMINISTIC_FAIL"
    NOT_REQUESTED = "NOT_REQUESTED"
    PASS = "PASS"
    REPAIR_REQUIRED = "REPAIR_REQUIRED"
    UNAVAILABLE = "UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    INVALID_RESPONSE = "INVALID_RESPONSE"


class CriticIssueSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CriticIssueType(str, Enum):
    VISUAL_HIERARCHY = "VISUAL_HIERARCHY"
    VISUAL_CLUTTER = "VISUAL_CLUTTER"
    READABILITY = "READABILITY"
    SPATIAL_BALANCE = "SPATIAL_BALANCE"
    MOTION_PACING = "MOTION_PACING"
    CONTINUITY = "CONTINUITY"
    PEDAGOGICAL_ALIGNMENT = "PEDAGOGICAL_ALIGNMENT"
    STYLE_CONSISTENCY = "STYLE_CONSISTENCY"


class CriticTargetKind(str, Enum):
    SCENE = "SCENE"
    NODE = "NODE"
    RELATION = "RELATION"


class CriticTargetRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: CriticTargetKind
    target_id: str = Field(..., min_length=1)

    @field_validator("target_id")
    @classmethod
    def _normalize_target_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise QAInvalidInputError("critic target_id cannot be blank")
        return value

    @model_validator(mode="after")
    def _validate_scene_target(self) -> "CriticTargetRef":
        if self.kind == CriticTargetKind.SCENE and self.target_id != "__scene__":
            raise QAInvalidInputError("SCENE critic target must use target_id='__scene__'")
        if self.kind != CriticTargetKind.SCENE and self.target_id == "__scene__":
            raise QAInvalidInputError("__scene__ is reserved for SCENE critic target")
        return self


class CriticPatchOp(str, Enum):
    SET_REGION = "SET_REGION"
    CHANGE_LAYOUT_STRATEGY = "CHANGE_LAYOUT_STRATEGY"
    INCREASE_GAP = "INCREASE_GAP"
    DECREASE_GAP = "DECREASE_GAP"
    CHANGE_IMPORTANCE = "CHANGE_IMPORTANCE"
    SCALE_NODE = "SCALE_NODE"
    REWRAP_TEXT = "REWRAP_TEXT"
    SPLIT_GROUP = "SPLIT_GROUP"
    MERGE_GROUP = "MERGE_GROUP"
    REROUTE_EDGE = "REROUTE_EDGE"
    CHANGE_EDGE_STYLE = "CHANGE_EDGE_STYLE"
    CHANGE_VISUAL_INTENT = "CHANGE_VISUAL_INTENT"
    REMOVE_DECORATION = "REMOVE_DECORATION"
    ADD_EMPHASIS = "ADD_EMPHASIS"
    CHANGE_MOTION_STYLE = "CHANGE_MOTION_STYLE"
    REDUCE_MOTION = "REDUCE_MOTION"


class CriticFrameReason(str, Enum):
    SCENE_START = "SCENE_START"
    AFTER_ENTER = "AFTER_ENTER"
    AFTER_TRANSFORM = "AFTER_TRANSFORM"
    BEFORE_EXIT = "BEFORE_EXIT"
    SCENE_END = "SCENE_END"


class NormalizedRect(BaseModel):
    """Renderer-neutral [0,1] geometry used only for critic context."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    left: float
    top: float
    right: float
    bottom: float

    @field_validator("left", "top", "right", "bottom", mode="before")
    @classmethod
    def _validate_coord(cls, value: Any, info: ValidationInfo) -> float:
        return _finite(value, info.field_name or "coordinate", minimum=0.0, maximum=1.0)

    @model_validator(mode="after")
    def _validate_rect(self) -> "NormalizedRect":
        if self.right <= self.left or self.bottom <= self.top:
            raise QAInvalidInputError("normalized rectangle must have positive width and height")
        return self


class CriticOverlayElement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    element_id: str = Field(..., min_length=1)
    anchor_cell: str = Field(..., pattern=r"^[A-F](0[1-6])$")
    semantic_region: str = Field(..., min_length=1)
    rect: NormalizedRect


class CriticOverlaySpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    grid_rows: Literal[6] = 6
    grid_columns: Literal[6] = 6
    elements: tuple[CriticOverlayElement, ...] = Field(default_factory=tuple)

    @field_validator("elements", mode="before")
    @classmethod
    def _tupleize(cls, value: Any) -> tuple[Any, ...]:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _validate_unique_sorted(self) -> "CriticOverlaySpec":
        ids = [item.element_id for item in self.elements]
        if len(ids) != len(set(ids)):
            raise QAInvalidInputError("critic overlay element IDs must be unique")
        ordered = tuple(sorted(self.elements, key=lambda item: item.element_id))
        if ordered != self.elements:
            object.__setattr__(self, "elements", ordered)
        return self


class CriticFrameSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    sample_id: str = Field(..., min_length=1)
    timestamp: float = Field(..., ge=0.0)
    reasons: tuple[str, ...] = Field(..., min_length=1)

    @field_validator("timestamp", mode="before")
    @classmethod
    def _validate_timestamp(cls, value: Any) -> float:
        return _finite(value, "timestamp", minimum=0.0)

    @field_validator("reasons", mode="before")
    @classmethod
    def _normalize_reasons(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple) or not value:
            raise QAInvalidInputError("frame-selection reasons must be a non-empty tuple/list")
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise QAInvalidInputError("frame-selection reasons must be non-empty strings")
        if len(value) != len(set(value)):
            raise QAInvalidInputError("frame-selection reasons cannot contain duplicates")
        return tuple(sorted(item.strip() for item in value))


class CriticFrameInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    selection: CriticFrameSelection
    image_ref: str = Field(..., min_length=1, description="Opaque rendered-frame reference; no raw image bytes in the contract")
    overlay: CriticOverlaySpec


class CriticSceneNodeSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    node_id: str = Field(..., min_length=1)
    kind: NodeKind
    label: str | None = None
    semantic_key: str | None = None
    semantic_role: str | None = None


class CriticSceneRelationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    relation_id: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    kind: RelationKind
    label: str | None = None


class CriticLayoutBoxSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    node_id: str = Field(..., min_length=1)
    semantic_region: str = Field(..., min_length=1)
    anchor_cell: str = Field(..., pattern=r"^[A-F](0[1-6])$")
    rect: NormalizedRect


class CriticMotionEventSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    event_id: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    target_kind: MotionTargetKind
    verb: MotionVerb
    style: MotionStyle
    start_time: float
    end_time: float
    trigger_beat: str | None = None

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def _validate_time(cls, value: Any, info: ValidationInfo) -> float:
        return _finite(value, info.field_name or "time", minimum=0.0)

    @model_validator(mode="after")
    def _validate_interval(self) -> "CriticMotionEventSummary":
        if self.end_time <= self.start_time:
            raise QAInvalidInputError("critic motion summary requires end_time > start_time")
        if self.verb in TIER_2_3_RESERVED_VERBS or self.style in TIER_2_3_RESERVED_STYLES:
            raise QAInvalidInputError("critic motion summary cannot contain unsupported Tier-2/Tier-3 motion")
        allowed = TIER_1_MOTION_GRAMMAR.get(self.verb)
        if allowed is None or self.style not in allowed:
            raise QAInvalidInputError("critic motion summary contains invalid Tier-1 verb/style combination")
        if self.target_kind != VERB_TARGET_KIND_MAP[self.verb]:
            raise QAInvalidInputError("critic motion summary target_kind contradicts motion verb")
        return self


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

    @field_validator("nodes", "relations", "layout_boxes", "motion_events", "frames", mode="before")
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
        box_ids = [item.node_id for item in self.layout_boxes]
        frame_ids = [item.selection.sample_id for item in self.frames]
        for name, values in (("node", node_ids), ("relation", relation_ids), ("layout box", box_ids), ("frame sample", frame_ids)):
            if len(values) != len(set(values)):
                raise QAInvalidInputError(f"critic request {name} IDs must be unique")
        if set(box_ids) - set(node_ids):
            raise QAInvalidInputError("critic layout summary references nodes absent from scene summary")
        if not node_ids:
            raise QAInvalidInputError("critic request requires at least one scene node")
        node_set = set(node_ids)
        relation_set = set(relation_ids)
        for relation in self.relations:
            if relation.source not in node_set or relation.target not in node_set:
                raise QAInvalidInputError(f"critic relation '{relation.relation_id}' references unknown node")
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

        object.__setattr__(self, "nodes", tuple(sorted(self.nodes, key=lambda item: item.node_id)))
        object.__setattr__(self, "relations", tuple(sorted(self.relations, key=lambda item: item.relation_id)))
        object.__setattr__(self, "layout_boxes", tuple(sorted(self.layout_boxes, key=lambda item: item.node_id)))
        object.__setattr__(self, "motion_events", tuple(sorted(self.motion_events, key=lambda item: (item.start_time, item.event_id))))
        object.__setattr__(self, "frames", tuple(sorted(self.frames, key=lambda item: (item.selection.timestamp, item.selection.sample_id))))
        return self

    def to_canonical_json(self) -> str:
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, payload: str) -> "CriticRequest":
        return cls.model_validate_json(payload)


class CriticIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    issue_id: str = Field(..., min_length=1, max_length=128)
    issue_type: CriticIssueType
    severity: CriticIssueSeverity
    targets: tuple[CriticTargetRef, ...] = Field(..., min_length=1)
    reason: str = Field(..., min_length=1, max_length=1000)

    @field_validator("targets", mode="before")
    @classmethod
    def _normalize_targets(cls, value: Any) -> tuple[Any, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple) or not value:
            raise QAInvalidInputError("critic issue targets must be a non-empty tuple/list")
        return value

    @model_validator(mode="after")
    def _validate_target_refs(self) -> "CriticIssue":
        identities = [(target.kind.value, target.target_id) for target in self.targets]
        if len(identities) != len(set(identities)):
            raise QAInvalidInputError("critic issue targets cannot contain duplicate typed identities")
        object.__setattr__(self, "targets", tuple(sorted(self.targets, key=lambda target: (target.kind.value, target.target_id))))
        return self

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str) -> str:
        if not value.strip():
            raise QAInvalidInputError("critic issue reason cannot be whitespace-only")
        return value.strip()


class CriticPatchSuggestion(BaseModel):
    """Whitelisted semantic suggestion only; CP2.12 never executes these patches."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    patch_id: str = Field(..., min_length=1, max_length=128)
    op: CriticPatchOp
    targets: tuple[CriticTargetRef, ...] = Field(..., min_length=1)
    normalized_magnitude: float | None = None
    region: PreferredRegion | None = None
    layout_strategy: LayoutStrategy | None = None
    motion_style: MotionStyle | None = None
    semantic_value: str | None = Field(default=None, max_length=120)

    @field_validator("targets", mode="before")
    @classmethod
    def _normalize_targets(cls, value: Any) -> tuple[Any, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple) or not value:
            raise QAInvalidInputError("critic patch targets must be a non-empty tuple/list")
        return value

    @field_validator("normalized_magnitude", mode="before")
    @classmethod
    def _validate_magnitude(cls, value: Any) -> float | None:
        if value is None:
            return None
        return _finite(value, "normalized_magnitude", minimum=-1.0, maximum=1.0)

    @field_validator("semantic_value")
    @classmethod
    def _normalize_semantic_value(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise QAInvalidInputError("semantic_value cannot be blank")
        if any(ch in value for ch in ("\n", "\r", "\x00")):
            raise QAInvalidInputError("semantic_value must be a single safe semantic token/phrase")
        if not value[0].isalpha() or any(not (ch.isalnum() or ch in " _.-:") for ch in value):
            raise QAInvalidInputError("semantic_value may contain only semantic words/tokens, not code, coordinates, or commands")
        upper = value.upper().replace("-", "_")
        forbidden = ("SET_PIXEL", "EXECUTE_CODE", "WRITE_PYTHON", "FFMPEG", "MANIM", "PILLOW", "SHELL", "TERMINAL")
        if any(token in upper for token in forbidden):
            raise QAInvalidInputError("semantic_value cannot encode renderer, executable-code, or pixel commands")
        return value

    @model_validator(mode="after")
    def _validate_op_parameters(self) -> "CriticPatchSuggestion":
        identities = [(target.kind.value, target.target_id) for target in self.targets]
        if len(identities) != len(set(identities)):
            raise QAInvalidInputError("critic patch targets cannot contain duplicate typed identities")
        object.__setattr__(self, "targets", tuple(sorted(self.targets, key=lambda target: (target.kind.value, target.target_id))))
        op = self.op
        expected: set[str] = set()
        if op == CriticPatchOp.SET_REGION:
            expected = {"region"}
        elif op == CriticPatchOp.CHANGE_LAYOUT_STRATEGY:
            expected = {"layout_strategy"}
        elif op in {
            CriticPatchOp.INCREASE_GAP,
            CriticPatchOp.DECREASE_GAP,
            CriticPatchOp.CHANGE_IMPORTANCE,
            CriticPatchOp.SCALE_NODE,
        }:
            expected = {"normalized_magnitude"}
        elif op == CriticPatchOp.CHANGE_MOTION_STYLE:
            expected = {"motion_style"}
        elif op in {CriticPatchOp.CHANGE_EDGE_STYLE, CriticPatchOp.CHANGE_VISUAL_INTENT}:
            expected = {"semantic_value"}

        present = {
            name
            for name, value in (
                ("normalized_magnitude", self.normalized_magnitude),
                ("region", self.region),
                ("layout_strategy", self.layout_strategy),
                ("motion_style", self.motion_style),
                ("semantic_value", self.semantic_value),
            )
            if value is not None
        }
        if present != expected:
            raise QAInvalidInputError(
                f"critic patch op '{op.value}' requires exactly {sorted(expected)}, got {sorted(present)}"
            )
        if self.normalized_magnitude is not None and self.normalized_magnitude == 0.0:
            raise QAInvalidInputError("normalized_magnitude cannot be zero")
        if op in {CriticPatchOp.INCREASE_GAP, CriticPatchOp.DECREASE_GAP, CriticPatchOp.CHANGE_IMPORTANCE}:
            if self.normalized_magnitude is None or self.normalized_magnitude <= 0.0:
                raise QAInvalidInputError(f"{op.value} requires positive normalized_magnitude")
        if self.motion_style in TIER_2_3_RESERVED_STYLES:
            raise QAInvalidInputError("critic cannot suggest unsupported Tier-2/Tier-3 motion style")
        return self


class CriticResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.1"] = V2_CRITIC_SCHEMA_VERSION
    status: CriticStatus
    issues: tuple[CriticIssue, ...] = Field(default_factory=tuple)
    patches: tuple[CriticPatchSuggestion, ...] = Field(default_factory=tuple)

    @field_validator("issues", "patches", mode="before")
    @classmethod
    def _tupleize(cls, value: Any) -> tuple[Any, ...]:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _validate_response(self) -> "CriticResponse":
        issue_ids = [item.issue_id for item in self.issues]
        patch_ids = [item.patch_id for item in self.patches]
        if len(issue_ids) != len(set(issue_ids)):
            raise QAInvalidInputError("critic response issue IDs must be unique")
        if len(patch_ids) != len(set(patch_ids)):
            raise QAInvalidInputError("critic response patch IDs must be unique")
        if self.status == CriticStatus.PASS and (self.issues or self.patches):
            raise QAInvalidInputError("critic PASS response cannot include issues or patches")
        if self.status == CriticStatus.REPAIR and (not self.issues or not self.patches):
            raise QAInvalidInputError("critic REPAIR response requires at least one issue and one patch suggestion")
        object.__setattr__(self, "issues", tuple(sorted(self.issues, key=lambda item: item.issue_id)))
        object.__setattr__(self, "patches", tuple(sorted(self.patches, key=lambda item: item.patch_id)))
        return self

    def to_canonical_json(self) -> str:
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, payload: str) -> "CriticResponse":
        return cls.model_validate_json(payload)


class QualityGateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.1"] = V2_CRITIC_SCHEMA_VERSION
    scene_id: str = Field(..., min_length=1)
    quality_mode: QualityMode
    failure_policy: CriticFailurePolicy
    deterministic_report: DeterministicQAReport
    critic_state: CriticGateState
    critic_response: CriticResponse | None = None
    approved: bool
    warnings: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("warnings", mode="before")
    @classmethod
    def _normalize_warnings(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple):
            raise QAInvalidInputError("quality-gate warnings must be tuple/list")
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise QAInvalidInputError("quality-gate warnings require non-empty strings")
        if len(value) != len(set(value)):
            raise QAInvalidInputError("quality-gate warnings cannot contain duplicates")
        return tuple(sorted(item.strip() for item in value))

    @model_validator(mode="after")
    def _validate_gate(self) -> "QualityGateResult":
        if self.scene_id != self.deterministic_report.scene_id:
            raise QAInvalidInputError("quality-gate scene_id must match deterministic report")
        if not self.deterministic_report.passed:
            if self.approved or self.critic_response is not None or self.critic_state != CriticGateState.SKIPPED_DETERMINISTIC_FAIL:
                raise QAInvalidInputError("deterministic QA failure must block approval and skip critic")
            if self.warnings:
                raise QAInvalidInputError("deterministic QA failure result cannot carry critic warnings")
            return self

        if self.quality_mode == QualityMode.DETERMINISTIC:
            if not self.approved or self.critic_state != CriticGateState.NOT_REQUESTED or self.critic_response is not None:
                raise QAInvalidInputError("deterministic quality mode must approve deterministic PASS without critic")
            if self.warnings:
                raise QAInvalidInputError("deterministic quality mode cannot carry critic warnings")
            return self

        if self.critic_state == CriticGateState.PASS:
            if not self.approved or self.critic_response is None or self.critic_response.status != CriticStatus.PASS:
                raise QAInvalidInputError("critic PASS state requires approved PASS response")
            if self.warnings:
                raise QAInvalidInputError("critic PASS state cannot carry failure warnings")
        elif self.critic_state == CriticGateState.REPAIR_REQUIRED:
            if self.approved or self.critic_response is None or self.critic_response.status != CriticStatus.REPAIR:
                raise QAInvalidInputError("critic REPAIR_REQUIRED state must block approval")
            if self.warnings:
                raise QAInvalidInputError("critic REPAIR_REQUIRED state cannot carry provider-failure warnings")
        elif self.critic_state in {
            CriticGateState.UNAVAILABLE,
            CriticGateState.TIMEOUT,
            CriticGateState.QUOTA_EXCEEDED,
            CriticGateState.PROVIDER_ERROR,
            CriticGateState.INVALID_RESPONSE,
        }:
            if self.critic_response is not None:
                raise QAInvalidInputError("critic failure state cannot carry a critic response")
            expected_approved = self.failure_policy == CriticFailurePolicy.CONTINUE
            if self.approved != expected_approved:
                raise QAInvalidInputError("critic failure approval contradicts configured failure policy")
            if not self.warnings:
                raise QAInvalidInputError("critic failure state requires an explicit warning")
        else:
            raise QAInvalidInputError(f"invalid critic state '{self.critic_state.value}' for critic quality mode")
        return self

    def to_canonical_json(self) -> str:
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, payload: str) -> "QualityGateResult":
        return cls.model_validate_json(payload)
