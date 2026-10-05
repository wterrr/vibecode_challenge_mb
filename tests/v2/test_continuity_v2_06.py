"""V2-06 Cross-Scene Layout Continuity and Stability test suite."""

from __future__ import annotations

import math
import pytest
from pydantic import ValidationError

from learnflow_v2.core.errors import LayoutInvalidInputError, LayoutUnsatisfiableError
from learnflow_v2.layout.constraints import LayoutItemInput, solve_layout
from learnflow_v2.layout.continuity import (
    ContinuityAnchor,
    ContinuityConstraint,
    ContinuityContext,
    ContinuityMetrics,
    ContinuityStrength,
    build_continuity_context,
    compute_continuity_metrics,
    derive_stable_graph_order,
)
from learnflow_v2.layout.graph import GraphLayoutKind, LayoutDirection, layout_directed_graph
from learnflow_v2.layout.optimization import (
    LayoutCandidate,
    choose_best_candidate,
    optimize_simple_layout,
    repair_layout_collisions,
)
from learnflow_v2.layout.preflight import validate_graph_layout, validate_layout_graph
from learnflow_v2.layout.profiles import (
    create_frame_profile_16_9,
    create_frame_profile_9_16,
    get_frame_profile,
)
from learnflow_v2.layout.schema import (
    FrameProfile,
    GraphBackendKind,
    LayoutBox,
    LayoutGraph,
    LayoutStrategy,
    Rect,
)
from learnflow_v2.layout.score import (
    LayoutFeasibilityReport,
    SoftLayoutScore,
    SoftScoreWeights,
    compute_soft_score,
)
from learnflow_v2.scenegraph.enums import LayoutIntent, NodeKind, ReadingDirection, RelationKind
from learnflow_v2.scenegraph.schema import (
    LayoutIntentSpec,
    SceneGraph,
    SceneNode,
    SceneRelation,
)


def _make_sg(scene_id: str, nodes: list[tuple[str, str, str | None]], relations: list[tuple[str, str, str]] | None = None) -> SceneGraph:
    """Helper to create SceneGraph with (id, label, semantic_key)."""
    scene_nodes = [
        SceneNode(
            id=nid,
            kind=NodeKind.CONCEPT,
            label=lbl,
            semantic_key=skey,
            concept_ref=skey,
        )
        for nid, lbl, skey in nodes
    ]
    scene_rels = []
    if relations:
        for rid, src, tgt in relations:
            scene_rels.append(
                SceneRelation(id=rid, source=src, target=tgt, kind=RelationKind.SEQUENCE_BEFORE)
            )
    return SceneGraph(
        scene_id=scene_id,
        nodes=scene_nodes,
        relations=scene_rels,
        layout_intent=LayoutIntentSpec(type=LayoutIntent.CONCEPT_CARD),
    )


# =========================================================================
# Task 3: Continuity Identity is semantic_key, not node_id/label
# =========================================================================

def test_semantic_key_identity_match():
    # Previous: node_id=old_loss, semantic_key=training.loss
    prev_sg = _make_sg("s1", [("old_loss", "Old Loss Label", "training.loss")])
    prev_items = [LayoutItemInput(node_id="old_loss", role="content", semantic_key="training.loss", min_width=200.0, min_height=100.0)]
    prev_layout = solve_layout("s1", LayoutStrategy.CONCEPT_CARD, "16:9", prev_items)

    # Current: node_id=current_loss_card, semantic_key=training.loss
    curr_sg = _make_sg("s2", [("current_loss_card", "Different Label", "training.loss")])
    curr_items = [LayoutItemInput(node_id="current_loss_card", role="content", semantic_key="training.loss", min_width=200.0, min_height=100.0)]

    ctx = build_continuity_context(prev_sg, prev_layout, curr_sg, current_layout_items=curr_items)
    assert len(ctx.anchors) == 1
    anchor = ctx.anchors[0]
    assert anchor.semantic_key == "training.loss"
    assert anchor.previous_node_id == "old_loss"
    assert anchor.current_node_id == "current_loss_card"


def test_same_label_different_semantic_key_no_match():
    prev_sg = _make_sg("s1", [("node1", "Loss", "key.one")])
    prev_items = [LayoutItemInput(node_id="node1", role="content", semantic_key="key.one", min_width=200.0, min_height=100.0)]
    prev_layout = solve_layout("s1", LayoutStrategy.CONCEPT_CARD, "16:9", prev_items)

    curr_sg = _make_sg("s2", [("node2", "Loss", "key.two")])
    curr_items = [LayoutItemInput(node_id="node2", role="content", semantic_key="key.two", min_width=200.0, min_height=100.0)]

    ctx = build_continuity_context(prev_sg, prev_layout, curr_sg, current_layout_items=curr_items)
    assert len(ctx.anchors) == 0
    assert "key.two" in ctx.new_keys
    assert "key.one" in ctx.removed_keys


# =========================================================================
# Task 4 & 5: Strict Artifacts Validation & Serialization
# =========================================================================

def test_strict_continuity_artifacts_forbid_extra_and_types():
    with pytest.raises(ValidationError):
        # extra fields forbidden
        ContinuityAnchor(
            semantic_key="k",
            previous_node_id="p",
            current_node_id="c",
            previous_rect=Rect(x=0.0, y=0.0, width=10.0, height=10.0),
            previous_zone="CONTENT",
            normalized_center_x=0.5,
            normalized_center_y=0.5,
            extra_field=123,  # type: ignore
        )

    with pytest.raises(ValidationError):
        # string for float forbidden
        ContinuityAnchor(
            semantic_key="k",
            previous_node_id="p",
            current_node_id="c",
            previous_rect=Rect(x=0.0, y=0.0, width=10.0, height=10.0),
            previous_zone="CONTENT",
            normalized_center_x="0.5",  # type: ignore
            normalized_center_y=0.5,
        )

    with pytest.raises(ValidationError):
        # NaN forbidden
        ContinuityAnchor(
            semantic_key="k",
            previous_node_id="p",
            current_node_id="c",
            previous_rect=Rect(x=0.0, y=0.0, width=10.0, height=10.0),
            previous_zone="CONTENT",
            normalized_center_x=float("nan"),
            normalized_center_y=0.5,
        )

    # Immutable check
    anchor = ContinuityAnchor(
        semantic_key="k",
        previous_node_id="p",
        current_node_id="c",
        previous_rect=Rect(x=0.0, y=0.0, width=10.0, height=10.0),
        previous_zone="CONTENT",
        normalized_center_x=0.5,
        normalized_center_y=0.5,
    )
    with pytest.raises(ValidationError):
        anchor.semantic_key = "new_k"  # type: ignore


def test_deterministic_serialization_by_semantic_key():
    anchors = [
        ContinuityAnchor(
            semantic_key="zebra",
            previous_node_id="p_z",
            current_node_id="c_z",
            previous_rect=Rect(x=0.0, y=0.0, width=10.0, height=10.0),
            previous_zone="CONTENT",
            normalized_center_x=0.5,
            normalized_center_y=0.5,
            target_center_x=50.0,
            target_center_y=50.0,
        ),
        ContinuityAnchor(
            semantic_key="apple",
            previous_node_id="p_a",
            current_node_id="c_a",
            previous_rect=Rect(x=0.0, y=0.0, width=10.0, height=10.0),
            previous_zone="CONTENT",
            normalized_center_x=0.5,
            normalized_center_y=0.5,
            target_center_x=20.0,
            target_center_y=20.0,
        ),
    ]
    constraints = [
        ContinuityConstraint(node_id="c_z", semantic_key="zebra", target_center_x=50.0, target_center_y=50.0),
        ContinuityConstraint(node_id="c_a", semantic_key="apple", target_center_x=20.0, target_center_y=20.0),
    ]
    ctx = ContinuityContext(
        anchors=anchors,
        constraints=constraints,
        new_keys=["z_new", "a_new"],
        removed_keys=["z_rem", "a_rem"],
    )
    # Check that anchors are sorted by semantic_key
    assert [a.semantic_key for a in ctx.anchors] == ["apple", "zebra"]
    assert ctx.new_keys == ["a_new", "z_new"]
    assert ctx.removed_keys == ["a_rem", "z_rem"]


# =========================================================================
# Task 6: Normalized Previous Position & Profile Shifts
# =========================================================================

def test_normalized_position_across_profiles():
    # 16:9 to 9:16
    prev_prof = create_frame_profile_16_9()
    curr_prof = create_frame_profile_9_16()

    prev_sg = _make_sg("s1", [("n1", "Node 1", "key.1")])
    prev_items = [LayoutItemInput(node_id="n1", role="content", semantic_key="key.1", min_width=200.0, min_height=100.0)]
    prev_layout = solve_layout("s1", LayoutStrategy.CONCEPT_CARD, prev_prof, prev_items)

    curr_sg = _make_sg("s2", [("n1_v2", "Node 1", "key.1")])
    curr_items = [LayoutItemInput(node_id="n1_v2", role="content", semantic_key="key.1", min_width=200.0, min_height=100.0)]

    ctx = build_continuity_context(
        previous_scene_graph=prev_sg,
        previous_layout=prev_layout,
        current_scene_graph=curr_sg,
        previous_profile=prev_prof,
        current_profile=curr_prof,
        current_layout_items=curr_items,
    )

    assert len(ctx.constraints) == 1
    c = ctx.constraints[0]
    # Current content zone:
    curr_content = curr_prof.get_zone("CONTENT")
    assert curr_content.x <= c.target_center_x <= curr_content.right
    assert curr_content.y <= c.target_center_y <= curr_content.bottom


# =========================================================================
# Task 7: Role/Zone Hard Constraints Beat Continuity
# =========================================================================

