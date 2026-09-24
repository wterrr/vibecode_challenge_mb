"""V2-04 graph layout tests."""

import json
import math
import shutil

import pytest
from pydantic import ValidationError

from learnflow_v2.core.errors import (
    GraphLayoutBackendUnavailableError,
    GraphLayoutInvalidInputError,
    GraphLayoutUnsupportedCapabilityError,
    GraphLayoutUnsupportedDirectionError,
    LayoutUnsatisfiableError,
)
from learnflow_v2.layout.graph import (
    BackendLayoutResult,
    BackendNode,
    BackendRoute,
    GraphEdgeInput,
    GraphLayoutInput,
    GraphLayoutKind,
    GraphNodeInput,
    LayoutDirection,
    PortSide,
    build_graph_layout_input,
    choose_direction,
    layout_directed_graph,
    translate_center_into_content,
)
from learnflow_v2.layout.graph_metrics import (
    compute_graph_metrics,
    edge_bend_count,
    edge_is_orthogonal,
    edge_length,
    point_on_rect_boundary,
    polyline_intersects_rect,
    segment_intersects_rect,
    segments_intersect,
    validate_routed_edge_endpoints,
)
from learnflow_v2.layout.profiles import create_frame_profile_16_9, create_frame_profile_9_16
from learnflow_v2.layout.schema import (
    FrameInsets,
    FrameProfile,
    GraphBackendKind,
    GridSpec,
    LayoutBox,
    LayoutGraph,
    LayoutStrategy,
    Point,
    Rect,
    RoutedEdge,
    RoutingStyle,
)
from learnflow_v2.scenegraph.enums import LayoutIntent, NodeKind, PortHint, ReadingDirection, RelationKind
from learnflow_v2.scenegraph.schema import LayoutIntentSpec, SceneGraph, SceneNode, SceneRelation


def scene(edges, *, direction=None, intent=LayoutIntent.PROCESS):
    kwargs = {}
    if direction is not None:
        kwargs["layout_intent"] = LayoutIntentSpec(type=intent, reading_direction=direction)
    else:
        kwargs["layout_intent"] = LayoutIntentSpec(type=intent)
    nodes = sorted({x for e in edges for x in e[:2]})
    return SceneGraph(
        scene_id="s",
        nodes=[SceneNode(id=n, kind=NodeKind.CONCEPT, label=n) for n in nodes],
        relations=[
            SceneRelation(
                id=f"e{i}",
                source=s,
                target=t,
                kind=k,
                source_port=sp if sp else PortHint.AUTO,
                target_port=tp if tp else PortHint.AUTO,
            )
            for i, (s, t, k, *ports) in enumerate(edges)
            for sp, tp in [(ports + [None, None])[:2]]
        ],
        layout_intent=kwargs["layout_intent"],
    )


def meas(sg, w=90.0, h=45.0):
    return {n.id: (w, h) for n in sg.nodes}


def fake_result(nodes, edges, backend=GraphBackendKind.ELK, style=RoutingStyle.ORTHOGONAL):
    bnodes = [BackendNode(id=n, x=i * 160.0, y=0.0, width=90.0, height=45.0) for i, n in enumerate(nodes)]
    idx = {n.id: n for n in bnodes}
    routes = []
    for i, (s, t) in enumerate(edges):
        a = idx[s]; b = idx[t]
        routes.append(BackendRoute(edge_id=f"e{i}", source=s, target=t, points=[
            Point(x=a.x + a.width, y=a.y + a.height / 2),
            Point(x=b.x, y=b.y + b.height / 2),
        ], routing_style=style))
    return BackendLayoutResult(nodes=bnodes, routes=routes, backend=backend, diagnostics={})


@pytest.mark.parametrize("bad", ["10", True, False, float("nan"), float("inf"), float("-inf")])
def test_rect_rejects_non_real_numbers(bad):
    with pytest.raises((ValidationError, ValueError)):
        Rect(x=0, y=0, width=bad, height=10)


