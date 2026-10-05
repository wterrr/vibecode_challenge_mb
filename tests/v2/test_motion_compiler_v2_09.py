"""Tests for LearnFlow V2 — CP 2.9: Motion Compiler (test_motion_compiler_v2_09.py)."""

import json
import pytest
from pydantic import ValidationError

from learnflow_v2.core.errors import (
    MotionCompilationError,
    MotionScheduleTimingError,
    MotionUnsupportedTierError,
)
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.motion.compiler import (
    CompiledMotionArtifact,
    CompiledMotionEvent,
    PropertyKeyframe,
    PropertyTrack,
    PropertyTrackKind,
    compile_event_to_tracks,
    compile_motion_schedule,
)
from learnflow_v2.motion.enums import (
    TIER_1_MOTION_GRAMMAR,
    MotionStyle,
    MotionTargetKind,
    MotionVerb,
)
from learnflow_v2.motion.scheduler import (
    MotionSchedule,
    ScheduledMotionEvent,
    schedule_motion_plan,
)
from learnflow_v2.motion.schema import MotionEvent, MotionPlan


# =========================================================================
# 1. Tier-1 Grammar Exhaustive Compilation Coverage
# =========================================================================

def test_every_tier_1_verb_style_combination_compiles():
    """Every valid Tier-1 verb and style has an explicit, valid compiler mapping."""
    start_t = 1.0
    for verb, styles in TIER_1_MOTION_GRAMMAR.items():
        for style in styles:
            target_kind = (
                MotionTargetKind.RELATION
                if verb == MotionVerb.RELATION
                else MotionTargetKind.NODE
            )
            ev = ScheduledMotionEvent(
                event_id=f"ev_{verb.value}_{style.value}",
                target="rel1" if target_kind == MotionTargetKind.RELATION else "node1",
                target_kind=target_kind,
                verb=verb,
                style=style,
                start_time=start_t,
                end_time=start_t + 0.50,
                duration=0.50,
            )
            tracks = compile_event_to_tracks(ev)
            assert len(tracks) >= 1, f"No tracks generated for {verb.value} + {style.value}"
            for tr in tracks:
                assert tr.start_time == start_t
                assert tr.end_time == start_t + 0.50
                assert len(tr.keyframes) >= 2
                for kf in tr.keyframes:
                    assert 0.0 <= kf.offset <= 1.0
                    assert 0.0 <= kf.value <= 1.0
                    assert start_t - 1e-4 <= kf.time <= start_t + 0.50 + 1e-4


def test_enter_fade_compilation():
    """ENTER + FADE compiles to OPACITY track 0.0 -> 1.0."""
    ev = ScheduledMotionEvent(
        event_id="e1",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.ENTER,
        style=MotionStyle.FADE,
        start_time=0.0,
        end_time=0.40,
        duration=0.40,
    )
    tracks = compile_event_to_tracks(ev)
    assert len(tracks) == 1
    tr = tracks[0]
    assert tr.property_kind == PropertyTrackKind.OPACITY
    assert tr.keyframes[0].value == 0.0
    assert tr.keyframes[1].value == 1.0
    assert tr.keyframes[0].time == 0.0
    assert tr.keyframes[1].time == 0.40


def test_enter_slide_compilation():
    """ENTER + SLIDE compiles to OPACITY and TRANSLATION_PROGRESS tracks."""
    ev = ScheduledMotionEvent(
        event_id="e1",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.ENTER,
        style=MotionStyle.SLIDE,
        start_time=0.0,
        end_time=0.50,
        duration=0.50,
    )
    tracks = compile_event_to_tracks(ev)
    assert len(tracks) == 2
    kinds = {t.property_kind for t in tracks}
    assert kinds == {PropertyTrackKind.OPACITY, PropertyTrackKind.TRANSLATION_PROGRESS}


