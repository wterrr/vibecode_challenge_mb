"""Deterministic motion scheduler for LearnFlow V2 Motion Grammar (CP 2.9).

Constructs dependency DAGs, validates target lifecycles and conflicts,
enforces cognitive motion budgets, and deterministically schedules Tier-1
motion events within scene duration boundaries.
"""

from __future__ import annotations

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
    MotionCognitiveBudgetExceededError,
    MotionConflictError,
    MotionDependencyCycleError,
    MotionDuplicateEventIdError,
    MotionGrammarIncompatibleError,
    MotionInvalidInputError,
    MotionInvalidTargetError,
    MotionLifecycleError,
    MotionSceneMismatchError,
    MotionScheduleTimingError,
    MotionUnsupportedTierError,
)
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.motion.beats import ResolvedMotionPlanTiming, TimingMode
from learnflow_v2.motion.enums import (
    TIER_1_MOTION_GRAMMAR,
    TIER_2_3_RESERVED_STYLES,
    TIER_2_3_RESERVED_VERBS,
    VERB_TARGET_KIND_MAP,
    MotionStyle,
    MotionTargetKind,
    MotionVerb,
)
from learnflow_v2.motion.schema import MotionEvent, MotionPlan
from learnflow_v2.scenegraph.schema import SceneGraph

# Authoritative immutable default durations per Tier-1 verb & style combination (seconds).
# Constructed directly with MappingProxyType without any mutable module-level backing alias.
DEFAULT_TIER_1_DURATIONS: MappingProxyType[tuple[MotionVerb, MotionStyle], float] = MappingProxyType({
    (MotionVerb.ENTER, MotionStyle.FADE): 0.40,
    (MotionVerb.ENTER, MotionStyle.SLIDE): 0.50,
    (MotionVerb.ENTER, MotionStyle.REVEAL): 0.45,
    (MotionVerb.EMPHASIZE, MotionStyle.HIGHLIGHT): 0.35,
    (MotionVerb.EMPHASIZE, MotionStyle.PULSE): 0.50,
    (MotionVerb.EMPHASIZE, MotionStyle.FOCUS): 0.40,
    (MotionVerb.RELATION, MotionStyle.DRAW_EDGE): 0.50,
    (MotionVerb.RELATION, MotionStyle.PROPAGATE): 0.60,
    (MotionVerb.TRANSFORM, MotionStyle.MOVE): 0.50,
    (MotionVerb.EXIT, MotionStyle.FADE): 0.40,
})

# Cognitive budget classifications
DEFAULT_MAJOR_VERBS: frozenset[MotionVerb] = frozenset({
    MotionVerb.ENTER,
    MotionVerb.TRANSFORM,
    MotionVerb.EXIT,
    MotionVerb.RELATION,
})

DEFAULT_MINOR_VERBS: frozenset[MotionVerb] = frozenset({
    MotionVerb.EMPHASIZE,
})

# Explicit target identity decoupling node and relation namespaces
TargetIdentity = tuple[MotionTargetKind, str]


