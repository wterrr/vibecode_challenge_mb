"""Layout candidate generation, bounded collision repair, and deterministic ranking for LearnFlow V2.

Core Pipeline (PLAN_V2):
    candidate generation
            ↓
       layout solve
            ↓
    collision detection
            ↓
      bounded repair (MAX_LAYOUT_SOLVES = 5)
            ↓
    HARD FEASIBILITY GATE
            ↓
     only feasible survive
            ↓
        SOFT SCORE
            ↓
   deterministic ranking
            ↓
   best feasible candidate

Invariants:
- Hard correctness > continuity > readability > aesthetics.
- An infeasible candidate NEVER outranks a feasible candidate.
- Input order NEVER determines the tie-break winner.
- Solver iteration is strictly bounded (MAX_LAYOUT_SOLVES = 5).
"""

import sys
from typing import Any

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, ValidationError, field_validator, model_validator

from learnflow_v2.core.errors import LayoutInvalidInputError, LayoutUnsatisfiableError
from learnflow_v2.layout.collision import (
    choose_separation_constraint,
    detect_box_collisions,
    SeparationConstraint,
)
from learnflow_v2.layout.constraints import LayoutItemInput, solve_layout
from learnflow_v2.layout.profiles import get_frame_profile
from learnflow_v2.layout.schema import FrameProfile, LayoutGraph, LayoutStrategy, SIMPLE_LAYOUT_STRATEGIES
from learnflow_v2.layout.score import (
    compute_soft_score,
    evaluate_feasibility,
    LayoutFeasibilityReport,
    SoftLayoutScore,
    SoftScoreWeights,
)

MAX_LAYOUT_SOLVES: int = 5


class CollisionRepairResult(BaseModel):
    """Strict immutable report on iterative collision repair execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    initial_graph: LayoutGraph = Field(..., description="Initial candidate layout graph before repair")
    repaired_graph: LayoutGraph = Field(..., description="Final layout graph after repair passes")
    solve_count: int = Field(..., ge=1, le=5, description="Total solver calls executed")
    repair_count: int = Field(..., ge=0, description="Total repair iterations executed")
    constraints_added: list[SeparationConstraint] = Field(default_factory=list, description="All separation constraints added")
    initial_collision_count: int = Field(..., ge=0, description="Collisions present in initial graph")
    remaining_collision_count: int = Field(..., ge=0, description="Collisions remaining in repaired graph")
    resolved: bool = Field(..., description="True if remaining_collision_count == 0")

    @field_validator("solve_count", "repair_count", "initial_collision_count", "remaining_collision_count", mode="before")
    @classmethod
    def validate_strict_counts(cls, v: Any, info: ValidationInfo) -> int:
        if isinstance(v, bool) or not isinstance(v, int):
            raise TypeError(f"Field '{info.field_name}' must be an integer, got {type(v).__name__}: {v!r}")
        if v < 0:
            raise ValueError(f"Field '{info.field_name}' must be >= 0, got {v}")
        return v

    @field_validator("resolved", mode="before")
    @classmethod
    def validate_resolved_bool(cls, v: Any, info: ValidationInfo) -> bool:
        if not isinstance(v, bool):
            raise TypeError(f"Field '{info.field_name}' must be a boolean, got {type(v).__name__}: {v!r}")
        return v

    @model_validator(mode="after")
    def validate_consistency(self) -> Self:
        expected_resolved = (self.remaining_collision_count == 0)
        if self.resolved != expected_resolved:
            raise ValueError(
                f"resolved ({self.resolved}) does not match (remaining_collision_count == 0, is {self.remaining_collision_count})"
            )
        if self.repair_count > self.solve_count - 1:
            raise ValueError(
                f"repair_count ({self.repair_count}) exceeds solve_count - 1 ({self.solve_count - 1})"
            )
        if self.initial_collision_count == 0 and self.repair_count > 0:
            raise ValueError(
                f"repair_count ({self.repair_count}) cannot be > 0 when initial_collision_count is 0"
            )
        if self.repair_count > 0 and self.initial_collision_count == 0:
            raise ValueError(
                f"initial_collision_count must be > 0 when repair_count ({self.repair_count}) > 0"
            )
        return self


class LayoutCandidate(BaseModel):
    """Explicit evaluation artifact for a layout candidate variant."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str = Field(..., min_length=1, description="Deterministic candidate identifier")
    strategy: LayoutStrategy = Field(..., description="Layout strategy applied")
    variant: str = Field(..., min_length=1, description="Topological variant (e.g. PRIMARY, STACKED)")
    layout_graph: LayoutGraph | None = Field(default=None, description="Solved LayoutGraph artifact if available")
    feasibility: LayoutFeasibilityReport = Field(..., description="Hard feasibility report")
    soft_score: SoftLayoutScore | None = Field(default=None, description="Soft layout score (feasible candidates only)")
    solve_count: int = Field(default=0, ge=0, description="Total solver calls executed for this candidate")
    repair_count: int = Field(default=0, ge=0, description="Total collision repair passes executed")

    @field_validator("solve_count", "repair_count", mode="before")
    @classmethod
    def validate_candidate_counts(cls, v: Any, info: ValidationInfo) -> int:
        if isinstance(v, bool) or not isinstance(v, int):
            raise TypeError(f"Field '{info.field_name}' must be an integer, got {type(v).__name__}: {v!r}")
        if v < 0:
            raise ValueError(f"Field '{info.field_name}' must be >= 0, got {v}")
        return v


