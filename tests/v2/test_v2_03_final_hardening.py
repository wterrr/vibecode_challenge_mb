"""Adversarial V2-03 final-hardening tests."""

from pathlib import Path
import math

import pytest
from pydantic import ValidationError

from learnflow_v2.core.errors import (
    LayoutInvalidInputError,
    LayoutPreflightFailedError,
    LayoutUnsatisfiableError,
)
from learnflow_v2.layout.constraints import LayoutItemInput, solve_layout
from learnflow_v2.layout.preflight import validate_layout_graph
from learnflow_v2.layout.profiles import create_frame_profile_16_9, create_frame_profile_9_16
from learnflow_v2.layout.schema import (
    FrameInsets,
    FrameProfile,
    GridSpec,
    LayoutBox,
    LayoutGraph,
    LayoutStrategy,
    SIMPLE_LAYOUT_STRATEGIES,
    Rect,
)


def _item(node_id: str, role: str = "content", **kwargs) -> LayoutItemInput:
    data = {"node_id": node_id, "role": role, "min_width": 40, "min_height": 30}
    data.update(kwargs)
    return LayoutItemInput(**data)


def _graph(node_ids=("a",), *, width=1280.0, height=720.0, boxes=None) -> LayoutGraph:
    profile = create_frame_profile_16_9()
    if boxes is None:
        boxes = [
            LayoutBox(
                node_id=node_id,
                rect=Rect(x=100 + 50 * i, y=200, width=40, height=30),
                zone="CONTENT",
                strategy_role="content",
            )
            for i, node_id in enumerate(node_ids)
        ]
    return LayoutGraph(
        scene_id="scene",
        frame_profile_id=profile.id,
        frame_width=width,
        frame_height=height,
        boxes=boxes,
        strategy=LayoutStrategy.CONCEPT_CARD,
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_width": float("nan")},
        {"min_height": float("inf")},
        {"preferred_width": float("nan")},
        {"preferred_height": -1},
        {"aspect_ratio": 0},
        {"aspect_ratio": -1},
        {"aspect_ratio": float("nan")},
    ],
)
def test_layout_item_input_rejects_adversarial_numbers(kwargs):
    with pytest.raises(ValidationError):
        LayoutItemInput(node_id="a", **kwargs)


def test_layout_item_input_is_immutable_and_forbids_extra():
    item = LayoutItemInput(node_id="a")
    with pytest.raises(ValidationError):
        LayoutItemInput(node_id="a", unknown=1)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        item.min_width = 20  # type: ignore[misc]


def test_unknown_target_zone_maps_to_structured_invalid_input():
    with pytest.raises(LayoutInvalidInputError) as exc:
        solve_layout(
            scene_id="scene",
            strategy=LayoutStrategy.CONCEPT_CARD,
            profile="16:9",
            items=[LayoutItemInput(node_id="a", target_zone="NOPE")],
        )
    assert exc.value.code == "LAYOUT_INVALID_INPUT"
    assert exc.value.details["node_id"] == "a"
    assert exc.value.details["target_zone"] == "NOPE"
    assert exc.value.details["profile_id"]


def test_layout_graph_schema_version_locked_and_json_safe_metadata():
    LayoutGraph(
        schema_version="2.1",
        scene_id="scene",
        frame_profile_id="16:9_1280x720",
        frame_width=1280,
        frame_height=720,
        boxes=[],
        strategy=LayoutStrategy.CONCEPT_CARD,
        metadata={"nested": [None, True, 1, 1.5, "ok", {"x": "y"}]},
    )

    for bad_version in ("2.0", "999", ""):
        with pytest.raises(ValidationError):
            LayoutGraph(
                schema_version=bad_version,
                scene_id="scene",
                frame_profile_id="16:9_1280x720",
                frame_width=1280,
                frame_height=720,
                boxes=[],
                strategy=LayoutStrategy.CONCEPT_CARD,
            )

    for bad_metadata in (
        {"x": object()},
        {"x": (1, 2)},
        {"x": float("nan")},
        {"x": float("inf")},
        {"x": {1, 2}},
        {"x": b"bytes"},
        {"x": Path("asset.png")},
        {"x": lambda: None},
    ):
        with pytest.raises(ValidationError):
            LayoutGraph(
                scene_id="scene",
                frame_profile_id="16:9_1280x720",
                frame_width=1280,
                frame_height=720,
                boxes=[],
                strategy=LayoutStrategy.CONCEPT_CARD,
                metadata=bad_metadata,
            )


