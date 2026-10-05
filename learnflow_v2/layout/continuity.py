"""Cross-scene continuity and previous-layout stability engine for LearnFlow V2.

Architecture (PLAN_V2 - V2-06 Hardened):
    Continuity anchors visual concepts across scene transitions using canonical
    `semantic_key` identity (NOT ephemeral node IDs, labels, or indices).
    
    Principles:
    1. Semantic Identity: Matching strictly by SceneNode.semantic_key.
    2. Authoritative Semantics: Uses shared canonical_zone_for_role, role_zone_class,
       and is_role_zone_compatible from semantics.py. Never maintains a private taxonomy.
    3. Normalized Proportional Mapping: Positions normalized relative to previous
       semantic zone [0.0, 1.0], projected into current legal zone.
    4. Hard Constraints Beat Continuity: Safe edge, role/zone containment, collision
       repair, and minimum dimensions strictly dominate soft continuity preferences.
    5. Real Solver-Based Continuity: Generates bounded soft WEAK linear constraints in Kiwi.
       Zero post-hoc coordinate manipulation or rectangle dragging.
    6. Graph Stability: Derives deterministic model order for ELK Layered layout
       to preserve dominant-axis arrangement across scene evolution, strictly invariant
       to input node insertion order.
"""

from __future__ import annotations

from enum import Enum
import math
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from learnflow_v2.core.errors import LayoutInvalidInputError
from learnflow_v2.layout.profiles import get_frame_profile
from learnflow_v2.layout.schema import FrameProfile, LayoutGraph, Rect
from learnflow_v2.layout.semantics import (
    canonical_zone_for_role,
    is_role_zone_compatible,
    role_zone_class,
)
from learnflow_v2.layout.graph import LayoutDirection
from learnflow_v2.scenegraph.enums import LayoutIntent, ReadingDirection
from learnflow_v2.scenegraph.schema import SceneGraph


class ContinuityStrength(str, Enum):
    """Bounded continuity preference strength for linear solver."""

    CONTINUITY = "CONTINUITY"
    WEAK = "WEAK"


def _validate_strict_int(v: Any, info: ValidationInfo, min_val: int = 0) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError(f"Field '{info.field_name}' must be an integer, got {type(v).__name__}: {v!r}")
    if v < min_val:
        raise ValueError(f"Field '{info.field_name}' must be >= {min_val}, got {v}")
    return v


def _validate_strict_float(v: Any, info: ValidationInfo, min_val: float | None = 0.0) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"Field '{info.field_name}' must be a real number, got {type(v).__name__}: {v!r}")
    f_val = float(v)
    if not math.isfinite(f_val):
        raise ValueError(f"Field '{info.field_name}' must be finite, got {f_val}")
    if min_val is not None and f_val < min_val:
        raise ValueError(f"Field '{info.field_name}' must be >= {min_val}, got {f_val}")
    return f_val


def _validate_unit_interval(v: Any, info: ValidationInfo) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"Field '{info.field_name}' must be a real number, got {type(v).__name__}: {v!r}")
    f_val = float(v)
    if not math.isfinite(f_val):
        raise ValueError(f"Field '{info.field_name}' must be finite, got {f_val}")
    if f_val < 0.0 or f_val > 1.0:
        raise ValueError(f"Field '{info.field_name}' must be in [0.0, 1.0], got {f_val}")
    return f_val


