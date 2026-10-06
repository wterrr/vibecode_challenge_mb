from pathlib import Path
from app.domain.lesson import LessonPlan
from learnflow_v2.integration import compile_v1_scene_to_v2


def _plans():
    for path in sorted(Path("benchmarks/fixtures/v1").glob("*.json")):
        yield LessonPlan.model_validate_json(path.read_text(encoding="utf-8"))


def test_all_frozen_v1_benchmark_scenes_compile_to_v2():
    count = 0
    for plan in _plans():
        for scene in plan.scenes:
            built = compile_v1_scene_to_v2(scene)
            assert built.scene_graph.scene_id == scene.scene_id
            assert built.layout_graph.scene_id == scene.scene_id
            assert built.layout_graph.feasible is True
            assert built.motion.scene_id == scene.scene_id
            assert {b.node_id for b in built.layout_graph.boxes} == {n.id for n in built.scene_graph.nodes}
            count += 1
    assert count == 9
