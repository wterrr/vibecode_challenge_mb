"""Strict public contracts for LearnFlow V2 CP2.12 optional VLM critic."""

from __future__ import annotations

from enum import Enum
import math
from types import MappingProxyType
from typing import Any, ClassVar, Literal, Mapping

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
    GROUP = "GROUP"


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

    @field_validator("sample_id")
    @classmethod
    def _normalize_sample_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise QAInvalidInputError("frame-selection sample_id cannot be blank")
        return normalized

    @field_validator("reasons", mode="before")
    @classmethod
    def _normalize_reasons(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple) or not value:
            raise QAInvalidInputError("frame-selection reasons must be a non-empty tuple/list")
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise QAInvalidInputError("frame-selection reasons must be non-empty strings")
        normalized = tuple(item.strip() for item in value)
        if len(normalized) != len(set(normalized)):
            raise QAInvalidInputError("frame-selection reasons cannot contain duplicates after normalization")
        return tuple(sorted(normalized))


class CriticFrameInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    selection: CriticFrameSelection
    image_ref: str = Field(..., min_length=1, description="Opaque rendered-frame reference; no raw image bytes in the contract")
    overlay: CriticOverlaySpec

    @field_validator("image_ref")
    @classmethod
    def _validate_image_ref(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise QAInvalidInputError("critic image_ref cannot be blank")
        if any(ch in normalized for ch in ("\n", "\r", "\x00")):
            raise QAInvalidInputError("critic image_ref cannot contain control characters")
        return normalized


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


class CriticSceneGroupSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    group_id: str = Field(..., min_length=1)
    member_ids: tuple[str, ...] = Field(..., min_length=1)
    label: str | None = None
    semantic_role: str | None = None

    @field_validator("member_ids", mode="before")
    @classmethod
    def _normalize_members(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple) or not value:
            raise QAInvalidInputError("critic group member_ids must be a non-empty tuple/list")
        normalized = tuple(item.strip() for item in value if isinstance(item, str))
        if len(normalized) != len(value) or any(not item for item in normalized):
            raise QAInvalidInputError("critic group member_ids require non-empty strings")
        if len(normalized) != len(set(normalized)):
            raise QAInvalidInputError("critic group member_ids cannot contain duplicates")
        return tuple(sorted(normalized))


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
