"""Comprehensive test suite for LearnFlow V2 — CP 2.8: Narration Beat Alignment."""

import math
import pytest
from pydantic import ValidationError

from learnflow_v2.core.errors import (
    MotionBeatAmbiguityError,
    MotionBeatTimingError,
    MotionSceneMismatchError,
    MotionUnknownBeatError,
)
from learnflow_v2.motion import (
    MotionEvent,
    MotionPlan,
    MotionStyle,
    MotionTargetKind,
    MotionTrigger,
    MotionVerb,
    NarrationBeatMap,
    PhraseTiming,
    ResolvedEventTiming,
    ResolvedMotionPlanTiming,
    SemanticBeat,
    TimingMode,
    WordTiming,
    create_beat_map_from_subtitle_cues,
    create_narration_beat_map,
    create_narration_beat_map_fallback,
    create_narration_beat_map_from_word_timings,
    group_words_into_phrases,
    resolve_motion_plan_timing,
    validate_word_timings,
)


# =========================================================================
# 1. Strict Word Timing Validation & Overlap Invariants (BLOCKER 2)
# =========================================================================

def test_word_timing_valid():
    """Valid WordTiming parses and preserves exact floats."""
    w = WordTiming(word="prediction", start=0.5, end=1.2)
    assert w.word == "prediction"
    assert w.start == 0.5
    assert w.end == 1.2


def test_word_timing_rejects_negative_timestamps():
    """Negative start or end must raise MotionBeatTimingError."""
    with pytest.raises(MotionBeatTimingError):
        WordTiming(word="test", start=-0.1, end=1.0)

    with pytest.raises(MotionBeatTimingError):
        WordTiming(word="test", start=0.0, end=-0.5)


def test_word_timing_rejects_nan_and_inf():
    """NaN and inf values must raise MotionBeatTimingError."""
    with pytest.raises(MotionBeatTimingError):
        WordTiming(word="test", start=float("nan"), end=1.0)

    with pytest.raises(MotionBeatTimingError):
        WordTiming(word="test", start=0.0, end=float("inf"))


def test_word_timing_rejects_end_before_start():
    """end < start must raise MotionBeatTimingError."""
    with pytest.raises(MotionBeatTimingError):
        WordTiming(word="test", start=1.5, end=1.2)


def test_word_timing_rejects_blank_word():
    """Empty or whitespace-only word token must raise MotionBeatTimingError."""
    with pytest.raises(MotionBeatTimingError):
        WordTiming(word="   ", start=0.0, end=0.5)

    with pytest.raises(MotionBeatTimingError):
        WordTiming(word="", start=0.0, end=0.5)


def test_validate_word_timings_rejects_overlapping_intervals():
    """Overlapping word intervals (e.g. 0->10 and 1->2) must be rejected explicitly."""
    w1 = WordTiming(word="first", start=0.0, end=10.0)
    w2 = WordTiming(word="second", start=1.0, end=2.0)

    with pytest.raises(MotionBeatTimingError) as exc_info:
        validate_word_timings([w1, w2])
    assert "overlapping" in str(exc_info.value).lower()


def test_validate_word_timings_accepts_adjacent_boundaries():
    """Adjacent words where prev.end == next.start must be accepted cleanly."""
    w1 = WordTiming(word="first", start=0.0, end=1.0)
    w2 = WordTiming(word="second", start=1.0, end=2.5)

    validated = validate_word_timings([w1, w2])
    assert len(validated) == 2
    assert validated[0].end == validated[1].start


def test_validate_word_timings_rejects_backwards_start():
    """Backwards start must raise MotionBeatTimingError."""
    w1 = WordTiming(word="first", start=2.0, end=2.5)
    w2 = WordTiming(word="second", start=1.5, end=2.8)

    with pytest.raises(MotionBeatTimingError):
        validate_word_timings([w1, w2])


def test_validate_word_timings_empty():
    """Empty sequence returns empty tuple cleanly."""
    assert validate_word_timings([]) == ()


