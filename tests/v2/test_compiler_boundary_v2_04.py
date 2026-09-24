"""V2-04 compiler boundary tests.

These tests pin the architectural separation between the simple template compiler
(`solve_layout`) and the directed graph compiler (`layout_directed_graph`).
"""

import shutil

import pytest

from learnflow_v2.core.errors import LayoutInvalidInputError, LayoutPreflightFailedError
from learnflow_v2.layout.constraints import LayoutItemInput, solve_layout
from learnflow_v2.layout.graph import layout_directed_graph
from learnflow_v2.layout.preflight import validate_graph_layout
from learnflow_v2.layout.profiles import create_frame_profile_16_9
from learnflow_v2.layout.schema import (
    GraphBackendKind,
    LayoutBox,
    LayoutGraph,
    LayoutStrategy,
    Rect,
    SIMPLE_LAYOUT_STRATEGIES,
)
from learnflow_v2.scenegraph.enums import LayoutIntent, NodeKind
from learnflow_v2.scenegraph.schema import LayoutIntentSpec, SceneGraph, SceneNode


def _minimal_items(strategy: LayoutStrategy) -> list[LayoutItemInput]:
    if strategy == LayoutStrategy.CONCEPT_CARD:
        return [LayoutItemInput(node_id="content", role="content", min_width=40, min_height=30)]
    if strategy == LayoutStrategy.COMPARISON:
        return [
            LayoutItemInput(node_id="left", role="left", min_width=40, min_height=30),
            LayoutItemInput(node_id="right", role="right", min_width=40, min_height=30),
        ]
    if strategy == LayoutStrategy.IMAGE_TEXT:
        return [
            LayoutItemInput(node_id="image", role="image", min_width=40, min_height=30, aspect_ratio=1.5),
            LayoutItemInput(node_id="text", role="text", min_width=40, min_height=30),
        ]
    if strategy == LayoutStrategy.QUOTE:
        return [LayoutItemInput(node_id="quote", role="quote", min_width=40, min_height=30)]
    raise AssertionError(f"Unhandled simple strategy: {strategy}")


@pytest.mark.parametrize("strategy", sorted(SIMPLE_LAYOUT_STRATEGIES, key=lambda s: s.value))
def test_solve_layout_accepts_only_authoritative_simple_strategy_set(strategy):
    lg = solve_layout("simple_boundary", strategy, "16:9", _minimal_items(strategy))
    assert lg.strategy == strategy
    assert lg.boxes
    assert not lg.routed_edges


def test_solve_layout_rejects_directed_graph_with_actionable_boundary_error():
    with pytest.raises(LayoutInvalidInputError) as exc:
        solve_layout(
            "scene",
            LayoutStrategy.DIRECTED_GRAPH,
            "16:9",
            [LayoutItemInput(node_id="a")],
        )

    assert exc.value.code == "LAYOUT_INVALID_INPUT"
    assert "DIRECTED_GRAPH must be compiled through layout_directed_graph()" in exc.value.message


def test_layout_directed_graph_produces_directed_graph_with_real_graphviz():
    assert shutil.which("dot"), "Graphviz dot executable must be available for this integration test"

    profile = create_frame_profile_16_9()
    sg = SceneGraph(
        scene_id="graph_boundary",
        nodes=[SceneNode(id="a", kind=NodeKind.CONCEPT, label="A")],
        relations=[],
        layout_intent=LayoutIntentSpec(type=LayoutIntent.PROCESS),
    )

    lg = layout_directed_graph(
        sg,
        {"a": (120, 60)},
        profile,
        GraphBackendKind.GRAPHVIZ,
        strict_orthogonal=False,
    )

    assert lg.strategy == LayoutStrategy.DIRECTED_GRAPH
    assert [box.node_id for box in lg.boxes] == ["a"]
    assert lg.routed_edges == []
    report = validate_graph_layout(lg, profile=profile)
    assert report.valid


def test_validate_graph_layout_rejects_non_directed_graph_strategy():
    profile = create_frame_profile_16_9()
    lg = LayoutGraph(
        scene_id="not_graph",
        frame_profile_id=profile.id,
        frame_width=profile.width,
        frame_height=profile.height,
        boxes=[
            LayoutBox(
                node_id="a",
                rect=Rect(x=profile.get_zone("CONTENT").x, y=profile.get_zone("CONTENT").y, width=120, height=60),
                zone="CONTENT",
                strategy_role="content",
            )
        ],
        routed_edges=[],
        strategy=LayoutStrategy.CONCEPT_CARD,
    )

    with pytest.raises(LayoutPreflightFailedError) as exc:
        validate_graph_layout(lg, profile=profile)

    assert exc.value.code == "LAYOUT_PREFLIGHT_FAILED"
    assert exc.value.details["expected_strategy"] == "DIRECTED_GRAPH"
