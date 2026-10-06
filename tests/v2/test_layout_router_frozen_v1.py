from __future__ import annotations

import json
from pathlib import Path

from app.domain.lesson import LessonPlan
from learnflow_v2.layout import compile_scene_layout, create_frame_profile_16_9, validate_layout_graph
from learnflow_v2.scenegraph import adapt_v1_lesson_plan


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
