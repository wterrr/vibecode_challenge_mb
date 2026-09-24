"""Strict immutable collision detection and separation constraint model for LearnFlow V2.

Implements pure box-box collision detection, deterministic separation axis selection,
and semantic order preservation without solver mutation or LLM calls.
"""

from enum import Enum
import math
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, model_validator

from learnflow_v2.layout.profiles import get_frame_profile
from learnflow_v2.layout.schema import FrameProfile, LayoutBox, LayoutGraph, LayoutStrategy, _check_finite_number
from learnflow_v2.layout.semantics import is_chrome_role, role_zone_class, ZoneClass


class SeparationAxis(str, Enum):
    """Axis along which colliding boxes are separated."""

    HORIZONTAL = "HORIZONTAL"
    VERTICAL = "VERTICAL"


class SeparationOrdering(str, Enum):
    """Directional ordering of nodes on the separation axis.

    FIRST_BEFORE_SECOND: first_node is left of (or above) second_node.
    SECOND_BEFORE_FIRST: second_node is left of (or above) first_node.
    """

    FIRST_BEFORE_SECOND = "FIRST_BEFORE_SECOND"
    SECOND_BEFORE_FIRST = "SECOND_BEFORE_FIRST"


class CollisionPair(BaseModel):
    """Strict immutable artifact representing overlap between two layout boxes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    first_node_id: str = Field(..., min_length=1, description="First node in canonical alphabetical order")
    second_node_id: str = Field(..., min_length=1, description="Second node in canonical alphabetical order")
    overlap_width: float = Field(..., ge=0.0, description="Horizontal intersection width")
    overlap_height: float = Field(..., ge=0.0, description="Vertical intersection height")
    overlap_area: float = Field(..., ge=0.0, description="2D intersection area")
    penetration_x: float = Field(..., ge=0.0, description="X-axis penetration depth")
    penetration_y: float = Field(..., ge=0.0, description="Y-axis penetration depth")

    @model_validator(mode="after")
    def validate_canonical_and_finite(self) -> "CollisionPair":
        if self.first_node_id >= self.second_node_id:
            raise ValueError(
                f"CollisionPair requires canonical node ordering: first_node_id '{self.first_node_id}' "
                f"must be strictly less than second_node_id '{self.second_node_id}'"
            )
        for attr in ("overlap_width", "overlap_height", "overlap_area", "penetration_x", "penetration_y"):
            val = getattr(self, attr)
            if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(val) or val < 0.0:
                raise ValueError(f"{attr} must be a non-negative finite number, got {val}")
        return self


class SeparationConstraint(BaseModel):
    """Deterministic linear inequality constraint to resolve box collisions in Kiwi."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    first_node_id: str = Field(..., min_length=1, description="First node identifier")
    second_node_id: str = Field(..., min_length=1, description="Second node identifier")
    axis: SeparationAxis = Field(..., description="Axis of separation")
    ordering: SeparationOrdering = Field(..., description="Directional ordering of nodes")
    minimum_gap: float = Field(default=16.0, ge=0.0, description="Required minimum gap in pixels")

    @model_validator(mode="after")
    def validate_constraint(self) -> "SeparationConstraint":
        if self.first_node_id == self.second_node_id:
            raise ValueError(f"SeparationConstraint cannot constrain node '{self.first_node_id}' against itself")
        if not isinstance(self.minimum_gap, (int, float)) or isinstance(self.minimum_gap, bool) or not math.isfinite(self.minimum_gap) or self.minimum_gap < 0.0:
            raise ValueError(f"minimum_gap must be a non-negative finite number, got {self.minimum_gap}")
        return self


