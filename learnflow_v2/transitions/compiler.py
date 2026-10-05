"""First-class cross-scene transition compiler for LearnFlow V2.

Compiles an InterSceneTransitionPlan from:
  previous LayoutGraph + next LayoutGraph + ConceptRegistry + continuity policy
Produces an immutable, versioned, canonically serializable artifact with:
  - semantic persistent-object matching validated by ConceptRegistry
  - MOVE as the authoritative baseline operation
  - renderer capability negotiation with deterministic FADE fallback
  - clean separation from scene-local MotionPlan.
"""

from __future__ import annotations

import math
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from learnflow_v2.concepts.registry import ConceptRegistry
from learnflow_v2.core.errors import (
    ConceptRegistryUnknownRefError,
    TransitionInvalidInputError,
    TransitionUnregisteredSemanticKeyError,
)
from learnflow_v2.layout.schema import LayoutBox, LayoutGraph
from learnflow_v2.scenegraph.schema import SceneGraph
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
    """Continuity and transition compilation policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    default_duration: float = Field(default=0.5, gt=0.0, description="Default transition duration (s)")
    min_duration: float = Field(default=0.05, gt=0.0, description="Minimum allowed duration (s)")
    max_duration: float = Field(default=10.0, gt=0.0, description="Maximum allowed duration (s)")
    detect_resize: bool = Field(default=False, description="Whether dimension changes request RESIZE")
    allow_resize: bool = Field(default=False, description="Whether RESIZE is permitted in requested operations")
    allow_morph: bool = Field(default=False, description="Whether MORPH is permitted in requested operations")
    require_geometry_change: bool = Field(
        default=False,
        description="Whether persistent objects require non-zero displacement",
    )


DEFAULT_TRANSITION_POLICY = TransitionPolicy()


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
    """Compile an InterSceneTransitionPlan between two consecutive LayoutGraphs.

    Enforces:
    1. ConceptRegistry is strictly authoritative:
       - persistent matching is based solely on canonical semantic key identity;
       - matching by label, node ID equality, or layout position is strictly rejected;
       - candidate semantic keys must resolve in ConceptRegistry (no silent matches of unknown keys).
    2. Baseline operation is MOVE:
       - negotiated against capabilities (e.g. falls back to deterministic FADE if MOVE unsupported).
    3. Distinct from scene-local MotionPlan:
       - purely cross-scene lifecycle artifact.
    """
    # 1. Validate inputs
    if not isinstance(from_layout, LayoutGraph):
        raise TransitionInvalidInputError(
            f"from_layout must be a LayoutGraph, got {type(from_layout).__name__}"
        )
    if not isinstance(to_layout, LayoutGraph):
        raise TransitionInvalidInputError(
            f"to_layout must be a LayoutGraph, got {type(to_layout).__name__}"
        )
    if from_layout.scene_id == to_layout.scene_id:
        raise TransitionInvalidInputError(
            f"from_layout and to_layout must have distinct scene_ids, got '{from_layout.scene_id}'"
        )
    if not isinstance(concept_registry, ConceptRegistry):
        raise TransitionInvalidInputError(
            f"concept_registry must be an authoritative ConceptRegistry instance, got {type(concept_registry).__name__}"
        )

    eff_policy = policy or DEFAULT_TRANSITION_POLICY
    eff_caps = capabilities or DEFAULT_TRANSITION_CAPABILITIES

    # 2. Determine duration
    if duration is not None:
        if not math.isfinite(duration) or duration <= 0.0:
            raise TransitionInvalidInputError(f"duration must be positive and finite, got {duration}")
        target_duration = float(duration)
    elif duration_ms is not None:
        if not math.isfinite(duration_ms) or duration_ms <= 0.0:
            raise TransitionInvalidInputError(f"duration_ms must be positive and finite, got {duration_ms}")
        target_duration = float(duration_ms) / 1000.0
    else:
        target_duration = eff_policy.default_duration

    # Clamp duration to capabilities and policy bounds
    effective_duration = min(
        max(target_duration, eff_caps.min_duration, eff_policy.min_duration),
        eff_caps.max_duration,
        eff_policy.max_duration,
    )

    diagnostics: list[str] = []
    if abs(effective_duration - target_duration) > 1e-4:
        diagnostics.append(
            f"Transition duration adjusted from {target_duration:.3f}s to {effective_duration:.3f}s by capability/policy bounds"
        )

    # 3. Collect node semantics for from_scene
    from_box_map: dict[str, LayoutBox] = {b.node_id: b for b in from_layout.boxes}
    from_node_raw_keys: dict[str, str] = {}

    if from_scene_graph is not None:
        if from_scene_graph.scene_id != from_layout.scene_id:
            raise TransitionInvalidInputError(
                f"from_scene_graph scene_id '{from_scene_graph.scene_id}' does not match from_layout.scene_id '{from_layout.scene_id}'"
            )
        for n in from_scene_graph.nodes:
            if n.semantic_key and n.semantic_key.strip():
                from_node_raw_keys[n.id] = n.semantic_key.strip()
            elif n.concept_ref and n.concept_ref.strip():
                from_node_raw_keys[n.id] = n.concept_ref.strip()

    # Also incorporate LayoutBox semantic keys
    for b in from_layout.boxes:
        if b.semantic_key and b.semantic_key.strip():
            if b.node_id in from_node_raw_keys and from_node_raw_keys[b.node_id] != b.semantic_key.strip():
                # Verify both resolve to same concept
                pass
            from_node_raw_keys.setdefault(b.node_id, b.semantic_key.strip())

    # 4. Collect node semantics for to_scene
    to_box_map: dict[str, LayoutBox] = {b.node_id: b for b in to_layout.boxes}
    to_node_raw_keys: dict[str, str] = {}

    if to_scene_graph is not None:
        if to_scene_graph.scene_id != to_layout.scene_id:
            raise TransitionInvalidInputError(
                f"to_scene_graph scene_id '{to_scene_graph.scene_id}' does not match to_layout.scene_id '{to_layout.scene_id}'"
            )
        for n in to_scene_graph.nodes:
            if n.semantic_key and n.semantic_key.strip():
                to_node_raw_keys[n.id] = n.semantic_key.strip()
            elif n.concept_ref and n.concept_ref.strip():
                to_node_raw_keys[n.id] = n.concept_ref.strip()

    for b in to_layout.boxes:
        if b.semantic_key and b.semantic_key.strip():
            to_node_raw_keys.setdefault(b.node_id, b.semantic_key.strip())

    # 5. Resolve candidate semantic keys against ConceptRegistry
    from_nodes_by_canonical_key: dict[str, list[tuple[str, Any]]] = {}
    for node_id, raw_key in from_node_raw_keys.items():
        try:
            entry = concept_registry.resolve(raw_key)
            from_nodes_by_canonical_key.setdefault(entry.canonical_key, []).append((node_id, entry))
        except ConceptRegistryUnknownRefError:
            raise TransitionUnregisteredSemanticKeyError(
                f"Semantic key '{raw_key}' on node '{node_id}' in scene '{from_layout.scene_id}' "
                f"is not registered in ConceptRegistry",
                details={"node_id": node_id, "semantic_key": raw_key, "scene_id": from_layout.scene_id},
            )

    to_nodes_by_canonical_key: dict[str, list[tuple[str, Any]]] = {}
    for node_id, raw_key in to_node_raw_keys.items():
        try:
            entry = concept_registry.resolve(raw_key)
            to_nodes_by_canonical_key.setdefault(entry.canonical_key, []).append((node_id, entry))
        except ConceptRegistryUnknownRefError:
            raise TransitionUnregisteredSemanticKeyError(
                f"Semantic key '{raw_key}' on node '{node_id}' in scene '{to_layout.scene_id}' "
                f"is not registered in ConceptRegistry",
                details={"node_id": node_id, "semantic_key": raw_key, "scene_id": to_layout.scene_id},
            )

    # 6. Check ambiguity
    from_keys = set(from_nodes_by_canonical_key.keys())
    to_keys = set(to_nodes_by_canonical_key.keys())

    ambiguous_keys: set[str] = set()
    for k, nodes in from_nodes_by_canonical_key.items():
        if len(nodes) > 1:
            ambiguous_keys.add(k)
            diagnostics.append(
                f"Ambiguous semantic key '{k}' in previous scene (used by multiple nodes: {[n[0] for n in nodes]})"
            )
    for k, nodes in to_nodes_by_canonical_key.items():
        if len(nodes) > 1:
            ambiguous_keys.add(k)
            diagnostics.append(
                f"Ambiguous semantic key '{k}' in next scene (used by multiple nodes: {[n[0] for n in nodes]})"
            )

    matched_candidate_keys = sorted(list((from_keys & to_keys) - ambiguous_keys))
    unmatched_keys = sorted(list((from_keys ^ to_keys) | ambiguous_keys))

    # 7. Compile persistent objects
    persistent_objects: list[PersistentObjectTransition] = []
    matched_from_node_ids: set[str] = set()
    matched_to_node_ids: set[str] = set()

    for k in matched_candidate_keys:
        from_nid, concept_entry = from_nodes_by_canonical_key[k][0]
        to_nid, _ = to_nodes_by_canonical_key[k][0]

        from_box = from_box_map.get(from_nid)
        to_box = to_box_map.get(to_nid)

        if from_box is None:
            diagnostics.append(f"Persistent concept '{k}' node '{from_nid}' missing from previous layout boxes")
            unmatched_keys.append(k)
            continue
        if to_box is None:
            diagnostics.append(f"Persistent concept '{k}' node '{to_nid}' missing from next layout boxes")
            unmatched_keys.append(k)
            continue

        dx = round(to_box.rect.center_x - from_box.rect.center_x, 4)
        dy = round(to_box.rect.center_y - from_box.rect.center_y, 4)
        sx = round(to_box.rect.width / from_box.rect.width, 4)
        sy = round(to_box.rect.height / from_box.rect.height, 4)

        is_dimension_changed = abs(sx - 1.0) > 1e-3 or abs(sy - 1.0) > 1e-3
        is_position_changed = abs(dx) > 1e-3 or abs(dy) > 1e-3

        if eff_policy.require_geometry_change and not (is_position_changed or is_dimension_changed):
            diagnostics.append(f"Persistent concept '{k}' skipped because geometry is stationary")
            continue

        # Determine requested operation
        if is_dimension_changed and eff_policy.detect_resize and eff_policy.allow_resize:
            requested_op = TransitionOperation.RESIZE
        else:
            requested_op = TransitionOperation.MOVE

        effective_op, fallback_reason = negotiate_operation_capability(requested_op, eff_caps)
        if fallback_reason:
            diagnostics.append(f"Concept '{k}': {fallback_reason}")

        p_obj = PersistentObjectTransition(
            semantic_key=k,
            concept_id=concept_entry.concept_id,
            from_node_id=from_nid,
            to_node_id=to_nid,
            requested_operation=requested_op,
            effective_operation=effective_op,
            source_rect=from_box.rect,
            target_rect=to_box.rect,
            source_zone=from_box.zone,
            target_zone=to_box.zone,
            displacement_x=dx,
            displacement_y=dy,
            scale_x=sx,
            scale_y=sy,
            fallback_reason=fallback_reason,
        )
        persistent_objects.append(p_obj)
        matched_from_node_ids.add(from_nid)
        matched_to_node_ids.add(to_nid)

    # 8. Identify departing and entering nodes
    departing_nodes = sorted([b.node_id for b in from_layout.boxes if b.node_id not in matched_from_node_ids])
    entering_nodes = sorted([b.node_id for b in to_layout.boxes if b.node_id not in matched_to_node_ids])

    plan_id = transition_id or f"{from_layout.scene_id}__{to_layout.scene_id}"

    return InterSceneTransitionPlan(
        schema_version="2.1",
        transition_id=plan_id,
        from_scene=from_layout.scene_id,
        to_scene=to_layout.scene_id,
        duration=effective_duration,
        duration_ms=round(effective_duration * 1000.0, 4),
        persistent_objects=tuple(sorted(persistent_objects, key=lambda x: x.semantic_key)),
        departing_node_ids=tuple(departing_nodes),
        entering_node_ids=tuple(entering_nodes),
        unmatched_keys=tuple(sorted(list(set(unmatched_keys)))),
        diagnostics=tuple(diagnostics),
    )
