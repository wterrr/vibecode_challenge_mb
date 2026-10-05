"""Immutable CP2.13 contracts for selective repair and artifact invalidation."""

from __future__ import annotations

from enum import Enum, IntEnum
import hashlib
import re
from types import MappingProxyType
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.qa.critic_schema import CriticPatchOp, CriticPatchSuggestion
from learnflow_v2.qa.schema import DeterministicQAReport
from learnflow_v2.repair.errors import RepairInvalidInputError
from learnflow_v2.scenegraph.schema import SceneGraph

V2_REPAIR_SCHEMA_VERSION = "2.1"
MAX_LAYOUT_SOLVES = 5
MAX_VLM_REPAIR_ROUNDS = 2
MAX_SCENE_REGENERATIONS = 1
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class ArtifactKind(str, Enum):
    CONCEPT_REGISTRY = "CONCEPT_REGISTRY"
    SCENE_GRAPH = "SCENE_GRAPH"
    NARRATION = "NARRATION"
    TTS_AUDIO = "TTS_AUDIO"
    NARRATION_BEATS = "NARRATION_BEATS"
    LAYOUT_GRAPH = "LAYOUT_GRAPH"
    MOTION_PLAN = "MOTION_PLAN"
    MOTION_SCHEDULE = "MOTION_SCHEDULE"
    RENDERED_SCENE = "RENDERED_SCENE"
    SCENE_QA = "SCENE_QA"
    INTER_SCENE_TRANSITION_PLAN = "INTER_SCENE_TRANSITION_PLAN"
    RENDERED_TRANSITION = "RENDERED_TRANSITION"
    ASSEMBLY = "ASSEMBLY"
    VIDEO_QA = "VIDEO_QA"


SCENE_SCOPED_ARTIFACTS = frozenset({
    ArtifactKind.SCENE_GRAPH,
    ArtifactKind.NARRATION,
    ArtifactKind.TTS_AUDIO,
    ArtifactKind.NARRATION_BEATS,
    ArtifactKind.LAYOUT_GRAPH,
    ArtifactKind.MOTION_PLAN,
    ArtifactKind.MOTION_SCHEDULE,
    ArtifactKind.RENDERED_SCENE,
    ArtifactKind.SCENE_QA,
})
TRANSITION_SCOPED_ARTIFACTS = frozenset({
    ArtifactKind.INTER_SCENE_TRANSITION_PLAN,
    ArtifactKind.RENDERED_TRANSITION,
})
GLOBAL_ARTIFACTS = frozenset({
    ArtifactKind.CONCEPT_REGISTRY,
    ArtifactKind.ASSEMBLY,
    ArtifactKind.VIDEO_QA,
})


class RepairChangeKind(str, Enum):
    GEOMETRY_ONLY = "GEOMETRY_ONLY"
    STYLE_ONLY = "STYLE_ONLY"
    MOTION_ONLY = "MOTION_ONLY"
    NARRATION = "NARRATION"
    SCENEGRAPH_STRUCTURE = "SCENEGRAPH_STRUCTURE"


class RepairLevel(IntEnum):
    AUTO_FIX = 0
    NODE_PATCH = 1
    GROUP_LAYOUT_PATCH = 2
    SCENEGRAPH_RECOMPILE = 3
    SCENE_REGENERATION_REQUEST = 4
    FALLBACK = 5


