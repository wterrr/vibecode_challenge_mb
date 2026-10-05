"""Tests for LearnFlow V2 — CP 2.9: Motion Scheduler (test_motion_scheduler_v2_09.py)."""

import math
import pytest
from pydantic import ValidationError

from learnflow_v2.core.errors import (
    MotionCognitiveBudgetExceededError,
    MotionConflictError,
    MotionDependencyCycleError,
    MotionDuplicateEventIdError,
    MotionLifecycleError,
    MotionScheduleTimingError,
    MotionUnsupportedTierError,
)
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.motion.beats import (
    ResolvedEventTiming,
    ResolvedMotionPlanTiming,
    TimingMode,
)
from learnflow_v2.motion.enums import MotionStyle, MotionTargetKind, MotionVerb
from learnflow_v2.motion.scheduler import (
    DEFAULT_MAJOR_VERBS,
    DEFAULT_MINOR_VERBS,
    DEFAULT_TIER_1_DURATIONS,
    MotionSchedule,
    ScheduledMotionEvent,
    SchedulerConfig,
    build_dependency_dag,
    schedule_motion_plan,
    topological_sort,
)
from learnflow_v2.motion.schema import MotionEvent, MotionPlan, MotionTrigger
from learnflow_v2.scenegraph.enums import NodeKind, RelationKind
from learnflow_v2.scenegraph.schema import SceneGraph, SceneNode, SceneRelation


# =========================================================================
# Fixtures & Helpers
# =========================================================================

def make_sample_scenegraph(scene_id: str = "scene_01") -> SceneGraph:
    return SceneGraph(
        scene_id=scene_id,
        nodes=[
            SceneNode(id="n1", kind=NodeKind.CONCEPT),
            SceneNode(id="n2", kind=NodeKind.CONCEPT),
        ],
        relations=[
            SceneRelation(id="r1", source="n1", target="n2", kind=RelationKind.FLOW),
        ],
    )


# =========================================================================
# 1. Dependency & Lifecycle Tests
# =========================================================================

def test_enter_emphasize_exit_valid():
    """ENTER -> EMPHASIZE -> EXIT on the same target is valid and scheduled in order."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            MotionEvent(id="e2", target="n1", verb=MotionVerb.EMPHASIZE, style=MotionStyle.HIGHLIGHT),
            MotionEvent(id="e3", target="n1", verb=MotionVerb.EXIT, style=MotionStyle.FADE),
        ),
    )
    dag = build_dependency_dag(plan)
    assert "e1" in dag["e2"]
    assert "e2" in dag["e3"]

    schedule = schedule_motion_plan(plan, scene_duration=5.0)
    assert len(schedule.scheduled_events) == 3
    e1_s, e2_s, e3_s = schedule.scheduled_events

    assert e1_s.event_id == "e1"
    assert e2_s.event_id == "e2"
    assert e3_s.event_id == "e3"

    assert e1_s.end_time <= e2_s.start_time
    assert e2_s.end_time <= e3_s.start_time
    assert e3_s.end_time <= 5.0


def test_emphasize_before_target_availability_rejected():
    """EMPHASIZE before ENTER on the same target is rejected with MotionLifecycleError."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.EMPHASIZE, style=MotionStyle.HIGHLIGHT),
            MotionEvent(id="e2", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
        ),
    )
    with pytest.raises(MotionLifecycleError) as exc_info:
        schedule_motion_plan(plan, scene_duration=5.0)
    assert "before its ENTER event" in str(exc_info.value)


def test_event_after_exit_rejected():
    """An event targeting a node after its EXIT event is rejected with MotionLifecycleError."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            MotionEvent(id="e2", target="n1", verb=MotionVerb.EMPHASIZE, style=MotionStyle.PULSE),
            MotionEvent(id="e3", target="n1", verb=MotionVerb.EXIT, style=MotionStyle.FADE),
            MotionEvent(id="e4", target="n1", verb=MotionVerb.EMPHASIZE, style=MotionStyle.HIGHLIGHT),
        ),
    )
    with pytest.raises(MotionLifecycleError) as exc_info:
        schedule_motion_plan(plan, scene_duration=5.0)
    assert "after its EXIT event" in str(exc_info.value)


def test_duplicate_exit_rejected():
    """Duplicate EXIT events on the same target are rejected with MotionLifecycleError."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            MotionEvent(id="e2", target="n1", verb=MotionVerb.EXIT, style=MotionStyle.FADE),
            MotionEvent(id="e3", target="n1", verb=MotionVerb.EXIT, style=MotionStyle.FADE),
        ),
    )
    with pytest.raises(MotionLifecycleError) as exc_info:
        schedule_motion_plan(plan, scene_duration=5.0)
    assert "multiple EXIT events" in str(exc_info.value)


