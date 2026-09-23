"""Tests for SceneGraph Pydantic schema, strict validation, and geometry rejection."""

import pytest
from pydantic import ValidationError

from learnflow_v2.core.errors import (
    SceneGraphDuplicateGroupIdError,
    SceneGraphDuplicateNodeIdError,
    SceneGraphDuplicateRelationIdError,
    SceneGraphInvalidGroupRefError,
    SceneGraphInvalidLayoutRefError,
    SceneGraphInvalidRelationRefError,
)
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


def test_minimal_graph_valid():
    graph = SceneGraph(
        scene_id="scene_001",
        nodes=[
            SceneNode(id="n1", kind=NodeKind.TEXT, label="Hello"),
        ],
    )
    assert graph.scene_id == "scene_001"
    assert len(graph.nodes) == 1
    assert graph.layout_intent.type == LayoutIntent.CONCEPT_CARD


def test_all_enums_parse():
    # Verify all enum values parse without error
    for kind in NodeKind:
        node = SceneNode(id=f"n_{kind.value.lower()}", kind=kind)
        assert node.kind == kind

    for r_kind in RelationKind:
        rel = SceneRelation(
            id=f"r_{r_kind.value.lower()}",
            source="n1",
            target="n2",
            kind=r_kind,
        )
        assert rel.kind == r_kind

    for purpose in ScenePurpose:
        assert ScenePurpose(purpose.value) == purpose

    for intent in LayoutIntent:
        assert LayoutIntent(intent.value) == intent

    for direction in ReadingDirection:
        assert ReadingDirection(direction.value) == direction

    for region in PreferredRegion:
        assert PreferredRegion(region.value) == region

    for port in PortHint:
        assert PortHint(port.value) == port


def test_duplicate_node_id_rejected():
    with pytest.raises(SceneGraphDuplicateNodeIdError) as exc_info:
        SceneGraph(
            scene_id="scene_dup_node",
            nodes=[
                SceneNode(id="same_id", kind=NodeKind.TEXT, label="A"),
                SceneNode(id="same_id", kind=NodeKind.CONCEPT, label="B"),
            ],
        )
    assert exc_info.value.code == "SCENEGRAPH_DUPLICATE_NODE_ID"


def test_duplicate_relation_id_rejected():
    with pytest.raises(SceneGraphDuplicateRelationIdError) as exc_info:
        SceneGraph(
            scene_id="scene_dup_rel",
            nodes=[
                SceneNode(id="n1", kind=NodeKind.TEXT),
                SceneNode(id="n2", kind=NodeKind.TEXT),
            ],
            relations=[
                SceneRelation(id="r_same", source="n1", target="n2", kind=RelationKind.FLOW),
                SceneRelation(id="r_same", source="n2", target="n1", kind=RelationKind.FLOW),
            ],
        )
    assert exc_info.value.code == "SCENEGRAPH_DUPLICATE_RELATION_ID"


def test_relation_unknown_source_rejected():
    with pytest.raises(SceneGraphInvalidRelationRefError) as exc_info:
        SceneGraph(
            scene_id="scene_bad_source",
            nodes=[SceneNode(id="n2", kind=NodeKind.TEXT)],
            relations=[
                SceneRelation(id="r1", source="missing_source", target="n2", kind=RelationKind.FLOW),
            ],
        )
    assert exc_info.value.code == "SCENEGRAPH_INVALID_RELATION_REF"


def test_relation_unknown_target_rejected():
    with pytest.raises(SceneGraphInvalidRelationRefError) as exc_info:
        SceneGraph(
            scene_id="scene_bad_target",
            nodes=[SceneNode(id="n1", kind=NodeKind.TEXT)],
            relations=[
                SceneRelation(id="r1", source="n1", target="missing_target", kind=RelationKind.FLOW),
            ],
        )
    assert exc_info.value.code == "SCENEGRAPH_INVALID_RELATION_REF"


def test_duplicate_group_id_rejected():
    with pytest.raises(SceneGraphDuplicateGroupIdError) as exc_info:
        SceneGraph(
            scene_id="scene_dup_grp",
            nodes=[
                SceneNode(id="n1", kind=NodeKind.TEXT),
                SceneNode(id="n2", kind=NodeKind.TEXT),
            ],
            groups=[
                SceneGroup(id="grp_1", member_ids=["n1"]),
                SceneGroup(id="grp_1", member_ids=["n2"]),
            ],
        )
    assert exc_info.value.code == "SCENEGRAPH_DUPLICATE_GROUP_ID"


def test_invalid_group_member_rejected():
    with pytest.raises(SceneGraphInvalidGroupRefError) as exc_info:
        SceneGraph(
            scene_id="scene_bad_grp_member",
            nodes=[SceneNode(id="n1", kind=NodeKind.TEXT)],
            groups=[
                SceneGroup(id="grp_1", member_ids=["n1", "missing_member"]),
            ],
        )
    assert exc_info.value.code == "SCENEGRAPH_INVALID_GROUP_REF"


def test_duplicate_group_member_rejected():
    with pytest.raises(SceneGraphInvalidGroupRefError) as exc_info:
        SceneGraph(
            scene_id="scene_dup_member",
            nodes=[SceneNode(id="n1", kind=NodeKind.TEXT)],
            groups=[
                SceneGroup(id="grp_1", member_ids=["n1", "n1"]),
            ],
        )
    assert exc_info.value.code == "SCENEGRAPH_INVALID_GROUP_REF"


