"""Tests for V1 -> V2 adapter across all VisualIntent types and benchmark fixtures."""

import json
from pathlib import Path
import pytest

from app.domain.enums import VisualIntent
from app.domain.lesson import (
    ComparisonColumn,
    ComparisonSpec,
    ConceptCardSpec,
    IllustrationSpec,
    LessonPlan,
    ProcessActor,
    ProcessDiagramSpec,
    ProcessStep,
    ScenePlan,
)
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.scenegraph.adapter_v1 import adapt_v1_lesson_plan
from learnflow_v2.scenegraph.enums import LayoutIntent
from learnflow_v2.scenegraph.validation import validate_scenegraph_with_registry


def _make_dummy_scene(
    scene_id: str,
    title: str,
    concept: str,
    visual_intent: VisualIntent,
    visual_spec,
) -> ScenePlan:
    return ScenePlan(
        scene_id=scene_id,
        title=title,
        concept=concept,
        narration=f"Narration for {title}",
        key_points=["Key point for " + title],
        visual_intent=visual_intent,
        visual_spec=visual_spec,
    )


def _make_dummy_plan(topic: str, scenes: list[ScenePlan]) -> LessonPlan:
    final_scenes = list(scenes)
    idx = len(final_scenes) + 1
    while len(final_scenes) < 3:
        final_scenes.append(
            ScenePlan(
                scene_id=f"s{idx:02d}_filler",
                title=f"Filler Title {idx}",
                concept=f"Filler Concept {idx}",
                narration="Filler narration text.",
                key_points=["Filler key point"],
                visual_intent=VisualIntent.CONCEPT_CARD,
                visual_spec=ConceptCardSpec(heading=f"Filler {idx}", points=["Point"]),
            )
        )
        idx += 1

    return LessonPlan(
        title=f"Lesson: {topic}",
        topic=topic,
        audience="Beginner",
        language="vi",
        learning_objective="Learn core concepts",
        summary="A concise summary of the lesson.",
        target_duration_seconds=60,
        scenes=final_scenes,
    )


def test_adapt_concept_card():
    scene = _make_dummy_scene(
        scene_id="s01_concept_card",
        title="Understanding Loss",
        concept="Loss Function",
        visual_intent=VisualIntent.CONCEPT_CARD,
        visual_spec=ConceptCardSpec(
            heading="Loss Function",
            points=["Measures error", "Drives optimization", "Scalar value"],
            emphasis=["Scalar value"],
        ),
    )
    plan = _make_dummy_plan("Loss Functions", [scene])

    result = adapt_v1_lesson_plan(plan)
    registry = result.get_registry()
    assert len(result.scene_graphs) == len(plan.scenes)

    graph = result.scene_graphs[0]
    assert graph.layout_intent.type == LayoutIntent.CONCEPT_CARD
    assert len(graph.nodes) == 4  # 1 primary concept + 3 points
    assert len(graph.relations) == 3  # 3 ANNOTATES relations
    assert len(graph.groups) == 1

    # Validate against registry
    validate_scenegraph_with_registry(graph, registry)


def test_adapt_process_diagram():
    scene = _make_dummy_scene(
        scene_id="s01_process",
        title="Training Loop",
        concept="Training Process",
        visual_intent=VisualIntent.PROCESS_DIAGRAM,
        visual_spec=ProcessDiagramSpec(
            title="Training Loop",
            actors=[
                ProcessActor(id="model", label="Model"),
                ProcessActor(id="loss_calc", label="Loss Calculator"),
            ],
            steps=[
                ProcessStep(order=1, from_actor="model", to_actor="loss_calc", label="Send Prediction"),
                ProcessStep(order=2, from_actor="loss_calc", to_actor="model", label="Send Gradient"),
            ],
        ),
    )
    plan = _make_dummy_plan("Training Loop", [scene])

    result = adapt_v1_lesson_plan(plan)
    registry = result.get_registry()
    graph = result.scene_graphs[0]

    assert graph.layout_intent.type == LayoutIntent.PROCESS
    # 1 process topic concept + 2 actors + 2 steps = 5 nodes
    assert len(graph.nodes) == 5
    # 2 from-relations + 2 to-relations + 1 sequence relation = 5 relations
    assert len(graph.relations) == 5

    # Primary topic node must exist and reference concept
    topic_node = next(n for n in graph.nodes if n.semantic_role == "PROCESS_TOPIC")
    assert topic_node.label == "Training Loop"
    assert topic_node.concept_ref is not None
    assert topic_node.semantic_key is not None

    validate_scenegraph_with_registry(graph, registry)