def test_emphasize_pulse_compilation():
    """EMPHASIZE + PULSE compiles to 2-cycle pulse keyframes on EMPHASIS_INTENSITY."""
    ev = ScheduledMotionEvent(
        event_id="e1",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.EMPHASIZE,
        style=MotionStyle.PULSE,
        start_time=1.0,
        end_time=2.0,
        duration=1.0,
    )
    tracks = compile_event_to_tracks(ev)
    assert len(tracks) == 1
    tr = tracks[0]
    assert tr.property_kind == PropertyTrackKind.EMPHASIS_INTENSITY
    assert len(tr.keyframes) == 5  # 0.0 -> 1.0 -> 0.2 -> 1.0 -> 0.0
    assert tr.keyframes[0].value == 0.0
    assert tr.keyframes[1].value == 1.0
    assert tr.keyframes[2].value == 0.2
    assert tr.keyframes[3].value == 1.0
    assert tr.keyframes[4].value == 0.0


def test_relation_draw_edge_compilation():
    """RELATION + DRAW_EDGE compiles to EDGE_DRAW_PROGRESS track."""
    ev = ScheduledMotionEvent(
        event_id="e1",
        target="r1",
        target_kind=MotionTargetKind.RELATION,
        verb=MotionVerb.RELATION,
        style=MotionStyle.DRAW_EDGE,
        start_time=2.0,
        end_time=2.50,
        duration=0.50,
    )
    tracks = compile_event_to_tracks(ev)
    assert len(tracks) == 1
    tr = tracks[0]
    assert tr.property_kind == PropertyTrackKind.EDGE_DRAW_PROGRESS
    assert tr.keyframes[0].value == 0.0
    assert tr.keyframes[1].value == 1.0


def test_transform_move_compilation():
    """TRANSFORM + MOVE compiles to normalized TRANSLATION_PROGRESS track."""
    ev = ScheduledMotionEvent(
        event_id="e1",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.TRANSFORM,
        style=MotionStyle.MOVE,
        start_time=1.0,
        end_time=1.50,
        duration=0.50,
    )
    tracks = compile_event_to_tracks(ev)
    assert len(tracks) == 1
    tr = tracks[0]
    assert tr.property_kind == PropertyTrackKind.TRANSLATION_PROGRESS
    assert tr.keyframes[0].value == 0.0
    assert tr.keyframes[1].value == 1.0


def test_exit_fade_compilation():
    """EXIT + FADE compiles to OPACITY track 1.0 -> 0.0."""
    ev = ScheduledMotionEvent(
        event_id="e1",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.EXIT,
        style=MotionStyle.FADE,
        start_time=3.0,
        end_time=3.40,
        duration=0.40,
    )
    tracks = compile_event_to_tracks(ev)
    assert len(tracks) == 1
    tr = tracks[0]
    assert tr.property_kind == PropertyTrackKind.OPACITY
    assert tr.keyframes[0].value == 1.0
    assert tr.keyframes[1].value == 0.0


# =========================================================================
# 2. Renderer Neutrality & Absence of Pixels / Renderer Commands
# =========================================================================