class ContinuityAnchor(BaseModel):
    """Normalized anchor connecting a persistent concept between two layouts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    semantic_key: str = Field(..., min_length=1, description="Persistent concept semantic key")
    previous_node_id: str = Field(..., min_length=1, description="Previous SceneNode ID")
    current_node_id: str = Field(..., min_length=1, description="Current SceneNode ID")
    previous_rect: Rect = Field(..., description="Solved bounding box in previous layout")
    previous_zone: str = Field(..., min_length=1, description="Zone occupied in previous layout")
    normalized_center_x: float = Field(..., description="Previous center X relative to previous zone [0.0, 1.0]")
    normalized_center_y: float = Field(..., description="Previous center Y relative to previous zone [0.0, 1.0]")
    target_center_x: float = Field(default=0.0, description="Projected target center X in current frame")
    target_center_y: float = Field(default=0.0, description="Projected target center Y in current frame")
    target_zone: str = Field(default="CONTENT", min_length=1, description="Legal assigned zone in current frame")

    @field_validator("normalized_center_x", "normalized_center_y", mode="before")
    @classmethod
    def validate_normalized_coords(cls, v: Any, info: ValidationInfo) -> float:
        return _validate_unit_interval(v, info)

    @field_validator("target_center_x", "target_center_y", mode="before")
    @classmethod
    def validate_target_coords(cls, v: Any, info: ValidationInfo) -> float:
        return _validate_strict_float(v, info, min_val=None)


class ContinuityConstraint(BaseModel):
    """Soft linear positioning target passed to Kiwi linear solver."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str = Field(..., min_length=1, description="Current SceneNode ID to constrain")
    semantic_key: str = Field(..., min_length=1, description="Associated semantic key")
    target_center_x: float = Field(..., description="Preferred center X coordinate")
    target_center_y: float = Field(..., description="Preferred center Y coordinate")
    strength: ContinuityStrength = Field(default=ContinuityStrength.CONTINUITY, description="Bounded soft preference strength")

    @field_validator("target_center_x", "target_center_y", mode="before")
    @classmethod
    def validate_targets(cls, v: Any, info: ValidationInfo) -> float:
        return _validate_strict_float(v, info, min_val=None)