def test_dependency_cycle_rejected():
    """Direct or indirect dependency cycles in DAG construction are rejected."""
    # Build a simulated cycle test with manual DAG cycle detection
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            MotionEvent(id="e2", target="n2", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
        ),
    )
    # The normal planner on independent nodes has no cycle
    dag = build_dependency_dag(plan)
    assert len(dag) == 2

    # A topological sort with artificially cyclical DAG triggers cycle error
    cyclic_dag = {"e1": ("e2",), "e2": ("e1",)}
    with pytest.raises(MotionDependencyCycleError):
        topological_sort(plan, cyclic_dag)


def test_deterministic_topological_order_for_independent_events():
    """Independent events maintain stable deterministic order matching original narrative order."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="alpha", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            MotionEvent(id="beta", target="n2", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
        ),
    )
    dag = build_dependency_dag(plan)
    ordered = topological_sort(plan, dag)
    assert [e.id for e in ordered] == ["alpha", "beta"]


# =========================================================================
# 2. Timing & Trigger Tests
# =========================================================================

def test_triggered_event_starts_according_to_resolved_timing():
    """Triggered events follow the exact timestamps provided by ResolvedMotionPlanTiming."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(
                id="e1",
                target="n1",
                verb=MotionVerb.ENTER,
                style=MotionStyle.FADE,
                trigger=MotionTrigger(beat="intro"),
            ),
            MotionEvent(
                id="e2",
                target="n1",
                verb=MotionVerb.EMPHASIZE,
                style=MotionStyle.PULSE,
                trigger=MotionTrigger(beat="focus_n1"),
            ),
        ),
    )
    resolved_timing = ResolvedMotionPlanTiming(
        scene_id="scene_01",
        timing_mode=TimingMode.PROVIDER_WORD_TIMINGS,
        event_timings=(
            ResolvedEventTiming(
                event_id="e1",
                beat_id="intro",
                time=1.20,
                target="n1",
                verb=MotionVerb.ENTER,
                style=MotionStyle.FADE,
            ),
            ResolvedEventTiming(
                event_id="e2",
                beat_id="focus_n1",
                time=2.50,
                target="n1",
                verb=MotionVerb.EMPHASIZE,
                style=MotionStyle.PULSE,
            ),
        ),
    )

    schedule = schedule_motion_plan(plan, scene_duration=5.0, resolved_timing=resolved_timing)
    assert schedule.scheduled_events[0].start_time == 1.20
    assert schedule.scheduled_events[1].start_time == 2.50
    assert schedule.timing_mode == TimingMode.PROVIDER_WORD_TIMINGS


def test_untriggered_events_receive_deterministic_scheduling():
    """Untriggered events are deterministically scheduled based on dependencies and durations."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            MotionEvent(id="e2", target="n2", verb=MotionVerb.ENTER, style=MotionStyle.SLIDE),
        ),
    )
    schedule = schedule_motion_plan(plan, scene_duration=5.0)
    assert schedule.scheduled_events[0].start_time == 0.0
    assert schedule.scheduled_events[0].end_time == 0.40  # default ENTER+FADE is 0.4s
    # e2 is independent, but scheduled in narrative sequence
    assert schedule.scheduled_events[1].start_time == 0.40
    assert schedule.scheduled_events[1].end_time == 0.90  # default ENTER+SLIDE is 0.5s


def test_event_cannot_extend_beyond_scene_duration_compress_or_reject():
    """Events anchored near scene end are compressed or rejected per configuration."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(
                id="e1",
                target="n1",
                verb=MotionVerb.ENTER,
                style=MotionStyle.FADE,
                trigger=MotionTrigger(beat="late"),
            ),
        ),
    )
    resolved_timing = ResolvedMotionPlanTiming(
        scene_id="scene_01",
        timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
        event_timings=(
            ResolvedEventTiming(
                event_id="e1",
                beat_id="late",
                time=4.80,
                target="n1",
                verb=MotionVerb.ENTER,
                style=MotionStyle.FADE,
            ),
        ),
    )
    # Default ENTER+FADE duration is 0.4s, which would end at 5.2s > 5.0s.
    # With default 'compress' policy and min_duration=0.05s, it compresses to 0.20s (4.80 to 5.00s)
    schedule = schedule_motion_plan(plan, scene_duration=5.0, resolved_timing=resolved_timing)
    ev = schedule.scheduled_events[0]
    assert ev.start_time == 4.80
    assert ev.end_time == 5.00
    assert ev.duration == 0.20

    # With 'reject' policy, it raises MotionScheduleTimingError
    cfg_reject = SchedulerConfig(boundary_policy="reject")
    with pytest.raises(MotionScheduleTimingError):
        schedule_motion_plan(
            plan,
            scene_duration=5.0,
            resolved_timing=resolved_timing,
            config=cfg_reject,
        )