def test_role_change_retains_identity_but_respects_new_zone():
    prev_sg = _make_sg("s1", [("loss", "Loss", "opt.loss")])
    prev_items = [LayoutItemInput(node_id="loss", role="content", semantic_key="opt.loss", min_width=200.0, min_height=100.0)]
    prev_layout = solve_layout("s1", LayoutStrategy.CONCEPT_CARD, "16:9", prev_items)

    # Current node has role='title'!
    curr_sg = _make_sg("s2", [("loss_title", "Loss Header", "opt.loss")])
    curr_items = [
        LayoutItemInput(node_id="loss_title", role="title", semantic_key="opt.loss", min_width=200.0, min_height=40.0),
        LayoutItemInput(node_id="other_content", role="content", semantic_key="opt.body", min_width=300.0, min_height=150.0),
    ]

    ctx = build_continuity_context(prev_sg, prev_layout, curr_sg, current_layout_items=curr_items)
    assert len(ctx.anchors) == 1
    assert ctx.anchors[0].semantic_key == "opt.loss"
    assert ctx.anchors[0].target_zone == "TITLE"

    # Solve with continuity
    opt_res = optimize_simple_layout(
        scene_id="s2",
        strategy=LayoutStrategy.CONCEPT_CARD,
        profile="16:9",
        items=curr_items,
        continuity=ctx,
    )

    assert opt_res.selected.feasibility.feasible
    box_map = {b.node_id: b for b in opt_res.selected.layout_graph.boxes}
    title_box = box_map["loss_title"]
    assert title_box.zone == "TITLE"
    prof = get_frame_profile("16:9")
    title_zone = prof.get_zone("TITLE")
    assert title_zone.contains_rect(title_box.rect, tol=1e-2)


# =========================================================================
# Task 8, 21, 22: Matching Rules, Ambiguous Keys, Removals, Missing Box
# =========================================================================

def test_matching_rules_ambiguous_and_removed():
    # Previous scene has 2 duplicate keys 'ambig' and one unique 'rem'
    prev_sg = _make_sg("s1", [
        ("p1", "P1", "ambig"),
        ("p2", "P2", "ambig"),
        ("p3", "P3", "rem"),
        ("p4", "P4", "kept"),
    ])
    prev_items = [
        LayoutItemInput(node_id="p1", role="content", semantic_key="ambig", min_width=100.0, min_height=50.0),
        LayoutItemInput(node_id="p2", role="content", semantic_key="ambig", min_width=100.0, min_height=50.0),
        LayoutItemInput(node_id="p3", role="content", semantic_key="rem", min_width=100.0, min_height=50.0),
        LayoutItemInput(node_id="p4", role="content", semantic_key="kept", min_width=100.0, min_height=50.0),
    ]
    prev_layout = solve_layout("s1", LayoutStrategy.CONCEPT_CARD, "16:9", prev_items)

    # Current scene has 'kept' and 'new_k' and 'ambig'
    curr_sg = _make_sg("s2", [
        ("c1", "C1", "kept"),
        ("c2", "C2", "new_k"),
        ("c3", "C3", "ambig"),
    ])
    curr_items = [
        LayoutItemInput(node_id="c1", role="content", semantic_key="kept", min_width=100.0, min_height=50.0),
        LayoutItemInput(node_id="c2", role="content", semantic_key="new_k", min_width=100.0, min_height=50.0),
        LayoutItemInput(node_id="c3", role="content", semantic_key="ambig", min_width=100.0, min_height=50.0),
    ]

    ctx = build_continuity_context(prev_sg, prev_layout, curr_sg, current_layout_items=curr_items)
    assert len(ctx.anchors) == 1
    assert ctx.anchors[0].semantic_key == "kept"
    assert "new_k" in ctx.new_keys
    assert "rem" in ctx.removed_keys
    assert "ambig" in ctx.ambiguous_keys


def test_missing_previous_layout_box_diagnostic():
    # If a node in prev_sg is somehow missing from prev_layout boxes:
    prev_sg = _make_sg("s1", [("missing_box_node", "M", "k.missing")])
    # prev_layout has empty boxes
    prev_layout = LayoutGraph(
        schema_version="2.1",
        scene_id="s1",
        frame_profile_id="16:9",
        frame_width=1920.0,
        frame_height=1080.0,
        boxes=[],
        strategy=LayoutStrategy.CONCEPT_CARD,
        feasible=True,
    )
    curr_sg = _make_sg("s2", [("curr_node", "M", "k.missing")])
    curr_items = [LayoutItemInput(node_id="curr_node", role="content", semantic_key="k.missing", min_width=100.0, min_height=50.0)]

    ctx = build_continuity_context(prev_sg, prev_layout, curr_sg, current_layout_items=curr_items)
    assert len(ctx.anchors) == 0
    assert any("missing from previous layout boxes" in d for d in ctx.diagnostics)


# =========================================================================
# Task 9: LayoutItemInput semantic_key validation
# =========================================================================

def test_layout_item_input_semantic_key_validation():
    item = LayoutItemInput(node_id="x", role="content", semantic_key=" valid.key ")
    assert item.semantic_key == "valid.key"

    with pytest.raises(ValidationError):
        LayoutItemInput(node_id="x", role="content", semantic_key="")

    with pytest.raises(ValidationError):
        LayoutItemInput(node_id="x", role="content", semantic_key=True)  # type: ignore


# =========================================================================
# Task 10, 11: Real Solver-Based Continuity (Kiwi Soft Constraints)
# =========================================================================

def test_real_kiwi_continuity_solve():
    prev_items = [
        LayoutItemInput(node_id="a", role="content", semantic_key="concept.a", min_width=200.0, min_height=100.0),
        LayoutItemInput(node_id="b", role="content", semantic_key="concept.b", min_width=200.0, min_height=100.0),
    ]
    prev_layout = solve_layout("s1", LayoutStrategy.COMPARISON, "16:9", prev_items)
    prev_sg = _make_sg("s1", [("a", "A", "concept.a"), ("b", "B", "concept.b")])

    curr_items = [
        LayoutItemInput(node_id="a_new", role="content", semantic_key="concept.a", min_width=200.0, min_height=100.0),
        LayoutItemInput(node_id="b_new", role="content", semantic_key="concept.b", min_width=200.0, min_height=100.0),
    ]
    curr_sg = _make_sg("s2", [("a_new", "A", "concept.a"), ("b_new", "B", "concept.b")])

    ctx = build_continuity_context(prev_sg, prev_layout, curr_sg, current_layout_items=curr_items)
    curr_layout = solve_layout(
        "s2",
        LayoutStrategy.COMPARISON,
        "16:9",
        curr_items,
        continuity_constraints=ctx.constraints,
    )
    assert curr_layout.feasible

    # Verify positions are very close to previous target positions
    box_map = {b.node_id: b for b in curr_layout.boxes}
    prev_map = {b.node_id: b for b in prev_layout.boxes}
    assert abs(box_map["a_new"].rect.center_x - prev_map["a"].rect.center_x) < 1.0
    assert abs(box_map["a_new"].rect.center_y - prev_map["a"].rect.center_y) < 1.0


# =========================================================================
# Task 12: Collision Repair Strictly Beats Continuity
# =========================================================================

def test_collision_repair_dominates_continuity():
    # In scene 1, nodes are small and side-by-side
    prev_items = [
        LayoutItemInput(node_id="n1", role="content", semantic_key="k1", min_width=100.0, min_height=100.0),
        LayoutItemInput(node_id="n2", role="content", semantic_key="k2", min_width=100.0, min_height=100.0),
    ]
    prev_layout = solve_layout("s1", LayoutStrategy.COMPARISON, "16:9", prev_items)
    prev_sg = _make_sg("s1", [("n1", "1", "k1"), ("n2", "2", "k2")])

    # In scene 2, nodes are much larger (e.g. width 450) such that their old centers would collide if forced
    curr_items = [
        LayoutItemInput(node_id="n1_lg", role="content", semantic_key="k1", min_width=450.0, min_height=150.0),
        LayoutItemInput(node_id="n2_lg", role="content", semantic_key="k2", min_width=450.0, min_height=150.0),
    ]
    curr_sg = _make_sg("s2", [("n1_lg", "1", "k1"), ("n2_lg", "2", "k2")])

    ctx = build_continuity_context(prev_sg, prev_layout, curr_sg, current_layout_items=curr_items)

    opt_res = optimize_simple_layout(
        scene_id="s2",
        strategy=LayoutStrategy.COMPARISON,
        profile="16:9",
        items=curr_items,
        continuity=ctx,
    )

    # Must be feasible and collision count == 0
    assert opt_res.selected.feasibility.feasible
    assert opt_res.selected.feasibility.fatal_overlap_count == 0


# =========================================================================
# Task 13, 14: ContinuityMetrics and Soft Scoring
# =========================================================================

def test_soft_score_and_weights_strict_validation():
    # Reject non-numeric / bool / inf
    with pytest.raises(ValidationError):
        SoftScoreWeights(continuity_weight=True)  # type: ignore

    with pytest.raises(ValidationError):
        SoftScoreWeights(continuity_weight=-1.0)

    with pytest.raises(ValidationError):
        SoftScoreWeights(continuity_weight=float("inf"))

    with pytest.raises(ValidationError):
        SoftLayoutScore(continuity_penalty=float("nan"))

    # Test score total consistency
    score = SoftLayoutScore(
        edge_penalty=1.0,
        typography_penalty=0.0,
        balance_penalty=2.0,
        continuity_penalty=3.0,
        whitespace_penalty=0.5,
    )
    assert abs(score.total - 6.5) < 1e-3


def test_no_previous_context_v2_05_parity():
    items = [
        LayoutItemInput(node_id="t", role="title", min_width=200.0, min_height=40.0),
        LayoutItemInput(node_id="c", role="content", min_width=300.0, min_height=100.0),
    ]
    opt_without = optimize_simple_layout("s1", LayoutStrategy.CONCEPT_CARD, "16:9", items)
    opt_with_none = optimize_simple_layout("s1", LayoutStrategy.CONCEPT_CARD, "16:9", items, continuity=None)

    assert opt_without.selected.soft_score.continuity_penalty == 0.0
    assert opt_with_none.selected.soft_score.continuity_penalty == 0.0
    assert opt_without.selected.soft_score.total == opt_with_none.selected.soft_score.total


