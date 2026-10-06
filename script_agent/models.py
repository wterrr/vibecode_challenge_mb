"""Validation artifacts for the LearnFlow Script Agent."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, computed_field, field_validator

from agent_contracts import ContractModel
from agent_contracts.base import normalize_id, require_unique


def _tupleize(value: Any):
    return tuple(value) if isinstance(value, list) else value


class ScriptIssue(str, Enum):
    CLAIM_SET_MISMATCH = "CLAIM_SET_MISMATCH"
    OBJECTIVE_NOT_COVERED = "OBJECTIVE_NOT_COVERED"
    FACT_BEARING_SEGMENT_WITHOUT_CLAIM = "FACT_BEARING_SEGMENT_WITHOUT_CLAIM"
    VISUAL_OR_IMPLEMENTATION_DIRECTIVE = "VISUAL_OR_IMPLEMENTATION_DIRECTIVE"


class ScriptValidation(ContractModel):
    script_id: str
    issues: tuple[ScriptIssue, ...] = Field(default_factory=tuple)
    missing_claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    unexpected_claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    uncovered_objective_ids: tuple[str, ...] = Field(default_factory=tuple)
    ungrounded_segment_ids: tuple[str, ...] = Field(default_factory=tuple)
    boundary_violation_segment_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator(
        "issues",
        "missing_claim_ids",
        "unexpected_claim_ids",
        "uncovered_objective_ids",
        "ungrounded_segment_ids",
        "boundary_violation_segment_ids",
        mode="before",
    )
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)

    @field_validator("script_id")
    @classmethod
    def _script_id(cls, value: str) -> str:
        return normalize_id(value, field_name="script_id")

    @field_validator(
        "missing_claim_ids",
        "unexpected_claim_ids",
        "uncovered_objective_ids",
        "ungrounded_segment_ids",
        "boundary_violation_segment_ids",
    )
    @classmethod
    def _ids(cls, value: tuple[str, ...], info) -> tuple[str, ...]:
        normalized = tuple(normalize_id(v, field_name=info.field_name) for v in value)
        require_unique(normalized, label=info.field_name)
        return normalized

    @field_validator("issues")
    @classmethod
    def _issues(cls, value: tuple[ScriptIssue, ...]) -> tuple[ScriptIssue, ...]:
        require_unique([item.value for item in value], label="ScriptValidation issues")
        return value

    @computed_field
    @property
    def ready_for_visual_director(self) -> bool:
        return not self.issues
