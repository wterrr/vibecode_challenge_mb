"""Versioned schema models for ConceptRegistry."""

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

from learnflow_v2 import V2_SCHEMA_VERSION
from learnflow_v2.core.jsonsafe import validate_json_safe


class SemanticType(str, Enum):
    """Finite taxonomic types for educational concepts."""

    CONCEPT = "CONCEPT"
    PROCESS = "PROCESS"
    ENTITY = "ENTITY"
    RELATION = "RELATION"
    METRIC = "METRIC"
    PROPERTY = "PROPERTY"


class ConceptEntry(BaseModel):
    """Canonical concept representation within a lesson."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    concept_id: str = Field(..., min_length=1, description="Deterministic unique concept ID, e.g. c_loss_a1b2c3")
    canonical_key: str = Field(..., min_length=1, description="Canonical semantic key, e.g. concept:loss")
    label: str = Field(..., min_length=1, description="Human-readable concept display label")
    aliases: list[str] = Field(default_factory=list, description="Explicit alternate terms/aliases")
    semantic_type: SemanticType = Field(default=SemanticType.CONCEPT, description="Taxonomic semantic category")
    provenance: str = Field(default="lesson", description="Source or generation provenance")
    domain_metadata: dict[str, Any] = Field(default_factory=dict, description="Bounded JSON-safe domain metadata")

    @field_validator("domain_metadata")
    @classmethod
    def validate_domain_metadata(cls, v: dict[str, Any]) -> dict[str, Any]:
        validate_json_safe(v, path="domain_metadata")
        return v


class ConceptRegistrySchema(BaseModel):
    """Serializable, versioned container for all concept entries in a lesson."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = Field(
        default=V2_SCHEMA_VERSION,  # type: ignore[arg-type]
        description="V2 schema version (2.1)",
    )
    concepts: list[ConceptEntry] = Field(default_factory=list, description="List of canonical concepts")