def test_phrase_timing_contains_every_word_interval():
    """Phrase interval must enclose all contained word intervals."""
    w1 = WordTiming(word="a", start=0.5, end=1.0)
    w2 = WordTiming(word="b", start=1.0, end=2.0)

    # Valid phrase interval enclosing both
    p_ok = PhraseTiming(id="p1", text="a b", start=0.5, end=2.0, words=(w1, w2))
    assert p_ok.start == 0.5

    # Invalid: phrase end earlier than word end
    with pytest.raises(MotionBeatTimingError):
        PhraseTiming(id="p_bad", text="a b", start=0.5, end=1.5, words=(w1, w2))

    # Invalid: phrase start later than word start
    with pytest.raises(MotionBeatTimingError):
        PhraseTiming(id="p_bad2", text="a b", start=0.8, end=2.0, words=(w1, w2))


# =========================================================================
# 2. NarrationBeatMap Temporal Bounds Invariants (BLOCKER 1)
# =========================================================================

def test_narration_beat_map_rejects_beat_outside_total_duration():
    """Direct construction with beat outside total_duration must raise MotionBeatTimingError."""
    late_beat = SemanticBeat(id="late", name="late", start=5.0, end=6.0)

    with pytest.raises(MotionBeatTimingError) as exc_info:
        NarrationBeatMap(
            scene_id="s",
            total_duration=1.0,
            timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
            beats=(late_beat,),
        )
    assert "lies outside narration duration" in str(exc_info.value)


def test_narration_beat_map_rejects_phrase_outside_total_duration():
    """Direct construction with phrase outside total_duration must raise MotionBeatTimingError."""
    late_phrase = PhraseTiming(id="p_late", text="late", start=2.0, end=3.0)

    with pytest.raises(MotionBeatTimingError) as exc_info:
        NarrationBeatMap(
            scene_id="s",
            total_duration=1.5,
            timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
            phrases=(late_phrase,),
        )
    assert "lies outside narration duration" in str(exc_info.value)


def test_narration_beat_map_rejects_non_monotonic_phrases():
    """Phrases that regress in start time must be rejected."""
    p1 = PhraseTiming(id="p1", text="first", start=0.0, end=2.0)
    p2 = PhraseTiming(id="p2", text="second", start=1.5, end=3.0)  # starts before p1 ends

    with pytest.raises(MotionBeatTimingError) as exc_info:
        NarrationBeatMap(
            scene_id="s",
            total_duration=5.0,
            timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
            phrases=(p1, p2),
        )
    assert "non-monotonic" in str(exc_info.value).lower()


def test_canonical_deserialization_rejects_impossible_timing_artifact():
    """Deserializing impossible temporal artifact from JSON must fail validation."""
    impossible_json = """{
        "scene_id": "scene_leak",
        "total_duration": 1.0,
        "timing_mode": "DETERMINISTIC_FALLBACK",
        "beats": [
            {
                "id": "beat_out_of_bounds",
                "name": "out",
                "start": 5.0,
                "end": 6.0,
                "confidence": 1.0,
                "text": ""
            }
        ],
        "phrases": []
    }"""
    with pytest.raises((MotionBeatTimingError, ValidationError)):
        NarrationBeatMap.from_canonical_json(impossible_json)


# =========================================================================
# 3. Unmatched Semantic Beats Must Fail (BLOCKER 3)
# =========================================================================

def test_unmatched_provider_semantic_beat_fails_explicitly():
    """A semantic beat definition not in narration must raise MotionUnknownBeatError.

    Must NOT silently fall back to phrase_0 or an interpolated position.
    """
    words = [
        WordTiming(word="alpha", start=0.0, end=0.5),
        WordTiming(word="beta.", start=0.5, end=1.0),
    ]

    with pytest.raises(MotionUnknownBeatError) as exc_info:
        create_narration_beat_map_from_word_timings(
            scene_id="s1",
            words=words,
            beat_definitions=["not_in_narration"],
        )
    assert "not_in_narration" in str(exc_info.value)


