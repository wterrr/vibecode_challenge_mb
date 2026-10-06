"""Video-critic result contract for LearnFlow V2 CP2.14."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.videoqa.errors import VideoCriticInvalidInputError
from learnflow_v2.videoqa._video_context import (
    V2_VIDEO_CRITIC_SCHEMA_VERSION, VideoCriticFailurePolicy, VideoCriticGateState, _normalized_strings,
)
from learnflow_v2.videoqa._video_request import VideoCriticRequest
from learnflow_v2.videoqa._video_response import (
    VideoCriticResponse, VideoCriticStatus, validate_video_critic_response_scope,
)

class VideoCriticResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = V2_VIDEO_CRITIC_SCHEMA_VERSION
    video_id: str = Field(..., min_length=1)
    request: VideoCriticRequest
    request_hash: str
    failure_policy: VideoCriticFailurePolicy
    state: VideoCriticGateState
    response: VideoCriticResponse | None = None
    approved: bool
    warnings: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("video_id")
    @classmethod
    def _normalize_video_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise VideoCriticInvalidInputError("video critic result video_id cannot be blank")
        return value

    @field_validator("request_hash")
    @classmethod
    def _validate_request_hash(cls, value: str) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value.strip().lower()):
            raise VideoCriticInvalidInputError("request_hash must be a lowercase SHA-256 digest")
        return value.strip().lower()

    @field_validator("approved", mode="before")
    @classmethod
    def _strict_approved(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise VideoCriticInvalidInputError("video critic approved must be boolean")
        return value

    @field_validator("warnings", mode="before")
    @classmethod
    def _normalize_warnings(cls, value: Any) -> tuple[str, ...]:
        return _normalized_strings(value, "video critic warnings")

    @model_validator(mode="after")
    def _validate_result(self) -> "VideoCriticResult":
        validated_request = VideoCriticRequest.model_validate(self.request.model_dump(mode="json"))
        object.__setattr__(self, "request", validated_request)
        if self.video_id != validated_request.video_id:
            raise VideoCriticInvalidInputError("video critic result video_id must match request")
        expected_hash = hashlib.sha256(canonical_json(validated_request).encode("utf-8")).hexdigest()
        if self.request_hash != expected_hash:
            raise VideoCriticInvalidInputError("video critic result request_hash must match embedded request")
        if self.response is not None:
            validated_response = VideoCriticResponse.model_validate(self.response.model_dump(mode="json"))
            validate_video_critic_response_scope(validated_response, validated_request)
            object.__setattr__(self, "response", validated_response)
        if self.state == VideoCriticGateState.PASS:
            if not self.approved or self.response is None or self.response.status != VideoCriticStatus.PASS or self.warnings:
                raise VideoCriticInvalidInputError("video critic PASS state requires an approved PASS response without warnings")
        elif self.state == VideoCriticGateState.REVIEW_REQUIRED:
            if self.approved or self.response is None or self.response.status != VideoCriticStatus.REVIEW_REQUIRED or self.warnings:
                raise VideoCriticInvalidInputError("REVIEW_REQUIRED must block approval with a structured review response")
        elif self.state in {
            VideoCriticGateState.UNAVAILABLE,
            VideoCriticGateState.TIMEOUT,
            VideoCriticGateState.QUOTA_EXCEEDED,
            VideoCriticGateState.PROVIDER_ERROR,
            VideoCriticGateState.INVALID_RESPONSE,
        }:
            if self.response is not None:
                raise VideoCriticInvalidInputError("video critic failure state cannot include a response")
            expected = self.failure_policy == VideoCriticFailurePolicy.CONTINUE
            if self.approved != expected:
                raise VideoCriticInvalidInputError("video critic failure approval contradicts failure policy")
            if not self.warnings:
                raise VideoCriticInvalidInputError("video critic failure state requires a warning")
        else:
            raise VideoCriticInvalidInputError(f"unsupported video critic state '{self.state.value}'")
        return self

    def to_canonical_json(self) -> str:
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, payload: str) -> "VideoCriticResult":
        return cls.model_validate_json(payload)
