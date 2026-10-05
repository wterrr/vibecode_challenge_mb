"""Critic response and quality-gate contracts for LearnFlow V2 CP2.12."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, ClassVar, Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.layout.schema import LayoutStrategy
from learnflow_v2.motion.enums import (
    MotionStyle, TIER_1_MOTION_GRAMMAR, TIER_2_3_RESERVED_STYLES, VERB_TARGET_KIND_MAP,
)
from learnflow_v2.qa.errors import QAInvalidInputError
from learnflow_v2.qa.schema import DeterministicQAReport
from learnflow_v2.scenegraph.enums import PreferredRegion
from learnflow_v2.qa._critic_context import (
    V2_CRITIC_SCHEMA_VERSION, QualityMode, CriticFailurePolicy, CriticStatus,
    CriticGateState, CriticIssueSeverity, CriticIssueType, CriticTargetKind,
    CriticTargetRef, CriticPatchOp, _finite,
)

class CriticIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    issue_id: str = Field(..., min_length=1, max_length=128)
    issue_type: CriticIssueType
    severity: CriticIssueSeverity
    targets: tuple[CriticTargetRef, ...] = Field(..., min_length=1)
    reason: str = Field(..., min_length=1, max_length=1000)

    @field_validator("issue_id")
    @classmethod
    def _normalize_issue_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise QAInvalidInputError("critic issue_id cannot be blank")
        return normalized

    @field_validator("targets", mode="before")
    @classmethod
    def _normalize_targets(cls, value: Any) -> tuple[Any, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple) or not value:
            raise QAInvalidInputError("critic issue targets must be a non-empty tuple/list")
        return value

    @model_validator(mode="after")
    def _validate_target_refs(self) -> "CriticIssue":
        identities = [(target.kind.value, target.target_id) for target in self.targets]
        if len(identities) != len(set(identities)):
            raise QAInvalidInputError("critic issue targets cannot contain duplicate typed identities")
        object.__setattr__(self, "targets", tuple(sorted(self.targets, key=lambda target: (target.kind.value, target.target_id))))
        return self

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str) -> str:
        if not value.strip():
            raise QAInvalidInputError("critic issue reason cannot be whitespace-only")
        return value.strip()


class CriticPatchSuggestion(BaseModel):
    """Whitelisted semantic suggestion only; CP2.12 never executes these patches."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    _STRICT_TARGET_KINDS: ClassVar[MappingProxyType] = MappingProxyType({
        CriticPatchOp.SET_REGION: frozenset({CriticTargetKind.NODE}),
        CriticPatchOp.CHANGE_LAYOUT_STRATEGY: frozenset({CriticTargetKind.SCENE}),
        CriticPatchOp.INCREASE_GAP: frozenset({CriticTargetKind.SCENE}),
        CriticPatchOp.DECREASE_GAP: frozenset({CriticTargetKind.SCENE}),
        CriticPatchOp.CHANGE_IMPORTANCE: frozenset({CriticTargetKind.NODE}),
        CriticPatchOp.SCALE_NODE: frozenset({CriticTargetKind.NODE}),
        CriticPatchOp.REWRAP_TEXT: frozenset({CriticTargetKind.NODE}),
        CriticPatchOp.SPLIT_GROUP: frozenset({CriticTargetKind.GROUP}),
        CriticPatchOp.MERGE_GROUP: frozenset({CriticTargetKind.GROUP}),
        CriticPatchOp.REROUTE_EDGE: frozenset({CriticTargetKind.RELATION}),
        CriticPatchOp.CHANGE_EDGE_STYLE: frozenset({CriticTargetKind.RELATION}),
        CriticPatchOp.ADD_EMPHASIS: frozenset({CriticTargetKind.NODE}),
    })
    patch_id: str = Field(..., min_length=1, max_length=128)
    op: CriticPatchOp
    targets: tuple[CriticTargetRef, ...] = Field(..., min_length=1)
    normalized_magnitude: float | None = None
    region: PreferredRegion | None = None
    layout_strategy: LayoutStrategy | None = None
    motion_style: MotionStyle | None = None
    semantic_value: str | None = Field(default=None, max_length=120)

    @field_validator("patch_id")
    @classmethod
    def _normalize_patch_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise QAInvalidInputError("critic patch_id cannot be blank")
        return normalized

    @field_validator("targets", mode="before")
    @classmethod
    def _normalize_targets(cls, value: Any) -> tuple[Any, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple) or not value:
            raise QAInvalidInputError("critic patch targets must be a non-empty tuple/list")
        return value

    @field_validator("normalized_magnitude", mode="before")
    @classmethod
    def _validate_magnitude(cls, value: Any) -> float | None:
        if value is None:
            return None
        return _finite(value, "normalized_magnitude", minimum=-1.0, maximum=1.0)

    @field_validator("semantic_value")
    @classmethod
    def _normalize_semantic_value(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise QAInvalidInputError("semantic_value cannot be blank")
        if any(ch in value for ch in ("\n", "\r", "\x00")):
            raise QAInvalidInputError("semantic_value must be a single safe semantic token/phrase")
        if not value[0].isalpha() or any(not (ch.isalnum() or ch in " _.-:") for ch in value):
            raise QAInvalidInputError("semantic_value may contain only semantic words/tokens, not code, coordinates, or commands")
        upper = value.upper().replace("-", "_")
        forbidden = (
            "SET_PIXEL", "PIXEL", "COORDINATE", "POSITION", "MOVE_TO",
            "EXECUTE_CODE", "WRITE_PYTHON", "FFMPEG", "MANIM", "PILLOW",
            "SHELL", "TERMINAL",
        )
        if any(token in upper for token in forbidden) or any(ch.isdigit() for ch in value):
            raise QAInvalidInputError(
                "semantic_value cannot encode renderer commands, executable code, or numeric/pixel coordinates"
            )
        return value

    @model_validator(mode="after")
    def _validate_op_parameters(self) -> "CriticPatchSuggestion":
        identities = [(target.kind.value, target.target_id) for target in self.targets]
        if len(identities) != len(set(identities)):
            raise QAInvalidInputError("critic patch targets cannot contain duplicate typed identities")
        object.__setattr__(self, "targets", tuple(sorted(self.targets, key=lambda target: (target.kind.value, target.target_id))))
        op = self.op
        expected: set[str] = set()
        if op == CriticPatchOp.SET_REGION:
            expected = {"region"}
        elif op == CriticPatchOp.CHANGE_LAYOUT_STRATEGY:
            expected = {"layout_strategy"}
        elif op in {
            CriticPatchOp.INCREASE_GAP,
            CriticPatchOp.DECREASE_GAP,
            CriticPatchOp.CHANGE_IMPORTANCE,
            CriticPatchOp.SCALE_NODE,
        }:
            expected = {"normalized_magnitude"}
        elif op == CriticPatchOp.CHANGE_MOTION_STYLE:
            expected = {"motion_style"}
        elif op in {CriticPatchOp.CHANGE_EDGE_STYLE, CriticPatchOp.CHANGE_VISUAL_INTENT}:
            expected = {"semantic_value"}

        present = {
            name
            for name, value in (
                ("normalized_magnitude", self.normalized_magnitude),
                ("region", self.region),
                ("layout_strategy", self.layout_strategy),
                ("motion_style", self.motion_style),
                ("semantic_value", self.semantic_value),
            )
            if value is not None
        }
        if present != expected:
            raise QAInvalidInputError(
                f"critic patch op '{op.value}' requires exactly {sorted(expected)}, got {sorted(present)}"
            )
        if self.normalized_magnitude is not None and self.normalized_magnitude == 0.0:
            raise QAInvalidInputError("normalized_magnitude cannot be zero")
        if op in {CriticPatchOp.INCREASE_GAP, CriticPatchOp.DECREASE_GAP, CriticPatchOp.CHANGE_IMPORTANCE}:
            if self.normalized_magnitude is None or self.normalized_magnitude <= 0.0:
                raise QAInvalidInputError(f"{op.value} requires positive normalized_magnitude")
        if self.motion_style in TIER_2_3_RESERVED_STYLES:
            raise QAInvalidInputError("critic cannot suggest unsupported Tier-2/Tier-3 motion style")

        if op == CriticPatchOp.SPLIT_GROUP and len(self.targets) != 1:
            raise QAInvalidInputError("SPLIT_GROUP requires exactly one GROUP target")
        if op == CriticPatchOp.MERGE_GROUP and len(self.targets) < 2:
            raise QAInvalidInputError("MERGE_GROUP requires at least two GROUP targets")

        allowed_target_kinds = self._STRICT_TARGET_KINDS.get(op)
        if allowed_target_kinds is not None:
            invalid = [target for target in self.targets if target.kind not in allowed_target_kinds]
            if invalid:
                expected_kinds = sorted(kind.value for kind in allowed_target_kinds)
                rendered = sorted(f"{target.kind.value}:{target.target_id}" for target in invalid)
                raise QAInvalidInputError(
                    f"critic patch op '{op.value}' requires target kind(s) {expected_kinds}; invalid targets={rendered}"
                )

        if op == CriticPatchOp.CHANGE_MOTION_STYLE and self.motion_style is not None:
            compatible_kinds = {
                VERB_TARGET_KIND_MAP[verb]
                for verb, styles in TIER_1_MOTION_GRAMMAR.items()
                if self.motion_style in styles
            }
            invalid = [target for target in self.targets if target.kind.value not in {kind.value for kind in compatible_kinds}]
            if invalid:
                expected_kinds = sorted(kind.value for kind in compatible_kinds)
                rendered = sorted(f"{target.kind.value}:{target.target_id}" for target in invalid)
                raise QAInvalidInputError(
                    f"motion style '{self.motion_style.value}' is incompatible with target kind(s); "
                    f"expected {expected_kinds}, invalid targets={rendered}"
                )
        return self


class CriticResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.1"] = V2_CRITIC_SCHEMA_VERSION
    status: CriticStatus
    issues: tuple[CriticIssue, ...] = Field(default_factory=tuple)
    patches: tuple[CriticPatchSuggestion, ...] = Field(default_factory=tuple)

    @field_validator("issues", "patches", mode="before")
    @classmethod
    def _tupleize(cls, value: Any) -> tuple[Any, ...]:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _validate_response(self) -> "CriticResponse":
        issue_ids = [item.issue_id for item in self.issues]
        patch_ids = [item.patch_id for item in self.patches]
        if len(issue_ids) != len(set(issue_ids)):
            raise QAInvalidInputError("critic response issue IDs must be unique")
        if len(patch_ids) != len(set(patch_ids)):
            raise QAInvalidInputError("critic response patch IDs must be unique")
        if self.status == CriticStatus.PASS and (self.issues or self.patches):
            raise QAInvalidInputError("critic PASS response cannot include issues or patches")
        if self.status == CriticStatus.REPAIR and (not self.issues or not self.patches):
            raise QAInvalidInputError("critic REPAIR response requires at least one issue and one patch suggestion")
        if self.status == CriticStatus.REPAIR:
            issue_targets = {
                (target.kind, target.target_id)
                for issue in self.issues
                for target in issue.targets
            }
            for patch in self.patches:
                patch_targets = {(target.kind, target.target_id) for target in patch.targets}
                has_scene_scope = any(kind == CriticTargetKind.SCENE for kind, _ in patch_targets)
                if not has_scene_scope and patch_targets.isdisjoint(issue_targets):
                    raise QAInvalidInputError(
                        f"critic patch '{patch.patch_id}' does not target any object implicated by critic issues"
                    )
        object.__setattr__(self, "issues", tuple(sorted(self.issues, key=lambda item: item.issue_id)))
        object.__setattr__(self, "patches", tuple(sorted(self.patches, key=lambda item: item.patch_id)))
        return self

    def to_canonical_json(self) -> str:
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, payload: str) -> "CriticResponse":
        return cls.model_validate_json(payload)


class QualityGateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.1"] = V2_CRITIC_SCHEMA_VERSION
    scene_id: str = Field(..., min_length=1)
    quality_mode: QualityMode
    failure_policy: CriticFailurePolicy
    deterministic_report: DeterministicQAReport
    critic_state: CriticGateState
    critic_response: CriticResponse | None = None
    approved: bool
    warnings: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("approved", mode="before")
    @classmethod
    def _validate_approved_strict(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise QAInvalidInputError("quality-gate approved must be a boolean")
        return value

    @field_validator("warnings", mode="before")
    @classmethod
    def _normalize_warnings(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple):
            raise QAInvalidInputError("quality-gate warnings must be tuple/list")
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise QAInvalidInputError("quality-gate warnings require non-empty strings")
        normalized = tuple(item.strip() for item in value)
        if len(normalized) != len(set(normalized)):
            raise QAInvalidInputError("quality-gate warnings cannot contain duplicates after normalization")
        return tuple(sorted(normalized))

    @model_validator(mode="after")
    def _validate_gate(self) -> "QualityGateResult":
        if self.scene_id != self.deterministic_report.scene_id:
            raise QAInvalidInputError("quality-gate scene_id must match deterministic report")
        if not self.deterministic_report.passed:
            if self.approved or self.critic_response is not None or self.critic_state != CriticGateState.SKIPPED_DETERMINISTIC_FAIL:
                raise QAInvalidInputError("deterministic QA failure must block approval and skip critic")
            if self.warnings:
                raise QAInvalidInputError("deterministic QA failure result cannot carry critic warnings")
            return self

        if self.quality_mode == QualityMode.DETERMINISTIC:
            if not self.approved or self.critic_state != CriticGateState.NOT_REQUESTED or self.critic_response is not None:
                raise QAInvalidInputError("deterministic quality mode must approve deterministic PASS without critic")
            if self.warnings:
                raise QAInvalidInputError("deterministic quality mode cannot carry critic warnings")
            return self

        if self.critic_state == CriticGateState.PASS:
            if not self.approved or self.critic_response is None or self.critic_response.status != CriticStatus.PASS:
                raise QAInvalidInputError("critic PASS state requires approved PASS response")
            if self.warnings:
                raise QAInvalidInputError("critic PASS state cannot carry failure warnings")
        elif self.critic_state == CriticGateState.REPAIR_REQUIRED:
            if self.approved or self.critic_response is None or self.critic_response.status != CriticStatus.REPAIR:
                raise QAInvalidInputError("critic REPAIR_REQUIRED state must block approval")
            if self.warnings:
                raise QAInvalidInputError("critic REPAIR_REQUIRED state cannot carry provider-failure warnings")
        elif self.critic_state in {
            CriticGateState.UNAVAILABLE,
            CriticGateState.TIMEOUT,
            CriticGateState.QUOTA_EXCEEDED,
            CriticGateState.PROVIDER_ERROR,
            CriticGateState.INVALID_RESPONSE,
        }:
            if self.critic_response is not None:
                raise QAInvalidInputError("critic failure state cannot carry a critic response")
            expected_approved = self.failure_policy == CriticFailurePolicy.CONTINUE
            if self.approved != expected_approved:
                raise QAInvalidInputError("critic failure approval contradicts configured failure policy")
            if not self.warnings:
                raise QAInvalidInputError("critic failure state requires an explicit warning")
        else:
            raise QAInvalidInputError(f"invalid critic state '{self.critic_state.value}' for critic quality mode")
        return self

    def to_canonical_json(self) -> str:
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, payload: str) -> "QualityGateResult":
        return cls.model_validate_json(payload)
