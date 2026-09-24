"""Layout constraint compiler for LearnFlow V2 simple strategies.

Compiles semantic items and intrinsic measurements into Kiwisolver linear constraints
and produces strict, deterministic LayoutGraph artifacts.

Supported strategies in V2-03:
- CONCEPT_CARD
- COMPARISON
- IMAGE_TEXT
- QUOTE
"""

import math
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator

from learnflow_v2.core.errors import (
    LayoutInvalidInputError,
    LayoutUnsatisfiableError,
)
from learnflow_v2.layout.backends.kiwi import (
    KiwiLayoutSolver,
    STRENGTH_MEDIUM,
    STRENGTH_REQUIRED,
    STRENGTH_STRONG,
    STRENGTH_WEAK,
)
from learnflow_v2.layout.profiles import get_frame_profile
from learnflow_v2.layout.schema import (
    FrameProfile,
    LayoutBox,
    LayoutGraph,
    LayoutStrategy,
    SIMPLE_LAYOUT_STRATEGIES,
    Rect,
    _check_finite_number,
)
from learnflow_v2.layout.semantics import (
    ZoneClass,
    canonical_zone_for_role,
    is_chrome_role,
    role_zone_class,
    role_zone_details,
    zone_class,
)


def _strict_positive_geometry_number(value: Any, name: str) -> float:
    """Accept real int/float geometry numbers and reject strings, bools, NaN/Inf, and <= 0."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a real numeric value, got {type(value).__name__}")
    f_val = _check_finite_number(value, name)
    if f_val <= 0.0:
        raise ValueError(f"{name} must be strictly positive, got {f_val}")
    return f_val


class LayoutItemInput(BaseModel):
    """Input specification for an item to be placed by the layout solver."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str = Field(..., min_length=1, description="SceneNode ID to place")
    role: str = Field(default="content", min_length=1, description="Layout role")
    min_width: float = Field(default=10.0, gt=0.0, description="Minimum readable width")
    min_height: float = Field(default=10.0, gt=0.0, description="Minimum readable height")
    preferred_width: float | None = Field(default=None, description="Preferred width (soft)")
    preferred_height: float | None = Field(default=None, description="Preferred height (soft)")
    aspect_ratio: float | None = Field(default=None, gt=0.0, description="Aspect ratio (width/height)")
    target_zone: str | None = Field(default=None, description="Specific layout zone override")

    @field_validator("min_width", "min_height", mode="before")
    @classmethod
    def validate_min_sizes(cls, v: Any, info: Any) -> float:
        return _strict_positive_geometry_number(v, info.field_name)

    @field_validator("preferred_width", "preferred_height", "aspect_ratio", mode="before")
    @classmethod
    def validate_optional_finite(cls, v: Any, info: Any) -> float | None:
        if v is None:
            return None
        return _strict_positive_geometry_number(v, info.field_name)

    @field_validator("target_zone")
    @classmethod
    def validate_target_zone(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("target_zone must be None or a non-empty string")
        return v



def _core_items(items: list[LayoutItemInput]) -> list[LayoutItemInput]:
    """Return ordinary content/core items, excluding title/caption chrome aliases."""
    return [item for item in items if not is_chrome_role(item.role)]


def _validate_simple_template_chrome_cardinality(
    strategy: LayoutStrategy,
    items: list[LayoutItemInput],
) -> None:
    """V2-03 simple templates permit at most one title-class and one caption-class item."""
    title_count = sum(1 for item in items if role_zone_class(item.role) == ZoneClass.TITLE)
    caption_count = sum(1 for item in items if role_zone_class(item.role) == ZoneClass.CAPTION)
    if title_count > 1:
        raise LayoutInvalidInputError(
            f"{strategy.value} strategy allows at most one title-class item, got {title_count}",
            details={
                "strategy": strategy.value,
                "zone_class": ZoneClass.TITLE.value,
                "count": title_count,
                "max_allowed": 1,
                "roles": [item.role for item in items if role_zone_class(item.role) == ZoneClass.TITLE],
            },
        )
    if caption_count > 1:
        raise LayoutInvalidInputError(
            f"{strategy.value} strategy allows at most one caption-class item, got {caption_count}",
            details={
                "strategy": strategy.value,
                "zone_class": ZoneClass.CAPTION.value,
                "count": caption_count,
                "max_allowed": 1,
                "roles": [item.role for item in items if role_zone_class(item.role) == ZoneClass.CAPTION],
            },
        )


def solve_layout(
    scene_id: str,
    strategy: LayoutStrategy | str,
    profile: FrameProfile | str,
    items: list[LayoutItemInput],
    metadata: dict[str, Any] | None = None,
) -> LayoutGraph:
    """Compile items and profile into linear constraints and solve for LayoutGraph.

    Args:
        scene_id: Identifier of source scene
        strategy: LayoutStrategy enum or string
        profile: FrameProfile instance or identifier ('16:9', '9:16')
        items: List of items with role and intrinsic measurement bounds
        metadata: Optional dictionary of layout metadata

    Returns:
        Feasible, deterministic LayoutGraph

    Raises:
        LayoutInvalidInputError: If inputs are malformed or missing
        LayoutUnsatisfiableError: If constraints cannot be satisfied
    """
    if not scene_id or not scene_id.strip():
        raise LayoutInvalidInputError("scene_id must be a non-empty string")

    if isinstance(strategy, str):
        try:
            strat_enum = LayoutStrategy(strategy)
        except ValueError as exc:
            raise LayoutInvalidInputError(
                f"Unsupported simple layout strategy '{strategy}'. Supported: {sorted(s.value for s in SIMPLE_LAYOUT_STRATEGIES)}",
                details={"strategy": strategy, "supported": sorted(s.value for s in SIMPLE_LAYOUT_STRATEGIES)},
            ) from exc
    elif isinstance(strategy, LayoutStrategy):
        strat_enum = strategy
    else:
        raise LayoutInvalidInputError(
            f"Invalid strategy type: expected LayoutStrategy or str, got {type(strategy).__name__}",
            details={"strategy": str(strategy)},
        )

    if strat_enum not in SIMPLE_LAYOUT_STRATEGIES:
        message = (
            "DIRECTED_GRAPH must be compiled through layout_directed_graph()"
            if strat_enum == LayoutStrategy.DIRECTED_GRAPH
            else f"{strat_enum.value} is not supported by solve_layout()"
        )
        raise LayoutInvalidInputError(
            message,
            details={
                "strategy": strat_enum.value,
                "supported": sorted(s.value for s in SIMPLE_LAYOUT_STRATEGIES),
                "compiler": "solve_layout",
            },
        )

    if not items:
        raise LayoutInvalidInputError("items list must contain at least one item")

    # Validate items and finiteness
    node_ids = set()
    validated_items: list[LayoutItemInput] = []
    for raw_item in items:
        if isinstance(raw_item, LayoutItemInput):
            item = raw_item
        elif isinstance(raw_item, dict):
            try:
                item = LayoutItemInput(**raw_item)
            except Exception as exc:
                raise LayoutInvalidInputError(
                    f"Malformed layout item input dict: {exc}",
                    details={"raw_item": raw_item, "error": str(exc)},
                ) from exc
        else:
            raise LayoutInvalidInputError(
                f"Expected LayoutItemInput or dict, got {type(raw_item).__name__}",
                details={"item_type": type(raw_item).__name__},
            )

        if not item.node_id or not item.node_id.strip():
            raise LayoutInvalidInputError("All items must have a non-empty node_id")
        if item.node_id in node_ids:
            raise LayoutInvalidInputError(
                f"Duplicate node_id '{item.node_id}' in layout input items",
                details={"duplicate_id": item.node_id},
            )
        node_ids.add(item.node_id)

        # Finiteness & positivity checks on item numbers
        for num_field, num_val in [
            ("min_width", item.min_width),
            ("min_height", item.min_height),
            ("preferred_width", item.preferred_width),
            ("preferred_height", item.preferred_height),
            ("aspect_ratio", item.aspect_ratio),
        ]:
            if num_val is not None:
                if not isinstance(num_val, (int, float)) or not math.isfinite(num_val):
                    raise LayoutInvalidInputError(
                        f"Item '{item.node_id}' has non-finite numeric value for '{num_field}': {num_val}",
                        details={"node_id": item.node_id, "field": num_field, "value": str(num_val)},
                    )
                if num_val <= 0:
                    raise LayoutInvalidInputError(
                        f"Item '{item.node_id}' has non-positive numeric value for '{num_field}': {num_val}",
                        details={"node_id": item.node_id, "field": num_field, "value": num_val},
                    )

        validated_items.append(item)

    items = validated_items

    frame_prof = get_frame_profile(profile)

    # Strategy cardinality validation: V2-03 supports bounded simple templates only.
    _validate_simple_template_chrome_cardinality(strat_enum, items)

    if strat_enum == LayoutStrategy.COMPARISON:
        comp_items = _core_items(items)
        if len(comp_items) != 2:
            raise LayoutInvalidInputError(
                f"COMPARISON strategy requires exactly 2 comparison items, got {len(comp_items)}",
                details={"strategy": "COMPARISON", "comparison_items_count": len(comp_items), "total_items": len(items)},
            )
    elif strat_enum == LayoutStrategy.IMAGE_TEXT:
        core_items = _core_items(items)
        image_items = [it for it in core_items if it.role == "image"]
        text_items = [it for it in core_items if it.role in ("text", "content")]
        extras = [it for it in core_items if it.role not in ("image", "text", "content")]
        if len(image_items) != 1 or len(text_items) != 1 or extras or len(core_items) != 2:
            raise LayoutInvalidInputError(
                "IMAGE_TEXT strategy requires exactly one image item and exactly one text/content item",
                details={
                    "strategy": "IMAGE_TEXT",
                    "image_count": len(image_items),
                    "text_count": len(text_items),
                    "extra_core_roles": [it.role for it in extras],
                    "core_count": len(core_items),
                },
            )
    elif strat_enum == LayoutStrategy.QUOTE:
        core_items = _core_items(items)
        quote_items = [it for it in core_items if it.role in ("quote", "content")]
        attr_items = [it for it in core_items if it.role in ("attribution", "author")]
        extras = [it for it in core_items if it.role not in ("quote", "content", "attribution", "author")]
        if len(quote_items) != 1 or len(attr_items) > 1 or extras or len(core_items) != len(quote_items) + len(attr_items):
            raise LayoutInvalidInputError(
                "QUOTE strategy requires exactly one quote/content item and zero or one attribution",
                details={
                    "strategy": "QUOTE",
                    "quote_count": len(quote_items),
                    "attribution_count": len(attr_items),
                    "extra_core_roles": [it.role for it in extras],
                    "core_count": len(core_items),
                },
            )

    solver = KiwiLayoutSolver(scene_id=scene_id)
    safe_edge = frame_prof.safe_edge_rect
    title_zone = frame_prof.get_zone("TITLE")
    content_zone = frame_prof.get_zone("CONTENT")
    caption_zone = frame_prof.get_zone("CAPTION")

    # Register all box variables and apply universal bounds
    item_zones: dict[str, str] = {}
    for item in items:
        bv = solver.add_box(item.node_id)

        # 1. Physical non-negativity and frame boundary (REQUIRED)
        solver.add_constraint(bv.x >= 0.0, STRENGTH_REQUIRED, stage="frame_bounds")
        solver.add_constraint(bv.y >= 0.0, STRENGTH_REQUIRED, stage="frame_bounds")
        solver.add_constraint(bv.x + bv.width <= frame_prof.width, STRENGTH_REQUIRED, stage="frame_bounds")
        solver.add_constraint(bv.y + bv.height <= frame_prof.height, STRENGTH_REQUIRED, stage="frame_bounds")

        # 2. Global Safe-Edge invariant (REQUIRED)
        solver.add_constraint(bv.x >= safe_edge.left, STRENGTH_REQUIRED, stage="safe_edge")
        solver.add_constraint(bv.y >= safe_edge.top, STRENGTH_REQUIRED, stage="safe_edge")
        solver.add_constraint(bv.x + bv.width <= safe_edge.right, STRENGTH_REQUIRED, stage="safe_edge")
        solver.add_constraint(bv.y + bv.height <= safe_edge.bottom, STRENGTH_REQUIRED, stage="safe_edge")

        # 3. Minimum intrinsic size invariant (REQUIRED)
        solver.add_constraint(bv.width >= float(item.min_width), STRENGTH_REQUIRED, stage="min_size")
        solver.add_constraint(bv.height >= float(item.min_height), STRENGTH_REQUIRED, stage="min_size")

        # 4. Soft preferred dimensions (prefer measured size if preferred not explicitly specified)
        pref_w = item.preferred_width if item.preferred_width is not None else item.min_width
        pref_h = item.preferred_height if item.preferred_height is not None else item.min_height
        if math.isfinite(pref_w):
            solver.add_constraint(bv.width == float(pref_w), STRENGTH_WEAK, stage="preferred_size")
        if math.isfinite(pref_h):
            solver.add_constraint(bv.height == float(pref_h), STRENGTH_WEAK, stage="preferred_size")

        # Determine and validate target zone. A target override may select only a
        # compatible alias within the role's semantic class; it may never cross
        # title/content/caption classes or use reserved spanning zones.
        if item.target_zone:
            assigned_zone = item.target_zone
            requested_class = zone_class(assigned_zone)
            if requested_class is not None and requested_class != role_zone_class(item.role):
                raise LayoutInvalidInputError(
                    f"Item '{item.node_id}' role '{item.role}' cannot target zone '{assigned_zone}'",
                    details=role_zone_details(item.node_id, item.role, assigned_zone),
                )
        else:
            assigned_zone = canonical_zone_for_role(item.role)

        item_zones[item.node_id] = assigned_zone
        try:
            z_rect = frame_prof.get_zone(assigned_zone)
        except KeyError as exc:
            raise LayoutInvalidInputError(
                f"Unknown target zone '{assigned_zone}' for item '{item.node_id}' in profile '{frame_prof.id}'",
                details={"node_id": item.node_id, "target_zone": assigned_zone, "profile_id": frame_prof.id},
            ) from exc

        requested_class = zone_class(assigned_zone)
        if requested_class is None or requested_class != role_zone_class(item.role):
            raise LayoutInvalidInputError(
                f"Item '{item.node_id}' role '{item.role}' cannot target zone '{assigned_zone}'",
                details=role_zone_details(item.node_id, item.role, assigned_zone),
            )

        # Enforce containment in assigned zone (REQUIRED)
        solver.add_constraint(bv.x >= z_rect.left, STRENGTH_REQUIRED, stage="zone_containment")
        solver.add_constraint(bv.y >= z_rect.top, STRENGTH_REQUIRED, stage="zone_containment")
        solver.add_constraint(bv.x + bv.width <= z_rect.right, STRENGTH_REQUIRED, stage="zone_containment")
        solver.add_constraint(bv.y + bv.height <= z_rect.bottom, STRENGTH_REQUIRED, stage="zone_containment")

    # Apply Strategy-Specific Constraints
    gutter_h = max(16.0, frame_prof.grid.horizontal_gap)
    gutter_v = max(16.0, frame_prof.grid.vertical_gap)

    if strat_enum == LayoutStrategy.CONCEPT_CARD:
        _apply_concept_card_constraints(solver, items, content_zone, title_zone, caption_zone)
    elif strat_enum == LayoutStrategy.COMPARISON:
        _apply_comparison_constraints(solver, items, content_zone, gutter_h)
    elif strat_enum == LayoutStrategy.IMAGE_TEXT:
        _apply_image_text_constraints(solver, items, content_zone, frame_prof.aspect_ratio, gutter_h, gutter_v)
    elif strat_enum == LayoutStrategy.QUOTE:
        _apply_quote_constraints(solver, items, content_zone, gutter_v)

    # Solve linear constraints
    rects = solver.solve()

    # Build LayoutBox artifacts sorted deterministically by node_id
    boxes = [
        LayoutBox(
            node_id=item.node_id,
            rect=rects[item.node_id],
            zone=item_zones[item.node_id],
            strategy_role=item.role,
        )
        for item in sorted(items, key=lambda x: x.node_id)
    ]

    return LayoutGraph(
        schema_version="2.1",
        scene_id=scene_id,
        frame_profile_id=frame_prof.id,
        frame_width=frame_prof.width,
        frame_height=frame_prof.height,
        boxes=boxes,
        strategy=strat_enum,
        feasible=True,
        metadata=metadata or {},
    )


def _apply_concept_card_constraints(
    solver: KiwiLayoutSolver,
    items: list[LayoutItemInput],
    content_zone: Rect,
    title_zone: Rect,
    caption_zone: Rect,
) -> None:
    """Concept card: title centered in TITLE, main content centered in CONTENT."""
    content_items = _core_items(items)
    title_items = [it for it in items if role_zone_class(it.role) == ZoneClass.TITLE]

    for it in title_items:
        bv = solver.get_box(it.node_id)
        # Center title horizontally
        solver.add_constraint(bv.center_x == title_zone.center_x, STRENGTH_STRONG, stage="concept_title_center")

    if content_items:
        primary = content_items[0]
        bv = solver.get_box(primary.node_id)
        # Center primary content horizontally and vertically in content zone
        solver.add_constraint(bv.center_x == content_zone.center_x, STRENGTH_STRONG, stage="concept_content_center_x")
        solver.add_constraint(bv.center_y == content_zone.center_y, STRENGTH_STRONG, stage="concept_content_center_y")

        # If secondary content items exist, stack them below primary
        for idx in range(1, len(content_items)):
            prev_bv = solver.get_box(content_items[idx - 1].node_id)
            cur_bv = solver.get_box(content_items[idx].node_id)
            solver.add_constraint(cur_bv.y >= prev_bv.bottom + 16.0, STRENGTH_REQUIRED, stage="concept_subitem_stack")
            solver.add_constraint(cur_bv.center_x == content_zone.center_x, STRENGTH_STRONG, stage="concept_subitem_center")


def _apply_comparison_constraints(
    solver: KiwiLayoutSolver,
    items: list[LayoutItemInput],
    content_zone: Rect,
    gutter_h: float,
) -> None:
    """Comparison: two columns (left & right) in CONTENT zone.

    Hard invariants:
    - left and right in CONTENT zone
    - non-overlapping with positive gutter: left.right + gutter <= right.left
    - same vertical top baseline: left.y == right.y

    Soft preferences:
    - equal widths: left.width == right.width (STRONG)
    - mirror symmetry around content center: (left.center_x + right.center_x) == 2 * content_zone.center_x (STRONG)
    - vertical centering in content zone: left.center_y == content_zone.center_y (MEDIUM)
    """
    comp_items = _core_items(items)
    if len(comp_items) != 2:
        raise LayoutInvalidInputError(
            "COMPARISON strategy requires exactly 2 comparison items",
            details={"item_count": len(comp_items)},
        )

    # Identify left and right items
    left_item = next((it for it in comp_items if it.role == "left"), comp_items[0])
    right_item = next((it for it in comp_items if it.role == "right" and it != left_item), comp_items[1])

    b_left = solver.get_box(left_item.node_id)
    b_right = solver.get_box(right_item.node_id)

    # 1. Non-overlap with required positive gutter (REQUIRED)
    solver.add_constraint(
        b_left.right + float(gutter_h) <= b_right.left,
        STRENGTH_REQUIRED,
        stage="comparison_non_overlap",
    )

    # 2. Same vertical top baseline (REQUIRED)
    solver.add_constraint(
        b_left.y == b_right.y,
        STRENGTH_REQUIRED,
        stage="comparison_top_alignment",
    )

    # 3. Soft preference: Equal widths (STRONG)
    solver.add_constraint(
        b_left.width == b_right.width,
        STRENGTH_STRONG,
        stage="comparison_equal_widths",
    )

    # 4. Soft preference: Mirror symmetry around content center (STRONG)
    # (b_left.center_x + b_right.center_x) / 2 == content_zone.center_x
    solver.add_constraint(
        b_left.center_x + b_right.center_x == 2.0 * content_zone.center_x,
        STRENGTH_STRONG,
        stage="comparison_mirror_symmetry",
    )

    # 5. Soft preference: Centered vertically in content zone (MEDIUM)
    solver.add_constraint(
        b_left.center_y == content_zone.center_y,
        STRENGTH_MEDIUM,
        stage="comparison_vertical_center",
    )

    # 6. Soft preference: Equal heights (WEAK)
    solver.add_constraint(
        b_left.height == b_right.height,
        STRENGTH_WEAK,
        stage="comparison_equal_heights",
    )


def _apply_image_text_constraints(
    solver: KiwiLayoutSolver,
    items: list[LayoutItemInput],
    content_zone: Rect,
    aspect_ratio: str,
    gutter_h: float,
    gutter_v: float,
) -> None:
    """Image + Text:

    - 16:9: Side-by-side (image | text)
    - 9:16: Stacked (image / text)
    """
    img_item = next((it for it in items if it.role == "image"), None)
    text_item = next((it for it in items if it.role in ("text", "content")), None)

    if img_item is None or text_item is None:
        raise LayoutInvalidInputError(
            "IMAGE_TEXT strategy requires both image and text items",
            details={"item_count": len(items)},
        )

    b_img = solver.get_box(img_item.node_id)
    b_txt = solver.get_box(text_item.node_id)

    if aspect_ratio == "16:9":
        # Side-by-side: image on left, text on right
        solver.add_constraint(
            b_img.right + float(gutter_h) <= b_txt.left,
            STRENGTH_REQUIRED,
            stage="image_text_horizontal_separation",
        )
        # Vertical centering in content zone
        solver.add_constraint(b_img.center_y == content_zone.center_y, STRENGTH_STRONG, stage="image_vertical_center")
        solver.add_constraint(b_txt.center_y == content_zone.center_y, STRENGTH_STRONG, stage="text_vertical_center")
        # Combined horizontal balance in content zone
        solver.add_constraint(
            b_img.left + b_txt.right == 2.0 * content_zone.center_x,
            STRENGTH_MEDIUM,
            stage="image_text_composition_center_x",
        )
    else:
        # 9:16 portrait: Stacked image on top, text on bottom
        solver.add_constraint(
            b_img.bottom + float(gutter_v) <= b_txt.top,
            STRENGTH_REQUIRED,
            stage="image_text_vertical_separation",
        )
        # Horizontal centering
        solver.add_constraint(b_img.center_x == content_zone.center_x, STRENGTH_STRONG, stage="image_horizontal_center")
        solver.add_constraint(b_txt.center_x == content_zone.center_x, STRENGTH_STRONG, stage="text_horizontal_center")
        # Combined vertical balance in content zone
        solver.add_constraint(
            b_img.top + b_txt.bottom == 2.0 * content_zone.center_y,
            STRENGTH_MEDIUM,
            stage="image_text_composition_center_y",
        )

    # Image aspect ratio constraint if specified
    if img_item.aspect_ratio is not None and img_item.aspect_ratio > 0:
        ar = float(img_item.aspect_ratio)
        solver.add_constraint(b_img.width == ar * b_img.height, STRENGTH_REQUIRED, stage="image_aspect_ratio")


def _apply_quote_constraints(
    solver: KiwiLayoutSolver,
    items: list[LayoutItemInput],
    content_zone: Rect,
    gutter_v: float,
) -> None:
    """Quote: quote box centered in CONTENT zone, bounded max width, optional attribution."""
    quote_item = next((it for it in items if it.role in ("quote", "content")), items[0])
    attr_item = next((it for it in items if it.role in ("attribution", "author")), None)

    b_quote = solver.get_box(quote_item.node_id)

    # 1. Bounded max width (e.g. 90% of content zone width) (REQUIRED)
    max_quote_w = round(content_zone.width * 0.90, 2)
    solver.add_constraint(
        b_quote.width <= max_quote_w,
        STRENGTH_REQUIRED,
        stage="quote_max_width_bound",
    )

    # 2. Centered horizontally in content zone (STRONG)
    solver.add_constraint(
        b_quote.center_x == content_zone.center_x,
        STRENGTH_STRONG,
        stage="quote_horizontal_center",
    )

    if attr_item is not None:
        b_attr = solver.get_box(attr_item.node_id)
        # Attribution must be below quote with positive gutter (REQUIRED)
        solver.add_constraint(
            b_attr.y >= b_quote.bottom + float(gutter_v),
            STRENGTH_REQUIRED,
            stage="quote_attribution_separation",
        )
        # Attribution horizontally aligned (STRONG)
        solver.add_constraint(
            b_attr.center_x == content_zone.center_x,
            STRENGTH_STRONG,
            stage="attribution_center",
        )
        # Vertical centering of combined composition (STRONG)
        solver.add_constraint(
            b_quote.top + b_attr.bottom == 2.0 * content_zone.center_y,
            STRENGTH_STRONG,
            stage="quote_composition_vertical_center",
        )
    else:
        # Quote alone centered vertically (STRONG)
        solver.add_constraint(
            b_quote.center_y == content_zone.center_y,
            STRENGTH_STRONG,
            stage="quote_alone_vertical_center",
        )
