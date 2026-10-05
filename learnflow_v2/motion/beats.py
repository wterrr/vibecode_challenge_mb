"""Narration beat alignment and timing resolution for LearnFlow V2 Motion Grammar (CP 2.8).

Binds high-level semantic MotionPlan triggers to narration timing:
- Ingests and strictly validates word timestamps when available.
- Groups words into deterministic phrases.
- Produces semantic beats matching MotionTrigger(beat="...").
- Provides deterministic fallback based on structured text segments + audio duration
  when provider word timestamps are unavailable.
- Resolves MotionPlan events into a separate, immutable timing resolution artifact
  without corrupting or complicating the pure semantic MotionPlan models.
"""

from enum import Enum
import math
import re
from typing import Any, Sequence
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from learnflow_v2.core.errors import (
    MotionBeatAmbiguityError,
    MotionBeatTimingError,
    MotionSceneMismatchError,
    MotionUnknownBeatError,
)
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.motion.enums import MotionStyle, MotionVerb
from learnflow_v2.motion.schema import MotionPlan


class TimingMode(str, Enum):
    """Provenance and calculation method of narration beat timing."""

    PROVIDER_WORD_TIMINGS = "PROVIDER_WORD_TIMINGS"
    DETERMINISTIC_FALLBACK = "DETERMINISTIC_FALLBACK"


class WordTiming(BaseModel):
    """Word-level timing information strictly validated."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    word: str = Field(..., description="Spoken word token")
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")

    @field_validator("word", mode="before")
    @classmethod
    def _validate_word(cls, v: Any) -> str:
        if not isinstance(v, str) or not v.strip():
            raise MotionBeatTimingError("Word token cannot be empty or whitespace-only")
        return v.strip()

    @field_validator("start", "end", mode="before")
    @classmethod
    def _validate_finite(cls, v: Any) -> float:
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise MotionBeatTimingError(f"Timestamp must be a valid float, got {v}")
        if not math.isfinite(val):
            raise MotionBeatTimingError(f"Timestamp must be finite, got {v}")
        if val < 0.0:
            raise MotionBeatTimingError(f"Timestamp cannot be negative, got {v}")
        return val

    @model_validator(mode="after")
    def _validate_interval(self) -> "WordTiming":
        if self.end < self.start:
            raise MotionBeatTimingError(
                f"Word '{self.word}' end ({self.end}) must be >= start ({self.start})"
            )
        return self


class PhraseTiming(BaseModel):
    """Deterministic phrase grouping of consecutive words or text segment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1, description="Unique phrase identifier")
    text: str = Field(..., min_length=1, description="Phrase text content")
    start: float = Field(..., ge=0.0, description="Phrase start timestamp in seconds")
    end: float = Field(..., ge=0.0, description="Phrase end timestamp in seconds")
    words: tuple[WordTiming, ...] = Field(
        default_factory=tuple,
        description="Underlying word timings if available",
    )

    @field_validator("start", "end")
    @classmethod
    def _validate_finite(cls, v: float) -> float:
        if not math.isfinite(v) or v < 0.0:
            raise MotionBeatTimingError(f"Phrase timestamp must be finite non-negative, got {v}")
        return float(v)

    @model_validator(mode="after")
    def _validate_interval(self) -> "PhraseTiming":
        if self.end < self.start:
            raise MotionBeatTimingError(
                f"Phrase '{self.id}' end ({self.end}) must be >= start ({self.start})"
            )
        if self.words:
            min_w_start = min(w.start for w in self.words)
            max_w_end = max(w.end for w in self.words)
            if min_w_start < self.start - 1e-6 or max_w_end > self.end + 1e-6:
                raise MotionBeatTimingError(
                    f"Phrase '{self.id}' interval [{self.start}, {self.end}] does not contain all words [{min_w_start}, {max_w_end}]"
                )
        return self