def detect_box_collisions(
    layout_graph: LayoutGraph,
    tol: float = 1e-3,
) -> list[CollisionPair]:
    """Pure, non-mutating box-box collision detection between nodes in a LayoutGraph.

    Boundary touching (e.g. A.right == B.left) is NOT considered a collision.
    Only positive area overlaps exceeding tolerance are reported.

    Args:
        layout_graph: Immutable LayoutGraph artifact to inspect
        tol: Deterministic tolerance threshold for boundary checks

    Returns:
        List of CollisionPair artifacts sorted deterministically by (first_node_id, second_node_id).
    """
    boxes = sorted(layout_graph.boxes, key=lambda b: b.node_id)
    n = len(boxes)
    collisions: list[CollisionPair] = []

    for i in range(n):
        box_a = boxes[i]
        rect_a = box_a.rect
        for j in range(i + 1, n):
            box_b = boxes[j]
            rect_b = box_b.rect

            # Box boundaries
            inter_left = max(rect_a.left, rect_b.left)
            inter_right = min(rect_a.right, rect_b.right)
            inter_top = max(rect_a.top, rect_b.top)
            inter_bottom = min(rect_a.bottom, rect_b.bottom)

            overlap_w = inter_right - inter_left
            overlap_h = inter_bottom - inter_top

            # Positive area check: touching at boundary (overlap <= tol) is not a collision
            if overlap_w > tol and overlap_h > tol:
                w_val = round(float(overlap_w), 4)
                h_val = round(float(overlap_h), 4)
                area_val = round(w_val * h_val, 4)
                collisions.append(
                    CollisionPair(
                        first_node_id=box_a.node_id,
                        second_node_id=box_b.node_id,
                        overlap_width=w_val,
                        overlap_height=h_val,
                        overlap_area=area_val,
                        penetration_x=w_val,
                        penetration_y=h_val,
                    )
                )

    collisions.sort(key=lambda c: (c.first_node_id, c.second_node_id))
    return collisions