def test_unmatched_fallback_semantic_beat_fails_explicitly():
    """Fallback mode must also reject unknown semantic beat definition without silent index fallback."""
    with pytest.raises(MotionUnknownBeatError) as exc_info:
        create_narration_beat_map_fallback(
            scene_id="s1",
            narration_text="alpha beta gamma.",
            total_duration=3.0,
            beat_definitions=["phantom_keyword"],
        )
    assert "phantom_keyword" in str(exc_info.value)


def test_fallback_explicit_phrase_index_allowed():
    """Explicit phrase_index in structured beat definition is accepted."""
    bm = create_narration_beat_map_fallback(
        scene_id="s1",
        narration_text="First step. Second step.",
        total_duration=4.0,
        beat_definitions=[{"id": "b_second", "name": "second", "phrase_index": 1}],
    )
    assert len(bm.beats) == 1
    assert bm.beats[0].id == "b_second"
    assert bm.beats[0].start == bm.phrases[1].start


# =========================================================================
# 4. Subtitle Cue Adapter Contract & Coordinate Space (BLOCKER 4)
# =========================================================================

def test_subtitle_cue_adapter_rejects_cue_exceeding_total_duration():
    """Cue exceeding total_duration must raise MotionBeatTimingError."""
    class MockCue:
        def __init__(self, start: float, end: float, text: str):
            self.start_seconds = start
            self.end_seconds = end
            self.text = text

    cues = [MockCue(0.0, 4.5, "long narration segment")]

    with pytest.raises(MotionBeatTimingError) as exc_info:
        create_beat_map_from_subtitle_cues(
            scene_id="scene_cues",
            cues=cues,
            total_duration=1.0,
        )
    assert "exceeds total_duration" in str(exc_info.value)


def test_subtitle_cue_adapter_coordinate_space_normalization():
    """Global lesson cues normalize cleanly to scene-local timing with scene_start_seconds."""
    class MockCue:
        def __init__(self, start: float, end: float, text: str):
            self.start_seconds = start
            self.end_seconds = end
            self.text = text

    # Global coordinates: scene runs from 10.0s to 15.0s
    global_cues = [
        MockCue(10.0, 12.0, "Welcome to the scene,"),
        MockCue(12.0, 15.0, "demonstrating concepts."),
    ]

    bm = create_beat_map_from_subtitle_cues(
        scene_id="s_local",
        cues=global_cues,
        total_duration=5.0,
        scene_start_seconds=10.0,
        beat_definitions=["Welcome", "concepts"],
    )

    # Must be normalized to scene-local [0, 5.0]
    assert bm.phrases[0].start == 0.0
    assert bm.phrases[0].end == 2.0
    assert bm.phrases[1].start == 2.0
    assert bm.phrases[1].end == 5.0
    assert bm.beats[0].start == 0.0
    assert bm.beats[1].start == 2.0


def test_subtitle_cue_adapter_rejects_negative_local_start():
    """Cue starting before scene_start_seconds produces negative local start and must be rejected."""
    class MockCue:
        def __init__(self, start: float, end: float, text: str):
            self.start_seconds = start
            self.end_seconds = end
            self.text = text

    bad_cues = [MockCue(8.0, 12.0, "starts too early")]

    with pytest.raises(MotionBeatTimingError):
        create_beat_map_from_subtitle_cues(
            scene_id="s_bad",
            cues=bad_cues,
            total_duration=5.0,
            scene_start_seconds=10.0,
        )


# =========================================================================
# 5. Narrative Timing Order Invariant (BLOCKER 5)
# =========================================================================

