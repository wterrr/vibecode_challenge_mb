"""Strict preflight validator for solved LearnFlow V2 LayoutGraphs.

Enforces zero-tolerance gates:
- Finite geometry (no NaN, no Inf)
- Positive dimensions (width > 0, height > 0)
- Inside frame bounds
- Inside global safe-edge bounds
- Inside assigned safe zone
- Zero content clipping relative to required intrinsic measurements
- Unique node IDs
- Template-specific non-overlap relationships
"""

from dataclasses import dataclass
import math
from typing import Any

from learnflow_v2.core.errors import LayoutPreflightFailedError
from learnflow_v2.layout.profiles import get_frame_profile
from learnflow_v2.layout.schema import FrameProfile, LayoutGraph, LayoutStrategy
from learnflow_v2.layout.semantics import role_zone_class, role_zone_details, zone_class


@dataclass(frozen=True)
class PreflightReport:
    """Diagnostic report from preflight validation."""

    valid: bool
    frame_overflow_count: int = 0
    safe_zone_violation_count: int = 0
    content_clipping_count: int = 0
    invalid_geometry_count: int = 0
    missing_node_count: int = 0
    violations: list[str] = None


def validate_layout_graph(
    layout_graph: LayoutGraph,
    profile: FrameProfile | str | None = None,
    measurements: dict[str, tuple[float, float]] | None = None,
    expected_node_ids: list[str] | set[str] | None = None,
    tol: float = 1e-2,
) -> PreflightReport:
    """Validate a solved LayoutGraph against physical, zone, and measurement constraints.

    Args:
        layout_graph: Solved LayoutGraph artifact
        profile: Optional FrameProfile to validate against (defaults to layout_graph.frame_profile_id)
        measurements: Optional dict mapping node_id -> (required_min_width, required_min_height)
        expected_node_ids: Optional set/list of node IDs expected to be present in layout
        tol: Floating point tolerance for boundary checks

    Returns:
        PreflightReport if all checks pass

    Raises:
        LayoutPreflightFailedError: If any hard gate is violated
    """
    if profile is None:
        frame_prof = get_frame_profile(layout_graph.frame_profile_id)
    else:
        frame_prof = get_frame_profile(profile)

    violations: list[str] = []
    frame_overflow = 0
    safe_zone_violations = 0
    content_clipping = 0
    invalid_geometry = 0
    missing_nodes = 0

    # LayoutGraph artifact dimensions must identify the same physical frame as the resolved profile.
    if (
        abs(layout_graph.frame_width - frame_prof.width) > tol
        or abs(layout_graph.frame_height - frame_prof.height) > tol
    ):
        violations.append(
            f"LayoutGraph frame dimensions {layout_graph.frame_width}x{layout_graph.frame_height} "
            f"do not match profile '{frame_prof.id}' dimensions {frame_prof.width}x{frame_prof.height}"
        )
        frame_overflow += 1

    seen_ids: set[str] = set()

    for box in layout_graph.boxes:
        # 1. Unique node IDs
        if box.node_id in seen_ids:
            msg = f"Duplicate node_id '{box.node_id}' in LayoutGraph boxes"
            violations.append(msg)
            invalid_geometry += 1
        seen_ids.add(box.node_id)

        # 2. Finite numbers
        coords = [box.rect.x, box.rect.y, box.rect.width, box.rect.height]
        if not all(math.isfinite(c) for c in coords):
            msg = f"Box '{box.node_id}' contains non-finite coordinates: {coords}"
            violations.append(msg)
            invalid_geometry += 1
            continue

        # 3. Positive dimensions & non-negative position
        if box.rect.width <= 0.0 or box.rect.height <= 0.0:
            msg = f"Box '{box.node_id}' has non-positive dimensions: {box.rect.width}x{box.rect.height}"
            violations.append(msg)
            invalid_geometry += 1

        if box.rect.x < -tol or box.rect.y < -tol:
            msg = f"Box '{box.node_id}' has negative position: ({box.rect.x}, {box.rect.y})"
            violations.append(msg)
            invalid_geometry += 1

        # 4. Inside physical frame
        if box.rect.right > frame_prof.width + tol or box.rect.bottom > frame_prof.height + tol:
            msg = (
                f"Box '{box.node_id}' overflows frame boundaries: "
                f"right={box.rect.right} > {frame_prof.width} or bottom={box.rect.bottom} > {frame_prof.height}"
            )
            violations.append(msg)
            frame_overflow += 1

        # 5. Inside global safe edge
        safe_edge = frame_prof.safe_edge_rect
        if not safe_edge.contains_rect(box.rect, tol=tol):
            msg = (
                f"Box '{box.node_id}' violates global safe edge ({safe_edge.left}, {safe_edge.top}, "
                f"{safe_edge.right}, {safe_edge.bottom}): box is ({box.rect.left}, {box.rect.top}, "
                f"{box.rect.right}, {box.rect.bottom})"
            )
            violations.append(msg)
            safe_zone_violations += 1

        # 6. Inside assigned zone and same role/zone semantic contract as the solver.
        if box.zone:
            try:
                zone_rect = frame_prof.get_zone(box.zone)
                expected_class = role_zone_class(box.strategy_role)
                actual_class = zone_class(box.zone)
                if actual_class is None or actual_class != expected_class:
                    details = role_zone_details(box.node_id, box.strategy_role, box.zone)
                    msg = (
                        f"Box '{box.node_id}' strategy_role '{box.strategy_role}' cannot use zone '{box.zone}' "
                        f"(expected_zone_class={details['expected_zone_class']}, actual_zone_class={details['actual_zone_class']})"
                    )
                    violations.append(msg)
                    safe_zone_violations += 1
                if not zone_rect.contains_rect(box.rect, tol=tol):
                    msg = (
                        f"Box '{box.node_id}' leaves assigned zone '{box.zone}' ({zone_rect.left}, {zone_rect.top}, "
                        f"{zone_rect.right}, {zone_rect.bottom}): box is ({box.rect.left}, {box.rect.top}, "
                        f"{box.rect.right}, {box.rect.bottom})"
                    )
                    violations.append(msg)
                    safe_zone_violations += 1
            except KeyError:
                msg = f"Box '{box.node_id}' references unknown zone '{box.zone}'"
                violations.append(msg)
                safe_zone_violations += 1

        # 7. No clipping relative to measurement
        if measurements and box.node_id in measurements:
            req_w, req_h = measurements[box.node_id]
            if box.rect.width < req_w - tol:
                msg = f"Box '{box.node_id}' clipped horizontally: width {box.rect.width} < required {req_w}"
                violations.append(msg)
                content_clipping += 1
            if box.rect.height < req_h - tol:
                msg = f"Box '{box.node_id}' clipped vertically: height {box.rect.height} < required {req_h}"
                violations.append(msg)
                content_clipping += 1

    # 8. Template-specific relationship checks
    box_map = {b.node_id: b for b in layout_graph.boxes}
    strategy = layout_graph.strategy

    if strategy == LayoutStrategy.COMPARISON:
        left_box = next((b for b in layout_graph.boxes if b.strategy_role == "left"), None)
        right_box = next((b for b in layout_graph.boxes if b.strategy_role == "right"), None)
        if left_box and right_box:
            if left_box.rect.right > right_box.rect.left + tol:
                msg = f"Comparison columns overlap: left right={left_box.rect.right} > right left={right_box.rect.left}"
                violations.append(msg)
                invalid_geometry += 1

    elif strategy == LayoutStrategy.IMAGE_TEXT:
        img_box = next((b for b in layout_graph.boxes if b.strategy_role == "image"), None)
        txt_box = next((b for b in layout_graph.boxes if b.strategy_role in ("text", "content")), None)
        if img_box and txt_box:
            if frame_prof.aspect_ratio == "16:9":
                if img_box.rect.right > txt_box.rect.left + tol:
                    msg = f"Image and text overlap in 16:9: img right={img_box.rect.right} > txt left={txt_box.rect.left}"
                    violations.append(msg)
                    invalid_geometry += 1
            else:
                if img_box.rect.bottom > txt_box.rect.top + tol:
                    msg = f"Image and text overlap in 9:16: img bottom={img_box.rect.bottom} > txt top={txt_box.rect.top}"
                    violations.append(msg)
                    invalid_geometry += 1

    elif strategy == LayoutStrategy.QUOTE:
        quote_box = next((b for b in layout_graph.boxes if b.strategy_role in ("quote", "content")), None)
        attr_box = next((b for b in layout_graph.boxes if b.strategy_role in ("attribution", "author")), None)
        if quote_box and attr_box:
            if quote_box.rect.bottom > attr_box.rect.top + tol:
                msg = f"Quote and attribution overlap: quote bottom={quote_box.rect.bottom} > attr top={attr_box.rect.top}"
                violations.append(msg)
                invalid_geometry += 1

    # 9. Expected nodes check
    if expected_node_ids is not None:
        expected_set = set(expected_node_ids)
        missing = expected_set - seen_ids
        unexpected = seen_ids - expected_set
        if missing:
            msg = f"LayoutGraph is missing {len(missing)} expected node(s): {sorted(missing)}"
            violations.append(msg)
            missing_nodes += len(missing)
        if unexpected:
            msg = f"LayoutGraph contains {len(unexpected)} unexpected node(s): {sorted(unexpected)}"
            violations.append(msg)
            invalid_geometry += len(unexpected)

    if violations:
        raise LayoutPreflightFailedError(
            f"Layout preflight validation failed with {len(violations)} violation(s): {'; '.join(violations[:3])}",
            details={
                "scene_id": layout_graph.scene_id,
                "strategy": layout_graph.strategy.value,
                "violations_count": len(violations),
                "violations": violations,
                "frame_overflow": frame_overflow,
                "safe_zone_violations": safe_zone_violations,
                "content_clipping": content_clipping,
                "invalid_geometry": invalid_geometry,
                "missing_nodes": missing_nodes,
            },
        )

    return PreflightReport(
        valid=True,
        frame_overflow_count=frame_overflow,
        safe_zone_violation_count=safe_zone_violations,
        content_clipping_count=content_clipping,
        invalid_geometry_count=invalid_geometry,
        missing_node_count=missing_nodes,
        violations=[],
    )