class SemanticBeat(BaseModel):
    """A semantic beat in the narration used to anchor motion triggers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1, description="Unique, stable beat identifier")
    name: str = Field(..., min_length=1, description="Descriptive semantic beat label")
    start: float = Field(..., ge=0.0, description="Anchor start timestamp in seconds")
    end: float | None = Field(default=None, description="Optional beat span end in seconds")
    phrase_id: str | None = Field(default=None, description="Associated phrase ID if any")
    text: str = Field(default="", description="Associated narration text")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Provenance confidence score")

    @field_validator("start")
    @classmethod
    def _validate_start(cls, v: float) -> float:
        if not math.isfinite(v) or v < 0.0:
            raise MotionBeatTimingError(f"Beat start time must be finite non-negative, got {v}")
        return float(v)

    @field_validator("end")
    @classmethod
    def _validate_end(cls, v: float | None) -> float | None:
        if v is not None and (not math.isfinite(v) or v < 0.0):
            raise MotionBeatTimingError(f"Beat end time must be finite non-negative, got {v}")
        return float(v) if v is not None else None

    @model_validator(mode="after")
    def _validate_span(self) -> "SemanticBeat":
        if self.end is not None and self.end < self.start:
            raise MotionBeatTimingError(
                f"Beat '{self.id}' end ({self.end}) must be >= start ({self.start})"
            )
        return self


class NarrationBeatMap(BaseModel):
    """Complete, immutable narration timing artifact for a scene."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scene_id: str = Field(..., min_length=1, description="Scene identifier")
    total_duration: float = Field(..., ge=0.0, description="Total narration audio duration in seconds")
    timing_mode: TimingMode = Field(..., description="Timing provenance mode")
    beats: tuple[SemanticBeat, ...] = Field(
        default_factory=tuple,
        description="Ordered sequence of semantic beats",
    )
    phrases: tuple[PhraseTiming, ...] = Field(
        default_factory=tuple,
        description="Deterministic phrase segments",
    )
    words: tuple[WordTiming, ...] | None = Field(
        default=None,
        description="Word-level timings when provided",
    )

    @field_validator("total_duration")
    @classmethod
    def _validate_duration(cls, v: float) -> float:
        if not math.isfinite(v) or v < 0.0:
            raise MotionBeatTimingError(f"Total duration must be finite non-negative, got {v}")
        return float(v)

    @model_validator(mode="after")
    def _validate_temporal_bounds_and_invariants(self) -> "NarrationBeatMap":
        # 1. Provenance consistency (TimingMode vs words)
        if self.timing_mode == TimingMode.PROVIDER_WORD_TIMINGS:
            if self.words is None or len(self.words) == 0:
                raise MotionBeatTimingError(
                    "NarrationBeatMap with TimingMode.PROVIDER_WORD_TIMINGS requires non-empty words"
                )
        elif self.timing_mode == TimingMode.DETERMINISTIC_FALLBACK:
            if self.words is not None:
                raise MotionBeatTimingError(
                    "NarrationBeatMap with TimingMode.DETERMINISTIC_FALLBACK cannot contain words"
                )

        # 2. Phrase uniqueness, bounds, and monotonicity
        seen_phrase_ids: set[str] = set()
        phrases_by_id: dict[str, PhraseTiming] = {}
        prev_phrase_end: float = 0.0
        for idx, p in enumerate(self.phrases):
            if p.id in seen_phrase_ids:
                raise MotionBeatTimingError(f"Duplicate phrase ID '{p.id}' in NarrationBeatMap")
            seen_phrase_ids.add(p.id)
            phrases_by_id[p.id] = p

            if p.start < 0.0 or p.end > self.total_duration + 1e-6:
                raise MotionBeatTimingError(
                    f"Phrase '{p.id}' span [{p.start}, {p.end}] lies outside narration duration [0, {self.total_duration}]"
                )
            if idx > 0 and p.start < prev_phrase_end - 1e-6:
                raise MotionBeatTimingError(
                    f"Phrases non-monotonic: phrase '{p.id}' start ({p.start}) < previous phrase end ({prev_phrase_end})"
                )
            prev_phrase_end = p.end

        # 3. Beats uniqueness, bounds, and phrase cross-reference integrity
        seen_beat_ids: set[str] = set()
        for b in self.beats:
            if b.id in seen_beat_ids:
                raise MotionBeatTimingError(f"Duplicate beat ID '{b.id}' in NarrationBeatMap")
            seen_beat_ids.add(b.id)

            if b.start < 0.0 or b.start > self.total_duration + 1e-6:
                raise MotionBeatTimingError(
                    f"Beat '{b.id}' start ({b.start}) lies outside narration duration [0, {self.total_duration}]"
                )
            if b.end is not None:
                if b.end < b.start or b.end > self.total_duration + 1e-6:
                    raise MotionBeatTimingError(
                        f"Beat '{b.id}' end ({b.end}) lies outside narration duration [{b.start}, {self.total_duration}]"
                    )

            # Phrase cross-reference integrity
            if b.phrase_id is not None:
                if b.phrase_id not in phrases_by_id:
                    raise MotionBeatTimingError(
                        f"Beat '{b.id}' references unknown phrase_id '{b.phrase_id}' in NarrationBeatMap"
                    )
                p = phrases_by_id[b.phrase_id]
                if b.start < p.start - 1e-6 or b.start > p.end + 1e-6:
                    raise MotionBeatTimingError(
                        f"Beat '{b.id}' start ({b.start}) is outside associated phrase '{p.id}' span [{p.start}, {p.end}]"
                    )
                if b.end is not None and b.end > p.end + 1e-6:
                    raise MotionBeatTimingError(
                        f"Beat '{b.id}' end ({b.end}) exceeds associated phrase '{p.id}' end ({p.end})"
                    )

        # 4. Words bounds and non-overlapping monotonicity (when present)
        if self.words is not None:
            prev_word_end: float = 0.0
            for idx, w in enumerate(self.words):
                if w.start < 0.0 or w.end > self.total_duration + 1e-6:
                    raise MotionBeatTimingError(
                        f"Word '{w.word}' span [{w.start}, {w.end}] lies outside narration duration [0, {self.total_duration}]"
                    )
                if idx > 0 and w.start < prev_word_end - 1e-6:
                    raise MotionBeatTimingError(
                        f"Word timings non-monotonic or overlapping: word '{w.word}' start ({w.start}) < previous end ({prev_word_end})"
                    )
                prev_word_end = w.end

        return self

    def get_beat(self, beat_ref: str) -> SemanticBeat | None:
        """Resolve a symbolic beat reference to a SemanticBeat.

        Resolution order:
        1. Exact match on beat.id
        2. Exact match on beat.name (must be unique among beats; raises MotionBeatAmbiguityError if ambiguous)
        3. Case-insensitive match on beat.id
        4. Case-insensitive match on beat.name (must be unique among beats; raises MotionBeatAmbiguityError if ambiguous)
        """
        ref_stripped = beat_ref.strip()
        ref_lower = ref_stripped.lower()

        # 1. Exact ID
        for b in self.beats:
            if b.id == ref_stripped:
                return b

        # 2. Exact Name
        matching_names = [b for b in self.beats if b.name == ref_stripped]
        if len(matching_names) == 1:
            return matching_names[0]
        elif len(matching_names) > 1:
            matching_ids = [b.id for b in matching_names]
            raise MotionBeatAmbiguityError(
                f"Ambiguous beat reference '{beat_ref}' matches multiple beats with name '{ref_stripped}': {matching_ids}"
            )

        # 3. Case-insensitive ID
        matching_ci_ids = [b for b in self.beats if b.id.lower() == ref_lower]
        if len(matching_ci_ids) == 1:
            return matching_ci_ids[0]
        elif len(matching_ci_ids) > 1:
            matching_ids = [b.id for b in matching_ci_ids]
            raise MotionBeatAmbiguityError(
                f"Ambiguous beat reference '{beat_ref}' matches multiple beats with case-insensitive ID: {matching_ids}"
            )

        # 4. Case-insensitive Name
        matching_ci_names = [b for b in self.beats if b.name.lower() == ref_lower]
        if len(matching_ci_names) == 1:
            return matching_ci_names[0]
        elif len(matching_ci_names) > 1:
            matching_ids = [b.id for b in matching_ci_names]
            raise MotionBeatAmbiguityError(
                f"Ambiguous beat reference '{beat_ref}' matches multiple beats with case-insensitive name: {matching_ids}"
            )

        return None

    def to_canonical_json(self) -> str:
        """Serialize NarrationBeatMap to canonical deterministic JSON."""
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, json_str: str) -> "NarrationBeatMap":
        """Deserialize from canonical JSON."""
        return cls.model_validate_json(json_str)


