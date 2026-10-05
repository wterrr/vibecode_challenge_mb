"""Deterministic renderer capability negotiation for V2 inter-scene transitions."""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from learnflow_v2.core.errors import TransitionInvalidInputError
from learnflow_v2.transitions.schema import InterSceneTransitionPlan, PersistentObjectTransition, TransitionOperation


class RendererTransitionCapabilities(BaseModel):
    """Immutable capability declaration for a transition backend.

    FADE is mandatory in V2-10 because it is the deterministic fallback required
    when MOVE or an advanced operation is unsupported.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    supported_operations: tuple[TransitionOperation, ...] = Field(
        default=(TransitionOperation.FADE, TransitionOperation.MOVE)
    )
    min_duration: float = Field(default=0.05, gt=0.0)
    max_duration: float = Field(default=10.0, gt=0.0)

    @field_validator("supported_operations", mode="before")
    @classmethod
    def _normalize_operations(cls, value: Any) -> tuple[TransitionOperation, ...]:
        if not isinstance(value, (list, tuple, set, frozenset)):
            raise TransitionInvalidInputError("supported_operations must be a collection")
        parsed: set[TransitionOperation] = set()
        for item in value:
            if isinstance(item, TransitionOperation):
                parsed.add(item)
            elif isinstance(item, str):
                try:
                    parsed.add(TransitionOperation(item.upper()))
                except ValueError as exc:
                    raise TransitionInvalidInputError(f"Unknown transition operation '{item}'") from exc
            else:
                raise TransitionInvalidInputError(
                    f"Invalid transition operation type '{type(item).__name__}'"
                )
        if not parsed:
            raise TransitionInvalidInputError("supported_operations cannot be empty")
        return tuple(sorted(parsed, key=lambda op: op.value))

    @field_validator("min_duration", "max_duration", mode="before")
    @classmethod
    def _validate_duration_bound(cls, value: Any, info: ValidationInfo) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TransitionInvalidInputError(f"{info.field_name} must be a finite positive number")
        result = float(value)
        if not math.isfinite(result) or result <= 0.0:
            raise TransitionInvalidInputError(f"{info.field_name} must be finite and > 0")
        return result

    @model_validator(mode="after")
    def _validate_capabilities(self) -> "RendererTransitionCapabilities":
        if self.min_duration > self.max_duration:
            raise TransitionInvalidInputError("min_duration cannot exceed max_duration")
        if TransitionOperation.FADE not in self.supported_operations:
            raise TransitionInvalidInputError(
                "V2-10 renderer capabilities must support FADE as deterministic fallback"
            )
        return self

    @property
    def supports_move(self) -> bool:
        return TransitionOperation.MOVE in self.supported_operations

    @property
    def supports_resize(self) -> bool:
        return TransitionOperation.RESIZE in self.supported_operations

    @property
    def supports_morph(self) -> bool:
        return TransitionOperation.MORPH in self.supported_operations

    @property
    def supports_fade(self) -> bool:
        return True

    def supports(self, operation: TransitionOperation) -> bool:
        return operation in self.supported_operations


DEFAULT_TRANSITION_CAPABILITIES = RendererTransitionCapabilities(
    supported_operations=(TransitionOperation.FADE, TransitionOperation.MOVE)
)
MINIMAL_TRANSITION_CAPABILITIES = RendererTransitionCapabilities(
    supported_operations=(TransitionOperation.FADE,)
)
FULL_TRANSITION_CAPABILITIES = RendererTransitionCapabilities(
    supported_operations=(
        TransitionOperation.FADE,
        TransitionOperation.MORPH,
        TransitionOperation.MOVE,
        TransitionOperation.RESIZE,
    )
)


def negotiate_operation_capability(
    requested_operation: TransitionOperation,
    capabilities: RendererTransitionCapabilities,
) -> tuple[TransitionOperation, str | None]:
    """Return deterministic effective operation and auditable fallback reason."""
    if capabilities.supports(requested_operation):
        return requested_operation, None

    if requested_operation == TransitionOperation.MOVE:
        return TransitionOperation.FADE, "BACKEND_UNSUPPORTED_MOVE"

    if requested_operation == TransitionOperation.RESIZE:
        if capabilities.supports_move:
            return TransitionOperation.MOVE, "BACKEND_UNSUPPORTED_RESIZE"
        return TransitionOperation.FADE, "BACKEND_UNSUPPORTED_RESIZE"

    if requested_operation == TransitionOperation.MORPH:
        if capabilities.supports_move:
            return TransitionOperation.MOVE, "BACKEND_UNSUPPORTED_MORPH"
        return TransitionOperation.FADE, "BACKEND_UNSUPPORTED_MORPH"

    raise TransitionInvalidInputError("FADE must be supported by every V2-10 transition backend")


def negotiate_transition_plan(
    plan: InterSceneTransitionPlan,
    capabilities: RendererTransitionCapabilities,
) -> InterSceneTransitionPlan:
    """Return a new plan negotiated against backend capabilities without mutating the source plan."""
    duration = min(max(plan.duration, capabilities.min_duration), capabilities.max_duration)
    diagnostics = list(plan.diagnostics)

    def _append_diagnostic_once(message: str) -> None:
        if message not in diagnostics:
            diagnostics.append(message)

    if abs(duration - plan.duration) > 1e-4:
        _append_diagnostic_once(f"DURATION_CLAMPED:{plan.duration:.6f}->{duration:.6f}")

    persistent: list[PersistentObjectTransition] = []
    for item in plan.persistent_objects:
        effective, reason = negotiate_operation_capability(item.requested_operation, capabilities)
        persistent.append(
            PersistentObjectTransition(
                transition_item_id=item.transition_item_id,
                semantic_key=item.semantic_key,
                concept_id=item.concept_id,
                from_node_id=item.from_node_id,
                to_node_id=item.to_node_id,
                requested_operation=item.requested_operation,
                effective_operation=effective,
                fallback_reason=reason,
                source_rect=item.source_rect,
                target_rect=item.target_rect,
                source_frame_width=item.source_frame_width,
                source_frame_height=item.source_frame_height,
                target_frame_width=item.target_frame_width,
                target_frame_height=item.target_frame_height,
                source_zone=item.source_zone,
                target_zone=item.target_zone,
                normalized_displacement_x=item.normalized_displacement_x,
                normalized_displacement_y=item.normalized_displacement_y,
                normalized_scale_x=item.normalized_scale_x,
                normalized_scale_y=item.normalized_scale_y,
                metadata=item.metadata,
            )
        )
        if reason:
            _append_diagnostic_once(f"{item.semantic_key}:{reason}")

    return InterSceneTransitionPlan(
        schema_version=plan.schema_version,
        transition_id=plan.transition_id,
        from_scene=plan.from_scene,
        to_scene=plan.to_scene,
        duration=duration,
        duration_ms=round(duration * 1000.0, 6),
        persistent_objects=tuple(persistent),
        departing_node_ids=plan.departing_node_ids,
        entering_node_ids=plan.entering_node_ids,
        unmatched_keys=plan.unmatched_keys,
        diagnostics=tuple(diagnostics),
        metadata=plan.metadata,
    )