def test_resolve_motion_plan_rejects_reversed_narrative_timing():
    """If MotionPlan event sequence conflicts with narration timing order, raise MotionBeatTimingError.

    Must NOT silently reorder semantic events.
    """
    words = [
        WordTiming(word="early", start=1.0, end=1.5),
        WordTiming(word="late", start=2.0, end=2.5),
    ]
    bm = create_narration_beat_map_from_word_timings(
        scene_id="scene_order",
        words=words,
        beat_definitions=["early", "late"],
    )

    # Narrative order: e1 (targets late at 2.0s) then e2 (targets early at 1.0s) -> REVERSED!
    plan_reversed = MotionPlan(
        scene_id="scene_order",
        events=[
            MotionEvent(
                id="e1_late",
                target="n1",
                verb=MotionVerb.ENTER,
                style=MotionStyle.FADE,
                trigger=MotionTrigger(beat="late"),
            ),
            MotionEvent(
                id="e2_early",
                target="n2",
                verb=MotionVerb.ENTER,
                style=MotionStyle.FADE,
                trigger=MotionTrigger(beat="early"),
            ),
        ],
    )

    with pytest.raises(MotionBeatTimingError) as exc_info:
        resolve_motion_plan_timing(plan_reversed, bm)
    assert "narrative event order conflicts with resolved beat timing" in str(exc_info.value)


def test_resolve_motion_plan_accepts_simultaneous_or_increasing_timing():
    """Narrative order with non-decreasing event timings is accepted."""
    words = [
        WordTiming(word="beat1", start=1.0, end=1.5),
        WordTiming(word="beat2", start=2.0, end=2.5),
    ]
    bm = create_narration_beat_map_from_word_timings(
        scene_id="scene_ok",
        words=words,
        beat_definitions=["beat1", "beat2"],
    )

    plan_ok = MotionPlan(
        scene_id="scene_ok",
        events=[
            MotionEvent(
                id="e1",
                target="n1",
                verb=MotionVerb.ENTER,
                style=MotionStyle.FADE,
                trigger=MotionTrigger(beat="beat1"),
            ),
            MotionEvent(
                id="e2_same",
                target="n2",
                verb=MotionVerb.ENTER,
                style=MotionStyle.SLIDE,
                trigger=MotionTrigger(beat="beat1"),  # simultaneous at 1.0s is valid
            ),
            MotionEvent(
                id="e3",
                target="n3",
                verb=MotionVerb.EXIT,
                style=MotionStyle.FADE,
                trigger=MotionTrigger(beat="beat2"),  # later at 2.0s
            ),
        ],
    )

    resolved = resolve_motion_plan_timing(plan_ok, bm)
    assert len(resolved.event_timings) == 3
    assert resolved.event_timings[0].time == 1.0
    assert resolved.event_timings[1].time == 1.0
    assert resolved.event_timings[2].time == 2.0


# =========================================================================
# 6. Trigger Identity Contract & Ambiguity Resolution
# =========================================================================

def test_get_beat_raises_on_ambiguous_name_lookup():
    """If multiple beats share the same display name, name lookup must raise MotionBeatAmbiguityError."""
    b1 = SemanticBeat(id="id_1", name="pulse", start=1.0)
    b2 = SemanticBeat(id="id_2", name="pulse", start=2.0)

    bm = NarrationBeatMap(
        scene_id="scene_ambig",
        total_duration=5.0,
        timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
        beats=(b1, b2),
    )

    # Exact ID lookup remains unambiguous
    assert bm.get_beat("id_1") is b1
    assert bm.get_beat("id_2") is b2

    # Ambiguous name lookup must NOT silently return first match
    with pytest.raises(MotionBeatAmbiguityError) as exc_info:
        bm.get_beat("pulse")
    assert "Ambiguous beat reference" in str(exc_info.value)


# =========================================================================
# 7. Provider Word Timestamps & Event Timing Following Narration
# =========================================================================

