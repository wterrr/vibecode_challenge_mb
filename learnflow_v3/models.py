"""LearnFlow V3.0 semantic contracts. No renderer code or freeform geometry."""
from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agent_contracts.base import normalize_id, normalize_text, require_unique
from learnflow_v2.core.jsonsafe import validate_json_safe

V3_SCHEMA_VERSION = "3.0"


class SemanticContractError(ValueError):
    """A V3 typed semantic contract cannot be accepted."""


class V3Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)  # JSON strings map to finite Enum members; unknown values fail


class VersionedArtifact(V3Model):
    schema_version: Literal["3.0"] = V3_SCHEMA_VERSION

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json", exclude_none=True),
            ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
        )

    def content_sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class CanonicalConceptRef(V3Model):
    """Always carry V2's exact concept_id AND canonical_key, never an inferred alias."""

    concept_id: str
    canonical_key: str

    @field_validator("concept_id", "canonical_key")
    @classmethod
    def _nonblank(cls, v: str) -> str:
        if not v or v != v.strip():
            raise SemanticContractError("canonical concept identity must be exact and nonblank")
        return v


class RepresentationType(str, Enum):
    WORKED_EXAMPLE_BOARD = "WORKED_EXAMPLE_BOARD"
    PROCESS_FLOW = "PROCESS_FLOW"
    EQUATION_GRAPH = "EQUATION_GRAPH"
    CONCEPT_CARD = "CONCEPT_CARD"


class ObjectKind(str, Enum):
    SEQUENCE = "SEQUENCE"
    INTERVAL = "INTERVAL"
    POINTER = "POINTER"
    EQUATION = "EQUATION"
    PROCESS = "PROCESS"
    LABEL = "LABEL"


class StateSourceKind(str, Enum):
    VERIFIED_TRACE = "VERIFIED_TRACE"
    STATIC = "STATIC"


class VisualTeachingConstraints(V3Model):
    language: str
    learner_level: str
    target_duration_minutes: float = Field(gt=0, le=30)
    cognitive_load_tier: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    accessibility: tuple[str, ...] = ()


class TeachingSection(V3Model):
    section_id: str
    objective_refs: tuple[str, ...] = Field(min_length=1)
    learner_state_before: str
    learner_state_after: str
    visual_teaching_goal: str
    representation_options: tuple[RepresentationType, ...] = Field(min_length=1)
    visual_complexity_budget: int = Field(strict=True, ge=1, le=10)
    hero_candidate: bool = False

    @model_validator(mode="after")
    def _refs(self):
        normalize_id(self.section_id, field_name="section_id")
        require_unique(self.objective_refs, label="section objective_refs")
        require_unique(self.representation_options, label="representation_options")
        for v in self.objective_refs:
            normalize_id(v, field_name="objective_ref")
        for v in (self.learner_state_before, self.learner_state_after, self.visual_teaching_goal):
            normalize_text(v)
        return self


class TeachingBeat(V3Model):
    beat_id: str
    section_ref: str
    script_segment_ref: str
    claim_refs: tuple[str, ...] = ()
    concept_refs: tuple[CanonicalConceptRef, ...] = ()
    expected_visible_state_change: str | None = None
    allowed_static_justification: str | None = None
    importance: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _refs(self):
        for v in (self.beat_id, self.section_ref, self.script_segment_ref):
            normalize_id(v)
        require_unique(self.claim_refs, label="beat claim_refs")
        require_unique([x.concept_id for x in self.concept_refs], label="beat concept_refs")
        for v in self.claim_refs:
            normalize_id(v)
        if bool(self.expected_visible_state_change) == bool(self.allowed_static_justification):
            raise SemanticContractError("beat requires exactly one visual change or static justification")
        return self


class VisualTeachingPlan(VersionedArtifact):
    lesson_id: str
    learning_objective_ids: tuple[str, ...] = Field(min_length=1)
    prerequisite_refs: tuple[CanonicalConceptRef, ...] = ()
    misconception_refs: tuple[CanonicalConceptRef, ...] = ()
    sections: tuple[TeachingSection, ...] = Field(min_length=1)
    beats: tuple[TeachingBeat, ...] = Field(min_length=1)
    constraints: VisualTeachingConstraints

    @model_validator(mode="after")
    def _local(self):
        normalize_id(self.lesson_id, field_name="lesson_id")
        require_unique(self.learning_objective_ids, label="learning_objective_ids")
        for v in self.learning_objective_ids:
            normalize_id(v, field_name="objective_id")
        require_unique([s.section_id for s in self.sections], label="section IDs")
        require_unique([b.beat_id for b in self.beats], label="beat IDs")
        order = {s.section_id: i for i, s in enumerate(self.sections)}
        used = []
        for section in self.sections:
            if not set(section.objective_refs) <= set(self.learning_objective_ids):
                raise SemanticContractError("section references unknown learning objective")
        for beat in self.beats:
            if beat.section_ref not in order:
                raise SemanticContractError("beat refers to unknown section")
            used.append(order[beat.section_ref])
        if used != sorted(used) or set(used) != set(order.values()):
            raise SemanticContractError("beat order/section coverage broken")
        return self


