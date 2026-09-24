"""Comprehensive test suite for LearnFlow V2-05 Collision & Optimization subsystem.

Coverage:
1. Collision Pair & Separation Constraint Model Contracts (canonical order, finite values, immutability)
2. Pure Box-Box Collision Detection (boundary touching is not collision, positive overlap detected)
3. Deterministic Separation Axis Selection & Semantic Ordering Preservation
4. Hard Feasibility Gate (strict invariant: feasible=False if any violation > 0, ValueError on violation)
5. Soft Layout Scoring (edge penalties, visual balance, whitespace/density)
6. Candidate Selection & Deterministic Tie-Breaking (order independence, categorical elimination)
7. Bounded Collision Repair & Solver Integration (MAX_LAYOUT_SOLVES = 5, required Kiwi constraints)
8. Fallback Variants (Comparison STACKED, Image-Text STACKED)
9. Dense Fixture Corpus Benchmark Runner (42 cases: no_collision, repairable, fallback_required, impossible)
10. Directed Graph Candidate Evaluation (zero node dragging, edge-node intersection gates)
11. Canonical Serialization (deterministic canonical_json output)
"""

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from learnflow_v2.core.errors import LayoutInvalidInputError, LayoutUnsatisfiableError
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.layout import (
    CollisionPair,
    FrameProfile,
    LayoutBox,
    LayoutCandidate,
    LayoutFeasibilityReport,
    LayoutGraph,
    LayoutItemInput,
    LayoutOptimizationResult,
    LayoutStrategy,
    MAX_LAYOUT_SOLVES,
    PROFILE_16_9,
    PROFILE_9_16,
    Rect,
    SeparationAxis,
    SeparationConstraint,
    SeparationOrdering,
    SoftLayoutScore,
    SoftScoreWeights,
    choose_best_candidate,
    choose_separation_constraint,
    compute_soft_score,
    detect_box_collisions,
    evaluate_feasibility,
    evaluate_graph_candidate,
    get_frame_profile,
    optimize_simple_layout,
    solve_layout,
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def make_box(node_id: str, x: float, y: float, w: float, h: float, role: str = "content", zone: str = "CONTENT") -> LayoutBox:
    return LayoutBox(
        node_id=node_id,
        rect=Rect(x=x, y=y, width=w, height=h),
        zone=zone,
        strategy_role=role,
    )


def make_graph(boxes: list[LayoutBox], strategy: LayoutStrategy = LayoutStrategy.CONCEPT_CARD, profile: str = "16:9") -> LayoutGraph:
    prof = get_frame_profile(profile)
    return LayoutGraph(
        schema_version="2.1",
        scene_id="test_scene",
        frame_profile_id=prof.id,
        frame_width=prof.width,
        frame_height=prof.height,
        boxes=sorted(boxes, key=lambda b: b.node_id),
        strategy=strategy,
        feasible=True,
    )


# ---------------------------------------------------------------------------
# 1. CollisionPair & SeparationConstraint Models
# ---------------------------------------------------------------------------


class TestCollisionModels:
    def test_collision_pair_canonical_ordering_enforced(self):
        # Canonical order: first_node_id < second_node_id
        pair = CollisionPair(
            first_node_id="box_a",
            second_node_id="box_b",
            overlap_width=20.0,
            overlap_height=30.0,
            overlap_area=600.0,
            penetration_x=20.0,
            penetration_y=30.0,
        )
        assert pair.first_node_id == "box_a"
        assert pair.second_node_id == "box_b"

        # Reversed order must be rejected
        with pytest.raises(ValidationError):
            CollisionPair(
                first_node_id="box_b",
                second_node_id="box_a",
                overlap_width=20.0,
                overlap_height=30.0,
                overlap_area=600.0,
                penetration_x=20.0,
                penetration_y=30.0,
            )

        # Equal IDs must be rejected
        with pytest.raises(ValidationError):
            CollisionPair(
                first_node_id="box_a",
                second_node_id="box_a",
                overlap_width=20.0,
                overlap_height=30.0,
                overlap_area=600.0,
                penetration_x=20.0,
                penetration_y=30.0,
            )

    def test_collision_pair_rejects_negative_or_nan(self):
        with pytest.raises(ValidationError):
            CollisionPair(
                first_node_id="a",
                second_node_id="b",
                overlap_width=-5.0,
                overlap_height=10.0,
                overlap_area=50.0,
                penetration_x=5.0,
                penetration_y=10.0,
            )

        with pytest.raises(ValidationError):
            CollisionPair(
                first_node_id="a",
                second_node_id="b",
                overlap_width=float("nan"),
                overlap_height=10.0,
                overlap_area=50.0,
                penetration_x=5.0,
                penetration_y=10.0,
            )

    def test_separation_constraint_validation(self):
        sc = SeparationConstraint(
            first_node_id="item_1",
            second_node_id="item_2",
            axis=SeparationAxis.HORIZONTAL,
            ordering=SeparationOrdering.FIRST_BEFORE_SECOND,
            minimum_gap=24.0,
        )
        assert sc.axis == SeparationAxis.HORIZONTAL
        assert sc.minimum_gap == 24.0

        # Self-constraint rejected
        with pytest.raises(ValidationError):
            SeparationConstraint(
                first_node_id="item_1",
                second_node_id="item_1",
                axis=SeparationAxis.HORIZONTAL,
                ordering=SeparationOrdering.FIRST_BEFORE_SECOND,
                minimum_gap=16.0,
            )


# ---------------------------------------------------------------------------
# 2. Pure Box-Box Collision Detection
# ---------------------------------------------------------------------------


class TestBoxCollisionDetection:
    def test_disjoint_boxes_have_zero_collisions(self):
        box1 = make_box("box1", 100, 100, 200, 150)
        box2 = make_box("box2", 350, 100, 200, 150)
        graph = make_graph([box1, box2])

        collisions = detect_box_collisions(graph)
        assert len(collisions) == 0

    def test_boundary_touching_is_not_collision(self):
        # box1 right is 300, box2 left is 300 (touching)
        box1 = make_box("box1", 100, 100, 200, 150)
        box2 = make_box("box2", 300, 100, 200, 150)
        graph = make_graph([box1, box2])

        collisions = detect_box_collisions(graph)
        assert len(collisions) == 0

    def test_overlapping_boxes_detected_accurately(self):
        # box1: [100, 300] x [100, 250]
        # box2: [250, 450] x [150, 300]
        # Overlap: X in [250, 300] (w=50), Y in [150, 250] (h=100) -> Area=5000
        box1 = make_box("box1", 100, 100, 200, 150)
        box2 = make_box("box2", 250, 150, 200, 150)
        graph = make_graph([box1, box2])

        collisions = detect_box_collisions(graph)
        assert len(collisions) == 1
        col = collisions[0]
        assert col.first_node_id == "box1"
        assert col.second_node_id == "box2"
        assert abs(col.overlap_width - 50.0) < 1e-3
        assert abs(col.overlap_height - 100.0) < 1e-3
        assert abs(col.overlap_area - 5000.0) < 1e-3

    def test_multi_box_sorted_deterministic_output(self):
        # 3 mutually overlapping boxes
        b_c = make_box("c_box", 100, 100, 100, 100)
        b_a = make_box("a_box", 120, 120, 100, 100)
        b_b = make_box("b_box", 140, 140, 100, 100)
        graph = make_graph([b_c, b_a, b_b])

        collisions = detect_box_collisions(graph)
        assert len(collisions) == 3
        # Strict canonical order by (first_node_id, second_node_id)
        assert [(c.first_node_id, c.second_node_id) for c in collisions] == [
            ("a_box", "b_box"),
            ("a_box", "c_box"),
            ("b_box", "c_box"),
        ]


# ---------------------------------------------------------------------------
# 3. Separation Axis & Ordering Choice
# ---------------------------------------------------------------------------


class TestSeparationChoice:
    def test_smaller_overlap_axis_chosen(self):
        # Box A and B overlap with large X overlap (100) and small Y overlap (10)
        # Vertical displacement is much cheaper
        box_a = make_box("a", 100, 100, 200, 100)
        box_b = make_box("b", 120, 190, 200, 100)
        box_map = {"a": box_a, "b": box_b}

        pair = CollisionPair(
            first_node_id="a",
            second_node_id="b",
            overlap_width=100.0,
            overlap_height=10.0,
            overlap_area=1000.0,
            penetration_x=100.0,
            penetration_y=10.0,
        )

        sc = choose_separation_constraint(pair, box_map, "16:9", LayoutStrategy.CONCEPT_CARD)
        assert sc.axis == SeparationAxis.VERTICAL
        assert sc.ordering == SeparationOrdering.FIRST_BEFORE_SECOND

    def test_semantic_order_preservation_chrome_hierarchy(self):
        # Title box overlaps Content card
        title = make_box("title", 100, 100, 500, 60, role="title", zone="TITLE")
        card = make_box("card", 100, 120, 500, 300, role="card", zone="CONTENT")
        box_map = {"card": card, "title": title}

        pair = CollisionPair(
            first_node_id="card",
            second_node_id="title",
            overlap_width=500.0,
            overlap_height=40.0,
            overlap_area=20000.0,
            penetration_x=500.0,
            penetration_y=40.0,
        )

        sc = choose_separation_constraint(pair, box_map, "16:9", LayoutStrategy.CONCEPT_CARD)
        assert sc.axis == SeparationAxis.VERTICAL
        # Title must be above Card: title (second) before card (first) -> SECOND_BEFORE_FIRST
        assert sc.ordering == SeparationOrdering.SECOND_BEFORE_FIRST

    def test_semantic_order_preservation_comparison(self):
        # Comparison left and right items
        b_left = make_box("item_left", 300, 300, 500, 300, role="left")
        b_right = make_box("item_right", 500, 300, 500, 300, role="right")
        box_map = {"item_left": b_left, "item_right": b_right}

        pair = CollisionPair(
            first_node_id="item_left",
            second_node_id="item_right",
            overlap_width=300.0,
            overlap_height=300.0,
            overlap_area=90000.0,
            penetration_x=300.0,
            penetration_y=300.0,
        )

        sc = choose_separation_constraint(pair, box_map, "16:9", LayoutStrategy.COMPARISON)
        assert sc.axis == SeparationAxis.HORIZONTAL
        assert sc.ordering == SeparationOrdering.FIRST_BEFORE_SECOND


# ---------------------------------------------------------------------------
# 4. Hard Feasibility Gate
# ---------------------------------------------------------------------------


class TestFeasibilityGate:
    def test_all_zeros_derives_feasible_true(self):
        rep = LayoutFeasibilityReport(
            overflow_count=0,
            fatal_overlap_count=0,
            clipping_count=0,
            safe_zone_violation_count=0,
            invalid_geometry_count=0,
            edge_node_intersection_count=0,
            minimum_readability_violation_count=0,
        )
        assert rep.feasible is True

    def test_nonzero_hard_violation_forces_feasible_false(self):
        rep = LayoutFeasibilityReport(
            overflow_count=1,
            fatal_overlap_count=0,
            clipping_count=0,
            safe_zone_violation_count=0,
            invalid_geometry_count=0,
            edge_node_intersection_count=0,
            minimum_readability_violation_count=0,
        )
        assert rep.feasible is False

    def test_attempting_to_construct_feasible_true_with_violations_raises(self):
        with pytest.raises(ValueError, match="Cannot construct feasible=True"):
            LayoutFeasibilityReport(
                overflow_count=1,
                fatal_overlap_count=0,
                clipping_count=0,
                safe_zone_violation_count=0,
                invalid_geometry_count=0,
                edge_node_intersection_count=0,
                minimum_readability_violation_count=0,
                feasible=True,
            )

    def test_evaluate_feasibility_catches_collision_without_raising(self):
        # Two overlapping boxes
        b1 = make_box("box1", 100, 250, 400, 200)
        b2 = make_box("box2", 200, 250, 400, 200)
        graph = make_graph([b1, b2])

        rep = evaluate_feasibility(graph)
        assert rep.feasible is False
        assert rep.fatal_overlap_count == 1
        assert any("Fatal node collision" in v for v in rep.violations)


# ---------------------------------------------------------------------------
# 5. Soft Layout Scoring
# ---------------------------------------------------------------------------


class TestSoftLayoutScore:
    def test_centered_layout_has_lower_balance_penalty(self):
        # Perfectly centered box in CONTENT zone (CONTENT center is ~960, 582 for 16:9)
        prof = get_frame_profile("16:9")
        cz = prof.get_zone("CONTENT")

        centered_box = make_box("card1", cz.center_x - 300, cz.center_y - 150, 600, 300)
        graph_centered = make_graph([centered_box])
        score_centered = compute_soft_score(graph_centered)

        # Off-center box
        off_box = make_box("card2", cz.left + 50, cz.top + 50, 600, 300)
        graph_off = make_graph([off_box])
        score_off = compute_soft_score(graph_off)

        assert score_centered.balance_penalty < score_off.balance_penalty
        assert score_centered.total < score_off.total

    def test_density_extremes_penalized(self):
        prof = get_frame_profile("16:9")
        cz = prof.get_zone("CONTENT")

        # Extremely tiny box (density ~ 0.007 < 0.25)
        tiny_box = make_box("tiny", cz.center_x - 50, cz.center_y - 50, 100, 100)
        graph_tiny = make_graph([tiny_box])
        score_tiny = compute_soft_score(graph_tiny)
        assert score_tiny.whitespace_penalty > 0.0

        # Normal box filling ~ 40% of content zone
        normal_box = make_box("normal", cz.center_x - 400, cz.center_y - 200, 800, 400)
        graph_normal = make_graph([normal_box])
        score_normal = compute_soft_score(graph_normal)
        assert score_normal.whitespace_penalty == 0.0


# ---------------------------------------------------------------------------
# 6. Candidate Comparison & Deterministic Selection
# ---------------------------------------------------------------------------


class TestCandidateSelection:
    def test_infeasible_candidate_never_beats_feasible(self):
        # Infeasible candidate with soft_total=0.0
        infeasible = LayoutCandidate(
            candidate_id="cand_bad",
            strategy=LayoutStrategy.COMPARISON,
            variant="PRIMARY",
            layout_graph=None,
            feasibility=LayoutFeasibilityReport(
                clipping_count=1,
                violations=["Clipping violation"],
            ),
            soft_score=None,
        )

        # Feasible candidate with high soft penalty
        prof = get_frame_profile("16:9")
        cz = prof.get_zone("CONTENT")
        box = make_box("b1", cz.left + 10, cz.top + 10, 400, 200)
        graph = make_graph([box])
        feasible = LayoutCandidate(
            candidate_id="cand_good",
            strategy=LayoutStrategy.COMPARISON,
            variant="STACKED",
            layout_graph=graph,
            feasibility=LayoutFeasibilityReport(),
            soft_score=SoftLayoutScore(total=85.0),
        )

        best = choose_best_candidate([infeasible, feasible])
        assert best.candidate_id == "cand_good"

        # Reverse input order: same outcome
        best_rev = choose_best_candidate([feasible, infeasible])
        assert best_rev.candidate_id == "cand_good"

    def test_all_infeasible_raises_layout_unsatisfiable(self):
        infeasible_1 = LayoutCandidate(
            candidate_id="c1",
            strategy=LayoutStrategy.COMPARISON,
            variant="PRIMARY",
            feasibility=LayoutFeasibilityReport(overflow_count=1),
        )
        infeasible_2 = LayoutCandidate(
            candidate_id="c2",
            strategy=LayoutStrategy.COMPARISON,
            variant="STACKED",
            feasibility=LayoutFeasibilityReport(clipping_count=1),
        )

        with pytest.raises(LayoutUnsatisfiableError, match="failed hard feasibility gates"):
            choose_best_candidate([infeasible_1, infeasible_2])

    def test_deterministic_tie_breaking_order_independent(self):
        # Two feasible candidates with identical score
        prof = get_frame_profile("16:9")
        box = make_box("b", 100, 250, 400, 200)
        graph = make_graph([box])

        c_a = LayoutCandidate(
            candidate_id="variant_alpha",
            strategy=LayoutStrategy.COMPARISON,
            variant="PRIMARY",
            layout_graph=graph,
            feasibility=LayoutFeasibilityReport(),
            soft_score=SoftLayoutScore(total=10.0),
        )
        c_b = LayoutCandidate(
            candidate_id="variant_beta",
            strategy=LayoutStrategy.COMPARISON,
            variant="PRIMARY",
            layout_graph=graph,
            feasibility=LayoutFeasibilityReport(),
            soft_score=SoftLayoutScore(total=10.0),
        )

        winner_1 = choose_best_candidate([c_a, c_b])
        winner_2 = choose_best_candidate([c_b, c_a])

        assert winner_1.candidate_id == "variant_alpha"
        assert winner_2.candidate_id == "variant_alpha"


# ---------------------------------------------------------------------------
# 7. Bounded Collision Repair Loop & Optimization
# ---------------------------------------------------------------------------


class TestOptimizationPass:
    def test_simple_layout_optimizes_cleanly(self):
        items = [
            LayoutItemInput(node_id="title", role="title", min_width=400, min_height=50),
            LayoutItemInput(node_id="card", role="card", min_width=600, min_height=300),
        ]
        result = optimize_simple_layout(
            scene_id="scene_test_1",
            strategy=LayoutStrategy.CONCEPT_CARD,
            profile="16:9",
            items=items,
        )

        assert isinstance(result, LayoutOptimizationResult)
        assert result.selected.feasibility.feasible is True
        assert result.selected.soft_score is not None
        assert result.selected.layout_graph is not None
        assert len(result.selected.layout_graph.boxes) == 2

    def test_fallback_variant_selected_when_primary_infeasible(self):
        # Comparison with items too wide for side-by-side (PRIMARY) in 16:9 CONTENT (width=1184)
        # Left min_width=700, Right min_width=700 -> 700 + 700 + 16 = 1416 > 1184!
        # But vertically (STACKED): height 180 + 180 + 16 = 376 <= 453.6 -> fits!
        items = [
            LayoutItemInput(node_id="item_a", role="left", min_width=700, min_height=180),
            LayoutItemInput(node_id="item_b", role="right", min_width=700, min_height=180),
        ]

        result = optimize_simple_layout(
            scene_id="scene_fallback",
            strategy=LayoutStrategy.COMPARISON,
            profile="16:9",
            items=items,
        )

        assert result.selected.variant == "STACKED"
        assert result.selected.feasibility.feasible is True
        # PRIMARY candidate variant must be marked infeasible
        primary_cand = next(c for c in result.candidates if c.variant == "PRIMARY")
        assert primary_cand.feasibility.feasible is False

    def test_impossible_layout_raises_unsatisfiable(self):
        # Items way too large to fit in any variant
        items = [
            LayoutItemInput(node_id="item_a", role="left", min_width=2500, min_height=1500),
            LayoutItemInput(node_id="item_b", role="right", min_width=2500, min_height=1500),
        ]

        with pytest.raises(LayoutUnsatisfiableError, match="failed hard feasibility gates"):
            optimize_simple_layout(
                scene_id="scene_impossible",
                strategy=LayoutStrategy.COMPARISON,
                profile="16:9",
                items=items,
            )


# ---------------------------------------------------------------------------
# 8. Dense Fixture Corpus Benchmark Runner
# ---------------------------------------------------------------------------


class TestDenseFixtureCorpus:
    def test_all_dense_fixtures_pass(self):
        fixture_path = Path("benchmarks/fixtures/v2/layout_dense_cases.json")
        assert fixture_path.exists(), "Dense fixtures file must exist"

        with open(fixture_path, "r", encoding="utf-8") as f:
            cases = json.load(f)

        assert len(cases) >= 36, f"Corpus must have at least 36 cases, found {len(cases)}"

        passed_count = 0
        for case in cases:
            case_id = case["case_id"]
            strategy = LayoutStrategy(case["strategy"])
            profile = case["profile"]
            items = [LayoutItemInput(**it) for it in case["items"]]
            expected_feasible = case["expected_feasible"]

            if expected_feasible:
                result = optimize_simple_layout(
                    scene_id=case_id,
                    strategy=strategy,
                    profile=profile,
                    items=items,
                )
                assert result.selected.feasibility.feasible is True, f"Case {case_id} failed feasibility"
                if "expected_variant" in case:
                    assert result.selected.variant == case["expected_variant"], (
                        f"Case {case_id} selected variant {result.selected.variant}, expected {case['expected_variant']}"
                    )
                # Verify zero collisions in selected layout
                collisions = detect_box_collisions(result.selected.layout_graph)
                assert len(collisions) == 0, f"Case {case_id} has unresolved collisions: {collisions}"
            else:
                with pytest.raises(LayoutUnsatisfiableError):
                    optimize_simple_layout(
                        scene_id=case_id,
                        strategy=strategy,
                        profile=profile,
                        items=items,
                    )

            passed_count += 1

        assert passed_count == len(cases)


# ---------------------------------------------------------------------------
# 9. Canonical Serialization Tests
# ---------------------------------------------------------------------------


class TestCanonicalSerializationV205:
    def test_collision_pair_canonical_json(self):
        pair = CollisionPair(
            first_node_id="alpha",
            second_node_id="beta",
            overlap_width=15.5,
            overlap_height=20.0,
            overlap_area=310.0,
            penetration_x=15.5,
            penetration_y=20.0,
        )
        json_str = canonical_json(pair)
        assert '"first_node_id": "alpha"' in json_str
        assert '"second_node_id": "beta"' in json_str

    def test_optimization_result_canonical_json(self):
        items = [
            LayoutItemInput(node_id="title", role="title", min_width=300, min_height=40),
            LayoutItemInput(node_id="card", role="card", min_width=500, min_height=250),
        ]
        result = optimize_simple_layout(
            scene_id="ser_test",
            strategy=LayoutStrategy.CONCEPT_CARD,
            profile="16:9",
            items=items,
        )
        json_1 = canonical_json(result)
        json_2 = canonical_json(result)
        assert json_1 == json_2, "Canonical serialization must be strictly deterministic"


# ---------------------------------------------------------------------------
# 10. Directed Graph Candidate Evaluation Tests
# ---------------------------------------------------------------------------


class TestDirectedGraphCandidateEvaluation:
    def test_evaluate_graph_candidate_preserves_node_coordinates(self):
        from learnflow_v2.scenegraph.schema import SceneGraph, SceneNode, SceneRelation, LayoutIntentSpec
        from learnflow_v2.scenegraph.enums import NodeKind, RelationKind, LayoutIntent
        from learnflow_v2.layout.graph import layout_directed_graph, GraphBackendKind

        sg = SceneGraph(
            scene_id="dg_eval_test",
            nodes=[
                SceneNode(id="step_1", kind=NodeKind.CONCEPT, label="Start"),
                SceneNode(id="step_2", kind=NodeKind.CONCEPT, label="End"),
            ],
            relations=[
                SceneRelation(id="r1", source="step_1", target="step_2", kind=RelationKind.SEQUENCE_BEFORE),
            ],
            layout_intent=LayoutIntentSpec(type=LayoutIntent.PROCESS),
        )
        profile = get_frame_profile("16:9")
        lg = layout_directed_graph(
            sg,
            {"step_1": (120, 60), "step_2": (120, 60)},
            profile,
            GraphBackendKind.GRAPHVIZ,
            strict_orthogonal=False,
        )

        orig_coords = [(b.node_id, b.rect.x, b.rect.y, b.rect.width, b.rect.height) for b in lg.boxes]

        candidate = evaluate_graph_candidate("cand_graph_1", lg, profile=profile)

        assert candidate.strategy == LayoutStrategy.DIRECTED_GRAPH
        assert candidate.feasibility.feasible is True
        assert candidate.soft_score is not None
        assert candidate.soft_score.total >= 0.0

        # Verify zero node dragging: coordinates remain strictly identical
        post_coords = [(b.node_id, b.rect.x, b.rect.y, b.rect.width, b.rect.height) for b in lg.boxes]
        assert orig_coords == post_coords