@pytest.mark.parametrize("model,kwargs", [
    (FrameInsets, {"top": "1", "right": 0, "bottom": 0, "left": 0}),
    (GridSpec, {"columns": "12"}),
    (GridSpec, {"columns": True}),
])
def test_numeric_artifacts_are_strict(model, kwargs):
    with pytest.raises((ValidationError, ValueError)):
        model(**kwargs)


def test_frame_profile_rejects_numeric_strings():
    with pytest.raises(Exception):
        create_frame_profile_16_9(width="1280", height=720)


def test_layout_graph_rejects_numeric_strings():
    with pytest.raises(ValidationError):
        LayoutGraph(scene_id="s", frame_profile_id="p", frame_width="1280", frame_height=720, boxes=[], strategy=LayoutStrategy.CONCEPT_CARD)


def test_point_and_routed_edge_are_strict_and_sorted():
    e2 = RoutedEdge(edge_id="b", source="a", target="c", points=[Point(x=0, y=0), Point(x=1, y=0)], routing_style=RoutingStyle.POLYLINE, backend=GraphBackendKind.GRAPHVIZ)
    e1 = RoutedEdge(edge_id="a", source="a", target="b", points=[Point(x=0, y=0), Point(x=1, y=0)], routing_style=RoutingStyle.POLYLINE, backend=GraphBackendKind.GRAPHVIZ)
    lg = LayoutGraph(scene_id="s", frame_profile_id="16:9_1280x720", frame_width=1280, frame_height=720, boxes=[], routed_edges=[e2, e1], strategy=LayoutStrategy.CONCEPT_CARD)
    assert [e.edge_id for e in lg.routed_edges] == ["a", "b"]
    with pytest.raises(ValidationError):
        Point(x="0", y=0)


@pytest.mark.parametrize("explicit,expected", [
    (ReadingDirection.LEFT_TO_RIGHT, LayoutDirection.RIGHT),
    (ReadingDirection.RIGHT_TO_LEFT, LayoutDirection.LEFT),
    (ReadingDirection.TOP_TO_BOTTOM, LayoutDirection.DOWN),
    (ReadingDirection.BOTTOM_TO_TOP, LayoutDirection.UP),
])
def test_reading_direction_mapping(explicit, expected):
    assert choose_direction(create_frame_profile_16_9(), explicit) == expected


@pytest.mark.parametrize("unsupported", [ReadingDirection.RADIAL, ReadingDirection.BIDIRECTIONAL])
def test_unsupported_direction(unsupported):
    with pytest.raises(GraphLayoutUnsupportedDirectionError):
        choose_direction(create_frame_profile_16_9(), unsupported)


def test_aspect_defaults():
    assert choose_direction(create_frame_profile_16_9(), None) == LayoutDirection.RIGHT
    assert choose_direction(create_frame_profile_9_16(), None) == LayoutDirection.DOWN


@pytest.mark.parametrize("kind", [RelationKind.FLOW, RelationKind.CAUSES, RelationKind.DEPENDS_ON, RelationKind.PART_OF, RelationKind.TRANSFORMS_INTO, RelationKind.SEQUENCE_BEFORE, RelationKind.SEQUENCE_AFTER])
def test_supported_relations_build(kind):
    sg = scene([("a", "b", kind)])
    gi = build_graph_layout_input(sg, meas(sg), create_frame_profile_16_9(), direction=LayoutDirection.RIGHT)
    assert gi.edges[0].source == "a" and gi.edges[0].target == "b"


@pytest.mark.parametrize("kind", [RelationKind.COMPARES_WITH, RelationKind.CONTRASTS_WITH, RelationKind.GROUP_WITH, RelationKind.EQUIVALENT_TO])
def test_unsupported_relations_rejected(kind):
    sg = scene([("a", "b", kind)])
    with pytest.raises(GraphLayoutInvalidInputError):
        build_graph_layout_input(sg, meas(sg), create_frame_profile_16_9())