def test_frame_profile_rejects_invalid_geometry_and_validates_aspect_ratio():
    with pytest.raises(ValidationError):
        FrameProfile(
            id="bad",
            width=100,
            height=100,
            aspect_ratio="1:1",
            safe_edge_insets=FrameInsets(left=60, right=60, top=10, bottom=10),
            zones={"SAFE_EDGE": Rect(x=10, y=10, width=80, height=80)},
            grid=GridSpec(),
        )

    with pytest.raises(ValidationError):
        FrameProfile(
            id="bad_zone",
            width=160,
            height=90,
            aspect_ratio="16:9",
            safe_edge_insets=FrameInsets(left=5, right=5, top=5, bottom=5),
            zones={"SAFE_EDGE": Rect(x=0, y=0, width=200, height=80)},
            grid=GridSpec(),
        )

    assert create_frame_profile_16_9(width=1920, height=1080).aspect_ratio == "16:9"
    with pytest.raises(ValidationError):
        create_frame_profile_16_9(width=1000, height=1000)

    assert create_frame_profile_9_16(width=1080, height=1920).aspect_ratio == "9:16"
    with pytest.raises(ValidationError):
        create_frame_profile_9_16(width=1920, height=1080)


def test_preflight_rejects_frame_identity_mismatch_and_expected_node_set():
    with pytest.raises(LayoutPreflightFailedError) as exc:
        validate_layout_graph(_graph(width=999, height=999), profile="16:9")
    assert exc.value.code == "LAYOUT_PREFLIGHT_FAILED"

    validate_layout_graph(_graph(node_ids=("a", "b")), profile="16:9", expected_node_ids={"a", "b"})

    with pytest.raises(LayoutPreflightFailedError):
        validate_layout_graph(_graph(node_ids=("a",)), profile="16:9", expected_node_ids={"a", "b"})

    with pytest.raises(LayoutPreflightFailedError):
        validate_layout_graph(_graph(node_ids=("a", "b")), profile="16:9", expected_node_ids={"a"})

    dup_box = LayoutBox(
        node_id="a",
        rect=Rect(x=100, y=200, width=40, height=30),
        zone="CONTENT",
        strategy_role="content",
    )
    with pytest.raises(LayoutPreflightFailedError):
        validate_layout_graph(_graph(boxes=[dup_box, dup_box]), profile="16:9")


def test_comparison_cardinality_contract():
    solve_layout("scene", LayoutStrategy.COMPARISON, "16:9", [_item("a", "left"), _item("b", "right")])

    for items in (
        [_item("a", "left")],
        [_item("a", "left"), _item("b", "right"), _item("c", "content")],
    ):
        with pytest.raises(LayoutInvalidInputError) as exc:
            solve_layout("scene", LayoutStrategy.COMPARISON, "16:9", items)
        assert exc.value.code == "LAYOUT_INVALID_INPUT"


def test_image_text_cardinality_contract():
    solve_layout("scene", LayoutStrategy.IMAGE_TEXT, "16:9", [_item("img", "image"), _item("txt", "text")])

    invalid_sets = [
        [_item("txt", "text")],
        [_item("img", "image")],
        [_item("img", "image"), _item("txt", "text"), _item("extra", "content")],
    ]
    for items in invalid_sets:
        with pytest.raises(LayoutInvalidInputError):
            solve_layout("scene", LayoutStrategy.IMAGE_TEXT, "16:9", items)


def test_quote_cardinality_contract():
    solve_layout("scene", LayoutStrategy.QUOTE, "16:9", [_item("q", "quote")])
    solve_layout("scene", LayoutStrategy.QUOTE, "16:9", [_item("q", "quote"), _item("a", "attribution")])

    invalid_sets = [
        [_item("q", "quote"), _item("a", "attribution"), _item("b", "author")],
        [_item("q", "quote"), _item("x", "diagram")],
    ]
    for items in invalid_sets:
        with pytest.raises(LayoutInvalidInputError):
            solve_layout("scene", LayoutStrategy.QUOTE, "16:9", items)