class ContinuityContext(BaseModel):
    """Auditable semantic continuity context between two consecutive scenes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    anchors: list[ContinuityAnchor] = Field(default_factory=list, description="Matched persistent concept anchors")
    constraints: list[ContinuityConstraint] = Field(default_factory=list, description="Soft Kiwi constraints")
    matched_keys: list[str] = Field(default_factory=list, description="Sorted list of matched semantic keys")
    new_keys: list[str] = Field(default_factory=list, description="Sorted list of newly introduced semantic keys")
    removed_keys: list[str] = Field(default_factory=list, description="Sorted list of removed semantic keys")
    ambiguous_keys: list[str] = Field(default_factory=list, description="Sorted list of ambiguous duplicate keys")
    missing_box_keys: list[str] = Field(default_factory=list, description="Semantic keys missing previous layout box")
    invalid_previous_geometry_keys: list[str] = Field(default_factory=list, description="Semantic keys with invalid previous box geometry")
    diagnostics: list[str] = Field(default_factory=list, description="Auditable diagnostic messages")

    @field_validator("anchors")
    @classmethod
    def validate_anchors_order(cls, v: list[ContinuityAnchor]) -> list[ContinuityAnchor]:
        return sorted(v, key=lambda a: a.semantic_key)

    @field_validator("constraints")
    @classmethod
    def validate_constraints_order(cls, v: list[ContinuityConstraint]) -> list[ContinuityConstraint]:
        return sorted(v, key=lambda c: c.semantic_key)

    @field_validator(
        "matched_keys",
        "new_keys",
        "removed_keys",
        "ambiguous_keys",
        "missing_box_keys",
        "invalid_previous_geometry_keys",
    )
    @classmethod
    def validate_keys_order(cls, v: list[str]) -> list[str]:
        return sorted(list(set(v)))

    @model_validator(mode="before")
    @classmethod
    def populate_matched_keys_if_missing(cls, data: Any) -> Any:
        if isinstance(data, dict):
            anchors = data.get("anchors", [])
            anchor_keys = [
                a.semantic_key if hasattr(a, "semantic_key") else a.get("semantic_key")
                for a in anchors
                if isinstance(a, (dict, ContinuityAnchor))
            ]
            if "matched_keys" not in data or data["matched_keys"] is None:
                data["matched_keys"] = sorted(list({k for k in anchor_keys if k}))
        return data

    @model_validator(mode="after")
    def validate_consistency(self) -> "ContinuityContext":
        anchor_keys = [a.semantic_key for a in self.anchors]
        if len(anchor_keys) != len(set(anchor_keys)):
            raise ValueError("anchor semantic keys must be unique")
        constraint_keys = [c.semantic_key for c in self.constraints]
        if len(constraint_keys) != len(set(constraint_keys)):
            raise ValueError("constraint semantic keys must be unique")
        constraint_node_ids = [c.node_id for c in self.constraints]
        if len(constraint_node_ids) != len(set(constraint_node_ids)):
            raise ValueError("constraint node IDs must be unique")

        anchor_key_set = set(anchor_keys)
        constraint_key_set = set(constraint_keys)
        matched_key_set = set(self.matched_keys)

        if anchor_key_set != constraint_key_set:
            if anchor_key_set - constraint_key_set:
                raise ValueError(
                    f"ContinuityContext missing constraint for anchor keys: {sorted(anchor_key_set - constraint_key_set)}"
                )
            else:
                raise ValueError(
                    f"ContinuityContext extra constraint for unanchored keys: {sorted(constraint_key_set - anchor_key_set)}"
                )

        if anchor_key_set != matched_key_set:
            raise ValueError(
                f"matched_keys {self.matched_keys} must be consistent with anchor keys {sorted(anchor_key_set)}"
            )

        constraints_by_key = {c.semantic_key: c for c in self.constraints}
        for a in self.anchors:
            c = constraints_by_key[a.semantic_key]
            if c.node_id != a.current_node_id:
                raise ValueError(
                    f"ContinuityContext node_id mismatch for key '{a.semantic_key}': "
                    f"constraint node_id '{c.node_id}' != anchor current_node_id '{a.current_node_id}'"
                )
            if abs(c.target_center_x - a.target_center_x) > 1e-3 or abs(c.target_center_y - a.target_center_y) > 1e-3:
                raise ValueError(
                    f"ContinuityContext target mismatch for key '{a.semantic_key}': "
                    f"constraint target ({c.target_center_x}, {c.target_center_y}) != "
                    f"anchor target ({a.target_center_x}, {a.target_center_y})"
                )

        return self


class ContinuityMetrics(BaseModel):
    """Explainable geometric displacement metrics for auditable continuity evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    matched_count: int = Field(default=0, ge=0, description="Number of persistent concepts matched")
    new_count: int = Field(default=0, ge=0, description="Number of newly introduced concepts")
    removed_count: int = Field(default=0, ge=0, description="Number of removed concepts")
    total_displacement: float = Field(default=0.0, ge=0.0, description="Sum of normalized displacements")
    mean_displacement: float = Field(default=0.0, ge=0.0, description="Mean normalized displacement")
    max_displacement: float = Field(default=0.0, ge=0.0, description="Maximum single-concept normalized displacement")

    @field_validator("matched_count", "new_count", "removed_count", mode="before")
    @classmethod
    def validate_counts(cls, v: Any, info: ValidationInfo) -> int:
        return _validate_strict_int(v, info, min_val=0)

    @field_validator("total_displacement", "mean_displacement", "max_displacement", mode="before")
    @classmethod
    def validate_displacements(cls, v: Any, info: ValidationInfo) -> float:
        return _validate_strict_float(v, info, min_val=0.0)