def test_missing_measurement_rejected():
    sg = scene([("a", "b", RelationKind.FLOW)])
    with pytest.raises(GraphLayoutInvalidInputError):
        build_graph_layout_input(sg, {"a": (10, 10)}, create_frame_profile_16_9())


def test_port_mapping_explicit_and_auto():
    sg = scene([("a", "b", RelationKind.FLOW, PortHint.RIGHT, PortHint.LEFT), ("a", "c", RelationKind.FLOW, PortHint.AUTO, PortHint.CENTER)])
    gi = build_graph_layout_input(sg, meas(sg), create_frame_profile_16_9(), direction=LayoutDirection.RIGHT)
    assert gi.edges[0].source_side == PortSide.EAST
    assert gi.edges[0].target_side == PortSide.WEST
    assert gi.edges[1].source_side is None and gi.edges[1].target_side is None


@pytest.mark.parametrize("edges", [
    [("a", "b", RelationKind.FLOW), ("b", "c", RelationKind.FLOW)],
    [("a", "b", RelationKind.FLOW), ("a", "c", RelationKind.FLOW)],
    [("a", "c", RelationKind.FLOW), ("b", "c", RelationKind.FLOW)],
    [("a", "b", RelationKind.FLOW), ("a", "c", RelationKind.FLOW), ("b", "d", RelationKind.FLOW), ("c", "d", RelationKind.FLOW)],
    [("a", "b", RelationKind.CAUSES), ("b", "c", RelationKind.CAUSES), ("c", "a", RelationKind.CAUSES)],
    [("root", "child_a", RelationKind.PART_OF), ("root", "child_b", RelationKind.PART_OF), ("root", "child_c", RelationKind.PART_OF)],
])
def test_translate_center_process_branch_merge_diamond_cycle_hierarchy(edges):
    sg = scene(edges)
    gi = build_graph_layout_input(sg, meas(sg), create_frame_profile_16_9(), direction=LayoutDirection.RIGHT)
    result = fake_result([n.id for n in gi.nodes], [(e.source, e.target) for e in gi.edges])
    lg = translate_center_into_content(result, gi, create_frame_profile_16_9())
    assert len(lg.boxes) == len(gi.nodes)
    assert len(lg.routed_edges) == len(gi.edges)
    assert lg.metadata["graph_metrics"]["edge_node_intersection_count"] >= 0


def test_unsat_no_node_scaling():
    sg = scene([("a", "b", RelationKind.FLOW)])
    gi = build_graph_layout_input(sg, {"a": (1000, 400), "b": (1000, 400)}, create_frame_profile_16_9(), direction=LayoutDirection.RIGHT)
    result = BackendLayoutResult(nodes=[
        BackendNode("a", 0, 0, 1000, 400),
        BackendNode("b", 1200, 0, 1000, 400),
    ], routes=[BackendRoute("e0", "a", "b", [Point(x=1000, y=200), Point(x=1200, y=200)], RoutingStyle.ORTHOGONAL)], backend=GraphBackendKind.ELK, diagnostics={})
    with pytest.raises(LayoutUnsatisfiableError):
        translate_center_into_content(result, gi, create_frame_profile_16_9())


def test_geometry_helpers():
    r = Rect(x=10, y=10, width=30, height=20)
    assert point_on_rect_boundary(Point(x=10, y=20), r)
    assert segment_intersects_rect(Point(x=0, y=20), Point(x=50, y=20), r)
    assert segment_intersects_rect(Point(x=20, y=0), Point(x=20, y=50), r)
    assert segment_intersects_rect(Point(x=0, y=0), Point(x=50, y=50), r)
    assert polyline_intersects_rect([Point(x=0, y=20), Point(x=50, y=20)], r)
    assert segments_intersect(Point(x=0, y=0), Point(x=10, y=10), Point(x=0, y=10), Point(x=10, y=0))


