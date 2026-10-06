"""Research and evidence contracts for the Hermes control plane."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, field_validator, model_validator

from .base import (
    AgentContractError,
    ContractModel,
    normalize_id,
    normalize_text,
    require_unique,
)


def _tupleize(value: Any):
    return tuple(value) if isinstance(value, list) else value


class SourceType(str, Enum):
    WEB = "WEB"
    PAPER = "PAPER"
    BOOK = "BOOK"
    DATASET = "DATASET"
    DOCUMENT = "DOCUMENT"
    OTHER = "OTHER"


class SourceRecord(ContractModel):
    source_id: str = Field(..., min_length=1)
    source_type: SourceType = SourceType.WEB
    title: str = Field(..., min_length=1)
    locator: str = Field(
        ...,
        min_length=1,
        description="Stable source locator such as URL, DOI, document URI, or dataset identifier.",
    )
    publisher: str | None = None
    authors: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("authors", mode="before")
    @classmethod
    def _authors_tuple(cls, value: Any):
        return _tupleize(value)

    @field_validator("source_id")
    @classmethod
    def _source_id(cls, value: str) -> str:
        return normalize_id(value, field_name="source_id")

    @field_validator("title", "locator")
    @classmethod
    def _required_text(cls, value: str, info) -> str:
        return normalize_text(value, field_name=info.field_name)

    @field_validator("publisher")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        return None if value is None else normalize_text(value, field_name="publisher")

    @field_validator("authors")
    @classmethod
    def _author_text(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(normalize_text(v, field_name="author") for v in value)
        require_unique(normalized, label="authors")
        return normalized


class ResearchClaim(ContractModel):
    claim_id: str = Field(..., min_length=1)
    statement: str = Field(..., min_length=1)
    source_ids: tuple[str, ...] = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    concept_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("source_ids", "concept_ids", mode="before")
    @classmethod
    def _tuple_fields(cls, value: Any):
        return _tupleize(value)

    @field_validator("claim_id")
    @classmethod
    def _claim_id(cls, value: str) -> str:
        return normalize_id(value, field_name="claim_id")

    @field_validator("statement")
    @classmethod
    def _statement(cls, value: str) -> str:
        return normalize_text(value, field_name="statement")

    @field_validator("source_ids", "concept_ids")
    @classmethod
    def _id_tuples(cls, value: tuple[str, ...], info) -> tuple[str, ...]:
        normalized = tuple(normalize_id(v, field_name=info.field_name) for v in value)
        require_unique(normalized, label=info.field_name)
        return normalized


class ResearchExample(ContractModel):
    example_id: str
    description: str
    claim_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("claim_ids", mode="before")
    @classmethod
    def _tuple_claims(cls, value: Any):
        return _tupleize(value)

    @field_validator("example_id")
    @classmethod
    def _id(cls, value: str) -> str:
        return normalize_id(value, field_name="example_id")

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        return normalize_text(value, field_name="description")

    @field_validator("claim_ids")
    @classmethod
    def _claims(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(normalize_id(v, field_name="claim_id") for v in value)
        require_unique(normalized, label="example claim_ids")
        return normalized


class ResearchMisconception(ContractModel):
    misconception_id: str
    statement: str
    correction: str
    claim_ids: tuple[str, ...] = Field(..., min_length=1)

    @field_validator("claim_ids", mode="before")
    @classmethod
    def _tuple_claims(cls, value: Any):
        return _tupleize(value)

    @field_validator("misconception_id")
    @classmethod
    def _id(cls, value: str) -> str:
        return normalize_id(value, field_name="misconception_id")

    @field_validator("statement", "correction")
    @classmethod
    def _text(cls, value: str, info) -> str:
        return normalize_text(value, field_name=info.field_name)

    @field_validator("claim_ids")
    @classmethod
    def _claims(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(normalize_id(v, field_name="claim_id") for v in value)
        require_unique(normalized, label="misconception claim_ids")
        return normalized


class ResearchPack(ContractModel):
    pack_id: str
    topic: str
    concepts: tuple[str, ...] = Field(default_factory=tuple)
    sources: tuple[SourceRecord, ...] = Field(default_factory=tuple)
    claims: tuple[ResearchClaim, ...] = Field(default_factory=tuple)
    misconceptions: tuple[ResearchMisconception, ...] = Field(default_factory=tuple)
    examples: tuple[ResearchExample, ...] = Field(default_factory=tuple)
    open_questions: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator(
        "concepts", "sources", "claims", "misconceptions", "examples", "open_questions",
        mode="before",
    )
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)

    @field_validator("pack_id")
    @classmethod
    def _pack_id(cls, value: str) -> str:
        return normalize_id(value, field_name="pack_id")

    @field_validator("topic")
    @classmethod
    def _topic(cls, value: str) -> str:
        return normalize_text(value, field_name="topic")

    @field_validator("concepts", "open_questions")
    @classmethod
    def _text_tuple(cls, value: tuple[str, ...], info) -> tuple[str, ...]:
        normalized = tuple(normalize_text(v, field_name=info.field_name) for v in value)
        require_unique(normalized, label=info.field_name)
        return normalized

    @model_validator(mode="after")
    def _references(self) -> "ResearchPack":
        source_ids = [item.source_id for item in self.sources]
        claim_ids = [item.claim_id for item in self.claims]
        example_ids = [item.example_id for item in self.examples]
        misconception_ids = [item.misconception_id for item in self.misconceptions]
        require_unique(source_ids, label="ResearchPack source_ids")
        require_unique(claim_ids, label="ResearchPack claim_ids")
        require_unique(example_ids, label="ResearchPack example_ids")
        require_unique(misconception_ids, label="ResearchPack misconception_ids")

        source_set = set(source_ids)
        claim_set = set(claim_ids)
        for claim in self.claims:
            unknown = sorted(set(claim.source_ids) - source_set)
            if unknown:
                raise AgentContractError(
                    f"claim {claim.claim_id!r} references unknown sources {unknown!r}"
                )
        for item in (*self.examples, *self.misconceptions):
            unknown = sorted(set(item.claim_ids) - claim_set)
            if unknown:
                raise AgentContractError(
                    f"research item references unknown claims {unknown!r}"
                )
        return self


class EvidenceRelation(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    DERIVES = "DERIVES"


class EvidenceNodeKind(str, Enum):
    SOURCE = "SOURCE"
    CLAIM = "CLAIM"


class EvidenceEdge(ContractModel):
    edge_id: str
    from_kind: EvidenceNodeKind
    from_id: str
    to_claim_id: str
    relation: EvidenceRelation

    @field_validator("edge_id", "from_id", "to_claim_id")
    @classmethod
    def _ids(cls, value: str, info) -> str:
        return normalize_id(value, field_name=info.field_name)

    @model_validator(mode="after")
    def _self_edge(self) -> "EvidenceEdge":
        if self.from_kind == EvidenceNodeKind.CLAIM and self.from_id == self.to_claim_id:
            raise AgentContractError("EvidenceGraph cannot contain a claim self-edge")
        return self


class EvidenceGraph(ContractModel):
    graph_id: str
    research_pack_id: str
    source_ids: tuple[str, ...] = Field(default_factory=tuple)
    claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    edges: tuple[EvidenceEdge, ...] = Field(default_factory=tuple)

    @field_validator("source_ids", "claim_ids", "edges", mode="before")
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)

    @field_validator("graph_id", "research_pack_id")
    @classmethod
    def _ids(cls, value: str, info) -> str:
        return normalize_id(value, field_name=info.field_name)

    @field_validator("source_ids", "claim_ids")
    @classmethod
    def _id_tuples(cls, value: tuple[str, ...], info) -> tuple[str, ...]:
        normalized = tuple(normalize_id(v, field_name=info.field_name) for v in value)
        require_unique(normalized, label=info.field_name)
        return normalized

    @model_validator(mode="after")
    def _edge_integrity(self) -> "EvidenceGraph":
        require_unique([edge.edge_id for edge in self.edges], label="EvidenceGraph edge_ids")
        source_set = set(self.source_ids)
        claim_set = set(self.claim_ids)
        for edge in self.edges:
            if edge.to_claim_id not in claim_set:
                raise AgentContractError(
                    f"edge {edge.edge_id!r} targets unknown claim {edge.to_claim_id!r}"
                )
            allowed = source_set if edge.from_kind == EvidenceNodeKind.SOURCE else claim_set
            if edge.from_id not in allowed:
                raise AgentContractError(
                    f"edge {edge.edge_id!r} references unknown {edge.from_kind.value.lower()} "
                    f"{edge.from_id!r}"
                )
        return self

    def validate_against_research_pack(self, pack: ResearchPack) -> None:
        if self.research_pack_id != pack.pack_id:
            raise AgentContractError("EvidenceGraph research_pack_id does not match ResearchPack")
        pack_sources = {item.source_id for item in pack.sources}
        pack_claims = {item.claim_id for item in pack.claims}
        if set(self.source_ids) != pack_sources:
            raise AgentContractError("EvidenceGraph source_ids must exactly match ResearchPack sources")
        if set(self.claim_ids) != pack_claims:
            raise AgentContractError("EvidenceGraph claim_ids must exactly match ResearchPack claims")

        incoming_support: dict[str, int] = {claim_id: 0 for claim_id in self.claim_ids}
        for edge in self.edges:
            if edge.relation in {EvidenceRelation.SUPPORTS, EvidenceRelation.DERIVES}:
                incoming_support[edge.to_claim_id] += 1
        unsupported = sorted(
            claim_id for claim_id, count in incoming_support.items() if count == 0
        )
        if unsupported:
            raise AgentContractError(
                f"EvidenceGraph has claims without supporting/derivation edges: {unsupported!r}"
            )
