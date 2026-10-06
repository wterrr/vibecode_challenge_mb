"""Immutable render artifacts for LearnFlow V2 deterministic renderer."""

from __future__ import annotations

from enum import Enum
import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.render.errors import RenderInvalidInputError

V2_RENDER_SCHEMA_VERSION = "2.1"


class RenderArtifactKind(str, Enum):
    SCENE = "SCENE"
    TRANSITION = "TRANSITION"
    VIDEO = "VIDEO"


class RenderProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_id: str = Field(..., min_length=1)
    fps: int = Field(default=30, ge=1, le=120)
    crf: int = Field(default=18, ge=0, le=51)
    preset: str = Field(default="medium", min_length=1)

    @field_validator("fps", "crf", mode="before")
    @classmethod
    def _strict_int(cls, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise RenderInvalidInputError("fps/crf must be strict integers")
        return value

    @field_validator("profile_id", "preset")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise RenderInvalidInputError("render profile strings cannot be blank")
        return value


class SubtitleRenderCue(BaseModel):
    """Renderer-neutral subtitle cue consumed by the deterministic FFmpeg backend."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    start_seconds: float = Field(..., ge=0.0)
    end_seconds: float = Field(..., gt=0.0)
    text: str = Field(..., min_length=1, max_length=4000)

    @field_validator("start_seconds", "end_seconds", mode="before")
    @classmethod
    def _finite_time(cls, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RenderInvalidInputError("subtitle times must be finite numbers")
        result = float(value)
        if not math.isfinite(result) or result < 0.0:
            raise RenderInvalidInputError("subtitle times must be finite and non-negative")
        return result

    @field_validator("text")
    @classmethod
    def _normalize_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise RenderInvalidInputError("subtitle text cannot be blank")
        return value

    @model_validator(mode="after")
    def _validate_interval(self) -> "SubtitleRenderCue":
        if self.end_seconds <= self.start_seconds:
            raise RenderInvalidInputError("subtitle end_seconds must be greater than start_seconds")
        return self


class RenderedArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = V2_RENDER_SCHEMA_VERSION
    artifact_id: str = Field(..., min_length=1)
    kind: RenderArtifactKind
    path: str = Field(..., min_length=1)
    duration: float = Field(..., gt=0.0)
    width: int = Field(..., ge=1)
    height: int = Field(..., ge=1)
    fps: int = Field(..., ge=1)
    frame_count: int = Field(..., ge=1)
    frame_digest: str
    source_hash: str

    @field_validator("width", "height", "fps", "frame_count", mode="before")
    @classmethod
    def _strict_int(cls, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise RenderInvalidInputError("render integer fields must be strict integers")
        return value

    @field_validator("duration", mode="before")
    @classmethod
    def _finite_duration(cls, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RenderInvalidInputError("duration must be a finite number")
        value = float(value)
        if not math.isfinite(value) or value <= 0:
            raise RenderInvalidInputError("duration must be finite and > 0")
        return value

    @field_validator("frame_digest", "source_hash")
    @classmethod
    def _sha256(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise RenderInvalidInputError("digest fields must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def _frame_duration_consistency(self) -> "RenderedArtifact":
        expected = self.frame_count / self.fps
        if abs(expected - self.duration) > max(1.0 / self.fps + 1e-6, 1e-3):
            raise RenderInvalidInputError("duration is inconsistent with frame_count/fps")
        return self

    def to_canonical_json(self) -> str:
        return canonical_json(self)
