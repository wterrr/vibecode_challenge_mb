"""Comprehensive tests for LearnFlow V2-03 constraint layout subsystem.

Tests cover:
1. Frame Profiles (16:9, 9:16, safe insets, zone containment, non-overlap, determinism)
2. Schema & Rect validation (finite, positive, bounds, computed properties, immutability)
3. Kiwisolver Backend (real solver, required vs soft, unsat mapping)
4. Concept Card Strategy (16:9, 9:16, centering, protected zones, Vietnamese content)
5. Comparison Strategy (non-overlap, gutter, symmetry around center, equal width preference, unsat)
6. Image + Text Strategy (16:9 side-by-side, 9:16 stacked, aspect ratio, unsat)
7. Quote Strategy (centering, bounded max width, attribution below, unsat)
8. Title/Content/Caption separation
9. Preflight Validator (zero clipping, bounds, non-overlap, preflight failed errors)
10. Fixture Corpus validation (valid cases pass, invalid cases raise LAYOUT_UNSATISFIABLE)
11. Canonical Serialization (determinism, order independence, distinctness)
"""

import json
import math
from pathlib import Path
import pytest
from pydantic import ValidationError

import kiwisolver

from learnflow_v2.core.errors import (
    LayoutInvalidInputError,
    LayoutPreflightFailedError,
    LayoutUnsatisfiableError,
)
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.layout import (
    FrameInsets,
    FrameProfile,
    GridSpec,
    LayoutBox,
    LayoutGraph,
    LayoutItemInput,
    LayoutStrategy,
    LayoutZone,
    PROFILE_16_9,
    PROFILE_9_16,
    Rect,
    create_frame_profile_16_9,
    create_frame_profile_9_16,
    get_frame_profile,
    measure_text,
    solve_layout,
    validate_layout_graph,
)
from learnflow_v2.layout.backends.kiwi import (
    KiwiLayoutSolver,
    STRENGTH_MEDIUM,
    STRENGTH_REQUIRED,
    STRENGTH_STRONG,
    STRENGTH_WEAK,
)


# ---------------------------------------------------------------------------
# 1. Schema & Rect Contract Tests
# ---------------------------------------------------------------------------


def test_rect_contract_valid():
    r = Rect(x=10.0, y=20.0, width=100.0, height=50.0)
    assert r.left == 10.0
    assert r.top == 20.0
    assert r.right == 110.0
    assert r.bottom == 70.0
    assert r.center_x == 60.0
    assert r.center_y == 45.0
    assert r.contains_point(50.0, 30.0)
    assert not r.contains_point(5.0, 30.0)


def test_rect_rejection_of_invalid_values():
    # Negative coordinates
    with pytest.raises(ValidationError):
        Rect(x=-5.0, y=0.0, width=10.0, height=10.0)

    with pytest.raises(ValidationError):
        Rect(x=0.0, y=-5.0, width=10.0, height=10.0)

    # Zero or negative sizes
    with pytest.raises(ValidationError):
        Rect(x=0.0, y=0.0, width=0.0, height=10.0)

    with pytest.raises(ValidationError):
        Rect(x=0.0, y=0.0, width=10.0, height=-10.0)

    # NaN and Infinity
    with pytest.raises(ValidationError):
        Rect(x=float("nan"), y=0.0, width=10.0, height=10.0)

    with pytest.raises(ValidationError):
        Rect(x=0.0, y=0.0, width=float("inf"), height=10.0)


def test_rect_immutability():
    r = Rect(x=10.0, y=20.0, width=100.0, height=50.0)
    with pytest.raises(ValidationError):
        r.x = 20.0


# ---------------------------------------------------------------------------
# 2. Frame Profile Tests
# ---------------------------------------------------------------------------