def test_adapt_comparison():
    scene = _make_dummy_scene(
        scene_id="s01_comparison",
        title="RAM vs SSD",
        concept="Memory Hierarchy",
        visual_intent=VisualIntent.COMPARISON,
        visual_spec=ComparisonSpec(
            title="RAM vs SSD",
            columns=[
                ComparisonColumn(title="RAM", points=["Volatile", "Fast"]),
                ComparisonColumn(title="SSD", points=["Non-volatile", "Slower"]),
            ],
        ),
    )
    plan = _make_dummy_plan("Computer Architecture", [scene])

    result = adapt_v1_lesson_plan(plan)
    registry = result.get_registry()
    graph = result.scene_graphs[0]

    assert graph.layout_intent.type == LayoutIntent.COMPARISON
    # 1 heading + 2 columns + 4 points = 7 nodes
    assert len(graph.nodes) == 7
    # 4 PART_OF + 1 COMPARES_WITH = 5 relations
    assert len(graph.relations) == 5

    validate_scenegraph_with_registry(graph, registry)


def test_adapt_illustration():
    scene = _make_dummy_scene(
        scene_id="s01_illustration",
        title="Chloroplast Structure",
        concept="Photosynthesis",
        visual_intent=VisualIntent.ILLUSTRATION,
        visual_spec=IllustrationSpec(
            prompt="A botanical illustration of chloroplast thylakoids",
            fallback_heading="Chloroplast Features",
            fallback_points=["Thylakoid stacks", "Stroma fluid"],
        ),
    )
    plan = _make_dummy_plan("Plant Biology", [scene])

    result = adapt_v1_lesson_plan(plan)
    registry = result.get_registry()
    graph = result.scene_graphs[0]

    assert graph.layout_intent.type == LayoutIntent.ILLUSTRATION
    # 1 primary + 1 image + 1 fallback heading + 2 fallback points = 5 nodes
    assert len(graph.nodes) == 5

    validate_scenegraph_with_registry(graph, registry)


def test_same_concept_across_two_scenes_shares_concept_ref():
    scene_1 = _make_dummy_scene(
        scene_id="s01_intro",
        title="Intro to Loss",
        concept="Loss Function",
        visual_intent=VisualIntent.CONCEPT_CARD,
        visual_spec=ConceptCardSpec(
            heading="Loss Function",
            points=["Defines cost"],
        ),
    )
    scene_2 = _make_dummy_scene(
        scene_id="s02_minimize",
        title="Minimizing Loss",
        concept="  Loss   Function  ",  # Normalized alias
        visual_intent=VisualIntent.CONCEPT_CARD,
        visual_spec=ConceptCardSpec(
            heading="Minimizing Loss",
            points=["Optimization objective"],
        ),
    )
    scene_3 = _make_dummy_scene(
        scene_id="s03_summary",
        title="Summary of Loss",
        concept="Loss Function",
        visual_intent=VisualIntent.CONCEPT_CARD,
        visual_spec=ConceptCardSpec(
            heading="Summary of Loss",
            points=["Wrap-up"],
        ),
    )
    plan = _make_dummy_plan("Machine Learning", [scene_1, scene_2, scene_3])

    result = adapt_v1_lesson_plan(plan)
    registry = result.get_registry()

    # Across the entire lesson, there should be exactly ONE registered concept
    assert len(registry.all_concepts()) == 1
    canonical_concept = registry.all_concepts()[0]

    # Both scenes must share the same concept_ref
    node_s1 = result.scene_graphs[0].nodes[0]
    node_s2 = result.scene_graphs[1].nodes[0]
    node_s3 = result.scene_graphs[2].nodes[0]

    assert node_s1.id != node_s2.id  # Scene-local IDs differ
    assert node_s1.concept_ref == canonical_concept.concept_id
    assert node_s2.concept_ref == canonical_concept.concept_id
    assert node_s3.concept_ref == canonical_concept.concept_id
    assert node_s1.semantic_key == canonical_concept.canonical_key
    assert node_s2.semantic_key == canonical_concept.canonical_key
    assert node_s3.semantic_key == canonical_concept.canonical_key


