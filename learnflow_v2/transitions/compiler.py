"""Compiler for first-class V2 InterSceneTransitionPlan artifacts."""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from learnflow_v2.concepts.registry import ConceptRegistry
from learnflow_v2.core.errors import (
    ConceptRegistryUnknownRefError,
    TransitionInvalidInputError,
    TransitionSemanticMismatchError,
    TransitionUnregisteredSemanticKeyError,
)
from learnflow_v2.layout.schema import LayoutBox, LayoutGraph
from learnflow_v2.scenegraph.schema import SceneGraph, SceneNode
from learnflow_v2.transitions.capabilities import (
    DEFAULT_TRANSITION_CAPABILITIES,
    RendererTransitionCapabilities,
    negotiate_operation_capability,
)
from learnflow_v2.transitions.schema import (
    InterSceneTransitionPlan,
    PersistentObjectTransition,
    TransitionOperation,
)


class TransitionPolicy(BaseModel):
    """Deterministic cross-scene transition compilation policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    default_duration: float = Field(default=0.5, gt=0.0)
    min_duration: float = Field(default=0.05, gt=0.0)
    max_duration: float = Field(default=10.0, gt=0.0)
    detect_resize: bool = False
    allow_resize: bool = False
    require_geometry_change: bool = False

    @field_validator("default_duration", "min_duration", "max_duration", mode="before")
    @classmethod
    def _finite_duration(cls, value: Any, info: ValidationInfo) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TransitionInvalidInputError(f"{info.field_name} must be a finite positive number")
        result = float(value)
        if not math.isfinite(result) or result <= 0.0:
            raise TransitionInvalidInputError(f"{info.field_name} must be finite and > 0")
        return result

    @model_validator(mode="after")
    def _validate_bounds(self) -> "TransitionPolicy":
        if self.min_duration > self.max_duration:
            raise TransitionInvalidInputError("min_duration cannot exceed max_duration")
        if not self.min_duration <= self.default_duration <= self.max_duration:
            raise TransitionInvalidInputError("default_duration must lie within [min_duration, max_duration]")
        if self.allow_resize and not self.detect_resize:
            raise TransitionInvalidInputError("allow_resize=True requires detect_resize=True")
        return self


DEFAULT_TRANSITION_POLICY = TransitionPolicy()


def _resolve_registry_identity(
    registry: ConceptRegistry,
    raw_reference: str,
    *,
    scene_id: str,
    node_id: str,
    source: str,
):
    try:
        entry = registry.resolve(raw_reference)
    except ConceptRegistryUnknownRefError as exc:
        raise TransitionUnregisteredSemanticKeyError(
            f"Semantic identity '{raw_reference}' for node '{node_id}' in scene '{scene_id}' "
            f"from {source} is not registered in ConceptRegistry",
            details={
                "scene_id": scene_id,
                "node_id": node_id,
                "semantic_identity": raw_reference,
                "source": source,
            },
        ) from exc

    # Cross-scene matching must never promote a label/alias into canonical identity.
    if source.endswith("semantic_key") and raw_reference.strip() != entry.canonical_key:
        raise TransitionSemanticMismatchError(
            f"{source} for node '{node_id}' must be canonical key '{entry.canonical_key}', "
            f"not alias/label '{raw_reference}'",
            details={"scene_id": scene_id, "node_id": node_id, "source": source},
        )
    if source == "SceneNode.concept_ref" and raw_reference.strip() != entry.concept_id:
        raise TransitionSemanticMismatchError(
            f"SceneNode.concept_ref for node '{node_id}' must be concept_id '{entry.concept_id}', "
            f"not alias/label '{raw_reference}'",
            details={"scene_id": scene_id, "node_id": node_id, "source": source},
        )
    return entry


def _canonical_identity_for_box(
    box: LayoutBox,
    scene_node: SceneNode | None,
    registry: ConceptRegistry,
    *,
    scene_id: str,
) -> tuple[str, Any] | None:
    """Resolve one layout box to exactly one canonical registry concept or None."""
    candidates: list[tuple[str, Any]] = []

    if box.semantic_key is not None:
        candidates.append(
            (
                "LayoutBox.semantic_key",
                _resolve_registry_identity(
                    registry,
                    box.semantic_key,
                    scene_id=scene_id,
                    node_id=box.node_id,
                    source="LayoutBox.semantic_key",
                ),
            )
        )

    if scene_node is not None and scene_node.semantic_key is not None:
        candidates.append(
            (
                "SceneNode.semantic_key",
                _resolve_registry_identity(
                    registry,
                    scene_node.semantic_key,
                    scene_id=scene_id,
                    node_id=box.node_id,
                    source="SceneNode.semantic_key",
                ),
            )
        )
        candidates.append(
            (
                "SceneNode.concept_ref",
                _resolve_registry_identity(
                    registry,
                    scene_node.concept_ref or "",
                    scene_id=scene_id,
                    node_id=box.node_id,
                    source="SceneNode.concept_ref",
                ),
            )
        )

    if not candidates:
        return None

    canonical_keys = {entry.canonical_key for _, entry in candidates}
    concept_ids = {entry.concept_id for _, entry in candidates}
    if len(canonical_keys) != 1 or len(concept_ids) != 1:
        raise TransitionSemanticMismatchError(
            f"Conflicting semantic identities for node '{box.node_id}' in scene '{scene_id}'",
            details={
                "node_id": box.node_id,
                "scene_id": scene_id,
                "candidates": [
                    {"source": source, "canonical_key": entry.canonical_key, "concept_id": entry.concept_id}
                    for source, entry in candidates
                ],
            },
        )

    entry = candidates[0][1]
    return entry.canonical_key, entry


def _build_semantic_index(
    layout: LayoutGraph,
    scene_graph: SceneGraph | None,
    registry: ConceptRegistry,
) -> dict[str, list[tuple[LayoutBox, Any]]]:
    if scene_graph is not None and scene_graph.scene_id != layout.scene_id:
        raise TransitionInvalidInputError(
            f"SceneGraph '{scene_graph.scene_id}' does not match LayoutGraph '{layout.scene_id}'"
        )

    scene_nodes: dict[str, SceneNode] = {}
    if scene_graph is not None:
        scene_nodes = {node.id: node for node in scene_graph.nodes}
        extra_layout_ids = sorted({box.node_id for box in layout.boxes} - set(scene_nodes))
        if extra_layout_ids:
            raise TransitionSemanticMismatchError(
                f"LayoutGraph '{layout.scene_id}' contains boxes not present in its SceneGraph",
                details={"extra_layout_node_ids": extra_layout_ids},
            )

    result: dict[str, list[tuple[LayoutBox, Any]]] = {}
    for box in layout.boxes:
        resolved = _canonical_identity_for_box(
            box,
            scene_nodes.get(box.node_id),
            registry,
            scene_id=layout.scene_id,
        )
        if resolved is None:
            continue
        canonical_key, entry = resolved
        result.setdefault(canonical_key, []).append((box, entry))
    return result


def _resolve_duration(
    duration: float | None,
    duration_ms: float | None,
    policy: TransitionPolicy,
    capabilities: RendererTransitionCapabilities,
) -> tuple[float, list[str]]:
    if duration is not None and duration_ms is not None:
        if (
            isinstance(duration, bool)
            or isinstance(duration_ms, bool)
            or not isinstance(duration, (int, float))
            or not isinstance(duration_ms, (int, float))
            or not math.isfinite(float(duration))
            or not math.isfinite(float(duration_ms))
        ):
            raise TransitionInvalidInputError("duration and duration_ms must be finite real numbers")
        if duration <= 0.0 or duration_ms <= 0.0:
            raise TransitionInvalidInputError("duration and duration_ms must be positive")
        if abs(float(duration) * 1000.0 - float(duration_ms)) > 1e-3:
            raise TransitionInvalidInputError("duration and duration_ms disagree")
        requested = float(duration)
    elif duration is not None:
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(float(duration)) or duration <= 0.0:
            raise TransitionInvalidInputError("duration must be finite and > 0")
        requested = float(duration)
    elif duration_ms is not None:
        if isinstance(duration_ms, bool) or not isinstance(duration_ms, (int, float)) or not math.isfinite(float(duration_ms)) or duration_ms <= 0.0:
            raise TransitionInvalidInputError("duration_ms must be finite and > 0")
        requested = float(duration_ms) / 1000.0
    else:
        requested = policy.default_duration

    lower = max(policy.min_duration, capabilities.min_duration)
    upper = min(policy.max_duration, capabilities.max_duration)
    if lower > upper:
        raise TransitionInvalidInputError(
            "Transition policy and renderer capability duration ranges do not overlap"
        )
    effective = min(max(requested, lower), upper)
    diagnostics: list[str] = []
    if abs(effective - requested) > 1e-4:
        diagnostics.append(f"DURATION_CLAMPED:{requested:.6f}->{effective:.6f}")
    return effective, diagnostics


def compile_inter_scene_transition(
    from_layout: LayoutGraph,
    to_layout: LayoutGraph,
    concept_registry: ConceptRegistry,
    from_scene_graph: SceneGraph | None = None,
    to_scene_graph: SceneGraph | None = None,
    duration: float | None = None,
    duration_ms: float | None = None,
    capabilities: RendererTransitionCapabilities | None = None,
    policy: TransitionPolicy | None = None,
    transition_id: str | None = None,
) -> InterSceneTransitionPlan:
    """Compile deterministic semantic persistence between two consecutive layouts."""
    if not isinstance(from_layout, LayoutGraph) or not isinstance(to_layout, LayoutGraph):
        raise TransitionInvalidInputError("from_layout and to_layout must be LayoutGraph instances")
    if from_layout.scene_id == to_layout.scene_id:
        raise TransitionInvalidInputError("from_layout and to_layout must have distinct scene IDs")
    if not isinstance(concept_registry, ConceptRegistry):
        raise TransitionInvalidInputError("concept_registry must be an authoritative ConceptRegistry")

    effective_policy = policy or DEFAULT_TRANSITION_POLICY
    effective_capabilities = capabilities or DEFAULT_TRANSITION_CAPABILITIES
    effective_duration, diagnostics = _resolve_duration(
        duration, duration_ms, effective_policy, effective_capabilities
    )

    from_index = _build_semantic_index(from_layout, from_scene_graph, concept_registry)
    to_index = _build_semantic_index(to_layout, to_scene_graph, concept_registry)

    from_keys = set(from_index)
    to_keys = set(to_index)
    ambiguous_keys: set[str] = set()
    for key in sorted(from_keys | to_keys):
        source_count = len(from_index.get(key, []))
        target_count = len(to_index.get(key, []))
        if source_count > 1 or target_count > 1:
            ambiguous_keys.add(key)
            diagnostics.append(
                f"AMBIGUOUS_SEMANTIC_KEY:{key}:from={source_count}:to={target_count}"
            )

    persistent_keys = sorted((from_keys & to_keys) - ambiguous_keys)
    unmatched_keys = set((from_keys ^ to_keys) | ambiguous_keys)
    persistent: list[PersistentObjectTransition] = []
    matched_from: set[str] = set()
    matched_to: set[str] = set()

    for key in persistent_keys:
        from_box, entry = from_index[key][0]
        to_box, _ = to_index[key][0]

        source_norm_w = from_box.rect.width / from_layout.frame_width
        source_norm_h = from_box.rect.height / from_layout.frame_height
        target_norm_w = to_box.rect.width / to_layout.frame_width
        target_norm_h = to_box.rect.height / to_layout.frame_height
        source_norm_cx = from_box.rect.center_x / from_layout.frame_width
        source_norm_cy = from_box.rect.center_y / from_layout.frame_height
        target_norm_cx = to_box.rect.center_x / to_layout.frame_width
        target_norm_cy = to_box.rect.center_y / to_layout.frame_height

        dimension_changed = abs(target_norm_w / source_norm_w - 1.0) > 1e-3 or abs(target_norm_h / source_norm_h - 1.0) > 1e-3
        position_changed = abs(target_norm_cx - source_norm_cx) > 1e-3 or abs(target_norm_cy - source_norm_cy) > 1e-3

        if effective_policy.require_geometry_change and not (dimension_changed or position_changed):
            unmatched_keys.add(key)
            diagnostics.append(f"STATIC_PERSISTENT_CONCEPT_SKIPPED:{key}")
            continue

        requested = (
            TransitionOperation.RESIZE
            if dimension_changed and effective_policy.detect_resize and effective_policy.allow_resize
            else TransitionOperation.MOVE
        )
        effective, fallback_reason = negotiate_operation_capability(requested, effective_capabilities)
        if fallback_reason:
            diagnostics.append(f"{key}:{fallback_reason}")

        persistent.append(
            PersistentObjectTransition(
                transition_item_id=f"{from_layout.scene_id}__{to_layout.scene_id}::{key}",
                semantic_key=key,
                concept_id=entry.concept_id,
                from_node_id=from_box.node_id,
                to_node_id=to_box.node_id,
                requested_operation=requested,
                effective_operation=effective,
                fallback_reason=fallback_reason,
                source_rect=from_box.rect,
                target_rect=to_box.rect,
                source_frame_width=from_layout.frame_width,
                source_frame_height=from_layout.frame_height,
                target_frame_width=to_layout.frame_width,
                target_frame_height=to_layout.frame_height,
                source_zone=from_box.zone,
                target_zone=to_box.zone,
            )
        )
        matched_from.add(from_box.node_id)
        matched_to.add(to_box.node_id)

    departing = tuple(sorted(box.node_id for box in from_layout.boxes if box.node_id not in matched_from))
    entering = tuple(sorted(box.node_id for box in to_layout.boxes if box.node_id not in matched_to))
    plan_id = (transition_id or f"{from_layout.scene_id}__{to_layout.scene_id}").strip()
    if not plan_id:
        raise TransitionInvalidInputError("transition_id must be non-empty")

    return InterSceneTransitionPlan(
        schema_version="2.1",
        transition_id=plan_id,
        from_scene=from_layout.scene_id,
        to_scene=to_layout.scene_id,
        duration=effective_duration,
        duration_ms=round(effective_duration * 1000.0, 6),
        persistent_objects=tuple(persistent),
        departing_node_ids=departing,
        entering_node_ids=entering,
        unmatched_keys=tuple(sorted(unmatched_keys)),
        diagnostics=tuple(diagnostics),
        metadata={
            "from_frame_profile_id": from_layout.frame_profile_id,
            "to_frame_profile_id": to_layout.frame_profile_id,
            "from_frame_width": from_layout.frame_width,
            "from_frame_height": from_layout.frame_height,
            "to_frame_width": to_layout.frame_width,
            "to_frame_height": to_layout.frame_height,
        },
    )
