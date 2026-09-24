"""Pure V2-04 graph geometry validation and observational metrics.

Detection only: no repair, no scoring, no ranking.
"""

from dataclasses import dataclass
import math
from itertools import combinations
from typing import Iterable

from learnflow_v2.layout.schema import Point, Rect, RoutedEdge, RoutingStyle

GEOM_TOL = 1e-3


@dataclass(frozen=True)
class GraphMetrics:
    edge_crossing_count: int
    edge_node_intersection_count: int
    bend_count: int
    total_edge_length: float


def _close(a: float, b: float, tol: float = GEOM_TOL) -> bool:
    return abs(a - b) <= tol


def point_on_rect_boundary(point: Point, rect: Rect, tol: float = GEOM_TOL) -> bool:
    x, y = point.x, point.y
    within_x = rect.left - tol <= x <= rect.right + tol
    within_y = rect.top - tol <= y <= rect.bottom + tol
    return within_x and within_y and (
        _close(x, rect.left, tol)
        or _close(x, rect.right, tol)
        or _close(y, rect.top, tol)
        or _close(y, rect.bottom, tol)
    )


def segment_is_orthogonal(a: Point, b: Point, tol: float = GEOM_TOL) -> bool:
    return _close(a.x, b.x, tol) or _close(a.y, b.y, tol)


def edge_is_orthogonal(edge: RoutedEdge, tol: float = GEOM_TOL) -> bool:
    return all(segment_is_orthogonal(a, b, tol) for a, b in zip(edge.points, edge.points[1:]))


def _orientation(a: Point, b: Point, c: Point, tol: float = GEOM_TOL) -> int:
    val = (b.y - a.y) * (c.x - b.x) - (b.x - a.x) * (c.y - b.y)
    if abs(val) <= tol:
        return 0
    return 1 if val > 0 else 2


def _on_segment(a: Point, b: Point, c: Point, tol: float = GEOM_TOL) -> bool:
    return (
        min(a.x, c.x) - tol <= b.x <= max(a.x, c.x) + tol
        and min(a.y, c.y) - tol <= b.y <= max(a.y, c.y) + tol
        and _orientation(a, b, c, tol) == 0
    )


def segments_intersect(a1: Point, a2: Point, b1: Point, b2: Point, tol: float = GEOM_TOL) -> bool:
    o1 = _orientation(a1, a2, b1, tol)
    o2 = _orientation(a1, a2, b2, tol)
    o3 = _orientation(b1, b2, a1, tol)
    o4 = _orientation(b1, b2, a2, tol)
    if o1 != o2 and o3 != o4:
        return True
    return (
        (o1 == 0 and _on_segment(a1, b1, a2, tol))
        or (o2 == 0 and _on_segment(a1, b2, a2, tol))
        or (o3 == 0 and _on_segment(b1, a1, b2, tol))
        or (o4 == 0 and _on_segment(b1, a2, b2, tol))
    )


def segment_intersects_rect(a: Point, b: Point, rect: Rect, tol: float = GEOM_TOL, boundary_counts: bool = True) -> bool:
    # Interior endpoint means intersection.
    def inside_interior(p: Point) -> bool:
        return rect.left + tol < p.x < rect.right - tol and rect.top + tol < p.y < rect.bottom - tol

    if inside_interior(a) or inside_interior(b):
        return True
    corners = [
        Point(x=rect.left, y=rect.top),
        Point(x=rect.right, y=rect.top),
        Point(x=rect.right, y=rect.bottom),
        Point(x=rect.left, y=rect.bottom),
    ]
    for c1, c2 in zip(corners, corners[1:] + corners[:1]):
        if segments_intersect(a, b, c1, c2, tol):
            if boundary_counts:
                return True
            # If touching only at the segment's own endpoint on a terminal node, caller may ignore.
            return True
    return False


def polyline_intersects_rect(points: list[Point], rect: Rect, tol: float = GEOM_TOL) -> bool:
    return any(segment_intersects_rect(a, b, rect, tol, boundary_counts=True) for a, b in zip(points, points[1:]))


def edge_length(edge: RoutedEdge) -> float:
    return round(sum(math.hypot(b.x - a.x, b.y - a.y) for a, b in zip(edge.points, edge.points[1:])), 4)


def edge_bend_count(edge: RoutedEdge, tol: float = GEOM_TOL) -> int:
    bends = 0
    for a, b, c in zip(edge.points, edge.points[1:], edge.points[2:]):
        v1 = (b.x - a.x, b.y - a.y)
        v2 = (c.x - b.x, c.y - b.y)
        if abs(v1[0] * v2[1] - v1[1] * v2[0]) > tol:
            bends += 1
    return bends


def count_edge_node_intersections(edges: Iterable[RoutedEdge], boxes: dict[str, Rect], tol: float = GEOM_TOL) -> int:
    count = 0
    for edge in edges:
        for node_id, rect in boxes.items():
            if node_id in {edge.source, edge.target}:
                continue
            if polyline_intersects_rect(edge.points, rect, tol):
                count += 1
    return count


def count_edge_crossings(edges: list[RoutedEdge], tol: float = GEOM_TOL) -> int:
    count = 0
    for e1, e2 in combinations(edges, 2):
        if {e1.source, e1.target} & {e2.source, e2.target}:
            continue
        for a1, a2 in zip(e1.points, e1.points[1:]):
            for b1, b2 in zip(e2.points, e2.points[1:]):
                # shared geometric endpoints are not counted as crossings
                if any(math.hypot(p.x - q.x, p.y - q.y) <= tol for p in (a1, a2) for q in (b1, b2)):
                    continue
                if segments_intersect(a1, a2, b1, b2, tol):
                    count += 1
    return count


def compute_graph_metrics(edges: list[RoutedEdge], boxes: dict[str, Rect], tol: float = GEOM_TOL) -> GraphMetrics:
    return GraphMetrics(
        edge_crossing_count=count_edge_crossings(edges, tol),
        edge_node_intersection_count=count_edge_node_intersections(edges, boxes, tol),
        bend_count=sum(edge_bend_count(e, tol) for e in edges),
        total_edge_length=round(sum(edge_length(e) for e in edges), 4),
    )


def validate_routed_edge_endpoints(edge: RoutedEdge, boxes: dict[str, Rect], tol: float = 2.0) -> bool:
    if edge.source not in boxes or edge.target not in boxes or len(edge.points) < 2:
        return False
    return point_on_rect_boundary(edge.points[0], boxes[edge.source], tol) and point_on_rect_boundary(edge.points[-1], boxes[edge.target], tol)


def validate_orthogonal_edges(edges: Iterable[RoutedEdge], tol: float = GEOM_TOL) -> bool:
    return all(e.routing_style != RoutingStyle.ORTHOGONAL or edge_is_orthogonal(e, tol) for e in edges)
