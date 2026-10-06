"""Immutable public contracts for LearnFlow V2 CP2.14 Video Critic."""

from __future__ import annotations

from enum import Enum
import hashlib
import math
import re
from types import MappingProxyType
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.videoqa.errors import VideoCriticInvalidInputError

V2_VIDEO_CRITIC_SCHEMA_VERSION = "2.1"
_DURATION_TOLERANCE = 1e-6


class VideoCriticFailurePolicy(str, Enum):
    CONTINUE = "CONTINUE"
    STRICT = "STRICT"


class VideoCriticStatus(str, Enum):
    PASS = "PASS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class VideoCriticGateState(str, Enum):
    PASS = "PASS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    UNAVAILABLE = "UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    INVALID_RESPONSE = "INVALID_RESPONSE"


class VideoCriticDimension(str, Enum):
    VISUAL_VARIETY = "VISUAL_VARIETY"
    CONTINUITY = "CONTINUITY"
    STYLE = "STYLE"
    PACING = "PACING"
    PEDAGOGICAL_ALIGNMENT = "PEDAGOGICAL_ALIGNMENT"


REQUIRED_VIDEO_CRITIC_DIMENSIONS = (
    VideoCriticDimension.VISUAL_VARIETY,
    VideoCriticDimension.CONTINUITY,
    VideoCriticDimension.STYLE,
    VideoCriticDimension.PACING,
    VideoCriticDimension.PEDAGOGICAL_ALIGNMENT,
)


class VideoIssueSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class VideoIssueType(str, Enum):
    VISUAL_REPETITION = "VISUAL_REPETITION"
    VISUAL_MODALITY_DIVERSITY = "VISUAL_MODALITY_DIVERSITY"
    SCENE_RHYTHM = "SCENE_RHYTHM"
    STYLE_INCONSISTENCY = "STYLE_INCONSISTENCY"
    TRANSITION_CONTINUITY = "TRANSITION_CONTINUITY"
    CONCEPT_PROGRESSION = "CONCEPT_PROGRESSION"
    PACING = "PACING"
    NARRATION_REDUNDANCY = "NARRATION_REDUNDANCY"
    PEDAGOGICAL_ALIGNMENT = "PEDAGOGICAL_ALIGNMENT"


ISSUE_DIMENSION = MappingProxyType({
    VideoIssueType.VISUAL_REPETITION: VideoCriticDimension.VISUAL_VARIETY,
    VideoIssueType.VISUAL_MODALITY_DIVERSITY: VideoCriticDimension.VISUAL_VARIETY,
    VideoIssueType.SCENE_RHYTHM: VideoCriticDimension.PACING,
    VideoIssueType.STYLE_INCONSISTENCY: VideoCriticDimension.STYLE,
    VideoIssueType.TRANSITION_CONTINUITY: VideoCriticDimension.CONTINUITY,
    VideoIssueType.CONCEPT_PROGRESSION: VideoCriticDimension.PEDAGOGICAL_ALIGNMENT,
    VideoIssueType.PACING: VideoCriticDimension.PACING,
    VideoIssueType.NARRATION_REDUNDANCY: VideoCriticDimension.PEDAGOGICAL_ALIGNMENT,
    VideoIssueType.PEDAGOGICAL_ALIGNMENT: VideoCriticDimension.PEDAGOGICAL_ALIGNMENT,
})


class VisualModality(str, Enum):
    DIAGRAM = "DIAGRAM"
    ILLUSTRATION = "ILLUSTRATION"
    COMPARISON = "COMPARISON"
    EQUATION = "EQUATION"
    CHART = "CHART"
    CODE = "CODE"
    IMAGE = "IMAGE"
    TIMELINE = "TIMELINE"
    CONCEPT_CARD = "CONCEPT_CARD"
    OTHER = "OTHER"


class VideoRecommendationOp(str, Enum):
    VARY_VISUAL_MODALITY = "VARY_VISUAL_MODALITY"
    CHANGE_VISUAL_MODALITY = "CHANGE_VISUAL_MODALITY"
    ALIGN_STYLE = "ALIGN_STYLE"
    FIX_CONTINUITY = "FIX_CONTINUITY"
    ADJUST_PACING = "ADJUST_PACING"
    REDUCE_NARRATION_REDUNDANCY = "REDUCE_NARRATION_REDUNDANCY"
    IMPROVE_CONCEPT_PROGRESSION = "IMPROVE_CONCEPT_PROGRESSION"
    IMPROVE_PEDAGOGICAL_ALIGNMENT = "IMPROVE_PEDAGOGICAL_ALIGNMENT"


RECOMMENDATION_DIMENSION = MappingProxyType({
    VideoRecommendationOp.VARY_VISUAL_MODALITY: VideoCriticDimension.VISUAL_VARIETY,
    VideoRecommendationOp.CHANGE_VISUAL_MODALITY: VideoCriticDimension.VISUAL_VARIETY,
    VideoRecommendationOp.ALIGN_STYLE: VideoCriticDimension.STYLE,
    VideoRecommendationOp.FIX_CONTINUITY: VideoCriticDimension.CONTINUITY,
    VideoRecommendationOp.ADJUST_PACING: VideoCriticDimension.PACING,
    VideoRecommendationOp.REDUCE_NARRATION_REDUNDANCY: VideoCriticDimension.PEDAGOGICAL_ALIGNMENT,
    VideoRecommendationOp.IMPROVE_CONCEPT_PROGRESSION: VideoCriticDimension.PEDAGOGICAL_ALIGNMENT,
    VideoRecommendationOp.IMPROVE_PEDAGOGICAL_ALIGNMENT: VideoCriticDimension.PEDAGOGICAL_ALIGNMENT,
})


