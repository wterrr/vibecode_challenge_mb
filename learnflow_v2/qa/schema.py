"""Immutable public artifacts for LearnFlow V2 deterministic QA (CP2.11)."""

from __future__ import annotations

from enum import Enum
import math
from types import MappingProxyType
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_serializer, field_validator, model_validator

from learnflow_v2.qa.errors import QAInvalidInputError
from learnflow_v2.core.jsonsafe import ensure_json_safe_dict
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.layout.schema import Rect

V2_QA_SCHEMA_VERSION = "2.1"


def _finite_number(value: Any, field: str, *, minimum: float | None = None, strictly_positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise QAInvalidInputError(f"{field} must be a real finite number")
    result = float(value)
    if not math.isfinite(result):
        raise QAInvalidInputError(f"{field} must be finite")
    if minimum is not None and result < minimum:
        raise QAInvalidInputError(f"{field} must be >= {minimum}")
    if strictly_positive and result <= 0.0:
        raise QAInvalidInputError(f"{field} must be > 0")
    return result


def _strict_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise QAInvalidInputError(f"{field} must be a boolean")
    return value


def _strict_nonnegative_int(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise QAInvalidInputError(f"{field} must be an integer")
    if value < minimum:
        raise QAInvalidInputError(f"{field} must be >= {minimum}")
    return value


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _unfreeze_json(value: Any) -> Any:
    if isinstance(value, MappingProxyType):
        return {key: _unfreeze_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_unfreeze_json(item) for item in value]
    return value


class QAIssueCode(str, Enum):
    BBOX_OVERLAP = "BBOX_OVERLAP"
    FRAME_OVERFLOW = "FRAME_OVERFLOW"
    CONTENT_CLIPPING = "CONTENT_CLIPPING"
    EDGE_NODE_INTERSECTION = "EDGE_NODE_INTERSECTION"
    SAFE_ZONE_VIOLATION = "SAFE_ZONE_VIOLATION"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    MIN_FONT_SIZE = "MIN_FONT_SIZE"
    INVALID_ALPHA = "INVALID_ALPHA"
    MISSING_ASSET = "MISSING_ASSET"
    BLANK_FRAME = "BLANK_FRAME"
    AUDIO_SILENCE = "AUDIO_SILENCE"
    DURATION_MISMATCH = "DURATION_MISMATCH"
    SUBTITLE_BOUNDS = "SUBTITLE_BOUNDS"


class QAIssueSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


class TextElementProbe(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    element_id: str = Field(..., min_length=1)
    font_size_px: float = Field(..., gt=0.0)
    alpha: float = Field(default=1.0)

    @field_validator("font_size_px", mode="before")
    @classmethod
    def _validate_font_size(cls, value: Any) -> float:
        return _finite_number(value, "font_size_px", strictly_positive=True)

    @field_validator("alpha", mode="before")
    @classmethod
    def _validate_alpha(cls, value: Any) -> float:
        return _finite_number(value, "alpha", minimum=None)


class VisualElementProbe(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    element_id: str = Field(..., min_length=1)
    alpha: float = Field(default=1.0)

    @field_validator("alpha", mode="before")
    @classmethod
    def _validate_alpha(cls, value: Any) -> float:
        return _finite_number(value, "alpha", minimum=None)


class AssetProbe(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    asset_id: str = Field(..., min_length=1)
    required: bool = True
    exists: bool

    @field_validator("required", "exists", mode="before")
    @classmethod
    def _validate_bool(cls, value: Any, info: ValidationInfo) -> bool:
        return _strict_bool(value, info.field_name or "asset_bool")


class FrameProbe(BaseModel):
    """Deterministic numeric summary of a sampled rendered frame."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    timestamp: float = Field(..., ge=0.0)
    mean_luma: float = Field(..., ge=0.0, le=255.0)
    non_black_fraction: float = Field(..., ge=0.0, le=1.0)
    expected_blank: bool = False

    @field_validator("expected_blank", mode="before")
    @classmethod
    def _validate_expected_blank(cls, value: Any) -> bool:
        return _strict_bool(value, "expected_blank")

    @field_validator("timestamp", "mean_luma", "non_black_fraction", mode="before")
    @classmethod
    def _validate_numeric(cls, value: Any, info: ValidationInfo) -> float:
        result = _finite_number(value, info.field_name or "value", minimum=0.0)
        if info.field_name == "mean_luma" and result > 255.0:
            raise QAInvalidInputError("mean_luma must be <= 255")
        if info.field_name == "non_black_fraction" and result > 1.0:
            raise QAInvalidInputError("non_black_fraction must be <= 1")
        return result


class AudioProbe(BaseModel):
    """Renderer-neutral audio QA probe using normalized RMS windows in [0, 1]."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    duration: float = Field(..., ge=0.0)
    rms_windows: tuple[float, ...] = Field(default_factory=tuple)
    expected_audio: bool = True

    @field_validator("expected_audio", mode="before")
    @classmethod
    def _validate_expected_audio_bool(cls, value: Any) -> bool:
        return _strict_bool(value, "expected_audio")

    @field_validator("duration", mode="before")
    @classmethod
    def _validate_duration(cls, value: Any) -> float:
        return _finite_number(value, "audio.duration", minimum=0.0)

    @field_validator("rms_windows", mode="before")
    @classmethod
    def _validate_windows(cls, value: Any) -> tuple[float, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple):
            raise QAInvalidInputError("audio.rms_windows must be a tuple/list")
        parsed: list[float] = []
        for index, item in enumerate(value):
            result = _finite_number(item, f"audio.rms_windows[{index}]", minimum=0.0)
            if result > 1.0:
                raise QAInvalidInputError("audio RMS windows must be <= 1")
            parsed.append(result)
        return tuple(parsed)

    @model_validator(mode="after")
    def _validate_expected_audio(self) -> "AudioProbe":
        if self.expected_audio and not self.rms_windows:
            raise QAInvalidInputError("expected audio requires at least one RMS window")
        return self


class SubtitleCueProbe(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    cue_id: str = Field(..., min_length=1)
    start_time: float = Field(..., ge=0.0)
    end_time: float = Field(..., gt=0.0)
    rect: Rect

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def _validate_times(cls, value: Any, info: ValidationInfo) -> float:
        return _finite_number(value, info.field_name or "subtitle_time", minimum=0.0)

    @model_validator(mode="after")
    def _validate_interval(self) -> "SubtitleCueProbe":
        if self.end_time <= self.start_time:
            raise QAInvalidInputError("subtitle end_time must be greater than start_time")
        return self


class RenderedSceneProbe(BaseModel):
    """Renderer-neutral evidence required by deterministic post-render QA."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.1"] = V2_QA_SCHEMA_VERSION
    scene_id: str = Field(..., min_length=1)
    expected_duration: float = Field(..., gt=0.0)
    rendered_duration: float = Field(..., gt=0.0)
    text_elements: tuple[TextElementProbe, ...] = Field(default_factory=tuple)
    visual_elements: tuple[VisualElementProbe, ...] = Field(default_factory=tuple)
    assets: tuple[AssetProbe, ...] = Field(default_factory=tuple)
    frames: tuple[FrameProbe, ...] = Field(..., min_length=1)
    audio: AudioProbe
    subtitles: tuple[SubtitleCueProbe, ...] = Field(default_factory=tuple)

    @field_validator("expected_duration", "rendered_duration", mode="before")
    @classmethod
    def _validate_duration(cls, value: Any, info: ValidationInfo) -> float:
        return _finite_number(value, info.field_name or "duration", strictly_positive=True)

    @field_validator("text_elements", "visual_elements", "assets", "frames", "subtitles", mode="before")
    @classmethod
    def _tupleize(cls, value: Any) -> Any:
        if isinstance(value, list):
            return tuple(value)
        return value

    @model_validator(mode="after")
    def _validate_identity_and_order(self) -> "RenderedSceneProbe":
        def _ensure_unique(items: tuple[Any, ...], attr: str, name: str) -> None:
            values = [getattr(item, attr) for item in items]
            if len(values) != len(set(values)):
                raise QAInvalidInputError(f"duplicate {name} identifiers are not allowed")

        _ensure_unique(self.text_elements, "element_id", "text element")
        _ensure_unique(self.visual_elements, "element_id", "visual element")
        element_ids = [item.element_id for item in self.text_elements] + [item.element_id for item in self.visual_elements]
        if len(element_ids) != len(set(element_ids)):
            raise QAInvalidInputError("text and visual element IDs must share one unique namespace")
        _ensure_unique(self.assets, "asset_id", "asset")
        _ensure_unique(self.subtitles, "cue_id", "subtitle")
        if not self.frames:
            raise QAInvalidInputError("deterministic QA requires at least one rendered frame probe")
        frame_times = [frame.timestamp for frame in self.frames]
        if len(frame_times) != len(set(frame_times)):
            raise QAInvalidInputError("frame probe timestamps must be unique")
        if all(frame.expected_blank for frame in self.frames):
            raise QAInvalidInputError("rendered frame evidence must include at least one non-expected-blank sample")
        for frame in self.frames:
            if frame.timestamp > self.rendered_duration + 1e-6:
                raise QAInvalidInputError("frame probe timestamp cannot exceed rendered_duration")
        ordered_frames = tuple(sorted(self.frames, key=lambda frame: frame.timestamp))
        if ordered_frames != self.frames:
            object.__setattr__(self, "frames", ordered_frames)
        ordered_text = tuple(sorted(self.text_elements, key=lambda item: item.element_id))
        if ordered_text != self.text_elements:
            object.__setattr__(self, "text_elements", ordered_text)
        ordered_visual = tuple(sorted(self.visual_elements, key=lambda item: item.element_id))
        if ordered_visual != self.visual_elements:
            object.__setattr__(self, "visual_elements", ordered_visual)
        ordered_assets = tuple(sorted(self.assets, key=lambda item: item.asset_id))
        if ordered_assets != self.assets:
            object.__setattr__(self, "assets", ordered_assets)
        ordered_subtitles = tuple(sorted(self.subtitles, key=lambda cue: (cue.start_time, cue.cue_id)))
        if ordered_subtitles != self.subtitles:
            object.__setattr__(self, "subtitles", ordered_subtitles)
        return self


class DeterministicQAConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    min_font_size_px: float = Field(default=18.0, gt=0.0)
    blank_mean_luma_threshold: float = Field(default=2.0, ge=0.0, le=255.0)
    blank_non_black_fraction_threshold: float = Field(default=0.002, ge=0.0, le=1.0)
    audio_silence_rms_threshold: float = Field(default=1e-4, ge=0.0, le=1.0)
    min_non_silent_audio_fraction: float = Field(default=0.02, gt=0.0, le=1.0)
    duration_tolerance_seconds: float = Field(default=0.08, ge=0.0)
    layout_tolerance: float = Field(default=1e-2, ge=0.0)

    @field_validator("min_font_size_px", "blank_mean_luma_threshold", "blank_non_black_fraction_threshold", "audio_silence_rms_threshold", "min_non_silent_audio_fraction", "duration_tolerance_seconds", "layout_tolerance", mode="before")
    @classmethod
    def _validate_config_number(cls, value: Any, info: ValidationInfo) -> float:
        return _finite_number(value, info.field_name or "config", minimum=0.0)


class QAIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)
    issue_id: str = Field(..., min_length=1)
    code: QAIssueCode
    severity: QAIssueSeverity = QAIssueSeverity.ERROR
    message: str = Field(..., min_length=1)
    object_ids: tuple[str, ...] = Field(default_factory=tuple)
    evidence: MappingProxyType[str, Any] = Field(default_factory=lambda: MappingProxyType({}))

    @model_validator(mode="after")
    def _validate_issue_identity(self) -> "QAIssue":
        if not self.issue_id.startswith(f"{self.code.value}:"):
            raise QAInvalidInputError("issue_id must be namespaced by issue code")
        return self

    @field_validator("object_ids", mode="before")
    @classmethod
    def _normalize_ids(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple):
            raise QAInvalidInputError("object_ids must be a tuple/list")
        if any(not isinstance(item, str) or not item for item in value):
            raise QAInvalidInputError("object_ids must contain non-empty strings")
        return tuple(sorted(set(value)))

    @field_validator("evidence", mode="before")
    @classmethod
    def _validate_evidence(cls, value: Any) -> MappingProxyType[str, Any]:
        if value is None:
            return MappingProxyType({})
        if isinstance(value, MappingProxyType):
            value = dict(value)
        if not isinstance(value, dict):
            raise QAInvalidInputError("evidence must be a JSON-safe dict")
        try:
            checked = ensure_json_safe_dict(value, path="evidence")
        except ValueError as exc:
            raise QAInvalidInputError(f"evidence not JSON-safe: {exc}") from exc
        return _freeze_json(checked)

    @field_serializer("evidence", mode="plain")
    def _serialize_evidence(self, value: MappingProxyType[str, Any]) -> dict[str, Any]:
        return _unfreeze_json(value)


class DeterministicQAReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.1"] = V2_QA_SCHEMA_VERSION
    scene_id: str = Field(..., min_length=1)
    passed: bool
    issues: tuple[QAIssue, ...] = Field(default_factory=tuple)

    @field_validator("issues", mode="before")
    @classmethod
    def _tupleize_issues(cls, value: Any) -> tuple[Any, ...]:
        if isinstance(value, list):
            return tuple(value)
        return value

    @model_validator(mode="after")
    def _validate_report(self) -> "DeterministicQAReport":
        ids = [issue.issue_id for issue in self.issues]
        if len(ids) != len(set(ids)):
            raise QAInvalidInputError("QA report issue_id values must be unique")
        sorted_issues = tuple(sorted(self.issues, key=lambda issue: issue.issue_id))
        if sorted_issues != self.issues:
            object.__setattr__(self, "issues", sorted_issues)
        expected_pass = not any(issue.severity == QAIssueSeverity.ERROR for issue in self.issues)
        if self.passed != expected_pass:
            raise QAInvalidInputError("QA report passed flag contradicts issue severities")
        return self

    def has_code(self, code: QAIssueCode) -> bool:
        return any(issue.code == code for issue in self.issues)

    def to_canonical_json(self) -> str:
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, payload: str) -> "DeterministicQAReport":
        import json
        return cls.model_validate(json.loads(payload))


class QAFixtureResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    fixture_id: str = Field(..., min_length=1)
    expected_issue_codes: tuple[QAIssueCode, ...] = Field(default_factory=tuple)
    report: DeterministicQAReport

    @field_validator("expected_issue_codes", mode="before")
    @classmethod
    def _normalize_codes(cls, value: Any) -> tuple[QAIssueCode, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple):
            raise QAInvalidInputError("expected_issue_codes must be a tuple/list")
        if len(value) != len(set(value)):
            raise QAInvalidInputError("expected_issue_codes cannot contain duplicates")
        return tuple(sorted(value, key=lambda code: code.value if isinstance(code, QAIssueCode) else str(code)))


class QAFixtureEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    total_fixtures: int = Field(..., ge=1)
    broken_fixtures: int = Field(..., ge=0)
    good_fixtures: int = Field(..., ge=0)
    detected_broken_fixtures: int = Field(..., ge=0)
    missed_broken_fixtures: tuple[str, ...] = Field(default_factory=tuple)
    false_positive_fixtures: tuple[str, ...] = Field(default_factory=tuple)
    detection_rate: float = Field(..., ge=0.0, le=1.0)
    false_positive_rate: float = Field(..., ge=0.0, le=1.0)

    @field_validator("total_fixtures", "broken_fixtures", "good_fixtures", "detected_broken_fixtures", mode="before")
    @classmethod
    def _validate_counts_strict(cls, value: Any, info: ValidationInfo) -> int:
        minimum = 1 if info.field_name == "total_fixtures" else 0
        return _strict_nonnegative_int(value, info.field_name or "count", minimum=minimum)

    @field_validator("detection_rate", "false_positive_rate", mode="before")
    @classmethod
    def _validate_rate_finite(cls, value: Any, info: ValidationInfo) -> float:
        result = _finite_number(value, info.field_name or "rate", minimum=0.0)
        if result > 1.0:
            raise QAInvalidInputError(f"{info.field_name} must be <= 1")
        return result

    @field_validator("missed_broken_fixtures", "false_positive_fixtures", mode="before")
    @classmethod
    def _normalize_fixture_ids(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, list):
            value = tuple(value)
        if not isinstance(value, tuple):
            raise QAInvalidInputError("fixture ID collections must be tuples/lists")
        if any(not isinstance(item, str) or not item for item in value):
            raise QAInvalidInputError("fixture ID collections require non-empty strings")
        if len(value) != len(set(value)):
            raise QAInvalidInputError("fixture ID collections cannot contain duplicates")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def _validate_counts(self) -> "QAFixtureEvaluation":
        if self.broken_fixtures + self.good_fixtures != self.total_fixtures:
            raise QAInvalidInputError("fixture evaluation counts do not add up")
        if self.detected_broken_fixtures > self.broken_fixtures:
            raise QAInvalidInputError("detected broken count cannot exceed broken fixture count")
        if len(self.false_positive_fixtures) > self.good_fixtures:
            raise QAInvalidInputError("false_positive_fixtures cannot exceed good fixture count")
        if len(self.missed_broken_fixtures) != self.broken_fixtures - self.detected_broken_fixtures:
            raise QAInvalidInputError("missed_broken_fixtures count contradicts detection counts")
        expected_detection_rate = self.detected_broken_fixtures / self.broken_fixtures if self.broken_fixtures else 1.0
        expected_fpr = len(self.false_positive_fixtures) / self.good_fixtures if self.good_fixtures else 0.0
        if abs(self.detection_rate - expected_detection_rate) > 1e-12:
            raise QAInvalidInputError("detection_rate contradicts fixture counts")
        if abs(self.false_positive_rate - expected_fpr) > 1e-12:
            raise QAInvalidInputError("false_positive_rate contradicts fixture counts")
        return self

    def to_canonical_json(self) -> str:
        return canonical_json(self)
