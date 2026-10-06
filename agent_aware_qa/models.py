"""Contracts for Agent-Aware QA ownership and repair routing."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, field_validator, model_validator

from agent_contracts import AgentContractError, ContractModel
from learnflow_v2.qa import QualityGateResult
from learnflow_v2.videoqa import VideoCriticResult


def _tupleize(value: Any):
    return tuple(value) if isinstance(value, list) else value


def _clean_ids(value: Any, label: str) -> tuple[str, ...]:
    value = _tupleize(value)
    if not isinstance(value, tuple):
        raise AgentContractError(f"{label} must be a tuple/list")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise AgentContractError(f"{label} must contain non-empty strings")
        normalized.append(item.strip())
    if len(normalized) != len(set(normalized)):
        raise AgentContractError(f"{label} cannot contain duplicates")
    return tuple(sorted(normalized))


class SemanticFindingKind(str, Enum):
    EVIDENCE_UNSUPPORTED = "EVIDENCE_UNSUPPORTED"
    EVIDENCE_CONTRADICTED = "EVIDENCE_CONTRADICTED"
    EVIDENCE_UNCERTAIN = "EVIDENCE_UNCERTAIN"
    NARRATION_FACT_MISMATCH = "NARRATION_FACT_MISMATCH"
    SEMANTIC_VISUAL_MISMATCH = "SEMANTIC_VISUAL_MISMATCH"
    PEDAGOGICAL_STRUCTURE = "PEDAGOGICAL_STRUCTURE"


class RepairOwner(str, Enum):
    RESEARCH_ORCHESTRATION = "RESEARCH_ORCHESTRATION"
    SCRIPT_AGENT = "SCRIPT_AGENT"
    PEDAGOGY_AGENT = "PEDAGOGY_AGENT"
    VISUAL_DIRECTOR = "VISUAL_DIRECTOR"
    CORE_REPAIR = "CORE_REPAIR"


class RepairActionKind(str, Enum):
    RESEARCH_EVIDENCE_REPAIR = "RESEARCH_EVIDENCE_REPAIR"
    SCRIPT_FACT_REWRITE = "SCRIPT_FACT_REWRITE"
    SCRIPT_PACING_REWRITE = "SCRIPT_PACING_REWRITE"
    PEDAGOGY_REPLAN = "PEDAGOGY_REPLAN"
    VISUAL_SEMANTIC_REGENERATION = "VISUAL_SEMANTIC_REGENERATION"
    CORE_DETERMINISTIC_REPAIR = "CORE_DETERMINISTIC_REPAIR"
    CORE_SELECTIVE_REPAIR = "CORE_SELECTIVE_REPAIR"
    CORE_TEMPORAL_REPAIR = "CORE_TEMPORAL_REPAIR"


class RepairSourceKind(str, Enum):
    SEMANTIC_FINDING = "SEMANTIC_FINDING"
    DETERMINISTIC_QA = "DETERMINISTIC_QA"
    SCENE_CRITIC = "SCENE_CRITIC"
    VIDEO_CRITIC = "VIDEO_CRITIC"


class QABlockerKind(str, Enum):
    SCENE_QUALITY_GATE = "SCENE_QUALITY_GATE"
    VIDEO_QUALITY_GATE = "VIDEO_QUALITY_GATE"


class SemanticQAFinding(ContractModel):
    finding_id: str = Field(..., min_length=1)
    kind: SemanticFindingKind
    reason: str = Field(..., min_length=1, max_length=4000)
    scene_ids: tuple[str, ...] = Field(default_factory=tuple)
    claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    segment_ids: tuple[str, ...] = Field(default_factory=tuple)
    objective_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("finding_id", "reason")
    @classmethod
    def _text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise AgentContractError("semantic QA finding text cannot be blank")
        return value

    @field_validator("scene_ids", "claim_ids", "segment_ids", "objective_ids", mode="before")
    @classmethod
    def _ids(cls, value: Any, info):
        return _clean_ids(value, info.field_name or "ids")

    @model_validator(mode="after")
    def _shape(self) -> "SemanticQAFinding":
        if self.kind in {
            SemanticFindingKind.EVIDENCE_UNSUPPORTED,
            SemanticFindingKind.EVIDENCE_CONTRADICTED,
            SemanticFindingKind.EVIDENCE_UNCERTAIN,
        } and not self.claim_ids:
            raise AgentContractError("evidence findings require at least one claim_id")
        if self.kind == SemanticFindingKind.NARRATION_FACT_MISMATCH and not (
            self.claim_ids or self.segment_ids
        ):
            raise AgentContractError(
                "narration factual mismatch requires claim_ids or segment_ids"
            )
        if self.kind == SemanticFindingKind.SEMANTIC_VISUAL_MISMATCH and not self.scene_ids:
            raise AgentContractError("semantic visual mismatch requires scene_ids")
        if self.kind == SemanticFindingKind.PEDAGOGICAL_STRUCTURE and not (
            self.objective_ids or self.scene_ids
        ):
            raise AgentContractError(
                "pedagogical structure finding requires objective_ids or scene_ids"
            )
        return self


class SceneObjectScope(ContractModel):
    scene_id: str = Field(..., min_length=1)
    node_ids: tuple[str, ...] = Field(default_factory=tuple)
    relation_ids: tuple[str, ...] = Field(default_factory=tuple)
    group_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("scene_id")
    @classmethod
    def _scene_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise AgentContractError("scene_id cannot be blank")
        return value

    @field_validator("node_ids", "relation_ids", "group_ids", mode="before")
    @classmethod
    def _object_ids(cls, value: Any, info):
        return _clean_ids(value, info.field_name or "object_ids")


class AgentAwareQAReport(ContractModel):
    report_id: str = Field(..., min_length=1)
    semantic_findings: tuple[SemanticQAFinding, ...] = Field(default_factory=tuple)
    scene_quality_results: tuple[QualityGateResult, ...] = Field(default_factory=tuple)
    video_critic_result: VideoCriticResult | None = None

    @field_validator("semantic_findings", "scene_quality_results", mode="before")
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)

    @field_validator("report_id")
    @classmethod
    def _report_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise AgentContractError("report_id cannot be blank")
        return value

    @model_validator(mode="after")
    def _identity(self) -> "AgentAwareQAReport":
        finding_ids = [item.finding_id for item in self.semantic_findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise AgentContractError("semantic finding IDs must be unique")
        quality_scene_ids = [item.scene_id for item in self.scene_quality_results]
        if len(quality_scene_ids) != len(set(quality_scene_ids)):
            raise AgentContractError(
                "scene quality results must have unique scene_ids"
            )
        return self


class QARoutingContext(ContractModel):
    scene_ids: tuple[str, ...] = Field(..., min_length=1)
    claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    segment_ids: tuple[str, ...] = Field(default_factory=tuple)
    objective_ids: tuple[str, ...] = Field(default_factory=tuple)
    scene_objects: tuple[SceneObjectScope, ...] = Field(..., min_length=1)

    @field_validator(
        "scene_ids",
        "claim_ids",
        "segment_ids",
        "objective_ids",
        mode="before",
    )
    @classmethod
    def _ids(cls, value: Any, info):
        return _clean_ids(value, info.field_name or "ids")

    @field_validator("scene_objects", mode="before")
    @classmethod
    def _scene_objects_tuple(cls, value: Any):
        return _tupleize(value)

    @model_validator(mode="after")
    def _scene_object_coverage(self) -> "QARoutingContext":
        scoped = [item.scene_id for item in self.scene_objects]
        if len(scoped) != len(set(scoped)):
            raise AgentContractError("scene object scopes must have unique scene_ids")
        if set(scoped) != set(self.scene_ids):
            raise AgentContractError(
                "scene object scopes must exactly cover routing scene_ids"
            )
        object.__setattr__(
            self,
            "scene_objects",
            tuple(sorted(self.scene_objects, key=lambda item: item.scene_id)),
        )
        return self


class RepairIntent(ContractModel):
    intent_id: str = Field(..., min_length=1)
    source_kind: RepairSourceKind
    source_id: str = Field(..., min_length=1)
    owner: RepairOwner
    action: RepairActionKind
    reason: str = Field(..., min_length=1, max_length=4000)
    scene_ids: tuple[str, ...] = Field(default_factory=tuple)
    claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    segment_ids: tuple[str, ...] = Field(default_factory=tuple)
    objective_ids: tuple[str, ...] = Field(default_factory=tuple)
    object_ids: tuple[str, ...] = Field(default_factory=tuple)
    core_patch_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("intent_id", "source_id", "reason")
    @classmethod
    def _text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise AgentContractError("repair intent text cannot be blank")
        return value

    @field_validator(
        "scene_ids",
        "claim_ids",
        "segment_ids",
        "objective_ids",
        "object_ids",
        "core_patch_ids",
        mode="before",
    )
    @classmethod
    def _ids(cls, value: Any, info):
        return _clean_ids(value, info.field_name or "ids")

    @model_validator(mode="after")
    def _owner_action(self) -> "RepairIntent":
        allowed = {
            RepairOwner.RESEARCH_ORCHESTRATION: {
                RepairActionKind.RESEARCH_EVIDENCE_REPAIR,
            },
            RepairOwner.SCRIPT_AGENT: {
                RepairActionKind.SCRIPT_FACT_REWRITE,
                RepairActionKind.SCRIPT_PACING_REWRITE,
            },
            RepairOwner.PEDAGOGY_AGENT: {
                RepairActionKind.PEDAGOGY_REPLAN,
            },
            RepairOwner.VISUAL_DIRECTOR: {
                RepairActionKind.VISUAL_SEMANTIC_REGENERATION,
            },
            RepairOwner.CORE_REPAIR: {
                RepairActionKind.CORE_DETERMINISTIC_REPAIR,
                RepairActionKind.CORE_SELECTIVE_REPAIR,
                RepairActionKind.CORE_TEMPORAL_REPAIR,
            },
        }
        if self.action not in allowed[self.owner]:
            raise AgentContractError(
                f"repair action {self.action.value} does not belong to owner {self.owner.value}"
            )
        if (
            self.owner == RepairOwner.CORE_REPAIR
            and self.action == RepairActionKind.CORE_SELECTIVE_REPAIR
            and not self.core_patch_ids
        ):
            raise AgentContractError("Core selective repair requires core_patch_ids")
        if self.owner != RepairOwner.CORE_REPAIR and self.core_patch_ids:
            raise AgentContractError(
                "agent-owned repair intent cannot carry Core patch IDs"
            )
        return self


class QABlocker(ContractModel):
    blocker_id: str = Field(..., min_length=1)
    kind: QABlockerKind
    state: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1, max_length=4000)
    scene_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("blocker_id", "state", "reason")
    @classmethod
    def _text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise AgentContractError("QA blocker text cannot be blank")
        return value

    @field_validator("scene_ids", mode="before")
    @classmethod
    def _scene_ids(cls, value: Any):
        return _clean_ids(value, "scene_ids")


class AgentAwareRoutingPlan(ContractModel):
    plan_id: str = Field(..., min_length=1)
    report_id: str = Field(..., min_length=1)
    intents: tuple[RepairIntent, ...] = Field(default_factory=tuple)
    blockers: tuple[QABlocker, ...] = Field(default_factory=tuple)
    publication_blocked: bool

    @field_validator("intents", "blockers", mode="before")
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)

    @field_validator("publication_blocked", mode="before")
    @classmethod
    def _strict_bool(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise AgentContractError("publication_blocked must be boolean")
        return value

    @model_validator(mode="after")
    def _integrity(self) -> "AgentAwareRoutingPlan":
        intent_ids = [item.intent_id for item in self.intents]
        blocker_ids = [item.blocker_id for item in self.blockers]
        if len(intent_ids) != len(set(intent_ids)):
            raise AgentContractError("repair intent IDs must be unique")
        if len(blocker_ids) != len(set(blocker_ids)):
            raise AgentContractError("QA blocker IDs must be unique")
        expected = bool(self.intents or self.blockers)
        if self.publication_blocked != expected:
            raise AgentContractError(
                "publication_blocked must reflect repair intents or unresolved QA blockers"
            )
        object.__setattr__(
            self, "intents", tuple(sorted(self.intents, key=lambda item: item.intent_id))
        )
        object.__setattr__(
            self, "blockers", tuple(sorted(self.blockers, key=lambda item: item.blocker_id))
        )
        return self