def test_adapter_is_deterministic_and_does_not_mutate():
    scene_1 = _make_dummy_scene(
        scene_id="s01_backprop",
        title="Backprop",
        concept="Backpropagation",
        visual_intent=VisualIntent.CONCEPT_CARD,
        visual_spec=ConceptCardSpec(
            heading="Backpropagation",
            points=["Chain rule"],
        ),
    )
    scene_2 = _make_dummy_scene(
        scene_id="s02_chain",
        title="Chain Rule",
        concept="Calculus",
        visual_intent=VisualIntent.CONCEPT_CARD,
        visual_spec=ConceptCardSpec(
            heading="Chain Rule",
            points=["Derivative product"],
        ),
    )
    scene_3 = _make_dummy_scene(
        scene_id="s03_update",
        title="Weight Update",
        concept="Optimization",
        visual_intent=VisualIntent.CONCEPT_CARD,
        visual_spec=ConceptCardSpec(
            heading="Weight Update",
            points=["Step along gradient"],
        ),
    )
    plan = _make_dummy_plan("Deep Learning", [scene_1, scene_2, scene_3])
    original_dump = plan.model_dump()

    res1 = adapt_v1_lesson_plan(plan)
    res2 = adapt_v1_lesson_plan(plan)

    # Identical canonical serialization
    assert canonical_json(res1) == canonical_json(res2)

    # V1 plan was not mutated
    assert plan.model_dump() == original_dump


@pytest.mark.parametrize(
    "fixture_filename",
    [
        "tcp_three_way_handshake.json",
        "photosynthesis.json",
        "ram_vs_ssd.json",
    ],
)
def test_adapt_frozen_v1_benchmark_fixtures(fixture_filename: str):
    fixture_path = Path("benchmarks/fixtures/v1") / fixture_filename
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)
    plan = LessonPlan.model_validate(data)

    result = adapt_v1_lesson_plan(plan)
    registry = result.get_registry()

    assert len(registry.all_concepts()) > 0
    assert len(result.scene_graphs) == len(plan.scenes)

    # Every adapted scene graph passes registry-aware validation and has a registry-backed node
    for idx, (scene, graph) in enumerate(zip(plan.scenes, result.scene_graphs)):
        validate_scenegraph_with_registry(graph, registry)
        # Every scene must have at least one node referencing the registered concept
        concept_nodes = [n for n in graph.nodes if n.concept_ref is not None and n.semantic_key is not None]
        assert len(concept_nodes) >= 1, f"Scene {idx} ({scene.title}) has zero registry-backed nodes"

        # The scene concept must resolve in the registry
        resolved = registry.resolve(scene.concept)
        assert any(n.concept_ref == resolved.concept_id for n in concept_nodes)


def test_all_visual_intents_have_registry_backed_primary_node():
    # 1. ConceptCard
    s_card = _make_dummy_scene(
        "s01_card",
        "Card",
        "Concept A",
        VisualIntent.CONCEPT_CARD,
        ConceptCardSpec(heading="Card", points=["P1"]),
    )
    # 2. ProcessDiagram
    s_proc = _make_dummy_scene(
        "s02_proc",
        "Proc",
        "Concept B",
        VisualIntent.PROCESS_DIAGRAM,
        ProcessDiagramSpec(
            title="Proc",
            actors=[ProcessActor(id="a1", label="Actor 1")],
            steps=[ProcessStep(order=1, label="Step 1")],
        ),
    )
    # 3. Comparison
    s_comp = _make_dummy_scene(
        "s03_comp",
        "Comp",
        "Concept C",
        VisualIntent.COMPARISON,
        ComparisonSpec(
            title="Comp",
            columns=[
                ComparisonColumn(title="Col 1", points=["Pt 1"]),
                ComparisonColumn(title="Col 2", points=["Pt 2"]),
            ],
        ),
    )
    # 4. Illustration
    s_ill = _make_dummy_scene(
        "s04_ill",
        "Ill",
        "Concept D",
        VisualIntent.ILLUSTRATION,
        IllustrationSpec(
            prompt="Draw chloroplast",
            fallback_heading="Fallback H",
            fallback_points=["Fallback P"],
        ),
    )

    plan = LessonPlan(
        title="Test Lesson",
        topic="Test",
        audience="All",
        language="vi",
        learning_objective="Obj",
        summary="Summary",
        target_duration_seconds=60,
        scenes=[s_card, s_proc, s_comp, s_ill],
    )
    result = adapt_v1_lesson_plan(plan)
    registry = result.get_registry()

    for idx, graph in enumerate(result.scene_graphs):
        validate_scenegraph_with_registry(graph, registry)
        primary_nodes = [n for n in graph.nodes if n.concept_ref is not None and n.semantic_key is not None]
        assert len(primary_nodes) >= 1, f"Intent {plan.scenes[idx].visual_intent} missing registry-backed primary node"

