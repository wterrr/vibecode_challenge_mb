"""Video-critic response contracts for LearnFlow V2 CP2.14."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.videoqa.errors import VideoCriticInvalidInputError
from learnflow_v2.videoqa._video_context import (
    V2_VIDEO_CRITIC_SCHEMA_VERSION, REQUIRED_VIDEO_CRITIC_DIMENSIONS,
    ISSUE_DIMENSION, RECOMMENDATION_DIMENSION,
    VideoCriticDimension, VideoCriticStatus, VideoIssueSeverity, VideoIssueType,
    VideoRecommendationOp, VisualModality, _normalized_strings,
)
from learnflow_v2.videoqa._video_request import VideoCriticRequest

class VideoDimensionAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dimension: VideoCriticDimension
    passed: bool
    summary: str = Field(..., min_length=1, max_length=2000)

    @field_validator("passed", mode="before")
    @classmethod
    def _strict_passed(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise VideoCriticInvalidInputError("video dimension assessment passed must be boolean")
        return value

    @field_validator("summary")
    @classmethod
    def _normalize_summary(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise VideoCriticInvalidInputError("video dimension assessment summary cannot be blank")
        return value


class VideoCriticIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_id: str = Field(..., min_length=1)
    issue_type: VideoIssueType
    severity: VideoIssueSeverity
    scene_ids: tuple[str, ...] = Field(..., min_length=1)
    transition_ids: tuple[str, ...] = Field(default_factory=tuple)
    reason: str = Field(..., min_length=1, max_length=4000)

    @field_validator("issue_id", "reason")
    @classmethod
    def _normalize_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise VideoCriticInvalidInputError("video critic issue strings cannot be blank")
        return value

    @field_validator("scene_ids", "transition_ids", mode="before")
    @classmethod
    def _normalize_ids(cls, value: Any, info) -> tuple[str, ...]:
        return _normalized_strings(value, info.field_name)

    @model_validator(mode="after")
    def _validate_issue_shape(self) -> "VideoCriticIssue":
        if self.issue_type in {VideoIssueType.VISUAL_REPETITION, VideoIssueType.VISUAL_MODALITY_DIVERSITY, VideoIssueType.STYLE_INCONSISTENCY} and len(self.scene_ids) < 2:
            raise VideoCriticInvalidInputError(f"{self.issue_type.value} must identify at least two scenes")
        if self.issue_type == VideoIssueType.TRANSITION_CONTINUITY:
            if len(self.scene_ids) != 2 or len(self.transition_ids) != 1:
                raise VideoCriticInvalidInputError("TRANSITION_CONTINUITY must identify exactly two scenes and one transition")
        elif self.transition_ids:
            raise VideoCriticInvalidInputError("only TRANSITION_CONTINUITY issues may reference transition IDs")
        return self


class VideoCriticRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    recommendation_id: str = Field(..., min_length=1)
    op: VideoRecommendationOp
    scene_ids: tuple[str, ...] = Field(..., min_length=1)
    rationale: str = Field(..., min_length=1, max_length=4000)
    suggested_modality: VisualModality | None = None

    @field_validator("recommendation_id", "rationale")
    @classmethod
    def _normalize_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise VideoCriticInvalidInputError("video critic recommendation strings cannot be blank")
        return value

    @field_validator("scene_ids", mode="before")
    @classmethod
    def _normalize_scene_ids(cls, value: Any) -> tuple[str, ...]:
        return _normalized_strings(value, "recommendation scene_ids")

    @model_validator(mode="after")
    def _validate_parameters(self) -> "VideoCriticRecommendation":
        needs_modality = self.op == VideoRecommendationOp.CHANGE_VISUAL_MODALITY
        if needs_modality != (self.suggested_modality is not None):
            raise VideoCriticInvalidInputError("CHANGE_VISUAL_MODALITY requires suggested_modality and other ops must not set it")
        return self


class VideoCriticResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = V2_VIDEO_CRITIC_SCHEMA_VERSION
    status: VideoCriticStatus
    dimension_assessments: tuple[VideoDimensionAssessment, ...]
    issues: tuple[VideoCriticIssue, ...] = Field(default_factory=tuple)
    recommendations: tuple[VideoCriticRecommendation, ...] = Field(default_factory=tuple)

    @field_validator("dimension_assessments", "issues", "recommendations", mode="before")
    @classmethod
    def _tupleize(cls, value: Any, info) -> tuple[Any, ...]:
        if isinstance(value, list):
            return tuple(value)
        if not isinstance(value, tuple):
            raise VideoCriticInvalidInputError(f"{info.field_name} must be a tuple/list")
        return value

    @model_validator(mode="after")
    def _validate_response(self) -> "VideoCriticResponse":
        validated_assessments = tuple(
            VideoDimensionAssessment.model_validate(item.model_dump(mode="json")) for item in self.dimension_assessments
        )
        dimensions = [item.dimension for item in validated_assessments]
        if len(dimensions) != len(REQUIRED_VIDEO_CRITIC_DIMENSIONS) or set(dimensions) != set(REQUIRED_VIDEO_CRITIC_DIMENSIONS):
            raise VideoCriticInvalidInputError("video critic response must assess all five required dimensions exactly once")
        validated_issues = tuple(VideoCriticIssue.model_validate(item.model_dump(mode="json")) for item in self.issues)
        validated_recommendations = tuple(
            VideoCriticRecommendation.model_validate(item.model_dump(mode="json")) for item in self.recommendations
        )
        issue_ids = [item.issue_id for item in validated_issues]
        recommendation_ids = [item.recommendation_id for item in validated_recommendations]
        if len(issue_ids) != len(set(issue_ids)):
            raise VideoCriticInvalidInputError("video critic issue IDs must be unique")
        if len(recommendation_ids) != len(set(recommendation_ids)):
            raise VideoCriticInvalidInputError("video critic recommendation IDs must be unique")
        failed_dimensions = {assessment.dimension for assessment in validated_assessments if not assessment.passed}
        if self.status == VideoCriticStatus.PASS:
            if validated_issues or validated_recommendations:
                raise VideoCriticInvalidInputError("video critic PASS cannot include issues/recommendations")
            if failed_dimensions:
                raise VideoCriticInvalidInputError("video critic PASS requires every dimension assessment to pass")
        if self.status == VideoCriticStatus.REVIEW_REQUIRED:
            if not validated_issues or not validated_recommendations:
                raise VideoCriticInvalidInputError("video critic REVIEW_REQUIRED needs issues and recommendations")
            if not failed_dimensions:
                raise VideoCriticInvalidInputError("video critic REVIEW_REQUIRED requires at least one failed dimension assessment")
            issue_dimensions = {ISSUE_DIMENSION[issue.issue_type] for issue in validated_issues}
            if issue_dimensions != failed_dimensions:
                missing = sorted(item.value for item in failed_dimensions - issue_dimensions)
                extra = sorted(item.value for item in issue_dimensions - failed_dimensions)
                raise VideoCriticInvalidInputError(
                    f"failed dimension assessments must exactly match issue dimensions; missing={missing}, extra={extra}"
                )
        if self.status == VideoCriticStatus.REVIEW_REQUIRED:
            implicated = {scene_id for issue in validated_issues for scene_id in issue.scene_ids}
            for recommendation in validated_recommendations:
                if set(recommendation.scene_ids).isdisjoint(implicated):
                    raise VideoCriticInvalidInputError(
                        f"recommendation '{recommendation.recommendation_id}' does not target any implicated scene"
                    )
                dimension = RECOMMENDATION_DIMENSION[recommendation.op]
                matching = [
                    issue for issue in validated_issues
                    if ISSUE_DIMENSION[issue.issue_type] == dimension
                    and not set(issue.scene_ids).isdisjoint(recommendation.scene_ids)
                ]
                if not matching:
                    raise VideoCriticInvalidInputError(
                        f"recommendation '{recommendation.recommendation_id}' has no matching issue dimension on its target scenes"
                    )
            for issue in validated_issues:
                dimension = ISSUE_DIMENSION[issue.issue_type]
                matching = [
                    recommendation for recommendation in validated_recommendations
                    if RECOMMENDATION_DIMENSION[recommendation.op] == dimension
                    and not set(recommendation.scene_ids).isdisjoint(issue.scene_ids)
                ]
                if not matching:
                    raise VideoCriticInvalidInputError(
                        f"issue '{issue.issue_id}' has no recommendation for its dimension/scene scope"
                    )
        object.__setattr__(self, "dimension_assessments", tuple(sorted(validated_assessments, key=lambda item: item.dimension.value)))
        object.__setattr__(self, "issues", tuple(sorted(validated_issues, key=lambda item: item.issue_id)))
        object.__setattr__(self, "recommendations", tuple(sorted(validated_recommendations, key=lambda item: item.recommendation_id)))
        return self

    def to_canonical_json(self) -> str:
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, payload: str) -> "VideoCriticResponse":
        return cls.model_validate_json(payload)


def validate_video_critic_response_scope(response: VideoCriticResponse, request: VideoCriticRequest) -> None:
    scene_ids = {scene.scene_id for scene in request.scenes}
    transition_map = {transition.transition_id: transition for transition in request.transitions}
    for issue in response.issues:
        unknown_scenes = set(issue.scene_ids) - scene_ids
        if unknown_scenes:
            raise VideoCriticInvalidInputError(
                f"video issue '{issue.issue_id}' references unknown scenes {sorted(unknown_scenes)}"
            )
        unknown_transitions = set(issue.transition_ids) - set(transition_map)
        if unknown_transitions:
            raise VideoCriticInvalidInputError(
                f"video issue '{issue.issue_id}' references unknown transitions {sorted(unknown_transitions)}"
            )
        if issue.issue_type == VideoIssueType.TRANSITION_CONTINUITY:
            transition = transition_map[issue.transition_ids[0]]
            expected = {transition.from_scene_id, transition.to_scene_id}
            if set(issue.scene_ids) != expected:
                raise VideoCriticInvalidInputError(
                    f"continuity issue '{issue.issue_id}' must point to the two scenes adjacent to transition '{transition.transition_id}'"
                )
    for recommendation in response.recommendations:
        unknown = set(recommendation.scene_ids) - scene_ids
        if unknown:
            raise VideoCriticInvalidInputError(
                f"video recommendation '{recommendation.recommendation_id}' references unknown scenes {sorted(unknown)}"
            )


