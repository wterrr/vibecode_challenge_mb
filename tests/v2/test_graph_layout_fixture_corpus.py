"""Executable V2-04 graph layout fixture corpus tests.

The JSON corpus is authoritative test input, not dead metadata.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from learnflow_v2.core.errors import LearnFlowV2Error
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.layout.graph import (
    BackendLayoutResult,
    BackendNode,
    BackendRoute,
    GraphLayoutInput,
    GraphLayoutKind,
    GraphNodeInput,
    LayoutDirection,
    build_graph_layout_input,
    layout_directed_graph,
    translate_center_into_content,
)
from learnflow_v2.layout.graph_metrics import edge_is_orthogonal, validate_routed_edge_endpoints
from learnflow_v2.layout.preflight import validate_graph_layout, validate_layout_graph
from learnflow_v2.layout.profiles import create_frame_profile_16_9, create_frame_profile_9_16
from learnflow_v2.layout.schema import GraphBackendKind, LayoutStrategy, Point, RoutingStyle
from learnflow_v2.scenegraph.enums import LayoutIntent, NodeKind, PortHint, ReadingDirection, RelationKind
from learnflow_v2.scenegraph.schema import LayoutIntentSpec, SceneGraph, SceneNode, SceneRelation


FIXTURE_DIR = Path("benchmarks/fixtures/v2")
VALID_PATH = FIXTURE_DIR / "graph_layout_cases.json"
INVALID_PATH = FIXTURE_DIR / "graph_layout_invalid_cases.json"


def _require_real_elk():
    from learnflow_v2.layout.backends.elk import ELKJS_REQUIRED_MESSAGE, is_available
    assert is_available(), ELKJS_REQUIRED_MESSAGE


def _load_valid():
    data = json.loads(VALID_PATH.read_text())
    assert data["count"] == 36
    assert len(data["cases"]) == 36
    return data["cases"]


def _load_invalid():
    data = json.loads(INVALID_PATH.read_text())
    assert data["count"] == 8
    assert len(data["cases"]) == 8
    return data["cases"]


def _profile(aspect: str):
    if aspect == "16:9":
        return create_frame_profile_16_9()
    if aspect == "9:16":
        return create_frame_profile_9_16()
    raise AssertionError(f"unsupported aspect in fixture: {aspect}")


def _scene_from_case(case: dict) -> SceneGraph:
    nodes = [SceneNode(id=n, kind=NodeKind.CONCEPT, label=n) for n in sorted(case["nodes"])]
    relations = [
        SceneRelation(
            id=e["id"],
            source=e["source"],
            target=e["target"],
            kind=RelationKind(e["kind"]),
            source_port=PortHint(e.get("source_port", "AUTO")),
            target_port=PortHint(e.get("target_port", "AUTO")),
        )
        for e in sorted(case["edges"], key=lambda x: x["id"])
    ]
    intent = LayoutIntent.HIERARCHY if case["kind"] == GraphLayoutKind.HIERARCHY.value else LayoutIntent.PROCESS
    return SceneGraph(
        scene_id=case["id"],
        nodes=nodes,
        relations=relations,
        layout_intent=LayoutIntentSpec(type=intent),
    )


def _measurements(scene_graph: SceneGraph) -> dict[str, tuple[float, float]]:
    return {n.id: (120.0, 60.0) for n in scene_graph.nodes}


def _assert_valid_layout(case: dict, lg):
    profile = _profile(case["aspect"])
    expected_nodes = set(case["nodes"])
    expected_edges = {e["id"] for e in case["edges"]}
    assert lg.strategy == LayoutStrategy.DIRECTED_GRAPH
    assert lg.metadata["graph_kind"] == case["kind"]
    assert {b.node_id for b in lg.boxes} == expected_nodes
    assert {e.edge_id for e in lg.routed_edges} == expected_edges
    for box in lg.boxes:
        assert box.rect.width == 120.0
        assert box.rect.height == 60.0
        assert profile.get_zone("CONTENT").contains_rect(box.rect)
        assert profile.safe_edge_rect.contains_rect(box.rect)
    boxes = {b.node_id: b.rect for b in lg.boxes}
    for edge in lg.routed_edges:
        assert edge.routing_style == RoutingStyle.ORTHOGONAL
        assert edge_is_orthogonal(edge)
        assert validate_routed_edge_endpoints(edge, boxes)
        for point in edge.points:
            assert profile.get_zone("CONTENT").contains_point(point.x, point.y)
            assert profile.safe_edge_rect.contains_point(point.x, point.y)
    validate_layout_graph(lg, profile=profile, measurements=_measurements(_scene_from_case(case)), expected_node_ids=expected_nodes)
    report = validate_graph_layout(lg, profile=profile)
    assert report.valid
    assert report.edge_node_intersection_count == 0


def test_valid_graph_fixture_corpus_count_contract():
    _load_valid()


@pytest.mark.parametrize("case", _load_valid(), ids=lambda c: c["id"])
def test_valid_graph_fixture_corpus_executes_real_elk(case):
    _require_real_elk()
    sg = _scene_from_case(case)
    profile = _profile(case["aspect"])
    lg = layout_directed_graph(
        sg,
        _measurements(sg),
        profile,
        GraphBackendKind.ELK,
        kind=GraphLayoutKind(case["kind"]),
    )
    _assert_valid_layout(case, lg)


def test_valid_graph_fixture_representative_subset_deterministic():
    _require_real_elk()
    cases = _load_valid()
    required_fragments = ["chain", "diamond", "cycle", "tree"]
    subset = []
    for fragment in required_fragments:
        subset.append(next(c for c in cases if fragment in c["id"]))
    subset.append(next(c for c in cases if c["edges"][0].get("source_port") == "RIGHT"))
    subset.append(next(c for c in cases if c["aspect"] == "9:16"))
    seen = set()
    unique_subset = []
    for case in subset:
        if case["id"] not in seen:
            seen.add(case["id"])
            unique_subset.append(case)
    for case in unique_subset:
        sg = _scene_from_case(case)
        profile = _profile(case["aspect"])
        lg1 = layout_directed_graph(sg, _measurements(sg), profile, GraphBackendKind.ELK, kind=GraphLayoutKind(case["kind"]))
        lg2 = layout_directed_graph(sg, _measurements(sg), profile, GraphBackendKind.ELK, kind=GraphLayoutKind(case["kind"]))
        assert canonical_json(lg1) == canonical_json(lg2)


def _invalid_code(func) -> str:
    try:
        func()
    except LearnFlowV2Error as exc:
        return exc.code
    except ValidationError:
        return "VALIDATION_ERROR"
    raise AssertionError("expected invalid fixture to fail")


def _run_invalid_case(case_id: str) -> str:
    profile = create_frame_profile_16_9()
    if case_id == "missing_measurement":
        sg = SceneGraph(
            scene_id=case_id,
            nodes=[SceneNode(id="a", kind=NodeKind.CONCEPT), SceneNode(id="b", kind=NodeKind.CONCEPT)],
            relations=[SceneRelation(id="e0", source="a", target="b", kind=RelationKind.FLOW)],
        )
        return _invalid_code(lambda: build_graph_layout_input(sg, {"a": (120, 60)}, profile))
    if case_id == "unknown_relation_endpoint":
        # Use model_construct to bypass SceneGraph validation and exercise graph compiler validation.
        sg = SceneGraph.model_construct(
            scene_id=case_id,
            nodes=[SceneNode(id="a", kind=NodeKind.CONCEPT)],
            relations=[SceneRelation(id="e0", source="a", target="missing", kind=RelationKind.FLOW)],
            layout_intent=LayoutIntentSpec(type=LayoutIntent.PROCESS),
        )
        return _invalid_code(lambda: build_graph_layout_input(sg, {"a": (120, 60)}, profile))
    if case_id == "unsupported_relation_kind":
        sg = SceneGraph(
            scene_id=case_id,
            nodes=[SceneNode(id="a", kind=NodeKind.CONCEPT), SceneNode(id="b", kind=NodeKind.CONCEPT)],
            relations=[SceneRelation(id="e0", source="a", target="b", kind=RelationKind.COMPARES_WITH)],
        )
        return _invalid_code(lambda: build_graph_layout_input(sg, {"a": (120, 60), "b": (120, 60)}, profile))
    if case_id == "unsupported_direction":
        sg = SceneGraph(scene_id=case_id, nodes=[SceneNode(id="a", kind=NodeKind.CONCEPT), SceneNode(id="b", kind=NodeKind.CONCEPT)], relations=[SceneRelation(id="e0", source="a", target="b", kind=RelationKind.FLOW)])
        return _invalid_code(lambda: build_graph_layout_input(sg, {"a": (120, 60), "b": (120, 60)}, profile, direction=ReadingDirection.RADIAL))
    if case_id == "bad_port_hint":
        return _invalid_code(lambda: SceneRelation(id="e0", source="a", target="b", kind=RelationKind.FLOW, source_port="DIAGONAL"))
    if case_id == "backend_unavailable":
        from learnflow_v2.layout.backends import elk
        old = elk.shutil.which
        try:
            elk.shutil.which = lambda _: None
            sg = SceneGraph(scene_id=case_id, nodes=[SceneNode(id="a", kind=NodeKind.CONCEPT), SceneNode(id="b", kind=NodeKind.CONCEPT)], relations=[SceneRelation(id="e0", source="a", target="b", kind=RelationKind.FLOW)])
            return _invalid_code(lambda: layout_directed_graph(sg, {"a": (120, 60), "b": (120, 60)}, profile, GraphBackendKind.ELK))
        finally:
            elk.shutil.which = old
    if case_id == "oversized_graph":
        graph_input = GraphLayoutInput(case_id, [GraphNodeInput("a", 1000, 400), GraphNodeInput("b", 1000, 400)], [], LayoutDirection.RIGHT, GraphLayoutKind.PROCESS)
        result = BackendLayoutResult(
            nodes=[BackendNode("a", 0, 0, 1000, 400), BackendNode("b", 1200, 0, 1000, 400)],
            routes=[],
            backend=GraphBackendKind.ELK,
            diagnostics={},
        )
        return _invalid_code(lambda: translate_center_into_content(result, graph_input, profile))
    if case_id == "malformed_backend_output":
        from learnflow_v2.layout.backends.elk import ElkBackend
        graph_input = GraphLayoutInput(case_id, [GraphNodeInput("a", 100, 50)], [], LayoutDirection.RIGHT, GraphLayoutKind.PROCESS)
        return _invalid_code(lambda: ElkBackend()._parse({"children": [{"id": "unknown", "x": 0, "y": 0, "width": 1, "height": 1}], "edges": []}, graph_input))
    raise AssertionError(f"unhandled invalid case: {case_id}")


@pytest.mark.parametrize("case", _load_invalid(), ids=lambda c: c["id"])
def test_invalid_graph_fixture_corpus_executes_stable_errors(case):
    assert _run_invalid_case(case["id"]) == case["error"]