def test_event_timing_strictly_follows_narration_word_movement():
    """Event timing must follow actual word timestamps when they move."""
    words_take1 = [
        WordTiming(word="The", start=0.0, end=0.2),
        WordTiming(word="model", start=0.2, end=0.5),
        WordTiming(word="makes", start=0.5, end=0.7),
        WordTiming(word="a", start=0.7, end=0.8),
        WordTiming(word="prediction,", start=0.8, end=1.4),
        WordTiming(word="and", start=1.4, end=1.6),
        WordTiming(word="propagates", start=1.6, end=2.2),
        WordTiming(word="error.", start=2.2, end=2.8),
    ]

    beat_map1 = create_narration_beat_map_from_word_timings(
        scene_id="scene_01",
        words=words_take1,
        beat_definitions=["prediction", "propagates"],
    )

    plan = MotionPlan(
        scene_id="scene_01",
        events=[
            MotionEvent(
                id="ev_enter_pred",
                target="node_pred",
                verb=MotionVerb.ENTER,
                style=MotionStyle.FADE,
                trigger=MotionTrigger(beat="prediction"),
            ),
            MotionEvent(
                id="ev_pulse_prop",
                target="node_prop",
                verb=MotionVerb.EMPHASIZE,
                style=MotionStyle.PULSE,
                trigger=MotionTrigger(beat="propagates"),
            ),
        ],
    )

    resolved_take1 = resolve_motion_plan_timing(plan, beat_map1)
    assert resolved_take1.get_event_time("ev_enter_pred") == 0.8
    assert resolved_take1.get_event_time("ev_pulse_prop") == 1.6

    # Audio Take 2: Narrator delays
    words_take2 = [
        WordTiming(word="The", start=0.0, end=0.3),
        WordTiming(word="model", start=0.3, end=0.7),
        WordTiming(word="makes", start=0.7, end=1.0),
        WordTiming(word="a", start=1.0, end=1.2),
        WordTiming(word="prediction,", start=2.5, end=3.2),
        WordTiming(word="and", start=3.2, end=3.5),
        WordTiming(word="propagates", start=4.0, end=4.8),
        WordTiming(word="error.", start=4.8, end=5.5),
    ]

    beat_map2 = create_narration_beat_map_from_word_timings(
        scene_id="scene_01",
        words=words_take2,
        beat_definitions=["prediction", "propagates"],
    )

    resolved_take2 = resolve_motion_plan_timing(plan, beat_map2)
    assert resolved_take2.get_event_time("ev_enter_pred") == 2.5
    assert resolved_take2.get_event_time("ev_pulse_prop") == 4.0


# =========================================================================
# 8. Determinism & Canonical JSON Serialization
# =========================================================================

def test_narration_beat_map_determinism_and_canonical_json():
    """Identical input produces identical byte-for-byte canonical JSON."""
    words = [
        WordTiming(word="Input", start=0.0, end=0.5),
        WordTiming(word="vector", start=0.5, end=1.0),
        WordTiming(word="transforms.", start=1.0, end=1.8),
    ]

    bm1 = create_narration_beat_map(
        scene_id="scene_det",
        narration_text="Input vector transforms.",
        words=words,
        beat_definitions=["Input", "transforms"],
    )
    bm2 = create_narration_beat_map(
        scene_id="scene_det",
        narration_text="Input vector transforms.",
        words=words,
        beat_definitions=["Input", "transforms"],
    )

    json1 = bm1.to_canonical_json()
    json2 = bm2.to_canonical_json()

    assert json1 == json2
    assert "PROVIDER_WORD_TIMINGS" in json1

    restored = NarrationBeatMap.from_canonical_json(json1)
    assert restored.scene_id == bm1.scene_id
    assert len(restored.beats) == len(bm1.beats)
    assert restored.beats[0].start == bm1.beats[0].start


# =========================================================================
# 9. Fallback Without Word Timestamps (PLAN A9)
# =========================================================================

