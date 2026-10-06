"""Compile frozen V1 storyboard scenes into typed V2 Core artifacts.

This adapter exists for Core-Gate benchmarking and side-by-side migration. It is
not an LLM planner and does not create raw renderer coordinates. Geometry is
owned by the V2 layout engines and motion by the V2 motion compiler.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.lesson import ScenePlan
from learnflow_v2.layout.constraints import LayoutItemInput
from learnflow_v2.layout.graph import layout_directed_graph
from learnflow_v2.layout.optimization import optimize_simple_layout
from learnflow_v2.layout.profiles import create_frame_profile_16_9
from learnflow_v2.layout.schema import FrameProfile, GraphBackendKind, LayoutGraph, LayoutStrategy
from learnflow_v2.motion import MotionEvent, MotionPlan, MotionStyle, MotionVerb, schedule_motion_plan
from learnflow_v2.motion.compiler import CompiledMotionArtifact, compile_motion_schedule
from learnflow_v2.scenegraph import LayoutIntentSpec, SceneGraph, SceneNode, SceneRelation
from learnflow_v2.scenegraph.enums import LayoutIntent, NodeKind, ReadingDirection, RelationKind, ScenePurpose


@dataclass(frozen=True)
class V2CompiledScene:
    source_scene_id: str
    narration: str
    scene_graph: SceneGraph
    layout_graph: LayoutGraph
    motion_plan: MotionPlan
    motion: CompiledMotionArtifact


def _strict_scene(scene: ScenePlan) -> ScenePlan:
    if not isinstance(scene, ScenePlan):
        raise TypeError("scene must be a V1 ScenePlan")
    return ScenePlan.model_validate(scene.model_dump(mode="json"))


def _concept_card(scene: ScenePlan, profile: FrameProfile) -> tuple[SceneGraph, LayoutGraph]:
    spec: Any = scene.visual_spec
    nodes = [SceneNode(id="title", kind=NodeKind.CONCEPT, label=spec.heading, semantic_role="TITLE")]
    for index, point in enumerate(spec.points):
        nodes.append(SceneNode(id=f"point{index + 1}", kind=NodeKind.TEXT, label=f"• {point}", semantic_role="SUPPORTING_POINT"))
    graph = SceneGraph(
        scene_id=scene.scene_id, purpose=ScenePurpose.INTRODUCE, concept=scene.concept,
        nodes=nodes, relations=[], groups=[], layout_intent=LayoutIntentSpec(type=LayoutIntent.CONCEPT_CARD),
    )
    items = [LayoutItemInput(node_id="title", role="title", min_width=220, min_height=42, preferred_width=520, preferred_height=48)]
    for node in nodes[1:]:
        items.append(LayoutItemInput(node_id=node.id, role="content", min_width=300, min_height=64, preferred_width=520, preferred_height=64))
    result = optimize_simple_layout(
        scene_id=scene.scene_id, strategy=LayoutStrategy.CONCEPT_CARD, profile=profile, items=items,
        metadata={"benchmark_adapter": "v1_storyboard_v1"},
    )
    if result.selected.layout_graph is None:
        raise RuntimeError(f"no feasible V2 concept-card layout for {scene.scene_id}")
    return graph, result.selected.layout_graph


def _comparison(scene: ScenePlan, profile: FrameProfile) -> tuple[SceneGraph, LayoutGraph]:
    spec: Any = scene.visual_spec
    nodes = [SceneNode(id="title", kind=NodeKind.CONCEPT, label=spec.title, semantic_role="TITLE")]
    for index, column in enumerate(spec.columns):
        content = "\n".join([column.title, column.subtitle or ""] + [f"• {point}" for point in column.points]).strip()
        nodes.append(SceneNode(id=f"col{index + 1}", kind=NodeKind.TEXT, label=content, semantic_role="COMPARISON_COLUMN"))
    if len(nodes) != 3:
        raise ValueError("Core benchmark comparison adapter requires exactly two comparison columns")
    graph = SceneGraph(
        scene_id=scene.scene_id, purpose=ScenePurpose.COMPARE, concept=scene.concept,
        nodes=nodes, relations=[], groups=[], layout_intent=LayoutIntentSpec(type=LayoutIntent.COMPARISON),
    )
    items = [
        LayoutItemInput(node_id="title", role="title", min_width=220, min_height=42, preferred_width=520, preferred_height=48),
        LayoutItemInput(node_id="col1", role="left", min_width=220, min_height=220, preferred_width=260, preferred_height=226),
        LayoutItemInput(node_id="col2", role="right", min_width=220, min_height=220, preferred_width=260, preferred_height=226),
    ]
    result = optimize_simple_layout(
        scene_id=scene.scene_id, strategy=LayoutStrategy.COMPARISON, profile=profile, items=items,
        metadata={"benchmark_adapter": "v1_storyboard_v1"},
    )
    if result.selected.layout_graph is None:
        raise RuntimeError(f"no feasible V2 comparison layout for {scene.scene_id}")
    return graph, result.selected.layout_graph


def _process(scene: ScenePlan, profile: FrameProfile) -> tuple[SceneGraph, LayoutGraph]:
    spec: Any = scene.visual_spec
    nodes = [SceneNode(id=actor.id, kind=NodeKind.CONCEPT, label=actor.label, semantic_role="PROCESS_ACTOR") for actor in spec.actors]
    relations = [
        SceneRelation(id=f"step{index + 1}", source=step.from_actor, target=step.to_actor, kind=RelationKind.FLOW, label=step.label)
        for index, step in enumerate(spec.steps)
    ]
    graph = SceneGraph(
        scene_id=scene.scene_id, purpose=ScenePurpose.DEMONSTRATE, concept=scene.concept,
        nodes=nodes, relations=relations, groups=[],
        layout_intent=LayoutIntentSpec(type=LayoutIntent.PROCESS, reading_direction=ReadingDirection.LEFT_TO_RIGHT),
    )
    measurements = {node.id: (145.0, 92.0) for node in nodes}
    layout = layout_directed_graph(graph, measurements, profile, backend=GraphBackendKind.GRAPHVIZ)
    return graph, layout


def _motion_for(graph: SceneGraph, *, scene_duration: float) -> tuple[MotionPlan, CompiledMotionArtifact]:
    events: list[MotionEvent] = []
    for index, node in enumerate(graph.nodes[:2]):
        events.append(MotionEvent(
            id=f"enter_{node.id}", target=node.id, verb=MotionVerb.ENTER,
            style=MotionStyle.FADE if index == 0 else MotionStyle.SLIDE,
        ))
    for relation in graph.relations:
        events.append(MotionEvent(
            id=f"draw_{relation.id}", target=relation.id, verb=MotionVerb.RELATION, style=MotionStyle.DRAW_EDGE,
        ))
    plan = MotionPlan(scene_id=graph.scene_id, events=tuple(events))
    schedule = schedule_motion_plan(plan, scene_duration=scene_duration, graph=graph)
    return plan, compile_motion_schedule(schedule)


def compile_v1_scene_to_v2(
    scene: ScenePlan,
    *,
    scene_duration: float = 4.0,
    profile: FrameProfile | None = None,
) -> V2CompiledScene:
    scene = _strict_scene(scene)
    if isinstance(scene_duration, bool) or not isinstance(scene_duration, (int, float)) or scene_duration <= 0:
        raise ValueError("scene_duration must be a positive real number")
    profile = profile or create_frame_profile_16_9(640.0, 360.0)
    intent = scene.visual_intent.value
    if intent == "concept_card":
        graph, layout = _concept_card(scene, profile)
    elif intent == "process_diagram":
        graph, layout = _process(scene, profile)
    elif intent == "comparison":
        graph, layout = _comparison(scene, profile)
    else:
        raise ValueError(f"V1 benchmark intent '{intent}' is not supported by the V2 Core benchmark adapter")
    motion_plan, motion = _motion_for(graph, scene_duration=float(scene_duration))
    return V2CompiledScene(
        source_scene_id=scene.scene_id, narration=scene.narration,
        scene_graph=graph, layout_graph=layout, motion_plan=motion_plan, motion=motion,
    )