def test_frame_profile_16_9_dimensions_and_zones():
    p = create_frame_profile_16_9(1280.0, 720.0)
    assert p.width == 1280.0
    assert p.height == 720.0
    assert p.aspect_ratio == "16:9"

    safe = p.safe_edge_rect
    assert safe.left == 64.0
    assert safe.top == 36.0
    assert safe.right == 1216.0
    assert safe.bottom == 684.0

    title = p.get_zone("TITLE")
    content = p.get_zone("CONTENT")
    caption = p.get_zone("CAPTION")

    # All zones inside safe edge
    assert safe.contains_rect(title)
    assert safe.contains_rect(content)
    assert safe.contains_rect(caption)

    # Zones are strictly positive and finite
    for z in [title, content, caption]:
        assert z.width > 0
        assert z.height > 0
        assert math.isfinite(z.x) and math.isfinite(z.y)

    # Title is above content, content is above caption (non-overlapping)
    assert title.bottom <= content.top
    assert content.bottom <= caption.top


def test_frame_profile_9_16_dimensions_and_zones():
    p = create_frame_profile_9_16(720.0, 1280.0)
    assert p.width == 720.0
    assert p.height == 1280.0
    assert p.aspect_ratio == "9:16"

    safe = p.safe_edge_rect
    assert safe.left >= 36.0
    assert safe.right <= 684.0

    title = p.get_zone("TITLE")
    content = p.get_zone("CONTENT")
    caption = p.get_zone("CAPTION")
    bottom_ui = p.get_zone("BOTTOM_UI_SAFE")

    assert safe.contains_rect(title)
    assert safe.contains_rect(content)
    assert safe.contains_rect(caption)
    assert safe.contains_rect(bottom_ui)

    assert title.bottom <= content.top
    assert content.bottom <= caption.top
    assert caption.bottom <= bottom_ui.top


def test_profile_resolution_helper():
    assert get_frame_profile("16:9").aspect_ratio == "16:9"
    assert get_frame_profile("9:16").aspect_ratio == "9:16"
    with pytest.raises(LayoutInvalidInputError):
        get_frame_profile("4:3_unsupported")


# ---------------------------------------------------------------------------
# 3. Kiwisolver Backend Tests
# ---------------------------------------------------------------------------


def test_kiwi_solver_required_and_soft_constraints():
    solver = KiwiLayoutSolver(scene_id="test_kiwi")
    b = solver.add_box("item1")

    # Required bounds
    solver.add_constraint(b.x >= 50.0, STRENGTH_REQUIRED)
    solver.add_constraint(b.right <= 500.0, STRENGTH_REQUIRED)
    solver.add_constraint(b.width >= 100.0, STRENGTH_REQUIRED)
    solver.add_constraint(b.height >= 50.0, STRENGTH_REQUIRED)
    solver.add_constraint(b.y >= 50.0, STRENGTH_REQUIRED)

    # Soft preference: x == 200 (STRONG), width == 100 (WEAK)
    solver.add_constraint(b.x == 200.0, STRENGTH_STRONG)
    solver.add_constraint(b.width == 100.0, STRENGTH_WEAK)

    res = solver.solve()
    assert "item1" in res
    assert res["item1"].x == 200.0
    assert res["item1"].width == 100.0


def test_kiwi_required_beats_soft_preference():
    solver = KiwiLayoutSolver(scene_id="test_kiwi_priority")
    b = solver.add_box("item2")

    # Hard constraint: x <= 80
    solver.add_constraint(b.x <= 80.0, STRENGTH_REQUIRED)
    solver.add_constraint(b.x >= 0.0, STRENGTH_REQUIRED)
    solver.add_constraint(b.y >= 0.0, STRENGTH_REQUIRED)
    solver.add_constraint(b.width >= 50.0, STRENGTH_REQUIRED)
    solver.add_constraint(b.height >= 50.0, STRENGTH_REQUIRED)

    # Soft preference: x == 200 (STRONG)
    solver.add_constraint(b.x == 200.0, STRENGTH_STRONG)

    res = solver.solve()
    # Hard constraint x <= 80 MUST NOT be violated by soft preference
    assert res["item2"].x <= 80.0


def test_kiwi_unsatisfiable_raises_structured_error():
    solver = KiwiLayoutSolver(scene_id="test_unsat")
    b = solver.add_box("impossible_item")

    solver.add_constraint(b.x >= 200.0, STRENGTH_REQUIRED)
    # Contradictory required constraint
    with pytest.raises(LayoutUnsatisfiableError) as exc_info:
        solver.add_constraint(b.x <= 100.0, STRENGTH_REQUIRED)
    assert exc_info.value.code == "LAYOUT_UNSATISFIABLE"