def test_fallback_without_word_timestamps_creates_monotonic_timing():
    """Fallback interpolates timing across [0, total_duration] using structured script."""
    narration = (
        "The model makes a prediction. "
        "It compares the output with ground truth. "
        "Finally, it backpropagates the loss gradient."
    )
    total_audio_duration = 9.0

    beat_map = create_narration_beat_map_fallback(
        scene_id="scene_fallback",
        narration_text=narration,
        total_duration=total_audio_duration,
        beat_definitions=["prediction", "truth", "loss gradient"],
    )

    assert beat_map.timing_mode == TimingMode.DETERMINISTIC_FALLBACK
    assert beat_map.total_duration == 9.0
    assert len(beat_map.phrases) == 3

    assert beat_map.phrases[0].start == 0.0
    assert beat_map.phrases[0].end == beat_map.phrases[1].start
    assert beat_map.phrases[1].end == beat_map.phrases[2].start
    assert beat_map.phrases[2].end == 9.0

    for b in beat_map.beats:
        assert 0.0 <= b.start <= 9.0

    plan = MotionPlan(
        scene_id="scene_fallback",
        events=[
            MotionEvent(
                id="e1",
                target="n1",
                verb=MotionVerb.ENTER,
                style=MotionStyle.FADE,
                trigger=MotionTrigger(beat="prediction"),
            ),
            MotionEvent(
                id="e2",
                target="n2",
                verb=MotionVerb.TRANSFORM,
                style=MotionStyle.MOVE,
                trigger=MotionTrigger(beat="truth"),
            ),
        ],
    )
    resolved = resolve_motion_plan_timing(plan, beat_map)
    assert len(resolved.event_timings) == 2
    assert resolved.event_timings[0].time < resolved.event_timings[1].time


def test_fallback_determinism():
    """Repeated fallback runs produce identical canonical serialization."""
    text = "Alpha starts here. Beta executes next. Gamma completes the run."
    duration = 6.4

    bm1 = create_narration_beat_map_fallback("s_det", text, duration)
    bm2 = create_narration_beat_map_fallback("s_det", text, duration)

    assert bm1.to_canonical_json() == bm2.to_canonical_json()


def test_fallback_rejects_empty_narration_or_invalid_duration():
    """Fallback must reject empty text or non-positive durations."""
    with pytest.raises(MotionBeatTimingError):
        create_narration_beat_map_fallback("s1", "", 5.0)

    with pytest.raises(MotionBeatTimingError):
        create_narration_beat_map_fallback("s1", "valid text", 0.0)

    with pytest.raises(MotionBeatTimingError):
        create_narration_beat_map_fallback("s1", "valid text", -2.5)

    with pytest.raises(MotionBeatTimingError):
        create_narration_beat_map_fallback("s1", "valid text", float("nan"))


# =========================================================================
# 10. Immutability of Beat Contracts
# =========================================================================

def test_beat_contracts_immutability():
    """All models in beats module must be frozen/immutable."""
    w = WordTiming(word="token", start=0.0, end=1.0)
    with pytest.raises(ValidationError):
        w.start = 0.5  # type: ignore[misc]

    b = SemanticBeat(id="b1", name="beat one", start=1.0)
    with pytest.raises(ValidationError):
        b.start = 2.0  # type: ignore[misc]

    bm = create_narration_beat_map_fallback("s1", "Short text.", 2.0)
    with pytest.raises(ValidationError):
        bm.total_duration = 3.0  # type: ignore[misc]

    resolved = ResolvedEventTiming(
        event_id="e1",
        beat_id="b1",
        time=1.0,
        target="n1",
        verb=MotionVerb.ENTER,
        style=MotionStyle.FADE,
    )
    with pytest.raises(ValidationError):
        resolved.time = 2.0  # type: ignore[misc]


# =========================================================================
# 11. Public Artifact Invariants (CP 2.8 Hardening)
# =========================================================================

def test_resolved_motion_plan_timing_direct_constructor_rejects_reversed_timing():
    """Direct construction with reversed event times must raise MotionBeatTimingError."""
    ev1 = ResolvedEventTiming(
        event_id="e1",
        beat_id="b1",
        time=2.0,
        target="n1",
        verb=MotionVerb.ENTER,
        style=MotionStyle.FADE,
    )
    ev2 = ResolvedEventTiming(
        event_id="e2",
        beat_id="b2",
        time=1.0,
        target="n2",
        verb=MotionVerb.ENTER,
        style=MotionStyle.FADE,
    )

    with pytest.raises(MotionBeatTimingError) as exc_info:
        ResolvedMotionPlanTiming(
            scene_id="s_direct",
            timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
            event_timings=(ev1, ev2),
        )
    assert "non-decreasing in narrative order" in str(exc_info.value)