@dataclass(frozen=True)
class GraphPreflightReport:
    """Diagnostic report for V2-04 routed graph geometry."""

    valid: bool
    endpoint_violation_count: int = 0
    orthogonal_violation_count: int = 0
    edge_node_intersection_count: int = 0
    edge_crossing_count: int = 0
    bend_count: int = 0
    total_edge_length: float = 0.0
    violations: list[str] = None


def validate_graph_layout(
    layout_graph: LayoutGraph,
    profile: FrameProfile | str | None = None,
    tol: float = 1e-2,
) -> GraphPreflightReport:
    """Validate routed-edge geometry for V2-04 graph LayoutGraphs."""
    if layout_graph.strategy != LayoutStrategy.DIRECTED_GRAPH:
        raise LayoutPreflightFailedError(
            "Graph layout preflight requires DIRECTED_GRAPH strategy",
            {
                "strategy": layout_graph.strategy.value,
                "expected_strategy": LayoutStrategy.DIRECTED_GRAPH.value,
            },
        )

    if profile is None:
        frame_prof = get_frame_profile(layout_graph.frame_profile_id)
    else:
        frame_prof = get_frame_profile(profile)
    content = frame_prof.get_zone("CONTENT")
    safe = frame_prof.safe_edge_rect
    from learnflow_v2.layout.graph_metrics import (
        compute_graph_metrics,
        edge_is_orthogonal,
        validate_routed_edge_endpoints,
    )
    from learnflow_v2.layout.schema import RoutingStyle

    boxes = {b.node_id: b.rect for b in layout_graph.boxes}
    violations: list[str] = []
    endpoint_v = 0
    ortho_v = 0
    for edge in layout_graph.routed_edges:
        if not validate_routed_edge_endpoints(edge, boxes, tol=2.0):
            endpoint_v += 1
            violations.append(f"Edge '{edge.edge_id}' endpoints are not on source/target boundaries")
        if edge.routing_style == RoutingStyle.ORTHOGONAL and not edge_is_orthogonal(edge, tol=1e-2):
            ortho_v += 1
            violations.append(f"Edge '{edge.edge_id}' is declared ORTHOGONAL but has diagonal segments")
        for pt in edge.points:
            if not safe.contains_point(pt.x, pt.y):
                violations.append(f"Edge '{edge.edge_id}' point leaves SAFE_EDGE")
            if not content.contains_point(pt.x, pt.y):
                violations.append(f"Edge '{edge.edge_id}' point leaves CONTENT/title-caption avoidance zone")

    metrics = compute_graph_metrics(layout_graph.routed_edges, boxes)
    if metrics.edge_node_intersection_count:
        violations.append(f"{metrics.edge_node_intersection_count} routed edge(s) intersect unrelated nodes")
    valid = not violations
    report = GraphPreflightReport(
        valid=valid,
        endpoint_violation_count=endpoint_v,
        orthogonal_violation_count=ortho_v,
        edge_node_intersection_count=metrics.edge_node_intersection_count,
        edge_crossing_count=metrics.edge_crossing_count,
        bend_count=metrics.bend_count,
        total_edge_length=metrics.total_edge_length,
        violations=violations,
    )
    if not valid:
        raise LayoutPreflightFailedError("Graph layout preflight failed", report.__dict__)
    return report
