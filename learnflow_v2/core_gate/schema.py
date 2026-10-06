"""Fail-closed Core Gate evidence contracts for LearnFlow V2."""

from __future__ import annotations

from enum import Enum
import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from learnflow_v2.core.serialization import canonical_json

V2_CORE_GATE_SCHEMA_VERSION = "2.1"


class CoreGateError(ValueError):
    pass


class CoreGateMetric(str, Enum):
    RENDER_SUCCESS_RATE = "RENDER_SUCCESS_RATE"
    FATAL_CLIPPING_COUNT = "FATAL_CLIPPING_COUNT"
    FATAL_OVERLAP_COUNT = "FATAL_OVERLAP_COUNT"
    INVALID_MOTION_PLAN_COUNT = "INVALID_MOTION_PLAN_COUNT"
    SELECTIVE_REPAIR_SUCCESS_RATE = "SELECTIVE_REPAIR_SUCCESS_RATE"
    REPRODUCIBILITY_RATE = "REPRODUCIBILITY_RATE"
    V1_V2_CRITICAL_REGRESSION_COUNT = "V1_V2_CRITICAL_REGRESSION_COUNT"
    V2_STATIC_QUALITY_DELTA = "V2_STATIC_QUALITY_DELTA"
    VLM_UNAVAILABLE_DETERMINISTIC_OK = "VLM_UNAVAILABLE_DETERMINISTIC_OK"
    LOCAL_REPAIR_SCOPE_OK = "LOCAL_REPAIR_SCOPE_OK"


class EvidenceKind(str, Enum):
    BENCHMARK = "BENCHMARK"
    CONTRACT_TEST = "CONTRACT_TEST"


class CriterionState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


class CoreGateState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


class CoreGateEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    metric: CoreGateMetric
    kind: EvidenceKind
    value: float | int | bool
    source: tuple[str, ...] = Field(..., min_length=1)
    sample_count: int | None = None
    benchmark_id: str | None = None
    notes: str = Field(default="", max_length=4000)

    @field_validator("value", mode="before")
    @classmethod
    def _strict_value(cls, value: Any) -> float | int | bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value
        if isinstance(value, float) and math.isfinite(value):
            return value
        raise CoreGateError("evidence value must be a finite number or strict boolean")

    @field_validator("source", mode="before")
    @classmethod
    def _normalize_source(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple) or not value:
            raise CoreGateError("evidence source must be a non-empty tuple/list")
        normalized = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
        if len(normalized) != len(value) or len(normalized) != len(set(normalized)):
            raise CoreGateError("evidence sources must be unique non-empty strings")
        return tuple(sorted(normalized))

    @field_validator("sample_count", mode="before")
    @classmethod
    def _strict_sample_count(cls, value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise CoreGateError("sample_count must be a positive strict integer")
        return value

    @field_validator("benchmark_id")
    @classmethod
    def _normalize_benchmark_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise CoreGateError("benchmark_id cannot be blank")
        return value

    @model_validator(mode="after")
    def _validate_kind(self) -> "CoreGateEvidence":
        benchmark_only = {
            CoreGateMetric.RENDER_SUCCESS_RATE,
            CoreGateMetric.FATAL_CLIPPING_COUNT,
            CoreGateMetric.FATAL_OVERLAP_COUNT,
            CoreGateMetric.INVALID_MOTION_PLAN_COUNT,
            CoreGateMetric.SELECTIVE_REPAIR_SUCCESS_RATE,
            CoreGateMetric.REPRODUCIBILITY_RATE,
            CoreGateMetric.V1_V2_CRITICAL_REGRESSION_COUNT,
            CoreGateMetric.V2_STATIC_QUALITY_DELTA,
        }
        if self.metric in benchmark_only and self.kind != EvidenceKind.BENCHMARK:
            raise CoreGateError(f"{self.metric.value} requires BENCHMARK evidence")
        if self.kind == EvidenceKind.BENCHMARK:
            if self.sample_count is None:
                raise CoreGateError("benchmark evidence requires sample_count")
            if self.benchmark_id is None:
                raise CoreGateError("benchmark evidence requires benchmark_id")
        return self


class CoreGateEvidenceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = V2_CORE_GATE_SCHEMA_VERSION
    repo_commit: str
    evidence: tuple[CoreGateEvidence, ...] = Field(default_factory=tuple)

    @field_validator("repo_commit")
    @classmethod
    def _validate_commit(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{40}", value):
            raise CoreGateError("repo_commit must be a 40-character git SHA")
        return value

    @field_validator("evidence", mode="before")
    @classmethod
    def _tupleize(cls, value: Any) -> tuple[Any, ...]:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _validate_unique_metrics(self) -> "CoreGateEvidenceBundle":
        metrics = [item.metric for item in self.evidence]
        if len(metrics) != len(set(metrics)):
            raise CoreGateError("Core Gate evidence may contain at most one record per metric")
        object.__setattr__(self, "evidence", tuple(sorted(self.evidence, key=lambda item: item.metric.value)))
        return self

    def to_canonical_json(self) -> str:
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, payload: str) -> "CoreGateEvidenceBundle":
        return cls.model_validate_json(payload)


class CriterionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    metric: CoreGateMetric
    state: CriterionState
    requirement: str
    observed: str
    source: tuple[str, ...] = Field(default_factory=tuple)


class CoreGateReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = V2_CORE_GATE_SCHEMA_VERSION
    repo_commit: str
    state: CoreGateState
    criteria: tuple[CriterionResult, ...]
    blockers: tuple[str, ...] = Field(default_factory=tuple)

    def to_canonical_json(self) -> str:
        return canonical_json(self)