# ---------------------------------------------------------------------------
# 4. Concept Card Strategy Tests
# ---------------------------------------------------------------------------


def test_concept_card_16_9_and_centering():
    items = [
        LayoutItemInput(node_id="title_node", role="title", min_width=250.0, min_height=40.0),
        LayoutItemInput(node_id="content_node", role="content", min_width=400.0, min_height=200.0),
    ]

    lg = solve_layout("sc_concept_169", LayoutStrategy.CONCEPT_CARD, "16:9", items)
    rep = validate_layout_graph(lg)
    assert rep.valid

    box_map = {b.node_id: b for b in lg.boxes}
    title_box = box_map["title_node"]
    content_box = box_map["content_node"]

    p = get_frame_profile("16:9")
    content_zone = p.get_zone("CONTENT")
    title_zone = p.get_zone("TITLE")

    # Content is horizontally and vertically centered in CONTENT zone
    assert abs(content_box.rect.center_x - content_zone.center_x) < 1.0
    assert abs(content_box.rect.center_y - content_zone.center_y) < 1.0

    # Title is in TITLE zone and centered horizontally
    assert abs(title_box.rect.center_x - title_zone.center_x) < 1.0
    assert title_box.zone == "TITLE"
    assert content_box.zone == "CONTENT"


def test_concept_card_9_16_portrait():
    items = [
        LayoutItemInput(node_id="title_p", role="title", min_width=200.0, min_height=35.0),
        LayoutItemInput(node_id="content_p", role="content", min_width=350.0, min_height=300.0),
    ]

    lg = solve_layout("sc_concept_916", LayoutStrategy.CONCEPT_CARD, "9:16", items)
    rep = validate_layout_graph(lg)
    assert rep.valid

    box_map = {b.node_id: b for b in lg.boxes}
    assert box_map["title_p"].zone == "TITLE"
    assert box_map["content_p"].zone == "CONTENT"


def test_concept_card_with_vietnamese_measurement():
    # Measure Vietnamese text via V2-02 intrinsic measurement
    m_title = measure_text("Khái niệm: Quang hợp ở thực vật")
    m_content = measure_text("Quá trình tổng hợp chất hữu cơ từ CO2 và H2O dưới tác dụng của năng lượng ánh sáng.")

    items = [
        LayoutItemInput(
            node_id="vi_title",
            role="title",
            min_width=m_title.minimum_readable_width,
            min_height=m_title.minimum_readable_height,
            preferred_width=m_title.width,
            preferred_height=m_title.height,
        ),
        LayoutItemInput(
            node_id="vi_content",
            role="content",
            min_width=m_content.minimum_readable_width,
            min_height=m_content.minimum_readable_height,
            preferred_width=m_content.width,
            preferred_height=m_content.height,
        ),
    ]

    lg = solve_layout("sc_concept_vi", LayoutStrategy.CONCEPT_CARD, "16:9", items)
    rep = validate_layout_graph(lg, measurements={
        "vi_title": (m_title.minimum_readable_width, m_title.minimum_readable_height),
        "vi_content": (m_content.minimum_readable_width, m_content.minimum_readable_height),
    })
    assert rep.valid
    assert rep.content_clipping_count == 0


# ---------------------------------------------------------------------------
# 5. Comparison Strategy Tests (Symmetry & Gutter)
# ---------------------------------------------------------------------------


def test_comparison_16_9_non_overlap_and_symmetry():
    items = [
        LayoutItemInput(node_id="card_a", role="left", min_width=300.0, min_height=180.0),
        LayoutItemInput(node_id="card_b", role="right", min_width=320.0, min_height=200.0),
    ]

    lg = solve_layout("sc_comp_169", LayoutStrategy.COMPARISON, "16:9", items)
    rep = validate_layout_graph(lg)
    assert rep.valid

    box_map = {b.node_id: b for b in lg.boxes}
    b_left = box_map["card_a"]
    b_right = box_map["card_b"]

    p = get_frame_profile("16:9")
    content_zone = p.get_zone("CONTENT")

    # 1. Non-overlapping with positive gutter
    gutter = b_right.rect.left - b_left.rect.right
    assert gutter >= 16.0

    # 2. Same vertical top alignment
    assert b_left.rect.top == b_right.rect.top

    # 3. Equal width preference
    assert b_left.rect.width == b_right.rect.width

    # 4. Symmetry around content center
    dist_left = content_zone.center_x - b_left.rect.center_x
    dist_right = b_right.rect.center_x - content_zone.center_x
    assert abs(dist_left - dist_right) < 1.0


