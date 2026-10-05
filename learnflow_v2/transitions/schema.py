"""Strict immutable schema for LearnFlow V2 cross-scene transition artifacts."""

from __future__ import annotations

import json
import math
from enum import Enum
from types import MappingProxyType
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_serializer, field_validator, model_validator

from learnflow_v2.core.errors import TransitionGeometryError, TransitionInvalidInputError
from learnflow_v2.core.jsonsafe import ensure_json_safe_dict
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.layout.schema import Rect

V2_TRANSITION_SCHEMA_VERSION = "2.1"
_EPS = 1e-4


class TransitionOperation(str, Enum):
    """Renderer-neutral cross-scene transition operations."""

    MOVE = "MOVE"
    RESIZE = "RESIZE"
    MORPH = "MORPH"
    FADE = "FADE"


TIER_1_TRANSITION_OPERATIONS = frozenset({TransitionOperation.MOVE, TransitionOperation.FADE})
TIER_2_TRANSITION_OPERATIONS = frozenset({TransitionOperation.RESIZE, TransitionOperation.MORPH})


def _finite_float(value: Any, name: str, *, strictly_positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TransitionInvalidInputError(
            f"{name} must be a real finite number, got {type(value).__name__}",
            details={"field": name, "value": repr(value)},
        )
    result = float(value)
    if not math.isfinite(result):
        raise TransitionInvalidInputError(
            f"{name} must be finite, got {result}",
            details={"field": name, "value": str(result)},
        )
    if strictly_positive and result <= 0.0:
        raise TransitionInvalidInputError(
            f"{name} must be strictly positive, got {result}",
            details={"field": name, "value": str(result)},
        )
    return result


def _non_empty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TransitionInvalidInputError(f"{name} must be a non-empty string")
    return value.strip()


def _thaw_json_value(value: Any) -> Any:
    if isinstance(value, (MappingProxyType, dict)):
        return {k: _thaw_json_value(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json_value(v) for v in value]
    if isinstance(value, list):
        return [_thaw_json_value(v) for v in value]
    return value


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({k: _freeze_json_value(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json_value(v) for v in value)
    return value


def _freeze_metadata(value: Any, *, field_name: str = "metadata") -> MappingProxyType[str, Any]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, (dict, MappingProxyType)):
        raise TransitionInvalidInputError(f"{field_name} must be a dict[str, JSON-safe value]")
    raw = _thaw_json_value(value)
    try:
        checked = ensure_json_safe_dict(raw, path=field_name)
    except ValueError as exc:
        raise TransitionInvalidInputError(f"{field_name} is not JSON-safe: {exc}") from exc
    return _freeze_json_value(checked)


def _normalized_geometry(
    source_rect: Rect,
    target_rect: Rect,
    source_frame_width: float,
    source_frame_height: float,
    target_frame_width: float,
    target_frame_height: float,
) -> tuple[float, float, float, float]:
    source_cx = source_rect.center_x / source_frame_width
    source_cy = source_rect.center_y / source_frame_height
    target_cx = target_rect.center_x / target_frame_width
    target_cy = target_rect.center_y / target_frame_height
    source_w = source_rect.width / source_frame_width
    source_h = source_rect.height / source_frame_height
    target_w = target_rect.width / target_frame_width
    target_h = target_rect.height / target_frame_height
    return (
        round(target_cx - source_cx, 8),
        round(target_cy - source_cy, 8),
        round(target_w / source_w, 8),
        round(target_h / source_h, 8),
    )


class PersistentObjectTransition(BaseModel):
    """One semantically persistent object moving between two scene layouts.

    Rectangles remain in their native frame coordinate spaces. Frame dimensions are
    therefore stored explicitly so a backend can interpolate deterministically even
    when source/target profiles differ (for example 16:9 -> 9:16).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    transition_item_id: str = Field(..., min_length=1)
    semantic_key: str = Field(..., min_length=1)
    concept_id: str = Field(..., min_length=1)
    from_node_id: str = Field(..., min_length=1)
    to_node_id: str = Field(..., min_length=1)
    requested_operation: TransitionOperation = Field(default=TransitionOperation.MOVE)
    effective_operation: TransitionOperation = Field(default=TransitionOperation.MOVE)
    fallback_reason: str | None = Field(default=None)
    source_rect: Rect
    target_rect: Rect
    source_frame_width: float = Field(..., gt=0.0)
    source_frame_height: float = Field(..., gt=0.0)
    target_frame_width: float = Field(..., gt=0.0)
    target_frame_height: float = Field(..., gt=0.0)
    source_zone: str = Field(default="CONTENT", min_length=1)
    target_zone: str = Field(default="CONTENT", min_length=1)
    normalized_displacement_x: float = Field(default=0.0)
    normalized_displacement_y: float = Field(default=0.0)
    normalized_scale_x: float = Field(default=1.0, gt=0.0)
    normalized_scale_y: float = Field(default=1.0, gt=0.0)
    metadata: MappingProxyType[str, Any] = Field(default_factory=lambda: MappingProxyType({}))

    @property
    def from_node(self) -> str:
        return self.from_node_id

    @property
    def to_node(self) -> str:
        return self.to_node_id

    @property
    def operation(self) -> TransitionOperation:
        return self.effective_operation

    @property
    def is_fallback(self) -> bool:
        return self.requested_operation != self.effective_operation

    @field_validator(
        "transition_item_id",
        "semantic_key",
        "concept_id",
        "from_node_id",
        "to_node_id",
        "source_zone",
        "target_zone",
        mode="before",
    )
    @classmethod
    def _validate_strings(cls, value: Any, info: ValidationInfo) -> str:
        return _non_empty_string(value, info.field_name or "value")

    @field_validator(
        "source_frame_width",
        "source_frame_height",
        "target_frame_width",
        "target_frame_height",
        mode="before",
    )
    @classmethod
    def _validate_frame_dimension(cls, value: Any, info: ValidationInfo) -> float:
        return _finite_float(value, info.field_name or "frame_dimension", strictly_positive=True)

    @field_validator("normalized_displacement_x", "normalized_displacement_y", mode="before")
    @classmethod
    def _validate_displacement(cls, value: Any, info: ValidationInfo) -> float:
        return _finite_float(value, info.field_name or "normalized_displacement")

    @field_validator("normalized_scale_x", "normalized_scale_y", mode="before")
    @classmethod
    def _validate_scale(cls, value: Any, info: ValidationInfo) -> float:
        result = _finite_float(value, info.field_name or "normalized_scale", strictly_positive=True)
        if result <= 0.0:
            raise TransitionGeometryError(f"{info.field_name} must be strictly positive")
        return result

    @field_validator("metadata", mode="before")
    @classmethod
    def _validate_metadata(cls, value: Any) -> MappingProxyType[str, Any]:
        return _freeze_metadata(value)

    @field_serializer("metadata", mode="plain")
    def _serialize_metadata(self, value: MappingProxyType[str, Any]) -> dict[str, Any]:
        return _thaw_json_value(value)

    @model_validator(mode="before")
    @classmethod
    def _fill_derived_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = dict(data)
        semantic_key = data.get("semantic_key")
        if semantic_key and "transition_item_id" not in data:
            data["transition_item_id"] = f"persist:{str(semantic_key).strip()}"

        required = (
            "source_rect",
            "target_rect",
            "source_frame_width",
            "source_frame_height",
            "target_frame_width",
            "target_frame_height",
        )
        if all(key in data for key in required):
            source_rect = data["source_rect"] if isinstance(data["source_rect"], Rect) else Rect.model_validate(data["source_rect"])
            target_rect = data["target_rect"] if isinstance(data["target_rect"], Rect) else Rect.model_validate(data["target_rect"])
            sfw = _finite_float(data["source_frame_width"], "source_frame_width", strictly_positive=True)
            sfh = _finite_float(data["source_frame_height"], "source_frame_height", strictly_positive=True)
            tfw = _finite_float(data["target_frame_width"], "target_frame_width", strictly_positive=True)
            tfh = _finite_float(data["target_frame_height"], "target_frame_height", strictly_positive=True)
            dx, dy, sx, sy = _normalized_geometry(source_rect, target_rect, sfw, sfh, tfw, tfh)
            data.setdefault("normalized_displacement_x", dx)
            data.setdefault("normalized_displacement_y", dy)
            data.setdefault("normalized_scale_x", sx)
            data.setdefault("normalized_scale_y", sy)
        return data

    @model_validator(mode="after")
    def _validate_invariants(self) -> "PersistentObjectTransition":
        if self.source_rect.right > self.source_frame_width + _EPS or self.source_rect.bottom > self.source_frame_height + _EPS:
            raise TransitionGeometryError(
                f"source_rect for '{self.semantic_key}' must fit inside source frame",
                details={"semantic_key": self.semantic_key},
            )
        if self.target_rect.right > self.target_frame_width + _EPS or self.target_rect.bottom > self.target_frame_height + _EPS:
            raise TransitionGeometryError(
                f"target_rect for '{self.semantic_key}' must fit inside target frame",
                details={"semantic_key": self.semantic_key},
            )

        expected = _normalized_geometry(
            self.source_rect,
            self.target_rect,
            self.source_frame_width,
            self.source_frame_height,
            self.target_frame_width,
            self.target_frame_height,
        )
        actual = (
            self.normalized_displacement_x,
            self.normalized_displacement_y,
            self.normalized_scale_x,
            self.normalized_scale_y,
        )
        if any(abs(a - e) > _EPS for a, e in zip(actual, expected)):
            raise TransitionGeometryError(
                f"Derived normalized geometry for '{self.semantic_key}' is inconsistent with source/target rects",
                details={"expected": expected, "actual": actual},
            )

        if self.requested_operation == self.effective_operation:
            if self.fallback_reason is not None:
                raise TransitionInvalidInputError(
                    "fallback_reason must be None when requested_operation equals effective_operation"
                )
        else:
            if self.fallback_reason is None or not self.fallback_reason.strip():
                raise TransitionInvalidInputError(
                    "fallback_reason is required when effective_operation differs from requested_operation"
                )
            allowed: dict[TransitionOperation, frozenset[TransitionOperation]] = {
                TransitionOperation.MOVE: frozenset({TransitionOperation.FADE}),
                TransitionOperation.RESIZE: frozenset({TransitionOperation.MOVE, TransitionOperation.FADE}),
                TransitionOperation.MORPH: frozenset({TransitionOperation.MOVE, TransitionOperation.FADE}),
                TransitionOperation.FADE: frozenset(),
            }
            if self.effective_operation not in allowed[self.requested_operation]:
                raise TransitionInvalidInputError(
                    f"Invalid fallback {self.requested_operation.value} -> {self.effective_operation.value}"
                )
        return self


class InterSceneTransitionPlan(BaseModel):
    """First-class cross-scene transition artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    schema_version: Literal["2.1"] = Field(default=V2_TRANSITION_SCHEMA_VERSION)
    transition_id: str = Field(..., min_length=1)
    from_scene: str = Field(..., min_length=1)
    to_scene: str = Field(..., min_length=1)
    duration: float = Field(..., gt=0.0)
    duration_ms: float = Field(..., gt=0.0)
    persistent_objects: tuple[PersistentObjectTransition, ...] = Field(default_factory=tuple)
    departing_node_ids: tuple[str, ...] = Field(default_factory=tuple)
    entering_node_ids: tuple[str, ...] = Field(default_factory=tuple)
    unmatched_keys: tuple[str, ...] = Field(default_factory=tuple)
    diagnostics: tuple[str, ...] = Field(default_factory=tuple)
    metadata: MappingProxyType[str, Any] = Field(default_factory=lambda: MappingProxyType({}))

    @property
    def from_scene_id(self) -> str:
        return self.from_scene

    @property
    def to_scene_id(self) -> str:
        return self.to_scene

    @field_validator("transition_id", "from_scene", "to_scene", mode="before")
    @classmethod
    def _validate_identifier(cls, value: Any, info: ValidationInfo) -> str:
        return _non_empty_string(value, info.field_name or "identifier")

    @field_validator("duration", "duration_ms", mode="before")
    @classmethod
    def _validate_duration(cls, value: Any, info: ValidationInfo) -> float:
        return _finite_float(value, info.field_name or "duration", strictly_positive=True)

    @field_validator("departing_node_ids", "entering_node_ids", "unmatched_keys", "diagnostics", mode="before")
    @classmethod
    def _normalize_string_tuple(cls, value: Any, info: ValidationInfo) -> tuple[str, ...]:
        if value is None:
            return tuple()
        if not isinstance(value, (list, tuple)):
            raise TransitionInvalidInputError(f"{info.field_name} must be a list or tuple of strings")
        result = tuple(_non_empty_string(v, info.field_name or "value") for v in value)
        if info.field_name != "diagnostics" and len(result) != len(set(result)):
            raise TransitionInvalidInputError(f"{info.field_name} must not contain duplicates")
        return result

    @field_validator("metadata", mode="before")
    @classmethod
    def _validate_metadata(cls, value: Any) -> MappingProxyType[str, Any]:
        return _freeze_metadata(value)

    @field_serializer("metadata", mode="plain")
    def _serialize_metadata(self, value: MappingProxyType[str, Any]) -> dict[str, Any]:
        return _thaw_json_value(value)

    @model_validator(mode="before")
    @classmethod
    def _fill_duration_pair(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if "duration" in data and "duration_ms" not in data:
            data["duration_ms"] = round(_finite_float(data["duration"], "duration", strictly_positive=True) * 1000.0, 6)
        elif "duration_ms" in data and "duration" not in data:
            data["duration"] = round(_finite_float(data["duration_ms"], "duration_ms", strictly_positive=True) / 1000.0, 9)
        return data

    @model_validator(mode="after")
    def _validate_plan(self) -> "InterSceneTransitionPlan":
        if self.from_scene == self.to_scene:
            raise TransitionInvalidInputError("from_scene and to_scene must be different")
        if abs(self.duration * 1000.0 - self.duration_ms) > 1e-3:
            raise TransitionInvalidInputError("duration and duration_ms disagree")

        item_ids = [p.transition_item_id for p in self.persistent_objects]
        semantic_keys = [p.semantic_key for p in self.persistent_objects]
        from_ids = [p.from_node_id for p in self.persistent_objects]
        to_ids = [p.to_node_id for p in self.persistent_objects]
        for label, values in (
            ("transition_item_id", item_ids),
            ("semantic_key", semantic_keys),
            ("from_node_id", from_ids),
            ("to_node_id", to_ids),
        ):
            if len(values) != len(set(values)):
                raise TransitionInvalidInputError(f"persistent_objects contain duplicate {label}")

        if set(from_ids) & set(self.departing_node_ids):
            raise TransitionInvalidInputError("A persistent source node cannot also be departing")
        if set(to_ids) & set(self.entering_node_ids):
            raise TransitionInvalidInputError("A persistent target node cannot also be entering")
        if set(semantic_keys) & set(self.unmatched_keys):
            raise TransitionInvalidInputError("A persistent semantic key cannot also be unmatched")

        canonical_objects = tuple(sorted(self.persistent_objects, key=lambda p: (p.semantic_key, p.transition_item_id)))
        canonical_departing = tuple(sorted(self.departing_node_ids))
        canonical_entering = tuple(sorted(self.entering_node_ids))
        canonical_unmatched = tuple(sorted(self.unmatched_keys))
        if canonical_objects != self.persistent_objects:
            object.__setattr__(self, "persistent_objects", canonical_objects)
        if canonical_departing != self.departing_node_ids:
            object.__setattr__(self, "departing_node_ids", canonical_departing)
        if canonical_entering != self.entering_node_ids:
            object.__setattr__(self, "entering_node_ids", canonical_entering)
        if canonical_unmatched != self.unmatched_keys:
            object.__setattr__(self, "unmatched_keys", canonical_unmatched)
        return self

    def get_persistent_object(self, semantic_key: str) -> PersistentObjectTransition | None:
        for item in self.persistent_objects:
            if item.semantic_key == semantic_key:
                return item
        return None

    def to_canonical_json(self) -> str:
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, payload: str) -> "InterSceneTransitionPlan":
        return cls.model_validate(json.loads(payload))