# =========================================================================
# Task 17: Hard Feasibility Beats Continuity
# =========================================================================

def test_hard_feasibility_beats_continuity():
    # Infeasible candidate with 0 continuity penalty vs Feasible candidate with high continuity penalty
    bad_candidate = LayoutCandidate(
        candidate_id="bad",
        strategy=LayoutStrategy.CONCEPT_CARD,
        variant="PRIMARY",
        layout_graph=None,
        feasibility=LayoutFeasibilityReport(
            overflow_count=1,
            fatal_overlap_count=0,
            clipping_count=0,
            safe_zone_violation_count=0,
            invalid_geometry_count=0,
            edge_node_intersection_count=0,
            minimum_readability_violation_count=0,
            feasible=False,
            violations=["Overflow"],
        ),
        soft_score=None,
    )

    prof = get_frame_profile("16:9")
    good_graph = solve_layout(
        "s",
        LayoutStrategy.CONCEPT_CARD,
        prof,
        [
            LayoutItemInput(node_id="t", role="title", min_width=200.0, min_height=40.0),
            LayoutItemInput(node_id="c", role="content", min_width=300.0, min_height=100.0),
        ],
    )
    good_candidate = LayoutCandidate(
        candidate_id="good",
        strategy=LayoutStrategy.CONCEPT_CARD,
        variant="PRIMARY",
        layout_graph=good_graph,
        feasibility=LayoutFeasibilityReport(
            overflow_count=0,
            fatal_overlap_count=0,
            clipping_count=0,
            safe_zone_violation_count=0,
            invalid_geometry_count=0,
            edge_node_intersection_count=0,
            minimum_readability_violation_count=0,
            feasible=True,
            violations=[],
        ),
        soft_score=SoftLayoutScore(
            edge_penalty=0.0,
            typography_penalty=0.0,
            balance_penalty=1.0,
            continuity_penalty=50.0,
            whitespace_penalty=0.0,
            total=51.0,
        ),
    )

    winner = choose_best_candidate([bad_candidate, good_candidate])
    assert winner.candidate_id == "good"


# =========================================================================
# Task 18: Continuity Beats Small Aesthetic Differences
# =========================================================================

def test_continuity_beats_small_aesthetic_differences():
    prof = get_frame_profile("16:9")
    graph = solve_layout(
        "s",
        LayoutStrategy.CONCEPT_CARD,
        prof,
        [
            LayoutItemInput(node_id="t", role="title", min_width=200.0, min_height=40.0),
            LayoutItemInput(node_id="c", role="content", min_width=300.0, min_height=100.0),
        ],
    )
    # Candidate A: much lower displacement (continuity_penalty = 0.1), slightly worse balance (balance_penalty = 2.0)
    # Total = 2.1
    cand_a = LayoutCandidate(
        candidate_id="cand_a",
        strategy=LayoutStrategy.CONCEPT_CARD,
        variant="PRIMARY",
        layout_graph=graph,
        feasibility=LayoutFeasibilityReport(
            overflow_count=0,
            fatal_overlap_count=0,
            clipping_count=0,
            safe_zone_violation_count=0,
            invalid_geometry_count=0,
            edge_node_intersection_count=0,
            minimum_readability_violation_count=0,
            feasible=True,
            violations=[],
        ),
        soft_score=SoftLayoutScore(
            edge_penalty=0.0,
            typography_penalty=0.0,
            balance_penalty=2.0,
            continuity_penalty=0.1,
            whitespace_penalty=0.0,
            total=2.1,
        ),
    )

    # Candidate B: large displacement (continuity_penalty = 10.0), slightly better balance (balance_penalty = 1.0)
    # Total = 11.0
    cand_b = LayoutCandidate(
        candidate_id="cand_b",
        strategy=LayoutStrategy.CONCEPT_CARD,
        variant="PRIMARY",
        layout_graph=graph,
        feasibility=LayoutFeasibilityReport(
            overflow_count=0,
            fatal_overlap_count=0,
            clipping_count=0,
            safe_zone_violation_count=0,
            invalid_geometry_count=0,
            edge_node_intersection_count=0,
            minimum_readability_violation_count=0,
            feasible=True,
            violations=[],
        ),
        soft_score=SoftLayoutScore(
            edge_penalty=0.0,
            typography_penalty=0.0,
            balance_penalty=1.0,
            continuity_penalty=10.0,
            whitespace_penalty=0.0,
            total=11.0,
        ),
    )

    winner = choose_best_candidate([cand_b, cand_a])
    assert winner.candidate_id == "cand_a"


# =========================================================================
# Task 19, 20: Simple Layout Acceptance & New Concept Insertion
# =========================================================================

@pytest.mark.parametrize("strat", [
    LayoutStrategy.CONCEPT_CARD,
    LayoutStrategy.COMPARISON,
    LayoutStrategy.IMAGE_TEXT,
    LayoutStrategy.QUOTE,
])
def test_simple_layout_acceptance_persistent_concepts(strat: LayoutStrategy):
    prof = get_frame_profile("16:9")
    if strat == LayoutStrategy.IMAGE_TEXT:
        prev_items = [
            LayoutItemInput(node_id="media", role="media", semantic_key="s.media", min_width=300.0, min_height=200.0),
            LayoutItemInput(node_id="text", role="content", semantic_key="s.text", min_width=300.0, min_height=100.0),
        ]
        curr_items = [
            LayoutItemInput(node_id="media_2", role="media", semantic_key="s.media", min_width=320.0, min_height=200.0),
            LayoutItemInput(node_id="text_2", role="content", semantic_key="s.text", min_width=300.0, min_height=110.0),
        ]
    elif strat == LayoutStrategy.QUOTE:
        prev_items = [
            LayoutItemInput(node_id="quote", role="content", semantic_key="s.q", min_width=400.0, min_height=100.0),
            LayoutItemInput(node_id="attr", role="caption", semantic_key="s.attr", min_width=200.0, min_height=30.0),
        ]
        curr_items = [
            LayoutItemInput(node_id="quote_2", role="content", semantic_key="s.q", min_width=420.0, min_height=110.0),
            LayoutItemInput(node_id="attr_2", role="caption", semantic_key="s.attr", min_width=210.0, min_height=30.0),
        ]
    else:
        prev_items = [
            LayoutItemInput(node_id="c1", role="content", semantic_key="s.c1", min_width=250.0, min_height=120.0),
            LayoutItemInput(node_id="c2", role="content", semantic_key="s.c2", min_width=250.0, min_height=120.0),
        ]
        curr_items = [
            LayoutItemInput(node_id="c1_2", role="content", semantic_key="s.c1", min_width=260.0, min_height=120.0),
            LayoutItemInput(node_id="c2_2", role="content", semantic_key="s.c2", min_width=260.0, min_height=120.0),
        ]

    prev_sg = _make_sg("prev", [(it.node_id, it.node_id, it.semantic_key) for it in prev_items])
    curr_sg = _make_sg("curr", [(it.node_id, it.node_id, it.semantic_key) for it in curr_items])

    prev_layout = solve_layout("prev", strat, prof, prev_items)
    ctx = build_continuity_context(prev_sg, prev_layout, curr_sg, current_layout_items=curr_items)

    res_with_cont = optimize_simple_layout("curr", strat, prof, curr_items, continuity=ctx)
    res_without_cont = optimize_simple_layout("curr", strat, prof, curr_items, continuity=None)

    m_with = compute_continuity_metrics(ctx, res_with_cont.selected.layout_graph, prof)
    m_without = compute_continuity_metrics(ctx, res_without_cont.selected.layout_graph, prof)

    assert m_with.mean_displacement <= m_without.mean_displacement + 1e-3


def test_new_concept_insertion_a_new_b():
    # Previous: A B
    prev_items = [
        LayoutItemInput(node_id="a", role="content", semantic_key="key.a", min_width=200.0, min_height=100.0),
        LayoutItemInput(node_id="b", role="content", semantic_key="key.b", min_width=200.0, min_height=100.0),
    ]
    prev_layout = solve_layout("s1", LayoutStrategy.CONCEPT_CARD, "16:9", prev_items)
    prev_sg = _make_sg("s1", [("a", "A", "key.a"), ("b", "B", "key.b")])

    # Current: A NEW B
    curr_items = [
        LayoutItemInput(node_id="a_v2", role="content", semantic_key="key.a", min_width=200.0, min_height=100.0),
        LayoutItemInput(node_id="new_item", role="content", semantic_key="key.new", min_width=200.0, min_height=100.0),
        LayoutItemInput(node_id="b_v2", role="content", semantic_key="key.b", min_width=200.0, min_height=100.0),
    ]
    curr_sg = _make_sg("s2", [("a_v2", "A", "key.a"), ("new_item", "NEW", "key.new"), ("b_v2", "B", "key.b")])

    ctx = build_continuity_context(prev_sg, prev_layout, curr_sg, current_layout_items=curr_items)
    assert len(ctx.anchors) == 2
    assert "key.new" in ctx.new_keys

    opt_with = optimize_simple_layout("s2", LayoutStrategy.CONCEPT_CARD, "16:9", curr_items, continuity=ctx)
    opt_without = optimize_simple_layout("s2", LayoutStrategy.CONCEPT_CARD, "16:9", curr_items, continuity=None)

    m_with = compute_continuity_metrics(ctx, opt_with.selected.layout_graph)
    m_without = compute_continuity_metrics(ctx, opt_without.selected.layout_graph)

    assert m_with.mean_displacement <= m_without.mean_displacement + 1e-3


# =========================================================================
# Task 23, 24: Graph Stable Order & Node Renaming
# =========================================================================

