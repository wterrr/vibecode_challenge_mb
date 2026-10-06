"""Video-critic request contract for LearnFlow V2 CP2.14."""

from __future__ import annotations

import re
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.videoqa.errors import VideoCriticInvalidInputError
from learnflow_v2.videoqa._video_context import (
    V2_VIDEO_CRITIC_SCHEMA_VERSION, REQUIRED_VIDEO_CRITIC_DIMENSIONS,
    VideoCriticDimension, VideoSceneSummary, VideoTransitionSummary, _strict_finite, _normalized_strings, _DURATION_TOLERANCE,
)

class VideoCriticRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = V2_VIDEO_CRITIC_SCHEMA_VERSION
    video_id: str = Field(..., min_length=1)
    final_video_ref: str = Field(..., min_length=1)
    video_artifact_hash: str
    lesson_goal: str = Field(..., min_length=1, max_length=20000)
    lesson_objective_ids: tuple[str, ...] = Field(default_factory=tuple)
    total_duration: float = Field(..., gt=0.0)
    dimensions: tuple[VideoCriticDimension, ...] = REQUIRED_VIDEO_CRITIC_DIMENSIONS
    scenes: tuple[VideoSceneSummary, ...] = Field(..., min_length=2)
    transitions: tuple[VideoTransitionSummary, ...]

    @field_validator("video_id", "final_video_ref", "lesson_goal")
    @classmethod
    def _normalize_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise VideoCriticInvalidInputError("video critic request required strings cannot be blank")
        return value

    @field_validator("total_duration", mode="before")
    @classmethod
    def _validate_total_duration(cls, value: Any) -> float:
        return _strict_finite(value, "video total_duration", minimum=0.0, allow_equal=False)

    @field_validator("video_artifact_hash", mode="before")
    @classmethod
    def _validate_video_hash(cls, value: Any) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value.strip().lower()):
            raise VideoCriticInvalidInputError("video_artifact_hash must be a lowercase SHA-256 digest")
        return value.strip().lower()

    @field_validator("lesson_objective_ids", mode="before")
    @classmethod
    def _normalize_objective_ids(cls, value: Any) -> tuple[str, ...]:
        return _normalized_strings(value, "lesson_objective_ids")

    @field_validator("dimensions", "scenes", "transitions", mode="before")
    @classmethod
    def _tupleize(cls, value: Any, info) -> tuple[Any, ...]:
        if isinstance(value, list):
            return tuple(value)
        if not isinstance(value, tuple):
            raise VideoCriticInvalidInputError(f"{info.field_name} must be a tuple/list")
        return value

    @model_validator(mode="after")
    def _validate_request(self) -> "VideoCriticRequest":
        if set(self.dimensions) != set(REQUIRED_VIDEO_CRITIC_DIMENSIONS) or len(self.dimensions) != len(REQUIRED_VIDEO_CRITIC_DIMENSIONS):
            raise VideoCriticInvalidInputError("CP2.14 request must cover all five required video-critic dimensions exactly once")

        if not self.lesson_objective_ids:
            raise VideoCriticInvalidInputError("video critic request requires lesson_objective_ids for pedagogical alignment")
        validated_scenes = tuple(VideoSceneSummary.model_validate(item.model_dump(mode="json")) for item in self.scenes)
        validated_transitions = tuple(VideoTransitionSummary.model_validate(item.model_dump(mode="json")) for item in self.transitions)
        lesson_objectives = set(self.lesson_objective_ids)
        covered_objectives: set[str] = set()
        for scene in validated_scenes:
            unknown = set(scene.learning_objective_ids) - lesson_objectives
            if unknown:
                raise VideoCriticInvalidInputError(
                    f"scene '{scene.scene_id}' references unknown lesson objectives {sorted(unknown)}"
                )
            covered_objectives.update(scene.learning_objective_ids)
        if covered_objectives != lesson_objectives:
            missing = sorted(lesson_objectives - covered_objectives)
            raise VideoCriticInvalidInputError(f"lesson objectives must be covered by at least one scene; missing={missing}")
        scene_ids = [scene.scene_id for scene in validated_scenes]
        ordinals = [scene.ordinal for scene in validated_scenes]
        quality_ids = [scene.quality_artifact_id for scene in validated_scenes]
        frame_refs = [scene.representative_frame_ref for scene in validated_scenes]
        if len(scene_ids) != len(set(scene_ids)):
            raise VideoCriticInvalidInputError("video critic scene IDs must be unique")
        if len(ordinals) != len(set(ordinals)):
            raise VideoCriticInvalidInputError("video critic scene ordinals must be unique")
        if len(quality_ids) != len(set(quality_ids)):
            raise VideoCriticInvalidInputError("scene quality artifact IDs must be unique")
        if len(frame_refs) != len(set(frame_refs)):
            raise VideoCriticInvalidInputError("representative frame refs must be unique per scene")
        if any(not scene.scene_quality_approved for scene in validated_scenes):
            raise VideoCriticInvalidInputError("video critic may run only after every scene is quality-approved")

        ordered_scenes = tuple(sorted(validated_scenes, key=lambda scene: scene.ordinal))
        if [scene.ordinal for scene in ordered_scenes] != list(range(len(ordered_scenes))):
            raise VideoCriticInvalidInputError("scene ordinals must form contiguous sequence 0..N-1")

        transition_ids = [transition.transition_id for transition in validated_transitions]
        if len(transition_ids) != len(set(transition_ids)):
            raise VideoCriticInvalidInputError("video transition IDs must be unique")
        expected_pairs = [(ordered_scenes[i].scene_id, ordered_scenes[i + 1].scene_id) for i in range(len(ordered_scenes) - 1)]
        actual_by_pair: dict[tuple[str, str], VideoTransitionSummary] = {}
        for transition in validated_transitions:
            pair = (transition.from_scene_id, transition.to_scene_id)
            if pair in actual_by_pair:
                raise VideoCriticInvalidInputError(f"duplicate transition for scene pair {pair}")
            actual_by_pair[pair] = transition
        if set(actual_by_pair) != set(expected_pairs):
            missing = sorted(set(expected_pairs) - set(actual_by_pair))
            extra = sorted(set(actual_by_pair) - set(expected_pairs))
            raise VideoCriticInvalidInputError(f"video transitions must exactly cover adjacent scenes; missing={missing}, extra={extra}")
        ordered_transitions = tuple(actual_by_pair[pair] for pair in expected_pairs)

        expected_duration = sum(scene.duration for scene in ordered_scenes) + sum(item.duration for item in ordered_transitions)
        if abs(self.total_duration - expected_duration) > _DURATION_TOLERANCE:
            raise VideoCriticInvalidInputError(
                f"video total_duration must equal scene+transition durations; expected={expected_duration:.6f}, got={self.total_duration:.6f}"
            )

        object.__setattr__(self, "dimensions", REQUIRED_VIDEO_CRITIC_DIMENSIONS)
        object.__setattr__(self, "scenes", ordered_scenes)
        object.__setattr__(self, "transitions", ordered_transitions)
        return self

    def to_canonical_json(self) -> str:
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, payload: str) -> "VideoCriticRequest":
        return cls.model_validate_json(payload)
