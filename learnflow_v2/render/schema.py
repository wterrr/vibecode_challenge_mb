"""Immutable renderer artifacts for LearnFlow V2."""

from __future__ import annotations

from enum import Enum
import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.render.errors import RenderInvalidInputError

V2_RENDER_SCHEMA_VERSION = "2.1"
_SHA = re.compile(r"^[0-9a-f]{64}$")


def _finite(value: Any, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RenderInvalidInputError(f"{field} must be a finite real number")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0):
        raise RenderInvalidInputError(f"{field} must be finite" + (" and > 0" if positive else ""))
    return result


def _pos_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RenderInvalidInputError(f"{field} must be a positive strict integer")
    return value


class RenderBackendKind(str, Enum):
    PILLOW_FFMPEG = "PILLOW_FFMPEG"


class RendererCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.1"] = V2_RENDER_SCHEMA_VERSION
    backend_id: str = Field(..., min_length=1)
    backend_kind: RenderBackendKind = RenderBackendKind.PILLOW_FFMPEG
    supports_tier1_motion: bool = True
    supports_transition_fade: bool = True
    supports_transition_move: bool = False
    supports_transition_resize: bool = False
    supports_transition_morph: bool = False

    @field_validator(
        "supports_tier1_motion", "supports_transition_fade",
        "supports_transition_move", "supports_transition_resize", "supports_transition_morph",
        mode="before",
    )
    @classmethod
    def _strict_bool(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise RenderInvalidInputError("renderer capability flags must be booleans")
        return value

    @model_validator(mode="after")
    def _fallback_required(self):
        if not self.supports_transition_fade:
            raise RenderInvalidInputError("Core V2 backend must support FADE fallback")
        return self


class FrameRenderDigest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    frame_index: int = Field(..., ge=0)
    timestamp: float = Field(..., ge=0)
    sha256: str
    mean_luma: float = Field(..., ge=0, le=255)
    non_black_fraction: float = Field(..., ge=0, le=1)

    @field_validator("frame_index", mode="before")
    @classmethod
    def _idx(cls, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise RenderInvalidInputError("frame_index must be a non-negative strict integer")
        return value

    @field_validator("timestamp", "mean_luma", "non_black_fraction", mode="before")
    @classmethod
    def _num(cls, value: Any, info) -> float:
        result = _finite(value, info.field_name or "value")
        if result < 0:
            raise RenderInvalidInputError(f"{info.field_name} must be >= 0")
        if info.field_name == "mean_luma" and result > 255:
            raise RenderInvalidInputError("mean_luma must be <= 255")
        if info.field_name == "non_black_fraction" and result > 1:
            raise RenderInvalidInputError("non_black_fraction must be <= 1")
        return result

    @field_validator("sha256")
    @classmethod
    def _hash(cls, value: str) -> str:
        value = value.strip().lower()
        if not _SHA.fullmatch(value):
            raise RenderInvalidInputError("frame sha256 must be a lowercase SHA-256 digest")
        return value


class TextRenderEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    element_id: str = Field(..., min_length=1)
    font_size_px: float = Field(..., gt=0)
    alpha: float = Field(..., ge=0, le=1)
    source_chars: int = Field(..., ge=0)
    rendered_chars: int = Field(..., ge=0)
    truncated: bool

    @field_validator("font_size_px", "alpha", mode="before")
    @classmethod
    def _floats(cls, value: Any, info) -> float:
        result = _finite(value, info.field_name or "value", positive=info.field_name == "font_size_px")
        if info.field_name == "alpha" and not 0 <= result <= 1:
            raise RenderInvalidInputError("alpha must be in [0,1]")
        return result

    @field_validator("source_chars", "rendered_chars", mode="before")
    @classmethod
    def _counts(cls, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise RenderInvalidInputError("text counts must be non-negative strict integers")
        return value

    @field_validator("truncated", mode="before")
    @classmethod
    def _bool(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise RenderInvalidInputError("truncated must be boolean")
        return value

    @model_validator(mode="after")
    def _consistent(self):
        if self.rendered_chars > self.source_chars:
            raise RenderInvalidInputError("rendered_chars cannot exceed source_chars")
        if self.truncated != (self.rendered_chars < self.source_chars):
            raise RenderInvalidInputError("truncated flag contradicts character counts")
        return self


class RenderedScene(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.1"] = V2_RENDER_SCHEMA_VERSION
    scene_id: str = Field(..., min_length=1)
    backend_id: str = Field(..., min_length=1)
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    fps: int = Field(..., gt=0)
    expected_duration: float = Field(..., gt=0)
    rendered_duration: float = Field(..., gt=0)
    frame_count: int = Field(..., gt=0)
    output_path: str = Field(..., min_length=1)
    file_size_bytes: int = Field(..., gt=0)
    visual_digest: str
    sampled_frames: tuple[FrameRenderDigest, ...] = Field(..., min_length=1)
    text_evidence: tuple[TextRenderEvidence, ...] = Field(default_factory=tuple)
    has_audio: bool
    audio_duration: float | None = None
    diagnostics: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("width", "height", "fps", "frame_count", "file_size_bytes", mode="before")
    @classmethod
    def _ints(cls, value: Any, info) -> int:
        return _pos_int(value, info.field_name or "integer")

    @field_validator("expected_duration", "rendered_duration", mode="before")
    @classmethod
    def _duration(cls, value: Any, info) -> float:
        return _finite(value, info.field_name or "duration", positive=True)

    @field_validator("audio_duration", mode="before")
    @classmethod
    def _audio(cls, value: Any) -> float | None:
        return None if value is None else _finite(value, "audio_duration", positive=True)

    @field_validator("visual_digest")
    @classmethod
    def _digest(cls, value: str) -> str:
        value = value.strip().lower()
        if not _SHA.fullmatch(value):
            raise RenderInvalidInputError("visual_digest must be SHA-256")
        return value

    @field_validator("has_audio", mode="before")
    @classmethod
    def _has_audio(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise RenderInvalidInputError("has_audio must be boolean")
        return value

    @field_validator("sampled_frames", "text_evidence", "diagnostics", mode="before")
    @classmethod
    def _tupleize(cls, value: Any):
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _shape(self):
        if self.has_audio != (self.audio_duration is not None):
            raise RenderInvalidInputError("audio_duration must exist exactly when has_audio=true")
        if abs(self.frame_count / self.fps - self.rendered_duration) > max(0.1, 2 / self.fps):
            raise RenderInvalidInputError("frame_count/fps disagrees with rendered_duration")
        if len({x.frame_index for x in self.sampled_frames}) != len(self.sampled_frames):
            raise RenderInvalidInputError("sampled frame indexes must be unique")
        if any(x.frame_index >= self.frame_count for x in self.sampled_frames):
            raise RenderInvalidInputError("sampled frame index exceeds frame_count")
        if len({x.element_id for x in self.text_evidence}) != len(self.text_evidence):
            raise RenderInvalidInputError("text evidence IDs must be unique")
        object.__setattr__(self, "sampled_frames", tuple(sorted(self.sampled_frames, key=lambda x: x.frame_index)))
        object.__setattr__(self, "text_evidence", tuple(sorted(self.text_evidence, key=lambda x: x.element_id)))
        object.__setattr__(self, "diagnostics", tuple(sorted(set(self.diagnostics))))
        return self

    def to_canonical_json(self) -> str:
        return canonical_json(self)


class RenderedVideo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.1"] = V2_RENDER_SCHEMA_VERSION
    video_id: str = Field(..., min_length=1)
    output_path: str = Field(..., min_length=1)
    scene_ids: tuple[str, ...] = Field(..., min_length=1)
    transition_ids: tuple[str, ...] = Field(default_factory=tuple)
    duration: float = Field(..., gt=0)
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    fps: int = Field(..., gt=0)
    file_size_bytes: int = Field(..., gt=0)
    video_sha256: str
    diagnostics: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("scene_ids", "transition_ids", "diagnostics", mode="before")
    @classmethod
    def _tuples(cls, value: Any):
        return tuple(value) if isinstance(value, list) else value

    @field_validator("video_sha256")
    @classmethod
    def _sha(cls, value: str) -> str:
        value = value.strip().lower()
        if not _SHA.fullmatch(value):
            raise RenderInvalidInputError("video_sha256 must be SHA-256")
        return value

    @model_validator(mode="after")
    def _validate(self):
        if len(self.scene_ids) != len(set(self.scene_ids)):
            raise RenderInvalidInputError("scene IDs must be unique")
        if len(self.transition_ids) not in {0, len(self.scene_ids) - 1}:
            raise RenderInvalidInputError("transition_ids must be empty or one per adjacent pair")
        return self

    def to_canonical_json(self) -> str:
        return canonical_json(self)
