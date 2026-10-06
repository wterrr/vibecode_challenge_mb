from __future__ import annotations

import json
from pathlib import Path

from app.domain.lesson import LessonPlan
from learnflow_v2.layout import compile_scene_layout, create_frame_profile_16_9, validate_layout_graph
from learnflow_v2.scenegraph import adapt_v1_lesson_plan
from learnflow_v2.qa import CriticPatchOp, CriticPatchSuggestion, CriticTargetKind, CriticTargetRef
from learnflow_v2.repair import apply_safe_scenegraph_patches
from learnflow_v2.scenegraph.enums import PreferredRegion


FIXTURES = Path("benchmarks/fixtures/v1")


def test_frozen_v1_corpus_compiles_through_production_layout_router():
    profile = create_frame_profile_16_9(640.0, 360.0)
    fixture_paths = sorted(FIXTURES.glob("*.json"))
    assert [path.stem for path in fixture_paths] == [
        "photosynthesis",
        "ram_vs_ssd",
        "tcp_three_way_handshake",
    ]

    scene_count = 0
    strategies = []
    for fixture_path in fixture_paths:
        plan = LessonPlan.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
        adapted = adapt_v1_lesson_plan(plan)
        assert len(adapted.scene_graphs) == 3
        for graph in adapted.scene_graphs:
            layout = compile_scene_layout(graph, profile=profile)
            report = validate_layout_graph(
                layout,
                profile=profile,
                expected_node_ids={node.id for node in graph.nodes},
                raise_on_error=False,
            )
            assert report.valid
            assert layout.feasible is True
            assert {box.node_id for box in layout.boxes} == {node.id for node in graph.nodes}
            strategies.append(layout.strategy.value)
            scene_count += 1

    assert scene_count == 9
    assert "DIRECTED_GRAPH" in strategies
    assert "COMPARISON" in strategies
    assert "CONCEPT_CARD" in strategies


def test_set_region_repair_changes_production_layout_geometry():
    profile = create_frame_profile_16_9(640.0, 360.0)
    fixture = FIXTURES / "photosynthesis.json"
    plan = LessonPlan.model_validate(json.loads(fixture.read_text(encoding="utf-8")))
    scene = adapt_v1_lesson_plan(plan).scene_graphs[0]
    target = sorted(scene.nodes, key=lambda node: node.id)[0]
    before = compile_scene_layout(scene, profile=profile)
    patch = CriticPatchSuggestion(
        patch_id="region-right",
        op=CriticPatchOp.SET_REGION,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id=target.id),),
        region=PreferredRegion.RIGHT,
    )
    repaired = apply_safe_scenegraph_patches(scene, (patch,))
    after = compile_scene_layout(repaired.scene_graph, profile=profile)
    before_box = next(box.rect for box in before.boxes if box.node_id == target.id)
    after_box = next(box.rect for box in after.boxes if box.node_id == target.id)
    assert repaired.original_scene_hash != repaired.repaired_scene_hash
    assert after_box != before_box