def choose_separation_constraint(
    pair: CollisionPair,
    box_map: dict[str, LayoutBox],
    profile: FrameProfile | str,
    strategy: LayoutStrategy | str,
) -> SeparationConstraint:
    """Deterministically choose separation axis and ordering for a CollisionPair.

    Preserves semantic ordering and template orientation invariants:
    - Title is always above Content / Caption
    - Caption is always below Content
    - Left column is always left of (or above in stacked fallback) Right column
    - Image is always left of Text in 16:9 side-by-side, above Text in portrait stacked
    - Quote is always above Attribution
    - When costs are tied, follows dominant profile orientation and stable node ID tie-break.
    """
    prof = get_frame_profile(profile)
    strat = LayoutStrategy(strategy) if isinstance(strategy, str) else strategy

    box_a = box_map[pair.first_node_id]
    box_b = box_map[pair.second_node_id]

    gutter_h = max(16.0, prof.grid.horizontal_gap)
    gutter_v = max(16.0, prof.grid.vertical_gap)

    # Required displacement along each axis
    h_cost = pair.overlap_width + gutter_h
    v_cost = pair.overlap_height + gutter_v

    # Dominant orientation for tie-breaking
    if prof.aspect_ratio == "9:16":
        dominant_axis = SeparationAxis.VERTICAL
    elif strat in (LayoutStrategy.COMPARISON, LayoutStrategy.IMAGE_TEXT):
        dominant_axis = SeparationAxis.HORIZONTAL
    else:
        dominant_axis = SeparationAxis.VERTICAL

    # Determine axis
    if abs(h_cost - v_cost) <= 0.1:
        chosen_axis = dominant_axis
    elif h_cost < v_cost:
        chosen_axis = SeparationAxis.HORIZONTAL
    else:
        chosen_axis = SeparationAxis.VERTICAL

    # Determine semantic ordering
    role_a = box_a.strategy_role
    role_b = box_b.strategy_role

    # Chrome hierarchy takes strict precedence
    if is_chrome_role(role_a) or is_chrome_role(role_b):
        zone_cls_a = role_zone_class(role_a)
        zone_cls_b = role_zone_class(role_b)
        chosen_axis = SeparationAxis.VERTICAL
        if zone_cls_a == ZoneClass.TITLE:
            ordering = SeparationOrdering.FIRST_BEFORE_SECOND
        elif zone_cls_b == ZoneClass.TITLE:
            ordering = SeparationOrdering.SECOND_BEFORE_FIRST
        elif zone_cls_a == ZoneClass.CAPTION:
            ordering = SeparationOrdering.SECOND_BEFORE_FIRST
        else:
            ordering = SeparationOrdering.FIRST_BEFORE_SECOND
    elif strat == LayoutStrategy.COMPARISON:
        if role_a == "left" and role_b == "right":
            ordering = SeparationOrdering.FIRST_BEFORE_SECOND
        elif role_a == "right" and role_b == "left":
            ordering = SeparationOrdering.SECOND_BEFORE_FIRST
        else:
            if chosen_axis == SeparationAxis.HORIZONTAL:
                ordering = (
                    SeparationOrdering.FIRST_BEFORE_SECOND
                    if box_a.rect.center_x <= box_b.rect.center_x
                    else SeparationOrdering.SECOND_BEFORE_FIRST
                )
            else:
                ordering = (
                    SeparationOrdering.FIRST_BEFORE_SECOND
                    if box_a.rect.center_y <= box_b.rect.center_y
                    else SeparationOrdering.SECOND_BEFORE_FIRST
                )
    elif strat == LayoutStrategy.IMAGE_TEXT:
        if role_a == "image" and role_b in ("text", "content"):
            ordering = SeparationOrdering.FIRST_BEFORE_SECOND
        elif role_b == "image" and role_a in ("text", "content"):
            ordering = SeparationOrdering.SECOND_BEFORE_FIRST
        else:
            if chosen_axis == SeparationAxis.HORIZONTAL:
                ordering = (
                    SeparationOrdering.FIRST_BEFORE_SECOND
                    if box_a.rect.center_x <= box_b.rect.center_x
                    else SeparationOrdering.SECOND_BEFORE_FIRST
                )
            else:
                ordering = (
                    SeparationOrdering.FIRST_BEFORE_SECOND
                    if box_a.rect.center_y <= box_b.rect.center_y
                    else SeparationOrdering.SECOND_BEFORE_FIRST
                )
    elif strat == LayoutStrategy.QUOTE:
        if role_a in ("quote", "content") and role_b in ("attribution", "author"):
            chosen_axis = SeparationAxis.VERTICAL
            ordering = SeparationOrdering.FIRST_BEFORE_SECOND
        elif role_b in ("quote", "content") and role_a in ("attribution", "author"):
            chosen_axis = SeparationAxis.VERTICAL
            ordering = SeparationOrdering.SECOND_BEFORE_FIRST
        else:
            if chosen_axis == SeparationAxis.HORIZONTAL:
                ordering = (
                    SeparationOrdering.FIRST_BEFORE_SECOND
                    if box_a.rect.center_x <= box_b.rect.center_x
                    else SeparationOrdering.SECOND_BEFORE_FIRST
                )
            else:
                ordering = (
                    SeparationOrdering.FIRST_BEFORE_SECOND
                    if box_a.rect.center_y <= box_b.rect.center_y
                    else SeparationOrdering.SECOND_BEFORE_FIRST
                )
    else:
        # Default spatial ordering
        if chosen_axis == SeparationAxis.HORIZONTAL:
            ordering = (
                SeparationOrdering.FIRST_BEFORE_SECOND
                if box_a.rect.center_x <= box_b.rect.center_x
                else SeparationOrdering.SECOND_BEFORE_FIRST
            )
        else:
            ordering = (
                SeparationOrdering.FIRST_BEFORE_SECOND
                if box_a.rect.center_y <= box_b.rect.center_y
                else SeparationOrdering.SECOND_BEFORE_FIRST
            )

    min_gap = gutter_h if chosen_axis == SeparationAxis.HORIZONTAL else gutter_v

    return SeparationConstraint(
        first_node_id=pair.first_node_id,
        second_node_id=pair.second_node_id,
        axis=chosen_axis,
        ordering=ordering,
        minimum_gap=min_gap,
    )