class ResolvedEventTiming(BaseModel):
    """Resolved timing coordinates for a single motion event."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(..., min_length=1, description="Motion event ID")
    beat_id: str = Field(..., min_length=1, description="Resolved semantic beat ID")
    time: float = Field(..., description="Resolved event start time in seconds")
    target: str = Field(..., min_length=1, description="Event target entity")
    verb: MotionVerb = Field(..., description="Motion category/verb")
    style: MotionStyle = Field(..., description="Motion style/action")

    @field_validator("time", mode="before")
    @classmethod
    def _validate_time(cls, v: Any) -> float:
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise MotionBeatTimingError(f"Event timing must be a valid float, got {v}")
        if not math.isfinite(val):
            raise MotionBeatTimingError(f"Event timing must be finite, got {v}")
        if val < 0.0:
            raise MotionBeatTimingError(f"Event timing cannot be negative, got {v}")
        return val


class ResolvedMotionPlanTiming(BaseModel):
    """Complete, immutable timing resolution artifact for a MotionPlan.

    Separates the timing result from the pure semantic MotionPlan.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    scene_id: str = Field(..., min_length=1, description="Scene identifier matching MotionPlan")
    timing_mode: TimingMode = Field(..., description="Timing provenance mode")
    event_timings: tuple[ResolvedEventTiming, ...] = Field(
        default_factory=tuple,
        description="Resolved event timings in narrative order",
    )
    untriggered_events: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Event IDs without triggers, scheduled by downstream scheduler",
    )

    @model_validator(mode="after")
    def _validate_invariants(self) -> "ResolvedMotionPlanTiming":
        seen_event_ids: set[str] = set()
        prev_time: float = -1.0
        prev_id: str = ""

        for ev in self.event_timings:
            if ev.event_id in seen_event_ids:
                raise MotionBeatTimingError(
                    f"Duplicate event ID '{ev.event_id}' in ResolvedMotionPlanTiming"
                )
            seen_event_ids.add(ev.event_id)

            if prev_time >= 0.0 and ev.time < prev_time - 1e-6:
                raise MotionBeatTimingError(
                    f"ResolvedMotionPlanTiming event timings must be non-decreasing in narrative order: "
                    f"event '{ev.event_id}' at {ev.time:.2f}s is earlier than preceding event '{prev_id}' at {prev_time:.2f}s"
                )
            prev_time = ev.time
            prev_id = ev.event_id

        seen_untriggered: set[str] = set()
        for u_id in self.untriggered_events:
            if u_id in seen_event_ids:
                raise MotionBeatTimingError(
                    f"Event ID '{u_id}' cannot appear in both event_timings and untriggered_events"
                )
            if u_id in seen_untriggered:
                raise MotionBeatTimingError(
                    f"Duplicate untriggered event ID '{u_id}' in ResolvedMotionPlanTiming"
                )
            seen_untriggered.add(u_id)

        return self

    def get_event_time(self, event_id: str) -> float | None:
        """Return resolved timing in seconds for a specific event ID, if triggered."""
        for ev in self.event_timings:
            if ev.event_id == event_id:
                return ev.time
        return None

    def to_canonical_json(self) -> str:
        """Serialize ResolvedMotionPlanTiming to canonical deterministic JSON."""
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, json_str: str) -> "ResolvedMotionPlanTiming":
        """Deserialize from canonical JSON."""
        return cls.model_validate_json(json_str)