REPAIR_PATCH_POLICY: MappingProxyType[CriticPatchOp, tuple[RepairLevel, RepairChangeKind, bool]] = MappingProxyType({
    CriticPatchOp.REWRAP_TEXT: (RepairLevel.AUTO_FIX, RepairChangeKind.GEOMETRY_ONLY, True),
    CriticPatchOp.SET_REGION: (RepairLevel.NODE_PATCH, RepairChangeKind.GEOMETRY_ONLY, False),
    CriticPatchOp.CHANGE_IMPORTANCE: (RepairLevel.NODE_PATCH, RepairChangeKind.GEOMETRY_ONLY, False),
    CriticPatchOp.SCALE_NODE: (RepairLevel.NODE_PATCH, RepairChangeKind.GEOMETRY_ONLY, True),
    CriticPatchOp.ADD_EMPHASIS: (RepairLevel.NODE_PATCH, RepairChangeKind.STYLE_ONLY, False),
    CriticPatchOp.REMOVE_DECORATION: (RepairLevel.NODE_PATCH, RepairChangeKind.STYLE_ONLY, False),
    CriticPatchOp.CHANGE_MOTION_STYLE: (RepairLevel.NODE_PATCH, RepairChangeKind.MOTION_ONLY, True),
    CriticPatchOp.REDUCE_MOTION: (RepairLevel.NODE_PATCH, RepairChangeKind.MOTION_ONLY, True),
    CriticPatchOp.INCREASE_GAP: (RepairLevel.GROUP_LAYOUT_PATCH, RepairChangeKind.GEOMETRY_ONLY, True),
    CriticPatchOp.DECREASE_GAP: (RepairLevel.GROUP_LAYOUT_PATCH, RepairChangeKind.GEOMETRY_ONLY, True),
    CriticPatchOp.CHANGE_LAYOUT_STRATEGY: (RepairLevel.GROUP_LAYOUT_PATCH, RepairChangeKind.GEOMETRY_ONLY, True),
    CriticPatchOp.SPLIT_GROUP: (RepairLevel.GROUP_LAYOUT_PATCH, RepairChangeKind.GEOMETRY_ONLY, True),
    CriticPatchOp.MERGE_GROUP: (RepairLevel.GROUP_LAYOUT_PATCH, RepairChangeKind.GEOMETRY_ONLY, True),
    CriticPatchOp.REROUTE_EDGE: (RepairLevel.GROUP_LAYOUT_PATCH, RepairChangeKind.GEOMETRY_ONLY, True),
    CriticPatchOp.CHANGE_EDGE_STYLE: (RepairLevel.GROUP_LAYOUT_PATCH, RepairChangeKind.STYLE_ONLY, False),
    CriticPatchOp.CHANGE_VISUAL_INTENT: (
        RepairLevel.SCENE_REGENERATION_REQUEST, RepairChangeKind.SCENEGRAPH_STRUCTURE, True
    ),
})