def test_metrics_crossing_bends_length_and_endpoints():
    box = {"a": Rect(x=0, y=0, width=20, height=20), "b": Rect(x=100, y=0, width=20, height=20), "c": Rect(x=40, y=40, width=20, height=20), "d": Rect(x=40, y=80, width=20, height=20)}
    e1 = RoutedEdge(edge_id="e1", source="a", target="b", points=[Point(x=20, y=10), Point(x=100, y=10)], routing_style=RoutingStyle.ORTHOGONAL, backend=GraphBackendKind.ELK)
    e2 = RoutedEdge(edge_id="e2", source="c", target="d", points=[Point(x=50, y=0), Point(x=50, y=100)], routing_style=RoutingStyle.ORTHOGONAL, backend=GraphBackendKind.ELK)
    m = compute_graph_metrics([e1, e2], box)
    assert m.edge_crossing_count == 1
    assert edge_bend_count(e2) == 0
    assert edge_length(e1) == 80
    assert edge_is_orthogonal(e1)
    assert validate_routed_edge_endpoints(e1, box)


def test_shared_endpoint_crossing_not_counted():
    box = {"a": Rect(x=0, y=0, width=20, height=20), "b": Rect(x=100, y=0, width=20, height=20), "c": Rect(x=0, y=100, width=20, height=20)}
    e1 = RoutedEdge(edge_id="e1", source="a", target="b", points=[Point(x=20, y=10), Point(x=100, y=10)], routing_style=RoutingStyle.ORTHOGONAL, backend=GraphBackendKind.ELK)
    e2 = RoutedEdge(edge_id="e2", source="a", target="c", points=[Point(x=20, y=10), Point(x=10, y=100)], routing_style=RoutingStyle.POLYLINE, backend=GraphBackendKind.GRAPHVIZ)
    assert compute_graph_metrics([e1, e2], box).edge_crossing_count == 0


def test_graphviz_real_dot_simple_dag_and_determinism():
    if not shutil.which("dot"):
        pytest.skip("dot unavailable")
    sg = scene([("a", "b", RelationKind.FLOW), ("b", "c", RelationKind.FLOW)])
    profile = create_frame_profile_16_9()
    lg1 = layout_directed_graph(sg, meas(sg), profile, GraphBackendKind.GRAPHVIZ, strict_orthogonal=False)
    lg2 = layout_directed_graph(sg, meas(sg), profile, GraphBackendKind.GRAPHVIZ, strict_orthogonal=False)
    assert lg1.model_dump(mode="json") == lg2.model_dump(mode="json")
    assert len(lg1.boxes) == 3 and len(lg1.routed_edges) == 2
    assert {e.routing_style for e in lg1.routed_edges} == {RoutingStyle.POLYLINE}


def test_graphviz_fixed_port_limitation_explicit():
    if not shutil.which("dot"):
        pytest.skip("dot unavailable")
    sg = scene([("a", "b", RelationKind.FLOW, PortHint.RIGHT, PortHint.LEFT)])
    with pytest.raises(GraphLayoutUnsupportedCapabilityError):
        layout_directed_graph(sg, meas(sg), create_frame_profile_16_9(), GraphBackendKind.GRAPHVIZ, strict_orthogonal=True)


def test_graphviz_backend_unavailable_simulation(monkeypatch):
    from learnflow_v2.layout.backends import graphviz
    monkeypatch.setattr(graphviz.shutil, "which", lambda _: None)
    sg = scene([("a", "b", RelationKind.FLOW)])
    with pytest.raises(GraphLayoutBackendUnavailableError):
        layout_directed_graph(sg, meas(sg), create_frame_profile_16_9(), GraphBackendKind.GRAPHVIZ, strict_orthogonal=False)