def test_resolved_motion_plan_timing_accepts_non_decreasing_timing():
    """Direct construction with equal and increasing times [1.0, 1.0, 2.0] is valid."""
    ev1 = ResolvedEventTiming(
        event_id="e1", beat_id="b1", time=1.0, target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE
    )
    ev2 = ResolvedEventTiming(
        event_id="e2", beat_id="b1", time=1.0, target="n2", verb=MotionVerb.ENTER, style=MotionStyle.SLIDE
    )
    ev3 = ResolvedEventTiming(
        event_id="e3", beat_id="b2", time=2.0, target="n3", verb=MotionVerb.EXIT, style=MotionStyle.FADE
    )

    resolved = ResolvedMotionPlanTiming(
        scene_id="s_ok",
        timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
        event_timings=(ev1, ev2, ev3),
    )
    assert len(resolved.event_timings) == 3
    assert resolved.event_timings[0].time == 1.0
    assert resolved.event_timings[1].time == 1.0
    assert resolved.event_timings[2].time == 2.0


def test_resolved_motion_plan_timing_canonical_deserialization_rejects_reversed():
    """Canonical JSON deserialization of a reversed timing artifact must fail."""
    reversed_json = """{
        "scene_id": "s_rev",
        "timing_mode": "DETERMINISTIC_FALLBACK",
        "event_timings": [
            {"event_id": "e1", "beat_id": "b1", "time": 3.0, "target": "n1", "verb": "ENTER", "style": "FADE"},
            {"event_id": "e2", "beat_id": "b2", "time": 1.5, "target": "n2", "verb": "ENTER", "style": "FADE"}
        ],
        "untriggered_events": []
    }"""
    with pytest.raises((MotionBeatTimingError, ValidationError)):
        ResolvedMotionPlanTiming.from_canonical_json(reversed_json)


def test_resolved_motion_plan_timing_rejects_duplicate_event_ids():
    """Duplicate event IDs in ResolvedMotionPlanTiming must be rejected."""
    ev1 = ResolvedEventTiming(
        event_id="dup_id", beat_id="b1", time=1.0, target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE
    )
    ev2 = ResolvedEventTiming(
        event_id="dup_id", beat_id="b2", time=2.0, target="n2", verb=MotionVerb.ENTER, style=MotionStyle.FADE
    )
    with pytest.raises(MotionBeatTimingError) as exc_info:
        ResolvedMotionPlanTiming(
            scene_id="s_dup",
            timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
            event_timings=(ev1, ev2),
        )
    assert "Duplicate event ID" in str(exc_info.value)


def test_resolved_event_timing_rejects_nan_and_inf():
    """ResolvedEventTiming must strictly reject NaN, +inf, -inf, and negative values."""
    with pytest.raises(MotionBeatTimingError):
        ResolvedEventTiming(
            event_id="e1", beat_id="b1", time=float("nan"), target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE
        )

    with pytest.raises(MotionBeatTimingError):
        ResolvedEventTiming(
            event_id="e1", beat_id="b1", time=float("inf"), target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE
        )

    with pytest.raises(MotionBeatTimingError):
        ResolvedEventTiming(
            event_id="e1", beat_id="b1", time=float("-inf"), target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE
        )

    with pytest.raises(MotionBeatTimingError):
        ResolvedEventTiming(
            event_id="e1", beat_id="b1", time=-0.5, target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE
        )