def test_nan_inf_negative_schedule_timing_rejected_by_artifact():
    """ScheduledMotionEvent and MotionSchedule reject NaN, inf, and negative timestamps."""
    with pytest.raises(MotionScheduleTimingError):
        ScheduledMotionEvent(
            event_id="e1",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            verb=MotionVerb.ENTER,
            style=MotionStyle.FADE,
            start_time=float("inf"),
            end_time=1.0,
            duration=1.0,
        )

    with pytest.raises(MotionScheduleTimingError):
        ScheduledMotionEvent(
            event_id="e1",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            verb=MotionVerb.ENTER,
            style=MotionStyle.FADE,
            start_time=-0.5,
            end_time=1.0,
            duration=1.5,
        )

    with pytest.raises(MotionScheduleTimingError):
        MotionSchedule(
            scene_id="s1",
            scene_duration=float("nan"),
            scheduled_events=(),
        )


def test_same_inputs_produce_identical_canonical_schedule():
    """Identical plan and timing inputs produce byte-for-byte identical canonical schedules."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            MotionEvent(id="e2", target="n1", verb=MotionVerb.EMPHASIZE, style=MotionStyle.HIGHLIGHT),
            MotionEvent(id="e3", target="n1", verb=MotionVerb.EXIT, style=MotionStyle.FADE),
        ),
    )
    s1 = schedule_motion_plan(plan, scene_duration=10.0)
    s2 = schedule_motion_plan(plan, scene_duration=10.0)

    json1 = s1.to_canonical_json()
    json2 = s2.to_canonical_json()
    assert json1 == json2

    roundtrip = MotionSchedule.from_canonical_json(json1)
    assert roundtrip.to_canonical_json() == json1


# =========================================================================
# 3. Conflict Tests
# =========================================================================

def test_direct_construction_rejects_overlapping_incompatible_motions():
    """MotionSchedule rejects directly constructed conflicting events on the same target."""
    e1 = ScheduledMotionEvent(
        event_id="e1",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.TRANSFORM,
        style=MotionStyle.MOVE,
        start_time=1.0,
        end_time=2.0,
        duration=1.0,
    )
    e2 = ScheduledMotionEvent(
        event_id="e2",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.TRANSFORM,
        style=MotionStyle.MOVE,
        start_time=1.5,
        end_time=2.5,
        duration=1.0,
    )
    with pytest.raises(MotionConflictError):
        MotionSchedule(
            scene_id="s1",
            scene_duration=5.0,
            scheduled_events=(e1, e2),
        )


def test_tier_1_gate_rejects_camera_and_tier_2_3():
    """CP2.9 scheduler strictly preserves Tier-1 boundaries, rejecting camera and reserved verbs."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
        ),
    )
    # Attempting to schedule with an invalid verb
    with pytest.raises(MotionUnsupportedTierError):
        ScheduledMotionEvent(
            event_id="cam_ev",
            target="cam",
            target_kind=MotionTargetKind.NODE,
            verb=MotionVerb.CAMERA,  # Reserved Tier 3
            style=MotionStyle.PUSH,
            start_time=0.0,
            end_time=1.0,
            duration=1.0,
        )


# =========================================================================
# 4. Cognitive Motion Budget Tests
# =========================================================================

