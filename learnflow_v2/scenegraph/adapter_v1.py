"""Deterministic adapter from V1 LessonPlan to V2 ConceptRegistry and SceneGraph."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

# Permitted import of V1 domain models
from app.domain.enums import VisualIntent
from app.domain.lesson import (
    ComparisonSpec,
    ConceptCardSpec,
    IllustrationSpec,
    LessonPlan,
    ProcessDiagramSpec,
    ScenePlan,
)

from learnflow_v2.concepts.normalize import (
    deterministic_concept_id,
    normalize_canonical_key,
    normalize_concept_alias,
)
from learnflow_v2.concepts.registry import ConceptRegistry
from learnflow_v2.concepts.schema import ConceptEntry, ConceptRegistrySchema, SemanticType
from learnflow_v2.scenegraph.enums import (
    LayoutIntent,
    NodeKind,
    PreferredRegion,
    ReadingDirection,
    RelationKind,
    ScenePurpose,
)
from learnflow_v2.scenegraph.schema import (
    LayoutHint,
    LayoutIntentSpec,
    SceneGraph,
    SceneGroup,
    SceneNode,
    SceneRelation,
)
from learnflow_v2.scenegraph.validation import validate_scenegraph_with_registry


class V1AdaptationResult(BaseModel):
    """Result of adapting a V1 LessonPlan into V2 semantic structures."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    registry: ConceptRegistrySchema
    scene_graphs: list[SceneGraph]

    def get_registry(self) -> ConceptRegistry:
        """Instantiate in-memory ConceptRegistry from schema."""
        return ConceptRegistry.from_schema(self.registry)


def _intent_to_layout_intent(intent: VisualIntent) -> LayoutIntent:
    """Map V1 VisualIntent to V2 LayoutIntent."""
    mapping = {
        VisualIntent.CONCEPT_CARD: LayoutIntent.CONCEPT_CARD,
        VisualIntent.PROCESS_DIAGRAM: LayoutIntent.PROCESS,
        VisualIntent.COMPARISON: LayoutIntent.COMPARISON,
        VisualIntent.ILLUSTRATION: LayoutIntent.ILLUSTRATION,
    }
    return mapping.get(intent, LayoutIntent.CONCEPT_CARD)


def _adapt_concept_card(
    scene_idx: int,
    scene: ScenePlan,
    spec: ConceptCardSpec,
    concept_id: str,
    canonical_key: str,
) -> tuple[list[SceneNode], list[SceneRelation], list[SceneGroup]]:
    nodes: list[SceneNode] = []
    relations: list[SceneRelation] = []
    groups: list[SceneGroup] = []

    primary_id = f"s_{scene_idx}_concept"
    nodes.append(
        SceneNode(
            id=primary_id,
            kind=NodeKind.CONCEPT,
            label=spec.heading,
            concept_ref=concept_id,
            semantic_key=canonical_key,
            semantic_role="PRIMARY_CONCEPT",
            layout_hint=LayoutHint(
                preferred_region=PreferredRegion.TOP,
                importance=1.0,
            ),
            style_refs=["concept.primary", "card.heading"],
        )
    )

    point_ids: list[str] = []
    for pt_idx, pt in enumerate(spec.points, 1):
        pt_id = f"s_{scene_idx}_pt_{pt_idx}"
        point_ids.append(pt_id)
        nodes.append(
            SceneNode(
                id=pt_id,
                kind=NodeKind.TEXT,
                label=pt,
                semantic_role="SUPPORTING_POINT",
                layout_hint=LayoutHint(
                    preferred_region=PreferredRegion.CENTER,
                    importance=0.7,
                    preferred_order=pt_idx,
                ),
                style_refs=["card.point"],
            )
        )
        relations.append(
            SceneRelation(
                id=f"rel_{scene_idx}_pt_{pt_idx}",
                source=pt_id,
                target=primary_id,
                kind=RelationKind.ANNOTATES,
                label="explains",
            )
        )

    groups.append(
        SceneGroup(
            id=f"grp_{scene_idx}_card",
            member_ids=[primary_id] + point_ids,
            label=spec.heading,
            semantic_role="CONCEPT_CARD_GROUP",
            layout_hint=LayoutHint(preferred_region=PreferredRegion.CENTER),
        )
    )

    return nodes, relations, groups