def test_compiler_emits_strictly_renderer_neutral_tracks():
    """Output contains no pixel coordinates, Pillow calls, Manim code, or FFmpeg commands."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.SLIDE),
            MotionEvent(id="e2", target="n1", verb=MotionVerb.EMPHASIZE, style=MotionStyle.PULSE),
            MotionEvent(id="e3", target="n1", verb=MotionVerb.TRANSFORM, style=MotionStyle.MOVE),
            MotionEvent(id="e4", target="n1", verb=MotionVerb.EXIT, style=MotionStyle.FADE),
        ),
    )
    schedule = schedule_motion_plan(plan, scene_duration=10.0)
    compiled = compile_motion_schedule(schedule)

    json_str = compiled.to_canonical_json()
    forbidden_tokens = ["px", "pixel", "manim", "pillow", "ffmpeg", "javascript", "canvas.draw"]
    for token in forbidden_tokens:
        assert token not in json_str.lower(), f"Forbidden renderer token '{token}' found in compiled output"

    # All keyframe values must be normalized floats in [0.0, 1.0]
    for tr in compiled.tracks:
        for kf in tr.keyframes:
            assert 0.0 <= kf.value <= 1.0


# =========================================================================
# 3. Direct Construction & Boundary Invariants
# =========================================================================

def test_property_track_direct_construction_rejects_out_of_bounds_keyframe():
    """PropertyTrack rejects keyframes that lie outside [start_time, end_time]."""
    with pytest.raises(MotionScheduleTimingError):
        PropertyTrack(
            track_id="tr1",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            property_kind=PropertyTrackKind.OPACITY,
            start_time=1.0,
            end_time=2.0,
            keyframes=(
                PropertyKeyframe(offset=0.0, time=0.5, value=0.0),  # earlier than start_time
                PropertyKeyframe(offset=1.0, time=2.0, value=1.0),
            ),
        )


def test_compiled_artifact_canonical_serialization_roundtrip():
    """CompiledMotionArtifact round-trips identically through canonical JSON."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            MotionEvent(id="e2", target="n1", verb=MotionVerb.EXIT, style=MotionStyle.FADE),
        ),
    )
    schedule = schedule_motion_plan(plan, scene_duration=5.0)
    artifact = compile_motion_schedule(schedule)

    serialized = artifact.to_canonical_json()
    roundtrip = CompiledMotionArtifact.from_canonical_json(serialized)
    assert roundtrip.to_canonical_json() == serialized
    assert len(roundtrip.events) == 2
    assert len(roundtrip.tracks) == 2


# =========================================================================
# 4. Focused Hardening Regressions (Blockers 3, 5, 8)
# =========================================================================

def test_property_track_metadata_immutable_and_cannot_be_mutated():
    """PropertyTrack.metadata is deeply immutable and rejects item assignment."""
    tr = PropertyTrack(
        track_id="tr1",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        property_kind=PropertyTrackKind.OPACITY,
        start_time=1.0,
        end_time=2.0,
        keyframes=(
            PropertyKeyframe(offset=0.0, time=1.0, value=0.0),
            PropertyKeyframe(offset=1.0, time=2.0, value=1.0),
        ),
        metadata={"direction": "up", "nested": {"cycles": 2}},
    )

    before_json = canonical_json(tr)

    # Attempt mutation
    with pytest.raises(TypeError):
        tr.metadata["direction"] = "down"  # type: ignore[index]

    with pytest.raises(TypeError):
        tr.metadata["nested"]["cycles"] = 99  # type: ignore[index]

    assert canonical_json(tr) == before_json


def test_compiled_motion_event_timing_validation():
    """CompiledMotionEvent rejects NaN, inf, negative start, and end <= start."""
    # NaN
    with pytest.raises(MotionScheduleTimingError):
        CompiledMotionEvent(
            event_id="e1",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            verb=MotionVerb.ENTER,
            style=MotionStyle.FADE,
            start_time=float("nan"),
            end_time=1.0,
        )

    # Inf
    with pytest.raises(MotionScheduleTimingError):
        CompiledMotionEvent(
            event_id="e1",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            verb=MotionVerb.ENTER,
            style=MotionStyle.FADE,
            start_time=float("inf"),
            end_time=float("inf"),
        )

    # Negative start
    with pytest.raises(MotionScheduleTimingError):
        CompiledMotionEvent(
            event_id="e1",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            verb=MotionVerb.ENTER,
            style=MotionStyle.FADE,
            start_time=-1.0,
            end_time=1.0,
        )

    # end <= start
    with pytest.raises(MotionScheduleTimingError):
        CompiledMotionEvent(
            event_id="e1",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            verb=MotionVerb.ENTER,
            style=MotionStyle.FADE,
            start_time=2.0,
            end_time=1.0,
        )

    # Rejection via canonical deserialization
    bad_json = (
        '{"event_id": "e1", "target": "n1", "target_kind": "NODE", '
        '"verb": "ENTER", "style": "FADE", "start_time": 2.0, "end_time": 1.0, "tracks": []}'
    )
    with pytest.raises((ValidationError, MotionScheduleTimingError)):
        CompiledMotionEvent.model_validate_json(bad_json)