def test_cognitive_budget_deferral():
    """Simultaneous major motions exceeding the budget (default 2) are deterministically deferred."""
    # 3 simultaneous ENTER events on different nodes
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE, trigger=MotionTrigger(beat="b1")),
            MotionEvent(id="e2", target="n2", verb=MotionVerb.ENTER, style=MotionStyle.FADE, trigger=MotionTrigger(beat="b1")),
            MotionEvent(id="e3", target="n3", verb=MotionVerb.ENTER, style=MotionStyle.FADE, trigger=MotionTrigger(beat="b1")),
        ),
    )
    resolved_timing = ResolvedMotionPlanTiming(
        scene_id="scene_01",
        timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
        event_timings=(
            ResolvedEventTiming(event_id="e1", beat_id="b1", time=1.0, target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            ResolvedEventTiming(event_id="e2", beat_id="b1", time=1.0, target="n2", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            ResolvedEventTiming(event_id="e3", beat_id="b1", time=1.0, target="n3", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
        ),
    )

    # With default policy='defer', max_major=2: e1 and e2 run at 1.0s, e3 is deferred until e1/e2 finish at 1.4s
    schedule = schedule_motion_plan(plan, scene_duration=10.0, resolved_timing=resolved_timing)
    assert schedule.scheduled_events[0].start_time == 1.0
    assert schedule.scheduled_events[1].start_time == 1.0
    assert schedule.scheduled_events[2].start_time == 1.40
    assert schedule.scheduled_events[2].end_time == 1.80


def test_cognitive_budget_rejection_policy():
    """Simultaneous major motions exceeding the budget raise MotionCognitiveBudgetExceededError when policy='reject'."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE, trigger=MotionTrigger(beat="b1")),
            MotionEvent(id="e2", target="n2", verb=MotionVerb.ENTER, style=MotionStyle.FADE, trigger=MotionTrigger(beat="b1")),
            MotionEvent(id="e3", target="n3", verb=MotionVerb.ENTER, style=MotionStyle.FADE, trigger=MotionTrigger(beat="b1")),
        ),
    )
    resolved_timing = ResolvedMotionPlanTiming(
        scene_id="scene_01",
        timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
        event_timings=(
            ResolvedEventTiming(event_id="e1", beat_id="b1", time=1.0, target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            ResolvedEventTiming(event_id="e2", beat_id="b1", time=1.0, target="n2", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            ResolvedEventTiming(event_id="e3", beat_id="b1", time=1.0, target="n3", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
        ),
    )
    cfg_reject = SchedulerConfig(budget_policy="reject", max_major_simultaneous_motion=2)
    with pytest.raises(MotionCognitiveBudgetExceededError) as exc_info:
        schedule_motion_plan(
            plan,
            scene_duration=10.0,
            resolved_timing=resolved_timing,
            config=cfg_reject,
        )
    assert "Major motion cognitive budget exceeded" in str(exc_info.value)


# =========================================================================
# 5. Focused Hardening Regressions (Blockers 1, 2, 4, 6, 7)
# =========================================================================

def test_no_mutable_duration_backing_alias_can_alter_runtime():
    """Verify no module-level mutable dict backing alias exists for DEFAULT_TIER_1_DURATIONS."""
    import learnflow_v2.motion.scheduler as scheduler_mod
    from types import MappingProxyType

    assert not hasattr(scheduler_mod, "_DEFAULT_TIER_1_DURATIONS"), (
        "Reachable mutable alias _DEFAULT_TIER_1_DURATIONS must not exist"
    )
    assert isinstance(scheduler_mod.DEFAULT_TIER_1_DURATIONS, MappingProxyType)

    with pytest.raises(TypeError):
        scheduler_mod.DEFAULT_TIER_1_DURATIONS[(MotionVerb.ENTER, MotionStyle.FADE)] = 99.0  # type: ignore[index]


def test_scheduler_config_duration_mapping_cannot_be_mutated():
    """SchedulerConfig.default_durations is an immutable MappingProxyType."""
    cfg = SchedulerConfig()
    with pytest.raises(TypeError):
        cfg.default_durations["ENTER:FADE"] = 7.0  # type: ignore[index]


def test_invalid_negative_nan_inf_duration_override_rejected():
    """SchedulerConfig rejects invalid keys, negative, zero, NaN, and inf duration values."""
    from learnflow_v2.core.errors import MotionInvalidInputError

    # Negative duration
    with pytest.raises(MotionScheduleTimingError):
        SchedulerConfig(default_durations={"ENTER:FADE": -1.0})

    # Zero duration
    with pytest.raises(MotionScheduleTimingError):
        SchedulerConfig(default_durations={"ENTER:FADE": 0.0})

    # NaN duration
    with pytest.raises(MotionScheduleTimingError):
        SchedulerConfig(default_durations={"ENTER:FADE": float("nan")})

    # Inf duration
    with pytest.raises(MotionScheduleTimingError):
        SchedulerConfig(default_durations={"ENTER:FADE": float("inf")})

    # Unknown/malformed key
    with pytest.raises(MotionInvalidInputError):
        SchedulerConfig(default_durations={"INVALID:ACTION": 0.5})


def test_scheduled_motion_event_duration_zero_rejected():
    """ScheduledMotionEvent strictly rejects zero-duration animations."""
    with pytest.raises(MotionScheduleTimingError):
        ScheduledMotionEvent(
            event_id="e1",
            target="n1",
            target_kind=MotionTargetKind.NODE,
            verb=MotionVerb.ENTER,
            style=MotionStyle.FADE,
            start_time=1.0,
            end_time=1.0,
            duration=0.0,
        )

    # Rejection via canonical deserialization
    bad_json = (
        '{"event_id": "e1", "target": "n1", "target_kind": "NODE", '
        '"verb": "ENTER", "style": "FADE", "start_time": 1.0, "end_time": 1.0, "duration": 0.0}'
    )
    with pytest.raises((ValidationError, MotionScheduleTimingError)):
        ScheduledMotionEvent.model_validate_json(bad_json)


def test_duplicate_enter_same_target_rejected():
    """Duplicate ENTER events on the same node target are rejected with MotionLifecycleError."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            MotionEvent(id="e2", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.SLIDE),
        ),
    )
    with pytest.raises(MotionLifecycleError) as exc_info:
        schedule_motion_plan(plan, scene_duration=5.0)
    assert "multiple ENTER events" in str(exc_info.value)

    # Artifact validation rejection
    ev1 = ScheduledMotionEvent(
        event_id="e1",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.ENTER,
        style=MotionStyle.FADE,
        start_time=0.0,
        end_time=0.40,
        duration=0.40,
    )
    ev2 = ScheduledMotionEvent(
        event_id="e2",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.ENTER,
        style=MotionStyle.SLIDE,
        start_time=0.40,
        end_time=0.90,
        duration=0.50,
    )
    with pytest.raises(MotionLifecycleError):
        MotionSchedule(scene_id="scene_01", scene_duration=5.0, scheduled_events=(ev1, ev2))


def test_relation_target_without_scenegraph_rejected():
    """Scheduling a RELATION event without a SceneGraph fails explicitly with MotionInvalidTargetError."""
    from learnflow_v2.core.errors import MotionInvalidTargetError

    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="ghost_rel", verb=MotionVerb.RELATION, style=MotionStyle.DRAW_EDGE),
        ),
    )
    with pytest.raises(MotionInvalidTargetError) as exc_info:
        schedule_motion_plan(plan, scene_duration=5.0, graph=None)
    assert "no SceneGraph was provided to validate target existence" in str(exc_info.value)


