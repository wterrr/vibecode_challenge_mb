"""Registry-aware semantic validation for SceneGraph."""

from learnflow_v2.concepts.registry import ConceptRegistry
from learnflow_v2.core.errors import (
    ConceptRegistryUnknownRefError,
    SceneGraphIncompleteSemanticIdentityError,
    SceneGraphSemanticKeyMismatchError,
    SceneGraphUnknownConceptRefError,
)
from learnflow_v2.scenegraph.schema import SceneGraph


def validate_scenegraph_with_registry(
    graph: SceneGraph,
    registry: ConceptRegistry,
) -> None:
    """Validate a SceneGraph against an explicit ConceptRegistry.

    Invariants checked:
    1. A node must either have BOTH concept_ref and semantic_key, or NEITHER.
       Incomplete pair raises SCENEGRAPH_INCOMPLETE_SEMANTIC_IDENTITY.
    2. Every node with concept_ref must reference an existing concept in registry.
       Unknown concept_ref raises SCENEGRAPH_UNKNOWN_CONCEPT_REF.
    3. The node's semantic_key must exactly match the registry concept's canonical_key.
       Mismatch raises SCENEGRAPH_SEMANTIC_KEY_MISMATCH.

    Raises:
        SceneGraphIncompleteSemanticIdentityError: if only one of concept_ref or semantic_key is provided.
        SceneGraphUnknownConceptRefError: if concept_ref does not exist in registry.
        SceneGraphSemanticKeyMismatchError: if semantic_key does not agree with registry.
    """
    for node in graph.nodes:
        has_ref = node.concept_ref is not None
        has_key = node.semantic_key is not None

        if has_ref != has_key:
            raise SceneGraphIncompleteSemanticIdentityError(
                f"Node '{node.id}' in scene '{graph.scene_id}' has incomplete semantic identity: "
                f"concept_ref={node.concept_ref!r}, semantic_key={node.semantic_key!r}. "
                "Nodes must specify both or neither."
            )

        if node.concept_ref is not None:
            # 1. Concept must exist
            try:
                concept_entry = registry.get(node.concept_ref)
            except ConceptRegistryUnknownRefError as err:
                raise SceneGraphUnknownConceptRefError(
                    f"Node '{node.id}' in scene '{graph.scene_id}' references unknown concept '{node.concept_ref}'"
                ) from err

            # 2. Semantic key agreement
            if node.semantic_key != concept_entry.canonical_key:
                raise SceneGraphSemanticKeyMismatchError(
                    f"Node '{node.id}' in scene '{graph.scene_id}' has semantic_key '{node.semantic_key}' "
                    f"which conflicts with canonical_key '{concept_entry.canonical_key}' "
                    f"for concept '{node.concept_ref}'"
                )