def test_comparison_portrait_9_16():
    items = [
        LayoutItemInput(node_id="col1", role="left", min_width=200.0, min_height=150.0),
        LayoutItemInput(node_id="col2", role="right", min_width=200.0, min_height=150.0),
    ]

    lg = solve_layout("sc_comp_916", LayoutStrategy.COMPARISON, "9:16", items)
    rep = validate_layout_graph(lg)
    assert rep.valid

    box_map = {b.node_id: b for b in lg.boxes}
    assert box_map["col1"].rect.right < box_map["col2"].rect.left


def test_comparison_oversized_raises_unsat():
    # Two columns that cannot fit in 1152px width with gutter
    items = [
        LayoutItemInput(node_id="c1", role="left", min_width=600.0, min_height=100.0),
        LayoutItemInput(node_id="c2", role="right", min_width=600.0, min_height=100.0),
    ]
    with pytest.raises(LayoutUnsatisfiableError) as exc_info:
        solve_layout("sc_comp_over", LayoutStrategy.COMPARISON, "16:9", items)
    assert exc_info.value.code == "LAYOUT_UNSATISFIABLE"


# ---------------------------------------------------------------------------
# 6. Image + Text Strategy Tests
# ---------------------------------------------------------------------------


def test_image_text_16_9_side_by_side():
    items = [
        LayoutItemInput(node_id="img_node", role="image", min_width=300.0, min_height=200.0, aspect_ratio=1.5),
        LayoutItemInput(node_id="txt_node", role="text", min_width=350.0, min_height=150.0),
    ]

    lg = solve_layout("sc_imgtxt_169", LayoutStrategy.IMAGE_TEXT, "16:9", items)
    rep = validate_layout_graph(lg)
    assert rep.valid

    box_map = {b.node_id: b for b in lg.boxes}
    img_b = box_map["img_node"]
    txt_b = box_map["txt_node"]

    # In 16:9: Side-by-side with gutter
    assert img_b.rect.right < txt_b.rect.left


def test_image_text_9_16_stacked():
    items = [
        LayoutItemInput(node_id="img_node", role="image", min_width=300.0, min_height=200.0, aspect_ratio=1.5),
        LayoutItemInput(node_id="txt_node", role="text", min_width=320.0, min_height=150.0),
    ]

    lg = solve_layout("sc_imgtxt_916", LayoutStrategy.IMAGE_TEXT, "9:16", items)
    rep = validate_layout_graph(lg)
    assert rep.valid

    box_map = {b.node_id: b for b in lg.boxes}
    img_b = box_map["img_node"]
    txt_b = box_map["txt_node"]

    # In 9:16: Stacked (image on top, text below)
    assert img_b.rect.bottom < txt_b.rect.top


def test_image_text_oversized_raises_unsat():
    # In portrait, heights combined exceed content zone height
    items = [
        LayoutItemInput(node_id="huge_img", role="image", min_width=200.0, min_height=600.0),
        LayoutItemInput(node_id="huge_txt", role="text", min_width=200.0, min_height=500.0),
    ]
    with pytest.raises(LayoutUnsatisfiableError) as exc_info:
        solve_layout("sc_imgtxt_over", LayoutStrategy.IMAGE_TEXT, "9:16", items)
    assert exc_info.value.code == "LAYOUT_UNSATISFIABLE"


# ---------------------------------------------------------------------------
# 7. Quote Strategy Tests
# ---------------------------------------------------------------------------


