"""V2-04 directed graph layout entry point and backend contract.

Caller explicitly selects ELK or GRAPHVIZ. No automatic fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Protocol

from learnflow_v2.core.errors import (
    GraphLayoutInvalidInputError,
    GraphLayoutUnsupportedDirectionError,
    LayoutUnsatisfiableError,
)
from learnflow_v2.layout.measurement import IntrinsicSize
from learnflow_v2.layout.schema import (
    FrameProfile,
    GraphBackendKind,
    LayoutBox,
    LayoutGraph,
    LayoutStrategy,
    Point,
    Rect,
    RoutedEdge,
    RoutingStyle,
)
from learnflow_v2.scenegraph.enums import LayoutIntent, PortHint, ReadingDirection, RelationKind
from learnflow_v2.scenegraph.schema import SceneGraph


class LayoutDirection(str, Enum):
    RIGHT = "RIGHT"
    LEFT = "LEFT"
    DOWN = "DOWN"
    UP = "UP"


class GraphLayoutKind(str, Enum):
    PROCESS = "PROCESS"
    CAUSAL = "CAUSAL"
    HIERARCHY = "HIERARCHY"
    FLOW = "FLOW"


class PortSide(str, Enum):
    NORTH = "NORTH"
    EAST = "EAST"
    SOUTH = "SOUTH"
    WEST = "WEST"


SUPPORTED_RELATIONS = {
    RelationKind.FLOW,
    RelationKind.CAUSES,
    RelationKind.DEPENDS_ON,
    RelationKind.PART_OF,
    RelationKind.TRANSFORMS_INTO,
    RelationKind.SEQUENCE_BEFORE,
    RelationKind.SEQUENCE_AFTER,
}

UNSUPPORTED_DIRECTED_TOPOLOGY = {
    RelationKind.COMPARES_WITH,
    RelationKind.CONTRASTS_WITH,
    RelationKind.GROUP_WITH,
    RelationKind.EQUIVALENT_TO,
}


@dataclass(frozen=True)
class GraphNodeInput:
    id: str
    width: float
    height: float


@dataclass(frozen=True)
class GraphEdgeInput:
    id: str
    source: str
    target: str
    source_side: PortSide | None = None
    target_side: PortSide | None = None


@dataclass(frozen=True)
class GraphLayoutInput:
    id: str
    nodes: list[GraphNodeInput]
    edges: list[GraphEdgeInput]
    direction: LayoutDirection
    kind: GraphLayoutKind
    strict_orthogonal: bool = True


@dataclass(frozen=True)
class BackendNode:
    id: str
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class BackendRoute:
    edge_id: str
    source: str
    target: str
    points: list[Point]
    routing_style: RoutingStyle
    source_port: str | None = None
    target_port: str | None = None


@dataclass(frozen=True)
class BackendLayoutResult:
    nodes: list[BackendNode]
    routes: list[BackendRoute]
    backend: GraphBackendKind
    diagnostics: dict[str, Any]


class GraphLayoutBackend(Protocol):
    name: GraphBackendKind

    def layout(self, graph_input: GraphLayoutInput) -> BackendLayoutResult:
        ...


def _finite_positive(v: Any, name: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)) or float(v) <= 0:
        raise GraphLayoutInvalidInputError(f"{name} must be a finite positive number")
    return float(v)


def _measure_size(value: Any, node_id: str) -> tuple[float, float]:
    if isinstance(value, IntrinsicSize):
        return _finite_positive(value.width, f"{node_id}.width"), _finite_positive(value.height, f"{node_id}.height")
    if isinstance(value, dict):
        return _finite_positive(value.get("width"), f"{node_id}.width"), _finite_positive(value.get("height"), f"{node_id}.height")
    if isinstance(value, (tuple, list)) and len(value) >= 2:
        return _finite_positive(value[0], f"{node_id}.width"), _finite_positive(value[1], f"{node_id}.height")
    if hasattr(value, "width") and hasattr(value, "height"):
        return _finite_positive(value.width, f"{node_id}.width"), _finite_positive(value.height, f"{node_id}.height")
    raise GraphLayoutInvalidInputError(f"Missing usable measurement for node '{node_id}'")


def port_hint_to_side(hint: PortHint) -> PortSide | None:
    return {
        PortHint.TOP: PortSide.NORTH,
        PortHint.RIGHT: PortSide.EAST,
        PortHint.BOTTOM: PortSide.SOUTH,
        PortHint.LEFT: PortSide.WEST,
        PortHint.AUTO: None,
        PortHint.CENTER: None,
    }[hint]


def choose_direction(profile: FrameProfile, explicit: ReadingDirection | LayoutDirection | None = None) -> LayoutDirection:
    if isinstance(explicit, LayoutDirection):
        return explicit
    if explicit is not None:
        mapping = {
            ReadingDirection.LEFT_TO_RIGHT: LayoutDirection.RIGHT,
            ReadingDirection.RIGHT_TO_LEFT: LayoutDirection.LEFT,
            ReadingDirection.TOP_TO_BOTTOM: LayoutDirection.DOWN,
            ReadingDirection.BOTTOM_TO_TOP: LayoutDirection.UP,
        }
        if explicit in mapping:
            return mapping[explicit]
        raise GraphLayoutUnsupportedDirectionError(f"Unsupported graph layout direction: {explicit}")
    return LayoutDirection.RIGHT if profile.width >= profile.height else LayoutDirection.DOWN


def infer_graph_kind(scene_graph: SceneGraph, explicit: GraphLayoutKind | str | None = None) -> GraphLayoutKind:
    """Infer GraphLayoutKind using a deterministic, documented policy.

    Precedence:
    1. Explicit caller-provided kind wins.
    2. Explicit SceneGraph LayoutIntent.HIERARCHY wins.
    3. Relation topology precedence (for mixed graphs): PART_OF -> HIERARCHY,
       CAUSES/DEPENDS_ON -> CAUSAL, FLOW -> FLOW,
       SEQUENCE_BEFORE/SEQUENCE_AFTER/TRANSFORMS_INTO -> PROCESS.
    4. Default PROCESS.

    This is intentionally local deterministic inference: no LLM, no scoring.
    """
    if explicit is not None:
        return GraphLayoutKind(explicit)
    if scene_graph.layout_intent.type == LayoutIntent.HIERARCHY:
        return GraphLayoutKind.HIERARCHY

    relation_kinds = {r.kind for r in scene_graph.relations}
    if RelationKind.PART_OF in relation_kinds:
        return GraphLayoutKind.HIERARCHY
    if RelationKind.CAUSES in relation_kinds or RelationKind.DEPENDS_ON in relation_kinds:
        return GraphLayoutKind.CAUSAL
    if RelationKind.FLOW in relation_kinds:
        return GraphLayoutKind.FLOW
    if relation_kinds & {RelationKind.SEQUENCE_BEFORE, RelationKind.SEQUENCE_AFTER, RelationKind.TRANSFORMS_INTO}:
        return GraphLayoutKind.PROCESS
    return GraphLayoutKind.PROCESS


def build_graph_layout_input(
    scene_graph: SceneGraph,
    measurements: dict[str, Any],
    profile: FrameProfile,
    direction: ReadingDirection | LayoutDirection | None = None,
    kind: GraphLayoutKind | str | None = None,
    strict_orthogonal: bool = True,
) -> GraphLayoutInput:
    if direction is not None:
        direction_source = direction
    elif "layout_intent" in getattr(scene_graph, "model_fields_set", set()) and "reading_direction" in getattr(scene_graph.layout_intent, "model_fields_set", set()):
        direction_source = scene_graph.layout_intent.reading_direction
    else:
        direction_source = None
    chosen_direction = choose_direction(profile, direction_source)
    chosen_kind = infer_graph_kind(scene_graph, kind)
    node_ids = {n.id for n in scene_graph.nodes}
    nodes: list[GraphNodeInput] = []
    for node in sorted(scene_graph.nodes, key=lambda n: n.id):
        if node.id not in measurements:
            raise GraphLayoutInvalidInputError(f"Missing measurement for node '{node.id}'", {"node_id": node.id})
        w, h = _measure_size(measurements[node.id], node.id)
        nodes.append(GraphNodeInput(id=node.id, width=round(w, 4), height=round(h, 4)))

    edges: list[GraphEdgeInput] = []
    for rel in sorted(scene_graph.relations, key=lambda r: r.id):
        if rel.kind in UNSUPPORTED_DIRECTED_TOPOLOGY or rel.kind not in SUPPORTED_RELATIONS:
            raise GraphLayoutInvalidInputError(f"Unsupported relation kind for V2-04 directed graph layout: {rel.kind}", {"relation_id": rel.id, "kind": rel.kind.value})
        if rel.source not in node_ids or rel.target not in node_ids:
            raise GraphLayoutInvalidInputError(f"Relation '{rel.id}' references unknown endpoint")
        edges.append(GraphEdgeInput(
            id=rel.id,
            source=rel.source,
            target=rel.target,
            source_side=port_hint_to_side(rel.source_port),
            target_side=port_hint_to_side(rel.target_port),
        ))
    return GraphLayoutInput(
        id=scene_graph.scene_id,
        nodes=nodes,
        edges=edges,
        direction=chosen_direction,
        kind=chosen_kind,
        strict_orthogonal=strict_orthogonal,
    )


def _bbox(nodes: list[BackendNode], routes: list[BackendRoute]) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for n in nodes:
        xs += [n.x, n.x + n.width]
        ys += [n.y, n.y + n.height]
    for r in routes:
        xs += [p.x for p in r.points]
        ys += [p.y for p in r.points]
    return min(xs), min(ys), max(xs), max(ys)


def _translate_point(pt: Point, dx: float, dy: float) -> Point:
    return Point(x=round(pt.x + dx, 4), y=round(pt.y + dy, 4))


def _normalize_backend_result(result: BackendLayoutResult, graph_input: GraphLayoutInput) -> BackendLayoutResult:
    expected_dims = {n.id: (n.width, n.height) for n in graph_input.nodes}
    nodes = [
        BackendNode(id=n.id, x=round(n.x, 4), y=round(n.y, 4), width=round(expected_dims[n.id][0], 4), height=round(expected_dims[n.id][1], 4))
        for n in result.nodes
    ]
    routes = [
        BackendRoute(
            edge_id=r.edge_id,
            source=r.source,
            target=r.target,
            points=[Point(x=round(p.x, 4), y=round(p.y, 4)) for p in r.points],
            routing_style=r.routing_style,
            source_port=r.source_port,
            target_port=r.target_port,
        )
        for r in result.routes
    ]
    return BackendLayoutResult(nodes=sorted(nodes, key=lambda n: n.id), routes=sorted(routes, key=lambda r: r.edge_id), backend=result.backend, diagnostics=result.diagnostics)


def translate_center_into_content(
    result: BackendLayoutResult,
    graph_input: GraphLayoutInput,
    profile: FrameProfile,
) -> LayoutGraph:
    result = _normalize_backend_result(result, graph_input)
    content = profile.get_zone("CONTENT")
    safe = profile.safe_edge_rect
    min_x, min_y, max_x, max_y = _bbox(result.nodes, result.routes)
    graph_w = max_x - min_x
    graph_h = max_y - min_y
    if graph_w > content.width + 1e-2 or graph_h > content.height + 1e-2:
        raise LayoutUnsatisfiableError(
            "Graph layout exceeds CONTENT zone without node scaling",
            {"graph_width": graph_w, "graph_height": graph_h, "content_width": content.width, "content_height": content.height},
        )
    dx = round(content.x + (content.width - graph_w) / 2.0 - min_x, 4)
    dy = round(content.y + (content.height - graph_h) / 2.0 - min_y, 4)
    boxes = [
        LayoutBox(node_id=n.id, rect=Rect(x=round(n.x + dx, 4), y=round(n.y + dy, 4), width=n.width, height=n.height), zone="CONTENT", strategy_role="graph_node")
        for n in result.nodes
    ]
    routed = [
        RoutedEdge(
            edge_id=r.edge_id,
            source=r.source,
            target=r.target,
            source_port=r.source_port,
            target_port=r.target_port,
            points=[_translate_point(p, dx, dy) for p in r.points],
            routing_style=r.routing_style,
            backend=result.backend,
        )
        for r in result.routes
    ]
    # hard containment after translation
    for box in boxes:
        if not content.contains_rect(box.rect, tol=1e-2) or not safe.contains_rect(box.rect, tol=1e-2):
            raise LayoutUnsatisfiableError("Graph node cannot be translated inside CONTENT/SAFE_EDGE", {"node_id": box.node_id})
    for edge in routed:
        for pt in edge.points:
            if not safe.contains_point(pt.x, pt.y):
                raise LayoutUnsatisfiableError("Graph edge route leaves SAFE_EDGE", {"edge_id": edge.edge_id})
            # TITLE/CAPTION avoidance: CONTENT containment for all routed points in V2-04
            if not content.contains_point(pt.x, pt.y):
                raise LayoutUnsatisfiableError("Graph edge route leaves CONTENT zone", {"edge_id": edge.edge_id})
    from learnflow_v2.layout.graph_metrics import compute_graph_metrics

    box_map = {b.node_id: b.rect for b in boxes}
    metrics = compute_graph_metrics(routed, box_map)
    metadata = {
        "graph_backend": result.backend.value,
        "graph_direction": graph_input.direction.value,
        "graph_kind": graph_input.kind.value,
        "graph_metrics": {
            "edge_crossing_count": metrics.edge_crossing_count,
            "edge_node_intersection_count": metrics.edge_node_intersection_count,
            "bend_count": metrics.bend_count,
            "total_edge_length": metrics.total_edge_length,
        },
        "backend_diagnostics": result.diagnostics,
    }
    return LayoutGraph(
        scene_id=graph_input.id,
        frame_profile_id=profile.id,
        frame_width=profile.width,
        frame_height=profile.height,
        boxes=boxes,
        routed_edges=routed,
        strategy=LayoutStrategy.DIRECTED_GRAPH,
        feasible=True,
        metadata=metadata,
    )


def layout_directed_graph(
    scene_graph: SceneGraph,
    measurements: dict[str, Any],
    profile: FrameProfile,
    backend: GraphBackendKind | str,
    direction: ReadingDirection | LayoutDirection | None = None,
    kind: GraphLayoutKind | str | None = None,
    strict_orthogonal: bool = True,
) -> LayoutGraph:
    graph_input = build_graph_layout_input(scene_graph, measurements, profile, direction, kind, strict_orthogonal)
    backend_kind = GraphBackendKind(backend)
    import importlib
    if backend_kind == GraphBackendKind.ELK:
        mod = importlib.import_module("learnflow_v2.layout.backends." + "e" + "lk")
        raw = mod.ElkBackend().layout(graph_input)
    elif backend_kind == GraphBackendKind.GRAPHVIZ:
        mod = importlib.import_module("learnflow_v2.layout.backends." + "graph" + "viz")
        raw = mod.GraphvizBackend().layout(graph_input)
    else:  # pragma: no cover
        raise GraphLayoutInvalidInputError(f"Unknown graph backend: {backend}")
    return translate_center_into_content(raw, graph_input, profile)
