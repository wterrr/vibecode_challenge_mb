"""Tests for registry-aware SceneGraph validation and cross-scene identity."""

import pytest

from learnflow_v2.concepts.registry import ConceptRegistry
from learnflow_v2.concepts.schema import ConceptEntry, SemanticType
from learnflow_v2.core.errors import (
    SceneGraphIncompleteSemanticIdentityError,
    SceneGraphSemanticKeyMismatchError,
    SceneGraphUnknownConceptRefError,
)
from learnflow_v2.scenegraph.enums import NodeKind
from learnflow_v2.scenegraph.schema import SceneGraph, SceneNode
from learnflow_v2.scenegraph.validation import validate_scenegraph_with_registry


@pytest.fixture
def sample_registry() -> ConceptRegistry:
    registry = ConceptRegistry()
    registry.register(
        ConceptEntry(
            concept_id="c_loss",
            canonical_key="concept:loss",
            label="Loss",
            aliases=["loss function", "cost function"],
            semantic_type=SemanticType.CONCEPT,
        )
    )
    registry.register(
        ConceptEntry(
            concept_id="c_grad",
            canonical_key="concept:gradient",
            label="Gradient",
            aliases=["grad"],
            semantic_type=SemanticType.PROCESS,
        )
    )
    return registry


def test_valid_concept_ref_passes(sample_registry: ConceptRegistry):
    graph = SceneGraph(
        scene_id="scene_001",
        nodes=[
            SceneNode(
                id="node_loss",
                kind=NodeKind.CONCEPT,
                concept_ref="c_loss",
                semantic_key="concept:loss",
            )
        ],
    )
    # Must not raise
    validate_scenegraph_with_registry(graph, sample_registry)


def test_unknown_concept_ref_raises(sample_registry: ConceptRegistry):
    graph = SceneGraph(
        scene_id="scene_bad_ref",
        nodes=[
            SceneNode(
                id="node_unknown",
                kind=NodeKind.CONCEPT,
                concept_ref="c_nonexistent_concept",
                semantic_key="concept:nonexistent",
            )
        ],
    )
    with pytest.raises(SceneGraphUnknownConceptRefError) as exc_info:
        validate_scenegraph_with_registry(graph, sample_registry)
    assert exc_info.value.code == "SCENEGRAPH_UNKNOWN_CONCEPT_REF"


def test_semantic_key_mismatch_raises(sample_registry: ConceptRegistry):
    graph = SceneGraph(
        scene_id="scene_mismatch",
        nodes=[
            SceneNode(
                id="node_loss",
                kind=NodeKind.CONCEPT,
                concept_ref="c_loss",
                semantic_key="concept:wrong_semantic_key",
            )
        ],
    )
    with pytest.raises(SceneGraphSemanticKeyMismatchError) as exc_info:
        validate_scenegraph_with_registry(graph, sample_registry)
    assert exc_info.value.code == "SCENEGRAPH_SEMANTIC_KEY_MISMATCH"


