"""Lesson-planning, script, and storyboard contracts."""

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
from .research import EvidenceGraph


def _tupleize(value: Any):
    return tuple(value) if isinstance(value, list) else value


class LearningBrief(ContractModel):
    brief_id: str
    user_query: str
    learner_level: str
    target_duration_minutes: float = Field(..., gt=0.0, le=180.0)
    language: str
    style: str = "clear educational"
    constraints: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("constraints", mode="before")
    @classmethod
    def _constraints_tuple(cls, value: Any):
        return _tupleize(value)

    @field_validator("brief_id")
    @classmethod
    def _brief_id(cls, value: str) -> str:
        return normalize_id(value, field_name="brief_id")

    @field_validator("user_query", "learner_level", "language", "style")
    @classmethod
    def _texts(cls, value: str, info) -> str:
        return normalize_text(value, field_name=info.field_name)

    @field_validator("constraints")
    @classmethod
    def _constraint_text(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(normalize_text(v, field_name="constraint") for v in value)
        require_unique(normalized, label="constraints")
        return normalized


class LearningObjective(ContractModel):
    objective_id: str
    description: str
    assessment_criterion: str

    @field_validator("objective_id")
    @classmethod
    def _id(cls, value: str) -> str:
        return normalize_id(value, field_name="objective_id")

    @field_validator("description", "assessment_criterion")
    @classmethod
    def _text(cls, value: str, info) -> str:
        return normalize_text(value, field_name=info.field_name)


class PedagogyExample(ContractModel):
    example_id: str
    concept: str
    description: str
    claim_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("claim_ids", mode="before")
    @classmethod
    def _claim_tuple(cls, value: Any):
        return _tupleize(value)

    @field_validator("example_id")
    @classmethod
    def _id(cls, value: str) -> str:
        return normalize_id(value, field_name="example_id")

    @field_validator("concept", "description")
    @classmethod
    def _text(cls, value: str, info) -> str:
        return normalize_text(value, field_name=info.field_name)

    @field_validator("claim_ids")
    @classmethod
    def _claims(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(normalize_id(v, field_name="claim_id") for v in value)
        require_unique(normalized, label="PedagogyExample claim_ids")
        return normalized


class PedagogyMisconception(ContractModel):
    misconception_id: str
    misconception: str
    correction: str
    claim_ids: tuple[str, ...] = Field(..., min_length=1)

    @field_validator("claim_ids", mode="before")
    @classmethod
    def _claim_tuple(cls, value: Any):
        return _tupleize(value)

    @field_validator("misconception_id")
    @classmethod
    def _id(cls, value: str) -> str:
        return normalize_id(value, field_name="misconception_id")

    @field_validator("misconception", "correction")
    @classmethod
    def _text(cls, value: str, info) -> str:
        return normalize_text(value, field_name=info.field_name)

    @field_validator("claim_ids")
    @classmethod
    def _claims(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(normalize_id(v, field_name="claim_id") for v in value)
        require_unique(normalized, label="PedagogyMisconception claim_ids")
        return normalized


class AssessmentProbe(ContractModel):
    probe_id: str
    prompt: str
    expected_outcome: str
    objective_ids: tuple[str, ...] = Field(..., min_length=1)

    @field_validator("objective_ids", mode="before")
    @classmethod
    def _objective_tuple(cls, value: Any):
        return _tupleize(value)

    @field_validator("probe_id")
    @classmethod
    def _id(cls, value: str) -> str:
        return normalize_id(value, field_name="probe_id")

    @field_validator("prompt", "expected_outcome")
    @classmethod
    def _text(cls, value: str, info) -> str:
        return normalize_text(value, field_name=info.field_name)

    @field_validator("objective_ids")
    @classmethod
    def _objective_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(normalize_id(v, field_name="objective_id") for v in value)
        require_unique(normalized, label="AssessmentProbe objective_ids")
        return normalized


class PedagogyPlan(ContractModel):
    plan_id: str
    brief_id: str
    research_pack_id: str
    evidence_graph_id: str
    learning_objectives: tuple[LearningObjective, ...] = Field(..., min_length=1)
    prerequisites: tuple[str, ...] = Field(default_factory=tuple)
    concept_order: tuple[str, ...] = Field(..., min_length=1)
    worked_examples: tuple[PedagogyExample, ...] = Field(default_factory=tuple)
    analogies: tuple[PedagogyExample, ...] = Field(default_factory=tuple)
    misconceptions: tuple[PedagogyMisconception, ...] = Field(default_factory=tuple)
    assessment_probes: tuple[AssessmentProbe, ...] = Field(default_factory=tuple)

    @field_validator(
        "learning_objectives", "prerequisites", "concept_order", "worked_examples",
        "analogies", "misconceptions", "assessment_probes", mode="before",
    )
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)

    @field_validator("plan_id", "brief_id", "research_pack_id", "evidence_graph_id")
    @classmethod
    def _ids(cls, value: str, info) -> str:
        return normalize_id(value, field_name=info.field_name)

    @field_validator("prerequisites", "concept_order")
    @classmethod
    def _texts(cls, value: tuple[str, ...], info) -> tuple[str, ...]:
        normalized = tuple(normalize_text(v, field_name=info.field_name) for v in value)
        require_unique(normalized, label=info.field_name)
        return normalized

    @model_validator(mode="after")
    def _local_refs(self) -> "PedagogyPlan":
        objective_ids = [item.objective_id for item in self.learning_objectives]
        require_unique(objective_ids, label="PedagogyPlan objective_ids")
        require_unique(
            [item.example_id for item in (*self.worked_examples, *self.analogies)],
            label="PedagogyPlan example_ids",
        )
        require_unique(
            [item.misconception_id for item in self.misconceptions],
            label="PedagogyPlan misconception_ids",
        )
        require_unique(
            [item.probe_id for item in self.assessment_probes],
            label="PedagogyPlan probe_ids",
        )
        objective_set = set(objective_ids)
        for probe in self.assessment_probes:
            unknown = sorted(set(probe.objective_ids) - objective_set)
            if unknown:
                raise AgentContractError(
                    f"assessment probe {probe.probe_id!r} references unknown objectives {unknown!r}"
                )
        return self

    def validate_against_evidence(self, graph: EvidenceGraph) -> None:
        if self.evidence_graph_id != graph.graph_id:
            raise AgentContractError("PedagogyPlan evidence_graph_id does not match EvidenceGraph")
        known = set(graph.claim_ids)
        for item in (*self.worked_examples, *self.analogies, *self.misconceptions):
            unknown = sorted(set(item.claim_ids) - known)
            if unknown:
                raise AgentContractError(
                    f"PedagogyPlan item references unknown claims {unknown!r}"
                )


class TeachingFunction(str, Enum):
    INTRODUCE = "INTRODUCE"
    EXPLAIN = "EXPLAIN"
    COMPARE = "COMPARE"
    DEMONSTRATE = "DEMONSTRATE"
    PRACTICE = "PRACTICE"
    CHECK = "CHECK"
    SUMMARIZE = "SUMMARIZE"


class ScriptSegment(ContractModel):
    segment_id: str
    spoken_text: str
    subtitle_text: str
    spoken_language: str
    subtitle_language: str
    claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    objective_ids: tuple[str, ...] = Field(default_factory=tuple)
    teaching_function: TeachingFunction
    emphasis: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("claim_ids", "objective_ids", "emphasis", mode="before")
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)

    @field_validator("segment_id")
    @classmethod
    def _id(cls, value: str) -> str:
        return normalize_id(value, field_name="segment_id")

    @field_validator("spoken_text", "subtitle_text", "spoken_language", "subtitle_language")
    @classmethod
    def _required_text(cls, value: str, info) -> str:
        return normalize_text(value, field_name=info.field_name)

    @field_validator("claim_ids", "objective_ids")
    @classmethod
    def _id_tuples(cls, value: tuple[str, ...], info) -> tuple[str, ...]:
        normalized = tuple(normalize_id(v, field_name=info.field_name) for v in value)
        require_unique(normalized, label=info.field_name)
        return normalized

    @field_validator("emphasis")
    @classmethod
    def _emphasis(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(normalize_text(v, field_name="emphasis") for v in value)
        require_unique(normalized, label="emphasis")
        return normalized


class LessonScript(ContractModel):
    script_id: str
    pedagogy_plan_id: str
    segments: tuple[ScriptSegment, ...] = Field(..., min_length=1)

    @field_validator("segments", mode="before")
    @classmethod
    def _segments_tuple(cls, value: Any):
        return _tupleize(value)

    @field_validator("script_id", "pedagogy_plan_id")
    @classmethod
    def _ids(cls, value: str, info) -> str:
        return normalize_id(value, field_name=info.field_name)

    @model_validator(mode="after")
    def _unique_segments(self) -> "LessonScript":
        require_unique(
            [segment.segment_id for segment in self.segments],
            label="LessonScript segment_ids",
        )
        return self

    def validate_against(self, graph: EvidenceGraph, pedagogy: PedagogyPlan) -> None:
        if self.pedagogy_plan_id != pedagogy.plan_id:
            raise AgentContractError("LessonScript pedagogy_plan_id does not match PedagogyPlan")
        known_claims = set(graph.claim_ids)
        known_objectives = {item.objective_id for item in pedagogy.learning_objectives}
        for segment in self.segments:
            unknown_claims = sorted(set(segment.claim_ids) - known_claims)
            unknown_objectives = sorted(set(segment.objective_ids) - known_objectives)
            if unknown_claims:
                raise AgentContractError(
                    f"script segment {segment.segment_id!r} references unknown claims "
                    f"{unknown_claims!r}"
                )
            if unknown_objectives:
                raise AgentContractError(
                    f"script segment {segment.segment_id!r} references unknown objectives "
                    f"{unknown_objectives!r}"
                )


class StoryboardScene(ContractModel):
    scene_id: str
    script_segment_ids: tuple[str, ...] = Field(..., min_length=1)
    teaching_function: TeachingFunction
    visual_intent: str
    concept_refs: tuple[str, ...] = Field(default_factory=tuple)
    continuity_keys: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("script_segment_ids", "concept_refs", "continuity_keys", mode="before")
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)

    @field_validator("scene_id")
    @classmethod
    def _scene_id(cls, value: str) -> str:
        return normalize_id(value, field_name="scene_id")

    @field_validator("visual_intent")
    @classmethod
    def _visual_intent(cls, value: str) -> str:
        return normalize_text(value, field_name="visual_intent")

    @field_validator("script_segment_ids")
    @classmethod
    def _segments(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(normalize_id(v, field_name="segment_id") for v in value)
        require_unique(normalized, label="StoryboardScene script_segment_ids")
        return normalized

    @field_validator("concept_refs", "continuity_keys")
    @classmethod
    def _semantic_refs(cls, value: tuple[str, ...], info) -> tuple[str, ...]:
        normalized = tuple(normalize_text(v, field_name=info.field_name) for v in value)
        require_unique(normalized, label=info.field_name)
        return normalized


class Storyboard(ContractModel):
    storyboard_id: str
    script_id: str
    scenes: tuple[StoryboardScene, ...] = Field(..., min_length=1)

    @field_validator("scenes", mode="before")
    @classmethod
    def _scenes_tuple(cls, value: Any):
        return _tupleize(value)

    @field_validator("storyboard_id", "script_id")
    @classmethod
    def _ids(cls, value: str, info) -> str:
        return normalize_id(value, field_name=info.field_name)

    @model_validator(mode="after")
    def _unique_scenes(self) -> "Storyboard":
        require_unique(
            [scene.scene_id for scene in self.scenes],
            label="Storyboard scene_ids",
        )
        return self

    def validate_against_script(self, script: LessonScript) -> None:
        if self.script_id != script.script_id:
            raise AgentContractError("Storyboard script_id does not match LessonScript")
        expected = [segment.segment_id for segment in script.segments]
        actual = [
            segment_id
            for scene in self.scenes
            for segment_id in scene.script_segment_ids
        ]
        if actual != expected:
            raise AgentContractError(
                "Storyboard must cover every LessonScript segment exactly once and in order"
            )