def test_compiled_motion_artifact_cross_reference_integrity():
    """CompiledMotionArtifact strictly requires artifact.tracks to match flattened event tracks."""
    tr1 = PropertyTrack(
        track_id="tr1",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        property_kind=PropertyTrackKind.OPACITY,
        start_time=0.0,
        end_time=1.0,
        keyframes=(
            PropertyKeyframe(offset=0.0, time=0.0, value=0.0),
            PropertyKeyframe(offset=1.0, time=1.0, value=1.0),
        ),
    )
    tr2 = PropertyTrack(
        track_id="tr2",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        property_kind=PropertyTrackKind.OPACITY,
        start_time=1.0,
        end_time=2.0,
        keyframes=(
            PropertyKeyframe(offset=0.0, time=1.0, value=1.0),
            PropertyKeyframe(offset=1.0, time=2.0, value=0.0),
        ),
    )
    ev1 = CompiledMotionEvent(
        event_id="e1",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.ENTER,
        style=MotionStyle.FADE,
        start_time=0.0,
        end_time=1.0,
        tracks=(tr1,),
    )

    # Missing flattened track: ev1 has tr1, but artifact.tracks is empty
    with pytest.raises(MotionCompilationError):
        CompiledMotionArtifact(
            scene_id="s1",
            scene_duration=5.0,
            events=(ev1,),
            tracks=(),
        )

    # Extra flattened track: ev1 has tr1, but artifact.tracks has (tr1, tr2)
    with pytest.raises(MotionCompilationError):
        CompiledMotionArtifact(
            scene_id="s1",
            scene_duration=5.0,
            events=(ev1,),
            tracks=(tr1, tr2),
        )

    # Valid agreement
    valid_art = CompiledMotionArtifact(
        scene_id="s1",
        scene_duration=5.0,
        events=(ev1,),
        tracks=(tr1,),
    )
    assert len(valid_art.tracks) == 1
    assert valid_art.tracks[0].track_id == "tr1"


# =========================================================================
# 5. Metadata Immutability & JSON-Safe Hardening Regressions (Blocker 1)
# =========================================================================

def test_property_track_metadata_nested_dict_list_deep_immutability():
    """PropertyTrack metadata deeply freezes nested dicts to MappingProxyType and lists to tuples."""
    track = PropertyTrack(
        track_id="tr_nested",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        property_kind=PropertyTrackKind.OPACITY,
        start_time=0.0,
        end_time=1.0,
        keyframes=(
            PropertyKeyframe(offset=0.0, time=0.0, value=0.0),
            PropertyKeyframe(offset=1.0, time=1.0, value=1.0),
        ),
        metadata={
            "tags": ["alpha", "beta"],
            "nested": {"config": {"cycles": 3, "flags": [True, False]}},
        },
    )

    # Top-level mapping cannot be mutated
    with pytest.raises(TypeError):
        track.metadata["new_key"] = 123  # type: ignore[index]

    # Nested mapping cannot be mutated
    with pytest.raises(TypeError):
        track.metadata["nested"]["config"]["cycles"] = 99  # type: ignore[index]

    # Nested list is frozen to tuple: cannot mutate or append
    with pytest.raises(TypeError):
        track.metadata["tags"][0] = "gamma"  # type: ignore[index]

    with pytest.raises(AttributeError):
        track.metadata["tags"].append("gamma")  # type: ignore[union-attr]

    with pytest.raises(TypeError):
        track.metadata["nested"]["config"]["flags"][0] = False  # type: ignore[index]