def test_malformed_backend_output_rejected():
    from learnflow_v2.layout.backends.graphviz import GraphvizBackend
    with pytest.raises(Exception):
        GraphvizBackend()._parse({"bb": "0,0,10,10", "objects": [], "edges": []}, GraphLayoutInput("s", [GraphNodeInput("a", 1, 1)], [], LayoutDirection.RIGHT, GraphLayoutKind.PROCESS))


def test_no_future_modules_present():
    import pathlib
    root = pathlib.Path("learnflow_v2/layout")
    forbidden = ["continuity.py", "motion", "render", "verification"]
    assert all(not (root / f).exists() for f in forbidden)


# --- V2-04 FINAL HARDENING additions ---

def _require_real_elk():
    from learnflow_v2.layout.backends.elk import ELKJS_REQUIRED_MESSAGE, is_available
    assert is_available(), ELKJS_REQUIRED_MESSAGE


def _assert_directed_graph_layout_ok(lg, expected_nodes, expected_edges, kind, profile):
    from learnflow_v2.layout.preflight import validate_graph_layout, validate_layout_graph
    assert lg.strategy == LayoutStrategy.DIRECTED_GRAPH
    assert lg.metadata["graph_kind"] == GraphLayoutKind(kind).value
    assert {b.node_id for b in lg.boxes} == set(expected_nodes)
    assert {e.edge_id for e in lg.routed_edges} == set(expected_edges)
    boxes = {b.node_id: b.rect for b in lg.boxes}
    for edge in lg.routed_edges:
        assert edge.routing_style == RoutingStyle.ORTHOGONAL
        assert edge_is_orthogonal(edge)
        assert validate_routed_edge_endpoints(edge, boxes)
    validate_layout_graph(lg, profile=profile, expected_node_ids=set(expected_nodes))
    report = validate_graph_layout(lg, profile=profile)
    assert report.valid
    assert report.edge_node_intersection_count == 0


def test_graph_artifact_uses_directed_graph_strategy_not_concept_card():
    sg = scene([("a", "b", RelationKind.FLOW)])
    gi = build_graph_layout_input(sg, meas(sg), create_frame_profile_16_9(), direction=LayoutDirection.RIGHT, kind=GraphLayoutKind.FLOW)
    result = fake_result([n.id for n in gi.nodes], [(e.source, e.target) for e in gi.edges])
    lg = translate_center_into_content(result, gi, create_frame_profile_16_9())
    assert lg.strategy == LayoutStrategy.DIRECTED_GRAPH
    assert lg.metadata["graph_kind"] == GraphLayoutKind.FLOW.value


@pytest.mark.parametrize("intent,rel_kind,expected", [
    (LayoutIntent.HIERARCHY, RelationKind.FLOW, GraphLayoutKind.HIERARCHY),
    (LayoutIntent.PROCESS, RelationKind.PART_OF, GraphLayoutKind.HIERARCHY),
    (LayoutIntent.PROCESS, RelationKind.CAUSES, GraphLayoutKind.CAUSAL),
    (LayoutIntent.PROCESS, RelationKind.DEPENDS_ON, GraphLayoutKind.CAUSAL),
    (LayoutIntent.PROCESS, RelationKind.FLOW, GraphLayoutKind.FLOW),
    (LayoutIntent.PROCESS, RelationKind.SEQUENCE_BEFORE, GraphLayoutKind.PROCESS),
    (LayoutIntent.PROCESS, RelationKind.SEQUENCE_AFTER, GraphLayoutKind.PROCESS),
    (LayoutIntent.PROCESS, RelationKind.TRANSFORMS_INTO, GraphLayoutKind.PROCESS),
])
def test_deterministic_graph_kind_inference_policy(intent, rel_kind, expected):
    from learnflow_v2.layout.graph import infer_graph_kind
    sg = scene([("a", "b", rel_kind)], intent=intent)
    assert infer_graph_kind(sg) == expected


