"""Renderer transition capability negotiation for LearnFlow V2.

Allows renderer backends to advertise supported transition operations
(MOVE, RESIZE, MORPH, FADE). Guarantees that unsupported operations
fall back deterministically (e.g. MOVE -> FADE, RESIZE -> MOVE or FADE)
without causing render failures or corrupting scene-local MotionPlans.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from learnflow_v2.core.errors import TransitionInvalidInputError, TransitionUnsupportedCapabilityError
from learnflow_v2.transitions.schema import (
    TIER_1_TRANSITION_OPERATIONS,
    InterSceneTransitionPlan,
    PersistentObjectTransition,
    TransitionOperation,
)


class RendererTransitionCapabilities(BaseModel):
    """Advertised transition capabilities of a renderer backend."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    supported_operations: frozenset[TransitionOperation] = Field(
        default=frozenset(TIER_1_TRANSITION_OPERATIONS),
        description="Set of transition operations supported natively by this backend",
    )
    min_duration: float = Field(default=0.05, gt=0.0, description="Minimum supported transition duration (s)")
    max_duration: float = Field(default=10.0, gt=0.0, description="Maximum supported transition duration (s)")

    @field_validator("supported_operations", mode="before")
    @classmethod
    def _validate_ops(cls, v: Any) -> frozenset[TransitionOperation]:
        if isinstance(v, (set, list, tuple, frozenset)):
            ops = set()
            for item in v:
                if isinstance(item, TransitionOperation):
                    ops.add(item)
                elif isinstance(item, str):
                    try:
                        ops.add(TransitionOperation(item.upper()))
                    except ValueError:
                        raise TransitionInvalidInputError(f"Unknown transition operation '{item}'")
                else:
                    raise TransitionInvalidInputError(f"Invalid operation type '{type(item).__name__}'")
            if not ops:
                raise TransitionInvalidInputError("supported_operations cannot be empty")
            return frozenset(ops)
        raise TransitionInvalidInputError(f"supported_operations must be a collection, got {type(v).__name__}")

    @model_validator(mode="after")
    def _validate_bounds(self) -> "RendererTransitionCapabilities":
        if self.min_duration > self.max_duration:
            raise TransitionInvalidInputError(
                f"min_duration ({self.min_duration}) cannot exceed max_duration ({self.max_duration})"
            )
        return self

    @property
    def supports_move(self) -> bool:
        return TransitionOperation.MOVE in self.supported_operations

    @property
    def supports_fade(self) -> bool:
        return TransitionOperation.FADE in self.supported_operations

    @property
    def supports_resize(self) -> bool:
        return TransitionOperation.RESIZE in self.supported_operations

    @property
    def supports_morph(self) -> bool:
        return TransitionOperation.MORPH in self.supported_operations

    def supports(self, op: TransitionOperation) -> bool:
        return op in self.supported_operations


# Standard capability presets
DEFAULT_TRANSITION_CAPABILITIES = RendererTransitionCapabilities(
    supported_operations=frozenset({TransitionOperation.MOVE, TransitionOperation.FADE})
)
"""Standard Tier-1 baseline capabilities supporting MOVE and deterministic FADE fallback."""

MINIMAL_TRANSITION_CAPABILITIES = RendererTransitionCapabilities(
    supported_operations=frozenset({TransitionOperation.FADE})
)
"""Minimal fallback renderer supporting only deterministic FADE transitions."""

FULL_TRANSITION_CAPABILITIES = RendererTransitionCapabilities(
    supported_operations=frozenset({
        TransitionOperation.MOVE,
        TransitionOperation.RESIZE,
        TransitionOperation.MORPH,
        TransitionOperation.FADE,
    })
)
"""Advanced renderer supporting Tier-1 and Tier-2 operations."""