def test_relation_target_unknown_in_scenegraph_rejected():
    """Scheduling a RELATION event with unknown relation ID in SceneGraph fails with MotionInvalidTargetError."""
    from learnflow_v2.core.errors import MotionInvalidTargetError

    graph = make_sample_scenegraph("scene_01")
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="unknown_rel", verb=MotionVerb.RELATION, style=MotionStyle.DRAW_EDGE),
        ),
    )
    with pytest.raises(MotionInvalidTargetError) as exc_info:
        schedule_motion_plan(plan, scene_duration=5.0, graph=graph)
    assert "unknown relation" in str(exc_info.value)


def test_relation_target_valid_in_scenegraph_schedules_successfully():
    """Scheduling a RELATION event with valid relation ID in SceneGraph succeeds."""
    graph = make_sample_scenegraph("scene_01")
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e_enter1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            MotionEvent(id="e_enter2", target="n2", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            MotionEvent(id="e_rel", target="r1", verb=MotionVerb.RELATION, style=MotionStyle.DRAW_EDGE),
        ),
    )
    schedule = schedule_motion_plan(plan, scene_duration=5.0, graph=graph)
    assert len(schedule.scheduled_events) == 3
    rel_s = schedule.scheduled_events[2]
    assert rel_s.event_id == "e_rel"
    assert rel_s.target == "r1"
    assert rel_s.target_kind == MotionTargetKind.RELATION


# =========================================================================
# 6. Target Namespace & Cross-Validation Regressions (Blockers 2 & 3)
# =========================================================================

def test_node_and_relation_same_id_distinct_namespaces():
    """NODE 'same' and RELATION 'same' have distinct target identities and do not conflate lifecycles."""
    # SceneGraph where a node and a relation share the same raw ID 'same'
    graph = SceneGraph(
        scene_id="scene_01",
        nodes=[
            SceneNode(id="same", kind=NodeKind.CONCEPT),
            SceneNode(id="other", kind=NodeKind.CONCEPT),
        ],
        relations=[
            SceneRelation(id="same", source="same", target="other", kind=RelationKind.FLOW),
        ],
    )
    # Plan: ENTER node same, EXIT node same, DRAW_EDGE relation same
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e_node_enter", target="same", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            MotionEvent(id="e_node_exit", target="same", verb=MotionVerb.EXIT, style=MotionStyle.FADE),
            MotionEvent(id="e_rel", target="same", verb=MotionVerb.RELATION, style=MotionStyle.DRAW_EDGE),
        ),
    )
    # Must schedule without raising lifecycle error between node 'same' and relation 'same'
    schedule = schedule_motion_plan(plan, scene_duration=5.0, graph=graph)
    assert len(schedule.scheduled_events) == 3

    node_exit = [e for e in schedule.scheduled_events if e.event_id == "e_node_exit"][0]
    rel_draw = [e for e in schedule.scheduled_events if e.event_id == "e_rel"][0]

    assert node_exit.target_kind == MotionTargetKind.NODE
    assert rel_draw.target_kind == MotionTargetKind.RELATION


def test_resolved_timing_semantic_mismatch_target_rejected():
    """ResolvedEventTiming with target mismatch is rejected."""
    from learnflow_v2.core.errors import MotionInvalidInputError

    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE, trigger=MotionTrigger(beat="b1")),
        ),
    )
    timing = ResolvedMotionPlanTiming(
        scene_id="scene_01",
        timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
        event_timings=(
            ResolvedEventTiming(event_id="e1", beat_id="b1", time=1.0, target="OTHER", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
        ),
    )
    with pytest.raises(MotionInvalidInputError) as exc_info:
        schedule_motion_plan(plan, scene_duration=5.0, resolved_timing=timing)
    assert "target mismatch" in str(exc_info.value)


def test_resolved_timing_semantic_mismatch_verb_rejected():
    """ResolvedEventTiming with verb mismatch is rejected."""
    from learnflow_v2.core.errors import MotionInvalidInputError

    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE, trigger=MotionTrigger(beat="b1")),
        ),
    )
    timing = ResolvedMotionPlanTiming(
        scene_id="scene_01",
        timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
        event_timings=(
            ResolvedEventTiming(event_id="e1", beat_id="b1", time=1.0, target="n1", verb=MotionVerb.EXIT, style=MotionStyle.FADE),
        ),
    )
    with pytest.raises(MotionInvalidInputError) as exc_info:
        schedule_motion_plan(plan, scene_duration=5.0, resolved_timing=timing)
    assert "verb mismatch" in str(exc_info.value)