@pytest.mark.parametrize("edges,kind", [
    ([("a", "b", RelationKind.FLOW), ("b", "c", RelationKind.FLOW)], GraphLayoutKind.PROCESS),
    ([("a", "b", RelationKind.FLOW), ("a", "c", RelationKind.FLOW), ("b", "d", RelationKind.FLOW), ("c", "d", RelationKind.FLOW)], GraphLayoutKind.FLOW),
    ([("a", "b", RelationKind.CAUSES), ("b", "c", RelationKind.CAUSES), ("c", "a", RelationKind.CAUSES)], GraphLayoutKind.CAUSAL),
    ([("root", "a", RelationKind.PART_OF), ("root", "b", RelationKind.PART_OF), ("root", "c", RelationKind.PART_OF)], GraphLayoutKind.HIERARCHY),
])
def test_real_elk_chain_diamond_cycle_hierarchy(edges, kind):
    _require_real_elk()
    profile = create_frame_profile_16_9()
    sg = scene(edges, intent=LayoutIntent.HIERARCHY if kind == GraphLayoutKind.HIERARCHY else LayoutIntent.PROCESS)
    lg1 = layout_directed_graph(sg, meas(sg, 110, 54), profile, GraphBackendKind.ELK, kind=kind)
    lg2 = layout_directed_graph(sg, meas(sg, 110, 54), profile, GraphBackendKind.ELK, kind=kind)
    _assert_directed_graph_layout_ok(lg1, [n.id for n in sg.nodes], [r.id for r in sg.relations], kind, profile)
    assert json.dumps(lg1.model_dump(mode="json"), sort_keys=True) == json.dumps(lg2.model_dump(mode="json"), sort_keys=True)


@pytest.mark.parametrize("source_hint,target_hint,source_side,target_side,direction", [
    (PortHint.RIGHT, PortHint.LEFT, "right", "left", LayoutDirection.RIGHT),
    (PortHint.BOTTOM, PortHint.TOP, "bottom", "top", LayoutDirection.DOWN),
])
def test_real_elk_fixed_ports_horizontal_vertical(source_hint, target_hint, source_side, target_side, direction):
    _require_real_elk()
    profile = create_frame_profile_16_9()
    sg = scene([("a", "b", RelationKind.FLOW, source_hint, target_hint)])
    lg = layout_directed_graph(sg, meas(sg, 120, 60), profile, GraphBackendKind.ELK, direction=direction, kind=GraphLayoutKind.FLOW)
    _assert_directed_graph_layout_ok(lg, ["a", "b"], ["e0"], GraphLayoutKind.FLOW, profile)
    boxes = {b.node_id: b.rect for b in lg.boxes}
    edge = lg.routed_edges[0]
    src = boxes["a"]; tgt = boxes["b"]
    if source_side == "right":
        assert abs(edge.points[0].x - src.right) <= 2.0
    else:
        assert abs(edge.points[0].y - src.bottom) <= 2.0
    if target_side == "left":
        assert abs(edge.points[-1].x - tgt.left) <= 2.0
    else:
        assert abs(edge.points[-1].y - tgt.top) <= 2.0


def test_real_elk_auto_ports_and_profile_defaults_16_9_right_9_16_down():
    _require_real_elk()
    sg = scene([("a", "b", RelationKind.FLOW)])
    for profile, expected_direction in [(create_frame_profile_16_9(), LayoutDirection.RIGHT), (create_frame_profile_9_16(), LayoutDirection.DOWN)]:
        lg = layout_directed_graph(sg, meas(sg, 110, 54), profile, GraphBackendKind.ELK, kind=GraphLayoutKind.FLOW)
        assert lg.metadata["graph_direction"] == expected_direction.value
        _assert_directed_graph_layout_ok(lg, ["a", "b"], ["e0"], GraphLayoutKind.FLOW, profile)


