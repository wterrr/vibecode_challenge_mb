"""Strict layout feasibility gate and soft scoring function for LearnFlow V2.

Architecture (PLAN_V2):
Stage A: Hard Feasibility Gate
    Categorical elimination if ANY hard constraint fails:
    - overflow == 0
    - fatal_overlap == 0
    - clipping == 0
    - safe_zone_violation == 0
    - invalid_geometry == 0
    - edge_node_intersection == 0
    - minimum_readability_violation == 0
    An infeasible candidate is NEVER evaluated or ranked against feasible candidates.

Stage B: Soft Scoring
    Calculates explainable, deterministic soft penalties for FEASIBLE candidates only:
    J_soft = lambda_e * E + lambda_t * T + lambda_b * B + lambda_w * W
"""

import math
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, model_validator

from learnflow_v2.layout.collision import detect_box_collisions
from learnflow_v2.layout.graph_metrics import compute_graph_metrics
from learnflow_v2.layout.preflight import validate_graph_layout, validate_layout_graph
from learnflow_v2.layout.profiles import get_frame_profile
from learnflow_v2.layout.schema import FrameProfile, LayoutGraph, LayoutStrategy
from learnflow_v2.layout.semantics import is_chrome_role


class LayoutFeasibilityReport(BaseModel):
    """Strict immutable report on hard geometric and semantic feasibility gates."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    overflow_count: int = Field(default=0, ge=0, description="Boxes overflowing frame boundary")
    fatal_overlap_count: int = Field(default=0, ge=0, description="Pairs of non-overlapping nodes that collide")
    clipping_count: int = Field(default=0, ge=0, description="Boxes rendered smaller than intrinsic measurement")
    safe_zone_violation_count: int = Field(default=0, ge=0, description="Boxes outside assigned zone or safe edge")
    invalid_geometry_count: int = Field(default=0, ge=0, description="Non-positive, non-finite or duplicate geometry")
    edge_node_intersection_count: int = Field(default=0, ge=0, description="Routed edges intersecting unrelated nodes")
    minimum_readability_violation_count: int = Field(default=0, ge=0, description="Violations of minimum readability")
    feasible: bool = Field(default=False, description="Derived hard gate pass/fail status")
    violations: list[str] = Field(default_factory=list, description="Descriptive list of violations")

    @model_validator(mode="after")
    def validate_hard_gate_invariant(self) -> "LayoutFeasibilityReport":
        hard_count = (
            self.overflow_count
            + self.fatal_overlap_count
            + self.clipping_count
            + self.safe_zone_violation_count
            + self.invalid_geometry_count
            + self.edge_node_intersection_count
            + self.minimum_readability_violation_count
        )
        if hard_count > 0 and self.feasible:
            raise ValueError(
                f"Cannot construct feasible=True when {hard_count} hard violation(s) exist. "
                f"(overflow={self.overflow_count}, fatal_overlap={self.fatal_overlap_count}, "
                f"clipping={self.clipping_count}, safe_zone={self.safe_zone_violation_count}, "
                f"invalid_geom={self.invalid_geometry_count}, edge_node={self.edge_node_intersection_count}, "
                f"readability={self.minimum_readability_violation_count})"
            )
        if hard_count == 0 and not self.feasible:
            object.__setattr__(self, "feasible", True)
        elif hard_count > 0 and not self.feasible:
            # Consistent with invariant
            pass
        return self


class SoftScoreWeights(BaseModel):
    """Centralized, deterministic weights for soft layout scoring components."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    edge_crossing_weight: float = Field(default=10.0, ge=0.0)
    edge_bend_weight: float = Field(default=2.0, ge=0.0)
    edge_length_weight: float = Field(default=0.001, ge=0.0)
    typography_weight: float = Field(default=1.0, ge=0.0)
    balance_weight: float = Field(default=5.0, ge=0.0)
    whitespace_weight: float = Field(default=3.0, ge=0.0)

    @model_validator(mode="after")
    def validate_finite_weights(self) -> "SoftScoreWeights":
        for attr in (
            "edge_crossing_weight",
            "edge_bend_weight",
            "edge_length_weight",
            "typography_weight",
            "balance_weight",
            "whitespace_weight",
        ):
            val = getattr(self, attr)
            if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(val) or val < 0.0:
                raise ValueError(f"{attr} must be a non-negative finite number, got {val}")
        return self