# =========================================================================
# Validation and Grouping Algorithms
# =========================================================================

def validate_word_timings(words: Sequence[WordTiming]) -> tuple[WordTiming, ...]:
    """Validate word timings sequence.

    Ensures timestamps are non-overlapping single-speaker intervals:
    current.start >= previous.end (equal boundaries are valid).
    Raises MotionBeatTimingError if overlapping, regressing, non-finite, or malformed.
    """
    if not words:
        return ()

    prev_end: float = 0.0
    validated: list[WordTiming] = []

    for idx, w in enumerate(words):
        if not isinstance(w, WordTiming):
            raise MotionBeatTimingError(f"Element at index {idx} is not a WordTiming instance: {type(w)}")
        if idx > 0 and w.start < prev_end - 1e-6:
            raise MotionBeatTimingError(
                f"Word timings non-monotonic or overlapping at index {idx}: word '{w.word}' start ({w.start}) "
                f"< previous word end ({prev_end})"
            )
        prev_end = w.end
        validated.append(w)

    return tuple(validated)


def group_words_into_phrases(
    words: Sequence[WordTiming],
    phrase_hints: Sequence[str] | None = None,
    pause_threshold: float = 0.35,
    max_words_per_phrase: int = 8,
) -> tuple[PhraseTiming, ...]:
    """Deterministically group word timings into phrases.

    - If phrase_hints are provided (structured script clauses), aligns words to hints sequentially.
    - Otherwise, groups by punctuation boundaries (. , ; ! ?), pause gaps, and length limits.
    """
    valid_words = validate_word_timings(words)
    if not valid_words:
        return ()

    phrases: list[PhraseTiming] = []

    if phrase_hints:
        clean_hints = [h.strip() for h in phrase_hints if h.strip()]
        word_idx = 0
        total_words = len(valid_words)

        for p_idx, hint in enumerate(clean_hints):
            if word_idx >= total_words:
                break
            hint_tokens = [t for t in re.split(r"\s+", hint) if t]
            count = len(hint_tokens)
            # Take count words or up to end
            group = valid_words[word_idx : min(word_idx + count, total_words)]
            if group:
                word_idx += len(group)
                phrases.append(
                    PhraseTiming(
                        id=f"phrase_{p_idx}",
                        text=" ".join(w.word for w in group),
                        start=group[0].start,
                        end=group[-1].end,
                        words=group,
                    )
                )

        # Catch-up any trailing words
        if word_idx < total_words:
            tail_group = valid_words[word_idx:]
            phrases.append(
                PhraseTiming(
                    id=f"phrase_{len(phrases)}",
                    text=" ".join(w.word for w in tail_group),
                    start=tail_group[0].start,
                    end=tail_group[-1].end,
                    words=tail_group,
                )
            )
    else:
        current_group: list[WordTiming] = []
        p_idx = 0

        for idx, w in enumerate(valid_words):
            current_group.append(w)
            is_last = idx == len(valid_words) - 1

            ends_with_punct = bool(re.search(r"[.!?,;\n]$", w.word))
            has_pause = False
            if not is_last:
                next_w = valid_words[idx + 1]
                if next_w.start - w.end >= pause_threshold:
                    has_pause = True

            exceeds_max = len(current_group) >= max_words_per_phrase

            if is_last or ends_with_punct or has_pause or exceeds_max:
                phrases.append(
                    PhraseTiming(
                        id=f"phrase_{p_idx}",
                        text=" ".join(gw.word for gw in current_group),
                        start=current_group[0].start,
                        end=current_group[-1].end,
                        words=tuple(current_group),
                    )
                )
                p_idx += 1
                current_group = []

    return tuple(phrases)


