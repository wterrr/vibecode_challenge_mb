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

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from learnflow_v2.core.errors import LayoutInvalidInputError, LayoutUnsatisfiableError
from learnflow_v2.layout.collision import choose_separation_constraint, detect_box_collisions, SeparationConstraint
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


class LayoutOptimizationResult(BaseModel):
    """Result of layout optimization pass over candidate variants."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    selected: LayoutCandidate = Field(..., description="Best feasible candidate selected")
    candidates: list[LayoutCandidate] = Field(..., description="All evaluated candidate variants")
    attempted_count: int = Field(..., ge=1, description="Number of candidate variants attempted")


def choose_best_candidate(candidates: list[LayoutCandidate]) -> LayoutCandidate:
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
                "violations": c.feasibility.violations[:5],
            }
            for c in candidates
        }
        raise LayoutUnsatisfiableError(
            f"All {len(candidates)} layout candidate(s) failed hard feasibility gates",
            details={
                "attempted_count": len(candidates),
                "rejected_candidates": list(rejected_details.keys()),
                "candidate_diagnostics": rejected_details,
            },
        )

    # Stage B: Soft Ranking with deterministic tie-breaking
    # Sort key: (total_score, strategy_value, variant, candidate_id)
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
) -> LayoutCandidate:
    """Evaluate a directed graph LayoutGraph as a candidate without mutating node coordinates.

    Zero node dragging is performed. All geometry comes strictly from graph compiler output.
    """
    prof = get_frame_profile(profile or layout_graph.frame_profile_id)
    feasibility = evaluate_feasibility(layout_graph, profile=prof)

    soft_score: SoftLayoutScore | None = None
    if feasibility.feasible:
        soft_score = compute_soft_score(layout_graph, profile=prof, weights=weights)

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
) -> LayoutOptimizationResult:
    """Coordinate candidate generation, bounded Kiwi collision repair, and deterministic selection.

    Supported strategies:
    - CONCEPT_CARD (PRIMARY variant)
    - COMPARISON (PRIMARY [two-column], STACKED [two-row fallback])
    - IMAGE_TEXT (PRIMARY [side-by-side in 16:9, stacked in 9:16], STACKED [fallback in 16:9])
    - QUOTE (PRIMARY variant)

    Bounded repair loop:
    Runs up to max_solves (default 5) total solves per candidate variant.
    Separation constraints are added as required linear inequalities.

    Raises:
        LayoutInvalidInputError: If inputs are invalid
        LayoutUnsatisfiableError: If all candidate variants fail hard feasibility gates
    """
    strat = LayoutStrategy(strategy) if isinstance(strategy, str) else strategy
    prof = get_frame_profile(profile)

    # Determine ordered list of topological variants to attempt
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

    # Prepare measurements map for clipping check
    validated_items: list[LayoutItemInput] = []
    for it in items:
        if isinstance(it, LayoutItemInput):
            validated_items.append(it)
        elif isinstance(it, dict):
            validated_items.append(LayoutItemInput(**it))
        else:
            raise LayoutInvalidInputError(f"Expected LayoutItemInput or dict, got {type(it).__name__}")

    measurements = {it.node_id: (float(it.min_width), float(it.min_height)) for it in validated_items}

    candidates: list[LayoutCandidate] = []

    for variant in variants:
        candidate_id = f"{strat.value}_{variant}"
        accumulated_constraints: list[SeparationConstraint] = []
        solve_count = 0
        repair_count = 0
        last_graph: LayoutGraph | None = None

        # Bounded collision repair loop: at most max_solves total solves
        while solve_count < max_solves:
            try:
                last_graph = solve_layout(
                    scene_id=scene_id,
                    strategy=strat,
                    profile=prof,
                    items=validated_items,
                    metadata=metadata,
                    separation_constraints=accumulated_constraints,
                    variant=variant,
                )
                solve_count += 1
            except LayoutUnsatisfiableError:
                solve_count += 1
                break
            except Exception:
                solve_count += 1
                break

            # Pure box collision detection
            collisions = detect_box_collisions(last_graph)
            if not collisions:
                # Collision-free solve achieved!
                break

            # If budget exhausted, stop
            if solve_count >= max_solves:
                break

            # Choose deterministic separation constraints for colliding boxes
            box_map = {b.node_id: b for b in last_graph.boxes}
            new_constraints: list[SeparationConstraint] = []
            for col in collisions:
                sc = choose_separation_constraint(col, box_map, prof, strat)
                if sc not in accumulated_constraints:
                    new_constraints.append(sc)

            if not new_constraints:
                # No new constraint could be proposed
                break

            accumulated_constraints.extend(new_constraints)
            repair_count += 1

        # Evaluate feasibility of this candidate variant
        if last_graph is not None:
            feasibility = evaluate_feasibility(
                layout_graph=last_graph,
                profile=prof,
                measurements=measurements,
                expected_node_ids=[it.node_id for it in validated_items],
            )
            soft_score: SoftLayoutScore | None = None
            if feasibility.feasible:
                soft_score = compute_soft_score(last_graph, profile=prof, weights=weights)

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
        else:
            # Solver completely failed on this variant
            empty_feasibility = LayoutFeasibilityReport(
                overflow_count=1,
                fatal_overlap_count=0,
                clipping_count=0,
                safe_zone_violation_count=0,
                invalid_geometry_count=0,
                edge_node_intersection_count=0,
                minimum_readability_violation_count=0,
                feasible=False,
                violations=["Kiwi linear solver could not satisfy constraints"],
            )
            candidates.append(
                LayoutCandidate(
                    candidate_id=candidate_id,
                    strategy=strat,
                    variant=variant,
                    layout_graph=None,
                    feasibility=empty_feasibility,
                    soft_score=None,
                    solve_count=solve_count,
                    repair_count=repair_count,
                )
            )

    # Rank and select best feasible candidate
    selected = choose_best_candidate(candidates)

    return LayoutOptimizationResult(
        selected=selected,
        candidates=candidates,
        attempted_count=len(candidates),
    )