def test_property_track_metadata_rejects_set_and_tuple():
    """PropertyTrack rejects sets, frozensets, and tuples in input metadata."""
    from learnflow_v2.core.errors import MotionInvalidInputError

    kf = (
        PropertyKeyframe(offset=0.0, time=0.0, value=0.0),
        PropertyKeyframe(offset=1.0, time=1.0, value=1.0),
    )

    # Set
    with pytest.raises(MotionInvalidInputError) as exc_info:
        PropertyTrack(
            track_id="tr_set",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            property_kind=PropertyTrackKind.OPACITY,
            start_time=0.0,
            end_time=1.0,
            keyframes=kf,
            metadata={"tags": {"alpha", "beta"}},
        )
    assert "set" in str(exc_info.value)

    # Tuple
    with pytest.raises(MotionInvalidInputError) as exc_info:
        PropertyTrack(
            track_id="tr_tuple",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            property_kind=PropertyTrackKind.OPACITY,
            start_time=0.0,
            end_time=1.0,
            keyframes=kf,
            metadata={"coords": (10.0, 20.0)},
        )
    assert "tuple" in str(exc_info.value)

    # Nested tuple inside list
    with pytest.raises(MotionInvalidInputError) as exc_info:
        PropertyTrack(
            track_id="tr_nested_tuple",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            property_kind=PropertyTrackKind.OPACITY,
            start_time=0.0,
            end_time=1.0,
            keyframes=kf,
            metadata={"items": [(1, 2)]},
        )
    assert "tuple" in str(exc_info.value)


def test_property_track_metadata_rejects_nan_and_inf():
    """PropertyTrack rejects NaN, +inf, and -inf in metadata."""
    from learnflow_v2.core.errors import MotionInvalidInputError

    kf = (
        PropertyKeyframe(offset=0.0, time=0.0, value=0.0),
        PropertyKeyframe(offset=1.0, time=1.0, value=1.0),
    )

    for bad_num in [float("nan"), float("inf"), float("-inf")]:
        with pytest.raises(MotionInvalidInputError) as exc_info:
            PropertyTrack(
                track_id="tr_bad_float",
                target="n1",
                target_kind=MotionTargetKind.NODE,
                property_kind=PropertyTrackKind.OPACITY,
                start_time=0.0,
                end_time=1.0,
                keyframes=kf,
                metadata={"scale": bad_num},
            )
        assert "finite float" in str(exc_info.value)


def test_property_track_metadata_rejects_non_string_keys():
    """PropertyTrack rejects non-string keys in metadata dictionaries."""
    from learnflow_v2.core.errors import MotionInvalidInputError

    kf = (
        PropertyKeyframe(offset=0.0, time=0.0, value=0.0),
        PropertyKeyframe(offset=1.0, time=1.0, value=1.0),
    )

    with pytest.raises(MotionInvalidInputError) as exc_info:
        PropertyTrack(
            track_id="tr_int_key",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            property_kind=PropertyTrackKind.OPACITY,
            start_time=0.0,
            end_time=1.0,
            keyframes=kf,
            metadata={100: "value"},  # type: ignore[dict-item]
        )
    assert "keys must be strings" in str(exc_info.value)


def test_property_track_metadata_rejects_custom_mutable_objects():
    """PropertyTrack rejects arbitrary Python objects, bytes, and callables."""
    from learnflow_v2.core.errors import MotionInvalidInputError

    kf = (
        PropertyKeyframe(offset=0.0, time=0.0, value=0.0),
        PropertyKeyframe(offset=1.0, time=1.0, value=1.0),
    )

    class CustomObject:
        pass

    for bad_val, desc in [
        (CustomObject(), "CustomObject"),
        (b"raw_bytes", "bytes"),
        (lambda x: x, "callable"),
    ]:
        with pytest.raises(MotionInvalidInputError) as exc_info:
            PropertyTrack(
                track_id=f"tr_{desc}",
                target="n1",
                target_kind=MotionTargetKind.NODE,
                property_kind=PropertyTrackKind.OPACITY,
                start_time=0.0,
                end_time=1.0,
                keyframes=kf,
                metadata={"payload": bad_val},
            )
        assert "non JSON-safe" in str(exc_info.value)