# =========================================================================
# Narration Beat Map Factories
# =========================================================================

def _normalize_token(text: str) -> str:
    """Normalize text token for semantic matching."""
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def create_narration_beat_map_from_word_timings(
    scene_id: str,
    words: Sequence[WordTiming],
    phrase_hints: Sequence[str] | None = None,
    beat_definitions: Sequence[dict[str, Any] | str] | None = None,
    total_duration: float | None = None,
) -> NarrationBeatMap:
    """Create a NarrationBeatMap from provider word timestamps."""
    if not scene_id or not scene_id.strip():
        raise MotionBeatTimingError("scene_id cannot be empty")

    valid_words = validate_word_timings(words)
    if not valid_words:
        raise MotionBeatTimingError("Word timings sequence cannot be empty for word-level alignment")

    calculated_duration = valid_words[-1].end
    if total_duration is not None:
        if not math.isfinite(total_duration) or total_duration < calculated_duration:
            raise MotionBeatTimingError(
                f"total_duration ({total_duration}) cannot be less than last word end ({calculated_duration})"
            )
        duration = float(total_duration)
    else:
        duration = calculated_duration

    phrases = group_words_into_phrases(valid_words, phrase_hints=phrase_hints)
    beats: list[SemanticBeat] = []

    if beat_definitions:
        for b_idx, b_def in enumerate(beat_definitions):
            explicit_phrase_idx: int | None = None
            if isinstance(b_def, str):
                b_id = b_def.strip()
                b_name = b_id
                target_key = _normalize_token(b_id)
            elif isinstance(b_def, dict):
                b_id = str(b_def.get("id", f"beat_{b_idx}")).strip()
                b_name = str(b_def.get("name", b_id)).strip()
                target_key = _normalize_token(str(b_def.get("keyword", b_name)))
                if "phrase_index" in b_def:
                    explicit_phrase_idx = int(b_def["phrase_index"])
            else:
                raise MotionBeatTimingError(f"Unsupported beat definition type: {type(b_def)}")

            # 1. Try to match word directly
            matched_word: WordTiming | None = None
            if target_key:
                for w in valid_words:
                    norm_w = _normalize_token(w.word)
                    if norm_w == target_key or (len(target_key) > 2 and norm_w.startswith(target_key)):
                        matched_word = w
                        break

            if matched_word is not None:
                beats.append(
                    SemanticBeat(
                        id=b_id,
                        name=b_name,
                        start=matched_word.start,
                        end=matched_word.end,
                        text=matched_word.word,
                        confidence=1.0,
                    )
                )
                continue

            # 2. Try to match phrase
            matched_phrase: PhraseTiming | None = None
            if target_key:
                for p in phrases:
                    if target_key in _normalize_token(p.text):
                        matched_phrase = p
                        break

            if matched_phrase is not None:
                beats.append(
                    SemanticBeat(
                        id=b_id,
                        name=b_name,
                        start=matched_phrase.start,
                        end=matched_phrase.end,
                        phrase_id=matched_phrase.id,
                        text=matched_phrase.text,
                        confidence=0.9,
                    )
                )
                continue

            # 3. Explicit phrase index binding
            if explicit_phrase_idx is not None:
                if 0 <= explicit_phrase_idx < len(phrases):
                    p = phrases[explicit_phrase_idx]
                    beats.append(
                        SemanticBeat(
                            id=b_id,
                            name=b_name,
                            start=p.start,
                            end=p.end,
                            phrase_id=p.id,
                            text=p.text,
                            confidence=0.8,
                        )
                    )
                    continue
                else:
                    raise MotionBeatTimingError(
                        f"Explicit phrase_index {explicit_phrase_idx} for beat '{b_id}' is out of range [0, {len(phrases)})"
                    )

            # 4. Unknown beat: reject explicitly, no silent substitution!
            raise MotionUnknownBeatError(
                f"Semantic beat definition '{b_id}' (keyword: '{target_key}') cannot be matched "
                f"to words or phrases in scene '{scene_id}'"
            )
    else:
        # Default: 1 beat per phrase
        for idx, p in enumerate(phrases):
            beats.append(
                SemanticBeat(
                    id=f"beat_{idx}",
                    name=p.text,
                    start=p.start,
                    end=p.end,
                    phrase_id=p.id,
                    text=p.text,
                    confidence=1.0,
                )
            )

    return NarrationBeatMap(
        scene_id=scene_id.strip(),
        total_duration=duration,
        timing_mode=TimingMode.PROVIDER_WORD_TIMINGS,
        beats=tuple(beats),
        phrases=phrases,
        words=valid_words,
    )