class ArtifactInputHash(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str = Field(..., min_length=1)
    content_hash: str

    @field_validator("artifact_id")
    @classmethod
    def _normalize_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise RepairInvalidInputError("artifact input ID cannot be blank")
        return value

    @field_validator("content_hash", mode="before")
    @classmethod
    def _validate_hash(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise RepairInvalidInputError("artifact input content_hash must be a string SHA-256 digest")
        value = value.strip().lower()
        if not _HASH_RE.fullmatch(value):
            raise RepairInvalidInputError("artifact input content_hash must be a lowercase SHA-256 hex digest")
        return value


class ArtifactRecord(BaseModel):
    """Deterministic artifact provenance record used for cache/invalidation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = V2_REPAIR_SCHEMA_VERSION
    artifact_id: str = Field(..., min_length=1)
    kind: ArtifactKind
    content_hash: str
    input_hashes: tuple[ArtifactInputHash, ...] = Field(default_factory=tuple)
    created_by_phase: str = Field(..., min_length=1)
    compiler_version: str = Field(..., min_length=1)
    scene_id: str | None = None
    transition_id: str | None = None
    from_scene_id: str | None = None
    to_scene_id: str | None = None

    @field_validator("artifact_id", "created_by_phase", "compiler_version")
    @classmethod
    def _normalize_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise RepairInvalidInputError("artifact provenance strings cannot be blank")
        return value

    @field_validator("scene_id", "transition_id", "from_scene_id", "to_scene_id")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise RepairInvalidInputError("artifact scope IDs cannot be blank")
        return value

    @field_validator("content_hash", mode="before")
    @classmethod
    def _validate_content_hash(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise RepairInvalidInputError("artifact content_hash must be a string SHA-256 digest")
        value = value.strip().lower()
        if not _HASH_RE.fullmatch(value):
            raise RepairInvalidInputError("artifact content_hash must be a lowercase SHA-256 hex digest")
        return value

    @field_validator("input_hashes", mode="before")
    @classmethod
    def _tupleize_inputs(cls, value: Any) -> tuple[Any, ...]:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _validate_record(self) -> "ArtifactRecord":
        validated_inputs = tuple(
            ArtifactInputHash.model_validate(item.model_dump(mode="json"))
            for item in self.input_hashes
        )
        object.__setattr__(self, "input_hashes", validated_inputs)
        ids = [item.artifact_id for item in validated_inputs]
        if len(ids) != len(set(ids)):
            raise RepairInvalidInputError("artifact input_hashes cannot contain duplicate artifact IDs")
        ordered = tuple(sorted(validated_inputs, key=lambda item: item.artifact_id))
        object.__setattr__(self, "input_hashes", ordered)

        if self.kind in SCENE_SCOPED_ARTIFACTS:
            if self.scene_id is None:
                raise RepairInvalidInputError(f"{self.kind.value} requires scene_id")
            if any(value is not None for value in (self.transition_id, self.from_scene_id, self.to_scene_id)):
                raise RepairInvalidInputError(f"{self.kind.value} cannot carry transition scope")
        elif self.kind in TRANSITION_SCOPED_ARTIFACTS:
            if self.transition_id is None or self.from_scene_id is None or self.to_scene_id is None:
                raise RepairInvalidInputError(f"{self.kind.value} requires transition_id/from_scene_id/to_scene_id")
            if self.scene_id is not None:
                raise RepairInvalidInputError(f"{self.kind.value} cannot carry scene_id")
            if self.from_scene_id == self.to_scene_id:
                raise RepairInvalidInputError("transition artifact endpoints must be different scenes")
        elif self.kind in GLOBAL_ARTIFACTS:
            if any(value is not None for value in (self.scene_id, self.transition_id, self.from_scene_id, self.to_scene_id)):
                raise RepairInvalidInputError(f"global artifact {self.kind.value} cannot carry scene/transition scope")
        return self

    def to_canonical_json(self) -> str:
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, payload: str) -> "ArtifactRecord":
        return cls.model_validate_json(payload)


class RepairBudgetState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    layout_solves: int = Field(default=0, ge=0, le=MAX_LAYOUT_SOLVES)
    vlm_repair_rounds: int = Field(default=0, ge=0, le=MAX_VLM_REPAIR_ROUNDS)
    scene_regenerations: int = Field(default=0, ge=0, le=MAX_SCENE_REGENERATIONS)

    @field_validator("layout_solves", "vlm_repair_rounds", "scene_regenerations", mode="before")
    @classmethod
    def _strict_int(cls, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise RepairInvalidInputError("repair counters must be strict integers")
        return value


class RepairAction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    patch_id: str = Field(..., min_length=1)
    op: CriticPatchOp
    patch: CriticPatchSuggestion
    level: RepairLevel
    change_kind: RepairChangeKind
    target_ids: tuple[str, ...] = Field(default_factory=tuple)
    deferred: bool = False

    @field_validator("patch_id")
    @classmethod
    def _normalize_patch_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise RepairInvalidInputError("repair patch_id cannot be blank")
        return value

    @field_validator("target_ids", mode="before")
    @classmethod
    def _normalize_target_ids(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple):
            raise RepairInvalidInputError("repair target_ids must be a tuple/list")
        normalized = tuple(item.strip() for item in value if isinstance(item, str))
        if len(normalized) != len(value) or any(not item for item in normalized):
            raise RepairInvalidInputError("repair target_ids must contain non-empty strings")
        if len(normalized) != len(set(normalized)):
            raise RepairInvalidInputError("repair target_ids cannot contain duplicates")
        return tuple(sorted(normalized))

    @field_validator("deferred", mode="before")
    @classmethod
    def _strict_deferred(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise RepairInvalidInputError("repair action deferred must be boolean")
        return value

    @model_validator(mode="after")
    def _validate_patch_identity(self) -> "RepairAction":
        validated_patch = CriticPatchSuggestion.model_validate(self.patch.model_dump(mode="json"))
        object.__setattr__(self, "patch", validated_patch)
        expected_targets = tuple(sorted(f"{target.kind.value}:{target.target_id}" for target in validated_patch.targets))
        if validated_patch.patch_id != self.patch_id or validated_patch.op != self.op or expected_targets != self.target_ids:
            raise RepairInvalidInputError("repair action identity must exactly match embedded critic patch")
        expected_policy = REPAIR_PATCH_POLICY.get(self.op)
        if expected_policy is None:
            raise RepairInvalidInputError(f"unsupported repair patch op '{self.op.value}'")
        if (self.level, self.change_kind, self.deferred) != expected_policy:
            raise RepairInvalidInputError("repair action level/change-kind/deferred flag contradicts CP2.13 policy")
        return self


class RepairPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = V2_REPAIR_SCHEMA_VERSION
    scene_id: str = Field(..., min_length=1)
    actions: tuple[RepairAction, ...] = Field(default_factory=tuple)
    max_level: RepairLevel = RepairLevel.AUTO_FIX
    requires_scene_regeneration: bool = False
    fallback_required: bool = False

    @field_validator("scene_id")
    @classmethod
    def _normalize_scene_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise RepairInvalidInputError("repair plan scene_id cannot be blank")
        return value

    @field_validator("actions", mode="before")
    @classmethod
    def _tupleize_actions(cls, value: Any) -> tuple[Any, ...]:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("requires_scene_regeneration", "fallback_required", mode="before")
    @classmethod
    def _strict_bool(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise RepairInvalidInputError("repair plan flags must be booleans")
        return value

    @model_validator(mode="after")
    def _validate_plan(self) -> "RepairPlan":
        validated_actions = tuple(RepairAction.model_validate(action.model_dump(mode="json")) for action in self.actions)
        ids = [action.patch_id for action in validated_actions]
        if len(ids) != len(set(ids)):
            raise RepairInvalidInputError("repair actions must have unique patch IDs")
        conflict_keys = [(action.op.value, action.target_ids) for action in validated_actions]
        if len(conflict_keys) != len(set(conflict_keys)):
            raise RepairInvalidInputError("repair plan cannot contain duplicate operations on the same typed targets")
        ordered = tuple(sorted(validated_actions, key=lambda action: action.patch_id))
        object.__setattr__(self, "actions", ordered)
        computed_max = max((action.level for action in ordered), default=RepairLevel.AUTO_FIX)
        if self.max_level != computed_max:
            raise RepairInvalidInputError("repair plan max_level must equal the maximum action level")
        if self.requires_scene_regeneration != (computed_max >= RepairLevel.SCENE_REGENERATION_REQUEST):
            raise RepairInvalidInputError("requires_scene_regeneration contradicts repair action levels")
        if self.fallback_required != (computed_max == RepairLevel.FALLBACK):
            raise RepairInvalidInputError("fallback_required contradicts repair action levels")
        return self

    def to_canonical_json(self) -> str:
        return canonical_json(self)


class ScenePatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = V2_REPAIR_SCHEMA_VERSION
    scene_id: str = Field(..., min_length=1)
    original_scene_hash: str
    repaired_scene_hash: str
    scene_graph: SceneGraph
    applied_patch_ids: tuple[str, ...] = Field(default_factory=tuple)
    deferred_patch_ids: tuple[str, ...] = Field(default_factory=tuple)
    noop_patch_ids: tuple[str, ...] = Field(default_factory=tuple)
    change_kinds: tuple[RepairChangeKind, ...] = Field(default_factory=tuple)

    @field_validator("scene_id")
    @classmethod
    def _normalize_patch_scene_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise RepairInvalidInputError("scene patch scene_id cannot be blank")
        return value

    @field_validator("original_scene_hash", "repaired_scene_hash", mode="before")
    @classmethod
    def _validate_hash(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise RepairInvalidInputError("scene patch hashes must be string SHA-256 digests")
        value = value.strip().lower()
        if not _HASH_RE.fullmatch(value):
            raise RepairInvalidInputError("scene patch hashes must be SHA-256 hex digests")
        return value

    @field_validator("applied_patch_ids", "deferred_patch_ids", "noop_patch_ids", mode="before")
    @classmethod
    def _normalize_ids(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple):
            raise RepairInvalidInputError("patch ID collections must be tuple/list")
        normalized = tuple(item.strip() for item in value if isinstance(item, str))
        if len(normalized) != len(value) or any(not item for item in normalized):
            raise RepairInvalidInputError("patch IDs must be non-empty strings")
        if len(normalized) != len(set(normalized)):
            raise RepairInvalidInputError("patch IDs cannot contain duplicates")
        return tuple(sorted(normalized))

    @field_validator("change_kinds", mode="before")
    @classmethod
    def _normalize_change_kinds(cls, value: Any) -> tuple[Any, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple):
            raise RepairInvalidInputError("change_kinds must be tuple/list")
        return value

    @model_validator(mode="after")
    def _validate_result(self) -> "ScenePatchResult":
        validated_graph = SceneGraph.model_validate(self.scene_graph.model_dump(mode="json"))
        object.__setattr__(self, "scene_graph", validated_graph)
        if validated_graph.scene_id != self.scene_id:
            raise RepairInvalidInputError("scene patch result scene_id must match SceneGraph")
        applied = set(self.applied_patch_ids)
        deferred = set(self.deferred_patch_ids)
        noop = set(self.noop_patch_ids)
        if (applied & deferred) or (applied & noop) or (deferred & noop):
            raise RepairInvalidInputError("a patch cannot be simultaneously applied, deferred, or no-op")
        expected_scene_hash = hashlib.sha256(("model\n" + canonical_json(validated_graph)).encode("utf-8")).hexdigest()
        if self.repaired_scene_hash != expected_scene_hash:
            raise RepairInvalidInputError("repaired_scene_hash must match the repaired SceneGraph content")
        normalized_kinds = tuple(sorted(set(self.change_kinds), key=lambda kind: kind.value))
        object.__setattr__(self, "change_kinds", normalized_kinds)
        changed = self.original_scene_hash != self.repaired_scene_hash
        if changed and (not self.applied_patch_ids or not normalized_kinds):
            raise RepairInvalidInputError("changed SceneGraph requires applied patches and concrete change_kinds")
        if not changed and (self.applied_patch_ids or normalized_kinds):
            raise RepairInvalidInputError("unchanged SceneGraph cannot claim applied patches or change_kinds")
        return self


class RepairVerificationResult(BaseModel):
    """Final fail-closed deterministic re-check for any repaired scene candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = V2_REPAIR_SCHEMA_VERSION
    scene_id: str = Field(..., min_length=1)
    repaired_scene_hash: str
    qa_input_scene_hash: str
    deterministic_report: DeterministicQAReport
    approved: bool

    @field_validator("scene_id")
    @classmethod
    def _normalize_verification_scene_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise RepairInvalidInputError("repair verification scene_id cannot be blank")
        return value

    @field_validator("repaired_scene_hash", "qa_input_scene_hash", mode="before")
    @classmethod
    def _validate_repaired_hash(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise RepairInvalidInputError("repair verification hash must be a string SHA-256 digest")
        value = value.strip().lower()
        if not _HASH_RE.fullmatch(value):
            raise RepairInvalidInputError("repair verification hash must be a SHA-256 hex digest")
        return value

    @field_validator("approved", mode="before")
    @classmethod
    def _strict_approved(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise RepairInvalidInputError("repair verification approved must be boolean")
        return value

    @model_validator(mode="after")
    def _validate_verification(self) -> "RepairVerificationResult":
        validated_report = DeterministicQAReport.model_validate(self.deterministic_report.model_dump(mode="json"))
        object.__setattr__(self, "deterministic_report", validated_report)
        if validated_report.scene_id != self.scene_id:
            raise RepairInvalidInputError("repair verification scene_id must match deterministic QA report")
        if self.qa_input_scene_hash != self.repaired_scene_hash:
            raise RepairInvalidInputError("deterministic re-check must be bound to the repaired scene hash")
        if self.approved != validated_report.passed:
            raise RepairInvalidInputError("repair approval must exactly equal deterministic re-check result")
        return self


class RepairPlanInvalidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = V2_REPAIR_SCHEMA_VERSION
    scene_id: str = Field(..., min_length=1)
    change_kinds: tuple[RepairChangeKind, ...] = Field(default_factory=tuple)
    root_artifact_ids: tuple[str, ...] = Field(default_factory=tuple)
    invalidated_artifact_ids: tuple[str, ...] = Field(default_factory=tuple)
    affected_transition_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("scene_id")
    @classmethod
    def _normalize_scene_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise RepairInvalidInputError("repair-plan invalidation scene_id cannot be blank")
        return value

    @field_validator("change_kinds", mode="before")
    @classmethod
    def _normalize_kinds(cls, value: Any) -> tuple[Any, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple):
            raise RepairInvalidInputError("repair-plan change_kinds must be tuple/list")
        return tuple(sorted(set(value), key=lambda kind: kind.value if isinstance(kind, RepairChangeKind) else str(kind)))

    @field_validator("root_artifact_ids", "invalidated_artifact_ids", "affected_transition_ids", mode="before")
    @classmethod
    def _normalize_ids(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple):
            raise RepairInvalidInputError("repair-plan invalidation IDs must be tuple/list")
        normalized = tuple(item.strip() for item in value if isinstance(item, str))
        if len(normalized) != len(value) or any(not item for item in normalized):
            raise RepairInvalidInputError("repair-plan invalidation IDs must be non-empty strings")
        return tuple(sorted(set(normalized)))

    @model_validator(mode="after")
    def _validate_plan_invalidation(self) -> "RepairPlanInvalidationResult":
        if not set(self.root_artifact_ids).issubset(set(self.invalidated_artifact_ids)):
            raise RepairInvalidInputError("repair-plan invalidation roots must be included in invalidated artifacts")
        return self


class InvalidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = V2_REPAIR_SCHEMA_VERSION
    scene_id: str = Field(..., min_length=1)
    change_kind: RepairChangeKind
    root_artifact_ids: tuple[str, ...] = Field(default_factory=tuple)
    invalidated_artifact_ids: tuple[str, ...] = Field(default_factory=tuple)
    affected_transition_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("scene_id")
    @classmethod
    def _normalize_invalidation_scene_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise RepairInvalidInputError("invalidation scene_id cannot be blank")
        return value

    @field_validator("root_artifact_ids", "invalidated_artifact_ids", "affected_transition_ids", mode="before")
    @classmethod
    def _normalize_ids(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple):
            raise RepairInvalidInputError("invalidation ID collections must be tuple/list")
        normalized = tuple(item.strip() for item in value if isinstance(item, str))
        if len(normalized) != len(value) or any(not item for item in normalized):
            raise RepairInvalidInputError("invalidation IDs must be non-empty strings")
        return tuple(sorted(set(normalized)))

    @model_validator(mode="after")
    def _validate_invalidation(self) -> "InvalidationResult":
        if not set(self.root_artifact_ids).issubset(set(self.invalidated_artifact_ids)):
            raise RepairInvalidInputError("invalidation roots must be included in invalidated_artifact_ids")
        return self
