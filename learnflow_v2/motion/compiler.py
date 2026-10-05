"""Renderer-neutral property-track compiler for LearnFlow V2 Motion Grammar (CP 2.9).

Compiles scheduled Tier-1 motion events into normalized semantic animation tracks
(e.g., opacity progression, reveal progress, emphasis intensity, translation progress,
edge draw, and propagation progress).

Strictly emits zero pixel coordinates, renderer commands, or executable code.
"""

from __future__ import annotations

from enum import Enum
import math
from types import MappingProxyType
from typing import Any, Literal
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from learnflow_v2.core.errors import (
    MotionCompilationError,
    MotionDuplicateEventIdError,
    MotionGrammarIncompatibleError,
    MotionInvalidInputError,
    MotionInvalidTargetError,
    MotionScheduleTimingError,
    MotionUnsupportedTierError,
)
from learnflow_v2.core.jsonsafe import ensure_json_safe_dict
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.motion.enums import (
    TIER_1_MOTION_GRAMMAR,
    TIER_2_3_RESERVED_STYLES,
    TIER_2_3_RESERVED_VERBS,
    VERB_TARGET_KIND_MAP,
    MotionStyle,
    MotionTargetKind,
    MotionVerb,
)
from learnflow_v2.motion.scheduler import MotionSchedule, ScheduledMotionEvent


class PropertyTrackKind(str, Enum):
    """Semantic property track categories."""

    OPACITY = "opacity"
    TRANSLATION_PROGRESS = "translation_progress"
    REVEAL_PROGRESS = "reveal_progress"
    EMPHASIS_INTENSITY = "emphasis_intensity"
    EDGE_DRAW_PROGRESS = "edge_draw_progress"
    PROPAGATION_PROGRESS = "propagation_progress"


# Authoritative Tier-1 compiler contract mapping verb & style to expected property track kinds.
TIER_1_COMPILER_TRACK_CONTRACT: MappingProxyType[tuple[MotionVerb, MotionStyle], tuple[PropertyTrackKind, ...]] = MappingProxyType({
    (MotionVerb.ENTER, MotionStyle.FADE): (PropertyTrackKind.OPACITY,),
    (MotionVerb.ENTER, MotionStyle.SLIDE): (PropertyTrackKind.OPACITY, PropertyTrackKind.TRANSLATION_PROGRESS),
    (MotionVerb.ENTER, MotionStyle.REVEAL): (PropertyTrackKind.OPACITY, PropertyTrackKind.REVEAL_PROGRESS),
    (MotionVerb.EMPHASIZE, MotionStyle.HIGHLIGHT): (PropertyTrackKind.EMPHASIS_INTENSITY,),
    (MotionVerb.EMPHASIZE, MotionStyle.PULSE): (PropertyTrackKind.EMPHASIS_INTENSITY,),
    (MotionVerb.EMPHASIZE, MotionStyle.FOCUS): (PropertyTrackKind.EMPHASIS_INTENSITY,),
    (MotionVerb.RELATION, MotionStyle.DRAW_EDGE): (PropertyTrackKind.EDGE_DRAW_PROGRESS,),
    (MotionVerb.RELATION, MotionStyle.PROPAGATE): (PropertyTrackKind.PROPAGATION_PROGRESS,),
    (MotionVerb.TRANSFORM, MotionStyle.MOVE): (PropertyTrackKind.TRANSLATION_PROGRESS,),
    (MotionVerb.EXIT, MotionStyle.FADE): (PropertyTrackKind.OPACITY,),
})


def freeze_json_safe(val: Any) -> Any:
    """Recursively freeze JSON-safe dicts and lists into MappingProxyType and tuple."""
    if isinstance(val, (dict, MappingProxyType)):
        return MappingProxyType({k: freeze_json_safe(v) for k, v in val.items()})
    elif isinstance(val, list):
        return tuple(freeze_json_safe(x) for x in val)
    return val


def unfreeze_json_safe(val: Any) -> Any:
    """Recursively unfreeze MappingProxyType and tuple into standard dict and list for JSON dumping."""
    if isinstance(val, (MappingProxyType, dict)):
        return {k: unfreeze_json_safe(v) for k, v in val.items()}
    elif isinstance(val, (tuple, list)):
        return [unfreeze_json_safe(x) for x in val]
    return val