def create_narration_beat_map_fallback(
    scene_id: str,
    narration_text: str,
    total_duration: float,
    phrase_hints: Sequence[str] | None = None,
    beat_definitions: Sequence[dict[str, Any] | str] | None = None,
) -> NarrationBeatMap:
    """Create a NarrationBeatMap via deterministic interpolation without word timestamps (PLAN A9).

    Uses structured script phrases or text segmentation combined with measured audio duration.
    Produces monotonic, deterministic timings covering [0, total_duration].
    """
    if not scene_id or not scene_id.strip():
        raise MotionBeatTimingError("scene_id cannot be empty")
    if not narration_text or not narration_text.strip():
        raise MotionBeatTimingError("narration_text cannot be empty or whitespace-only for fallback alignment")
    if not math.isfinite(total_duration) or total_duration <= 0.0:
        raise MotionBeatTimingError(
            f"total_duration must be positive and finite for fallback alignment, got {total_duration}"
        )

    # 1. Determine segments
    segments: list[str]
    if phrase_hints:
        segments = [h.strip() for h in phrase_hints if h.strip()]
        if not segments:
            segments = [narration_text.strip()]
    else:
        # Split by sentences if sentence endings exist, otherwise clauses
        if re.search(r"[.!?\n]\s+", narration_text.strip()):
            raw = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", narration_text.strip()) if s.strip()]
        else:
            raw = [s.strip() for s in re.split(r"(?<=[.!?,;\n])\s+", narration_text.strip()) if s.strip()]
        segments = raw if raw else [narration_text.strip()]

    # 2. Weights based on character lengths (excluding whitespace/punctuation)
    weights: list[int] = []
    for s in segments:
        clean_len = len(re.sub(r"[\s\W]+", "", s))
        weights.append(max(clean_len, 1))

    total_weight = sum(weights)
    phrases: list[PhraseTiming] = []
    accum_weight = 0

    for idx, (seg, w) in enumerate(zip(segments, weights)):
        start = round((accum_weight / total_weight) * total_duration, 4)
        accum_weight += w
        end = round((accum_weight / total_weight) * total_duration, 4)
        if idx == 0:
            start = 0.0
        if idx == len(segments) - 1:
            end = float(total_duration)

        phrases.append(
            PhraseTiming(
                id=f"phrase_{idx}",
                text=seg,
                start=start,
                end=end,
                words=(),
            )
        )

    # 3. Create beats
    beats: list[SemanticBeat] = []
    if beat_definitions:
        for b_idx, b_def in enumerate(beat_definitions):
            explicit_phrase_idx: int | None = None
            if isinstance(b_def, str):
                b_id = b_def.strip()
                b_name = b_id
                target_key = _normalize_token(b_id)
            elif isinstance(b_def, dict):
                b_id = str(b_def.get("id", f"beat_{b_idx}")).strip()
                b_name = str(b_def.get("name", b_id)).strip()
                target_key = _normalize_token(str(b_def.get("keyword", b_name)))
                if "phrase_index" in b_def:
                    explicit_phrase_idx = int(b_def["phrase_index"])
            else:
                raise MotionBeatTimingError(f"Unsupported beat definition type: {type(b_def)}")

            matched_phrase: PhraseTiming | None = None
            if target_key:
                for p in phrases:
                    if target_key in _normalize_token(p.text):
                        matched_phrase = p
                        break

            if matched_phrase is not None:
                beats.append(
                    SemanticBeat(
                        id=b_id,
                        name=b_name,
                        start=matched_phrase.start,
                        end=matched_phrase.end,
                        phrase_id=matched_phrase.id,
                        text=matched_phrase.text,
                        confidence=0.8,
                    )
                )
                continue

            if explicit_phrase_idx is not None:
                if 0 <= explicit_phrase_idx < len(phrases):
                    p = phrases[explicit_phrase_idx]
                    beats.append(
                        SemanticBeat(
                            id=b_id,
                            name=b_name,
                            start=p.start,
                            end=p.end,
                            phrase_id=p.id,
                            text=p.text,
                            confidence=0.7,
                        )
                    )
                    continue
                else:
                    raise MotionBeatTimingError(
                        f"Explicit phrase_index {explicit_phrase_idx} for beat '{b_id}' is out of range [0, {len(phrases)})"
                    )

            # Unknown beat in fallback: reject explicitly!
            raise MotionUnknownBeatError(
                f"Semantic beat definition '{b_id}' (keyword: '{target_key}') cannot be matched "
                f"to fallback narration segments in scene '{scene_id}'"
            )
    else:
        for idx, p in enumerate(phrases):
            beats.append(
                SemanticBeat(
                    id=f"beat_{idx}",
                    name=p.text,
                    start=p.start,
                    end=p.end,
                    phrase_id=p.id,
                    text=p.text,
                    confidence=0.8,
                )
            )

    return NarrationBeatMap(
        scene_id=scene_id.strip(),
        total_duration=float(total_duration),
        timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
        beats=tuple(beats),
        phrases=tuple(phrases),
        words=None,
    )


