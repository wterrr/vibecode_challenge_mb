"""Typed contracts specific to LearnFlow research orchestration."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, field_validator, model_validator

from agent_contracts import (
    AgentContractError,
    ContractModel,
    EvidenceEdge,
    EvidenceGraph,
    ResearchClaim,
    ResearchExample,
    ResearchMisconception,
    ResearchPack,
    SourceRecord,
)

MAX_SPECIALIST_RESEARCHERS = 3
MAX_DELEGATION_DEPTH = 2


def _tupleize(value: Any):
    return tuple(value) if isinstance(value, list) else value


class ResearchRole(str, Enum):
    CONCEPT = "CONCEPT_RESEARCHER"
    EVIDENCE = "EVIDENCE_RESEARCHER"
    MISCONCEPTION = "MISCONCEPTION_RESEARCHER"


class ConceptResearchFindings(ContractModel):
    concepts: tuple[str, ...] = Field(..., min_length=1)
    open_questions: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("concepts", "open_questions", mode="before")
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)

    @field_validator("concepts", "open_questions")
    @classmethod
    def _clean_text(cls, value: tuple[str, ...], info) -> tuple[str, ...]:
        cleaned = tuple(item.strip() for item in value if item.strip())
        if len(cleaned) != len(set(cleaned)):
            raise AgentContractError(f"{info.field_name} must be unique")
        return cleaned


class EvidenceResearchFindings(ContractModel):
    sources: tuple[SourceRecord, ...] = Field(..., min_length=1)
    claims: tuple[ResearchClaim, ...] = Field(..., min_length=1)
    evidence_edges: tuple[EvidenceEdge, ...] = Field(..., min_length=1)

    @field_validator("sources", "claims", "evidence_edges", mode="before")
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)

    @model_validator(mode="after")
    def _reference_integrity(self) -> "EvidenceResearchFindings":
        source_ids = [item.source_id for item in self.sources]
        claim_ids = [item.claim_id for item in self.claims]
        if len(source_ids) != len(set(source_ids)):
            raise AgentContractError("EvidenceResearchFindings source_ids must be unique")
        if len(claim_ids) != len(set(claim_ids)):
            raise AgentContractError("EvidenceResearchFindings claim_ids must be unique")
        source_set = set(source_ids)
        claim_set = set(claim_ids)
        for claim in self.claims:
            unknown = sorted(set(claim.source_ids) - source_set)
            if unknown:
                raise AgentContractError(
                    f"claim {claim.claim_id!r} references unknown sources {unknown!r}"
                )
        for edge in self.evidence_edges:
            if edge.to_claim_id not in claim_set:
                raise AgentContractError(
                    f"evidence edge {edge.edge_id!r} targets unknown claim {edge.to_claim_id!r}"
                )
            if edge.from_kind.value == "SOURCE" and edge.from_id not in source_set:
                raise AgentContractError(
                    f"evidence edge {edge.edge_id!r} references unknown source {edge.from_id!r}"
                )
            if edge.from_kind.value == "CLAIM" and edge.from_id not in claim_set:
                raise AgentContractError(
                    f"evidence edge {edge.edge_id!r} references unknown claim {edge.from_id!r}"
                )
        return self


class MisconceptionResearchFindings(ContractModel):
    misconceptions: tuple[ResearchMisconception, ...] = Field(default_factory=tuple)
    examples: tuple[ResearchExample, ...] = Field(default_factory=tuple)

    @field_validator("misconceptions", "examples", mode="before")
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)


class SpecialistTask(ContractModel):
    role: ResearchRole
    goal: str = Field(..., min_length=1)
    context: str = Field(..., min_length=1)
    output_schema: dict[str, Any]

    @field_validator("goal", "context")
    @classmethod
    def _text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise AgentContractError("specialist task text cannot be blank")
        return value


class ResearchOrchestrationPlan(ContractModel):
    plan_id: str
    brief_id: str
    max_delegation_depth: int = MAX_DELEGATION_DEPTH
    max_specialists: int = MAX_SPECIALIST_RESEARCHERS
    specialist_tasks: tuple[SpecialistTask, ...] = Field(..., min_length=1)

    @field_validator("specialist_tasks", mode="before")
    @classmethod
    def _tuple_tasks(cls, value: Any):
        return _tupleize(value)

    @model_validator(mode="after")
    def _bounds(self) -> "ResearchOrchestrationPlan":
        if self.max_delegation_depth != MAX_DELEGATION_DEPTH:
            raise AgentContractError(
                f"research delegation depth must be exactly {MAX_DELEGATION_DEPTH}"
            )
        if self.max_specialists != MAX_SPECIALIST_RESEARCHERS:
            raise AgentContractError(
                f"max_specialists must be exactly {MAX_SPECIALIST_RESEARCHERS}"
            )
        if len(self.specialist_tasks) > self.max_specialists:
            raise AgentContractError("research plan exceeds specialist limit")
        roles = [task.role for task in self.specialist_tasks]
        if len(roles) != len(set(roles)):
            raise AgentContractError("research specialist roles must be unique")
        return self


class ResearchOrchestrationResult(ContractModel):
    research_pack: ResearchPack
    evidence_graph: EvidenceGraph
    specialist_roles: tuple[ResearchRole, ...]
    delegation_depth: int = MAX_DELEGATION_DEPTH

    @field_validator("specialist_roles", mode="before")
    @classmethod
    def _tuple_roles(cls, value: Any):
        return _tupleize(value)

    @model_validator(mode="after")
    def _integrity(self) -> "ResearchOrchestrationResult":
        if self.delegation_depth != MAX_DELEGATION_DEPTH:
            raise AgentContractError("unexpected delegation_depth")
        if len(self.specialist_roles) > MAX_SPECIALIST_RESEARCHERS:
            raise AgentContractError("too many specialist roles in result")
        if len(self.specialist_roles) != len(set(self.specialist_roles)):
            raise AgentContractError("specialist_roles must be unique")
        self.evidence_graph.validate_against_research_pack(self.research_pack)
        return self