def test_derive_stable_graph_order_and_renaming():
    # Previous: old_a (key=A), old_b (key=B)
    prev_sg = _make_sg("s1", [("old_a", "A", "concept.A"), ("old_b", "B", "concept.B")])
    prev_layout = LayoutGraph(
        schema_version="2.1",
        scene_id="s1",
        frame_profile_id="16:9",
        frame_width=1920.0,
        frame_height=1080.0,
        boxes=[
            LayoutBox(node_id="old_a", rect=Rect(x=100.0, y=100.0, width=150.0, height=80.0), zone="CONTENT", strategy_role="graph_node", semantic_key="concept.A"),
            LayoutBox(node_id="old_b", rect=Rect(x=400.0, y=100.0, width=150.0, height=80.0), zone="CONTENT", strategy_role="graph_node", semantic_key="concept.B"),
        ],
        strategy=LayoutStrategy.DIRECTED_GRAPH,
        feasible=True,
    )

    # Current: current_a (key=A), current_b (key=B)
    curr_sg = _make_sg("s2", [("current_b", "B", "concept.B"), ("current_a", "A", "concept.A")])

    order = derive_stable_graph_order(prev_sg, prev_layout, curr_sg, direction=LayoutDirection.RIGHT)
    # Even though curr_sg lists current_b first, stable order derived from previous x-coordinates must place current_a first!
    assert order == ["current_a", "current_b"]


# =========================================================================
# Task 25, 26: Real ELK Insertion and Branch Tests
# =========================================================================

def test_real_elk_insertion_chain():
    from learnflow_v2.layout.backends.elk import is_available
    assert is_available(), "elkjs must be installed and available"

    prof = create_frame_profile_16_9()
    measurements = {
        "node_a": {"width": 140.0, "height": 60.0},
        "node_b": {"width": 140.0, "height": 60.0},
        "node_c": {"width": 140.0, "height": 60.0},
        "node_new": {"width": 140.0, "height": 60.0},
    }

    # Previous: A -> B -> C
    prev_sg = _make_sg(
        "s1",
        [("node_a", "A", "key.A"), ("node_b", "B", "key.B"), ("node_c", "C", "key.C")],
        [("e1", "node_a", "node_b"), ("e2", "node_b", "node_c")],
    )
    prev_layout = layout_directed_graph(
        scene_graph=prev_sg,
        measurements=measurements,
        profile=prof,
        backend=GraphBackendKind.ELK,
        direction=LayoutDirection.RIGHT,
    )
    rep_prev = validate_graph_layout(prev_layout, prof)
    assert rep_prev.valid
    assert rep_prev.edge_node_intersection_count == 0

    # Current: A -> B -> NEW -> C
    curr_sg = _make_sg(
        "s2",
        [("node_a", "A", "key.A"), ("node_b", "B", "key.B"), ("node_new", "NEW", "key.NEW"), ("node_c", "C", "key.C")],
        [("e1", "node_a", "node_b"), ("e_new", "node_b", "node_new"), ("e2", "node_new", "node_c")],
    )

    curr_layout = layout_directed_graph(
        scene_graph=curr_sg,
        measurements=measurements,
        profile=prof,
        backend=GraphBackendKind.ELK,
        direction=LayoutDirection.RIGHT,
        previous_scene_graph=prev_sg,
        previous_layout=prev_layout,
    )

    rep_curr = validate_graph_layout(curr_layout, prof)
    assert rep_curr.valid
    assert rep_curr.edge_node_intersection_count == 0

    box_map = {b.node_id: b.rect for b in curr_layout.boxes}
    # Horizontal chain: A.x < B.x < NEW.x < C.x
    assert box_map["node_a"].right < box_map["node_b"].left
    assert box_map["node_b"].right < box_map["node_new"].left
    assert box_map["node_new"].right < box_map["node_c"].left


def test_real_elk_branch_insertion():
    from learnflow_v2.layout.backends.elk import is_available
    assert is_available(), "elkjs must be installed and available"

    prof = create_frame_profile_16_9()
    measurements = {
        "node_a": {"width": 120.0, "height": 60.0},
        "node_b": {"width": 120.0, "height": 60.0},
        "node_c": {"width": 120.0, "height": 60.0},
        "node_new": {"width": 120.0, "height": 60.0},
    }

    # Previous: A -> B, A -> C
    prev_sg = _make_sg(
        "s1",
        [("node_a", "A", "key.A"), ("node_b", "B", "key.B"), ("node_c", "C", "key.C")],
        [("e1", "node_a", "node_b"), ("e2", "node_a", "node_c")],
    )
    prev_layout = layout_directed_graph(
        scene_graph=prev_sg,
        measurements=measurements,
        profile=prof,
        backend=GraphBackendKind.ELK,
        direction=LayoutDirection.RIGHT,
    )
    rep_prev = validate_graph_layout(prev_layout, prof)
    assert rep_prev.valid

    # Current: A -> B, A -> NEW, A -> C
    curr_sg = _make_sg(
        "s2",
        [("node_a", "A", "key.A"), ("node_b", "B", "key.B"), ("node_new", "NEW", "key.NEW"), ("node_c", "C", "key.C")],
        [("e1", "node_a", "node_b"), ("e_new", "node_a", "node_new"), ("e2", "node_a", "node_c")],
    )

    curr_layout = layout_directed_graph(
        scene_graph=curr_sg,
        measurements=measurements,
        profile=prof,
        backend=GraphBackendKind.ELK,
        direction=LayoutDirection.RIGHT,
        previous_scene_graph=prev_sg,
        previous_layout=prev_layout,
    )

    rep_curr = validate_graph_layout(curr_layout, prof)
    assert rep_curr.valid
    assert rep_curr.edge_node_intersection_count == 0


# =========================================================================
# V2-06 Hardening Tests
# =========================================================================

def test_authoritative_role_zone_projection():
    """Verify continuity role->zone projection matches authoritative V2-03 semantics."""
    prev_prof = get_frame_profile("16:9")
    prev_items = [
        LayoutItemInput(node_id="p_t", role="title", semantic_key="k.title", min_width=200.0, min_height=40.0),
        LayoutItemInput(node_id="p_c", role="content", semantic_key="k.content", min_width=200.0, min_height=100.0),
    ]
    prev_layout = solve_layout("prev", LayoutStrategy.CONCEPT_CARD, prev_prof, prev_items)
    prev_sg = _make_sg("prev", [("p_t", "T", "k.title"), ("p_c", "C", "k.content")])

    # Check TITLE class: title, safe_title, header
    for role in ["title", "safe_title", "header"]:
        curr_sg = _make_sg("curr", [("c_t", "T", "k.title")])
        curr_items = [LayoutItemInput(node_id="c_t", role=role, semantic_key="k.title", min_width=200.0, min_height=40.0)]
        ctx = build_continuity_context(prev_sg, prev_layout, curr_sg, current_layout_items=curr_items)
        assert len(ctx.anchors) == 1
        assert ctx.anchors[0].target_zone == "TITLE", f"Role '{role}' projected to {ctx.anchors[0].target_zone}, expected TITLE"

    # Check CAPTION class: caption, safe_caption, subtitle
    for role in ["caption", "safe_caption", "subtitle"]:
        curr_sg = _make_sg("curr", [("c_t", "T", "k.title")])
        curr_items = [LayoutItemInput(node_id="c_t", role=role, semantic_key="k.title", min_width=200.0, min_height=30.0)]
        ctx = build_continuity_context(prev_sg, prev_layout, curr_sg, current_layout_items=curr_items)
        assert len(ctx.anchors) == 1
        assert ctx.anchors[0].target_zone == "CAPTION", f"Role '{role}' projected to {ctx.anchors[0].target_zone}, expected CAPTION"

    # Check CONTENT class: content, media, image, text, left, right, quote, attribution, author, headline
    content_roles = ["content", "media", "image", "text", "left", "right", "quote", "attribution", "author", "headline"]
    for role in content_roles:
        curr_sg = _make_sg("curr", [("c_c", "C", "k.content")])
        curr_items = [LayoutItemInput(node_id="c_c", role=role, semantic_key="k.content", min_width=200.0, min_height=80.0)]
        ctx = build_continuity_context(prev_sg, prev_layout, curr_sg, current_layout_items=curr_items)
        assert len(ctx.anchors) == 1
        assert ctx.anchors[0].target_zone == "CONTENT", f"Role '{role}' projected to {ctx.anchors[0].target_zone}, expected CONTENT"


def test_unknown_role_without_current_layout_items_diagnostic():
    """Do NOT invent role='content' when current role is unknown. Omit positional constraint with diagnostic."""
    prev_items = [LayoutItemInput(node_id="p", role="content", semantic_key="opt.loss", min_width=200.0, min_height=100.0)]
    prev_layout = solve_layout("prev", LayoutStrategy.CONCEPT_CARD, "16:9", prev_items)
    prev_sg = _make_sg("prev", [("p", "P", "opt.loss")])

    curr_sg = _make_sg("curr", [("c", "C", "opt.loss")])
    # Calling build_continuity_context without current_layout_items for simple layout
    ctx = build_continuity_context(prev_sg, prev_layout, curr_sg)

    # Positional anchor and constraint must be omitted because legal current zone is genuinely unknown
    assert len(ctx.anchors) == 0
    assert len(ctx.constraints) == 0
    assert any("legal current zone unknown without layout items" in d for d in ctx.diagnostics)


def test_validate_explicit_target_zone_using_shared_semantics():
    """Explicit target_zone must exist in profile and be compatible with role, else LAYOUT_INVALID_INPUT."""
    prev_items = [LayoutItemInput(node_id="p", role="content", semantic_key="k.data", min_width=200.0, min_height=100.0)]
    prev_layout = solve_layout("prev", LayoutStrategy.CONCEPT_CARD, "16:9", prev_items)
    prev_sg = _make_sg("prev", [("p", "P", "k.data")])
    curr_sg = _make_sg("curr", [("c", "C", "k.data")])

    # 1. Non-existent zone in profile
    with pytest.raises(LayoutInvalidInputError) as exc_info:
        curr_items = [LayoutItemInput(node_id="c", role="content", semantic_key="k.data", target_zone="NON_EXISTENT_ZONE")]
        build_continuity_context(prev_sg, prev_layout, curr_sg, current_layout_items=curr_items)
    assert exc_info.value.code == "LAYOUT_INVALID_INPUT"

    # 2. Incompatible role and target_zone (e.g. role='content' in target_zone='TITLE')
    with pytest.raises(LayoutInvalidInputError) as exc_info2:
        curr_items = [LayoutItemInput(node_id="c", role="content", semantic_key="k.data", target_zone="TITLE")]
        build_continuity_context(prev_sg, prev_layout, curr_sg, current_layout_items=curr_items)
    assert exc_info2.value.code == "LAYOUT_INVALID_INPUT"