def test_resolved_timing_semantic_mismatch_style_rejected():
    """ResolvedEventTiming with style mismatch is rejected."""
    from learnflow_v2.core.errors import MotionInvalidInputError

    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE, trigger=MotionTrigger(beat="b1")),
        ),
    )
    timing = ResolvedMotionPlanTiming(
        scene_id="scene_01",
        timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
        event_timings=(
            ResolvedEventTiming(event_id="e1", beat_id="b1", time=1.0, target="n1", verb=MotionVerb.ENTER, style=MotionStyle.SLIDE),
        ),
    )
    with pytest.raises(MotionInvalidInputError) as exc_info:
        schedule_motion_plan(plan, scene_duration=5.0, resolved_timing=timing)
    assert "style mismatch" in str(exc_info.value)


def test_resolved_timing_semantic_mismatch_beat_id_rejected():
    """ResolvedEventTiming with beat_id mismatch is rejected."""
    from learnflow_v2.core.errors import MotionInvalidInputError

    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE, trigger=MotionTrigger(beat="intro")),
        ),
    )
    timing = ResolvedMotionPlanTiming(
        scene_id="scene_01",
        timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
        event_timings=(
            ResolvedEventTiming(event_id="e1", beat_id="wrong_beat", time=1.0, target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
        ),
    )
    with pytest.raises(MotionInvalidInputError) as exc_info:
        schedule_motion_plan(plan, scene_duration=5.0, resolved_timing=timing)
    assert "beat_id mismatch" in str(exc_info.value)


def test_resolved_timing_triggered_event_in_untriggered_rejected():
    """Triggered event placed in untriggered_events is rejected."""
    from learnflow_v2.core.errors import MotionInvalidInputError

    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE, trigger=MotionTrigger(beat="intro")),
        ),
    )
    timing = ResolvedMotionPlanTiming(
        scene_id="scene_01",
        timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
        event_timings=(),
        untriggered_events=("e1",),
    )
    with pytest.raises(MotionInvalidInputError) as exc_info:
        schedule_motion_plan(plan, scene_duration=5.0, resolved_timing=timing)
    assert "must appear in resolved event_timings" in str(exc_info.value)


def test_resolved_timing_untriggered_event_in_timings_rejected():
    """Untriggered event placed in event_timings is rejected."""
    from learnflow_v2.core.errors import MotionInvalidInputError

    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
        ),
    )
    timing = ResolvedMotionPlanTiming(
        scene_id="scene_01",
        timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
        event_timings=(
            ResolvedEventTiming(event_id="e1", beat_id="fallback", time=1.0, target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
        ),
        untriggered_events=(),
    )
    with pytest.raises(MotionInvalidInputError) as exc_info:
        schedule_motion_plan(plan, scene_duration=5.0, resolved_timing=timing)
    assert "Untriggered event 'e1' cannot appear in resolved event_timings" in str(exc_info.value)


# =========================================================================
# 7. Narration Trigger Requirement & Provenance Invariants (Blocker 1)
# =========================================================================

def test_triggered_plan_without_resolved_timing_rejected():
    """MotionPlan containing triggered events rejects scheduling if resolved_timing is None."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(
                id="e1",
                target="n1",
                verb=MotionVerb.ENTER,
                style=MotionStyle.FADE,
                trigger=MotionTrigger(beat="intro"),
            ),
        ),
    )
    with pytest.raises(MotionScheduleTimingError) as exc_info:
        schedule_motion_plan(plan, scene_duration=5.0, resolved_timing=None)
    assert "contains triggered events" in str(exc_info.value)
    assert "resolved_timing was not provided" in str(exc_info.value)


def test_all_untriggered_plan_without_resolved_timing_succeeds():
    """MotionPlan without triggers schedules deterministically when resolved_timing is None."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            MotionEvent(id="e2", target="n1", verb=MotionVerb.EXIT, style=MotionStyle.FADE),
        ),
    )
    schedule = schedule_motion_plan(plan, scene_duration=5.0, resolved_timing=None)
    assert schedule.timing_mode is None
    assert len(schedule.scheduled_events) == 2
    assert all(ev.trigger_beat is None for ev in schedule.scheduled_events)