def negotiate_operation_capability(
    requested_op: TransitionOperation,
    capabilities: RendererTransitionCapabilities,
) -> tuple[TransitionOperation, str | None]:
    """Negotiate a single requested transition operation against backend capabilities.

    Rules:
    - If requested operation is supported, return (requested_op, None).
    - If RESIZE/MORPH requested but unsupported:
        - fall back to MOVE if MOVE supported;
        - else fall back to FADE if FADE supported;
        - else raise TransitionUnsupportedCapabilityError.
    - If MOVE requested but unsupported:
        - fall back to FADE if FADE supported;
        - else raise TransitionUnsupportedCapabilityError.
    - If FADE requested:
        - return FADE if supported, else raise TransitionUnsupportedCapabilityError.
    """
    if capabilities.supports(requested_op):
        return (requested_op, None)

    # Fallback ladder for Tier-2 operations
    if requested_op in {TransitionOperation.RESIZE, TransitionOperation.MORPH}:
        if capabilities.supports_move:
            return (
                TransitionOperation.MOVE,
                f"Renderer capabilities do not support requested operation '{requested_op.value}'; "
                f"fell back to MOVE",
            )
        elif capabilities.supports_fade:
            return (
                TransitionOperation.FADE,
                f"Renderer capabilities do not support requested operation '{requested_op.value}'; "
                f"fell back to deterministic FADE",
            )
        else:
            raise TransitionUnsupportedCapabilityError(
                f"Renderer cannot execute '{requested_op.value}' and supports neither MOVE nor FADE fallback",
                details={"requested_operation": requested_op.value, "supported": [op.value for op in capabilities.supported_operations]},
            )

    # Fallback ladder for Tier-1 MOVE
    if requested_op == TransitionOperation.MOVE:
        if capabilities.supports_fade:
            return (
                TransitionOperation.FADE,
                "Renderer capabilities do not support requested operation 'MOVE'; "
                "fell back to deterministic FADE",
            )
        else:
            raise TransitionUnsupportedCapabilityError(
                "Renderer cannot execute 'MOVE' and does not support FADE fallback",
                details={"requested_operation": requested_op.value, "supported": [op.value for op in capabilities.supported_operations]},
            )

    if requested_op == TransitionOperation.FADE:
        raise TransitionUnsupportedCapabilityError(
            "Renderer does not support FADE transition",
            details={"requested_operation": requested_op.value, "supported": [op.value for op in capabilities.supported_operations]},
        )

    raise TransitionUnsupportedCapabilityError(f"Unsupported transition operation '{requested_op}'")


def negotiate_transition_plan(
    plan: InterSceneTransitionPlan,
    capabilities: RendererTransitionCapabilities,
) -> InterSceneTransitionPlan:
    """Negotiate an existing InterSceneTransitionPlan against renderer capabilities.

    Returns a new immutable plan where every persistent object's effective_operation
    and fallback_reason reflect the negotiated backend capabilities, and duration
    is verified against capability bounds.
    """
    # 1. Check duration bounds
    clamped_duration = min(max(plan.duration, capabilities.min_duration), capabilities.max_duration)
    duration_changed = abs(clamped_duration - plan.duration) > 1e-4

    new_diagnostics = list(plan.diagnostics)
    if duration_changed:
        new_diagnostics.append(
            f"Transition duration clamped from {plan.duration:.3f}s to {clamped_duration:.3f}s "
            f"to meet backend limits [{capabilities.min_duration:.3f}s, {capabilities.max_duration:.3f}s]"
        )

    # 2. Negotiate each persistent object
    negotiated_objects: list[PersistentObjectTransition] = []
    for p in plan.persistent_objects:
        eff_op, fallback_reason = negotiate_operation_capability(p.requested_operation, capabilities)
        if eff_op != p.effective_operation or fallback_reason != p.fallback_reason:
            negotiated_p = PersistentObjectTransition(
                semantic_key=p.semantic_key,
                concept_id=p.concept_id,
                from_node_id=p.from_node_id,
                to_node_id=p.to_node_id,
                requested_operation=p.requested_operation,
                effective_operation=eff_op,
                source_rect=p.source_rect,
                target_rect=p.target_rect,
                source_zone=p.source_zone,
                target_zone=p.target_zone,
                displacement_x=p.displacement_x,
                displacement_y=p.displacement_y,
                scale_x=p.scale_x,
                scale_y=p.scale_y,
                fallback_reason=fallback_reason,
                metadata=p.metadata,
            )
            negotiated_objects.append(negotiated_p)
            if fallback_reason:
                new_diagnostics.append(f"Object '{p.semantic_key}': {fallback_reason}")
        else:
            negotiated_objects.append(p)

    return InterSceneTransitionPlan(
        schema_version=plan.schema_version,
        transition_id=plan.transition_id,
        from_scene=plan.from_scene,
        to_scene=plan.to_scene,
        duration=clamped_duration,
        duration_ms=round(clamped_duration * 1000.0, 4),
        persistent_objects=tuple(negotiated_objects),
        departing_node_ids=plan.departing_node_ids,
        entering_node_ids=plan.entering_node_ids,
        unmatched_keys=plan.unmatched_keys,
        diagnostics=tuple(new_diagnostics),
        metadata=plan.metadata,
    )