def test_bound_normalized_continuity_coordinates():
    """ContinuityAnchor must strictly enforce normalized coordinates in [0.0, 1.0]."""
    rect = Rect(x=10.0, y=10.0, width=50.0, height=50.0)

    # Valid bounds: 0.0, 0.5, 1.0
    for val in [0.0, 0.5, 1.0, 0, 1]:
        anchor = ContinuityAnchor(
            semantic_key="k",
            previous_node_id="p",
            current_node_id="c",
            previous_rect=rect,
            previous_zone="CONTENT",
            normalized_center_x=float(val),
            normalized_center_y=float(val),
        )
        assert 0.0 <= anchor.normalized_center_x <= 1.0
        assert 0.0 <= anchor.normalized_center_y <= 1.0

    # Invalid bounds / types: reject
    invalid_vals = [-0.001, 1.001, -0.2, 1.2, True, False, "0.5", float("nan"), float("inf"), float("-inf")]
    for inv in invalid_vals:
        with pytest.raises(ValidationError):
            ContinuityAnchor(
                semantic_key="k",
                previous_node_id="p",
                current_node_id="c",
                previous_rect=rect,
                previous_zone="CONTENT",
                normalized_center_x=inv,  # type: ignore
                normalized_center_y=0.5,
            )
        with pytest.raises(ValidationError):
            ContinuityAnchor(
                semantic_key="k",
                previous_node_id="p",
                current_node_id="c",
                previous_rect=rect,
                previous_zone="CONTENT",
                normalized_center_x=0.5,
                normalized_center_y=inv,  # type: ignore
            )


def test_validate_previous_anchor_geometry():
    """Verify that previous box geometry is validated against frame and zone before creating anchor."""
    prof = get_frame_profile("16:9")
    prev_sg = _make_sg("prev", [("node_ok", "OK", "k.ok"), ("node_bad", "BAD", "k.bad")])
    curr_sg = _make_sg("curr", [("node_ok", "OK", "k.ok"), ("node_bad", "BAD", "k.bad")])
    curr_items = [
        LayoutItemInput(node_id="node_ok", role="content", semantic_key="k.ok", min_width=100.0, min_height=50.0),
        LayoutItemInput(node_id="node_bad", role="content", semantic_key="k.bad", min_width=100.0, min_height=50.0),
    ]

    # Box outside previous frame
    prev_layout = LayoutGraph(
        schema_version="2.1",
        scene_id="prev",
        frame_profile_id="16:9",
        frame_width=prof.width,
        frame_height=prof.height,
        boxes=[
            LayoutBox(node_id="node_ok", zone="CONTENT", rect=Rect(x=100.0, y=200.0, width=100.0, height=50.0)),
            LayoutBox(node_id="node_bad", zone="CONTENT", rect=Rect(x=prof.width + 100.0, y=200.0, width=100.0, height=50.0)),
        ],
        strategy=LayoutStrategy.CONCEPT_CARD,
        feasible=True,
    )

    ctx = build_continuity_context(prev_sg, prev_layout, curr_sg, current_layout_items=curr_items)
    assert len(ctx.anchors) == 1
    assert ctx.anchors[0].semantic_key == "k.ok"
    assert "k.bad" in ctx.invalid_previous_geometry_keys

    # Box outside declared zone (e.g. box placed in TITLE area but claims CONTENT zone)
    prev_layout_zone_mismatch = LayoutGraph(
        schema_version="2.1",
        scene_id="prev",
        frame_profile_id="16:9",
        frame_width=prof.width,
        frame_height=prof.height,
        boxes=[
            LayoutBox(node_id="node_ok", zone="CONTENT", rect=Rect(x=100.0, y=200.0, width=100.0, height=50.0)),
            LayoutBox(node_id="node_bad", zone="CONTENT", rect=Rect(x=100.0, y=40.0, width=100.0, height=40.0)),  # in TITLE y-range, not CONTENT
        ],
        strategy=LayoutStrategy.CONCEPT_CARD,
        feasible=True,
    )

    ctx2 = build_continuity_context(prev_sg, prev_layout_zone_mismatch, curr_sg, current_layout_items=curr_items)
    assert len(ctx2.anchors) == 1
    assert ctx2.anchors[0].semantic_key == "k.ok"
    assert "k.bad" in ctx2.invalid_previous_geometry_keys


def test_remove_silent_previous_zone_fallback():
    """If previous LayoutBox claims an unknown zone, do not fall back to SAFE_EDGE; skip anchor and record diagnostic."""
    prof = get_frame_profile("16:9")
    prev_sg = _make_sg("prev", [("node_1", "N1", "k.1")])
    curr_sg = _make_sg("curr", [("node_1", "N1", "k.1")])
    curr_items = [LayoutItemInput(node_id="node_1", role="content", semantic_key="k.1", min_width=100.0, min_height=50.0)]

    prev_layout = LayoutGraph(
        schema_version="2.1",
        scene_id="prev",
        frame_profile_id="16:9",
        frame_width=prof.width,
        frame_height=prof.height,
        boxes=[
            LayoutBox(node_id="node_1", zone="UNKNOWN_MYTHICAL_ZONE", rect=Rect(x=100.0, y=200.0, width=100.0, height=50.0)),
        ],
        strategy=LayoutStrategy.CONCEPT_CARD,
        feasible=True,
    )

    ctx = build_continuity_context(prev_sg, prev_layout, curr_sg, current_layout_items=curr_items)
    assert len(ctx.anchors) == 0
    assert len(ctx.constraints) == 0
    assert "k.1" in ctx.invalid_previous_geometry_keys
    assert any("references unknown previous zone" in d for d in ctx.diagnostics)


def test_graph_stable_order_input_list_order_invariance():
    """Verify input-list-order invariance: different SceneGraph list insertion order produces identical stable order."""
    prof = get_frame_profile("16:9")
    prev_sg_1 = _make_sg("s1", [("n1", "1", "k.1"), ("n2", "2", "k.2"), ("n3", "3", "k.3")])
    prev_sg_2 = _make_sg("s1", [("n3", "3", "k.3"), ("n1", "1", "k.1"), ("n2", "2", "k.2")])

    prev_layout = LayoutGraph(
        schema_version="2.1",
        scene_id="s1",
        frame_profile_id="16:9",
        frame_width=prof.width,
        frame_height=prof.height,
        boxes=[
            LayoutBox(node_id="n1", zone="CONTENT", rect=Rect(x=100.0, y=100.0, width=80.0, height=40.0)),
            LayoutBox(node_id="n2", zone="CONTENT", rect=Rect(x=300.0, y=100.0, width=80.0, height=40.0)),
            LayoutBox(node_id="n3", zone="CONTENT", rect=Rect(x=500.0, y=100.0, width=80.0, height=40.0)),
        ],
        strategy=LayoutStrategy.DIRECTED_GRAPH,
        feasible=True,
    )

    curr_sg_a = _make_sg("s2", [("c1", "1", "k.1"), ("c2", "2", "k.2"), ("c3", "3", "k.3")])
    curr_sg_b = _make_sg("s2", [("c3", "3", "k.3"), ("c2", "2", "k.2"), ("c1", "1", "k.1")])

    order_a = derive_stable_graph_order(prev_sg_1, prev_layout, curr_sg_a, direction=LayoutDirection.RIGHT)
    order_b = derive_stable_graph_order(prev_sg_2, prev_layout, curr_sg_b, direction=LayoutDirection.RIGHT)

    assert order_a == order_b == ["c1", "c2", "c3"]


def test_graph_stable_order_duplicate_key_ambiguity_both_sides():
    """Duplicate semantic keys on either side must be ambiguous and receive no persistent rank anchor."""
    prof = get_frame_profile("16:9")

    # 1. Duplicate in previous scene: [p1(dup), p2(dup), q(unique)]
    prev_sg_dup = _make_sg("s1", [("p1", "P1", "dup"), ("p2", "P2", "dup"), ("q", "Q", "unique")])
    prev_layout_1 = LayoutGraph(
        schema_version="2.1",
        scene_id="s1",
        frame_profile_id="16:9",
        frame_width=prof.width,
        frame_height=prof.height,
        boxes=[
            LayoutBox(node_id="p1", zone="CONTENT", rect=Rect(x=100.0, y=100.0, width=80.0, height=40.0)),
            LayoutBox(node_id="p2", zone="CONTENT", rect=Rect(x=500.0, y=100.0, width=80.0, height=40.0)),
            LayoutBox(node_id="q", zone="CONTENT", rect=Rect(x=300.0, y=100.0, width=80.0, height=40.0)),
        ],
        strategy=LayoutStrategy.DIRECTED_GRAPH,
        feasible=True,
    )

    curr_sg_1 = _make_sg("s2", [("cq", "Q", "unique"), ("cdup", "DUP", "dup")])
    curr_sg_2 = _make_sg("s2", [("cdup", "DUP", "dup"), ("cq", "Q", "unique")])

    order_1 = derive_stable_graph_order(prev_sg_dup, prev_layout_1, curr_sg_1, direction=LayoutDirection.RIGHT)
    order_2 = derive_stable_graph_order(prev_sg_dup, prev_layout_1, curr_sg_2, direction=LayoutDirection.RIGHT)

    # In both, cq gets persistent rank (x=300 -> rank 10.0), cdup is ambiguous (fallback rank 50.0).
    # Thus cq comes first regardless of list order!
    assert order_1 == order_2 == ["cq", "cdup"]

    # 2. Duplicate in current scene: current has two nodes with same semantic key
    prev_sg_clean = _make_sg("s1", [("p_a", "A", "key.A"), ("p_b", "B", "key.B")])
    prev_layout_2 = LayoutGraph(
        schema_version="2.1",
        scene_id="s1",
        frame_profile_id="16:9",
        frame_width=prof.width,
        frame_height=prof.height,
        boxes=[
            LayoutBox(node_id="p_a", zone="CONTENT", rect=Rect(x=400.0, y=100.0, width=80.0, height=40.0)),
            LayoutBox(node_id="p_b", zone="CONTENT", rect=Rect(x=100.0, y=100.0, width=80.0, height=40.0)),
        ],
        strategy=LayoutStrategy.DIRECTED_GRAPH,
        feasible=True,
    )
    # Current has two nodes with key.A (ambiguous!) and one with key.B (unique persistent)
    curr_sg_dup_current = _make_sg("s2", [("c_a1", "A1", "key.A"), ("c_a2", "A2", "key.A"), ("c_b", "B", "key.B")])
    order_curr_dup = derive_stable_graph_order(prev_sg_clean, prev_layout_2, curr_sg_dup_current, direction=LayoutDirection.RIGHT)

    # c_b is the only persistent match (rank 10.0), so c_b must come first!
    assert order_curr_dup[0] == "c_b"