def test_quote_alone_centered():
    items = [
        LayoutItemInput(node_id="q_body", role="quote", min_width=350.0, min_height=100.0),
    ]

    lg = solve_layout("sc_quote_solo", LayoutStrategy.QUOTE, "16:9", items)
    rep = validate_layout_graph(lg)
    assert rep.valid

    q_box = lg.boxes[0]
    p = get_frame_profile("16:9")
    content_zone = p.get_zone("CONTENT")

    assert abs(q_box.rect.center_x - content_zone.center_x) < 1.0
    assert abs(q_box.rect.center_y - content_zone.center_y) < 1.0
    assert q_box.rect.width <= content_zone.width * 0.90 + 0.1


def test_quote_with_attribution():
    items = [
        LayoutItemInput(node_id="q_body", role="quote", min_width=350.0, min_height=100.0),
        LayoutItemInput(node_id="q_author", role="attribution", min_width=180.0, min_height=30.0),
    ]

    lg = solve_layout("sc_quote_attr", LayoutStrategy.QUOTE, "16:9", items)
    rep = validate_layout_graph(lg)
    assert rep.valid

    box_map = {b.node_id: b for b in lg.boxes}
    q_b = box_map["q_body"]
    a_b = box_map["q_author"]

    # Attribution is below quote
    assert a_b.rect.top > q_b.rect.bottom


def test_quote_oversized_raises_unsat():
    # Exceeds max bounded width
    items = [
        LayoutItemInput(node_id="too_wide", role="quote", min_width=1150.0, min_height=100.0),
    ]
    with pytest.raises(LayoutUnsatisfiableError) as exc_info:
        solve_layout("sc_quote_over", LayoutStrategy.QUOTE, "16:9", items)
    assert exc_info.value.code == "LAYOUT_UNSATISFIABLE"


# ---------------------------------------------------------------------------
# 8. Title / Content / Caption Protection Tests
# ---------------------------------------------------------------------------


def test_title_content_caption_separation():
    items = [
        LayoutItemInput(node_id="title1", role="title", min_width=200.0, min_height=30.0),
        LayoutItemInput(node_id="content1", role="content", min_width=300.0, min_height=100.0),
        LayoutItemInput(node_id="caption1", role="caption", min_width=250.0, min_height=30.0),
    ]

    lg = solve_layout("sc_sep", LayoutStrategy.CONCEPT_CARD, "16:9", items)
    validate_layout_graph(lg)

    box_map = {b.node_id: b for b in lg.boxes}
    p = get_frame_profile("16:9")

    # Content does not enter TITLE or CAPTION zones
    assert box_map["content1"].rect.top >= p.get_zone("TITLE").bottom
    assert box_map["content1"].rect.bottom <= p.get_zone("CAPTION").top


# ---------------------------------------------------------------------------
# 9. Preflight Validator Error Tests
# ---------------------------------------------------------------------------


def test_preflight_detects_clipping():
    items = [
        LayoutItemInput(node_id="item1", role="content", min_width=200.0, min_height=100.0),
    ]
    lg = solve_layout("sc_clip", LayoutStrategy.CONCEPT_CARD, "16:9", items)

    # When expected measurement demands 300 width, but box is smaller
    with pytest.raises(LayoutPreflightFailedError) as exc_info:
        validate_layout_graph(lg, measurements={"item1": (1200.0, 100.0)})
    assert exc_info.value.code == "LAYOUT_PREFLIGHT_FAILED"


def test_preflight_detects_frame_overflow():
    # Construct an invalid LayoutGraph with out-of-frame box
    invalid_box = LayoutBox(
        node_id="bad_box",
        rect=Rect(x=1200.0, y=100.0, width=200.0, height=100.0),  # right=1400 > 1280
        zone="CONTENT",
    )
    lg = LayoutGraph(
        schema_version="2.1",
        scene_id="sc_overflow",
        frame_profile_id="16:9_1280x720",
        frame_width=1280.0,
        frame_height=720.0,
        boxes=[invalid_box],
        strategy=LayoutStrategy.CONCEPT_CARD,
    )
    with pytest.raises(LayoutPreflightFailedError) as exc_info:
        validate_layout_graph(lg)
    assert exc_info.value.code == "LAYOUT_PREFLIGHT_FAILED"


