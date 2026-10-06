"""Typed outputs for LearnFlow Fact Verification."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, computed_field, field_validator, model_validator

from agent_contracts import AgentContractError, ContractModel
from agent_contracts.base import normalize_id, require_unique


def _tupleize(value: Any):
    return tuple(value) if isinstance(value, list) else value


class VerificationIssue(str, Enum):
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTION = "CONTRADICTION"
    SEMANTIC_UNCERTAINTY = "SEMANTIC_UNCERTAINTY"


class SemanticVerdict(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNCERTAIN = "UNCERTAIN"


class SemanticClaimReview(ContractModel):
    claim_id: str
    verdict: SemanticVerdict
    rationale: str = Field(..., min_length=1)
    cited_source_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("cited_source_ids", mode="before")
    @classmethod
    def _tuple_sources(cls, value: Any):
        return _tupleize(value)

    @field_validator("claim_id")
    @classmethod
    def _claim_id(cls, value: str) -> str:
        return normalize_id(value, field_name="claim_id")

    @field_validator("rationale")
    @classmethod
    def _rationale(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise AgentContractError("rationale cannot be blank")
        return value

    @field_validator("cited_source_ids")
    @classmethod
    def _source_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(normalize_id(v, field_name="source_id") for v in value)
        require_unique(normalized, label="SemanticClaimReview cited_source_ids")
        return normalized


class SemanticFactReview(ContractModel):
    review_id: str
    research_pack_id: str
    evidence_graph_id: str
    claims: tuple[SemanticClaimReview, ...] = Field(..., min_length=1)

    @field_validator("claims", mode="before")
    @classmethod
    def _claims_tuple(cls, value: Any):
        return _tupleize(value)

    @field_validator("review_id", "research_pack_id", "evidence_graph_id")
    @classmethod
    def _ids(cls, value: str, info) -> str:
        return normalize_id(value, field_name=info.field_name)

    @model_validator(mode="after")
    def _unique_claims(self) -> "SemanticFactReview":
        require_unique(
            [item.claim_id for item in self.claims],
            label="SemanticFactReview claim_ids",
        )
        return self


class ClaimVerification(ContractModel):
    claim_id: str
    issues: tuple[VerificationIssue, ...] = Field(default_factory=tuple)
    grounded_source_ids: tuple[str, ...] = Field(default_factory=tuple)
    support_edge_ids: tuple[str, ...] = Field(default_factory=tuple)
    contradiction_edge_ids: tuple[str, ...] = Field(default_factory=tuple)
    semantic_verdict: SemanticVerdict | None = None

    @field_validator(
        "issues",
        "grounded_source_ids",
        "support_edge_ids",
        "contradiction_edge_ids",
        mode="before",
    )
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)

    @field_validator("claim_id")
    @classmethod
    def _claim_id(cls, value: str) -> str:
        return normalize_id(value, field_name="claim_id")

    @field_validator("grounded_source_ids", "support_edge_ids", "contradiction_edge_ids")
    @classmethod
    def _ids(cls, value: tuple[str, ...], info) -> tuple[str, ...]:
        normalized = tuple(normalize_id(v, field_name=info.field_name) for v in value)
        require_unique(normalized, label=info.field_name)
        return normalized

    @field_validator("issues")
    @classmethod
    def _issues(cls, value: tuple[VerificationIssue, ...]) -> tuple[VerificationIssue, ...]:
        require_unique([item.value for item in value], label="ClaimVerification issues")
        return value

    @computed_field
    @property
    def eligible_for_narration(self) -> bool:
        return not self.issues


class FactVerificationReport(ContractModel):
    report_id: str
    research_pack_id: str
    evidence_graph_id: str
    claims: tuple[ClaimVerification, ...] = Field(..., min_length=1)

    @field_validator("claims", mode="before")
    @classmethod
    def _claims_tuple(cls, value: Any):
        return _tupleize(value)

    @field_validator("report_id", "research_pack_id", "evidence_graph_id")
    @classmethod
    def _ids(cls, value: str, info) -> str:
        return normalize_id(value, field_name=info.field_name)

    @model_validator(mode="after")
    def _integrity(self) -> "FactVerificationReport":
        require_unique(
            [item.claim_id for item in self.claims],
            label="FactVerificationReport claim_ids",
        )
        return self

    @computed_field
    @property
    def approved_claim_ids(self) -> tuple[str, ...]:
        return tuple(item.claim_id for item in self.claims if item.eligible_for_narration)

    @computed_field
    @property
    def blocked_claim_ids(self) -> tuple[str, ...]:
        return tuple(item.claim_id for item in self.claims if not item.eligible_for_narration)

    @computed_field
    @property
    def contradiction_claim_ids(self) -> tuple[str, ...]:
        return tuple(
            item.claim_id
            for item in self.claims
            if VerificationIssue.CONTRADICTION in item.issues
        )
