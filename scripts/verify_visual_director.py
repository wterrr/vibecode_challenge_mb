#!/usr/bin/env python3
"""Acceptance verifier for the LearnFlow Visual Director."""

from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import Storyboard, StoryboardScene, TeachingFunction
from learnflow_v2.scenegraph import (
    LayoutHint,
    LayoutIntent,
    LayoutIntentSpec,
    NodeKind,
    PreferredRegion,
    ReadingDirection,
    RelationKind,
    SceneGraph,
    SceneNode,
    ScenePurpose,
    SceneRelation,
)
from scripts.verify_script_agent import build_fixture, build_script
from visual_director import (
    VisualDirectorOutput,
    build_visual_concept_registry,
    build_visual_director_task,
    require_core_ready,
    validate_visual_director_output,
)


def _node(entry, node_id: str, *, region: PreferredRegion | None = None):
    return SceneNode(
        id=node_id,
        kind=NodeKind.CONCEPT,
        label=entry.label,
        concept_ref=entry.concept_id,
        semantic_key=entry.canonical_key,
        layout_hint=LayoutHint(
            preferred_region=region,
            importance=0.8,
        ),
        style_refs=["concept.primary"],
    )


def build_visual_output(script, registry) -> VisualDirectorOutput:
    loss = registry.resolve("loss")
    gradient = registry.resolve("gradient")
    learning_rate = registry.resolve("learning rate")

    scenes = (
        StoryboardScene(
            scene_id="scene.intro",
            script_segment_ids=("S01",),
            teaching_function=TeachingFunction.INTRODUCE,
            visual_intent="Open with a restrained semantic title card that establishes the topic.",
        ),
        StoryboardScene(
            scene_id="scene.explain",
            script_segment_ids=("S02",),
            teaching_function=TeachingFunction.EXPLAIN,
            visual_intent="Show the relationship between gradient and loss as a simple conceptual process.",
            concept_refs=(loss.concept_id, gradient.concept_id),
            continuity_keys=(loss.canonical_key, gradient.canonical_key),
        ),
        StoryboardScene(
            scene_id="scene.demo",
            script_segment_ids=("S03",),
            teaching_function=TeachingFunction.DEMONSTRATE,
            visual_intent="Use a semantic downhill-step illustration with the same canonical concepts.",
            concept_refs=(loss.concept_id, gradient.concept_id, learning_rate.concept_id),
            continuity_keys=(
                loss.canonical_key,
                gradient.canonical_key,
                learning_rate.canonical_key,
            ),
        ),
        StoryboardScene(
            scene_id="scene.check",
            script_segment_ids=("S04",),
            teaching_function=TeachingFunction.CHECK,
            visual_intent="Present a concise learner check centered on qualitative step size.",
            concept_refs=(learning_rate.concept_id,),
            continuity_keys=(learning_rate.canonical_key,),
        ),
        StoryboardScene(
            scene_id="scene.summary",
            script_segment_ids=("S05",),
            teaching_function=TeachingFunction.SUMMARIZE,
            visual_intent="Reconnect the canonical concepts in a compact semantic summary.",
            concept_refs=(loss.concept_id, gradient.concept_id, learning_rate.concept_id),
            continuity_keys=(
                loss.canonical_key,
                gradient.canonical_key,
                learning_rate.canonical_key,
            ),
        ),
    )

    graphs = (
        SceneGraph(
            scene_id="scene.intro",
            purpose=ScenePurpose.INTRODUCE,
            concept="gradient descent",
            nodes=[
                SceneNode(
                    id="title",
                    kind=NodeKind.TEXT,
                    label="Gradient Descent",
                    layout_hint=LayoutHint(
                        preferred_region=PreferredRegion.CENTER,
                        importance=1.0,
                    ),
                    style_refs=["title.primary"],
                )
            ],
            layout_intent=LayoutIntentSpec(type=LayoutIntent.CONCEPT_CARD),
        ),
        SceneGraph(
            scene_id="scene.explain",
            purpose=ScenePurpose.EXPLAIN,
            concept="gradient and loss",
            nodes=[
                _node(gradient, "gradient", region=PreferredRegion.LEFT),
                _node(loss, "loss", region=PreferredRegion.RIGHT),
            ],
            relations=[
                SceneRelation(
                    id="rel.update",
                    source="gradient",
                    target="loss",
                    kind=RelationKind.FLOW,
                    label="guides an update intended to reduce",
                )
            ],
            layout_intent=LayoutIntentSpec(
                type=LayoutIntent.PROCESS,
                reading_direction=ReadingDirection.LEFT_TO_RIGHT,
            ),
        ),
        SceneGraph(
            scene_id="scene.demo",
            purpose=ScenePurpose.DEMONSTRATE,
            concept="downhill step",
            nodes=[
                _node(loss, "loss", region=PreferredRegion.RIGHT),
                _node(gradient, "gradient", region=PreferredRegion.LEFT),
                _node(learning_rate, "learning_rate", region=PreferredRegion.BOTTOM),
                SceneNode(
                    id="step",
                    kind=NodeKind.SHAPE,
                    label="careful downhill step",
                    semantic_role="WORKED_EXAMPLE_STEP",
                    layout_hint=LayoutHint(
                        keep_near=["gradient", "learning_rate"],
                        preferred_order=2,
                    ),
                    style_refs=["example.step"],
                ),
            ],
            relations=[
                SceneRelation(
                    id="rel.gradient_step",
                    source="gradient",
                    target="step",
                    kind=RelationKind.DEPENDS_ON,
                ),
                SceneRelation(
                    id="rel.rate_step",
                    source="learning_rate",
                    target="step",
                    kind=RelationKind.ANNOTATES,
                ),
                SceneRelation(
                    id="rel.step_loss",
                    source="step",
                    target="loss",
                    kind=RelationKind.FLOW,
                ),
            ],
            layout_intent=LayoutIntentSpec(type=LayoutIntent.ILLUSTRATION),
        ),
        SceneGraph(
            scene_id="scene.check",
            purpose=ScenePurpose.RECAP,
            concept="step size check",
            nodes=[
                _node(learning_rate, "learning_rate", region=PreferredRegion.CENTER),
                SceneNode(
                    id="question",
                    kind=NodeKind.CALLOUT,
                    label="What can an oversized step cause?",
                    layout_hint=LayoutHint(
                        keep_near=["learning_rate"],
                        importance=0.9,
                    ),
                    style_refs=["learner.check"],
                ),
            ],
            relations=[
                SceneRelation(
                    id="rel.question",
                    source="question",
                    target="learning_rate",
                    kind=RelationKind.ANNOTATES,
                )
            ],
            layout_intent=LayoutIntentSpec(type=LayoutIntent.CONCEPT_CARD),
        ),
        SceneGraph(
            scene_id="scene.summary",
            purpose=ScenePurpose.SUMMARIZE,
            concept="gradient descent summary",
            nodes=[
                _node(gradient, "gradient", region=PreferredRegion.LEFT),
                _node(learning_rate, "learning_rate", region=PreferredRegion.CENTER),
                _node(loss, "loss", region=PreferredRegion.RIGHT),
            ],
            relations=[
                SceneRelation(
                    id="rel.summary.1",
                    source="gradient",
                    target="learning_rate",
                    kind=RelationKind.GROUP_WITH,
                ),
                SceneRelation(
                    id="rel.summary.2",
                    source="learning_rate",
                    target="loss",
                    kind=RelationKind.FLOW,
                ),
            ],
            layout_intent=LayoutIntentSpec(type=LayoutIntent.PROCESS),
        ),
    )

    return VisualDirectorOutput(
        storyboard=Storyboard(
            storyboard_id="storyboard.gradient",
            script_id=script.script_id,
            scenes=scenes,
        ),
        scenegraphs=graphs,
    )


