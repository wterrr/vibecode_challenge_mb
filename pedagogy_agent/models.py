"""Validation artifacts for the LearnFlow Pedagogy Agent."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, computed_field, field_validator

from agent_contracts import ContractModel
from agent_contracts.base import normalize_id, require_unique


def _tupleize(value: Any):
    return tuple(value) if isinstance(value, list) else value


class PedagogyIssue(str, Enum):
    BLOCKED_CLAIM_REFERENCE = "BLOCKED_CLAIM_REFERENCE"
    UNKNOWN_CONCEPT = "UNKNOWN_CONCEPT"
    OBJECTIVE_WITHOUT_ASSESSMENT = "OBJECTIVE_WITHOUT_ASSESSMENT"
    MISSING_EXAMPLE = "MISSING_EXAMPLE"


class PedagogyValidation(ContractModel):
    plan_id: str
    issues: tuple[PedagogyIssue, ...] = Field(default_factory=tuple)
    blocked_claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    unknown_concepts: tuple[str, ...] = Field(default_factory=tuple)
    unassessed_objective_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator(
        "issues",
        "blocked_claim_ids",
        "unknown_concepts",
        "unassessed_objective_ids",
        mode="before",
    )
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)

    @field_validator("plan_id")
    @classmethod
    def _plan_id(cls, value: str) -> str:
        return normalize_id(value, field_name="plan_id")

    @field_validator("blocked_claim_ids", "unassessed_objective_ids")
    @classmethod
    def _ids(cls, value: tuple[str, ...], info) -> tuple[str, ...]:
        normalized = tuple(normalize_id(v, field_name=info.field_name) for v in value)
        require_unique(normalized, label=info.field_name)
        return normalized

    @field_validator("unknown_concepts")
    @classmethod
    def _concepts(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value if item.strip())
        require_unique(normalized, label="unknown_concepts")
        return normalized

    @field_validator("issues")
    @classmethod
    def _issues(cls, value: tuple[PedagogyIssue, ...]) -> tuple[PedagogyIssue, ...]:
        require_unique([item.value for item in value], label="PedagogyValidation issues")
        return value

    @computed_field
    @property
    def ready_for_script(self) -> bool:
        return not self.issues