def _adapt_process_diagram(
    scene_idx: int,
    scene: ScenePlan,
    spec: ProcessDiagramSpec,
    concept_id: str,
    canonical_key: str,
) -> tuple[list[SceneNode], list[SceneRelation], list[SceneGroup]]:
    nodes: list[SceneNode] = []
    relations: list[SceneRelation] = []
    groups: list[SceneGroup] = []

    # 1. Primary semantic node representing the process concept
    topic_id = f"s_{scene_idx}_topic"
    topic_label = spec.title or scene.concept or scene.title
    nodes.append(
        SceneNode(
            id=topic_id,
            kind=NodeKind.CONCEPT,
            label=topic_label,
            concept_ref=concept_id,
            semantic_key=canonical_key,
            semantic_role="PROCESS_TOPIC",
            layout_hint=LayoutHint(
                preferred_region=PreferredRegion.TOP,
                importance=1.0,
            ),
            style_refs=["process.topic", "concept.primary"],
        )
    )

    # 2. Actors as entities
    actor_node_map: dict[str, str] = {}
    actor_ids: list[str] = []
    for actor in spec.actors:
        act_id = f"s_{scene_idx}_act_{actor.id}"
        actor_node_map[actor.id] = act_id
        actor_ids.append(act_id)
        nodes.append(
            SceneNode(
                id=act_id,
                kind=NodeKind.CONTAINER,
                label=actor.label,
                semantic_role="PROCESS_ACTOR",
                layout_hint=LayoutHint(
                    preferred_region=PreferredRegion.TOP,
                    importance=0.8,
                ),
                style_refs=["process.actor"],
            )
        )

    # 3. Steps as concepts/events
    step_ids: list[str] = []
    prev_step_id: str | None = None
    for step in spec.steps:
        step_id = f"s_{scene_idx}_step_{step.order}"
        step_ids.append(step_id)
        nodes.append(
            SceneNode(
                id=step_id,
                kind=NodeKind.CONCEPT,
                label=step.label,
                content=step.description,
                semantic_role="PROCESS_STEP",
                layout_hint=LayoutHint(
                    preferred_region=PreferredRegion.CENTER,
                    importance=0.7,
                    preferred_order=step.order,
                ),
                style_refs=["process.step"],
            )
        )

        # Relation from actor to step
        if step.from_actor and step.from_actor in actor_node_map:
            relations.append(
                SceneRelation(
                    id=f"rel_{scene_idx}_from_{step.order}",
                    source=actor_node_map[step.from_actor],
                    target=step_id,
                    kind=RelationKind.FLOW,
                    label="sends",
                )
            )

        # Relation from step to actor
        if step.to_actor and step.to_actor in actor_node_map:
            relations.append(
                SceneRelation(
                    id=f"rel_{scene_idx}_to_{step.order}",
                    source=step_id,
                    target=actor_node_map[step.to_actor],
                    kind=RelationKind.FLOW,
                    label="receives",
                )
            )

        # Sequence flow between steps
        if prev_step_id:
            relations.append(
                SceneRelation(
                    id=f"rel_{scene_idx}_seq_{step.order}",
                    source=prev_step_id,
                    target=step_id,
                    kind=RelationKind.SEQUENCE_BEFORE,
                )
            )
        prev_step_id = step_id

    all_members = [topic_id] + actor_ids + step_ids
    if all_members:
        groups.append(
            SceneGroup(
                id=f"grp_{scene_idx}_process",
                member_ids=all_members,
                label=spec.title,
                semantic_role="PROCESS_GROUP",
            )
        )

    return nodes, relations, groups