def test_continuity_constraint_strength_contract():
    """ContinuityConstraint exposes bounded strength enum and rejects arbitrary raw numeric weight."""
    c = ContinuityConstraint(
        node_id="n",
        semantic_key="k",
        target_center_x=100.0,
        target_center_y=200.0,
        strength=ContinuityStrength.WEAK,
    )
    assert c.strength == ContinuityStrength.WEAK

    # Extra raw weight field is forbidden
    with pytest.raises(ValidationError):
        ContinuityConstraint(
            node_id="n",
            semantic_key="k",
            target_center_x=100.0,
            target_center_y=200.0,
            weight=999999999,  # type: ignore
        )


def test_continuity_context_consistency_rules():
    """ContinuityContext enforces uniqueness of anchor keys, constraint keys, constraint node IDs, and consistency with matched_keys."""
    rect = Rect(x=0.0, y=0.0, width=10.0, height=10.0)
    a1 = ContinuityAnchor(
        semantic_key="k1",
        previous_node_id="p1",
        current_node_id="c1",
        previous_rect=rect,
        previous_zone="CONTENT",
        normalized_center_x=0.5,
        normalized_center_y=0.5,
        target_center_x=10.0,
        target_center_y=10.0,
    )
    a2 = ContinuityAnchor(
        semantic_key="k2",
        previous_node_id="p2",
        current_node_id="c2",
        previous_rect=rect,
        previous_zone="CONTENT",
        normalized_center_x=0.5,
        normalized_center_y=0.5,
        target_center_x=20.0,
        target_center_y=20.0,
    )
    c1 = ContinuityConstraint(node_id="c1", semantic_key="k1", target_center_x=10.0, target_center_y=10.0)
    c2 = ContinuityConstraint(node_id="c2", semantic_key="k2", target_center_x=20.0, target_center_y=20.0)

    # Valid consistent context
    ctx = ContinuityContext(anchors=[a1, a2], constraints=[c1, c2])
    assert ctx.matched_keys == ["k1", "k2"]

    # Reject duplicate anchor keys
    with pytest.raises(ValidationError, match="anchor semantic keys must be unique"):
        ContinuityContext(anchors=[a1, a1], constraints=[c1])

    # Reject duplicate constraint keys
    with pytest.raises(ValidationError, match="constraint semantic keys must be unique"):
        ContinuityContext(anchors=[a1], constraints=[c1, ContinuityConstraint(node_id="c_other", semantic_key="k1", target_center_x=10.0, target_center_y=10.0)])

    # Reject duplicate constraint node IDs
    with pytest.raises(ValidationError, match="constraint node IDs must be unique"):
        ContinuityContext(anchors=[a1, a2], constraints=[c1, ContinuityConstraint(node_id="c1", semantic_key="k2", target_center_x=20.0, target_center_y=20.0)])

    # Reject inconsistent matched_keys
    with pytest.raises(ValidationError, match="matched_keys"):
        ContinuityContext(anchors=[a1], constraints=[c1], matched_keys=["different_key"])

    # Reject mismatched keys between anchors and constraints
    with pytest.raises(ValidationError, match="missing constraint for anchor keys"):
        ContinuityContext(anchors=[a1], constraints=[])

    with pytest.raises(ValidationError, match="extra constraint for unanchored keys"):
        ContinuityContext(anchors=[a1], constraints=[c1, c2])

    # Reject mismatched node IDs
    c1_wrong_node = ContinuityConstraint(node_id="wrong_node", semantic_key="k1", target_center_x=10.0, target_center_y=10.0)
    with pytest.raises(ValidationError, match="node_id mismatch"):
        ContinuityContext(anchors=[a1], constraints=[c1_wrong_node])

    # Reject mismatched target coordinates
    c1_wrong_target = ContinuityConstraint(node_id="c1", semantic_key="k1", target_center_x=999.0, target_center_y=999.0)
    with pytest.raises(ValidationError, match="target mismatch"):
        ContinuityContext(anchors=[a1], constraints=[c1_wrong_target])


# =========================================================================
# V2-06 Final Hardening: Dominance, Correctness, and Boundary Tests
# =========================================================================

def test_continuity_dominates_aesthetic_soft_constraints():
    """Continuity soft preference must dominate ordinary aesthetic centering."""
    prof = create_frame_profile_16_9()
    content_zone = prof.get_zone("CONTENT")

    # Item with min_width=200, min_height=100
    items = [
        LayoutItemInput(
            node_id="c1",
            role="content",
            semantic_key="concept.alpha",
            min_width=200.0,
            min_height=100.0,
        )
    ]

    # 1. Ordinary solve without continuity -> centers in CONTENT (x=640)
    ordinary_graph = solve_layout("scene_ord", LayoutStrategy.CONCEPT_CARD, prof, items)
    ord_box = next(b for b in ordinary_graph.boxes if b.node_id == "c1")
    assert abs(ord_box.rect.center_x - content_zone.center_x) < 1.0

    # 2. Target near the left side of CONTENT zone: x = content_zone.x + 150 = 64 + 150 = 214
    target_cx = round(content_zone.x + 150.0, 4)
    target_cy = round(content_zone.center_y, 4)

    anchor = ContinuityAnchor(
        semantic_key="concept.alpha",
        previous_node_id="p1",
        current_node_id="c1",
        previous_rect=Rect(x=content_zone.x + 50.0, y=content_zone.y + 50.0, width=200.0, height=100.0),
        previous_zone="CONTENT",
        normalized_center_x=0.15,
        normalized_center_y=0.5,
        target_center_x=target_cx,
        target_center_y=target_cy,
        target_zone="CONTENT",
    )
    constraint = ContinuityConstraint(
        node_id="c1",
        semantic_key="concept.alpha",
        target_center_x=target_cx,
        target_center_y=target_cy,
        strength=ContinuityStrength.CONTINUITY,
    )
    ctx = ContinuityContext(anchors=[anchor], constraints=[constraint])

    # 3. Solve with continuity
    cont_graph = solve_layout(
        "scene_cont",
        LayoutStrategy.CONCEPT_CARD,
        prof,
        items,
        continuity_constraints=ctx.constraints,
    )
    cont_box = next(b for b in cont_graph.boxes if b.node_id == "c1")

    # Verify continuity wins: cont_box stays near target_cx rather than centering at 640
    assert abs(cont_box.rect.center_x - target_cx) < 5.0
    assert abs(cont_box.rect.center_x - content_zone.center_x) > 300.0

    # Verify displacement difference is large and meaningful
    ord_metrics = compute_continuity_metrics(ctx, ordinary_graph, prof)
    cont_metrics = compute_continuity_metrics(ctx, cont_graph, prof)

    assert cont_metrics.mean_displacement < ord_metrics.mean_displacement - 0.2
    assert cont_metrics.mean_displacement < 0.05

    # Verify feasibility & containment
    assert cont_graph.feasible is True
    assert content_zone.contains_rect(cont_box.rect, tol=1e-2)


def test_hard_correctness_dominates_continuity():
    """Hard correctness (safe-zone containment, minimum gaps) must never yield to continuity."""
    prof = create_frame_profile_16_9()
    content_zone = prof.get_zone("CONTENT")

    # Item with min_width=200, min_height=100
    items = [
        LayoutItemInput(
            node_id="c1",
            role="content",
            semantic_key="concept.hard",
            min_width=200.0,
            min_height=100.0,
        )
    ]

    # Target is outside legal CONTENT: x = 10.0 (CONTENT starts at x=64)
    # Placing box at center_x = 10 would place left edge at 10 - 100 = -90 (outside screen!)
    illegal_target_cx = 10.0
    target_cy = content_zone.center_y

    anchor = ContinuityAnchor(
        semantic_key="concept.hard",
        previous_node_id="p1",
        current_node_id="c1",
        previous_rect=Rect(x=10.0, y=10.0, width=200.0, height=100.0),
        previous_zone="CONTENT",
        normalized_center_x=0.01,
        normalized_center_y=0.5,
        target_center_x=illegal_target_cx,
        target_center_y=target_cy,
        target_zone="CONTENT",
    )
    constraint = ContinuityConstraint(
        node_id="c1",
        semantic_key="concept.hard",
        target_center_x=illegal_target_cx,
        target_center_y=target_cy,
        strength=ContinuityStrength.CONTINUITY,
    )

    # Solve layout with illegal continuity target
    graph = solve_layout(
        "scene_hard",
        LayoutStrategy.CONCEPT_CARD,
        prof,
        items,
        continuity_constraints=[constraint],
    )

    # Hard correctness MUST WIN: box must be inside CONTENT zone
    box = next(b for b in graph.boxes if b.node_id == "c1")
    assert graph.feasible is True
    assert box.rect.x >= content_zone.x - 1e-2
    assert content_zone.contains_rect(box.rect, tol=1e-2)
    # Box cannot be at illegal target_cx = 10.0
    assert box.rect.center_x > content_zone.x + 90.0


