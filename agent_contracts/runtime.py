"""Execution-audit and budget contracts for future Hermes orchestration."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, computed_field, field_validator, model_validator

from .base import (
    AgentContractError,
    ArtifactRef,
    ContractModel,
    finite_nonnegative,
    normalize_id,
    normalize_text,
    require_unique,
)


def _tupleize(value: Any):
    return tuple(value) if isinstance(value, list) else value


class AgentRunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class AgentStageRecord(ContractModel):
    step_id: str
    stage_name: str
    agent_id: str
    status: AgentRunStatus
    model: str | None = None
    input_artifact_ids: tuple[str, ...] = Field(default_factory=tuple)
    output_artifact_ids: tuple[str, ...] = Field(default_factory=tuple)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    duration_ms: int = Field(default=0, ge=0)
    error: str | None = None

    @field_validator("input_artifact_ids", "output_artifact_ids", mode="before")
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)

    @field_validator("step_id", "agent_id")
    @classmethod
    def _ids(cls, value: str, info) -> str:
        return normalize_id(value, field_name=info.field_name)

    @field_validator("stage_name")
    @classmethod
    def _stage(cls, value: str) -> str:
        return normalize_text(value, field_name="stage_name")

    @field_validator("model")
    @classmethod
    def _model(cls, value: str | None) -> str | None:
        return None if value is None else normalize_text(value, field_name="model")

    @field_validator("input_artifact_ids", "output_artifact_ids")
    @classmethod
    def _artifact_ids(cls, value: tuple[str, ...], info) -> tuple[str, ...]:
        normalized = tuple(normalize_id(v, field_name=info.field_name) for v in value)
        require_unique(normalized, label=info.field_name)
        return normalized

    @field_validator("cost_usd", mode="before")
    @classmethod
    def _cost(cls, value: Any) -> float:
        return finite_nonnegative(value, field_name="cost_usd")

    @field_validator("error")
    @classmethod
    def _error(cls, value: str | None) -> str | None:
        return None if value is None else normalize_text(value, field_name="error")

    @model_validator(mode="after")
    def _failure_reason(self) -> "AgentStageRecord":
        if self.status in {AgentRunStatus.FAILED, AgentRunStatus.BLOCKED} and self.error is None:
            raise AgentContractError("FAILED/BLOCKED AgentStageRecord requires error")
        if self.status not in {AgentRunStatus.FAILED, AgentRunStatus.BLOCKED} and self.error is not None:
            raise AgentContractError("error is only valid for FAILED/BLOCKED AgentStageRecord")
        return self


class AgentRun(ContractModel):
    run_id: str
    brief_id: str
    root_agent_id: str
    status: AgentRunStatus
    stages: tuple[AgentStageRecord, ...] = Field(default_factory=tuple)
    artifacts: tuple[ArtifactRef, ...] = Field(default_factory=tuple)

    @field_validator("stages", "artifacts", mode="before")
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)

    @field_validator("run_id", "brief_id", "root_agent_id")
    @classmethod
    def _ids(cls, value: str, info) -> str:
        return normalize_id(value, field_name=info.field_name)

    @model_validator(mode="after")
    def _integrity(self) -> "AgentRun":
        require_unique([item.step_id for item in self.stages], label="AgentRun step_ids")
        require_unique(
            [f"{item.artifact_type}:{item.artifact_id}" for item in self.artifacts],
            label="AgentRun artifact refs",
        )
        known_artifacts = {item.artifact_id for item in self.artifacts}
        for stage in self.stages:
            unknown = sorted(
                (set(stage.input_artifact_ids) | set(stage.output_artifact_ids))
                - known_artifacts
            )
            if unknown:
                raise AgentContractError(
                    f"AgentStageRecord {stage.step_id!r} references unregistered artifacts "
                    f"{unknown!r}"
                )
        return self


class BudgetSpend(ContractModel):
    llm: float = Field(default=0.0, ge=0.0)
    vlm: float = Field(default=0.0, ge=0.0)
    image: float = Field(default=0.0, ge=0.0)
    tts: float = Field(default=0.0, ge=0.0)
    other: float = Field(default=0.0, ge=0.0)

    @field_validator("llm", "vlm", "image", "tts", "other", mode="before")
    @classmethod
    def _finite(cls, value: Any, info) -> float:
        return finite_nonnegative(value, field_name=info.field_name)

    @computed_field
    @property
    def total_usd(self) -> float:
        return round(self.llm + self.vlm + self.image + self.tts + self.other, 10)


class BudgetLimits(ContractModel):
    subagent_calls: int = Field(default=0, ge=0)
    vlm_repairs: int = Field(default=0, ge=0)
    image_generations: int = Field(default=0, ge=0)


class BudgetUsage(ContractModel):
    subagent_calls: int = Field(default=0, ge=0)
    vlm_repairs: int = Field(default=0, ge=0)
    image_generations: int = Field(default=0, ge=0)


class BudgetLedger(ContractModel):
    ledger_id: str
    max_usd: float = Field(..., ge=0.0)
    spent: BudgetSpend = Field(default_factory=BudgetSpend)
    limits: BudgetLimits = Field(default_factory=BudgetLimits)
    usage: BudgetUsage = Field(default_factory=BudgetUsage)

    @field_validator("ledger_id")
    @classmethod
    def _ledger_id(cls, value: str) -> str:
        return normalize_id(value, field_name="ledger_id")

    @field_validator("max_usd", mode="before")
    @classmethod
    def _max_usd(cls, value: Any) -> float:
        return finite_nonnegative(value, field_name="max_usd")

    @model_validator(mode="after")
    def _budget_bounds(self) -> "BudgetLedger":
        if self.spent.total_usd > self.max_usd + 1e-9:
            raise AgentContractError(
                f"BudgetLedger overspent: spent={self.spent.total_usd} max={self.max_usd}"
            )
        for name in ("subagent_calls", "vlm_repairs", "image_generations"):
            used = getattr(self.usage, name)
            limit = getattr(self.limits, name)
            if used > limit:
                raise AgentContractError(
                    f"BudgetLedger usage exceeds {name}: used={used} limit={limit}"
                )
        return self

    @computed_field
    @property
    def remaining_usd(self) -> float:
        return round(max(0.0, self.max_usd - self.spent.total_usd), 10)
