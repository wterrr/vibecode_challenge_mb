"""Typed artifacts for the LearnFlow Visual Director."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, computed_field, field_validator, model_validator

from agent_contracts import ContractModel, Storyboard
from agent_contracts.base import normalize_id, require_unique
from learnflow_v2.scenegraph import SceneGraph


def _tupleize(value: Any):
    return tuple(value) if isinstance(value, list) else value


class VisualDirectorIssue(str, Enum):
    STORYBOARD_SCRIPT_COVERAGE = "STORYBOARD_SCRIPT_COVERAGE"
    SCENEGRAPH_SCENE_COVERAGE = "SCENEGRAPH_SCENE_COVERAGE"
    TEACHING_FUNCTION_MISMATCH = "TEACHING_FUNCTION_MISMATCH"
    SCENE_PURPOSE_MISMATCH = "SCENE_PURPOSE_MISMATCH"
    UNKNOWN_CONCEPT_REF = "UNKNOWN_CONCEPT_REF"
    CONTINUITY_KEY_MISMATCH = "CONTINUITY_KEY_MISMATCH"
    SCENE_CONCEPT_SET_MISMATCH = "SCENE_CONCEPT_SET_MISMATCH"
    EMPTY_SCENEGRAPH = "EMPTY_SCENEGRAPH"
    REGISTRY_VALIDATION_FAILED = "REGISTRY_VALIDATION_FAILED"
    VISUAL_IMPLEMENTATION_DIRECTIVE = "VISUAL_IMPLEMENTATION_DIRECTIVE"


class VisualDirectorOutput(ContractModel):
    """Hermes output envelope: semantic storyboard plus one SceneGraph per scene."""

    storyboard: Storyboard
    scenegraphs: tuple[SceneGraph, ...] = Field(..., min_length=1)

    @field_validator("scenegraphs", mode="before")
    @classmethod
    def _scenegraphs_tuple(cls, value: Any):
        return _tupleize(value)

    @model_validator(mode="after")
    def _unique_scenegraphs(self) -> "VisualDirectorOutput":
        require_unique(
            [graph.scene_id for graph in self.scenegraphs],
            label="VisualDirectorOutput scenegraph scene_ids",
        )
        return self


class VisualDirectorValidation(ContractModel):
    storyboard_id: str
    issues: tuple[VisualDirectorIssue, ...] = Field(default_factory=tuple)
    scene_coverage_error_ids: tuple[str, ...] = Field(default_factory=tuple)
    teaching_function_scene_ids: tuple[str, ...] = Field(default_factory=tuple)
    purpose_scene_ids: tuple[str, ...] = Field(default_factory=tuple)
    unknown_concept_refs: tuple[str, ...] = Field(default_factory=tuple)
    continuity_scene_ids: tuple[str, ...] = Field(default_factory=tuple)
    concept_set_scene_ids: tuple[str, ...] = Field(default_factory=tuple)
    empty_scene_ids: tuple[str, ...] = Field(default_factory=tuple)
    registry_invalid_scene_ids: tuple[str, ...] = Field(default_factory=tuple)
    boundary_violation_scene_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator(
        "issues",
        "scene_coverage_error_ids",
        "teaching_function_scene_ids",
        "purpose_scene_ids",
        "unknown_concept_refs",
        "continuity_scene_ids",
        "concept_set_scene_ids",
        "empty_scene_ids",
        "registry_invalid_scene_ids",
        "boundary_violation_scene_ids",
        mode="before",
    )
    @classmethod
    def _tuples(cls, value: Any):
        return _tupleize(value)

    @field_validator("storyboard_id")
    @classmethod
    def _storyboard_id(cls, value: str) -> str:
        return normalize_id(value, field_name="storyboard_id")

    @field_validator(
        "scene_coverage_error_ids",
        "teaching_function_scene_ids",
        "purpose_scene_ids",
        "unknown_concept_refs",
        "continuity_scene_ids",
        "concept_set_scene_ids",
        "empty_scene_ids",
        "registry_invalid_scene_ids",
        "boundary_violation_scene_ids",
    )
    @classmethod
    def _ids(cls, value: tuple[str, ...], info) -> tuple[str, ...]:
        normalized = tuple(normalize_id(v, field_name=info.field_name) for v in value)
        require_unique(normalized, label=info.field_name)
        return normalized

    @field_validator("issues")
    @classmethod
    def _issues(
        cls, value: tuple[VisualDirectorIssue, ...]
    ) -> tuple[VisualDirectorIssue, ...]:
        require_unique([item.value for item in value], label="VisualDirectorValidation issues")
        return value

    @computed_field
    @property
    def ready_for_core(self) -> bool:
        return not self.issues
