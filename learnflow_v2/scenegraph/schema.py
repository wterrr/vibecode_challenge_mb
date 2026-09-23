"""Strict, semantic Pydantic models for SceneGraph V2.

SceneGraph represents semantic intent, structural topology, and relational meaning.
It contains strictly zero pixel geometry, coordinates, or render commands.
"""

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from learnflow_v2.core.errors import (
    SceneGraphDuplicateGroupIdError,
    SceneGraphDuplicateNodeIdError,
    SceneGraphDuplicateRelationIdError,
    SceneGraphIncompleteSemanticIdentityError,
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

V2_SCENEGRAPH_SCHEMA_VERSION = "2.1"


class LayoutHint(BaseModel):
    """Semantic spatial preferences for layout solver. Contains no pixel values."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    preferred_region: PreferredRegion | None = Field(
        default=None,
        description="Abstract region preference (e.g. CENTER, LEFT, TOP)",
    )
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Relative visual weight and visual hierarchy [0.0, 1.0]",
    )
    keep_near: list[str] = Field(
        default_factory=list,
        description="Node IDs that should be kept in spatial proximity",
    )
    keep_apart: list[str] = Field(
        default_factory=list,
        description="Node IDs that should be kept visually distinct or separated",
    )
    preferred_order: int | None = Field(
        default=None,
        ge=0,
        description="Logical sequence ordering index",
    )


class SceneNode(BaseModel):
    """Semantic visual primitive node in the scene."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1, description="Scene-local unique node identifier")
    kind: NodeKind = Field(..., description="Finite visual primitive category")
    label: str | None = Field(default=None, description="Primary human-readable label or text")
    content: str | None = Field(default=None, description="Supplementary or formula content")
    concept_ref: str | None = Field(
        default=None,
        description="Reference to lesson-wide ConceptRegistry concept_id",
    )
    semantic_key: str | None = Field(
        default=None,
        description="Canonical semantic key agreeing with ConceptRegistry",
    )
    semantic_role: str | None = Field(
        default=None,
        description="Domain-specific semantic role, e.g. PRIMARY_ACTOR, LOSS_FUNCTION",
    )
    layout_hint: LayoutHint | None = Field(
        default=None,
        description="Semantic layout preferences",
    )
    style_refs: list[str] = Field(
        default_factory=list,
        description="Symbolic style tokens, e.g. ['concept.primary', 'emphasis.high']",
    )

    @model_validator(mode="after")
    def validate_semantic_identity(self) -> "SceneNode":
        """Enforce concept_ref and semantic_key are either both defined or both None."""
        has_ref = self.concept_ref is not None
        has_key = self.semantic_key is not None
        if has_ref != has_key:
            raise SceneGraphIncompleteSemanticIdentityError(
                f"SceneNode '{self.id}' must specify both concept_ref and semantic_key or neither. "
                f"Got concept_ref={self.concept_ref!r}, semantic_key={self.semantic_key!r}"
            )
        return self


class SceneRelation(BaseModel):
    """Typed semantic relationship connecting two nodes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1, description="Scene-local unique relation identifier")
    source: str = Field(..., min_length=1, description="Source node ID")
    target: str = Field(..., min_length=1, description="Target node ID")
    kind: RelationKind = Field(..., description="Semantic relation taxonomy kind")
    label: str | None = Field(default=None, description="Optional relation or edge label")
    source_port: PortHint = Field(
        default=PortHint.AUTO,
        description="Abstract port location on source",
    )
    target_port: PortHint = Field(
        default=PortHint.AUTO,
        description="Abstract port location on target",
    )
    style_refs: list[str] = Field(
        default_factory=list,
        description="Symbolic style tokens",
    )


class SceneGroup(BaseModel):
    """Semantic grouping of nodes within the scene."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1, description="Scene-local unique group identifier")
    member_ids: list[str] = Field(
        ...,
        min_length=1,
        description="Node IDs contained in this semantic group",
    )
    label: str | None = Field(default=None, description="Optional group label or title")
    semantic_role: str | None = Field(default=None, description="Semantic role of the container")
    layout_hint: LayoutHint | None = Field(default=None, description="Group spatial preferences")


class LayoutIntentSpec(BaseModel):
    """Overall scene layout intention and flow direction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: LayoutIntent = Field(default=LayoutIntent.CONCEPT_CARD)
    reading_direction: ReadingDirection = Field(default=ReadingDirection.LEFT_TO_RIGHT)


class SceneGraph(BaseModel):
    """Complete semantic scene intermediate representation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = Field(
        default=V2_SCENEGRAPH_SCHEMA_VERSION,  # type: ignore[arg-type]
        description="V2 schema version (2.1)",
    )
    scene_id: str = Field(..., min_length=1, description="Unique scene identifier")
    purpose: ScenePurpose = Field(default=ScenePurpose.EXPLAIN, description="Pedagogical goal")
    concept: str | None = Field(default=None, description="Primary concept label of the scene")
    nodes: list[SceneNode] = Field(default_factory=list, description="Scene semantic nodes")
    relations: list[SceneRelation] = Field(default_factory=list, description="Semantic relations")
    groups: list[SceneGroup] = Field(default_factory=list, description="Semantic groups")
    layout_intent: LayoutIntentSpec = Field(
        default_factory=lambda: LayoutIntentSpec(type=LayoutIntent.CONCEPT_CARD),
        description="High-level visual layout strategy",
    )
    style_refs: list[str] = Field(
        default_factory=list,
        description="Scene-level symbolic style tokens",
    )

    @model_validator(mode="after")
    def validate_local_graph(self) -> "SceneGraph":
        """Enforce strict local topology and reference integrity."""
        # 1. Duplicate node ID check
        node_ids: set[str] = set()
        for node in self.nodes:
            if node.id in node_ids:
                raise SceneGraphDuplicateNodeIdError(
                    f"Duplicate node ID '{node.id}' in scene '{self.scene_id}'"
                )
            node_ids.add(node.id)

        # 2. Duplicate relation ID check
        relation_ids: set[str] = set()
        for rel in self.relations:
            if rel.id in relation_ids:
                raise SceneGraphDuplicateRelationIdError(
                    f"Duplicate relation ID '{rel.id}' in scene '{self.scene_id}'"
                )
            relation_ids.add(rel.id)

            # Check relation endpoint integrity
            if rel.source not in node_ids:
                raise SceneGraphInvalidRelationRefError(
                    f"Relation '{rel.id}' references unknown source node '{rel.source}'"
                )
            if rel.target not in node_ids:
                raise SceneGraphInvalidRelationRefError(
                    f"Relation '{rel.id}' references unknown target node '{rel.target}'"
                )

        # 3. Duplicate group ID and member integrity check
        group_ids: set[str] = set()
        for group in self.groups:
            if group.id in group_ids:
                raise SceneGraphDuplicateGroupIdError(
                    f"Duplicate group ID '{group.id}' in scene '{self.scene_id}'"
                )
            group_ids.add(group.id)

            seen_members: set[str] = set()
            for member_id in group.member_ids:
                if member_id in seen_members:
                    raise SceneGraphInvalidGroupRefError(
                        f"Group '{group.id}' contains duplicate member '{member_id}'"
                    )
                seen_members.add(member_id)

                if member_id not in node_ids:
                    raise SceneGraphInvalidGroupRefError(
                        f"Group '{group.id}' references unknown member node '{member_id}'"
                    )

        # 4. Validate layout hint node references in nodes and groups
        for node in self.nodes:
            if node.layout_hint:
                for near_id in node.layout_hint.keep_near:
                    if near_id not in node_ids:
                        raise SceneGraphInvalidLayoutRefError(
                            f"Node '{node.id}' layout_hint keep_near references unknown node '{near_id}'"
                        )
                for apart_id in node.layout_hint.keep_apart:
                    if apart_id not in node_ids:
                        raise SceneGraphInvalidLayoutRefError(
                            f"Node '{node.id}' layout_hint keep_apart references unknown node '{apart_id}'"
                        )

        for group in self.groups:
            if group.layout_hint:
                for near_id in group.layout_hint.keep_near:
                    if near_id not in node_ids:
                        raise SceneGraphInvalidLayoutRefError(
                            f"Group '{group.id}' layout_hint keep_near references unknown node '{near_id}'"
                        )
                for apart_id in group.layout_hint.keep_apart:
                    if apart_id not in node_ids:
                        raise SceneGraphInvalidLayoutRefError(
                            f"Group '{group.id}' layout_hint keep_apart references unknown node '{apart_id}'"
                        )

        return self