def test_property_track_canonical_json_identical_across_seeds():
    """Canonical serialization of PropertyTrack is byte-for-byte identical across repeated runs."""
    kf = (
        PropertyKeyframe(offset=0.0, time=0.0, value=0.0),
        PropertyKeyframe(offset=1.0, time=1.0, value=1.0),
    )
    meta = {
        "z_key": "last",
        "a_key": "first",
        "m_list": ["two", "one", "three"],
        "nested": {"beta": 2, "alpha": 1},
    }

    t1 = PropertyTrack(
        track_id="tr_stable",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        property_kind=PropertyTrackKind.OPACITY,
        start_time=0.0,
        end_time=1.0,
        keyframes=kf,
        metadata=dict(meta),
    )
    t2 = PropertyTrack(
        track_id="tr_stable",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        property_kind=PropertyTrackKind.OPACITY,
        start_time=0.0,
        end_time=1.0,
        keyframes=kf,
        metadata=dict(reversed(list(meta.items()))),
    )

    assert canonical_json(t1) == canonical_json(t2)
    # Validate round-trip preserves JSON-safe types and unfreezes correctly
    rt = PropertyTrack.model_validate_json(canonical_json(t1))
    assert canonical_json(rt) == canonical_json(t1)


# =========================================================================
# 6. Explicit Negative Compiler Regression Tests
# =========================================================================

def test_compiled_motion_event_enter_fade_empty_tracks_rejected():
    """CompiledMotionEvent with ENTER+FADE and empty tracks tuple is rejected."""
    with pytest.raises(MotionCompilationError) as exc_info:
        CompiledMotionEvent(
            event_id="e1",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            verb=MotionVerb.ENTER,
            style=MotionStyle.FADE,
            start_time=0.0,
            end_time=1.0,
            tracks=(),
        )
    assert "Expected track kinds ['opacity'], got []" in str(exc_info.value)


def test_compiled_motion_event_enter_fade_wrong_track_kind_rejected():
    """CompiledMotionEvent with ENTER+FADE and PROPAGATION_PROGRESS track is rejected."""
    bad_track = PropertyTrack(
        track_id="tr1",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        property_kind=PropertyTrackKind.PROPAGATION_PROGRESS,
        start_time=0.0,
        end_time=1.0,
        keyframes=(
            PropertyKeyframe(offset=0.0, time=0.0, value=0.0),
            PropertyKeyframe(offset=1.0, time=1.0, value=1.0),
        ),
    )
    with pytest.raises(MotionCompilationError) as exc_info:
        CompiledMotionEvent(
            event_id="e1",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            verb=MotionVerb.ENTER,
            style=MotionStyle.FADE,
            start_time=0.0,
            end_time=1.0,
            tracks=(bad_track,),
        )
    assert "Expected track kinds ['opacity'], got ['propagation_progress']" in str(exc_info.value)


def test_property_track_zero_duration_rejected():
    """PropertyTrack with start_time == end_time is rejected."""
    with pytest.raises(MotionScheduleTimingError) as exc_info:
        PropertyTrack(
            track_id="tr1",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            property_kind=PropertyTrackKind.OPACITY,
            start_time=1.0,
            end_time=1.0,
            keyframes=(
                PropertyKeyframe(offset=0.0, time=1.0, value=0.0),
                PropertyKeyframe(offset=1.0, time=1.0, value=1.0),
            ),
        )
    assert "must be strictly greater than start_time" in str(exc_info.value)


def test_property_track_decreasing_normalized_offsets_rejected():
    """PropertyTrack with decreasing normalized offsets is rejected."""
    with pytest.raises(MotionScheduleTimingError) as exc_info:
        PropertyTrack(
            track_id="tr1",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            property_kind=PropertyTrackKind.OPACITY,
            start_time=0.0,
            end_time=1.0,
            keyframes=(
                PropertyKeyframe(offset=0.0, time=0.0, value=0.0),
                PropertyKeyframe(offset=0.8, time=0.4, value=0.5),
                PropertyKeyframe(offset=0.3, time=0.7, value=0.8),  # decreasing offset!
                PropertyKeyframe(offset=1.0, time=1.0, value=1.0),
            ),
        )
    assert "normalized offsets in track 'tr1' must be non-decreasing" in str(exc_info.value)


