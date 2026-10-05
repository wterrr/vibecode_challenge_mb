"""Tests for continuity fixture corpus (benchmarks/fixtures/v2/continuity_cases.json)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from learnflow_v2.layout.constraints import LayoutItemInput, solve_layout
from learnflow_v2.layout.continuity import (
    build_continuity_context,
    compute_continuity_metrics,
)
from learnflow_v2.layout.graph import (
    GraphLayoutKind,
    LayoutDirection,
    layout_directed_graph,
)
from learnflow_v2.layout.optimization import optimize_simple_layout
from learnflow_v2.layout.profiles import get_frame_profile
from learnflow_v2.layout.schema import GraphBackendKind, LayoutBox, LayoutGraph, Rect
from learnflow_v2.scenegraph.enums import LayoutIntent, NodeKind, RelationKind
from learnflow_v2.scenegraph.schema import (
    LayoutIntentSpec,
    SceneGraph,
    SceneNode,
    SceneRelation,
)

CORPUS_PATH = Path("benchmarks/fixtures/v2/continuity_cases.json")


def _make_layout_item(it: dict) -> LayoutItemInput:
    d = dict(it)
    d.pop("label", None)
    return LayoutItemInput(**d)


def _make_scene_graph(
    scene_id: str,
    items: list[dict],
    relations: list[dict] | None = None,
    intent_type: LayoutIntent = LayoutIntent.CONCEPT_CARD,
) -> SceneGraph:
    nodes = [
        SceneNode(
            id=it["node_id"],
            kind=NodeKind.CONCEPT if it.get("role") == "content" else NodeKind.TEXT,
            label=it.get("label", it["node_id"]),
            semantic_key=it.get("semantic_key"),
            concept_ref=it.get("semantic_key"),
        )
        for it in items
    ]
    scene_rels = []
    if relations:
        for r in relations:
            scene_rels.append(
                SceneRelation(
                    id=r["id"],
                    source=r["source"],
                    target=r["target"],
                    kind=RelationKind.SEQUENCE_BEFORE,
                )
            )
    return SceneGraph(
        scene_id=scene_id,
        nodes=nodes,
        relations=scene_rels,
        layout_intent=LayoutIntentSpec(type=intent_type),
    )


def test_continuity_corpus_exists_and_valid():
    assert CORPUS_PATH.exists(), f"Missing {CORPUS_PATH}"
    cases = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    assert isinstance(cases, list)
    assert 28 <= len(cases) <= 40, f"Expected 28 to 40 cases, got {len(cases)}"


@pytest.mark.parametrize("case", json.loads(CORPUS_PATH.read_text(encoding="utf-8")), ids=lambda c: c["case_id"])
def test_continuity_fixture_case(case: dict):
    strategy = case["strategy"]
    prev_prof_id = case.get("previous_profile", case.get("profile", "16:9"))
    curr_prof_id = case.get("current_profile", case.get("profile", "16:9"))

    prev_prof = get_frame_profile(prev_prof_id)
    curr_prof = get_frame_profile(curr_prof_id)

    if strategy == "DIRECTED_GRAPH":
        # Directed graph fixture execution
        graph_kind_str = case.get("graph_kind", "PROCESS")
        intent_type = LayoutIntent.PROCESS if graph_kind_str == "PROCESS" else LayoutIntent.HIERARCHY

        prev_sg = _make_scene_graph(
            "prev_scene",
            case["previous_items"],
            case.get("previous_relations"),
            intent_type=intent_type,
        )
        curr_sg = _make_scene_graph(
            "curr_scene",
            case["current_items"],
            case.get("current_relations"),
            intent_type=intent_type,
        )

        prev_measurements = {
            it["node_id"]: {"width": it.get("min_width", 120.0), "height": it.get("min_height", 60.0)}
            for it in case["previous_items"]
        }
        curr_measurements = {
            it["node_id"]: {"width": it.get("min_width", 120.0), "height": it.get("min_height", 60.0)}
            for it in case["current_items"]
        }

        # Use Graphviz backend for deterministic graph execution without local elkjs requirement
        prev_layout = layout_directed_graph(
            scene_graph=prev_sg,
            measurements=prev_measurements,
            profile=prev_prof,
            backend=GraphBackendKind.GRAPHVIZ,
            direction=LayoutDirection.RIGHT,
            kind=GraphLayoutKind(graph_kind_str),
        )

        context = build_continuity_context(
            previous_scene_graph=prev_sg,
            previous_layout=prev_layout,
            current_scene_graph=curr_sg,
            previous_profile=prev_prof,
            current_profile=curr_prof,
        )

        expected = case["expected_metrics"]
        assert len(context.anchors) == expected["matched_count"]
        assert len(context.new_keys) == expected["new_count"]
        assert len(context.removed_keys) == expected["removed_count"]
        assert len(context.ambiguous_keys) == expected["ambiguous_count"]

        curr_layout = layout_directed_graph(
            scene_graph=curr_sg,
            measurements=curr_measurements,
            profile=curr_prof,
            backend=GraphBackendKind.GRAPHVIZ,
            direction=LayoutDirection.RIGHT,
            kind=GraphLayoutKind(graph_kind_str),
            previous_scene_graph=prev_sg,
            previous_layout=prev_layout,
        )

        assert curr_layout.feasible
        metrics = compute_continuity_metrics(
            continuity_context=context,
            current_layout=curr_layout,
            profile=curr_prof,
        )

        assert metrics.matched_count == expected["matched_count"]
        assert metrics.new_count == expected["new_count"]
        assert metrics.removed_count == expected["removed_count"]

    else:
        # Simple layout fixture execution
        prev_items = [_make_layout_item(it) for it in case["previous_items"]]
        curr_items = [_make_layout_item(it) for it in case["current_items"]]

        prev_sg = _make_scene_graph("prev_scene", case["previous_items"])
        curr_sg = _make_scene_graph("curr_scene", case["current_items"])

        # Solve previous scene
        prev_layout = solve_layout(
            scene_id="prev_scene",
            strategy=strategy,
            profile=prev_prof,
            items=prev_items,
        )

        # Apply intentional box corruption if specified in test case
        if "corrupt_previous_box" in case:
            corrupt = case["corrupt_previous_box"]
            if corrupt["type"] == "missing":
                prev_layout = LayoutGraph(
                    schema_version=prev_layout.schema_version,
                    scene_id=prev_layout.scene_id,
                    frame_profile_id=prev_layout.frame_profile_id,
                    frame_width=prev_layout.frame_width,
                    frame_height=prev_layout.frame_height,
                    boxes=[b for b in prev_layout.boxes if b.node_id != corrupt["node_id"]],
                    strategy=prev_layout.strategy,
                    feasible=prev_layout.feasible,
                )
            elif corrupt["type"] == "out_of_zone":
                corrupt_boxes = []
                for b in prev_layout.boxes:
                    if b.node_id == corrupt["node_id"]:
                        corrupt_boxes.append(
                            LayoutBox(
                                node_id=b.node_id,
                                zone=b.zone,
                                rect=Rect(x=prev_prof.width + 100.0, y=200.0, width=50.0, height=50.0),
                                strategy_role=b.strategy_role,
                                semantic_key=b.semantic_key,
                            )
                        )
                    else:
                        corrupt_boxes.append(b)
                prev_layout = LayoutGraph(
                    schema_version=prev_layout.schema_version,
                    scene_id=prev_layout.scene_id,
                    frame_profile_id=prev_layout.frame_profile_id,
                    frame_width=prev_layout.frame_width,
                    frame_height=prev_layout.frame_height,
                    boxes=corrupt_boxes,
                    strategy=prev_layout.strategy,
                    feasible=prev_layout.feasible,
                )

        # Build continuity context with actual current layout items
        context = build_continuity_context(
            previous_scene_graph=prev_sg,
            previous_layout=prev_layout,
            current_scene_graph=curr_sg,
            previous_profile=prev_prof,
            current_profile=curr_prof,
            current_layout_items=curr_items,
        )

        expected = case["expected_metrics"]
        assert len(context.anchors) == expected["matched_count"]
        assert len(context.new_keys) == expected["new_count"]
        assert len(context.removed_keys) == expected["removed_count"]
        assert len(context.ambiguous_keys) == expected["ambiguous_count"]

        # Solve current scene with continuity
        opt_res = optimize_simple_layout(
            scene_id="curr_scene",
            strategy=strategy,
            profile=curr_prof,
            items=curr_items,
            continuity=context,
        )

        assert opt_res.selected.feasibility.feasible
        assert opt_res.selected.layout_graph is not None

        metrics = compute_continuity_metrics(
            continuity_context=context,
            current_layout=opt_res.selected.layout_graph,
            profile=curr_prof,
        )

        assert metrics.matched_count == expected["matched_count"]
        assert metrics.new_count == expected["new_count"]
        assert metrics.removed_count == expected["removed_count"]
        if expected["matched_count"] > 0:
            assert metrics.mean_displacement >= 0.0
        else:
            assert metrics.mean_displacement == 0.0