def create_narration_beat_map(
    scene_id: str,
    narration_text: str,
    total_duration: float | None = None,
    words: Sequence[WordTiming] | None = None,
    phrase_hints: Sequence[str] | None = None,
    beat_definitions: Sequence[dict[str, Any] | str] | None = None,
) -> NarrationBeatMap:
    """Unified entry point for creating a NarrationBeatMap.

    Automatically uses provider word timings when provided, or falls back to
    deterministic interpolation with measured audio duration.
    """
    if words:
        return create_narration_beat_map_from_word_timings(
            scene_id=scene_id,
            words=words,
            phrase_hints=phrase_hints,
            beat_definitions=beat_definitions,
            total_duration=total_duration,
        )

    if total_duration is None:
        raise MotionBeatTimingError(
            "total_duration must be supplied when words timestamps are not available"
        )

    return create_narration_beat_map_fallback(
        scene_id=scene_id,
        narration_text=narration_text,
        total_duration=total_duration,
        phrase_hints=phrase_hints,
        beat_definitions=beat_definitions,
    )


def create_beat_map_from_subtitle_cues(
    scene_id: str,
    cues: Sequence[Any],
    total_duration: float | None = None,
    scene_start_seconds: float = 0.0,
    beat_definitions: Sequence[dict[str, Any] | str] | None = None,
) -> NarrationBeatMap:
    """Adapter to construct a scene-local NarrationBeatMap from V1 SubtitleCue objects.

    Contract:
    - Coordinates must be scene-local.
    - If cues are in lesson/global coordinates, provide scene_start_seconds to normalize:
      local_time = global_time - scene_start_seconds.
    - All local cue timings must satisfy 0 <= local_start <= local_end <= total_duration.
    - Rejects cues exceeding total_duration with MotionBeatTimingError.
    """
    if not cues:
        raise MotionBeatTimingError("Cannot create beat map from empty subtitle cues")

    phrases: list[PhraseTiming] = []
    for idx, cue in enumerate(cues):
        raw_start = float(getattr(cue, "start_seconds", getattr(cue, "start", 0.0)))
        raw_end = float(getattr(cue, "end_seconds", getattr(cue, "end", raw_start)))
        text = str(getattr(cue, "text", "")).strip()

        local_start = round(raw_start - scene_start_seconds, 4)
        local_end = round(raw_end - scene_start_seconds, 4)

        if local_start < 0.0:
            raise MotionBeatTimingError(
                f"Subtitle cue start ({local_start}s) is negative after applying scene_start_seconds ({scene_start_seconds}s)"
            )
        if local_end < local_start:
            raise MotionBeatTimingError(
                f"Subtitle cue end ({local_end}s) must be >= start ({local_start}s)"
            )

        phrases.append(
            PhraseTiming(
                id=f"phrase_{idx}",
                text=text,
                start=local_start,
                end=local_end,
                words=(),
            )
        )

    max_end = phrases[-1].end if phrases else 0.0
    if total_duration is not None:
        if max_end > float(total_duration) + 1e-4:
            raise MotionBeatTimingError(
                f"Subtitle cue end ({max_end}s) exceeds total_duration ({total_duration}s)"
            )
        duration = float(total_duration)
    else:
        duration = max_end

    beats: list[SemanticBeat] = []
    if beat_definitions:
        for b_idx, b_def in enumerate(beat_definitions):
            explicit_phrase_idx: int | None = None
            if isinstance(b_def, str):
                b_id = b_def.strip()
                b_name = b_id
                target_key = _normalize_token(b_id)
            elif isinstance(b_def, dict):
                b_id = str(b_def.get("id", f"beat_{b_idx}")).strip()
                b_name = str(b_def.get("name", b_id)).strip()
                target_key = _normalize_token(str(b_def.get("keyword", b_name)))
                if "phrase_index" in b_def:
                    explicit_phrase_idx = int(b_def["phrase_index"])
            else:
                raise MotionBeatTimingError(f"Unsupported beat definition type: {type(b_def)}")

            matched_phrase = next((p for p in phrases if target_key in _normalize_token(p.text)), None)
            if matched_phrase:
                beats.append(
                    SemanticBeat(
                        id=b_id,
                        name=b_name,
                        start=matched_phrase.start,
                        end=matched_phrase.end,
                        phrase_id=matched_phrase.id,
                        text=matched_phrase.text,
                    )
                )
                continue

            if explicit_phrase_idx is not None and 0 <= explicit_phrase_idx < len(phrases):
                p = phrases[explicit_phrase_idx]
                beats.append(
                    SemanticBeat(
                        id=b_id,
                        name=b_name,
                        start=p.start,
                        end=p.end,
                        phrase_id=p.id,
                        text=p.text,
                    )
                )
                continue

            raise MotionUnknownBeatError(
                f"Semantic beat definition '{b_id}' cannot be matched in subtitle cues for scene '{scene_id}'"
            )
    else:
        for idx, p in enumerate(phrases):
            beats.append(
                SemanticBeat(
                    id=f"beat_{idx}",
                    name=p.text,
                    start=p.start,
                    end=p.end,
                    phrase_id=p.id,
                    text=p.text,
                )
            )

    return NarrationBeatMap(
        scene_id=scene_id,
        total_duration=duration,
        timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
        beats=tuple(beats),
        phrases=tuple(phrases),
        words=None,
    )