def test_layout_hint_unknown_reference_rejected():
    with pytest.raises(SceneGraphInvalidLayoutRefError) as exc_info:
        SceneGraph(
            scene_id="scene_bad_layout_ref",
            nodes=[
                SceneNode(
                    id="n1",
                    kind=NodeKind.TEXT,
                    layout_hint=LayoutHint(keep_near=["nonexistent_node"]),
                )
            ],
        )
    assert exc_info.value.code == "SCENEGRAPH_INVALID_LAYOUT_REF"


def test_importance_bounds_validated():
    # Valid importance in [0.0, 1.0]
    hint = LayoutHint(importance=0.0)
    assert hint.importance == 0.0
    hint2 = LayoutHint(importance=1.0)
    assert hint2.importance == 1.0

    # Outside bounds raises ValidationError
    with pytest.raises(ValidationError):
        LayoutHint(importance=-0.1)

    with pytest.raises(ValidationError):
        LayoutHint(importance=1.1)


def test_strict_model_rejects_pixel_geometry():
    """SceneGraph MUST NOT contain x, y, pixel coordinates, or renderer primitives."""
    # Extra field 'x'
    with pytest.raises(ValidationError):
        SceneNode(id="n1", kind=NodeKind.TEXT, x=100)  # type: ignore[call-arg]

    # Extra field 'y'
    with pytest.raises(ValidationError):
        SceneNode(id="n1", kind=NodeKind.TEXT, y=200)  # type: ignore[call-arg]

    # Extra field 'pixel_width'
    with pytest.raises(ValidationError):
        SceneNode(id="n1", kind=NodeKind.TEXT, pixel_width=300)  # type: ignore[call-arg]

    # Extra field 'font_size'
    with pytest.raises(ValidationError):
        SceneNode(id="n1", kind=NodeKind.TEXT, font_size=24)  # type: ignore[call-arg]

    # Extra geometry on LayoutHint
    with pytest.raises(ValidationError):
        LayoutHint(x=50)  # type: ignore[call-arg]

    # Extra geometry on SceneGraph root
    with pytest.raises(ValidationError):
        SceneGraph(scene_id="s1", width=1920)  # type: ignore[call-arg]


def test_scenegraph_schema_version_enforced():
    # 2.1 passes
    sg = SceneGraph(scene_id="s_ver", schema_version="2.1")
    assert sg.schema_version == "2.1"

    # Unsupported versions rejected
    with pytest.raises(ValidationError):
        SceneGraph(scene_id="s_bad_ver", schema_version="2.0")  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        SceneGraph(scene_id="s_bad_ver", schema_version="999")  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        SceneGraph(scene_id="s_bad_ver", schema_version="")  # type: ignore[arg-type]


def test_canonical_serialization_order_invariance():
    from learnflow_v2.concepts.registry import ConceptRegistry
    from learnflow_v2.concepts.schema import ConceptEntry
    from learnflow_v2.core.serialization import canonical_json

    # 1. Registry order invariance
    c_a = ConceptEntry(concept_id="c_alpha", canonical_key="concept:alpha", label="Alpha", aliases=["a2", "a1"])
    c_b = ConceptEntry(concept_id="c_beta", canonical_key="concept:beta", label="Beta")

    reg1 = ConceptRegistry()
    reg1.register(c_a)
    reg1.register(c_b)

    reg2 = ConceptRegistry()
    reg2.register(c_b)
    reg2.register(c_a)

    assert canonical_json(reg1.to_schema()) == canonical_json(reg2.to_schema())

    # 2. SceneGraph node order invariance
    node1 = SceneNode(id="n1", kind=NodeKind.TEXT, label="One", style_refs=["style.b", "style.a"])
    node2 = SceneNode(id="n2", kind=NodeKind.CONCEPT, label="Two")
    node3 = SceneNode(id="n3", kind=NodeKind.ICON, label="Three")

    graph_nodes_1 = SceneGraph(scene_id="sg_order", nodes=[node1, node2, node3])
    graph_nodes_2 = SceneGraph(scene_id="sg_order", nodes=[node3, node1, node2])

    assert canonical_json(graph_nodes_1) == canonical_json(graph_nodes_2)

    # 3. Relation order invariance
    r1 = SceneRelation(id="r1", source="n1", target="n2", kind=RelationKind.FLOW)
    r2 = SceneRelation(id="r2", source="n2", target="n3", kind=RelationKind.SEQUENCE_BEFORE)

    graph_rel_1 = SceneGraph(scene_id="sg_rel", nodes=[node1, node2, node3], relations=[r1, r2])
    graph_rel_2 = SceneGraph(scene_id="sg_rel", nodes=[node1, node2, node3], relations=[r2, r1])

    assert canonical_json(graph_rel_1) == canonical_json(graph_rel_2)

    # 4. Group order invariance
    g1 = SceneGroup(id="g1", member_ids=["n1", "n2"], label="Group 1")
    g2 = SceneGroup(id="g2", member_ids=["n2", "n3"], label="Group 2")

    graph_grp_1 = SceneGraph(scene_id="sg_grp", nodes=[node1, node2, node3], groups=[g1, g2])
    graph_grp_2 = SceneGraph(scene_id="sg_grp", nodes=[node1, node2, node3], groups=[g2, g1])

    assert canonical_json(graph_grp_1) == canonical_json(graph_grp_2)

    # 5. Meaningfully different graphs produce different canonical JSON
    graph_diff = SceneGraph(scene_id="sg_grp", nodes=[node1, node2, node3], groups=[g1])
    assert canonical_json(graph_grp_1) != canonical_json(graph_diff)

    # 6. Round-trip stability
    json_str = canonical_json(graph_grp_1)
    restored = SceneGraph.model_validate_json(json_str)
    assert canonical_json(restored) == json_str
