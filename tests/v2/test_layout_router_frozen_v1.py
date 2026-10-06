from __future__ import annotations

import json
from pathlib import Path

from app.domain.lesson import LessonPlan
from learnflow_v2.layout import compile_scene_layout, create_frame_profile_16_9, validate_layout_graph
from learnflow_v2.scenegraph import adapt_v1_lesson_plan
from learnflow_v2.qa import CriticPatchOp, CriticPatchSuggestion, CriticTargetKind, CriticTargetRef
from learnflow_v2.repair import apply_safe_scenegraph_patches
from learnflow_v2.render import DeterministicPillowRenderer
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


def test_frozen_v1_corpus_layouts_are_renderable_at_readable_text_contract():
    profile = create_frame_profile_16_9(640.0, 360.0)
    renderer = DeterministicPillowRenderer()
    rendered = 0
    for fixture_path in sorted(FIXTURES.glob("*.json")):
        plan = LessonPlan.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
        adapted = adapt_v1_lesson_plan(plan)
        for graph in adapted.scene_graphs:
            layout = compile_scene_layout(graph, profile=profile)
            frame = renderer.render_frame(graph, layout, None, 0.0)
            assert frame.size == (640, 360)
            rendered += 1
    assert rendered == 9


def test_frozen_comparison_region_repairs_change_geometry_and_pixels():
    profile = create_frame_profile_16_9(640.0, 360.0)
    renderer = DeterministicPillowRenderer()
    checked = 0
    for fixture_path in sorted(FIXTURES.glob("*.json")):
        plan = LessonPlan.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))
        comparison = adapt_v1_lesson_plan(plan).scene_graphs[2]
        target = sorted(comparison.nodes, key=lambda node: node.id)[0]
        current = target.layout_hint.preferred_region if target.layout_hint else None
        requested = PreferredRegion.RIGHT if current != PreferredRegion.RIGHT else PreferredRegion.LEFT
        before_layout = compile_scene_layout(comparison, profile=profile)
        before_frame = renderer.render_frame(comparison, before_layout, None, 0.0)

        patch = CriticPatchSuggestion(
            patch_id=f"comparison-region-{fixture_path.stem}",
            op=CriticPatchOp.SET_REGION,
            targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id=target.id),),
            region=requested,
        )
        repaired = apply_safe_scenegraph_patches(comparison, (patch,))
        after_layout = compile_scene_layout(repaired.scene_graph, profile=profile)
        after_frame = renderer.render_frame(repaired.scene_graph, after_layout, None, 0.0)

        before_box = next(box.rect for box in before_layout.boxes if box.node_id == target.id)
        after_box = next(box.rect for box in after_layout.boxes if box.node_id == target.id)
        assert before_box != after_box
        assert before_frame.tobytes() != after_frame.tobytes()
        checked += 1
    assert checked == 3