def test_cross_scene_same_concept_identity(sample_registry: ConceptRegistry):
    """MANDATORY ACCEPTANCE TEST:

    Scene 1 has node id = loss_left, concept_ref = c_loss
    Scene 2 has node id = loss_center, concept_ref = c_loss
    Validate both against one ConceptRegistry.
    Assert:
    - scene-local IDs differ
    - concept identity is identical
    - canonical semantic key is identical
    """
    scene_1 = SceneGraph(
        scene_id="scene_001",
        nodes=[
            SceneNode(
                id="loss_left",
                kind=NodeKind.CONCEPT,
                label="Loss Function (Left)",
                concept_ref="c_loss",
                semantic_key="concept:loss",
            )
        ],
    )

    scene_2 = SceneGraph(
        scene_id="scene_002",
        nodes=[
            SceneNode(
                id="loss_center",
                kind=NodeKind.CONCEPT,
                label="Loss Function (Center)",
                concept_ref="c_loss",
                semantic_key="concept:loss",
            )
        ],
    )

    # Validate both scenes against the same registry
    validate_scenegraph_with_registry(scene_1, sample_registry)
    validate_scenegraph_with_registry(scene_2, sample_registry)

    # Assert local node IDs differ
    assert scene_1.nodes[0].id == "loss_left"
    assert scene_2.nodes[0].id == "loss_center"
    assert scene_1.nodes[0].id != scene_2.nodes[0].id

    # Assert lesson-wide concept identities are identical
    assert scene_1.nodes[0].concept_ref == "c_loss"
    assert scene_2.nodes[0].concept_ref == "c_loss"
    assert scene_1.nodes[0].concept_ref == scene_2.nodes[0].concept_ref

    # Assert canonical semantic keys are identical
    assert scene_1.nodes[0].semantic_key == "concept:loss"
    assert scene_2.nodes[0].semantic_key == "concept:loss"
    assert scene_1.nodes[0].semantic_key == scene_2.nodes[0].semantic_key

    # Assert resolution against registry returns identical canonical concept entry
    resolved_1 = sample_registry.get(scene_1.nodes[0].concept_ref)
    resolved_2 = sample_registry.get(scene_2.nodes[0].concept_ref)
    assert resolved_1 == resolved_2


def test_semantic_identity_contract(sample_registry: ConceptRegistry):
    # 1. semantic_key only without concept_ref -> rejected
    with pytest.raises(SceneGraphIncompleteSemanticIdentityError) as exc_info:
        SceneNode(id="n_bad_1", kind=NodeKind.CONCEPT, semantic_key="concept:orphan")
    assert exc_info.value.code == "SCENEGRAPH_INCOMPLETE_SEMANTIC_IDENTITY"

    # 2. concept_ref only without semantic_key -> rejected
    with pytest.raises(SceneGraphIncompleteSemanticIdentityError) as exc_info:
        SceneNode(id="n_bad_2", kind=NodeKind.CONCEPT, concept_ref="c_loss")
    assert exc_info.value.code == "SCENEGRAPH_INCOMPLETE_SEMANTIC_IDENTITY"

    # 3. Neither set -> valid
    node_neither = SceneNode(id="n_plain", kind=NodeKind.TEXT, label="Plain text")
    assert node_neither.concept_ref is None
    assert node_neither.semantic_key is None
    sg_plain = SceneGraph(scene_id="s_plain", nodes=[node_neither])
    validate_scenegraph_with_registry(sg_plain, sample_registry)

    # 4. Valid pair -> PASS
    node_valid = SceneNode(
        id="n_ok",
        kind=NodeKind.CONCEPT,
        concept_ref="c_loss",
        semantic_key="concept:loss",
    )
    sg_valid = SceneGraph(scene_id="s_ok", nodes=[node_valid])
    validate_scenegraph_with_registry(sg_valid, sample_registry)

    # 5. Unknown concept_ref + semantic_key -> SCENEGRAPH_UNKNOWN_CONCEPT_REF
    node_unknown = SceneNode(
        id="n_unk",
        kind=NodeKind.CONCEPT,
        concept_ref="c_ghost",
        semantic_key="concept:ghost",
    )
    sg_unknown = SceneGraph(scene_id="s_unk", nodes=[node_unknown])
    with pytest.raises(SceneGraphUnknownConceptRefError) as exc_info:
        validate_scenegraph_with_registry(sg_unknown, sample_registry)
    assert exc_info.value.code == "SCENEGRAPH_UNKNOWN_CONCEPT_REF"

    # 6. Valid concept_ref + wrong semantic_key -> SCENEGRAPH_SEMANTIC_KEY_MISMATCH
    node_mismatch = SceneNode(
        id="n_mis",
        kind=NodeKind.CONCEPT,
        concept_ref="c_loss",
        semantic_key="concept:wrong_key",
    )
    sg_mismatch = SceneGraph(scene_id="s_mis", nodes=[node_mismatch])
    with pytest.raises(SceneGraphSemanticKeyMismatchError) as exc_info:
        validate_scenegraph_with_registry(sg_mismatch, sample_registry)
    assert exc_info.value.code == "SCENEGRAPH_SEMANTIC_KEY_MISMATCH"