def build_continuity_context(
    previous_scene_graph: SceneGraph,
    previous_layout: LayoutGraph,
    current_scene_graph: SceneGraph,
    previous_profile: FrameProfile | str | None = None,
    current_profile: FrameProfile | str | None = None,
    current_layout_items: list[Any] | None = None,
    is_graph_layout: bool | None = None,
) -> ContinuityContext:
    """Derive continuity anchors and soft positioning constraints from previous layout.

    Hardened Contracts (V2-06):
    - Matching is based strictly on SceneNode.semantic_key (never node_id, label, or content).
    - Exactly-one-key on both sides -> ContinuityAnchor + ContinuityConstraint.
    - New key in current scene -> new_keys (no anchor).
    - Key present only in previous scene -> removed_keys (no error).
    - Duplicate key in either scene -> ambiguous_keys (NO arbitrary anchor created).
    - Matched key missing a LayoutBox in previous_layout -> missing_box_keys (diagnostic, no crash).
    - Role to zone projection uses shared authoritative semantics (canonical_zone_for_role, is_role_zone_compatible).
    - Explicit target_zone validated against role and current profile, raising LAYOUT_INVALID_INPUT if invalid.
    - Previous box geometry validated: previous zone exists (no SAFE_EDGE fallback), box inside frame, box inside zone.
    - If current node role is unknown without layout items, omit positional constraint with explicit diagnostic (do not invent content).
    """
    prev_prof = get_frame_profile(previous_profile or previous_layout.frame_profile_id)
    curr_prof = get_frame_profile(current_profile or prev_prof.id)

    # 1. Map previous nodes by semantic_key
    prev_nodes_by_key: dict[str, list[Any]] = {}
    for node in previous_scene_graph.nodes:
        if node.semantic_key and node.semantic_key.strip():
            prev_nodes_by_key.setdefault(node.semantic_key.strip(), []).append(node)

    # 2. Map current nodes by semantic_key
    curr_nodes_by_key: dict[str, list[Any]] = {}
    for node in current_scene_graph.nodes:
        if node.semantic_key and node.semantic_key.strip():
            curr_nodes_by_key.setdefault(node.semantic_key.strip(), []).append(node)

    prev_keys = set(prev_nodes_by_key.keys())
    curr_keys = set(curr_nodes_by_key.keys())

    # 3. Classify keys
    ambiguous_keys: set[str] = set()
    for k, nodes in prev_nodes_by_key.items():
        if len(nodes) > 1:
            ambiguous_keys.add(k)
    for k, nodes in curr_nodes_by_key.items():
        if len(nodes) > 1:
            ambiguous_keys.add(k)

    removed_keys = sorted(list((prev_keys - curr_keys) - ambiguous_keys))
    new_keys = sorted(list((curr_keys - prev_keys) - ambiguous_keys))
    candidate_matched_keys = sorted(list((prev_keys & curr_keys) - ambiguous_keys))

    # 4. Map previous boxes by node_id
    prev_box_map = {b.node_id: b for b in previous_layout.boxes}

    # 5. Map current items by node_id to determine legal current zone
    current_roles: dict[str, str] = {}
    current_target_zones: dict[str, str] = {}
    if current_layout_items:
        for it in current_layout_items:
            nid = getattr(it, "node_id", None) or (it.get("node_id") if isinstance(it, dict) else None)
            role = getattr(it, "role", None) or (it.get("role") if isinstance(it, dict) else None)
            tz = getattr(it, "target_zone", None) or (it.get("target_zone") if isinstance(it, dict) else None)
            if nid:
                if role is not None:
                    current_roles[nid] = str(role)
                if tz is not None:
                    tz_str = str(tz)
                    try:
                        curr_prof.get_zone(tz_str)
                    except KeyError:
                        raise LayoutInvalidInputError(
                            f"Target zone '{tz_str}' does not exist in profile '{curr_prof.id}' for node '{nid}'",
                            details={"node_id": nid, "target_zone": tz_str, "profile": curr_prof.id},
                        )
                    if role is not None and not is_role_zone_compatible(str(role), tz_str):
                        raise LayoutInvalidInputError(
                            f"Target zone '{tz_str}' is incompatible with role '{role}' for node '{nid}'",
                            details={"node_id": nid, "role": str(role), "target_zone": tz_str},
                        )
                    current_target_zones[nid] = tz_str

    intent_type = getattr(getattr(current_scene_graph, "layout_intent", None), "type", None)
    if is_graph_layout is not None:
        effective_graph_layout = bool(is_graph_layout)
    else:
        effective_graph_layout = intent_type in {LayoutIntent.PROCESS, LayoutIntent.HIERARCHY}

    anchors: list[ContinuityAnchor] = []
    constraints: list[ContinuityConstraint] = []
    matched_keys: list[str] = []
    missing_box_keys: list[str] = []
    invalid_previous_geometry_keys: list[str] = []
    diagnostics: list[str] = []

    for k in candidate_matched_keys:
        prev_node = prev_nodes_by_key[k][0]
        curr_node = curr_nodes_by_key[k][0]

        if prev_node.id not in prev_box_map:
            missing_box_keys.append(k)
            continue

        prev_box = prev_box_map[prev_node.id]

        # Validate previous zone exists (NO silent fallback to SAFE_EDGE)
        try:
            prev_zone_rect = prev_prof.get_zone(prev_box.zone)
        except KeyError:
            invalid_previous_geometry_keys.append(k)
            diagnostics.append(f"Semantic key '{k}' references unknown previous zone '{prev_box.zone}' in profile '{prev_prof.id}'")
            continue

        # Validate previous box is inside previous frame
        prev_frame_rect = Rect(x=0.0, y=0.0, width=prev_prof.width, height=prev_prof.height)
        if not prev_frame_rect.contains_rect(prev_box.rect, tol=1e-2):
            invalid_previous_geometry_keys.append(k)
            diagnostics.append(f"Semantic key '{k}' previous box is outside previous frame")
            continue

        # Validate previous box is inside its declared previous zone
        if not prev_zone_rect.contains_rect(prev_box.rect, tol=1e-2):
            invalid_previous_geometry_keys.append(k)
            diagnostics.append(f"Semantic key '{k}' previous box is outside its declared previous zone '{prev_box.zone}'")
            continue

        if prev_zone_rect.width <= 0 or prev_zone_rect.height <= 0:
            invalid_previous_geometry_keys.append(k)
            diagnostics.append(f"Semantic key '{k}' previous zone has non-positive dimensions")
            continue

        norm_x = (prev_box.rect.center_x - prev_zone_rect.x) / prev_zone_rect.width
        norm_y = (prev_box.rect.center_y - prev_zone_rect.y) / prev_zone_rect.height

        if not (0.0 <= norm_x <= 1.0 and 0.0 <= norm_y <= 1.0):
            invalid_previous_geometry_keys.append(k)
            diagnostics.append(f"Semantic key '{k}' normalized center ({norm_x:.4f}, {norm_y:.4f}) outside [0, 1]")
            continue

        # Determine legal current target zone using authoritative shared semantics
        if curr_node.id in current_roles:
            role = current_roles[curr_node.id]
            if curr_node.id in current_target_zones:
                curr_zone_name = current_target_zones[curr_node.id]
            else:
                curr_zone_name = canonical_zone_for_role(role)
        elif effective_graph_layout:
            role = "content"
            curr_zone_name = "CONTENT"
        else:
            # Current role is unknown without layout items. DO NOT invent role="content"!
            diagnostics.append(
                f"Positional constraint omitted for node '{curr_node.id}' (semantic key '{k}'): legal current zone unknown without layout items"
            )
            continue

        try:
            curr_zone_rect = curr_prof.get_zone(curr_zone_name)
        except KeyError:
            diagnostics.append(f"Semantic key '{k}' current target zone '{curr_zone_name}' not found in profile '{curr_prof.id}'")
            continue

        target_cx = round(curr_zone_rect.x + norm_x * curr_zone_rect.width, 4)
        target_cy = round(curr_zone_rect.y + norm_y * curr_zone_rect.height, 4)

        if not curr_zone_rect.contains_point(target_cx, target_cy):
            diagnostics.append(f"Semantic key '{k}' projected target ({target_cx}, {target_cy}) outside current zone '{curr_zone_name}'")
            continue

        anchor = ContinuityAnchor(
            semantic_key=k,
            previous_node_id=prev_node.id,
            current_node_id=curr_node.id,
            previous_rect=prev_box.rect,
            previous_zone=prev_box.zone,
            normalized_center_x=round(norm_x, 4),
            normalized_center_y=round(norm_y, 4),
            target_center_x=target_cx,
            target_center_y=target_cy,
            target_zone=curr_zone_name,
        )
        anchors.append(anchor)
        matched_keys.append(k)

        constraints.append(
            ContinuityConstraint(
                node_id=curr_node.id,
                semantic_key=k,
                target_center_x=target_cx,
                target_center_y=target_cy,
                strength=ContinuityStrength.CONTINUITY,
            )
        )

    for k in sorted(missing_box_keys):
        diagnostics.append(f"Semantic key '{k}' missing from previous layout boxes")
    for k in sorted(list(ambiguous_keys)):
        diagnostics.append(f"Semantic key '{k}' is ambiguous (multiple nodes share this key)")

    return ContinuityContext(
        anchors=anchors,
        constraints=constraints,
        matched_keys=matched_keys,
        new_keys=new_keys,
        removed_keys=removed_keys,
        ambiguous_keys=sorted(list(ambiguous_keys)),
        missing_box_keys=sorted(missing_box_keys),
        invalid_previous_geometry_keys=sorted(invalid_previous_geometry_keys),
        diagnostics=diagnostics,
    )