class PropertyKeyframe(BaseModel):
    """Normalized keyframe point along a property animation track."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    offset: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized time offset within event interval [0.0, 1.0]",
    )
    time: float = Field(
        ...,
        description="Absolute scene timeline timestamp in seconds",
    )
    value: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized property value [0.0, 1.0]",
    )
    easing: str = Field(
        default="linear",
        min_length=1,
        description="Semantic easing name (e.g. 'linear', 'ease_in', 'ease_out', 'ease_in_out')",
    )

    @field_validator("time", "offset", "value", mode="before")
    @classmethod
    def _validate_finite_float(cls, v: Any) -> float:
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise MotionScheduleTimingError(f"Keyframe numerical value must be a valid float, got {v}")
        if not math.isfinite(val):
            raise MotionScheduleTimingError(f"Keyframe numerical value must be finite, got {v}")
        return val


class PropertyTrack(BaseModel):
    """Renderer-neutral continuous property track for an animated entity.

    Metadata is strictly JSON-safe and deeply immutable via MappingProxyType.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    track_id: str = Field(..., min_length=1, description="Unique track identifier")
    target: str = Field(..., min_length=1, description="Target node or relation ID")
    target_kind: MotionTargetKind = Field(..., description="Target entity kind")
    property_kind: PropertyTrackKind = Field(..., description="Animated property kind")
    start_time: float = Field(..., description="Track start time in seconds")
    end_time: float = Field(..., description="Track end time in seconds")
    keyframes: tuple[PropertyKeyframe, ...] = Field(
        default_factory=tuple,
        description="Ordered sequence of property keyframes",
    )
    metadata: MappingProxyType[str, Any] = Field(
        default_factory=lambda: MappingProxyType({}),
        description="Renderer-neutral semantic parameters (e.g. direction, mode)",
    )

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def _validate_finite_float(cls, v: Any) -> float:
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise MotionScheduleTimingError(f"Track timing value must be a valid float, got {v}")
        if not math.isfinite(val):
            raise MotionScheduleTimingError(f"Track timing value must be finite, got {v}")
        if val < 0.0:
            raise MotionScheduleTimingError(f"Track timing value cannot be negative, got {v}")
        return val

    @field_validator("metadata", mode="before")
    @classmethod
    def _validate_metadata(cls, v: Any) -> MappingProxyType[str, Any]:
        if v is None:
            return MappingProxyType({})
        if isinstance(v, MappingProxyType):
            if len(v) == 0:
                return MappingProxyType({})
            def _unwrap_mapping_proxy(item: Any) -> Any:
                if isinstance(item, MappingProxyType):
                    return {k: _unwrap_mapping_proxy(val) for k, val in item.items()}
                return item
            raw = _unwrap_mapping_proxy(v)
        elif isinstance(v, dict):
            raw = v
        else:
            raise MotionInvalidInputError(f"Track metadata must be a dict[str, JSON-safe], got {type(v).__name__}")

        try:
            ensure_json_safe_dict(raw, path="metadata")
        except ValueError as e:
            raise MotionInvalidInputError(f"Track metadata not JSON-safe: {e}") from e

        return freeze_json_safe(raw)

    @field_serializer("metadata", mode="plain")
    def _serialize_metadata(self, v: MappingProxyType[str, Any]) -> dict[str, Any]:
        return unfreeze_json_safe(v)

    @model_validator(mode="after")
    def _validate_track_invariants(self) -> "PropertyTrack":
        # 1. Non-zero animation duration
        if self.end_time <= self.start_time + 1e-4:
            raise MotionScheduleTimingError(
                f"Track '{self.track_id}' end_time ({self.end_time:.4f}s) must be strictly greater than start_time ({self.start_time:.4f}s)"
            )

        # 2. Keyframes completeness: at least 2 keyframes
        if len(self.keyframes) < 2:
            raise MotionScheduleTimingError(
                f"Track '{self.track_id}' must contain at least 2 keyframes, got {len(self.keyframes)}"
            )

        # 3. Endpoint keyframe correspondence
        first_kf = self.keyframes[0]
        last_kf = self.keyframes[-1]
        if abs(first_kf.offset - 0.0) > 1e-3:
            raise MotionScheduleTimingError(
                f"Track '{self.track_id}' first keyframe offset ({first_kf.offset:.4f}) must be approximately 0.0"
            )
        if abs(last_kf.offset - 1.0) > 1e-3:
            raise MotionScheduleTimingError(
                f"Track '{self.track_id}' last keyframe offset ({last_kf.offset:.4f}) must be approximately 1.0"
            )
        if abs(first_kf.time - self.start_time) > 1e-3:
            raise MotionScheduleTimingError(
                f"Track '{self.track_id}' first keyframe time ({first_kf.time:.4f}s) must correspond to track start_time ({self.start_time:.4f}s)"
            )
        if abs(last_kf.time - self.end_time) > 1e-3:
            raise MotionScheduleTimingError(
                f"Track '{self.track_id}' last keyframe time ({last_kf.time:.4f}s) must correspond to track end_time ({self.end_time:.4f}s)"
            )

        # 4. Monotonicity of offsets and times
        prev_time = self.start_time - 1e-4
        prev_offset = -1e-4
        for idx, kf in enumerate(self.keyframes):
            if kf.time < self.start_time - 1e-4 or kf.time > self.end_time + 1e-4:
                raise MotionScheduleTimingError(
                    f"Keyframe {idx} at time {kf.time:.4f}s lies outside track interval [{self.start_time:.4f}s, {self.end_time:.4f}s]"
                )
            if kf.time < prev_time - 1e-4:
                raise MotionScheduleTimingError(
                    f"Keyframe times in track '{self.track_id}' must be non-decreasing (got {kf.time:.4f}s < previous {prev_time:.4f}s)"
                )
            if kf.offset < prev_offset - 1e-4:
                raise MotionScheduleTimingError(
                    f"Keyframe normalized offsets in track '{self.track_id}' must be non-decreasing (got {kf.offset:.4f} < previous {prev_offset:.4f})"
                )
            prev_time = kf.time
            prev_offset = kf.offset

        return self


