"""Deterministic generator for 100 valid SceneGraph fixtures and negative invalid cases.

Produces:
- benchmarks/fixtures/v2/scenegraph_valid_corpus.json
- benchmarks/fixtures/v2/scenegraph_invalid_cases.json

Strictly deterministic: no network, no LLMs, seeded/fixed math only.
"""

import json
from pathlib import Path

from learnflow_v2.concepts.normalize import (
    deterministic_concept_id,
    normalize_canonical_key,
)
from learnflow_v2.concepts.registry import ConceptRegistry
from learnflow_v2.concepts.schema import ConceptEntry, SemanticType
from learnflow_v2.scenegraph.enums import (
    LayoutIntent,
    NodeKind,
    PortHint,
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

OUTPUT_DIR = Path("benchmarks/fixtures/v2")


def build_corpus_concept_registry() -> ConceptRegistry:
    registry = ConceptRegistry()

    concepts_data = [
        ("Loss Function", ["loss", "cost function", "error function"], SemanticType.CONCEPT),
        ("Gradient Descent", ["gradient", "steepest descent"], SemanticType.PROCESS),
        ("Neural Network", ["network", "ann", "neural net"], SemanticType.ENTITY),
        ("Backpropagation", ["backprop", "backward pass"], SemanticType.PROCESS),
        ("Learning Rate", ["eta", "step size"], SemanticType.PROPERTY),
        ("Cross Entropy", ["log loss", "multinomial loss"], SemanticType.CONCEPT),
        ("Attention Mechanism", ["self attention", "cross attention"], SemanticType.PROCESS),
        ("Transformer Block", ["transformer", "transformer layer"], SemanticType.ENTITY),
        ("Validation Accuracy", ["val acc", "test accuracy"], SemanticType.METRIC),
        ("Overfitting", ["high variance", "generalization gap"], SemanticType.CONCEPT),
        ("Regularization", ["weight decay", "l2 penalty"], SemanticType.PROCESS),
        ("Optimizer", ["adam", "sgd", "rmsprop"], SemanticType.ENTITY),
    ]

    for label, aliases, sem_type in concepts_data:
        canon_key = normalize_canonical_key(label)
        cid = deterministic_concept_id(canon_key)
        registry.register(
            ConceptEntry(
                concept_id=cid,
                canonical_key=canon_key,
                label=label,
                aliases=aliases,
                semantic_type=sem_type,
            )
        )

    return registry


def build_100_valid_scenegraphs(registry: ConceptRegistry) -> list[SceneGraph]:
    graphs: list[SceneGraph] = []
    concepts = registry.all_concepts()

    node_kinds = list(NodeKind)
    relation_kinds = list(RelationKind)
    purposes = list(ScenePurpose)
    intents = list(LayoutIntent)
    directions = list(ReadingDirection)
    regions = list(PreferredRegion)
    ports = list(PortHint)

    for i in range(1, 101):
        scene_id = f"corpus_scene_{i:03d}"
        purpose = purposes[(i - 1) % len(purposes)]
        intent = intents[(i - 1) % len(intents)]
        direction = directions[(i - 1) % len(directions)]

        # Concept binding: cycle through concepts
        primary_concept = concepts[(i - 1) % len(concepts)]
        secondary_concept = concepts[i % len(concepts)]

        nodes: list[SceneNode] = []
        relations: list[SceneRelation] = []
        groups: list[SceneGroup] = []

        # Ensure representation of all NodeKinds across the corpus
        primary_kind = node_kinds[(i - 1) % len(node_kinds)]
        secondary_kind = node_kinds[i % len(node_kinds)]
        tertiary_kind = node_kinds[(i + 1) % len(node_kinds)]

        n1_id = f"node_{i:03d}_a"
        n2_id = f"node_{i:03d}_b"
        n3_id = f"node_{i:03d}_c"

        n1 = SceneNode(
            id=n1_id,
            kind=primary_kind,
            label=f"Primary Node {i} ({primary_concept.label})",
            content="f(x) = y" if primary_kind in (NodeKind.MATH, NodeKind.EQUATION) else None,
            concept_ref=primary_concept.concept_id,
            semantic_key=primary_concept.canonical_key,
            semantic_role="PRIMARY_FOCUS",
            layout_hint=LayoutHint(
                preferred_region=regions[(i - 1) % len(regions)],
                importance=0.9,
                keep_near=[n2_id],
                preferred_order=1,
            ),
            style_refs=["concept.primary", f"theme.{intent.value.lower()}"],
        )

        n2 = SceneNode(
            id=n2_id,
            kind=secondary_kind,
            label=f"Secondary Node {i} ({secondary_concept.label})",
            concept_ref=secondary_concept.concept_id,
            semantic_key=secondary_concept.canonical_key,
            semantic_role="SECONDARY_FOCUS",
            layout_hint=LayoutHint(
                preferred_region=regions[i % len(regions)],
                importance=0.7,
                keep_apart=[n3_id],
                preferred_order=2,
            ),
            style_refs=["concept.secondary"],
        )

        n3 = SceneNode(
            id=n3_id,
            kind=tertiary_kind,
            label=f"Supporting Element {i}",
            content="code_snippet()" if tertiary_kind == NodeKind.CODE else None,
            semantic_role="SUPPORTING_ELEMENT",
            layout_hint=LayoutHint(
                preferred_region=regions[(i + 1) % len(regions)],
                importance=0.5,
                preferred_order=3,
            ),
            style_refs=["support.default"],
        )

        nodes.extend([n1, n2, n3])

        # Relations: cycle through ALL relation kinds
        rel_kind_1 = relation_kinds[(i - 1) % len(relation_kinds)]
        rel_kind_2 = relation_kinds[i % len(relation_kinds)]

        r1 = SceneRelation(
            id=f"rel_{i:03d}_1",
            source=n1_id,
            target=n2_id,
            kind=rel_kind_1,
            label=f"{rel_kind_1.value.lower()}_relation",
            source_port=ports[(i - 1) % len(ports)],
            target_port=ports[i % len(ports)],
            style_refs=["edge.primary"],
        )

        r2 = SceneRelation(
            id=f"rel_{i:03d}_2",
            source=n2_id,
            target=n3_id,
            kind=rel_kind_2,
            label=f"{rel_kind_2.value.lower()}_relation",
            source_port=ports[i % len(ports)],
            target_port=ports[(i + 1) % len(ports)],
            style_refs=["edge.secondary"],
        )

        relations.extend([r1, r2])

        # Groups
        g1 = SceneGroup(
            id=f"grp_{i:03d}_main",
            member_ids=[n1_id, n2_id],
            label=f"Group {i} Primary",
            semantic_role="MAIN_CLUSTER",
            layout_hint=LayoutHint(
                preferred_region=regions[(i - 1) % len(regions)],
                importance=0.8,
            ),
        )
        groups.append(g1)

        graph = SceneGraph(
            scene_id=scene_id,
            purpose=purpose,
            concept=primary_concept.label,
            nodes=nodes,
            relations=relations,
            groups=groups,
            layout_intent=LayoutIntentSpec(
                type=intent,
                reading_direction=direction,
            ),
            style_refs=[f"scene.{intent.value.lower()}"],
        )

        validate_scenegraph_with_registry(graph, registry)
        graphs.append(graph)

    return graphs


def build_invalid_cases_corpus() -> list[dict]:
    return [
        {
            "case_id": "duplicate_node_id",
            "description": "Two nodes in the same scene share the identical node ID",
            "expected_error_code": "SCENEGRAPH_DUPLICATE_NODE_ID",
            "target_type": "scenegraph",
            "payload": {
                "scene_id": "invalid_dup_node",
                "nodes": [
                    {"id": "node_x", "kind": "CONCEPT", "label": "Node 1"},
                    {"id": "node_x", "kind": "TEXT", "label": "Node 2"},
                ],
            },
        },
        {
            "case_id": "duplicate_relation_id",
            "description": "Two relations in the same scene share the identical relation ID",
            "expected_error_code": "SCENEGRAPH_DUPLICATE_RELATION_ID",
            "target_type": "scenegraph",
            "payload": {
                "scene_id": "invalid_dup_rel",
                "nodes": [
                    {"id": "node_a", "kind": "CONCEPT", "label": "Node A"},
                    {"id": "node_b", "kind": "TEXT", "label": "Node B"},
                ],
                "relations": [
                    {"id": "rel_1", "source": "node_a", "target": "node_b", "kind": "FLOW"},
                    {"id": "rel_1", "source": "node_b", "target": "node_a", "kind": "FLOW"},
                ],
            },
        },
        {
            "case_id": "duplicate_group_id",
            "description": "Two groups in the same scene share the identical group ID",
            "expected_error_code": "SCENEGRAPH_DUPLICATE_GROUP_ID",
            "target_type": "scenegraph",
            "payload": {
                "scene_id": "invalid_dup_grp",
                "nodes": [
                    {"id": "node_a", "kind": "CONCEPT"},
                    {"id": "node_b", "kind": "TEXT"},
                ],
                "groups": [
                    {"id": "grp_1", "member_ids": ["node_a"]},
                    {"id": "grp_1", "member_ids": ["node_b"]},
                ],
            },
        },
        {
            "case_id": "unknown_relation_source",
            "description": "Relation references a source node ID that does not exist",
            "expected_error_code": "SCENEGRAPH_INVALID_RELATION_REF",
            "target_type": "scenegraph",
            "payload": {
                "scene_id": "invalid_rel_source",
                "nodes": [{"id": "node_b", "kind": "TEXT"}],
                "relations": [
                    {"id": "rel_1", "source": "ghost_node", "target": "node_b", "kind": "FLOW"}
                ],
            },
        },
        {
            "case_id": "unknown_relation_target",
            "description": "Relation references a target node ID that does not exist",
            "expected_error_code": "SCENEGRAPH_INVALID_RELATION_REF",
            "target_type": "scenegraph",
            "payload": {
                "scene_id": "invalid_rel_target",
                "nodes": [{"id": "node_a", "kind": "CONCEPT"}],
                "relations": [
                    {"id": "rel_1", "source": "node_a", "target": "ghost_node", "kind": "FLOW"}
                ],
            },
        },
        {
            "case_id": "unknown_group_member",
            "description": "Group member_ids includes a node ID that does not exist",
            "expected_error_code": "SCENEGRAPH_INVALID_GROUP_REF",
            "target_type": "scenegraph",
            "payload": {
                "scene_id": "invalid_grp_member",
                "nodes": [{"id": "node_a", "kind": "CONCEPT"}],
                "groups": [{"id": "grp_1", "member_ids": ["node_a", "ghost_node"]}],
            },
        },
        {
            "case_id": "duplicate_group_member",
            "description": "Group member_ids contains the same node ID twice",
            "expected_error_code": "SCENEGRAPH_INVALID_GROUP_REF",
            "target_type": "scenegraph",
            "payload": {
                "scene_id": "invalid_dup_member",
                "nodes": [{"id": "node_a", "kind": "CONCEPT"}],
                "groups": [{"id": "grp_1", "member_ids": ["node_a", "node_a"]}],
            },
        },
        {
            "case_id": "unknown_layout_hint_ref",
            "description": "LayoutHint keep_near references a node ID that does not exist",
            "expected_error_code": "SCENEGRAPH_INVALID_LAYOUT_REF",
            "target_type": "scenegraph",
            "payload": {
                "scene_id": "invalid_layout_ref",
                "nodes": [
                    {
                        "id": "node_a",
                        "kind": "CONCEPT",
                        "layout_hint": {"keep_near": ["missing_node"]},
                    }
                ],
            },
        },
        {
            "case_id": "unknown_concept_ref",
            "description": "SceneNode concept_ref does not exist in ConceptRegistry",
            "expected_error_code": "SCENEGRAPH_UNKNOWN_CONCEPT_REF",
            "target_type": "registry_validation",
            "payload": {
                "scene_id": "unknown_cref",
                "nodes": [
                    {
                        "id": "node_a",
                        "kind": "CONCEPT",
                        "concept_ref": "c_non_existent",
                        "semantic_key": "concept:non_existent",
                    }
                ],
            },
        },
        {
            "case_id": "semantic_key_mismatch",
            "description": "SceneNode semantic_key conflicts with canonical_key in ConceptRegistry",
            "expected_error_code": "SCENEGRAPH_SEMANTIC_KEY_MISMATCH",
            "target_type": "registry_validation",
            "payload": {
                "scene_id": "mismatch_key",
                "nodes": [
                    {
                        "id": "node_a",
                        "kind": "CONCEPT",
                        "concept_ref": "c_loss_test",
                        "semantic_key": "concept:wrong_key",
                    }
                ],
            },
        },
        {
            "case_id": "importance_out_of_bounds",
            "description": "LayoutHint importance > 1.0 rejected by Pydantic bounds",
            "expected_error_code": "VALIDATION_ERROR",
            "target_type": "scenegraph",
            "payload": {
                "scene_id": "invalid_importance",
                "nodes": [
                    {
                        "id": "node_a",
                        "kind": "CONCEPT",
                        "layout_hint": {"importance": 1.5},
                    }
                ],
            },
        },
        {
            "case_id": "forbidden_geometry_x",
            "description": "Forbidden pixel coordinate x rejected by extra='forbid'",
            "expected_error_code": "VALIDATION_ERROR",
            "target_type": "scenegraph",
            "payload": {
                "scene_id": "invalid_geometry_x",
                "nodes": [
                    {
                        "id": "node_a",
                        "kind": "CONCEPT",
                        "x": 472,
                    }
                ],
            },
        },
        {
            "case_id": "forbidden_geometry_pixel_width",
            "description": "Forbidden pixel_width rejected by extra='forbid'",
            "expected_error_code": "VALIDATION_ERROR",
            "target_type": "scenegraph",
            "payload": {
                "scene_id": "invalid_pixel_width",
                "nodes": [
                    {
                        "id": "node_a",
                        "kind": "CONCEPT",
                        "pixel_width": 300,
                    }
                ],
            },
        },
        {
            "case_id": "registry_canonical_key_collision",
            "description": "Registering two distinct concepts with the same canonical key",
            "expected_error_code": "CONCEPT_REGISTRY_COLLISION",
            "target_type": "registry",
            "payload": {
                "concept_1": {
                    "concept_id": "c_1",
                    "canonical_key": "concept:loss",
                    "label": "Loss A",
                },
                "concept_2": {
                    "concept_id": "c_2",
                    "canonical_key": "concept:loss",
                    "label": "Loss B",
                },
            },
        },
        {
            "case_id": "registry_ambiguous_alias_collision",
            "description": "Registering two distinct concepts claiming the same alias",
            "expected_error_code": "CONCEPT_REGISTRY_COLLISION",
            "target_type": "registry",
            "payload": {
                "concept_1": {
                    "concept_id": "c_1",
                    "canonical_key": "concept:loss",
                    "label": "Loss",
                    "aliases": ["cost function"],
                },
                "concept_2": {
                    "concept_id": "c_2",
                    "canonical_key": "concept:cost",
                    "label": "Cost",
                    "aliases": ["cost function"],
                },
            },
        },
        {
            "case_id": "semantic_key_without_concept_ref",
            "description": "SceneNode specifies semantic_key without required concept_ref",
            "expected_error_code": "SCENEGRAPH_INCOMPLETE_SEMANTIC_IDENTITY",
            "target_type": "scenegraph",
            "payload": {
                "scene_id": "invalid_sem_key_only",
                "nodes": [
                    {
                        "id": "node_a",
                        "kind": "CONCEPT",
                        "semantic_key": "concept:orphan",
                    }
                ],
            },
        },
        {
            "case_id": "concept_ref_without_semantic_key",
            "description": "SceneNode specifies concept_ref without required semantic_key",
            "expected_error_code": "SCENEGRAPH_INCOMPLETE_SEMANTIC_IDENTITY",
            "target_type": "scenegraph",
            "payload": {
                "scene_id": "invalid_cref_only",
                "nodes": [
                    {
                        "id": "node_a",
                        "kind": "CONCEPT",
                        "concept_ref": "c_loss_test",
                    }
                ],
            },
        },
        {
            "case_id": "unsupported_scenegraph_schema_version",
            "description": "SceneGraph schema_version is unsupported (e.g. 999)",
            "expected_error_code": "VALIDATION_ERROR",
            "target_type": "scenegraph",
            "payload": {
                "schema_version": "999",
                "scene_id": "invalid_version_sg",
                "nodes": [{"id": "node_a", "kind": "CONCEPT"}],
            },
        },
        {
            "case_id": "unsupported_registry_schema_version",
            "description": "ConceptRegistrySchema schema_version is unsupported (e.g. 999)",
            "expected_error_code": "VALIDATION_ERROR",
            "target_type": "registry_schema",
            "payload": {
                "schema_version": "999",
                "concepts": [],
            },
        },
    ]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    registry = build_corpus_concept_registry()
    graphs = build_100_valid_scenegraphs(registry)

    valid_corpus_path = OUTPUT_DIR / "scenegraph_valid_corpus.json"
    corpus_data = {
        "registry": registry.to_schema().model_dump(mode="json"),
        "graph_count": len(graphs),
        "graphs": [g.model_dump(mode="json") for g in graphs],
    }
    with open(valid_corpus_path, "w", encoding="utf-8") as f:
        json.dump(corpus_data, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(graphs)} valid graphs into {valid_corpus_path}")

    invalid_corpus_path = OUTPUT_DIR / "scenegraph_invalid_cases.json"
    invalid_cases = build_invalid_cases_corpus()
    with open(invalid_corpus_path, "w", encoding="utf-8") as f:
        json.dump(invalid_cases, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(invalid_cases)} invalid cases into {invalid_corpus_path}")


if __name__ == "__main__":
    main()