def test_motion_schedule_trigger_beat_without_timing_mode_rejected():
    """Direct construction of MotionSchedule with trigger_beat rejects timing_mode=None."""
    ev = ScheduledMotionEvent(
        event_id="e1",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.ENTER,
        style=MotionStyle.FADE,
        start_time=0.0,
        end_time=0.40,
        duration=0.40,
        trigger_beat="intro",
    )
    with pytest.raises(MotionScheduleTimingError) as exc_info:
        MotionSchedule(
            scene_id="scene_01",
            scene_duration=5.0,
            scheduled_events=(ev,),
            timing_mode=None,
        )
    assert "contains triggered events with trigger_beat" in str(exc_info.value)
    assert "timing_mode (narration timing provenance) is None" in str(exc_info.value)


def test_motion_schedule_trigger_beat_without_timing_mode_canonical_deserialization_rejected():
    """Canonical deserialization rejects MotionSchedule having trigger_beat with null timing_mode."""
    bad_json = (
        '{"schema_version": "2.1", "scene_id": "scene_01", "scene_duration": 5.0, '
        '"scheduled_events": [{"event_id": "e1", "target": "n1", "target_kind": "NODE", '
        '"verb": "ENTER", "style": "FADE", "start_time": 0.0, "end_time": 0.40, "duration": 0.40, '
        '"dependencies": [], "trigger_beat": "intro"}], "timing_mode": null}'
    )
    with pytest.raises((ValidationError, MotionScheduleTimingError)):
        MotionSchedule.model_validate_json(bad_json)