# ---------------------------------------------------------------------------
# 10. Fixture Corpus Tests (32 valid + 8 invalid)
# ---------------------------------------------------------------------------


def test_fixture_corpus_valid_cases():
    fixture_path = Path("benchmarks/fixtures/v2/layout_simple_cases.json")
    assert fixture_path.exists(), "layout_simple_cases.json fixture must exist"

    with open(fixture_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    assert len(cases) >= 32, f"Expected at least 32 valid cases, got {len(cases)}"

    for case in cases:
        items = [
            LayoutItemInput(
                node_id=it["node_id"],
                role=it["role"],
                min_width=it["min_width"],
                min_height=it["min_height"],
                aspect_ratio=it.get("aspect_ratio"),
            )
            for it in case["items"]
        ]
        lg = solve_layout(case["case_id"], case["strategy"], case["profile"], items)
        rep = validate_layout_graph(lg)
        assert rep.valid
        assert rep.frame_overflow_count == 0
        assert rep.safe_zone_violation_count == 0
        assert rep.content_clipping_count == 0
        assert rep.invalid_geometry_count == 0


def test_fixture_corpus_invalid_cases():
    fixture_path = Path("benchmarks/fixtures/v2/layout_invalid_cases.json")
    assert fixture_path.exists(), "layout_invalid_cases.json fixture must exist"

    with open(fixture_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    assert len(cases) >= 8, f"Expected at least 8 invalid cases, got {len(cases)}"

    for case in cases:
        items = [
            LayoutItemInput(
                node_id=it["node_id"],
                role=it["role"],
                min_width=it["min_width"],
                min_height=it["min_height"],
            )
            for it in case["items"]
        ]
        with pytest.raises(LayoutUnsatisfiableError) as exc_info:
            solve_layout(case["case_id"], case["strategy"], case["profile"], items)
        assert exc_info.value.code == case["expected_error"]


# ---------------------------------------------------------------------------
# 11. Canonical Serialization Tests
# ---------------------------------------------------------------------------


def test_layout_graph_canonical_serialization_determinism():
    items = [
        LayoutItemInput(node_id="beta_item", role="content", min_width=250.0, min_height=100.0),
        LayoutItemInput(node_id="alpha_item", role="title", min_width=200.0, min_height=40.0),
    ]

    lg1 = solve_layout("sc_canon", LayoutStrategy.CONCEPT_CARD, "16:9", items)
    lg2 = solve_layout("sc_canon", LayoutStrategy.CONCEPT_CARD, "16:9", items)

    json1 = canonical_json(lg1)
    json2 = canonical_json(lg2)

    assert json1 == json2, "Repeated layout solve must produce byte-identical canonical JSON"


def test_layout_graph_canonical_serialization_order_independence():
    # Pass items in different order
    items_order_1 = [
        LayoutItemInput(node_id="b_node", role="right", min_width=200.0, min_height=100.0),
        LayoutItemInput(node_id="a_node", role="left", min_width=200.0, min_height=100.0),
    ]
    items_order_2 = [
        LayoutItemInput(node_id="a_node", role="left", min_width=200.0, min_height=100.0),
        LayoutItemInput(node_id="b_node", role="right", min_width=200.0, min_height=100.0),
    ]

    lg1 = solve_layout("sc_order", LayoutStrategy.COMPARISON, "16:9", items_order_1)
    lg2 = solve_layout("sc_order", LayoutStrategy.COMPARISON, "16:9", items_order_2)

    json1 = canonical_json(lg1)
    json2 = canonical_json(lg2)

    assert json1 == json2, "Input item order must not affect canonical JSON serialization"


def test_layout_graph_distinct_inputs_produce_distinct_json():
    items1 = [LayoutItemInput(node_id="item", role="content", min_width=200.0, min_height=100.0)]
    items2 = [LayoutItemInput(node_id="item", role="content", min_width=400.0, min_height=200.0)]

    lg1 = solve_layout("sc_d1", LayoutStrategy.CONCEPT_CARD, "16:9", items1)
    lg2 = solve_layout("sc_d2", LayoutStrategy.CONCEPT_CARD, "16:9", items2)

    assert canonical_json(lg1) != canonical_json(lg2)


# ---------------------------------------------------------------------------
# 12. Regression & Hardening Tests for V2-03 Blockers
# ---------------------------------------------------------------------------


def test_finite_solver_inputs_rejected_strictly():
    """Blocker 1: Finite solver inputs enforced strictly."""
    # NaN
    with pytest.raises((ValidationError, LayoutInvalidInputError)):
        LayoutItemInput(node_id="n1", min_width=float("nan"))

    with pytest.raises((ValidationError, LayoutInvalidInputError)):
        solve_layout(
            "sc_nan",
            LayoutStrategy.CONCEPT_CARD,
            "16:9",
            [LayoutItemInput(node_id="n1", min_width=100.0, preferred_width=float("nan"))],
        )

    # Inf
    with pytest.raises((ValidationError, LayoutInvalidInputError)):
        LayoutItemInput(node_id="n1", min_height=float("inf"))

    # -Inf
    with pytest.raises((ValidationError, LayoutInvalidInputError)):
        LayoutItemInput(node_id="n1", min_width=float("-inf"))

    # Non-positive values
    with pytest.raises((ValidationError, LayoutInvalidInputError)):
        LayoutItemInput(node_id="n1", min_width=0.0)

    with pytest.raises((ValidationError, LayoutInvalidInputError)):
        LayoutItemInput(node_id="n1", min_width=-10.0)


def test_structured_invalid_input_errors():
    """Blocker 2: Structured invalid-input errors with code and details."""
    # Empty scene_id
    with pytest.raises(LayoutInvalidInputError) as exc_info:
        solve_layout("", LayoutStrategy.CONCEPT_CARD, "16:9", [LayoutItemInput(node_id="n1")])
    assert exc_info.value.code == "LAYOUT_INVALID_INPUT"

    # Empty items
    with pytest.raises(LayoutInvalidInputError) as exc_info:
        solve_layout("sc1", LayoutStrategy.CONCEPT_CARD, "16:9", [])
    assert exc_info.value.code == "LAYOUT_INVALID_INPUT"

    # Duplicate node IDs
    with pytest.raises(LayoutInvalidInputError) as exc_info:
        solve_layout(
            "sc1",
            LayoutStrategy.CONCEPT_CARD,
            "16:9",
            [LayoutItemInput(node_id="dup"), LayoutItemInput(node_id="dup")],
        )
    assert exc_info.value.code == "LAYOUT_INVALID_INPUT"
    assert exc_info.value.details.get("duplicate_id") == "dup"

    # Invalid strategy string
    with pytest.raises(LayoutInvalidInputError) as exc_info:
        solve_layout("sc1", "INVALID_STRATEGY", "16:9", [LayoutItemInput(node_id="n1")])
    assert exc_info.value.code == "LAYOUT_INVALID_INPUT"


def test_layout_graph_schema_version_enforced():
    """Blocker 3: LayoutGraph schema version is explicit and verified."""
    items = [LayoutItemInput(node_id="n1", min_width=100.0, min_height=50.0)]
    lg = solve_layout("sc_ver", LayoutStrategy.CONCEPT_CARD, "16:9", items)
    assert lg.schema_version == "2.1"

    # Reject mismatched schema_version
    with pytest.raises(ValidationError):
        LayoutGraph(
            schema_version="99.9",
            scene_id="sc_ver",
            frame_profile_id="16:9_1280x720",
            frame_width=1280.0,
            frame_height=720.0,
            boxes=lg.boxes,
            strategy=LayoutStrategy.CONCEPT_CARD,
            feasible=True,
        )


def test_replayable_json_safe_metadata():
    """Blocker 4: LayoutGraph metadata must be JSON-serializable and replayable."""
    items = [LayoutItemInput(node_id="n1", min_width=100.0, min_height=50.0)]
    meta = {
        "generator": "test_suite",
        "nested": {"run_id": 42, "tags": ["alpha", "beta"]},
        "factor": 1.5,
    }
    lg = solve_layout("sc_meta", LayoutStrategy.CONCEPT_CARD, "16:9", items, metadata=meta)
    assert lg.metadata == meta
    s = canonical_json(lg)
    assert "generator" in s
    assert "alpha" in s

    # Non-JSON-serializable metadata rejected
    class UnserializableObject:
        pass

    with pytest.raises((ValidationError, ValueError)):
        LayoutGraph(
            schema_version="2.1",
            scene_id="sc_meta_bad",
            frame_profile_id="16:9_1280x720",
            frame_width=1280.0,
            frame_height=720.0,
            boxes=lg.boxes,
            strategy=LayoutStrategy.CONCEPT_CARD,
            feasible=True,
            metadata={"bad_obj": UnserializableObject()},
        )


def test_expected_node_preflight_validation():
    """Blocker 5: Preflight validates that expected nodes are all present."""
    items = [LayoutItemInput(node_id="node_a", min_width=100.0, min_height=50.0)]
    lg = solve_layout("sc_pre_exp", LayoutStrategy.CONCEPT_CARD, "16:9", items)

    # All expected present -> PASS
    report = validate_layout_graph(lg, expected_node_ids=["node_a"])
    assert report.valid is True
    assert report.missing_node_count == 0

    # Missing expected node -> REJECT with LayoutPreflightFailedError
    with pytest.raises(LayoutPreflightFailedError) as exc_info:
        validate_layout_graph(lg, expected_node_ids=["node_a", "node_b_missing"])
    assert exc_info.value.code == "LAYOUT_PREFLIGHT_FAILED"
    assert "missing" in str(exc_info.value).lower()
    assert exc_info.value.details.get("missing_nodes") == 1


def test_invalid_frame_profile_rejection():
    """Blocker 6: Invalid FrameProfile configurations are rejected."""
    # Unknown profile identifier
    with pytest.raises(LayoutInvalidInputError) as exc_info:
        get_frame_profile("unsupported_32:9")
    assert exc_info.value.code == "LAYOUT_INVALID_INPUT"

    # Invalid FrameProfile where insets exceed frame dimensions
    from learnflow_v2.layout.schema import FrameInsets, GridSpec
    with pytest.raises(ValidationError):
        FrameProfile(
            id="bad_profile",
            width=100.0,
            height=100.0,
            aspect_ratio="1:1",
            safe_edge_insets=FrameInsets(top=60.0, bottom=60.0, left=10.0, right=10.0),
            zones={"CONTENT": Rect(x=10.0, y=10.0, width=50.0, height=50.0)},
            grid=GridSpec(),
        )

    # Invalid FrameProfile where zone exceeds safe_edge
    with pytest.raises(ValidationError):
        FrameProfile(
            id="bad_profile_zone",
            width=1000.0,
            height=1000.0,
            aspect_ratio="1:1",
            safe_edge_insets=FrameInsets(top=50.0, bottom=50.0, left=50.0, right=50.0),
            zones={"CONTENT": Rect(x=10.0, y=10.0, width=800.0, height=800.0)},  # x=10 outside safe left 50
            grid=GridSpec(),
        )


def test_strategy_cardinality_enforced():
    """Blocker 7: Strategy cardinality constraints strictly enforced."""
    # COMPARISON requires >= 2 comparison items
    with pytest.raises(LayoutInvalidInputError) as exc_info:
        solve_layout(
            "sc_comp_card",
            LayoutStrategy.COMPARISON,
            "16:9",
            [LayoutItemInput(node_id="only_one", role="left", min_width=100.0, min_height=100.0)],
        )
    assert exc_info.value.code == "LAYOUT_INVALID_INPUT"
    assert "COMPARISON" in str(exc_info.value)

    # IMAGE_TEXT requires both image and text (or >= 2 content items)
    with pytest.raises(LayoutInvalidInputError) as exc_info:
        solve_layout(
            "sc_it_card",
            LayoutStrategy.IMAGE_TEXT,
            "16:9",
            [LayoutItemInput(node_id="single_img", role="image", min_width=100.0, min_height=100.0)],
        )
    assert exc_info.value.code == "LAYOUT_INVALID_INPUT"
    assert "IMAGE_TEXT" in str(exc_info.value)