def test_boundary_validation_rejects_stale_or_mismatched_continuity_constraints():
    """Boundary functions solve_layout and optimize_simple_layout reject stale or mismatched constraints."""
    prof = create_frame_profile_16_9()
    items = [
        LayoutItemInput(
            node_id="valid_node",
            role="content",
            semantic_key="key.valid",
            min_width=100.0,
            min_height=100.0,
        )
    ]

    # 1. Unknown node_id
    stale_constraint = ContinuityConstraint(
        node_id="unknown_node",
        semantic_key="key.valid",
        target_center_x=100.0,
        target_center_y=100.0,
    )
    with pytest.raises(LayoutInvalidInputError, match="references unknown node_id"):
        solve_layout("s1", LayoutStrategy.CONCEPT_CARD, prof, items, continuity_constraints=[stale_constraint])

    # 2. Semantic key mismatch
    mismatched_constraint = ContinuityConstraint(
        node_id="valid_node",
        semantic_key="key.different",
        target_center_x=100.0,
        target_center_y=100.0,
    )
    with pytest.raises(LayoutInvalidInputError, match="does not match item"):
        solve_layout("s1", LayoutStrategy.CONCEPT_CARD, prof, items, continuity_constraints=[mismatched_constraint])

    # 3. Same checks in optimize_simple_layout
    ctx_stale = ContinuityContext(
        anchors=[
            ContinuityAnchor(
                semantic_key="key.valid",
                previous_node_id="p1",
                current_node_id="unknown_node",
                previous_rect=Rect(x=0, y=0, width=10, height=10),
                previous_zone="CONTENT",
                normalized_center_x=0.5,
                normalized_center_y=0.5,
                target_center_x=100.0,
                target_center_y=100.0,
            )
        ],
        constraints=[stale_constraint],
    )
    with pytest.raises(LayoutInvalidInputError, match="references unknown node_id"):
        optimize_simple_layout("s1", LayoutStrategy.CONCEPT_CARD, prof, items, continuity=ctx_stale)


def test_compute_continuity_metrics_strict_error_handling():
    """compute_continuity_metrics raises LayoutInvalidInputError for missing boxes or missing zones."""
    prof = create_frame_profile_16_9()
    anchor = ContinuityAnchor(
        semantic_key="k1",
        previous_node_id="p1",
        current_node_id="missing_node",
        previous_rect=Rect(x=0, y=0, width=10, height=10),
        previous_zone="CONTENT",
        normalized_center_x=0.5,
        normalized_center_y=0.5,
        target_center_x=100.0,
        target_center_y=100.0,
        target_zone="CONTENT",
    )
    c1 = ContinuityConstraint(node_id="missing_node", semantic_key="k1", target_center_x=100.0, target_center_y=100.0)
    ctx = ContinuityContext(anchors=[anchor], constraints=[c1])

    # Missing node in layout
    layout = LayoutGraph(
        scene_id="s1",
        frame_profile_id="16:9",
        frame_width=1280.0,
        frame_height=720.0,
        strategy=LayoutStrategy.CONCEPT_CARD,
        boxes=[],
        feasible=True,
    )
    with pytest.raises(LayoutInvalidInputError, match="missing box for matched continuity anchor node"):
        compute_continuity_metrics(ctx, layout, prof)

    # Nonexistent target zone in profile
    anchor_bad_zone = ContinuityAnchor(
        semantic_key="k1",
        previous_node_id="p1",
        current_node_id="n1",
        previous_rect=Rect(x=0, y=0, width=10, height=10),
        previous_zone="CONTENT",
        normalized_center_x=0.5,
        normalized_center_y=0.5,
        target_center_x=100.0,
        target_center_y=100.0,
        target_zone="NON_EXISTENT_ZONE",
    )
    c1_bad = ContinuityConstraint(node_id="n1", semantic_key="k1", target_center_x=100.0, target_center_y=100.0)
    ctx_bad_zone = ContinuityContext(anchors=[anchor_bad_zone], constraints=[c1_bad])
    layout_with_box = LayoutGraph(
        scene_id="s1",
        frame_profile_id="16:9",
        frame_width=1280.0,
        frame_height=720.0,
        strategy=LayoutStrategy.CONCEPT_CARD,
        boxes=[LayoutBox(node_id="n1", rect=Rect(x=10, y=10, width=50, height=50), zone="CONTENT", strategy_role="content")],
        feasible=True,
    )
    with pytest.raises(LayoutInvalidInputError, match="Anchor target zone 'NON_EXISTENT_ZONE' does not exist"):
        compute_continuity_metrics(ctx_bad_zone, layout_with_box, prof)


# =========================================================================
# CP 2.6 Hardening: Graphviz Stable Ordering, Weak Strength & Displacement
# =========================================================================

def test_graphviz_backend_consumes_stable_continuity_ordering():
    """Graphviz layout consumes explicit stable ordering from continuity pipeline without ID sorting."""
    from learnflow_v2.scenegraph.schema import SceneGraph, SceneNode, SceneRelation, NodeKind, RelationKind
    from learnflow_v2.layout.schema import GraphBackendKind, Rect, LayoutStrategy
    from learnflow_v2.layout.profiles import create_frame_profile_16_9
    from learnflow_v2.layout.graph import layout_directed_graph

    prof = create_frame_profile_16_9()

    # Previous layout: 'alpha' was above 'beta' (y=200 vs y=400)
    prev_sg = SceneGraph(
        scene_id="s1",
        nodes=[
            SceneNode(id="root", kind=NodeKind.CONCEPT, concept_ref="concept.root", semantic_key="concept.root", label="Root"),
            SceneNode(id="n_alpha", kind=NodeKind.CONCEPT, concept_ref="concept.alpha", semantic_key="concept.alpha", label="Alpha"),
            SceneNode(id="n_beta", kind=NodeKind.CONCEPT, concept_ref="concept.beta", semantic_key="concept.beta", label="Beta"),
        ],
        relations=[
            SceneRelation(id="r1", source="root", target="n_alpha", kind=RelationKind.FLOW),
            SceneRelation(id="r2", source="root", target="n_beta", kind=RelationKind.FLOW),
        ],
    )
    prev_lg = LayoutGraph(
        scene_id="s1",
        frame_profile_id=prof.id,
        frame_width=prof.width,
        frame_height=prof.height,
        strategy=LayoutStrategy.DIRECTED_GRAPH,
        boxes=[
            LayoutBox(node_id="root", rect=Rect(x=200, y=300, width=120, height=60), zone="CONTENT", strategy_role="graph_node", semantic_key="concept.root"),
            LayoutBox(node_id="n_alpha", rect=Rect(x=500, y=200, width=120, height=60), zone="CONTENT", strategy_role="graph_node", semantic_key="concept.alpha"),
            LayoutBox(node_id="n_beta", rect=Rect(x=500, y=400, width=120, height=60), zone="CONTENT", strategy_role="graph_node", semantic_key="concept.beta"),
        ],
        feasible=True,
    )

    # Current scene: node IDs lexicographically inverted: 'z_alpha' vs 'a_beta'
    curr_sg = SceneGraph(
        scene_id="s2",
        nodes=[
            SceneNode(id="root", kind=NodeKind.CONCEPT, concept_ref="concept.root", semantic_key="concept.root", label="Root"),
            SceneNode(id="z_alpha", kind=NodeKind.CONCEPT, concept_ref="concept.alpha", semantic_key="concept.alpha", label="Alpha"),
            SceneNode(id="a_beta", kind=NodeKind.CONCEPT, concept_ref="concept.beta", semantic_key="concept.beta", label="Beta"),
        ],
        relations=[
            SceneRelation(id="r1", source="root", target="z_alpha", kind=RelationKind.FLOW),
            SceneRelation(id="r2", source="root", target="a_beta", kind=RelationKind.FLOW),
        ],
    )
    meas = {n.id: {"width": 120, "height": 60} for n in curr_sg.nodes}

    # With continuity: Graphviz respects stable continuity order, placing z_alpha above a_beta
    lg_cont = layout_directed_graph(
        curr_sg,
        meas,
        prof,
        backend=GraphBackendKind.GRAPHVIZ,
        strict_orthogonal=False,
        previous_scene_graph=prev_sg,
        previous_layout=prev_lg,
    )
    box_map_cont = {b.node_id: b.rect for b in lg_cont.boxes}
    assert box_map_cont["z_alpha"].y < box_map_cont["a_beta"].y, (
        f"Expected z_alpha (y={box_map_cont['z_alpha'].y}) to remain above a_beta (y={box_map_cont['a_beta'].y}) due to continuity"
    )

    # Without continuity: deterministic fallback sorts by node.id ('a_beta' < 'z_alpha'), putting a_beta on top
    lg_no_cont = layout_directed_graph(
        curr_sg,
        meas,
        prof,
        backend=GraphBackendKind.GRAPHVIZ,
        strict_orthogonal=False,
    )
    box_map_no_cont = {b.node_id: b.rect for b in lg_no_cont.boxes}
    assert box_map_no_cont["a_beta"].y < box_map_no_cont["z_alpha"].y, (
        "Without continuity, Graphviz must deterministically sort by node.id"
    )