class LayoutOptimizationResult(BaseModel):
    """Result of layout optimization pass over candidate variants."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    selected: LayoutCandidate = Field(..., description="Best feasible candidate selected")
    candidates: list[LayoutCandidate] = Field(..., description="All evaluated candidate variants")
    attempted_count: int = Field(..., ge=1, description="Number of candidate variants attempted")

    @field_validator("attempted_count", mode="before")
    @classmethod
    def validate_strict_attempted_count(cls, v: Any, info: ValidationInfo) -> int:
        if isinstance(v, bool) or not isinstance(v, int):
            raise TypeError(f"Field '{info.field_name}' must be a strict int, got {type(v).__name__}: {v!r}")
        if v < 1:
            raise ValueError(f"Field '{info.field_name}' must be >= 1, got {v}")
        return v

    @model_validator(mode="after")
    def validate_consistency(self) -> Self:
        if not self.candidates:
            raise ValueError("candidates list must contain at least 1 candidate")
        if self.attempted_count != len(self.candidates):
            raise ValueError(
                f"attempted_count ({self.attempted_count}) must match len(candidates) ({len(self.candidates)})"
            )
        candidate_ids = [c.candidate_id for c in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError(f"Duplicate candidate IDs found in candidates: {candidate_ids}")
        if not any(c.candidate_id == self.selected.candidate_id for c in self.candidates):
            raise ValueError(
                f"selected candidate '{self.selected.candidate_id}' not found in candidates: {candidate_ids}"
            )
        return self


def repair_layout_collisions(
    initial_graph: LayoutGraph,
    profile: FrameProfile | str | None = None,
    items: list[LayoutItemInput] | None = None,
    max_solves: int = MAX_LAYOUT_SOLVES,
    variant: str = "PRIMARY",
    tol: float = 1e-3,
    continuity_constraints: list[Any] | None = None,
) -> CollisionRepairResult:
    """Repair box collisions in a LayoutGraph using deterministic linear separation constraints and real Kiwi re-solve.

    Algorithm (V2-05 Section C):
        initial solved/candidate LayoutGraph
                    ↓
        detect_box_collisions()
                    ↓
        choose deterministic CollisionPair
                    ↓
        choose_separation_constraint()
                    ↓
        add REQUIRED SeparationConstraint
                    ↓
        real solve_layout() / Kiwi solve
                    ↓
        detect again

    No manual coordinate mutation is performed. All geometry is re-solved by Kiwi.
    Bounded strictly by max_solves (1 <= max_solves <= MAX_LAYOUT_SOLVES).
    """
    if isinstance(max_solves, bool) or not isinstance(max_solves, int) or max_solves < 1 or max_solves > MAX_LAYOUT_SOLVES:
        raise LayoutInvalidInputError(
            f"max_solves must be an integer between 1 and {MAX_LAYOUT_SOLVES}, got {max_solves}"
        )

    prof = get_frame_profile(profile or initial_graph.frame_profile_id)
    strat = initial_graph.strategy

    if items is None:
        layout_items = [
            LayoutItemInput(
                node_id=b.node_id,
                role=b.strategy_role or "content",
                target_zone=b.zone,
                min_width=b.rect.width,
                min_height=b.rect.height,
                semantic_key=b.semantic_key,
            )
            for b in initial_graph.boxes
        ]
    else:
        layout_items = items

    initial_collisions = detect_box_collisions(initial_graph, tol=tol)
    initial_collision_count = len(initial_collisions)

    if initial_collision_count == 0:
        return CollisionRepairResult(
            initial_graph=initial_graph,
            repaired_graph=initial_graph,
            solve_count=1,
            repair_count=0,
            constraints_added=[],
            initial_collision_count=0,
            remaining_collision_count=0,
            resolved=True,
        )

    current_graph = initial_graph
    current_collisions = list(initial_collisions)
    constraints_added: list[SeparationConstraint] = []
    solve_count = 1
    repair_count = 0

    while current_collisions and solve_count < max_solves:
        col = current_collisions[0]
        box_map = {b.node_id: b for b in current_graph.boxes}
        sc = choose_separation_constraint(col, box_map, prof, strat)

        if sc in constraints_added:
            break

        constraints_added.append(sc)

        try:
            re_solved = solve_layout(
                scene_id=initial_graph.scene_id,
                strategy=strat,
                profile=prof,
                items=layout_items,
                variant=variant,
                separation_constraints=constraints_added,
                continuity_constraints=continuity_constraints,
            )
            current_graph = re_solved
            solve_count += 1
            repair_count += 1
            current_collisions = detect_box_collisions(current_graph, tol=tol)
        except LayoutUnsatisfiableError:
            solve_count += 1
            break

    remaining_collision_count = len(current_collisions)
    resolved = (remaining_collision_count == 0)

    return CollisionRepairResult(
        initial_graph=initial_graph,
        repaired_graph=current_graph,
        solve_count=solve_count,
        repair_count=repair_count,
        constraints_added=constraints_added,
        initial_collision_count=initial_collision_count,
        remaining_collision_count=remaining_collision_count,
        resolved=resolved,
    )


def choose_best_candidate(candidates: list[LayoutCandidate], scene_id: str = "") -> LayoutCandidate:
    """Deterministically choose the best layout candidate following Stage A/B architecture.

    Algorithm:
    1. Categorically eliminate infeasible candidates (feasibility.feasible == False).
    2. If zero feasible candidates remain, raise LayoutUnsatisfiableError.
    3. Rank remaining feasible candidates by soft_score.total ascending.
    4. Deterministic tie-break on (soft_score.total, strategy.value, variant, candidate_id).
       Input order never influences the winner.
    """
    if not candidates:
        raise LayoutInvalidInputError("choose_best_candidate requires at least one candidate")

    # Stage A: Hard Feasibility Gate
    feasible = [
        c
        for c in candidates
        if c.feasibility.feasible and c.layout_graph is not None and c.soft_score is not None
    ]

    if not feasible:
        rejected_details = {
            c.candidate_id: {
                "feasible": c.feasibility.feasible,
                "overflow": c.feasibility.overflow_count,
                "overlap": c.feasibility.fatal_overlap_count,
                "clipping": c.feasibility.clipping_count,
                "safe_zone": c.feasibility.safe_zone_violation_count,
                "invalid_geometry": c.feasibility.invalid_geometry_count,
                "edge_node": c.feasibility.edge_node_intersection_count,
                "readability": c.feasibility.minimum_readability_violation_count,
                "violations": c.feasibility.violations[:5],
            }
            for c in candidates
        }
        raise LayoutUnsatisfiableError(
            f"All {len(candidates)} layout candidate(s) failed hard feasibility gates",
            details={
                "scene_id": scene_id,
                "attempted_count": len(candidates),
                "rejected_candidates": list(rejected_details.keys()),
                "candidate_diagnostics": rejected_details,
            },
        )

    # Stage B: Soft Ranking with deterministic tie-breaking
    sorted_candidates = sorted(
        feasible,
        key=lambda c: (
            c.soft_score.total,
            c.strategy.value,
            c.variant,
            c.candidate_id,
        ),
    )

    return sorted_candidates[0]


def evaluate_graph_candidate(
    candidate_id: str,
    layout_graph: LayoutGraph,
    variant: str = "PRIMARY",
    profile: FrameProfile | str | None = None,
    weights: SoftScoreWeights | None = None,
    continuity: Any | None = None,
) -> LayoutCandidate:
    """Evaluate a directed graph LayoutGraph as a candidate without mutating node coordinates.

    Zero node dragging is performed. All geometry comes strictly from graph compiler output.
    """
    prof = get_frame_profile(profile or layout_graph.frame_profile_id)
    feasibility = evaluate_feasibility(layout_graph, profile=prof)

    soft_score: SoftLayoutScore | None = None
    if feasibility.feasible:
        soft_score = compute_soft_score(
            layout_graph,
            profile=prof,
            weights=weights,
            continuity_context=continuity,
        )

    return LayoutCandidate(
        candidate_id=candidate_id,
        strategy=layout_graph.strategy,
        variant=variant,
        layout_graph=layout_graph if feasibility.feasible else None,
        feasibility=feasibility,
        soft_score=soft_score,
        solve_count=1,
        repair_count=0,
    )


def optimize_simple_layout(
    scene_id: str,
    strategy: LayoutStrategy | str,
    profile: FrameProfile | str,
    items: list[LayoutItemInput | dict[str, Any]],
    metadata: dict[str, Any] | None = None,
    weights: SoftScoreWeights | None = None,
    max_solves: int = MAX_LAYOUT_SOLVES,
    continuity: Any | None = None,
) -> LayoutOptimizationResult:
    """Coordinate candidate generation, bounded Kiwi collision repair, and deterministic selection.

    Supported strategies:
    - CONCEPT_CARD (PRIMARY variant)
    - COMPARISON (PRIMARY [two-column], STACKED [two-row fallback])
    - IMAGE_TEXT (PRIMARY [side-by-side in 16:9, stacked in 9:16], STACKED [fallback in 16:9])
    - QUOTE (PRIMARY variant)

    Bounded repair loop:
    Runs up to max_solves (default 5, 1 <= max_solves <= 5) total solves per candidate variant.
    Separation constraints are added as required linear inequalities.

    Raises:
        LayoutInvalidInputError: If inputs are invalid or max_solves out of bounds
        LayoutUnsatisfiableError: If all candidate variants fail hard feasibility gates
    """
    if isinstance(max_solves, bool) or not isinstance(max_solves, int) or max_solves < 1 or max_solves > MAX_LAYOUT_SOLVES:
        raise LayoutInvalidInputError(
            f"max_solves must be an integer between 1 and {MAX_LAYOUT_SOLVES}, got {max_solves}"
        )

    strat = LayoutStrategy(strategy) if isinstance(strategy, str) else strategy
    prof = get_frame_profile(profile)

    if strat == LayoutStrategy.COMPARISON:
        variants = ["PRIMARY", "STACKED"]
    elif strat == LayoutStrategy.IMAGE_TEXT:
        variants = ["PRIMARY", "STACKED"] if prof.aspect_ratio == "16:9" else ["PRIMARY"]
    elif strat == LayoutStrategy.CONCEPT_CARD:
        variants = ["PRIMARY"]
    elif strat == LayoutStrategy.QUOTE:
        variants = ["PRIMARY"]
    else:
        raise LayoutInvalidInputError(
            f"optimize_simple_layout does not support strategy '{strat.value}'. Supported: {sorted(s.value for s in SIMPLE_LAYOUT_STRATEGIES)}"
        )

    validated_items: list[LayoutItemInput] = []
    for it in items:
        if isinstance(it, LayoutItemInput):
            validated_items.append(it)
        elif isinstance(it, dict):
            try:
                validated_items.append(LayoutItemInput(**it))
            except (ValidationError, TypeError, ValueError) as exc:
                raise LayoutInvalidInputError(f"Invalid item data: {exc}") from exc
        else:
            raise LayoutInvalidInputError(f"Expected LayoutItemInput or dict, got {type(it).__name__}")

    measurements = {it.node_id: (float(it.min_width), float(it.min_height)) for it in validated_items}

    continuity_constraints = continuity.constraints if continuity and hasattr(continuity, "constraints") else None
    if continuity_constraints:
        item_by_id = {it.node_id: it for it in validated_items}
        for cc in continuity_constraints:
            if cc.node_id not in item_by_id:
                raise LayoutInvalidInputError(
                    f"Continuity constraint references unknown node_id '{cc.node_id}' not in current layout items",
                    details={"node_id": cc.node_id, "constraint_semantic_key": cc.semantic_key},
                )
            cur_item = item_by_id[cc.node_id]
            if cur_item.semantic_key and cur_item.semantic_key != cc.semantic_key:
                raise LayoutInvalidInputError(
                    f"Continuity constraint semantic_key '{cc.semantic_key}' does not match item '{cc.node_id}' semantic_key '{cur_item.semantic_key}'",
                    details={
                        "node_id": cc.node_id,
                        "constraint_semantic_key": cc.semantic_key,
                        "item_semantic_key": cur_item.semantic_key,
                    },
                )

    candidates: list[LayoutCandidate] = []

    for variant in variants:
        candidate_id = f"{strat.value}_{variant}"

        try:
            # 1. Initial candidate solve with Kiwi
            initial_graph = solve_layout(
                scene_id=scene_id,
                strategy=strat,
                profile=prof,
                items=validated_items,
                metadata=metadata,
                variant=variant,
                continuity_constraints=continuity_constraints,
            )
        except LayoutUnsatisfiableError:
            infeasible_report = LayoutFeasibilityReport(
                overflow_count=1,
                fatal_overlap_count=0,
                clipping_count=0,
                safe_zone_violation_count=0,
                invalid_geometry_count=0,
                edge_node_intersection_count=0,
                minimum_readability_violation_count=0,
                feasible=False,
                violations=["Kiwi constraints unsatisfiable for variant"],
            )
            candidates.append(
                LayoutCandidate(
                    candidate_id=candidate_id,
                    strategy=strat,
                    variant=variant,
                    layout_graph=None,
                    feasibility=infeasible_report,
                    soft_score=None,
                    solve_count=1,
                    repair_count=0,
                )
            )
            continue

        # 2. Check collisions and run bounded repair if needed
        cols = detect_box_collisions(initial_graph)
        if cols:
            repair_res = repair_layout_collisions(
                initial_graph=initial_graph,
                profile=prof,
                items=validated_items,
                max_solves=max_solves,
                variant=variant,
                continuity_constraints=continuity_constraints,
            )
            last_graph = repair_res.repaired_graph
            solve_count = repair_res.solve_count
            repair_count = repair_res.repair_count
        else:
            last_graph = initial_graph
            solve_count = 1
            repair_count = 0

        # 3. Hard feasibility evaluation (Stage A)
        feasibility = evaluate_feasibility(
            layout_graph=last_graph,
            profile=prof,
            measurements=measurements,
            expected_node_ids=[it.node_id for it in validated_items],
            min_readable_bounds=measurements,
        )

        # 4. Soft scoring (Stage B: feasible candidates only)
        soft_score: SoftLayoutScore | None = None
        if feasibility.feasible:
            soft_score = compute_soft_score(
                last_graph,
                profile=prof,
                weights=weights,
                continuity_context=continuity,
            )

        candidates.append(
            LayoutCandidate(
                candidate_id=candidate_id,
                strategy=strat,
                variant=variant,
                layout_graph=last_graph if feasibility.feasible else None,
                feasibility=feasibility,
                soft_score=soft_score,
                solve_count=solve_count,
                repair_count=repair_count,
            )
        )

    # 5. Deterministic selection
    selected = choose_best_candidate(candidates, scene_id=scene_id)

    return LayoutOptimizationResult(
        selected=selected,
        candidates=candidates,
        attempted_count=len(variants),
    )