# =========================================================================
# MotionPlan Trigger Resolution
# =========================================================================

def resolve_motion_plan_timing(
    plan: MotionPlan,
    beat_map: NarrationBeatMap,
) -> ResolvedMotionPlanTiming:
    """Resolve MotionPlan event triggers against a scene NarrationBeatMap.

    - Resolves symbolic trigger.beat to exact narration timing.
    - Preserves narrative order of events.
    - Enforces that resolved event timings are non-decreasing in narrative order.
    - Explicitly raises MotionBeatTimingError if narrative order conflicts with timing.
    - Explicitly raises MotionUnknownBeatError for any unrecognized beat reference.
    - Explicitly raises MotionSceneMismatchError if scene_ids do not match.
    - Untriggered events are collected for downstream scheduling without throwing.
    """
    if plan.scene_id != beat_map.scene_id:
        raise MotionSceneMismatchError(
            f"MotionPlan scene_id '{plan.scene_id}' does not match NarrationBeatMap scene_id '{beat_map.scene_id}'"
        )

    resolved_events: list[ResolvedEventTiming] = []
    untriggered: list[str] = []
    prev_time: float = -1.0
    prev_ev_id: str = ""

    for ev in plan.events:
        if ev.trigger is not None:
            beat = beat_map.get_beat(ev.trigger.beat)
            if beat is None:
                available = [b.id for b in beat_map.beats]
                raise MotionUnknownBeatError(
                    f"Motion event '{ev.id}' in scene '{plan.scene_id}' references unknown beat '{ev.trigger.beat}'. "
                    f"Available beats in map: {available}"
                )

            # Enforce that resolved event times are non-decreasing in narrative order
            if prev_time >= 0.0 and beat.start < prev_time - 1e-6:
                raise MotionBeatTimingError(
                    f"MotionPlan narrative event order conflicts with resolved beat timing in scene '{plan.scene_id}': "
                    f"event '{ev.id}' resolved to {beat.start:.2f}s (beat '{beat.id}') which is earlier than "
                    f"preceding narrative event '{prev_ev_id}' resolved to {prev_time:.2f}s"
                )

            resolved_events.append(
                ResolvedEventTiming(
                    event_id=ev.id,
                    beat_id=beat.id,
                    time=beat.start,
                    target=ev.target,
                    verb=ev.verb,
                    style=ev.style,
                )
            )
            prev_time = beat.start
            prev_ev_id = ev.id
        else:
            untriggered.append(ev.id)

    return ResolvedMotionPlanTiming(
        scene_id=plan.scene_id,
        timing_mode=beat_map.timing_mode,
        event_timings=tuple(resolved_events),
        untriggered_events=tuple(untriggered),
    )
