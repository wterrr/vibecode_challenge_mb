"""Versioned schema models for ConceptRegistry."""

import math
from enum import Enum
from typing import Any, Literal, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator

from learnflow_v2 import V2_SCHEMA_VERSION

# Bounded recursive JSON-compatible type
JSONSafeValue = Union[
    str,
    int,
    float,
    bool,
    None,
    list["JSONSafeValue"],
    dict[str, "JSONSafeValue"],
]


def _check_json_safe(val: Any) -> None:
    """Validate that val is strictly JSON-safe (finite numbers, strings, bool, None, lists, dicts).
    Rejects: tuple, set, bytes, Path, callable, custom object, NaN, +Infinity, -Infinity.
    """
    if val is None or isinstance(val, (str, bool)):
        return
    if isinstance(val, float):
        if not math.isfinite(val):
            raise ValueError(f"Non-finite float value '{val}' is not allowed in domain_metadata")
        return
    if isinstance(val, int):
        return
    if isinstance(val, list):
        for item in val:
            _check_json_safe(item)
        return
    if isinstance(val, dict):
        for k, v in val.items():
            if not isinstance(k, str):
                raise ValueError(f"Domain metadata key must be a string, got {type(k).__name__}")
            _check_json_safe(v)
        return
    raise ValueError(
        f"Value of type '{type(val).__name__}' is not JSON-safe for domain_metadata. "
        "Only str, finite int, finite float, bool, None, and nested lists/dicts are allowed. "
        "Tuples, sets, and non-finite floats are strictly forbidden."
    )


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
        _check_json_safe(v)
        return v


class ConceptRegistrySchema(BaseModel):
    """Serializable, versioned container for all concept entries in a lesson."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = Field(
        default=V2_SCHEMA_VERSION,  # type: ignore[arg-type]
        description="V2 schema version (2.1)",
    )
    concepts: list[ConceptEntry] = Field(default_factory=list, description="List of canonical concepts")
