"""Strict, immutable Pydantic schema for LearnFlow V2 InterSceneTransitionPlan.

Cross-scene transition represents persistent-object visual transformations
between two consecutive scenes (previous LayoutGraph -> next LayoutGraph).
It is a first-class, versioned, canonically serializable artifact distinct
from scene-local MotionPlan.
"""

from __future__ import annotations

from enum import Enum
import math
from types import MappingProxyType
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_serializer, field_validator, model_validator

from learnflow_v2.core.errors import (
    TransitionGeometryError,
    TransitionInvalidInputError,
)
from learnflow_v2.core.jsonsafe import ensure_json_safe_dict
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.layout.schema import Rect

V2_TRANSITION_SCHEMA_VERSION = "2.1"


class TransitionOperation(str, Enum):
    """Supported inter-scene transition operations for persistent concepts."""

    MOVE = "MOVE"
    RESIZE = "RESIZE"
    MORPH = "MORPH"
    FADE = "FADE"


TIER_1_TRANSITION_OPERATIONS = frozenset({
    TransitionOperation.MOVE,
    TransitionOperation.FADE,
})
"""Authoritative Tier-1 baseline operations."""

TIER_2_TRANSITION_OPERATIONS = frozenset({
    TransitionOperation.RESIZE,
    TransitionOperation.MORPH,
})
"""Optional Tier-2 operations subject to renderer capability negotiation."""


def _check_finite_float(val: Any, name: str, min_val: float | None = 0.0) -> float:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise TransitionInvalidInputError(
            f"Field '{name}' must be a real finite number, got {type(val).__name__}: {val!r}",
            details={"field": name, "value": str(val)},
        )
    f_val = float(val)
    if not math.isfinite(f_val):
        raise TransitionInvalidInputError(
            f"Field '{name}' must be finite, got {f_val}",
            details={"field": name, "value": str(val)},
        )
    if min_val is not None and f_val < min_val:
        raise TransitionInvalidInputError(
            f"Field '{name}' must be >= {min_val}, got {f_val}",
            details={"field": name, "value": str(val), "min_val": min_val},
        )
    return f_val


def freeze_transition_metadata(val: Any) -> Any:
    """Recursively freeze JSON-safe dicts and lists into MappingProxyType and tuple."""
    if isinstance(val, (dict, MappingProxyType)):
        return MappingProxyType({k: freeze_transition_metadata(v) for k, v in val.items()})
    elif isinstance(val, list):
        return tuple(freeze_transition_metadata(v) for v in val)
    return val


def unfreeze_transition_metadata(val: Any) -> Any:
    """Recursively unfreeze MappingProxyType and tuples into dicts and lists for serialization."""
    if isinstance(val, (MappingProxyType, dict)):
        return {k: unfreeze_transition_metadata(v) for k, v in val.items()}
    elif isinstance(val, (tuple, list)):
        return [unfreeze_transition_metadata(v) for v in val]
    return val