class CompiledMotionEvent(BaseModel):
    """Scheduled motion event compiled into renderer-neutral property tracks."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    event_id: str = Field(..., min_length=1, description="Source motion event identifier")
    target: str = Field(..., min_length=1, description="Target entity ID")
    target_kind: MotionTargetKind = Field(..., description="Target entity kind")
    verb: MotionVerb = Field(..., description="Semantic motion verb")
    style: MotionStyle = Field(..., description="Semantic motion style")
    start_time: float = Field(..., description="Event start time in seconds")
    end_time: float = Field(..., description="Event end time in seconds")
    tracks: tuple[PropertyTrack, ...] = Field(
        default_factory=tuple,
        description="Property tracks driven by this motion event",
    )

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def _validate_finite_time(cls, v: Any) -> float:
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise MotionScheduleTimingError(f"CompiledMotionEvent timing must be a float, got {v}")
        if not math.isfinite(val):
            raise MotionScheduleTimingError(f"CompiledMotionEvent timing must be finite, got {v}")
        return val

    @model_validator(mode="after")
    def _validate_event_invariants(self) -> "CompiledMotionEvent":
        # 1. Timing bounds
        if self.start_time < 0.0:
            raise MotionScheduleTimingError(
                f"Event '{self.event_id}' start_time ({self.start_time:.4f}s) cannot be negative"
            )
        if self.end_time <= self.start_time + 1e-4:
            raise MotionScheduleTimingError(
                f"Event '{self.event_id}' end_time ({self.end_time:.4f}s) must be strictly greater than start_time ({self.start_time:.4f}s)"
            )

        # 2. Grammar & target kind integrity
        if self.verb in TIER_2_3_RESERVED_VERBS:
            raise MotionUnsupportedTierError(
                f"Motion verb '{self.verb.value}' is reserved for Tier 2/3 and unsupported in Tier 1."
            )
        if self.style in TIER_2_3_RESERVED_STYLES:
            raise MotionUnsupportedTierError(
                f"Motion style '{self.style.value}' is reserved for Tier 2/3 and unsupported in Tier 1."
            )

        allowed_styles = TIER_1_MOTION_GRAMMAR.get(self.verb)
        if allowed_styles is None or self.style not in allowed_styles:
            allowed_names = sorted(s.value for s in (allowed_styles or frozenset()))
            raise MotionGrammarIncompatibleError(
                f"Invalid motion grammar combination: verb '{self.verb.value}' with style '{self.style.value}'. "
                f"Allowed styles for {self.verb.value}: {allowed_names}"
            )

        expected_kind = VERB_TARGET_KIND_MAP[self.verb]
        if self.target_kind != expected_kind:
            raise MotionInvalidTargetError(
                f"Motion verb '{self.verb.value}' requires target_kind '{expected_kind.value}', "
                f"got '{self.target_kind.value}'"
            )

        # 3. Check against authoritative compiler track contract
        expected_track_kinds = TIER_1_COMPILER_TRACK_CONTRACT.get((self.verb, self.style))
        if expected_track_kinds is None:
            raise MotionCompilationError(
                f"No compiler track contract defined for Tier-1 {self.verb.value} + {self.style.value}"
            )
        actual_track_kinds = tuple(tr.property_kind for tr in self.tracks)
        if actual_track_kinds != expected_track_kinds:
            expected_names = [k.value for k in expected_track_kinds]
            actual_names = [k.value for k in actual_track_kinds]
            raise MotionCompilationError(
                f"CompiledMotionEvent '{self.event_id}' ({self.verb.value} + {self.style.value}) tracks mismatch. "
                f"Expected track kinds {expected_names}, got {actual_names}"
            )

        # 4. Track interval & target containment
        for tr in self.tracks:
            if tr.start_time < self.start_time - 1e-4 or tr.end_time > self.end_time + 1e-4:
                raise MotionScheduleTimingError(
                    f"Track '{tr.track_id}' interval [{tr.start_time:.4f}s, {tr.end_time:.4f}s] "
                    f"exceeds event '{self.event_id}' interval [{self.start_time:.4f}s, {self.end_time:.4f}s]"
                )
            if tr.target != self.target:
                raise MotionInvalidTargetError(
                    f"Track '{tr.track_id}' target '{tr.target}' does not match event target '{self.target}'"
                )
            if tr.target_kind != self.target_kind:
                raise MotionInvalidTargetError(
                    f"Track '{tr.track_id}' target_kind '{tr.target_kind.value}' does not match event target_kind '{self.target_kind.value}'"
                )

        return self


class CompiledMotionArtifact(BaseModel):
    """Complete, immutable compiled animation tracks for a scene."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    schema_version: Literal["2.1"] = Field(
        default="2.1",
        description="Compiler schema version (2.1)",
    )
    scene_id: str = Field(..., min_length=1, description="Scene identifier matching MotionSchedule")
    scene_duration: float = Field(..., description="Total scene duration in seconds")
    events: tuple[CompiledMotionEvent, ...] = Field(
        default_factory=tuple,
        description="Compiled events with associated tracks",
    )
    tracks: tuple[PropertyTrack, ...] = Field(
        default_factory=tuple,
        description="Flattened sequence of all compiled property tracks",
    )

    @field_validator("scene_duration", mode="before")
    @classmethod
    def _validate_duration(cls, v: Any) -> float:
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise MotionScheduleTimingError(f"scene_duration must be a valid float, got {v}")
        if not math.isfinite(val):
            raise MotionScheduleTimingError(f"scene_duration must be finite, got {v}")
        if val < 0.0:
            raise MotionScheduleTimingError(f"scene_duration cannot be negative, got {v}")
        return float(val)

    @model_validator(mode="after")
    def _validate_artifact_invariants(self) -> "CompiledMotionArtifact":
        # 1. Unique event IDs
        seen_event_ids: set[str] = set()
        for ev in self.events:
            if ev.event_id in seen_event_ids:
                raise MotionDuplicateEventIdError(
                    f"Duplicate event ID '{ev.event_id}' in CompiledMotionArtifact"
                )
            seen_event_ids.add(ev.event_id)
            if ev.end_time > self.scene_duration + 1e-4:
                raise MotionScheduleTimingError(
                    f"Event '{ev.event_id}' end_time {ev.end_time:.4f}s exceeds scene duration {self.scene_duration:.4f}s"
                )

        # 2. Cross-reference integrity: tracks must strictly match flattened event tracks
        expected_tracks = tuple(tr for ev in self.events for tr in ev.tracks)
        if self.tracks != expected_tracks:
            raise MotionCompilationError(
                f"CompiledMotionArtifact.tracks ({len(self.tracks)} tracks) does not match "
                f"flattened event tracks ({len(expected_tracks)} tracks)"
            )

        # 3. Unique track IDs and duration containment
        seen_track_ids: set[str] = set()
        for tr in self.tracks:
            if tr.track_id in seen_track_ids:
                raise MotionCompilationError(
                    f"Duplicate property track ID '{tr.track_id}' in CompiledMotionArtifact"
                )
            seen_track_ids.add(tr.track_id)
            if tr.end_time > self.scene_duration + 1e-4:
                raise MotionScheduleTimingError(
                    f"Track '{tr.track_id}' end_time {tr.end_time:.4f}s exceeds scene duration {self.scene_duration:.4f}s"
                )
        return self

    def to_canonical_json(self) -> str:
        """Serialize CompiledMotionArtifact to canonical deterministic JSON."""
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, json_str: str) -> "CompiledMotionArtifact":
        """Deserialize CompiledMotionArtifact from canonical JSON string."""
        return cls.model_validate_json(json_str)