class ScheduledMotionEvent(BaseModel):
    """Immutable scheduled motion event with deterministic timeline placement."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(..., min_length=1, description="Unique motion event identifier")
    target: str = Field(..., min_length=1, description="Target node or relation ID")
    target_kind: MotionTargetKind = Field(..., description="Target entity kind (NODE or RELATION)")
    verb: MotionVerb = Field(..., description="Semantic motion verb")
    style: MotionStyle = Field(..., description="Semantic motion style")
    start_time: float = Field(..., description="Scheduled start time in seconds")
    end_time: float = Field(..., description="Scheduled end time in seconds")
    duration: float = Field(..., description="Calculated duration in seconds")
    dependencies: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Event IDs that must precede this event",
    )
    trigger_beat: str | None = Field(
        default=None,
        description="Associated symbolic narration beat ID if triggered",
    )

    @property
    def target_identity(self) -> TargetIdentity:
        """Explicit typed target identity decoupling NODE and RELATION namespaces."""
        return (self.target_kind, self.target)

    @field_validator("event_id", "target")
    @classmethod
    def _validate_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise MotionInvalidInputError("Identifier cannot be empty or whitespace-only")
        return v.strip()

    @field_validator("start_time", "end_time", "duration", mode="before")
    @classmethod
    def _validate_finite_float(cls, v: Any) -> float:
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise MotionScheduleTimingError(f"Schedule timing value must be a valid float, got {v}")
        if not math.isfinite(val):
            raise MotionScheduleTimingError(f"Schedule timing value must be finite, got {v}")
        if val < 0.0:
            raise MotionScheduleTimingError(f"Schedule timing value cannot be negative, got {v}")
        return val

    @model_validator(mode="after")
    def _validate_event_invariants(self) -> "ScheduledMotionEvent":
        # 1. Grammar validation
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

        # 2. Timing consistency: must represent actual non-zero animation
        if self.end_time <= self.start_time + 1e-4:
            raise MotionScheduleTimingError(
                f"Event '{self.event_id}' end_time ({self.end_time:.4f}s) must be strictly greater than start_time ({self.start_time:.4f}s)"
            )
        if self.duration <= 0.0:
            raise MotionScheduleTimingError(
                f"Event '{self.event_id}' duration must be > 0, got {self.duration:.4f}s"
            )

        expected_dur = round(self.end_time - self.start_time, 4)
        if abs(self.duration - expected_dur) > 1e-3:
            raise MotionScheduleTimingError(
                f"Event '{self.event_id}' duration mismatch: declared {self.duration:.4f}s != calculated {expected_dur:.4f}s"
            )

        return self


class MotionSchedule(BaseModel):
    """Complete, immutable deterministic motion schedule artifact for a scene."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = Field(
        default="2.1",
        description="Schedule schema version (2.1)",
    )
    scene_id: str = Field(..., min_length=1, description="Scene identifier matching MotionPlan")
    scene_duration: float = Field(..., description="Total scene / narration duration in seconds")
    scheduled_events: tuple[ScheduledMotionEvent, ...] = Field(
        default_factory=tuple,
        description="Ordered sequence of scheduled motion events",
    )
    timing_mode: TimingMode | None = Field(
        default=None,
        description="Timing provenance mode from narration beat alignment",
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
    def _validate_schedule_invariants(self) -> "MotionSchedule":
        seen_event_ids: set[str] = set()
        events_by_id: dict[str, ScheduledMotionEvent] = {}
        events_by_target: dict[TargetIdentity, list[ScheduledMotionEvent]] = {}

        prev_start = 0.0
        for ev in self.scheduled_events:
            # 1. Unique event ID
            if ev.event_id in seen_event_ids:
                raise MotionDuplicateEventIdError(
                    f"Duplicate event ID '{ev.event_id}' in MotionSchedule for scene '{self.scene_id}'"
                )
            seen_event_ids.add(ev.event_id)
            events_by_id[ev.event_id] = ev
            events_by_target.setdefault(ev.target_identity, []).append(ev)

            # 2. Scene boundary containment
            if ev.start_time < 0.0 or ev.end_time > self.scene_duration + 1e-4:
                raise MotionScheduleTimingError(
                    f"Scheduled event '{ev.event_id}' interval [{ev.start_time:.4f}s, {ev.end_time:.4f}s] "
                    f"lies outside scene duration [0.0s, {self.scene_duration:.4f}s]"
                )

            # 3. Chronological non-decreasing start order
            if ev.start_time < prev_start - 1e-6:
                raise MotionScheduleTimingError(
                    f"Scheduled events must be ordered non-decreasing by start_time. "
                    f"Event '{ev.event_id}' ({ev.start_time:.4f}s) < previous start ({prev_start:.4f}s)"
                )
            prev_start = ev.start_time

        # Narration timing provenance invariant
        has_triggered_events = any(ev.trigger_beat is not None for ev in self.scheduled_events)
        if has_triggered_events and self.timing_mode is None:
            raise MotionScheduleTimingError(
                f"MotionSchedule for scene '{self.scene_id}' contains triggered events with trigger_beat, "
                f"but timing_mode (narration timing provenance) is None"
            )

        # 4. Dependency graph integrity & causality
        for ev in self.scheduled_events:
            for dep_id in ev.dependencies:
                if dep_id not in events_by_id:
                    raise MotionInvalidInputError(
                        f"Event '{ev.event_id}' references unknown dependency '{dep_id}'"
                    )
                dep_ev = events_by_id[dep_id]
                if dep_ev.end_time > ev.start_time + 1e-4:
                    raise MotionScheduleTimingError(
                        f"Dependency causality violated: dependency '{dep_id}' ends at {dep_ev.end_time:.4f}s "
                        f"after event '{ev.event_id}' starts at {ev.start_time:.4f}s"
                    )

        # 5. Target lifecycle & conflict validation per typed target identity
        for (target_kind, target), target_events in events_by_target.items():
            exit_events = [e for e in target_events if e.verb == MotionVerb.EXIT]
            enter_events = [e for e in target_events if e.verb == MotionVerb.ENTER]

            # Duplicate ENTER check
            if len(enter_events) > 1:
                ids = [e.event_id for e in enter_events]
                raise MotionLifecycleError(
                    f"Target ({target_kind.value}) '{target}' has multiple ENTER events: {ids}"
                )

            # Duplicate EXIT check
            if len(exit_events) > 1:
                ids = [e.event_id for e in exit_events]
                raise MotionLifecycleError(
                    f"Target ({target_kind.value}) '{target}' has multiple EXIT events: {ids}"
                )

            # Events before ENTER availability (if target has an ENTER event)
            if enter_events:
                enter_ev = enter_events[0]
                for e in target_events:
                    if e.event_id == enter_ev.event_id:
                        continue
                    if e.start_time < enter_ev.end_time - 1e-6:
                        raise MotionLifecycleError(
                            f"Target lifecycle error: event '{e.event_id}' ({e.verb.value}) on target "
                            f"({target_kind.value}) '{target}' starts at {e.start_time:.2f}s before target is "
                            f"available at {enter_ev.end_time:.2f}s (after its ENTER event '{enter_ev.event_id}')"
                        )

            # Events after EXIT starts or overlaps EXIT
            if exit_events:
                exit_ev = exit_events[0]
                for e in target_events:
                    if e.event_id == exit_ev.event_id:
                        continue
                    # Any event that starts at or after exit starts
                    if e.start_time >= exit_ev.start_time - 1e-6:
                        raise MotionLifecycleError(
                            f"Target lifecycle error: event '{e.event_id}' ({e.verb.value}) occurs on target "
                            f"({target_kind.value}) '{target}' after its EXIT event '{exit_ev.event_id}' at {exit_ev.start_time:.2f}s"
                        )
                    # Overlap with EXIT check
                    if e.end_time > exit_ev.start_time + 1e-6:
                        raise MotionConflictError(
                            f"Conflict: event '{e.event_id}' ({e.verb.value}) on target ({target_kind.value}) '{target}' "
                            f"overlaps with EXIT event '{exit_ev.event_id}' [{exit_ev.start_time:.2f}s, {exit_ev.end_time:.2f}s]"
                        )

            # Same-target serialization: no two operations on the same target identity may overlap
            for i in range(len(target_events)):
                for j in range(i + 1, len(target_events)):
                    e1 = target_events[i]
                    e2 = target_events[j]
                    overlap_start = max(e1.start_time, e2.start_time)
                    overlap_end = min(e1.end_time, e2.end_time)
                    if overlap_start < overlap_end - 1e-6:
                        if e1.verb == MotionVerb.ENTER or e2.verb == MotionVerb.ENTER:
                            raise MotionLifecycleError(
                                f"Target lifecycle error: simultaneous operation with ENTER on target "
                                f"({target_kind.value}) '{target}' between '{e1.event_id}' and '{e2.event_id}'"
                            )
                        if e1.verb == MotionVerb.EXIT or e2.verb == MotionVerb.EXIT:
                            raise MotionConflictError(
                                f"Conflict: simultaneous operation with EXIT on target "
                                f"({target_kind.value}) '{target}' between '{e1.event_id}' and '{e2.event_id}'"
                            )
                        raise MotionConflictError(
                            f"Conflict: simultaneous overlapping operations on target ({target_kind.value}) '{target}' "
                            f"between '{e1.event_id}' ({e1.verb.value}) and '{e2.event_id}' ({e2.verb.value})"
                        )

        return self

    def to_canonical_json(self) -> str:
        """Serialize MotionSchedule to canonical deterministic JSON."""
        return canonical_json(self)

    @classmethod
    def from_canonical_json(cls, json_str: str) -> "MotionSchedule":
        """Deserialize MotionSchedule from canonical JSON string."""
        return cls.model_validate_json(json_str)


class SchedulerConfig(BaseModel):
    """Deterministic configuration for motion scheduling and cognitive budget.

    All duration mapping state is deeply immutable via MappingProxyType.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    default_durations: MappingProxyType[str, float] = Field(
        default_factory=lambda: MappingProxyType({
            f"{verb.value}:{style.value}": dur
            for (verb, style), dur in DEFAULT_TIER_1_DURATIONS.items()
        }),
        description="Duration mapping keyed by 'verb:style'",
    )
    max_major_simultaneous_motion: int = Field(
        default=2,
        ge=1,
        description="Maximum concurrent major motions allowed simultaneously",
    )
    max_minor_simultaneous_motion: int = Field(
        default=3,
        ge=1,
        description="Maximum concurrent minor motions allowed simultaneously",
    )
    major_verbs: tuple[MotionVerb, ...] = Field(
        default=tuple(sorted(DEFAULT_MAJOR_VERBS, key=lambda v: v.value)),
        description="Verbs categorized as major cognitive load",
    )
    minor_verbs: tuple[MotionVerb, ...] = Field(
        default=tuple(sorted(DEFAULT_MINOR_VERBS, key=lambda v: v.value)),
        description="Verbs categorized as minor cognitive load",
    )
    budget_policy: Literal["defer", "reject"] = Field(
        default="defer",
        description="Policy when cognitive budget is exceeded ('defer' or 'reject')",
    )
    boundary_policy: Literal["compress", "reject"] = Field(
        default="compress",
        description="Policy when event duration overflows scene boundary ('compress' or 'reject')",
    )
    min_duration: float = Field(
        default=0.05,
        ge=0.01,
        description="Minimum compressed animation duration in seconds",
    )

    @field_validator("default_durations", mode="before")
    @classmethod
    def _validate_default_durations(cls, v: Any) -> MappingProxyType[str, float]:
        if v is None:
            source_dict = {
                f"{verb.value}:{style.value}": dur
                for (verb, style), dur in DEFAULT_TIER_1_DURATIONS.items()
            }
        elif isinstance(v, (dict, MappingProxyType)):
            source_dict = dict(v)
        else:
            raise MotionInvalidInputError(f"default_durations must be a mapping, got {type(v)}")

        valid_keys = {
            f"{verb.value}:{style.value}"
            for verb, styles in TIER_1_MOTION_GRAMMAR.items()
            for style in styles
        }

        validated: dict[str, float] = {}
        for k, val in source_dict.items():
            if k not in valid_keys:
                raise MotionInvalidInputError(
                    f"Invalid Tier-1 verb:style duration key '{k}'. Valid keys: {sorted(valid_keys)}"
                )
            try:
                num = float(val)
            except (ValueError, TypeError):
                raise MotionScheduleTimingError(f"Duration for '{k}' must be a float, got {val}")
            if not math.isfinite(num) or num <= 0.0:
                raise MotionScheduleTimingError(
                    f"Duration for '{k}' must be finite and > 0, got {num}"
                )
            validated[k] = num

        return MappingProxyType(validated)

    @field_serializer("default_durations", mode="plain")
    def _serialize_durations(self, v: MappingProxyType[str, float]) -> dict[str, float]:
        return dict(v)

    def get_duration(self, verb: MotionVerb, style: MotionStyle) -> float:
        """Retrieve deterministic duration for verb and style."""
        key = f"{verb.value}:{style.value}"
        if key in self.default_durations:
            return float(self.default_durations[key])
        lookup = (verb, style)
        if lookup in DEFAULT_TIER_1_DURATIONS:
            return DEFAULT_TIER_1_DURATIONS[lookup]
        return 0.40


def build_dependency_dag(
    plan: MotionPlan,
    graph: SceneGraph | None = None,
) -> dict[str, tuple[str, ...]]:
    """Construct deterministic dependency DAG for scene motion events.

    Invariants accounted for:
    - Target lifecycle per (target_kind, target): ENTER -> subsequent operations -> EXIT.
    - Narrative sequence on same target identity: earlier event on target precedes later event.
    - Graph relations: RELATION(edge) depends on ENTER of source and target nodes if present.

    Returns:
        dict mapping event_id -> tuple of prerequisite event_ids.
    Raises:
        MotionDependencyCycleError if a cycle is detected.
    """
    events = list(plan.events)
    deps: dict[str, set[str]] = {ev.id: set() for ev in events}

    # Group events by typed TargetIdentity (target_kind, target)
    events_by_target: dict[TargetIdentity, list[MotionEvent]] = {}
    for ev in events:
        target_kind = ev.target_kind or VERB_TARGET_KIND_MAP[ev.verb]
        events_by_target.setdefault((target_kind, ev.target), []).append(ev)

    # 1. Target lifecycle & narrative ordering on the same target identity
    for (target_kind, target), target_events in events_by_target.items():
        enter_events = [e for e in target_events if e.verb == MotionVerb.ENTER]
        exit_events = [e for e in target_events if e.verb == MotionVerb.EXIT]

        # All non-ENTER events depend on ENTER
        if enter_events:
            enter_id = enter_events[0].id
            for e in target_events:
                if e.id != enter_id:
                    deps[e.id].add(enter_id)

        # EXIT depends on all prior events on this target
        if exit_events:
            exit_id = exit_events[0].id
            for e in target_events:
                if e.id != exit_id and e.id not in enter_events:
                    deps[exit_id].add(e.id)

        # Sequential operations on same target depend on previous operation
        for i in range(len(target_events) - 1):
            curr_ev = target_events[i]
            next_ev = target_events[i + 1]
            deps[next_ev.id].add(curr_ev.id)

    # 2. Relation dependency on endpoint nodes (if SceneGraph is available)
    if graph is not None:
        relations_by_id = {r.id: r for r in graph.relations}
        node_enter_events: dict[str, str] = {}
        for ev in events:
            if ev.verb == MotionVerb.ENTER and (ev.target_kind == MotionTargetKind.NODE or VERB_TARGET_KIND_MAP.get(ev.verb) == MotionTargetKind.NODE):
                node_enter_events[ev.target] = ev.id

        for ev in events:
            if ev.verb == MotionVerb.RELATION:
                rel = relations_by_id.get(ev.target)
                if rel:
                    if rel.source in node_enter_events:
                        deps[ev.id].add(node_enter_events[rel.source])
                    if rel.target in node_enter_events:
                        deps[ev.id].add(node_enter_events[rel.target])

    # 3. Cycle detection using DFS
    visited: dict[str, int] = {}  # 0: unvisited, 1: visiting, 2: visited
    for ev_id in deps:
        visited[ev_id] = 0

    def dfs(node: str, path: list[str]) -> None:
        visited[node] = 1
        path.append(node)
        for neighbor in sorted(deps[node]):
            if visited.get(neighbor) == 1:
                cycle_path = " -> ".join(path[path.index(neighbor) :] + [neighbor])
                raise MotionDependencyCycleError(
                    f"Dependency cycle detected in motion events: {cycle_path}"
                )
            elif visited.get(neighbor) == 0:
                dfs(neighbor, path)
        path.pop()
        visited[node] = 2

    for ev_id in sorted(deps.keys()):
        if visited[ev_id] == 0:
            dfs(ev_id, [])

    # Format return as deterministic sorted tuples
    return {
        ev_id: tuple(sorted(dep_set))
        for ev_id, dep_set in sorted(deps.items(), key=lambda kv: kv[0])
    }


def topological_sort(
    plan: MotionPlan,
    dag: dict[str, tuple[str, ...]],
) -> list[MotionEvent]:
    """Deterministically sort motion events according to DAG and original narrative order."""
    event_lookup = {ev.id: ev for ev in plan.events}
    original_order = {ev.id: idx for idx, ev in enumerate(plan.events)}

    in_degree = {ev.id: 0 for ev in plan.events}
    reverse_graph: dict[str, list[str]] = {ev.id: [] for ev in plan.events}

    for ev_id, dep_tuple in dag.items():
        in_degree[ev_id] = len(dep_tuple)
        for dep in dep_tuple:
            reverse_graph[dep].append(ev_id)

    # Priority queue / sorted ready list based on narrative index
    ready = [ev_id for ev_id, deg in in_degree.items() if deg == 0]
    ready.sort(key=lambda eid: original_order[eid])

    sorted_events: list[MotionEvent] = []
    while ready:
        curr = ready.pop(0)
        sorted_events.append(event_lookup[curr])
        for nxt in sorted(reverse_graph[curr], key=lambda eid: original_order[eid]):
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                ready.append(nxt)
                ready.sort(key=lambda eid: original_order[eid])

    if len(sorted_events) != len(plan.events):
        raise MotionDependencyCycleError("Dependency cycle prevented complete topological sort")

    return sorted_events


def schedule_motion_plan(
    plan: MotionPlan,
    scene_duration: float,
    resolved_timing: ResolvedMotionPlanTiming | None = None,
    graph: SceneGraph | None = None,
    config: SchedulerConfig | None = None,
) -> MotionSchedule:
    """Schedule semantic MotionPlan into an immutable, conflict-free MotionSchedule.

    Validates:
    - Target availability and lifecycle (no event after EXIT, duplicate ENTER/EXIT rejected).
    - Decoupled target identity for NODE vs RELATION namespaces.
    - Strict cross-validation of ResolvedMotionPlanTiming against MotionPlan.
    - Relation target validation (requires SceneGraph to validate target existence).
    - Cognitive motion budget (bounds major/minor concurrent motions).
    - Scene duration boundaries (events never overflow timeline).
    - Tier-1 scope (rejects Camera and Tier 2/3 verbs).
    """
    if config is None:
        config = SchedulerConfig()

    # 1. Require resolved_timing if any event in MotionPlan has a trigger
    has_triggers = any(ev.trigger is not None for ev in plan.events)
    if has_triggers and resolved_timing is None:
        triggered_ids = [ev.id for ev in plan.events if ev.trigger is not None]
        raise MotionScheduleTimingError(
            f"MotionPlan for scene '{plan.scene_id}' contains triggered events {triggered_ids}, "
            f"but resolved_timing was not provided. Triggered events must be resolved via narration alignment."
        )

    # Cross-validate ResolvedMotionPlanTiming against MotionPlan
    if resolved_timing is not None:
        if plan.scene_id != resolved_timing.scene_id:
            raise MotionSceneMismatchError(
                f"MotionPlan scene_id '{plan.scene_id}' does not match resolved timing scene_id '{resolved_timing.scene_id}'"
            )

        plan_events_by_id = {ev.id: ev for ev in plan.events}
        plan_ids = set(plan_events_by_id.keys())

        resolved_ids_list = [ret.event_id for ret in resolved_timing.event_timings]
        resolved_ids = set(resolved_ids_list)
        if len(resolved_ids_list) != len(resolved_ids):
            raise MotionInvalidInputError("ResolvedMotionPlanTiming contains duplicate event_id in event_timings")

        untriggered_ids_list = list(resolved_timing.untriggered_events)
        untriggered_ids = set(untriggered_ids_list)
        if len(untriggered_ids_list) != len(untriggered_ids):
            raise MotionInvalidInputError("ResolvedMotionPlanTiming contains duplicate event_id in untriggered_events")

        overlap = resolved_ids & untriggered_ids
        if overlap:
            raise MotionInvalidInputError(f"Event IDs appear in both event_timings and untriggered_events: {sorted(overlap)}")

        extra_resolved = resolved_ids - plan_ids
        if extra_resolved:
            raise MotionInvalidInputError(f"ResolvedMotionPlanTiming contains unknown event IDs not in plan: {sorted(extra_resolved)}")

        extra_untriggered = untriggered_ids - plan_ids
        if extra_untriggered:
            raise MotionInvalidInputError(f"ResolvedMotionPlanTiming untriggered_events contains unknown event IDs not in plan: {sorted(extra_untriggered)}")

        missing_ids = plan_ids - (resolved_ids | untriggered_ids)
        if missing_ids:
            raise MotionInvalidInputError(f"MotionPlan event IDs missing from ResolvedMotionPlanTiming: {sorted(missing_ids)}")

        # Enforce trigger contract and semantic identity
        for ev in plan.events:
            if ev.trigger is not None:
                if ev.id not in resolved_ids:
                    raise MotionInvalidInputError(
                        f"Triggered event '{ev.id}' (beat '{ev.trigger.beat}') must appear in resolved event_timings, "
                        f"but was found in untriggered_events or missing"
                    )
            else:
                if ev.id not in untriggered_ids:
                    raise MotionInvalidInputError(
                        f"Untriggered event '{ev.id}' cannot appear in resolved event_timings; must be in untriggered_events"
                    )

        for ret in resolved_timing.event_timings:
            ev = plan_events_by_id[ret.event_id]
            if ret.target != ev.target:
                raise MotionInvalidInputError(
                    f"ResolvedEventTiming for '{ev.id}' target mismatch: expected '{ev.target}', got '{ret.target}'"
                )
            if ret.verb != ev.verb:
                raise MotionInvalidInputError(
                    f"ResolvedEventTiming for '{ev.id}' verb mismatch: expected '{ev.verb.value}', got '{ret.verb.value}'"
                )
            if ret.style != ev.style:
                raise MotionInvalidInputError(
                    f"ResolvedEventTiming for '{ev.id}' style mismatch: expected '{ev.style.value}', got '{ret.style.value}'"
                )
            if ev.trigger is not None and ret.beat_id != ev.trigger.beat:
                raise MotionInvalidInputError(
                    f"ResolvedEventTiming for '{ev.id}' beat_id mismatch: expected '{ev.trigger.beat}', got '{ret.beat_id}'"
                )

    # 2. Relation target existence check
    relation_events = [
        ev for ev in plan.events
        if ev.verb == MotionVerb.RELATION or ev.target_kind == MotionTargetKind.RELATION
    ]
    if relation_events:
        if graph is None:
            first_rel = relation_events[0]
            raise MotionInvalidTargetError(
                f"Motion event '{first_rel.id}' targets relation '{first_rel.target}', "
                f"but no SceneGraph was provided to validate target existence."
            )

    if graph is not None:
        plan.validate_with_scenegraph(graph)

    # 3. Check for Tier-2/3 or Camera attempts
    for ev in plan.events:
        if ev.verb in TIER_2_3_RESERVED_VERBS:
            raise MotionUnsupportedTierError(
                f"Motion verb '{ev.verb.value}' is reserved for Tier 2/3 and unsupported in Tier 1."
            )
        if ev.style in TIER_2_3_RESERVED_STYLES:
            raise MotionUnsupportedTierError(
                f"Motion style '{ev.style.value}' is reserved for Tier 2/3 and unsupported in Tier 1."
            )

    # 4. Pre-flight lifecycle check on plan narrative order per TargetIdentity
    events_by_target: dict[TargetIdentity, list[MotionEvent]] = {}
    for ev in plan.events:
        target_kind = ev.target_kind or VERB_TARGET_KIND_MAP[ev.verb]
        events_by_target.setdefault((target_kind, ev.target), []).append(ev)

    for (target_kind, target), target_events in events_by_target.items():
        enter_indices = [idx for idx, e in enumerate(target_events) if e.verb == MotionVerb.ENTER]
        if len(enter_indices) > 1:
            enter_ids = [target_events[idx].id for idx in enter_indices]
            raise MotionLifecycleError(
                f"Target ({target_kind.value}) '{target}' has multiple ENTER events: {enter_ids}"
            )

        exit_indices = [idx for idx, e in enumerate(target_events) if e.verb == MotionVerb.EXIT]
        if len(exit_indices) > 1:
            exit_ids = [target_events[idx].id for idx in exit_indices]
            raise MotionLifecycleError(
                f"Target ({target_kind.value}) '{target}' has multiple EXIT events: {exit_ids}"
            )
        if exit_indices:
            exit_idx = exit_indices[0]
            exit_ev = target_events[exit_idx]
            # Check if any event occurs after EXIT on the same target in plan order
            if exit_idx < len(target_events) - 1:
                after_ev = target_events[exit_idx + 1]
                raise MotionLifecycleError(
                    f"Target lifecycle error: event '{after_ev.id}' ({after_ev.verb.value}) occurs on target "
                    f"({target_kind.value}) '{target}' after its EXIT event '{exit_ev.id}'"
                )

        # Check if EMPHASIZE or TRANSFORM appears before ENTER on a node that has ENTER
        if enter_indices:
            enter_idx = enter_indices[0]
            enter_ev = target_events[enter_idx]
            if enter_idx > 0:
                before_ev = target_events[0]
                raise MotionLifecycleError(
                    f"Target lifecycle error: event '{before_ev.id}' ({before_ev.verb.value}) occurs on target "
                    f"({target_kind.value}) '{target}' before its ENTER event '{enter_ev.id}'"
                )

    # 5. Build DAG & Topological Order
    dag = build_dependency_dag(plan, graph)
    sorted_events = topological_sort(plan, dag)

    # 6. Build timing mapping from ResolvedMotionPlanTiming
    resolved_times: dict[str, float] = {}
    timing_mode: TimingMode | None = None
    if resolved_timing is not None:
        timing_mode = resolved_timing.timing_mode
        for ret in resolved_timing.event_timings:
            resolved_times[ret.event_id] = ret.time

    # 7. Schedule events iteratively
    scheduled_list: list[ScheduledMotionEvent] = []
    scheduled_by_id: dict[str, ScheduledMotionEvent] = {}
    target_last_end_time: dict[TargetIdentity, float] = {}

    for ev in sorted_events:
        target_kind = ev.target_kind or VERB_TARGET_KIND_MAP[ev.verb]
        target_key: TargetIdentity = (target_kind, ev.target)

        # Determine duration
        raw_duration = config.get_duration(ev.verb, ev.style)

        # Determine target dependencies completion time
        dep_ids = dag.get(ev.id, ())
        dep_end_times = [scheduled_by_id[dep_id].end_time for dep_id in dep_ids if dep_id in scheduled_by_id]
        min_dep_time = max(dep_end_times, default=0.0)

        # Determine target serialization: operations on the same target identity must not overlap
        min_target_time = target_last_end_time.get(target_key, 0.0)

        # Initial start time
        if ev.id in resolved_times:
            candidate_start = resolved_times[ev.id]
        else:
            # Untriggered event: schedule immediately after dependencies and prior event
            prev_end = scheduled_list[-1].end_time if scheduled_list else 0.0
            candidate_start = max(min_dep_time, min_target_time, prev_end)

        # Enforce causality
        candidate_start = max(candidate_start, min_dep_time, min_target_time)

        # Cognitive Budget check and adjustment
        is_major = ev.verb in config.major_verbs
        is_minor = ev.verb in config.minor_verbs

        def count_active(t_start: float, t_end: float) -> tuple[int, int]:
            major_cnt = 0
            minor_cnt = 0
            for s in scheduled_list:
                # Overlap test: [t_start, t_end) with [s.start_time, s.end_time)
                if max(t_start, s.start_time) < min(t_end, s.end_time) - 1e-4:
                    if s.verb in config.major_verbs:
                        major_cnt += 1
                    elif s.verb in config.minor_verbs:
                        minor_cnt += 1
            return major_cnt, minor_cnt

        curr_start = candidate_start
        curr_duration = raw_duration

        # Iterate finding a budget-compliant slot
        max_search_steps = 100
        step = 0
        while step < max_search_steps:
            step += 1
            curr_end = curr_start + curr_duration
            major_cnt, minor_cnt = count_active(curr_start, curr_end)

            if is_major and major_cnt >= config.max_major_simultaneous_motion:
                if config.budget_policy == "reject":
                    raise MotionCognitiveBudgetExceededError(
                        f"Major motion cognitive budget exceeded for event '{ev.id}' at {curr_start:.2f}s "
                        f"(maximum {config.max_major_simultaneous_motion} simultaneous major motions allowed)"
                    )
                # Defer: find next scheduled event end time to jump to
                next_release = min(
                    (s.end_time for s in scheduled_list if s.end_time > curr_start + 1e-4 and s.verb in config.major_verbs),
                    default=curr_start + 0.1,
                )
                curr_start = round(next_release, 4)
                continue

            if is_minor and minor_cnt >= config.max_minor_simultaneous_motion:
                if config.budget_policy == "reject":
                    raise MotionCognitiveBudgetExceededError(
                        f"Minor motion cognitive budget exceeded for event '{ev.id}' at {curr_start:.2f}s "
                        f"(maximum {config.max_minor_simultaneous_motion} simultaneous minor motions allowed)"
                    )
                next_release = min(
                    (s.end_time for s in scheduled_list if s.end_time > curr_start + 1e-4 and s.verb in config.minor_verbs),
                    default=curr_start + 0.1,
                )
                curr_start = round(next_release, 4)
                continue

            # Budget satisfied
            break

        # Check scene boundary policy
        curr_end = round(curr_start + curr_duration, 4)
        if curr_end > scene_duration + 1e-4:
            available_time = scene_duration - curr_start
            if config.boundary_policy == "compress":
                if available_time < config.min_duration - 1e-4:
                    raise MotionScheduleTimingError(
                        f"Event '{ev.id}' start time {curr_start:.2f}s cannot fit within scene duration {scene_duration:.2f}s "
                        f"(available {available_time:.2f}s < minimum {config.min_duration:.2f}s)"
                    )
                curr_duration = round(available_time, 4)
                curr_end = round(scene_duration, 4)
            else:
                raise MotionScheduleTimingError(
                    f"Event '{ev.id}' scheduled end time {curr_end:.2f}s exceeds scene duration {scene_duration:.2f}s"
                )

        scheduled_ev = ScheduledMotionEvent(
            event_id=ev.id,
            target=ev.target,
            target_kind=target_kind,
            verb=ev.verb,
            style=ev.style,
            start_time=round(curr_start, 4),
            end_time=round(curr_end, 4),
            duration=round(curr_duration, 4),
            dependencies=dag.get(ev.id, ()),
            trigger_beat=ev.trigger.beat if ev.trigger else None,
        )

        scheduled_list.append(scheduled_ev)
        scheduled_by_id[ev.id] = scheduled_ev
        target_last_end_time[target_key] = scheduled_ev.end_time

    # Sort final schedule deterministically by start_time, then end_time, then event_id
    scheduled_list.sort(key=lambda s: (s.start_time, s.end_time, s.event_id))

    return MotionSchedule(
        scene_id=plan.scene_id,
        scene_duration=scene_duration,
        scheduled_events=tuple(scheduled_list),
        timing_mode=timing_mode,
    )