def test_property_track_first_offset_not_zero_rejected():
    """PropertyTrack where first keyframe offset != 0.0 is rejected."""
    with pytest.raises(MotionScheduleTimingError) as exc_info:
        PropertyTrack(
            track_id="tr1",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            property_kind=PropertyTrackKind.OPACITY,
            start_time=0.0,
            end_time=1.0,
            keyframes=(
                PropertyKeyframe(offset=0.2, time=0.0, value=0.0),
                PropertyKeyframe(offset=1.0, time=1.0, value=1.0),
            ),
        )
    assert "first keyframe offset" in str(exc_info.value)
    assert "must be approximately 0.0" in str(exc_info.value)


def test_property_track_last_offset_not_one_rejected():
    """PropertyTrack where last keyframe offset != 1.0 is rejected."""
    with pytest.raises(MotionScheduleTimingError) as exc_info:
        PropertyTrack(
            track_id="tr1",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            property_kind=PropertyTrackKind.OPACITY,
            start_time=0.0,
            end_time=1.0,
            keyframes=(
                PropertyKeyframe(offset=0.0, time=0.0, value=0.0),
                PropertyKeyframe(offset=0.8, time=1.0, value=1.0),
            ),
        )
    assert "last keyframe offset" in str(exc_info.value)
    assert "must be approximately 1.0" in str(exc_info.value)


def test_property_track_first_keyframe_time_mismatch_rejected():
    """PropertyTrack where first keyframe time != start_time is rejected."""
    with pytest.raises(MotionScheduleTimingError) as exc_info:
        PropertyTrack(
            track_id="tr1",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            property_kind=PropertyTrackKind.OPACITY,
            start_time=1.0,
            end_time=2.0,
            keyframes=(
                PropertyKeyframe(offset=0.0, time=1.2, value=0.0),  # != 1.0
                PropertyKeyframe(offset=1.0, time=2.0, value=1.0),
            ),
        )
    assert "first keyframe time" in str(exc_info.value)
    assert "must correspond to track start_time" in str(exc_info.value)


def test_property_track_last_keyframe_time_mismatch_rejected():
    """PropertyTrack where last keyframe time != end_time is rejected."""
    with pytest.raises(MotionScheduleTimingError) as exc_info:
        PropertyTrack(
            track_id="tr1",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            property_kind=PropertyTrackKind.OPACITY,
            start_time=1.0,
            end_time=2.0,
            keyframes=(
                PropertyKeyframe(offset=0.0, time=1.0, value=0.0),
                PropertyKeyframe(offset=1.0, time=1.8, value=1.0),  # != 2.0
            ),
        )
    assert "last keyframe time" in str(exc_info.value)
    assert "must correspond to track end_time" in str(exc_info.value)


def test_canonical_deserialization_rejects_malformed_property_track():
    """Canonical deserialization rejects PropertyTrack with invalid endpoints or decreasing offsets."""
    # Decreasing offsets in JSON
    bad_track_json = (
        '{"track_id": "tr1", "target": "n1", "target_kind": "NODE", "property_kind": "opacity", '
        '"start_time": 0.0, "end_time": 1.0, "keyframes": ['
        '{"offset": 0.0, "time": 0.0, "value": 0.0, "easing": "linear"}, '
        '{"offset": 0.9, "time": 0.5, "value": 0.5, "easing": "linear"}, '
        '{"offset": 0.4, "time": 0.8, "value": 0.8, "easing": "linear"}, '
        '{"offset": 1.0, "time": 1.0, "value": 1.0, "easing": "linear"}'
        '], "metadata": {}}'
    )
    with pytest.raises((ValidationError, MotionScheduleTimingError)):
        PropertyTrack.model_validate_json(bad_track_json)


def test_canonical_deserialization_rejects_malformed_compiled_event():
    """Canonical deserialization rejects CompiledMotionEvent with mismatched track kinds."""
    bad_event_json = (
        '{"event_id": "e1", "target": "n1", "target_kind": "NODE", "verb": "ENTER", "style": "FADE", '
        '"start_time": 0.0, "end_time": 1.0, "tracks": []}'
    )
    with pytest.raises((ValidationError, MotionCompilationError)):
        CompiledMotionEvent.model_validate_json(bad_event_json)