class StateSource(V3Model):
    kind: StateSourceKind
    ref: str

    @model_validator(mode="after")
    def _kind_ref(self):
        expected = "trace:" if self.kind == StateSourceKind.VERIFIED_TRACE else "static:"
        if not self.ref.startswith(expected) or not self.ref[len(expected):]:
            raise SemanticContractError("state_source kind/ref mismatch")
        normalize_id(self.ref)
        return self


class SemanticObject(V3Model):
    object_id: str
    kind: ObjectKind
    concept: CanonicalConceptRef | None = None
    state_ref: str | None = None

    @model_validator(mode="after")
    def _local(self):
        normalize_id(self.object_id, field_name="object_id")
        if self.state_ref is not None:
            normalize_id(self.state_ref, field_name="state_ref")
        return self


class VisualPatternSpec(VersionedArtifact):
    pattern_id: str
    scene_id: str
    pattern_type: RepresentationType
    objective_refs: tuple[str, ...] = Field(min_length=1)
    source_refs: tuple[str, ...] = Field(min_length=1)
    concept_refs: tuple[CanonicalConceptRef, ...] = Field(min_length=1)
    state_source: StateSource
    semantic_objects: tuple[SemanticObject, ...] = Field(min_length=1)
    visual_constraints: dict[str, str] = Field(default_factory=dict)
    fallback_family: tuple[RepresentationType, ...] = ()
    renderer_requirement: Literal["STATIC", "STATEFUL_SEQUENCE", "PROCESS", "MATH"]

    @model_validator(mode="after")
    def _local(self):
        normalize_id(self.pattern_id)
        normalize_id(self.scene_id)
        require_unique(self.objective_refs, label="pattern objective_refs")
        require_unique(self.source_refs, label="pattern source_refs")
        require_unique([c.concept_id for c in self.concept_refs], label="pattern concept_refs")
        require_unique([o.object_id for o in self.semantic_objects], label="pattern object IDs")
        require_unique(self.fallback_family, label="fallback_family")
        for ref in self.source_refs:
            if not (ref.startswith("script:") or ref.startswith("trace:")):
                raise SemanticContractError("unrecognized source ref namespace")
            normalize_id(ref)
        if self.state_source.ref not in self.source_refs and self.state_source.kind == StateSourceKind.VERIFIED_TRACE:
            raise SemanticContractError("verified trace omitted from pattern source_refs")
        if any(o.state_ref is not None and o.state_ref != self.state_source.ref for o in self.semantic_objects):
            raise SemanticContractError("semantic object state_ref mismatch")
        if self.state_source.kind == StateSourceKind.VERIFIED_TRACE and self.renderer_requirement == "STATIC":
            raise SemanticContractError("verified trace cannot declare STATIC renderer")
        forbidden = {"x", "y", "left_px", "top_px", "width_px", "height_px", "font_size", "pixel_x", "pixel_y"}
        if forbidden & self.visual_constraints.keys():
            raise SemanticContractError("renderer geometry directives are not semantic contracts")
        return self


class ObjectState(V3Model):
    object_id: str
    properties: dict[str, Any] = Field(min_length=1)

    @field_validator("properties")
    @classmethod
    def _json_safe(cls, v: dict[str, Any]) -> dict[str, Any]:
        validate_json_safe(v, path="object_state.properties")
        forbidden = {"x", "y", "x_px", "y_px", "left_px", "top_px", "pixel_x", "pixel_y"}
        if forbidden & v.keys():
            raise SemanticContractError("pixel coordinate state is forbidden")
        return v


class LedgerStep(V3Model):
    step_id: str
    beat_ref: str
    object_states: tuple[ObjectState, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _local(self):
        normalize_id(self.step_id)
        normalize_id(self.beat_ref)
        require_unique([x.object_id for x in self.object_states], label="step object IDs")
        return self


class StateLedger(VersionedArtifact):
    ledger_id: str
    pattern_ref: str
    source_ref: str
    steps: tuple[LedgerStep, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _local(self):
        normalize_id(self.ledger_id)
        normalize_id(self.pattern_ref)
        normalize_id(self.source_ref)
        require_unique([x.step_id for x in self.steps], label="ledger step IDs")
        require_unique([x.beat_ref for x in self.steps], label="ledger step beat_refs")
        first = {x.object_id for x in self.steps[0].object_states}
        if any({x.object_id for x in s.object_states} != first for s in self.steps[1:]):
            raise SemanticContractError("every ledger step must preserve object identities")
        return self