def test_image_aspect_ratio_is_required_content_invariant():
    graph = solve_layout(
        "scene",
        LayoutStrategy.IMAGE_TEXT,
        "16:9",
        [
            _item("img", "image", min_width=160, min_height=90, aspect_ratio=16 / 9),
            _item("txt", "text", min_width=100, min_height=60),
        ],
    )
    img_box = next(b for b in graph.boxes if b.node_id == "img")
    assert abs((img_box.rect.width / img_box.rect.height) - (16 / 9)) <= 1e-2

    with pytest.raises(LayoutUnsatisfiableError) as exc:
        solve_layout(
            "scene",
            LayoutStrategy.IMAGE_TEXT,
            "16:9",
            [
                _item("img", "image", min_width=500, min_height=500, aspect_ratio=10),
                _item("txt", "text", min_width=100, min_height=60),
            ],
        )
    assert exc.value.code == "LAYOUT_UNSATISFIABLE"


# ---------------------------------------------------------------------------
# V2-03 CONTRACT SEAL: role/zone semantics, chrome cardinality, strict numbers
# ---------------------------------------------------------------------------


def _minimal_items_for_strategy(strategy: LayoutStrategy, extra_items: list[LayoutItemInput] | None = None) -> list[LayoutItemInput]:
    extras = list(extra_items or [])
    if strategy == LayoutStrategy.CONCEPT_CARD:
        return [_item("content", "content"), *extras]
    if strategy == LayoutStrategy.COMPARISON:
        return [_item("left", "left"), _item("right", "right"), *extras]
    if strategy == LayoutStrategy.IMAGE_TEXT:
        return [_item("image", "image", aspect_ratio=1.5), _item("text", "text"), *extras]
    if strategy == LayoutStrategy.QUOTE:
        return [_item("quote", "quote"), *extras]
    raise AssertionError(f"Unhandled strategy {strategy}")


@pytest.mark.parametrize(
    ("role", "target_zone"),
    [
        ("content", "CAPTION"),
        ("content", "TITLE"),
        ("title", "CONTENT"),
        ("caption", "CONTENT"),
        ("content", "SAFE_EDGE"),
    ],
)
def test_solver_rejects_cross_class_target_zone_overrides(role, target_zone):
    with pytest.raises(LayoutInvalidInputError) as exc:
        solve_layout(
            scene_id="semantic_reject",
            strategy=LayoutStrategy.CONCEPT_CARD,
            profile="16:9",
            items=[_item("n", role, target_zone=target_zone)],
        )
    assert exc.value.code == "LAYOUT_INVALID_INPUT"
    assert exc.value.details["node_id"] == "n"
    assert exc.value.details["role"] == role
    assert exc.value.details["target_zone"] == target_zone
    assert exc.value.details["expected_zone_class"] in {"TITLE", "CONTENT", "CAPTION"}


@pytest.mark.parametrize(
    ("role", "target_zone"),
    [
        ("title", "SAFE_TITLE"),
        ("content", "SAFE_CONTENT"),
        ("caption", "SAFE_CAPTION"),
    ],
)
def test_solver_accepts_compatible_landscape_aliases(role, target_zone):
    graph = solve_layout(
        scene_id=f"alias_{role}",
        strategy=LayoutStrategy.CONCEPT_CARD,
        profile="16:9",
        items=[_item("n", role, target_zone=target_zone)],
    )
    assert graph.boxes[0].zone == target_zone
    validate_layout_graph(graph)


@pytest.mark.parametrize(
    ("role", "target_zone"),
    [
        ("title", "TOP_HOOK"),
        ("content", "PRIMARY_CONTENT"),
        ("caption", "SUBTITLE_ZONE"),
    ],
)
def test_solver_accepts_compatible_portrait_aliases(role, target_zone):
    graph = solve_layout(
        scene_id=f"portrait_alias_{role}",
        strategy=LayoutStrategy.CONCEPT_CARD,
        profile="9:16",
        items=[_item("n", role, target_zone=target_zone)],
    )
    assert graph.boxes[0].zone == target_zone
    validate_layout_graph(graph)


def _manual_graph_for_role_zone(role: str, zone: str) -> LayoutGraph:
    profile = create_frame_profile_16_9()
    zone_rect = profile.get_zone(zone)
    return LayoutGraph(
        scene_id=f"manual_{role}_{zone}",
        frame_profile_id=profile.id,
        frame_width=profile.width,
        frame_height=profile.height,
        strategy=LayoutStrategy.CONCEPT_CARD,
        boxes=[
            LayoutBox(
                node_id="n",
                rect=Rect(x=zone_rect.x + 1, y=zone_rect.y + 1, width=40, height=30),
                zone=zone,
                strategy_role=role,
            )
        ],
    )