class PersistentObjectTransition(BaseModel):
    """Specification of a persistent visual entity transitioning across scenes."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    semantic_key: str = Field(..., min_length=1, description="Canonical semantic key from ConceptRegistry")
    concept_id: str | None = Field(default=None, description="ConceptRegistry concept_id for provenance")
    from_node_id: str = Field(..., min_length=1, description="SceneNode ID in previous scene")
    to_node_id: str = Field(..., min_length=1, description="SceneNode ID in next scene")
    from_node: str | None = Field(default=None, description="Compat alias for from_node_id")
    to_node: str | None = Field(default=None, description="Compat alias for to_node_id")
    requested_operation: TransitionOperation = Field(
        default=TransitionOperation.MOVE,
        description="Transition operation requested by planner/compiler",
    )
    effective_operation: TransitionOperation = Field(
        default=TransitionOperation.MOVE,
        description="Negotiated operation actually executed by renderer backend",
    )
    operation: TransitionOperation | None = Field(default=None, description="Compat alias for effective_operation")
    source_rect: Rect = Field(..., description="Solved bounding rect in previous LayoutGraph")
    target_rect: Rect = Field(..., description="Solved bounding rect in next LayoutGraph")
    source_zone: str = Field(default="CONTENT", min_length=1, description="Source layout zone")
    target_zone: str = Field(default="CONTENT", min_length=1, description="Target layout zone")
    displacement_x: float = Field(default=0.0, description="Horizontal displacement (target.cx - source.cx)")
    displacement_y: float = Field(default=0.0, description="Vertical displacement (target.cy - source.cy)")
    scale_x: float = Field(default=1.0, gt=0.0, description="Horizontal scale factor (target.w / source.w)")
    scale_y: float = Field(default=1.0, gt=0.0, description="Vertical scale factor (target.h / source.h)")
    fallback_reason: str | None = Field(default=None, description="Provenance explaining negotiation fallback")
    metadata: MappingProxyType[str, Any] = Field(
        default_factory=lambda: MappingProxyType({}),
        description="Deeply immutable JSON-safe metadata",
    )

    @field_validator("metadata", mode="before")
    @classmethod
    def _validate_metadata(cls, v: Any) -> MappingProxyType[str, Any]:
        if v is None:
            return MappingProxyType({})
        if isinstance(v, MappingProxyType):
            raw_dict = dict(v)
            try:
                checked = ensure_json_safe_dict(raw_dict, path="metadata")
            except ValueError as e:
                raise TransitionInvalidInputError(f"metadata not JSON-safe: {e}") from e
            return freeze_transition_metadata(checked)
        if isinstance(v, dict):
            try:
                checked = ensure_json_safe_dict(v, path="metadata")
            except ValueError as e:
                raise TransitionInvalidInputError(f"metadata not JSON-safe: {e}") from e
            return freeze_transition_metadata(checked)
        raise TransitionInvalidInputError(
            f"metadata must be a dictionary or MappingProxyType, got {type(v).__name__}",
            details={"type": type(v).__name__},
        )

    @field_serializer("metadata", mode="plain")
    def _serialize_metadata(self, v: MappingProxyType[str, Any]) -> dict[str, Any]:
        return unfreeze_transition_metadata(v)

    @field_validator("displacement_x", "displacement_y", mode="before")
    @classmethod
    def _validate_displacement(cls, v: Any, info: ValidationInfo) -> float:
        return _check_finite_float(v, info.field_name or "displacement", min_val=None)

    @field_validator("scale_x", "scale_y", mode="before")
    @classmethod
    def _validate_scale(cls, v: Any, info: ValidationInfo) -> float:
        val = _check_finite_float(v, info.field_name or "scale", min_val=0.0001)
        if val <= 0.0:
            raise TransitionGeometryError(f"Scale factor '{info.field_name}' must be strictly positive, got {val}")
        return val

    @model_validator(mode="before")
    @classmethod
    def _normalize_compat_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. Alias node IDs
            if "from_node" in data and "from_node_id" in data and data["from_node"] != data["from_node_id"]:
                raise TransitionInvalidInputError("from_node and from_node_id cannot conflict")
            if "from_node" in data and "from_node_id" not in data:
                data["from_node_id"] = data["from_node"]
            if "from_node_id" in data and "from_node" not in data:
                data["from_node"] = data["from_node_id"]

            if "to_node" in data and "to_node_id" in data and data["to_node"] != data["to_node_id"]:
                raise TransitionInvalidInputError("to_node and to_node_id cannot conflict")
            if "to_node" in data and "to_node_id" not in data:
                data["to_node_id"] = data["to_node"]
            if "to_node_id" in data and "to_node" not in data:
                data["to_node"] = data["to_node_id"]

            # 2. Alias operations
            if "operation" in data and "effective_operation" in data and data["operation"] != data["effective_operation"]:
                raise TransitionInvalidInputError("operation and effective_operation cannot conflict")
            if "operation" in data:
                op = data["operation"]
                data.setdefault("requested_operation", op)
                data.setdefault("effective_operation", op)
            elif "effective_operation" in data:
                data.setdefault("operation", data["effective_operation"])
            elif "requested_operation" in data:
                data.setdefault("effective_operation", data["requested_operation"])
                data.setdefault("operation", data["requested_operation"])
            else:
                data.setdefault("requested_operation", TransitionOperation.MOVE)
                data.setdefault("effective_operation", TransitionOperation.MOVE)
                data.setdefault("operation", TransitionOperation.MOVE)

            # 3. Geometry auto-calculation if rects exist and displacements missing
            src = data.get("source_rect")
            tgt = data.get("target_rect")
            if src is not None and tgt is not None:
                src_rect = src if isinstance(src, Rect) else Rect.model_validate(src)
                tgt_rect = tgt if isinstance(tgt, Rect) else Rect.model_validate(tgt)

                if "displacement_x" not in data:
                    data["displacement_x"] = round(tgt_rect.center_x - src_rect.center_x, 4)
                if "displacement_y" not in data:
                    data["displacement_y"] = round(tgt_rect.center_y - src_rect.center_y, 4)
                if "scale_x" not in data:
                    data["scale_x"] = round(tgt_rect.width / src_rect.width, 4)
                if "scale_y" not in data:
                    data["scale_y"] = round(tgt_rect.height / src_rect.height, 4)

        return data

    @model_validator(mode="after")
    def _validate_invariants(self) -> "PersistentObjectTransition":
        if self.from_node != self.from_node_id:
            object.__setattr__(self, "from_node", self.from_node_id)
        if self.to_node != self.to_node_id:
            object.__setattr__(self, "to_node", self.to_node_id)
        if self.operation != self.effective_operation:
            object.__setattr__(self, "operation", self.effective_operation)
        return self

    @property
    def is_fallback(self) -> bool:
        """Whether capability negotiation triggered a fallback from requested operation."""
        return self.effective_operation != self.requested_operation


class InterSceneTransitionPlan(BaseModel):
    """Immutable, versioned, first-class inter-scene transition plan artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    schema_version: Literal["2.1"] = Field(
        default=V2_TRANSITION_SCHEMA_VERSION,
        description="Transition artifact schema version",
    )
    transition_id: str = Field(..., min_length=1, description="Deterministic transition identifier")
    from_scene: str = Field(..., min_length=1, description="Source SceneGraph ID")
    to_scene: str = Field(..., min_length=1, description="Target SceneGraph ID")
    duration: float = Field(..., gt=0.0, description="Transition duration in seconds")
    duration_ms: float = Field(..., gt=0.0, description="Transition duration in milliseconds")
    persistent_objects: tuple[PersistentObjectTransition, ...] = Field(
        default_factory=tuple,
        description="Matched persistent objects undergoing cross-scene transform",
    )
    departing_node_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        description="SceneNode IDs in from_scene that do not persist into to_scene",
    )
    entering_node_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        description="SceneNode IDs in to_scene that are newly introduced",
    )
    unmatched_keys: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Semantic keys present on either side that could not be matched",
    )
    diagnostics: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Auditable compiler and negotiation messages",
    )
    metadata: MappingProxyType[str, Any] = Field(
        default_factory=lambda: MappingProxyType({}),
        description="Deeply immutable JSON-safe metadata",
    )

    @property
    def from_scene_id(self) -> str:
        """Alias for from_scene."""
        return self.from_scene

    @property
    def to_scene_id(self) -> str:
        """Alias for to_scene."""
        return self.to_scene

    @field_validator("metadata", mode="before")
    @classmethod
    def _validate_metadata(cls, v: Any) -> MappingProxyType[str, Any]:
        if v is None:
            return MappingProxyType({})
        if isinstance(v, MappingProxyType):
            raw_dict = dict(v)
            checked = ensure_json_safe_dict(raw_dict, path="metadata")
            return freeze_transition_metadata(checked)
        if isinstance(v, dict):
            checked = ensure_json_safe_dict(v, path="metadata")
            return freeze_transition_metadata(checked)
        raise TransitionInvalidInputError(
            f"metadata must be a dictionary or MappingProxyType, got {type(v).__name__}",
            details={"type": type(v).__name__},
        )

    @field_serializer("metadata", mode="plain")
    def _serialize_metadata(self, v: MappingProxyType[str, Any]) -> dict[str, Any]:
        return unfreeze_transition_metadata(v)

    @field_validator("duration", mode="before")
    @classmethod
    def _validate_duration(cls, v: Any) -> float:
        val = _check_finite_float(v, "duration", min_val=0.0001)
        if val <= 0.0:
            raise TransitionInvalidInputError(f"duration must be strictly positive, got {val}")
        return val

    @field_validator("duration_ms", mode="before")
    @classmethod
    def _validate_duration_ms(cls, v: Any) -> float:
        val = _check_finite_float(v, "duration_ms", min_val=0.1)
        if val <= 0.0:
            raise TransitionInvalidInputError(f"duration_ms must be strictly positive, got {val}")
        return val

    @model_validator(mode="before")
    @classmethod
    def _normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. Alias scenes
            if "from_scene_id" in data and "from_scene" not in data:
                data["from_scene"] = data["from_scene_id"]
            if "to_scene_id" in data and "to_scene" not in data:
                data["to_scene"] = data["to_scene_id"]

            # 2. Sync duration and duration_ms
            if "duration" in data and "duration_ms" not in data:
                d = _check_finite_float(data["duration"], "duration", min_val=0.0001)
                data["duration_ms"] = round(d * 1000.0, 4)
            elif "duration_ms" in data and "duration" not in data:
                d_ms = _check_finite_float(data["duration_ms"], "duration_ms", min_val=0.1)
                data["duration"] = round(d_ms / 1000.0, 6)

            # 3. List to tuple conversions for frozen model
            for k in ("persistent_objects", "departing_node_ids", "entering_node_ids", "unmatched_keys", "diagnostics"):
                if k in data and isinstance(data[k], list):
                    data[k] = tuple(data[k])

        return data

    @model_validator(mode="after")
    def _validate_plan_invariants(self) -> "InterSceneTransitionPlan":
        # 1. from_scene != to_scene
        if self.from_scene == self.to_scene:
            raise TransitionInvalidInputError(
                f"from_scene and to_scene cannot be identical: '{self.from_scene}'",
                details={"from_scene": self.from_scene, "to_scene": self.to_scene},
            )

        # 2. duration and duration_ms agreement
        if abs(self.duration * 1000.0 - self.duration_ms) > 1e-2:
            raise TransitionInvalidInputError(
                f"duration ({self.duration}s) and duration_ms ({self.duration_ms}ms) disagree materially",
                details={"duration": self.duration, "duration_ms": self.duration_ms},
            )

        # 3. Unique semantic_keys in persistent_objects
        seen_keys: set[str] = set()
        for p in self.persistent_objects:
            if p.semantic_key in seen_keys:
                raise TransitionInvalidInputError(
                    f"Duplicate persistent object semantic key '{p.semantic_key}'",
                    details={"semantic_key": p.semantic_key},
                )
            seen_keys.add(p.semantic_key)

        # 4. Canonical sorting
        sorted_objs = tuple(sorted(self.persistent_objects, key=lambda x: x.semantic_key))
        if sorted_objs != self.persistent_objects:
            object.__setattr__(self, "persistent_objects", sorted_objs)

        sorted_departing = tuple(sorted(self.departing_node_ids))
        if sorted_departing != self.departing_node_ids:
            object.__setattr__(self, "departing_node_ids", sorted_departing)

        sorted_entering = tuple(sorted(self.entering_node_ids))
        if sorted_entering != self.entering_node_ids:
            object.__setattr__(self, "entering_node_ids", sorted_entering)

        sorted_unmatched = tuple(sorted(self.unmatched_keys))
        if sorted_unmatched != self.unmatched_keys:
            object.__setattr__(self, "unmatched_keys", sorted_unmatched)

        return self

    def get_persistent_object(self, semantic_key: str) -> PersistentObjectTransition | None:
        """Find persistent object transition by its canonical semantic key."""
        for p in self.persistent_objects:
            if p.semantic_key == semantic_key:
                return p
        return None

    def get_persistent_object_by_from_node(self, node_id: str) -> PersistentObjectTransition | None:
        """Find persistent object transition by previous scene node ID."""
        for p in self.persistent_objects:
            if p.from_node_id == node_id:
                return p
        return None

    def get_persistent_object_by_to_node(self, node_id: str) -> PersistentObjectTransition | None:
        """Find persistent object transition by next scene node ID."""
        for p in self.persistent_objects:
            if p.to_node_id == node_id:
                return p
        return None

    def to_canonical_json(self) -> str:
        """Deterministic canonical JSON serialization."""
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, json_str: str) -> "InterSceneTransitionPlan":
        """Deserialize from canonical JSON string with full invariant verification."""
        import json
        data = json.loads(json_str)
        return cls.model_validate(data)