def main() -> int:
    brief, pack, evidence_graph, report, pedagogy = build_fixture()
    script = build_script(pedagogy)

    task = build_visual_director_task(
        brief,
        pack,
        evidence_graph,
        report,
        pedagogy,
        script,
    )
    context = json.loads(task["context"])
    if context["required_ids"]["script_id"] != script.script_id:
        raise SystemExit("VISUAL_DIRECTOR=FAIL script binding")
    if len(context["concept_registry"]["concepts"]) != len(pedagogy.concept_order):
        raise SystemExit("VISUAL_DIRECTOR=FAIL deterministic concept registry")

    registry = build_visual_concept_registry(pedagogy)
    output = build_visual_output(script, registry)
    validation = validate_visual_director_output(
        output,
        script=script,
        registry=registry,
    )
    require_core_ready(validation)
    if not validation.ready_for_core:
        raise SystemExit("VISUAL_DIRECTOR=FAIL valid semantic output rejected")

    print("VISUAL_DIRECTOR=PASS")
    print("scenegraphs_schema_valid=PASS")
    print("storyboard_script_coverage=PASS")
    print("deterministic_concept_registry=PASS")
    print("registry_identity_validation=PASS")
    print("semantic_layout_hints_only=PASS")
    print("no_pixel_coordinates=PASS")
    print("core_readiness_gate=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