def test_valid_triggered_plan_with_cp2_08_resolved_timing_succeeds():
    """Triggered plan with valid CP2.8 resolved timing produces schedule with correct timing provenance."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(
                id="e1",
                target="n1",
                verb=MotionVerb.ENTER,
                style=MotionStyle.FADE,
                trigger=MotionTrigger(beat="intro"),
            ),
        ),
    )
    timing = ResolvedMotionPlanTiming(
        scene_id="scene_01",
        timing_mode=TimingMode.PROVIDER_WORD_TIMINGS,
        event_timings=(
            ResolvedEventTiming(
                event_id="e1",
                beat_id="intro",
                time=1.50,
                target="n1",
                verb=MotionVerb.ENTER,
                style=MotionStyle.FADE,
            ),
        ),
    )
    schedule = schedule_motion_plan(plan, scene_duration=5.0, resolved_timing=timing)
    assert schedule.timing_mode == TimingMode.PROVIDER_WORD_TIMINGS
    assert len(schedule.scheduled_events) == 1
    assert schedule.scheduled_events[0].start_time == 1.50
    assert schedule.scheduled_events[0].trigger_beat == "intro"


def test_deterministic_fallback_cp2_08_timing_remains_valid():
    """Triggered plan with CP2.8 deterministic fallback timing succeeds and preserves fallback provenance."""
    plan = MotionPlan(
        scene_id="scene_01",
        events=(
            MotionEvent(
                id="e1",
                target="n1",
                verb=MotionVerb.ENTER,
                style=MotionStyle.FADE,
                trigger=MotionTrigger(beat="intro"),
            ),
        ),
    )
    timing = ResolvedMotionPlanTiming(
        scene_id="scene_01",
        timing_mode=TimingMode.DETERMINISTIC_FALLBACK,
        event_timings=(
            ResolvedEventTiming(
                event_id="e1",
                beat_id="intro",
                time=2.00,
                target="n1",
                verb=MotionVerb.ENTER,
                style=MotionStyle.FADE,
            ),
        ),
    )
    schedule = schedule_motion_plan(plan, scene_duration=5.0, resolved_timing=timing)
    assert schedule.timing_mode == TimingMode.DETERMINISTIC_FALLBACK
    assert schedule.scheduled_events[0].start_time == 2.00


# =========================================================================
# 8. Target Lifecycle & Same-Target Availability Invariants (Blocker 2)
# =========================================================================

def test_motion_schedule_enter_overlaps_emphasize_rejected():
    """Direct construction of MotionSchedule where ENTER overlaps EMPHASIZE on same target is rejected."""
    e_enter = ScheduledMotionEvent(
        event_id="e_enter",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.ENTER,
        style=MotionStyle.FADE,
        start_time=0.0,
        end_time=1.0,
        duration=1.0,
    )
    e_emph = ScheduledMotionEvent(
        event_id="e_emph",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.EMPHASIZE,
        style=MotionStyle.PULSE,
        start_time=0.2,
        end_time=0.8,
        duration=0.6,
    )
    with pytest.raises(MotionLifecycleError) as exc_info:
        MotionSchedule(
            scene_id="scene_01",
            scene_duration=5.0,
            scheduled_events=(e_enter, e_emph),
        )
    assert "before target is available" in str(exc_info.value) or "simultaneous operation with ENTER" in str(exc_info.value)


def test_motion_schedule_enter_overlaps_transform_rejected():
    """Direct construction of MotionSchedule where ENTER overlaps TRANSFORM on same target is rejected."""
    e_enter = ScheduledMotionEvent(
        event_id="e_enter",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.ENTER,
        style=MotionStyle.FADE,
        start_time=0.0,
        end_time=1.0,
        duration=1.0,
    )
    e_trans = ScheduledMotionEvent(
        event_id="e_trans",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.TRANSFORM,
        style=MotionStyle.MOVE,
        start_time=0.5,
        end_time=1.2,
        duration=0.7,
    )
    with pytest.raises(MotionLifecycleError) as exc_info:
        MotionSchedule(
            scene_id="scene_01",
            scene_duration=5.0,
            scheduled_events=(e_enter, e_trans),
        )
    assert "before target is available" in str(exc_info.value) or "simultaneous operation with ENTER" in str(exc_info.value)


def test_motion_schedule_emphasize_starts_exactly_at_enter_end_valid():
    """Operation on target starting exactly at ENTER.end is valid."""
    e_enter = ScheduledMotionEvent(
        event_id="e_enter",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.ENTER,
        style=MotionStyle.FADE,
        start_time=0.0,
        end_time=1.0,
        duration=1.0,
    )
    e_emph = ScheduledMotionEvent(
        event_id="e_emph",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.EMPHASIZE,
        style=MotionStyle.HIGHLIGHT,
        start_time=1.0,
        end_time=1.5,
        duration=0.5,
        dependencies=("e_enter",),
    )
    schedule = MotionSchedule(
        scene_id="scene_01",
        scene_duration=5.0,
        scheduled_events=(e_enter, e_emph),
    )
    assert len(schedule.scheduled_events) == 2
    assert schedule.scheduled_events[0].end_time == schedule.scheduled_events[1].start_time


def test_existing_enter_emphasize_exit_schedule_remains_valid():
    """Existing full lifecycle sequence ENTER -> EMPHASIZE -> EXIT on target is valid."""
    e1 = ScheduledMotionEvent(
        event_id="e1",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.ENTER,
        style=MotionStyle.FADE,
        start_time=0.0,
        end_time=1.0,
        duration=1.0,
    )
    e2 = ScheduledMotionEvent(
        event_id="e2",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.EMPHASIZE,
        style=MotionStyle.PULSE,
        start_time=1.0,
        end_time=1.8,
        duration=0.8,
        dependencies=("e1",),
    )
    e3 = ScheduledMotionEvent(
        event_id="e3",
        target="n1",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.EXIT,
        style=MotionStyle.FADE,
        start_time=1.8,
        end_time=2.3,
        duration=0.5,
        dependencies=("e2",),
    )
    schedule = MotionSchedule(
        scene_id="scene_01",
        scene_duration=5.0,
        scheduled_events=(e1, e2, e3),
    )
    assert len(schedule.scheduled_events) == 3


def test_node_and_relation_same_id_remain_independent_in_schedule():
    """NODE 'same' and RELATION 'same' can have overlapping schedules without lifecycle collision."""
    e_node = ScheduledMotionEvent(
        event_id="e_node",
        target="same",
        target_kind=MotionTargetKind.NODE,
        verb=MotionVerb.ENTER,
        style=MotionStyle.FADE,
        start_time=0.0,
        end_time=1.0,
        duration=1.0,
    )
    e_rel = ScheduledMotionEvent(
        event_id="e_rel",
        target="same",
        target_kind=MotionTargetKind.RELATION,
        verb=MotionVerb.RELATION,
        style=MotionStyle.DRAW_EDGE,
        start_time=0.2,
        end_time=0.8,
        duration=0.6,
    )
    # Different target identities: (NODE, "same") vs (RELATION, "same")
    schedule = MotionSchedule(
        scene_id="scene_01",
        scene_duration=5.0,
        scheduled_events=(e_node, e_rel),
    )
    assert len(schedule.scheduled_events) == 2


def test_canonical_deserialization_rejects_lifecycle_overlap():
    """Canonical deserialization rejects MotionSchedule violating target lifecycle availability."""
    bad_json = (
        '{"schema_version": "2.1", "scene_id": "scene_01", "scene_duration": 5.0, '
        '"scheduled_events": ['
        '{"event_id": "e_enter", "target": "n1", "target_kind": "NODE", "verb": "ENTER", "style": "FADE", '
        '"start_time": 0.0, "end_time": 1.0, "duration": 1.0, "dependencies": []}, '
        '{"event_id": "e_emph", "target": "n1", "target_kind": "NODE", "verb": "EMPHASIZE", "style": "PULSE", '
        '"start_time": 0.2, "end_time": 0.8, "duration": 0.6, "dependencies": []}'
        '], "timing_mode": null}'
    )
    with pytest.raises((ValidationError, MotionLifecycleError)):
        MotionSchedule.model_validate_json(bad_json)

