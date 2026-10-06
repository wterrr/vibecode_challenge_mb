"""Strict benchmark contracts for LearnFlowBench."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BenchmarkDomain(str, Enum):
    CS = "cs"
    MATH = "math"
    PHYSICS = "physics"
    BIOLOGY = "biology"
    CHEMISTRY = "chemistry"
    HISTORY_GENERAL = "history_general"


class BenchmarkDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class BenchmarkCandidateId(str, Enum):
    V1 = "v1"
    V2A = "v2a"
    V2B = "v2b"
    V2C = "v2c"
    V2D = "v2d"


class BenchmarkMetricCategory(str, Enum):
    STRUCTURAL = "structural"
    VISUAL = "visual"
    TEMPORAL = "temporal"
    SEMANTIC = "semantic"
    PEDAGOGY = "pedagogy"
    LEARNING_OUTCOME = "learning_outcome"
    COST = "cost"


class MeasurementState(str, Enum):
    MEASURED = "MEASURED"
    UNMEASURED = "UNMEASURED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class BenchmarkTopic(_StrictModel):
    topic_id: str = Field(..., min_length=1)
    domain: BenchmarkDomain
    difficulty: BenchmarkDifficulty
    query: str = Field(..., min_length=1)
    learner_level: str = Field(..., min_length=1)
    target_duration_minutes: float = Field(..., gt=0.0, le=30.0)
    language: str = Field(default="en", min_length=2)
    tags: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("topic_id")
    @classmethod
    def _topic_id(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for ch in value):
            raise ValueError("topic_id must be lowercase alphanumeric/hyphen/underscore")
        return value

    @field_validator("query", "learner_level", "language")
    @classmethod
    def _text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("benchmark text cannot be blank")
        return value

    @field_validator("tags", mode="before")
    @classmethod
    def _tuple_tags(cls, value: Any):
        return tuple(value) if isinstance(value, list) else value

    @field_validator("tags")
    @classmethod
    def _tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
        if len(cleaned) != len(value) or len(cleaned) != len(set(cleaned)):
            raise ValueError("tags must be unique non-empty strings")
        return cleaned


class BenchmarkCorpus(_StrictModel):
    schema_version: str = "1.0"
    corpus_id: str = Field(..., min_length=1)
    topics: tuple[BenchmarkTopic, ...] = Field(..., min_length=1)
    frozen: bool = True

    @field_validator("topics", mode="before")
    @classmethod
    def _tuple_topics(cls, value: Any):
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _integrity(self) -> "BenchmarkCorpus":
        ids = [topic.topic_id for topic in self.topics]
        queries = [topic.query.casefold() for topic in self.topics]
        if len(ids) != len(set(ids)):
            raise ValueError("benchmark topic IDs must be unique")
        if len(queries) != len(set(queries)):
            raise ValueError("benchmark topic queries must be unique")
        return self


class BenchmarkCandidate(_StrictModel):
    candidate_id: BenchmarkCandidateId
    label: str = Field(..., min_length=1)
    track: str = Field(..., min_length=1)
    scenegraph: bool
    layout_solver: bool
    motion: bool
    transitions: bool
    deterministic_qa: bool
    critic: bool
    repair: bool
    hermes_control_plane: bool

    @model_validator(mode="after")
    def _milestone_order(self) -> "BenchmarkCandidate":
        if self.motion and not (self.scenegraph and self.layout_solver):
            raise ValueError("motion candidate requires SceneGraph + Layout Solver")
        if self.transitions and not self.motion:
            raise ValueError("transitions require motion")
        if self.critic and not self.deterministic_qa:
            raise ValueError("critic requires deterministic QA")
        if self.repair and not self.deterministic_qa:
            raise ValueError("repair requires deterministic QA")
        if self.hermes_control_plane and not self.repair:
            raise ValueError("Hermes full system must include the accepted self-repair core")
        return self


class BenchmarkObservation(_StrictModel):
    metric_id: str = Field(..., min_length=1)
    category: BenchmarkMetricCategory
    state: MeasurementState
    value: float | int | bool | str | None = None
    unit: str | None = None
    sample_count: int | None = Field(default=None, ge=0)
    evidence: tuple[str, ...] = Field(default_factory=tuple)
    notes: str = ""

    @field_validator("evidence", mode="before")
    @classmethod
    def _tuple_evidence(cls, value: Any):
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _measurement_integrity(self) -> "BenchmarkObservation":
        if self.state == MeasurementState.MEASURED:
            if self.value is None:
                raise ValueError("MEASURED observation requires a value")
            if not self.evidence:
                raise ValueError("MEASURED observation requires evidence")
        elif self.value is not None:
            raise ValueError("UNMEASURED/NOT_APPLICABLE observations cannot carry a value")
        return self


class BenchmarkCandidateResult(_StrictModel):
    candidate_id: BenchmarkCandidateId
    execution_mode: str = Field(..., min_length=1)
    fixture_set_sha256: str = Field(..., min_length=64, max_length=64)
    observations: tuple[BenchmarkObservation, ...] = Field(default_factory=tuple)

    @field_validator("observations", mode="before")
    @classmethod
    def _tuple_observations(cls, value: Any):
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _unique_metrics(self) -> "BenchmarkCandidateResult":
        ids = [item.metric_id for item in self.observations]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate metric IDs must be unique")
        return self


class BenchmarkReport(_StrictModel):
    schema_version: str = "1.0"
    benchmark_id: str = Field(..., min_length=1)
    source_commit: str = Field(..., min_length=40, max_length=40)
    corpus_sha256: str = Field(..., min_length=64, max_length=64)
    core_fixture_sha256: str = Field(..., min_length=64, max_length=64)
    corpus_topic_count: int = Field(..., ge=1)
    core_ablation_topic_count: int = Field(..., ge=1)
    full_system_fixture_count: int = Field(..., ge=1)
    results: tuple[BenchmarkCandidateResult, ...] = Field(..., min_length=1)
    benchmark_execution_passed: bool
    sota_claim_allowed: bool = False
    limitations: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("results", "limitations", mode="before")
    @classmethod
    def _tuples(cls, value: Any):
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _report_integrity(self) -> "BenchmarkReport":
        ids = [result.candidate_id for result in self.results]
        if len(ids) != len(set(ids)):
            raise ValueError("benchmark report candidate IDs must be unique")
        if set(ids) != set(BenchmarkCandidateId):
            raise ValueError("benchmark report must contain exactly V1, V2A, V2B, V2C, and V2D")
        if self.corpus_topic_count != 100:
            raise ValueError("LearnFlowBench v1 corpus must contain exactly 100 topics")
        if self.sota_claim_allowed:
            raise ValueError(
                "LearnFlowBench v1 cannot authorize a SOTA claim; external/human learning-outcome "
                "and full live-provider evaluation are not yet part of the accepted harness"
            )
        return self