def test_continuity_strength_weak_vs_normal_hierarchy():
    """ContinuityStrength.CONTINUITY and ContinuityStrength.WEAK are not equivalent when competing with soft constraints."""
    from learnflow_v2.layout.profiles import create_frame_profile_16_9
    from learnflow_v2.layout.constraints import LayoutItemInput, solve_layout
    from learnflow_v2.layout.continuity import ContinuityConstraint, ContinuityStrength

    prof = create_frame_profile_16_9()
    content_zone = prof.get_zone("CONTENT")
    items = [LayoutItemInput(node_id="c1", role="content", semantic_key="k1", min_width=200, min_height=100)]

    # Off-center target
    target_x = 214.0
    target_y = 360.0

    c_normal = ContinuityConstraint(
        node_id="c1",
        semantic_key="k1",
        target_center_x=target_x,
        target_center_y=target_y,
        strength=ContinuityStrength.CONTINUITY,
    )
    c_weak = ContinuityConstraint(
        node_id="c1",
        semantic_key="k1",
        target_center_x=target_x,
        target_center_y=target_y,
        strength=ContinuityStrength.WEAK,
    )

    # Solve with CONTINUITY
    g_normal = solve_layout("s1", LayoutStrategy.CONCEPT_CARD, prof, items, continuity_constraints=[c_normal])
    # Solve with WEAK
    g_weak = solve_layout("s2", LayoutStrategy.CONCEPT_CARD, prof, items, continuity_constraints=[c_weak])

    box_normal = next(b for b in g_normal.boxes if b.node_id == "c1")
    box_weak = next(b for b in g_weak.boxes if b.node_id == "c1")

    # CONTINUITY dominates aesthetic centering: lands at target_x (214.0)
    assert pytest.approx(box_normal.rect.center_x, abs=1.0) == target_x
    # WEAK yields to aesthetic centering (STRENGTH_STRONG): lands at content zone center_x (640.0)
    assert pytest.approx(box_weak.rect.center_x, abs=1.0) == content_zone.center_x

    # They are strictly not equivalent
    assert box_normal.rect.center_x != box_weak.rect.center_x


def test_continuity_strength_hierarchy_hard_beats_normal():
    """Hard constraints strictly dominate normal continuity constraints without infeasibility."""
    from learnflow_v2.layout.profiles import create_frame_profile_16_9
    from learnflow_v2.layout.constraints import LayoutItemInput, solve_layout
    from learnflow_v2.layout.continuity import ContinuityConstraint, ContinuityStrength

    prof = create_frame_profile_16_9()
    content_zone = prof.get_zone("CONTENT")
    items = [LayoutItemInput(node_id="c1", role="content", semantic_key="k1", min_width=200, min_height=100)]

    # Target placed outside the safe content zone (e.g. x = -500)
    c_impossible = ContinuityConstraint(
        node_id="c1",
        semantic_key="k1",
        target_center_x=-500.0,
        target_center_y=360.0,
        strength=ContinuityStrength.CONTINUITY,
    )
    res = solve_layout("s1", LayoutStrategy.CONCEPT_CARD, prof, items, continuity_constraints=[c_impossible])
    box = next(b for b in res.boxes if b.node_id == "c1")
    # Must remain within content zone despite strong continuity pull
    assert box.rect.x >= content_zone.left - 1e-4
    assert box.rect.right <= content_zone.right + 1e-4


def test_stable_scene_persistent_node_displacement_bounded():
    """In a stable scene, persistent nodes remain close to previous positions and displacement is minimized."""
    from learnflow_v2.layout.profiles import create_frame_profile_16_9
    from learnflow_v2.layout.constraints import LayoutItemInput, solve_layout
    from learnflow_v2.layout.continuity import (
        ContinuityConstraint,
        ContinuityAnchor,
        ContinuityContext,
        compute_continuity_metrics,
    )

    prof = create_frame_profile_16_9()
    items = [
        LayoutItemInput(node_id="col_left", role="left", semantic_key="k.col1", min_width=300, min_height=200),
        LayoutItemInput(node_id="col_right", role="right", semantic_key="k.col2", min_width=300, min_height=200),
    ]

    # Suppose previous layout had columns at specific positions
    prev_left_cx = 280.0
    prev_right_cx = 850.0
    prev_cy = 380.0

    anchors = [
        ContinuityAnchor(
            semantic_key="k.col1",
            previous_node_id="prev_col1",
            current_node_id="col_left",
            previous_rect=Rect(x=130, y=280, width=300, height=200),
            previous_zone="CONTENT",
            normalized_center_x=(prev_left_cx - prof.get_zone("CONTENT").left) / prof.get_zone("CONTENT").width,
            normalized_center_y=(prev_cy - prof.get_zone("CONTENT").top) / prof.get_zone("CONTENT").height,
            target_center_x=prev_left_cx,
            target_center_y=prev_cy,
            target_zone="CONTENT",
        ),
        ContinuityAnchor(
            semantic_key="k.col2",
            previous_node_id="prev_col2",
            current_node_id="col_right",
            previous_rect=Rect(x=700, y=280, width=300, height=200),
            previous_zone="CONTENT",
            normalized_center_x=(prev_right_cx - prof.get_zone("CONTENT").left) / prof.get_zone("CONTENT").width,
            normalized_center_y=(prev_cy - prof.get_zone("CONTENT").top) / prof.get_zone("CONTENT").height,
            target_center_x=prev_right_cx,
            target_center_y=prev_cy,
            target_zone="CONTENT",
        ),
    ]
    constraints = [
        ContinuityConstraint(node_id="col_left", semantic_key="k.col1", target_center_x=prev_left_cx, target_center_y=prev_cy),
        ContinuityConstraint(node_id="col_right", semantic_key="k.col2", target_center_x=prev_right_cx, target_center_y=prev_cy),
    ]
    ctx = ContinuityContext(anchors=anchors, constraints=constraints)

    layout_with_cont = solve_layout("s1", LayoutStrategy.COMPARISON, prof, items, continuity_constraints=constraints)
    layout_without_cont = solve_layout("s1", LayoutStrategy.COMPARISON, prof, items)

    metrics_with_cont = compute_continuity_metrics(ctx, layout_with_cont, prof)
    metrics_without_cont = compute_continuity_metrics(ctx, layout_without_cont, prof)

    # Continuity must reduce or equal displacement compared to no continuity
    assert metrics_with_cont.mean_displacement <= metrics_without_cont.mean_displacement
    assert metrics_with_cont.mean_displacement < 0.05


def test_incremental_insertion_avoids_global_reshuffle():
    """Inserting a new concept into an existing pipeline does not cause an unnecessary global reshuffle."""
    from learnflow_v2.scenegraph.schema import SceneGraph, SceneNode, SceneRelation, NodeKind, RelationKind
    from learnflow_v2.layout.schema import GraphBackendKind, Rect, LayoutStrategy
    from learnflow_v2.layout.profiles import create_frame_profile_16_9
    from learnflow_v2.layout.graph import layout_directed_graph
    from learnflow_v2.layout.continuity import derive_stable_graph_order

    prof = create_frame_profile_16_9()

    # Previous pipeline: A -> B -> C
    prev_sg = SceneGraph(
        scene_id="s1",
        nodes=[
            SceneNode(id="n_a", kind=NodeKind.CONCEPT, concept_ref="concept.a", semantic_key="concept.a", label="A"),
            SceneNode(id="n_b", kind=NodeKind.CONCEPT, concept_ref="concept.b", semantic_key="concept.b", label="B"),
            SceneNode(id="n_c", kind=NodeKind.CONCEPT, concept_ref="concept.c", semantic_key="concept.c", label="C"),
        ],
        relations=[
            SceneRelation(id="r1", source="n_a", target="n_b", kind=RelationKind.FLOW),
            SceneRelation(id="r2", source="n_b", target="n_c", kind=RelationKind.FLOW),
        ],
    )
    prev_lg = LayoutGraph(
        scene_id="s1",
        frame_profile_id=prof.id,
        frame_width=prof.width,
        frame_height=prof.height,
        strategy=LayoutStrategy.DIRECTED_GRAPH,
        boxes=[
            LayoutBox(node_id="n_a", rect=Rect(x=150, y=300, width=120, height=60), zone="CONTENT", strategy_role="graph_node", semantic_key="concept.a"),
            LayoutBox(node_id="n_b", rect=Rect(x=450, y=300, width=120, height=60), zone="CONTENT", strategy_role="graph_node", semantic_key="concept.b"),
            LayoutBox(node_id="n_c", rect=Rect(x=750, y=300, width=120, height=60), zone="CONTENT", strategy_role="graph_node", semantic_key="concept.c"),
        ],
        feasible=True,
    )

    # Current pipeline: A -> B -> NEW -> C
    # Node IDs intentionally permuted to verify node IDs do not control layout order
    curr_sg = SceneGraph(
        scene_id="s2",
        nodes=[
            SceneNode(id="id_c", kind=NodeKind.CONCEPT, concept_ref="concept.c", semantic_key="concept.c", label="C"),
            SceneNode(id="id_new", kind=NodeKind.CONCEPT, concept_ref="concept.new", semantic_key="concept.new", label="NEW"),
            SceneNode(id="id_b", kind=NodeKind.CONCEPT, concept_ref="concept.b", semantic_key="concept.b", label="B"),
            SceneNode(id="id_a", kind=NodeKind.CONCEPT, concept_ref="concept.a", semantic_key="concept.a", label="A"),
        ],
        relations=[
            SceneRelation(id="r1", source="id_a", target="id_b", kind=RelationKind.FLOW),
            SceneRelation(id="r2", source="id_b", target="id_new", kind=RelationKind.FLOW),
            SceneRelation(id="r3", source="id_new", target="id_c", kind=RelationKind.FLOW),
        ],
    )
    meas = {n.id: {"width": 120, "height": 60} for n in curr_sg.nodes}

    # Verify stable order derivation: A before B, NEW between B and C, C last
    stable_order = derive_stable_graph_order(prev_sg, prev_lg, curr_sg, "RIGHT")
    assert stable_order == ["id_a", "id_b", "id_new", "id_c"]

    # Execute graph layout with Graphviz
    lg_curr = layout_directed_graph(
        curr_sg,
        meas,
        prof,
        backend=GraphBackendKind.GRAPHVIZ,
        strict_orthogonal=False,
        previous_scene_graph=prev_sg,
        previous_layout=prev_lg,
    )

    box_map = {b.node_id: b.rect for b in lg_curr.boxes}
    # Monotonic left-to-right progression must be preserved
    assert box_map["id_a"].center_x < box_map["id_b"].center_x
    assert box_map["id_b"].center_x < box_map["id_new"].center_x
    assert box_map["id_new"].center_x < box_map["id_c"].center_x

    # Persistent concepts A and B remain on left/middle, C remains on right
    assert box_map["id_a"].center_x < 400.0
    assert box_map["id_c"].center_x > 700.0