def compile_event_to_tracks(ev: ScheduledMotionEvent) -> tuple[PropertyTrack, ...]:
    """Compile a single scheduled Tier-1 motion event into renderer-neutral property tracks."""
    if ev.verb in TIER_2_3_RESERVED_VERBS or ev.style in TIER_2_3_RESERVED_STYLES:
        raise MotionUnsupportedTierError(
            f"Cannot compile reserved Tier-2/3 motion: verb '{ev.verb.value}', style '{ev.style.value}'"
        )

    t0 = ev.start_time
    t1 = ev.end_time
    dur = max(t1 - t0, 1e-4)

    # 1. ENTER: FADE, SLIDE, REVEAL
    if ev.verb == MotionVerb.ENTER:
        if ev.style == MotionStyle.FADE:
            opacity_track = PropertyTrack(
                track_id=f"{ev.event_id}__opacity",
                target=ev.target,
                target_kind=ev.target_kind,
                property_kind=PropertyTrackKind.OPACITY,
                start_time=t0,
                end_time=t1,
                keyframes=(
                    PropertyKeyframe(offset=0.0, time=t0, value=0.0, easing="ease_out"),
                    PropertyKeyframe(offset=1.0, time=t1, value=1.0, easing="ease_out"),
                ),
                metadata={"transition": "fade_in"},
            )
            return (opacity_track,)

        elif ev.style == MotionStyle.SLIDE:
            opacity_track = PropertyTrack(
                track_id=f"{ev.event_id}__opacity",
                target=ev.target,
                target_kind=ev.target_kind,
                property_kind=PropertyTrackKind.OPACITY,
                start_time=t0,
                end_time=t1,
                keyframes=(
                    PropertyKeyframe(offset=0.0, time=t0, value=0.0, easing="ease_out"),
                    PropertyKeyframe(offset=1.0, time=t1, value=1.0, easing="ease_out"),
                ),
                metadata={"transition": "fade_in"},
            )
            slide_track = PropertyTrack(
                track_id=f"{ev.event_id}__slide",
                target=ev.target,
                target_kind=ev.target_kind,
                property_kind=PropertyTrackKind.TRANSLATION_PROGRESS,
                start_time=t0,
                end_time=t1,
                keyframes=(
                    PropertyKeyframe(offset=0.0, time=t0, value=0.0, easing="ease_out"),
                    PropertyKeyframe(offset=1.0, time=t1, value=1.0, easing="ease_out"),
                ),
                metadata={"direction": "up", "normalized_distance": 1.0},
            )
            return (opacity_track, slide_track)

        elif ev.style == MotionStyle.REVEAL:
            opacity_track = PropertyTrack(
                track_id=f"{ev.event_id}__opacity",
                target=ev.target,
                target_kind=ev.target_kind,
                property_kind=PropertyTrackKind.OPACITY,
                start_time=t0,
                end_time=t1,
                keyframes=(
                    PropertyKeyframe(offset=0.0, time=t0, value=0.0, easing="ease_out"),
                    PropertyKeyframe(offset=1.0, time=t1, value=1.0, easing="ease_out"),
                ),
                metadata={"transition": "fade_in"},
            )
            reveal_track = PropertyTrack(
                track_id=f"{ev.event_id}__reveal",
                target=ev.target,
                target_kind=ev.target_kind,
                property_kind=PropertyTrackKind.REVEAL_PROGRESS,
                start_time=t0,
                end_time=t1,
                keyframes=(
                    PropertyKeyframe(offset=0.0, time=t0, value=0.0, easing="ease_out"),
                    PropertyKeyframe(offset=1.0, time=t1, value=1.0, easing="ease_out"),
                ),
                metadata={"direction": "start_to_end", "reveal_axis": "x"},
            )
            return (opacity_track, reveal_track)

    # 2. EMPHASIZE: HIGHLIGHT, PULSE, FOCUS
    elif ev.verb == MotionVerb.EMPHASIZE:
        if ev.style == MotionStyle.HIGHLIGHT:
            t_peak = round(t0 + 0.40 * dur, 4)
            highlight_track = PropertyTrack(
                track_id=f"{ev.event_id}__emphasis",
                target=ev.target,
                target_kind=ev.target_kind,
                property_kind=PropertyTrackKind.EMPHASIS_INTENSITY,
                start_time=t0,
                end_time=t1,
                keyframes=(
                    PropertyKeyframe(offset=0.0, time=t0, value=0.0, easing="ease_out"),
                    PropertyKeyframe(offset=0.4, time=t_peak, value=1.0, easing="ease_in_out"),
                    PropertyKeyframe(offset=1.0, time=t1, value=0.0, easing="ease_in"),
                ),
                metadata={"emphasis_type": "highlight"},
            )
            return (highlight_track,)

        elif ev.style == MotionStyle.PULSE:
            t_p1 = round(t0 + 0.25 * dur, 4)
            t_dip = round(t0 + 0.50 * dur, 4)
            t_p2 = round(t0 + 0.75 * dur, 4)
            pulse_track = PropertyTrack(
                track_id=f"{ev.event_id}__pulse",
                target=ev.target,
                target_kind=ev.target_kind,
                property_kind=PropertyTrackKind.EMPHASIS_INTENSITY,
                start_time=t0,
                end_time=t1,
                keyframes=(
                    PropertyKeyframe(offset=0.0, time=t0, value=0.0, easing="ease_out"),
                    PropertyKeyframe(offset=0.25, time=t_p1, value=1.0, easing="ease_in_out"),
                    PropertyKeyframe(offset=0.50, time=t_dip, value=0.2, easing="ease_in_out"),
                    PropertyKeyframe(offset=0.75, time=t_p2, value=1.0, easing="ease_in_out"),
                    PropertyKeyframe(offset=1.0, time=t1, value=0.0, easing="ease_in"),
                ),
                metadata={"cycles": 2, "emphasis_type": "pulse"},
            )
            return (pulse_track,)

        elif ev.style == MotionStyle.FOCUS:
            focus_track = PropertyTrack(
                track_id=f"{ev.event_id}__focus",
                target=ev.target,
                target_kind=ev.target_kind,
                property_kind=PropertyTrackKind.EMPHASIS_INTENSITY,
                start_time=t0,
                end_time=t1,
                keyframes=(
                    PropertyKeyframe(offset=0.0, time=t0, value=0.0, easing="ease_out"),
                    PropertyKeyframe(offset=1.0, time=t1, value=1.0, easing="ease_out"),
                ),
                metadata={"emphasis_type": "focus"},
            )
            return (focus_track,)

    # 3. RELATION: DRAW_EDGE, PROPAGATE
    elif ev.verb == MotionVerb.RELATION:
        if ev.style == MotionStyle.DRAW_EDGE:
            edge_track = PropertyTrack(
                track_id=f"{ev.event_id}__draw_edge",
                target=ev.target,
                target_kind=ev.target_kind,
                property_kind=PropertyTrackKind.EDGE_DRAW_PROGRESS,
                start_time=t0,
                end_time=t1,
                keyframes=(
                    PropertyKeyframe(offset=0.0, time=t0, value=0.0, easing="ease_in_out"),
                    PropertyKeyframe(offset=1.0, time=t1, value=1.0, easing="ease_in_out"),
                ),
                metadata={"stroke_progress": "source_to_target"},
            )
            return (edge_track,)

        elif ev.style == MotionStyle.PROPAGATE:
            prop_track = PropertyTrack(
                track_id=f"{ev.event_id}__propagate",
                target=ev.target,
                target_kind=ev.target_kind,
                property_kind=PropertyTrackKind.PROPAGATION_PROGRESS,
                start_time=t0,
                end_time=t1,
                keyframes=(
                    PropertyKeyframe(offset=0.0, time=t0, value=0.0, easing="ease_in_out"),
                    PropertyKeyframe(offset=1.0, time=t1, value=1.0, easing="ease_in_out"),
                ),
                metadata={"signal_mode": "forward_pulse"},
            )
            return (prop_track,)

    # 4. TRANSFORM: MOVE
    elif ev.verb == MotionVerb.TRANSFORM:
        if ev.style == MotionStyle.MOVE:
            move_track = PropertyTrack(
                track_id=f"{ev.event_id}__move",
                target=ev.target,
                target_kind=ev.target_kind,
                property_kind=PropertyTrackKind.TRANSLATION_PROGRESS,
                start_time=t0,
                end_time=t1,
                keyframes=(
                    PropertyKeyframe(offset=0.0, time=t0, value=0.0, easing="ease_in_out"),
                    PropertyKeyframe(offset=1.0, time=t1, value=1.0, easing="ease_in_out"),
                ),
                metadata={"motion_type": "scene_local_move", "reference": "layout_resting_state"},
            )
            return (move_track,)

    # 5. EXIT: FADE
    elif ev.verb == MotionVerb.EXIT:
        if ev.style == MotionStyle.FADE:
            opacity_track = PropertyTrack(
                track_id=f"{ev.event_id}__opacity",
                target=ev.target,
                target_kind=ev.target_kind,
                property_kind=PropertyTrackKind.OPACITY,
                start_time=t0,
                end_time=t1,
                keyframes=(
                    PropertyKeyframe(offset=0.0, time=t0, value=1.0, easing="ease_in"),
                    PropertyKeyframe(offset=1.0, time=t1, value=0.0, easing="ease_in"),
                ),
                metadata={"transition": "fade_out"},
            )
            return (opacity_track,)

    # Unsupported or unmapped
    raise MotionCompilationError(
        f"Unsupported or unmapped Tier-1 motion: verb '{ev.verb.value}', style '{ev.style.value}'"
    )


def compile_motion_schedule(schedule: MotionSchedule) -> CompiledMotionArtifact:
    """Compile a deterministic MotionSchedule into renderer-neutral property tracks."""
    compiled_events: list[CompiledMotionEvent] = []
    all_tracks: list[PropertyTrack] = []

    for ev in schedule.scheduled_events:
        tracks = compile_event_to_tracks(ev)
        compiled_ev = CompiledMotionEvent(
            event_id=ev.event_id,
            target=ev.target,
            target_kind=ev.target_kind,
            verb=ev.verb,
            style=ev.style,
            start_time=ev.start_time,
            end_time=ev.end_time,
            tracks=tracks,
        )
        compiled_events.append(compiled_ev)
        all_tracks.extend(tracks)

    return CompiledMotionArtifact(
        scene_id=schedule.scene_id,
        scene_duration=schedule.scene_duration,
        events=tuple(compiled_events),
        tracks=tuple(all_tracks),
    )