def _adapt_comparison(
    scene_idx: int,
    scene: ScenePlan,
    spec: ComparisonSpec,
    concept_id: str,
    canonical_key: str,
) -> tuple[list[SceneNode], list[SceneRelation], list[SceneGroup]]:
    nodes: list[SceneNode] = []
    relations: list[SceneRelation] = []
    groups: list[SceneGroup] = []

    primary_id = f"s_{scene_idx}_heading"
    nodes.append(
        SceneNode(
            id=primary_id,
            kind=NodeKind.CONCEPT,
            label=spec.title,
            concept_ref=concept_id,
            semantic_key=canonical_key,
            semantic_role="COMPARISON_TOPIC",
            layout_hint=LayoutHint(
                preferred_region=PreferredRegion.TOP,
                importance=1.0,
            ),
            style_refs=["comparison.title"],
        )
    )

    col_ids: list[str] = []
    all_members: list[str] = [primary_id]

    for col_idx, col in enumerate(spec.columns, 1):
        col_id = f"s_{scene_idx}_col_{col_idx}"
        col_ids.append(col_id)
        all_members.append(col_id)

        region = (
            PreferredRegion.LEFT
            if col_idx == 1
            else (PreferredRegion.RIGHT if col_idx == 2 else PreferredRegion.CENTER)
        )
        nodes.append(
            SceneNode(
                id=col_id,
                kind=NodeKind.CONTAINER,
                label=col.title,
                content=col.subtitle,
                semantic_role="COMPARISON_COLUMN",
                layout_hint=LayoutHint(
                    preferred_region=region,
                    importance=0.8,
                    preferred_order=col_idx,
                ),
                style_refs=["comparison.column"],
            )
        )

        col_point_ids: list[str] = []
        for pt_idx, pt in enumerate(col.points, 1):
            pt_id = f"s_{scene_idx}_c{col_idx}_pt_{pt_idx}"
            col_point_ids.append(pt_id)
            all_members.append(pt_id)
            nodes.append(
                SceneNode(
                    id=pt_id,
                    kind=NodeKind.TEXT,
                    label=pt,
                    semantic_role="COLUMN_POINT",
                    layout_hint=LayoutHint(
                        preferred_region=region,
                        importance=0.6,
                        preferred_order=pt_idx,
                    ),
                    style_refs=["comparison.point"],
                )
            )
            relations.append(
                SceneRelation(
                    id=f"rel_{scene_idx}_c{col_idx}_pt_{pt_idx}",
                    source=pt_id,
                    target=col_id,
                    kind=RelationKind.PART_OF,
                )
            )

        groups.append(
            SceneGroup(
                id=f"grp_{scene_idx}_col_{col_idx}",
                member_ids=[col_id] + col_point_ids,
                label=col.title,
                semantic_role="COLUMN_GROUP",
            )
        )

    # Cross-column comparison relation
    if len(col_ids) >= 2:
        relations.append(
            SceneRelation(
                id=f"rel_{scene_idx}_compare",
                source=col_ids[0],
                target=col_ids[1],
                kind=RelationKind.COMPARES_WITH,
                label="vs",
            )
        )

    groups.append(
        SceneGroup(
            id=f"grp_{scene_idx}_comparison",
            member_ids=all_members,
            label=spec.title,
            semantic_role="COMPARISON_GROUP",
        )
    )

    return nodes, relations, groups


def _adapt_illustration(
    scene_idx: int,
    scene: ScenePlan,
    spec: IllustrationSpec,
    concept_id: str,
    canonical_key: str,
) -> tuple[list[SceneNode], list[SceneRelation], list[SceneGroup]]:
    nodes: list[SceneNode] = []
    relations: list[SceneRelation] = []
    groups: list[SceneGroup] = []

    primary_id = f"s_{scene_idx}_concept"
    nodes.append(
        SceneNode(
            id=primary_id,
            kind=NodeKind.CONCEPT,
            label=scene.title,
            concept_ref=concept_id,
            semantic_key=canonical_key,
            semantic_role="ILLUSTRATION_SUBJECT",
            layout_hint=LayoutHint(
                preferred_region=PreferredRegion.TOP,
                importance=1.0,
            ),
            style_refs=["illustration.title"],
        )
    )

    img_id = f"s_{scene_idx}_image"
    nodes.append(
        SceneNode(
            id=img_id,
            kind=NodeKind.IMAGE,
            label=spec.prompt,
            semantic_role="ILLUSTRATION_IMAGE_PLACEHOLDER",
            layout_hint=LayoutHint(
                preferred_region=PreferredRegion.CENTER,
                importance=0.9,
            ),
            style_refs=["illustration.image"],
        )
    )

    relations.append(
        SceneRelation(
            id=f"rel_{scene_idx}_illustrates",
            source=img_id,
            target=primary_id,
            kind=RelationKind.ANNOTATES,
            label="visualizes",
        )
    )

    heading_id = f"s_{scene_idx}_fallback_heading"
    nodes.append(
        SceneNode(
            id=heading_id,
            kind=NodeKind.TEXT,
            label=spec.fallback_heading,
            semantic_role="FALLBACK_HEADING",
            layout_hint=LayoutHint(
                preferred_region=PreferredRegion.BOTTOM,
                importance=0.6,
            ),
            style_refs=["illustration.fallback_heading"],
        )
    )

    fb_pt_ids: list[str] = []
    for pt_idx, pt in enumerate(spec.fallback_points, 1):
        pt_id = f"s_{scene_idx}_fb_pt_{pt_idx}"
        fb_pt_ids.append(pt_id)
        nodes.append(
            SceneNode(
                id=pt_id,
                kind=NodeKind.TEXT,
                label=pt,
                semantic_role="FALLBACK_POINT",
                layout_hint=LayoutHint(
                    preferred_region=PreferredRegion.BOTTOM,
                    importance=0.5,
                    preferred_order=pt_idx,
                ),
                style_refs=["illustration.fallback_point"],
            )
        )
        relations.append(
            SceneRelation(
                id=f"rel_{scene_idx}_fb_rel_{pt_idx}",
                source=pt_id,
                target=heading_id,
                kind=RelationKind.PART_OF,
            )
        )

    groups.append(
        SceneGroup(
            id=f"grp_{scene_idx}_illustration",
            member_ids=[primary_id, img_id, heading_id] + fb_pt_ids,
            label=scene.title,
            semantic_role="ILLUSTRATION_GROUP",
        )
    )

    return nodes, relations, groups