def _parser_graph_input():
    return GraphLayoutInput(
        "s",
        [GraphNodeInput("a", 100, 50), GraphNodeInput("b", 100, 50)],
        [GraphEdgeInput("e0", "a", "b")],
        LayoutDirection.RIGHT,
        GraphLayoutKind.PROCESS,
    )


def _valid_elk_raw():
    return {
        "children": [
            {"id": "a", "x": 0, "y": 0, "width": 100, "height": 50},
            {"id": "b", "x": 200, "y": 0, "width": 100, "height": 50},
        ],
        "edges": [
            {"id": "e0", "sections": [{"startPoint": {"x": 100, "y": 25}, "bendPoints": [], "endPoint": {"x": 200, "y": 25}}]},
        ],
    }


@pytest.mark.parametrize("mutate", [
    lambda raw: raw["children"].__setitem__(0, {**raw["children"][0], "id": "z"}),   # unknown node ID
    lambda raw: raw["children"].pop(),                                               # missing node
    lambda raw: raw["edges"].__setitem__(0, {**raw["edges"][0], "id": "z"}),          # unknown edge ID
    lambda raw: raw["edges"].__setitem__(0, {k: v for k, v in raw["edges"][0].items() if k != "id"}),  # missing edge ID
    lambda raw: raw["edges"][0].pop("sections"),                                     # no sections
    lambda raw: raw["edges"][0]["sections"][0].pop("startPoint"),                    # missing start
    lambda raw: raw["edges"][0]["sections"][0].pop("endPoint"),                      # missing end
    lambda raw: raw["edges"][0]["sections"][0]["startPoint"].__setitem__("x", float("nan")), # nonfinite
    lambda raw: raw["children"][0].__setitem__("width", 0),                          # invalid dimensions
])
def test_direct_elk_parser_malformed_cases_map_to_backend_error_only(mutate):
    from learnflow_v2.core.errors import GraphLayoutBackendError
    from learnflow_v2.layout.backends.elk import ElkBackend
    raw = _valid_elk_raw()
    mutate(raw)
    with pytest.raises(GraphLayoutBackendError) as exc:
        ElkBackend()._parse(raw, _parser_graph_input())
    assert exc.value.code == "GRAPH_LAYOUT_BACKEND_ERROR"


def _manual_graph_for_preflight(points, *, boxes=None):
    profile = create_frame_profile_16_9()
    content = profile.get_zone("CONTENT")
    if boxes is None:
        boxes = [
            LayoutBox(node_id="a", rect=Rect(x=content.x + 100, y=content.y + 100, width=80, height=40), zone="CONTENT", strategy_role="graph_node"),
            LayoutBox(node_id="b", rect=Rect(x=content.x + 400, y=content.y + 100, width=80, height=40), zone="CONTENT", strategy_role="graph_node"),
        ]
    edge = RoutedEdge(edge_id="e0", source="a", target="b", points=points, routing_style=RoutingStyle.ORTHOGONAL, backend=GraphBackendKind.ELK)
    return LayoutGraph(scene_id="pf", frame_profile_id=profile.id, frame_width=profile.width, frame_height=profile.height, boxes=boxes, routed_edges=[edge], strategy=LayoutStrategy.DIRECTED_GRAPH), profile