def test_provenance_provider_word_timings_requires_words():
    """NarrationBeatMap with PROVIDER_WORD_TIMINGS must have non-empty words."""
    b = SemanticBeat(id="b1", name="beat", start=0.5)

    with pytest.raises(MotionBeatTimingError) as exc_info:
        NarrationBeatMap(
            scene_id="s_prov",
            total_duration=2.0,
            timing_mode=TimingMode.PROVIDER_WORD_TIMINGS,
            beats=(b,),
            words=None,
        )
    assert "requires non-empty words" in str(exc_info.value)

    with pytest.raises(MotionBeatTimingError) as exc_info2:
        NarrationBeatMap(
            scene_id="s_prov",
            total_duration=2.0,
            timing_mode=TimingMode.PROVIDER_WORD_TIMINGS,
            beats=(b,),
            words=(),
        )
    assert "requires non-empty words" in str(exc_info2.value)


def test_provenance_deterministic_fallback_forbids_words():
    """NarrationBeatMap with DETERMINISTIC_FALLBACK must have words=None."""
    b = SemanticBeat(id="b1", name="beat", start=0.5)
    w = WordTiming(word="word", start=0.0, end=1.0)

    with pytest.raises(MotionBeatTimingError) as exc_info:
        NarrationBeatMap(
            scene_id="s_fb",
            total_duration=2.0,
            timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
            beats=(b,),
            words=(w,),
        )
    assert "cannot contain words" in str(exc_info.value)


def test_provenance_invariant_survives_canonical_roundtrip():
    """Provenance invariants remain valid through canonical serialization."""
    words = [WordTiming(word="hello", start=0.0, end=1.0)]
    bm_word = create_narration_beat_map_from_word_timings("s1", words)
    bm_word_rt = NarrationBeatMap.from_canonical_json(bm_word.to_canonical_json())
    assert bm_word_rt.timing_mode == TimingMode.PROVIDER_WORD_TIMINGS
    assert bm_word_rt.words is not None and len(bm_word_rt.words) == 1

    bm_fb = create_narration_beat_map_fallback("s2", "fallback text", 3.0)
    bm_fb_rt = NarrationBeatMap.from_canonical_json(bm_fb.to_canonical_json())
    assert bm_fb_rt.timing_mode == TimingMode.DETERMINISTIC_FALLBACK
    assert bm_fb_rt.words is None


def test_semantic_beat_phrase_id_missing_phrase_rejected():
    """Beat referencing a non-existent phrase_id must be rejected."""
    p0 = PhraseTiming(id="p0", text="phrase zero", start=0.0, end=2.0)
    b_ghost = SemanticBeat(id="b1", name="ghost", start=0.5, phrase_id="ghost_phrase")

    with pytest.raises(MotionBeatTimingError) as exc_info:
        NarrationBeatMap(
            scene_id="s_ghost",
            total_duration=3.0,
            timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
            phrases=(p0,),
            beats=(b_ghost,),
        )
    assert "references unknown phrase_id" in str(exc_info.value)


def test_semantic_beat_temporally_outside_phrase_rejected():
    """Beat referencing phrase p0 [0.0, 1.0] but placed at 2.0s must be rejected."""
    p0 = PhraseTiming(id="p0", text="phrase zero", start=0.0, end=1.0)
    b_outside = SemanticBeat(id="b1", name="out", start=2.0, end=2.5, phrase_id="p0")

    with pytest.raises(MotionBeatTimingError) as exc_info:
        NarrationBeatMap(
            scene_id="s_out",
            total_duration=3.0,
            timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
            phrases=(p0,),
            beats=(b_outside,),
        )
    assert "outside associated phrase" in str(exc_info.value)


def test_provider_word_level_beat_with_none_phrase_id_valid():
    """Provider word-level beats with phrase_id=None are completely valid."""
    w = WordTiming(word="word", start=0.5, end=1.0)
    p = PhraseTiming(id="p0", text="word", start=0.5, end=1.0, words=(w,))
    b = SemanticBeat(id="b_word", name="word", start=0.5, end=1.0, phrase_id=None)

    bm = NarrationBeatMap(
        scene_id="s_word",
        total_duration=2.0,
        timing_mode=TimingMode.PROVIDER_WORD_TIMINGS,
        phrases=(p,),
        beats=(b,),
        words=(w,),
    )
    assert bm.beats[0].phrase_id is None
    assert bm.beats[0].start == 0.5