@pytest.mark.parametrize(
    ("role", "zone"),
    [
        ("content", "CAPTION"),
        ("title", "CONTENT"),
        ("caption", "CONTENT"),
    ],
)
def test_preflight_rejects_cross_class_persisted_artifacts(role, zone):
    graph = _manual_graph_for_role_zone(role, zone)
    with pytest.raises(LayoutPreflightFailedError) as exc:
        validate_layout_graph(graph)
    assert exc.value.code == "LAYOUT_PREFLIGHT_FAILED"
    assert "expected_zone_class" in "; ".join(exc.value.details["violations"])


@pytest.mark.parametrize(
    ("role", "zone"),
    [
        ("content", "CONTENT"),
        ("title", "TITLE"),
        ("caption", "CAPTION"),
        ("header", "SAFE_TITLE"),
        ("subtitle", "SAFE_CAPTION"),
    ],
)
def test_preflight_accepts_valid_role_zone_combinations(role, zone):
    validate_layout_graph(_manual_graph_for_role_zone(role, zone))


@pytest.mark.parametrize("strategy", sorted(SIMPLE_LAYOUT_STRATEGIES, key=lambda s: s.value))
def test_every_strategy_rejects_two_title_class_items(strategy):
    items = _minimal_items_for_strategy(strategy, [_item("title_1", "title"), _item("title_2", "safe_title")])
    with pytest.raises(LayoutInvalidInputError) as exc:
        solve_layout("two_titles", strategy, "16:9", items)
    assert exc.value.code == "LAYOUT_INVALID_INPUT"
    assert exc.value.details["zone_class"] == "TITLE"
    assert exc.value.details["max_allowed"] == 1


@pytest.mark.parametrize("strategy", sorted(SIMPLE_LAYOUT_STRATEGIES, key=lambda s: s.value))
def test_every_strategy_rejects_two_caption_class_items(strategy):
    items = _minimal_items_for_strategy(strategy, [_item("cap_1", "caption"), _item("cap_2", "safe_caption")])
    with pytest.raises(LayoutInvalidInputError) as exc:
        solve_layout("two_captions", strategy, "16:9", items)
    assert exc.value.code == "LAYOUT_INVALID_INPUT"
    assert exc.value.details["zone_class"] == "CAPTION"
    assert exc.value.details["max_allowed"] == 1


@pytest.mark.parametrize("strategy", sorted(SIMPLE_LAYOUT_STRATEGIES, key=lambda s: s.value))
def test_every_strategy_rejects_title_header_alias_mix(strategy):
    items = _minimal_items_for_strategy(strategy, [_item("title_1", "title"), _item("header_1", "header")])
    with pytest.raises(LayoutInvalidInputError) as exc:
        solve_layout("title_header_mix", strategy, "16:9", items)
    assert exc.value.details["zone_class"] == "TITLE"
    assert exc.value.details["roles"] == ["title", "header"]


@pytest.mark.parametrize("strategy", sorted(SIMPLE_LAYOUT_STRATEGIES, key=lambda s: s.value))
def test_every_strategy_rejects_caption_subtitle_alias_mix(strategy):
    items = _minimal_items_for_strategy(strategy, [_item("caption_1", "caption"), _item("subtitle_1", "subtitle")])
    with pytest.raises(LayoutInvalidInputError) as exc:
        solve_layout("caption_subtitle_mix", strategy, "16:9", items)
    assert exc.value.details["zone_class"] == "CAPTION"
    assert exc.value.details["roles"] == ["caption", "subtitle"]


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("min_width", "10"),
        ("min_height", "10"),
        ("preferred_width", "10"),
        ("preferred_height", "10"),
        ("aspect_ratio", "1.5"),
        ("min_width", True),
        ("min_height", False),
        ("preferred_width", True),
        ("preferred_height", False),
        ("aspect_ratio", True),
    ],
)
def test_layout_item_input_rejects_string_and_bool_geometry(field, bad_value):
    kwargs = {field: bad_value}
    with pytest.raises(ValidationError):
        LayoutItemInput(node_id="strict", **kwargs)


@pytest.mark.parametrize(
    ("field", "good_value"),
    [
        ("min_width", 10),
        ("min_width", 10.0),
        ("min_height", 10),
        ("min_height", 10.0),
        ("preferred_width", 10),
        ("preferred_height", 10.0),
        ("aspect_ratio", 1),
        ("aspect_ratio", 1.5),
    ],
)
def test_layout_item_input_accepts_real_int_and_float_geometry(field, good_value):
    item = LayoutItemInput(node_id="strict_ok", **{field: good_value})
    assert getattr(item, field) == float(good_value)