def compute_continuity_metrics(
    continuity: ContinuityContext | None = None,
    layout_graph: LayoutGraph | None = None,
    profile: FrameProfile | str | None = None,
    *,
    continuity_context: ContinuityContext | None = None,
    current_layout: LayoutGraph | None = None,
) -> ContinuityMetrics:
    """Compute normalized spatial displacement metrics between solved layout and continuity targets."""
    ctx = continuity_context if continuity_context is not None else continuity
    target_graph = current_layout if current_layout is not None else layout_graph
    if ctx is None or not ctx.anchors or target_graph is None:
        new_cnt = len(ctx.new_keys) if ctx else 0
        rem_cnt = len(ctx.removed_keys) if ctx else 0
        return ContinuityMetrics(
            matched_count=0,
            new_count=new_cnt,
            removed_count=rem_cnt,
            total_displacement=0.0,
            mean_displacement=0.0,
            max_displacement=0.0,
        )

    prof = get_frame_profile(profile or target_graph.frame_profile_id)
    box_map = {b.node_id: b for b in target_graph.boxes}

    displacements: list[float] = []
    for anchor in ctx.anchors:
        if anchor.current_node_id not in box_map:
            raise LayoutInvalidInputError(
                f"LayoutGraph is missing box for matched continuity anchor node '{anchor.current_node_id}' (semantic key '{anchor.semantic_key}')",
                details={"node_id": anchor.current_node_id, "semantic_key": anchor.semantic_key},
            )
        box = box_map[anchor.current_node_id]
        dx = box.rect.center_x - anchor.target_center_x
        dy = box.rect.center_y - anchor.target_center_y
        dist = math.sqrt(dx * dx + dy * dy)

        try:
            zone_rect = prof.get_zone(anchor.target_zone)
        except KeyError:
            raise LayoutInvalidInputError(
                f"Anchor target zone '{anchor.target_zone}' does not exist in profile '{prof.id}'",
                details={"target_zone": anchor.target_zone, "profile": prof.id},
            )

        diag = math.sqrt(zone_rect.width * zone_rect.width + zone_rect.height * zone_rect.height)
        if diag <= 0.0:
            diag = math.sqrt(prof.width * prof.width + prof.height * prof.height)

        norm_disp = dist / diag if diag > 0.0 else 0.0
        displacements.append(norm_disp)

    matched_count = len(displacements)
    if matched_count == 0:
        return ContinuityMetrics(
            matched_count=0,
            new_count=len(ctx.new_keys),
            removed_count=len(ctx.removed_keys),
            total_displacement=0.0,
            mean_displacement=0.0,
            max_displacement=0.0,
        )

    total_d = round(sum(displacements), 4)
    mean_d = round(total_d / matched_count, 4)
    max_d = round(max(displacements), 4)

    return ContinuityMetrics(
        matched_count=matched_count,
        new_count=len(ctx.new_keys),
        removed_count=len(ctx.removed_keys),
        total_displacement=total_d,
        mean_displacement=mean_d,
        max_displacement=max_d,
    )