@pytest.mark.parametrize("case", ["source_endpoint", "target_endpoint", "diagonal", "collision", "content", "safe"])
def test_direct_graph_preflight_negative_cases(case):
    from learnflow_v2.core.errors import LayoutPreflightFailedError
    from learnflow_v2.layout.preflight import validate_graph_layout
    profile = create_frame_profile_16_9()
    c = profile.get_zone("CONTENT")
    a = LayoutBox(node_id="a", rect=Rect(x=c.x + 100, y=c.y + 100, width=80, height=40), zone="CONTENT", strategy_role="graph_node")
    b = LayoutBox(node_id="b", rect=Rect(x=c.x + 400, y=c.y + 100, width=80, height=40), zone="CONTENT", strategy_role="graph_node")
    if case == "source_endpoint":
        pts = [Point(x=a.rect.center_x, y=a.rect.center_y), Point(x=b.rect.left, y=b.rect.center_y)]
        boxes = [a, b]
    elif case == "target_endpoint":
        pts = [Point(x=a.rect.right, y=a.rect.center_y), Point(x=b.rect.center_x, y=b.rect.center_y)]
        boxes = [a, b]
    elif case == "diagonal":
        pts = [Point(x=a.rect.right, y=a.rect.center_y), Point(x=b.rect.left, y=b.rect.center_y + 30)]
        boxes = [a, b]
    elif case == "collision":
        blocker = LayoutBox(node_id="c", rect=Rect(x=c.x + 250, y=c.y + 90, width=80, height=60), zone="CONTENT", strategy_role="graph_node")
        pts = [Point(x=a.rect.right, y=a.rect.center_y), Point(x=b.rect.left, y=b.rect.center_y)]
        boxes = [a, b, blocker]
    elif case == "content":
        pts = [Point(x=a.rect.right, y=a.rect.center_y), Point(x=a.rect.right + 20, y=profile.get_zone("TITLE").center_y), Point(x=b.rect.left, y=b.rect.center_y)]
        boxes = [a, b]
    else:
        pts = [Point(x=a.rect.right, y=a.rect.center_y), Point(x=profile.safe_edge_rect.left - 5, y=a.rect.center_y), Point(x=b.rect.left, y=b.rect.center_y)]
        boxes = [a, b]
    edge = RoutedEdge(edge_id="e0", source="a", target="b", points=pts, routing_style=RoutingStyle.ORTHOGONAL, backend=GraphBackendKind.ELK)
    lg = LayoutGraph(scene_id="pf", frame_profile_id=profile.id, frame_width=profile.width, frame_height=profile.height, boxes=boxes, routed_edges=[edge], strategy=LayoutStrategy.DIRECTED_GRAPH)
    with pytest.raises(LayoutPreflightFailedError):
        validate_graph_layout(lg, profile=profile)


def test_graphviz_real_diamond_cycle_and_fixed_port_rejection():
    if not shutil.which("dot"):
        pytest.skip("dot unavailable")
    profile = create_frame_profile_16_9()
    for edges in [
        [("a", "b", RelationKind.FLOW), ("a", "c", RelationKind.FLOW), ("b", "d", RelationKind.FLOW), ("c", "d", RelationKind.FLOW)],
        [("a", "b", RelationKind.FLOW), ("b", "c", RelationKind.FLOW), ("c", "a", RelationKind.FLOW)],
    ]:
        sg = scene(edges)
        lg = layout_directed_graph(sg, meas(sg), profile, GraphBackendKind.GRAPHVIZ, strict_orthogonal=False)
        assert lg.strategy == LayoutStrategy.DIRECTED_GRAPH
        assert {e.routing_style for e in lg.routed_edges} == {RoutingStyle.POLYLINE}
    sg_fixed = scene([("a", "b", RelationKind.FLOW, PortHint.RIGHT, PortHint.LEFT)])
    with pytest.raises(GraphLayoutUnsupportedCapabilityError):
        layout_directed_graph(sg_fixed, meas(sg_fixed), profile, GraphBackendKind.GRAPHVIZ, strict_orthogonal=True)


def test_preflight_v2_graph_unavailable_is_nonzero(tmp_path):
    import os
    import subprocess
    import sys
    env = os.environ.copy()
    env["PATH"] = str(tmp_path)
    res = subprocess.run([sys.executable, "scripts/preflight_v2_graph.py"], cwd=".", env=env, capture_output=True, text=True, timeout=20)
    assert res.returncode != 0
    assert "FAIL" in (res.stdout + res.stderr)