def adapt_v1_lesson_plan(plan: LessonPlan) -> V1AdaptationResult:
    """Adapt a V1 LessonPlan into V2 ConceptRegistry and SceneGraph models.

    Invariants:
    - Never mutates the input LessonPlan.
    - Fully deterministic: identical input yields byte-identical output.
    - ConceptRegistry: canonical entries derived from ScenePlan.concept.
    - All 4 VisualIntent types are supported.
    - All SceneGraphs pass strict local and registry-aware validation.
    """
    registry = ConceptRegistry()

    # 1. Register canonical concepts across the entire lesson
    concept_map: dict[str, tuple[str, str]] = {}  # normalized concept -> (concept_id, canonical_key)

    for scene in plan.scenes:
        raw_concept = scene.concept.strip() if scene.concept else plan.topic.strip()
        norm_alias = normalize_concept_alias(raw_concept)

        if norm_alias not in concept_map:
            canonical_key = normalize_canonical_key(raw_concept)
            concept_id = deterministic_concept_id(canonical_key)

            if not registry.contains(concept_id):
                registry.register(
                    ConceptEntry(
                        concept_id=concept_id,
                        canonical_key=canonical_key,
                        label=raw_concept,
                        aliases=[norm_alias] if norm_alias != raw_concept.casefold() else [],
                        semantic_type=SemanticType.CONCEPT,
                        provenance="v1_lesson_plan",
                    )
                )
            concept_map[norm_alias] = (concept_id, canonical_key)

    # 2. Build SceneGraphs
    scene_graphs: list[SceneGraph] = []

    for scene_idx, scene in enumerate(plan.scenes, 1):
        raw_concept = scene.concept.strip() if scene.concept else plan.topic.strip()
        norm_alias = normalize_concept_alias(raw_concept)
        concept_id, canonical_key = concept_map[norm_alias]

        layout_intent_type = _intent_to_layout_intent(scene.visual_intent)
        layout_spec = LayoutIntentSpec(
            type=layout_intent_type,
            reading_direction=ReadingDirection.LEFT_TO_RIGHT,
        )

        nodes: list[SceneNode] = []
        relations: list[SceneRelation] = []
        groups: list[SceneGroup] = []

        if isinstance(scene.visual_spec, ConceptCardSpec):
            nodes, relations, groups = _adapt_concept_card(
                scene_idx, scene, scene.visual_spec, concept_id, canonical_key
            )
        elif isinstance(scene.visual_spec, ProcessDiagramSpec):
            nodes, relations, groups = _adapt_process_diagram(
                scene_idx, scene, scene.visual_spec, concept_id, canonical_key
            )
        elif isinstance(scene.visual_spec, ComparisonSpec):
            nodes, relations, groups = _adapt_comparison(
                scene_idx, scene, scene.visual_spec, concept_id, canonical_key
            )
        elif isinstance(scene.visual_spec, IllustrationSpec):
            nodes, relations, groups = _adapt_illustration(
                scene_idx, scene, scene.visual_spec, concept_id, canonical_key
            )
        else:
            # Fallback concept node
            nodes.append(
                SceneNode(
                    id=f"s_{scene_idx}_concept",
                    kind=NodeKind.CONCEPT,
                    label=scene.title,
                    concept_ref=concept_id,
                    semantic_key=canonical_key,
                )
            )

        graph = SceneGraph(
            scene_id=scene.scene_id,
            purpose=ScenePurpose.EXPLAIN,
            concept=scene.concept,
            nodes=nodes,
            relations=relations,
            groups=groups,
            layout_intent=layout_spec,
            style_refs=[f"scene.{scene.visual_intent.value}"],
        )

        # Validate against registry
        validate_scenegraph_with_registry(graph, registry)
        scene_graphs.append(graph)

    return V1AdaptationResult(
        registry=registry.to_schema(),
        scene_graphs=scene_graphs,
    )