def derive_stable_graph_order(
    previous_scene_graph: SceneGraph,
    previous_layout: LayoutGraph,
    current_scene_graph: SceneGraph,
    direction: LayoutDirection | ReadingDirection | str = "RIGHT",
) -> list[str]:
    """Derive deterministic graph node order preserving previous dominant-axis relative positions.

    V2-06 Section 23 & Hardening:
    - Semantic key occurs exactly once in previous AND exactly once in current -> persistent stable-order anchor.
    - Duplicate key on either side is ambiguous -> no persistent rank for that key.
    - Persistent keys ordered from previous layout dominant axis:
        RIGHT / LEFT -> previous center_x
        DOWN / UP    -> previous center_y
    - New / ambiguous nodes assigned ranks based on topological predecessor/successor relationships,
      falling back to preferred_order, with deterministic node ID tie-breaking.
    - Output is strictly invariant to input SceneGraph list insertion order.
    """
    dir_str = direction.value if hasattr(direction, "value") else str(direction)
    horizontal = dir_str in {"RIGHT", "LEFT", "left_to_right", "right_to_left"}

    # 1. Group previous nodes by semantic_key
    prev_nodes_by_key: dict[str, list[Any]] = {}
    for n in previous_scene_graph.nodes:
        if n.semantic_key and n.semantic_key.strip():
            prev_nodes_by_key.setdefault(n.semantic_key.strip(), []).append(n)

    # 2. Group current nodes by semantic_key
    curr_nodes_by_key: dict[str, list[Any]] = {}
    for n in current_scene_graph.nodes:
        if n.semantic_key and n.semantic_key.strip():
            curr_nodes_by_key.setdefault(n.semantic_key.strip(), []).append(n)

    prev_box_map = {b.node_id: b for b in previous_layout.boxes}

    # 3. Find unambiguous persistent keys (occur exactly once in previous AND exactly once in current)
    persistent_positions: list[tuple[float, float, str, str]] = []  # (pos_primary, pos_cross, semantic_key, current_node_id)
    current_matched_ids: set[str] = set()

    for k, curr_nodes in sorted(curr_nodes_by_key.items()):
        if len(curr_nodes) == 1 and k in prev_nodes_by_key and len(prev_nodes_by_key[k]) == 1:
            curr_n = curr_nodes[0]
            prev_n = prev_nodes_by_key[k][0]
            if prev_n.id in prev_box_map:
                b = prev_box_map[prev_n.id]
                pos = b.rect.center_x if horizontal else b.rect.center_y
                cross = b.rect.center_y if horizontal else b.rect.center_x
                persistent_positions.append((pos, cross, k, curr_n.id))
                current_matched_ids.add(curr_n.id)

    # Sort persistent nodes deterministically by previous coordinate, cross-axis, then key, then current node ID
    persistent_positions.sort(key=lambda p: (round(p[0], 2), round(p[1], 2), p[2], p[3]))

    # Assign base ranks to persistent nodes: 10.0, 20.0, 30.0...
    ranks: dict[str, float] = {}
    for idx, (_, _, _, nid) in enumerate(persistent_positions):
        ranks[nid] = (idx + 1) * 10.0

    # 4. Topological relationships for current nodes
    preds: dict[str, set[str]] = {n.id: set() for n in current_scene_graph.nodes}
    succs: dict[str, set[str]] = {n.id: set() for n in current_scene_graph.nodes}
    for rel in current_scene_graph.relations:
        if rel.source in preds and rel.target in succs:
            preds[rel.target].add(rel.source)
            succs[rel.source].add(rel.target)

    # 5. Assign ranks to new or ambiguous nodes (sorted deterministically by ID)
    unmatched_node_ids = sorted([n.id for n in current_scene_graph.nodes if n.id not in current_matched_ids])
    curr_node_map = {n.id: n for n in current_scene_graph.nodes}

    for nid in unmatched_node_ids:
        pred_ranks = [ranks[p] for p in preds[nid] if p in ranks]
        succ_ranks = [ranks[s] for s in succs[nid] if s in ranks]

        if pred_ranks and succ_ranks:
            ranks[nid] = (max(pred_ranks) + min(succ_ranks)) / 2.0
        elif pred_ranks:
            ranks[nid] = max(pred_ranks) + 5.0
        elif succ_ranks:
            ranks[nid] = min(succ_ranks) - 5.0
        else:
            curr_node = curr_node_map[nid]
            pref = (
                curr_node.layout_hint.preferred_order
                if (curr_node and curr_node.layout_hint and curr_node.layout_hint.preferred_order is not None)
                else 50.0
            )
            ranks[nid] = float(pref)

    # 6. Produce final node order deterministically sorted by rank, then node ID
    all_current_nodes = sorted(current_scene_graph.nodes, key=lambda n: (ranks.get(n.id, 999.0), n.id))
    return [n.id for n in all_current_nodes]