def _strict_finite(value: Any, label: str, *, minimum: float = 0.0, allow_equal: bool = True) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VideoCriticInvalidInputError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise VideoCriticInvalidInputError(f"{label} must be finite")
    if allow_equal:
        if result < minimum:
            raise VideoCriticInvalidInputError(f"{label} must be >= {minimum}")
    elif result <= minimum:
        raise VideoCriticInvalidInputError(f"{label} must be > {minimum}")
    return result


def _normalized_strings(value: Any, label: str) -> tuple[str, ...]:
    if isinstance(value, list):
        value = tuple(value)
    if not isinstance(value, tuple):
        raise VideoCriticInvalidInputError(f"{label} must be a tuple/list")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise VideoCriticInvalidInputError(f"{label} must contain non-empty strings")
        normalized.append(item.strip())
    if len(normalized) != len(set(normalized)):
        raise VideoCriticInvalidInputError(f"{label} cannot contain duplicates")
    return tuple(sorted(normalized))


class VideoSceneSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scene_id: str = Field(..., min_length=1)
    ordinal: int = Field(..., ge=0)
    duration: float = Field(..., gt=0.0)
    narration: str = Field(..., min_length=1, max_length=20000)
    visual_modality: VisualModality
    style_signature: tuple[str, ...] = Field(default_factory=tuple)
    concept_keys: tuple[str, ...] = Field(default_factory=tuple)
    learning_objective_ids: tuple[str, ...] = Field(default_factory=tuple)
    representative_frame_ref: str = Field(..., min_length=1)
    scene_quality_approved: bool
    quality_artifact_id: str = Field(..., min_length=1)
    quality_artifact_hash: str

    @field_validator("scene_id", "representative_frame_ref", "quality_artifact_id")
    @classmethod
    def _normalize_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise VideoCriticInvalidInputError("scene summary required strings cannot be blank")
        return value

    @field_validator("narration")
    @classmethod
    def _normalize_narration(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise VideoCriticInvalidInputError("scene narration cannot be whitespace-only")
        return value

    @field_validator("ordinal", mode="before")
    @classmethod
    def _strict_ordinal(cls, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise VideoCriticInvalidInputError("scene ordinal must be a strict integer")
        return value

    @field_validator("duration", mode="before")
    @classmethod
    def _validate_duration(cls, value: Any) -> float:
        return _strict_finite(value, "scene duration", minimum=0.0, allow_equal=False)

    @field_validator("scene_quality_approved", mode="before")
    @classmethod
    def _strict_quality_approved(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise VideoCriticInvalidInputError("scene_quality_approved must be boolean")
        return value

    @field_validator("quality_artifact_hash", mode="before")
    @classmethod
    def _validate_quality_hash(cls, value: Any) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value.strip().lower()):
            raise VideoCriticInvalidInputError("quality_artifact_hash must be a lowercase SHA-256 digest")
        return value.strip().lower()

    @field_validator("style_signature", "concept_keys", "learning_objective_ids", mode="before")
    @classmethod
    def _normalize_string_collections(cls, value: Any, info) -> tuple[str, ...]:
        return _normalized_strings(value, info.field_name)

    @model_validator(mode="after")
    def _validate_critic_evidence(self) -> "VideoSceneSummary":
        if not self.style_signature:
            raise VideoCriticInvalidInputError("video scene summary requires style_signature for cross-scene style review")
        if not self.learning_objective_ids:
            raise VideoCriticInvalidInputError("video scene summary requires learning_objective_ids for pedagogical alignment")
        return self


class VideoTransitionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    transition_id: str = Field(..., min_length=1)
    from_scene_id: str = Field(..., min_length=1)
    to_scene_id: str = Field(..., min_length=1)
    duration: float = Field(default=0.0, ge=0.0)
    effective_operation: str = Field(..., min_length=1)
    fallback_reason: str | None = None
    persistent_semantic_keys: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("transition_id", "from_scene_id", "to_scene_id", "effective_operation")
    @classmethod
    def _normalize_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise VideoCriticInvalidInputError("transition summary required strings cannot be blank")
        return value

    @field_validator("fallback_reason")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise VideoCriticInvalidInputError("fallback_reason cannot be whitespace-only")
        return value

    @field_validator("duration", mode="before")
    @classmethod
    def _validate_duration(cls, value: Any) -> float:
        return _strict_finite(value, "transition duration", minimum=0.0, allow_equal=True)

    @field_validator("persistent_semantic_keys", mode="before")
    @classmethod
    def _normalize_keys(cls, value: Any) -> tuple[str, ...]:
        return _normalized_strings(value, "persistent_semantic_keys")

    @model_validator(mode="after")
    def _validate_endpoints(self) -> "VideoTransitionSummary":
        if self.from_scene_id == self.to_scene_id:
            raise VideoCriticInvalidInputError("transition endpoints must be different scenes")
        return self