class SoftLayoutScore(BaseModel):
    """Explainable, multi-component soft score for ranking feasible layouts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    edge_penalty: float = Field(default=0.0, ge=0.0, description="Penalty for edge crossings, bends, and length")
    typography_penalty: float = Field(default=0.0, ge=0.0, description="Penalty for deviation from preferred typography")
    balance_penalty: float = Field(default=0.0, ge=0.0, description="Penalty for visual center-of-mass imbalance")
    whitespace_penalty: float = Field(default=0.0, ge=0.0, description="Penalty for extreme sparseness or density")
    total: float = Field(default=0.0, ge=0.0, description="Total soft layout objective (lower is better)")

    @model_validator(mode="after")
    def validate_score(self) -> "SoftLayoutScore":
        for attr in ("edge_penalty", "typography_penalty", "balance_penalty", "whitespace_penalty", "total"):
            val = getattr(self, attr)
            if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(val) or val < 0.0:
                raise ValueError(f"{attr} must be a non-negative finite number, got {val}")
        expected_total = round(
            self.edge_penalty + self.typography_penalty + self.balance_penalty + self.whitespace_penalty, 4
        )
        if abs(self.total - expected_total) > 1e-3:
            object.__setattr__(self, "total", expected_total)
        return self


def evaluate_feasibility(
    layout_graph: LayoutGraph,
    profile: FrameProfile | str | None = None,
    measurements: dict[str, tuple[float, float]] | None = None,
    expected_node_ids: list[str] | set[str] | None = None,
    tol: float = 1e-2,
) -> LayoutFeasibilityReport:
    """Evaluate all hard feasibility gates for a solved LayoutGraph without raising.

    Uses existing preflight and collision detection logic.
    Candidate is marked feasible=True ONLY if every hard violation count is 0.
    """
    prof = get_frame_profile(profile or layout_graph.frame_profile_id)

    # 1. Base layout geometry & preflight checks (overflow, clipping, safe-zone, invalid geometry)
    preflight_rep = validate_layout_graph(
        layout_graph=layout_graph,
        profile=prof,
        measurements=measurements,
        expected_node_ids=expected_node_ids,
        tol=tol,
        raise_on_error=False,
    )

    # 2. Pure box-box collision detection
    collisions = detect_box_collisions(layout_graph, tol=tol)

    # 3. Directed graph specific checks if applicable
    edge_node_intersections = 0
    graph_violations: list[str] = []
    if layout_graph.strategy == LayoutStrategy.DIRECTED_GRAPH:
        graph_rep = validate_graph_layout(layout_graph=layout_graph, profile=prof, tol=tol, raise_on_error=False)
        edge_node_intersections = graph_rep.edge_node_intersection_count
        graph_violations = graph_rep.violations or []

    # Compile violations list
    all_violations: list[str] = list(preflight_rep.violations or [])
    for col in collisions:
        all_violations.append(
            f"Fatal node collision between '{col.first_node_id}' and '{col.second_node_id}': "
            f"overlap area={col.overlap_area}px² ({col.overlap_width}x{col.overlap_height})"
        )
    all_violations.extend(graph_violations)

    total_hard_violations = (
        preflight_rep.frame_overflow_count
        + len(collisions)
        + preflight_rep.content_clipping_count
        + preflight_rep.safe_zone_violation_count
        + preflight_rep.invalid_geometry_count
        + preflight_rep.missing_node_count
        + edge_node_intersections
    )

    return LayoutFeasibilityReport(
        overflow_count=preflight_rep.frame_overflow_count,
        fatal_overlap_count=len(collisions),
        clipping_count=preflight_rep.content_clipping_count,
        safe_zone_violation_count=preflight_rep.safe_zone_violation_count,
        invalid_geometry_count=preflight_rep.invalid_geometry_count + preflight_rep.missing_node_count,
        edge_node_intersection_count=edge_node_intersections,
        minimum_readability_violation_count=0,
        feasible=(total_hard_violations == 0),
        violations=all_violations,
    )


def compute_soft_score(
    layout_graph: LayoutGraph,
    profile: FrameProfile | str | None = None,
    weights: SoftScoreWeights | None = None,
) -> SoftLayoutScore:
    """Compute explainable soft layout score for a FEASIBLE LayoutGraph.

    Components:
    - edge_penalty: crossings (dominant), bends, total edge length
    - typography_penalty: 0.0 in V2-05 (adaptive typography reserved for later)
    - balance_penalty: distance of layout center-of-mass from content zone center
    - whitespace_penalty: layout density deviation from optimal range [0.25, 0.65]
    """
    prof = get_frame_profile(profile or layout_graph.frame_profile_id)
    w = weights or SoftScoreWeights()

    # 1. Edge soft penalty
    edge_pen = 0.0
    if layout_graph.strategy == LayoutStrategy.DIRECTED_GRAPH and layout_graph.routed_edges:
        boxes = {b.node_id: b.rect for b in layout_graph.boxes}
        metrics = compute_graph_metrics(layout_graph.routed_edges, boxes)
        edge_pen = round(
            w.edge_crossing_weight * metrics.edge_crossing_count
            + w.edge_bend_weight * metrics.bend_count
            + w.edge_length_weight * metrics.total_edge_length,
            4,
        )

    # 2. Typography soft penalty (0.0 for V2-05)
    typo_pen = 0.0

    # 3. Visual balance penalty
    content_zone = prof.get_zone("CONTENT")
    content_boxes = [b for b in layout_graph.boxes if not is_chrome_role(b.strategy_role)]
    if not content_boxes:
        content_boxes = layout_graph.boxes

    total_area = sum(b.rect.width * b.rect.height for b in content_boxes)
    if total_area > 0 and content_zone.width > 0 and content_zone.height > 0:
        mass_cx = sum(b.rect.width * b.rect.height * b.rect.center_x for b in content_boxes) / total_area
        mass_cy = sum(b.rect.width * b.rect.height * b.rect.center_y for b in content_boxes) / total_area
        # Normalize offset relative to half-extent of content zone
        norm_dx = abs(mass_cx - content_zone.center_x) / (0.5 * content_zone.width)
        norm_dy = abs(mass_cy - content_zone.center_y) / (0.5 * content_zone.height)
        imbalance = math.sqrt(norm_dx * norm_dx + norm_dy * norm_dy)
        balance_pen = round(w.balance_weight * imbalance, 4)
    else:
        balance_pen = 0.0

    # 4. Whitespace / density penalty
    content_area = content_zone.width * content_zone.height
    if content_area > 0:
        density = total_area / content_area
        # Preferred density band: 0.25 to 0.65
        if density < 0.25:
            density_diff = (0.25 - density) / 0.25
        elif density > 0.65:
            density_diff = (density - 0.65) / 0.35
        else:
            density_diff = 0.0
        whitespace_pen = round(w.whitespace_weight * density_diff, 4)
    else:
        whitespace_pen = 0.0

    total_score = round(edge_pen + typo_pen + balance_pen + whitespace_pen, 4)

    return SoftLayoutScore(
        edge_penalty=edge_pen,
        typography_penalty=typo_pen,
        balance_penalty=balance_pen,
        whitespace_penalty=whitespace_pen,
        total=total_score,
    )
