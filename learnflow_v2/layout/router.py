"""Production SceneGraph -> LayoutGraph router for LearnFlow V2.

This is the missing orchestration layer described in PLAN_V2.md §6/§8. It does
not contain lesson-specific branches. Selection is driven only by SceneGraph
layout intent and semantic roles.
"""

from __future__ import annotations

import math
from typing import Iterable

from learnflow_v2.core.errors import LayoutUnsatisfiableError
from learnflow_v2.layout.graph import layout_directed_graph
from learnflow_v2.layout.measurement import MeasurementPolicy, TextMeasurement, measure_node, measure_text
from learnflow_v2.layout.preflight import validate_layout_graph
from learnflow_v2.layout.profiles import create_frame_profile_16_9
from learnflow_v2.layout.schema import (
    FrameProfile,
    GraphBackendKind,
    LayoutBox,
    LayoutGraph,
    LayoutStrategy,
    Point,
    Rect,
    RoutedEdge,
    RoutingStyle,
)
from learnflow_v2.scenegraph.enums import LayoutIntent, NodeKind, PreferredRegion, RelationKind
from learnflow_v2.scenegraph.schema import SceneGraph, SceneNode


_DEFAULT_POLICY = MeasurementPolicy(
    preferred_font_size=18.0,
    minimum_font_size=18.0,
    candidate_max_widths=[120.0, 180.0, 240.0, 320.0, 480.0],
)


def _text(node: SceneNode) -> str:
    return (node.content or node.label or node.semantic_role or node.kind.value).strip()


def _measure(node: SceneNode, policy: MeasurementPolicy) -> TextMeasurement:
    """Measure every benchmark-relevant semantic node deterministically.

    Container/group-like semantic nodes still render text labels, so they use
    text measurement instead of pretending to be external assets.
    """
    if node.kind in {NodeKind.TEXT, NodeKind.CONCEPT, NodeKind.CALLOUT, NodeKind.CODE}:
        measured = measure_node(node, policy=policy)
        assert isinstance(measured, TextMeasurement)
        return measured
    return measure_text(_text(node), policy)


def measure_scene_nodes(
    scene_graph: SceneGraph,
    *,
    policy: MeasurementPolicy | None = None,
) -> dict[str, TextMeasurement]:
    policy = policy or _DEFAULT_POLICY
    return {node.id: _measure(node, policy) for node in scene_graph.nodes}


def _wrapped_text_height(measurement: TextMeasurement, outer_width: float, *, horizontal_padding: float = 20.0) -> float:
    """Measure wrapped readable text at the exact renderer inner width."""
    inner_width = max(1.0, float(outer_width) - horizontal_padding)
    exact = measure_text(
        measurement.content,
        MeasurementPolicy(
            preferred_font_size=_DEFAULT_POLICY.preferred_font_size,
            minimum_font_size=_DEFAULT_POLICY.minimum_font_size,
            candidate_max_widths=[inner_width],
            emergency_break_long_tokens=False,
        ),
    )
    candidate = exact.wrap_candidates[0]
    if candidate.had_overflow_token or candidate.width > inner_width + 1e-6:
        raise LayoutUnsatisfiableError(
            "Text cannot fit readable width without overflow",
            {
                "inner_width": inner_width,
                "candidate_width": candidate.width,
                "candidate_max_width": candidate.max_width,
            },
        )
    return float(candidate.height)


def _fit_rect(
    zone: Rect,
    *,
    preferred_width: float,
    preferred_height: float,
    preferred_region: PreferredRegion | None = None,
    margin_x: float = 8.0,
    margin_y: float = 4.0,
) -> Rect:
    """Fit within one semantic zone while honoring abstract region intent.

    preferred_region remains semantic. This function alone converts LEFT/RIGHT/
    TOP/BOTTOM into deterministic geometry inside the already-authorized zone.
    """
    width = min(max(24.0, preferred_width), max(24.0, zone.width - margin_x * 2.0))
    height = min(max(20.0, preferred_height), max(20.0, zone.height - margin_y * 2.0))
    left_regions = {PreferredRegion.LEFT, PreferredRegion.TOP_LEFT, PreferredRegion.BOTTOM_LEFT}
    right_regions = {PreferredRegion.RIGHT, PreferredRegion.TOP_RIGHT, PreferredRegion.BOTTOM_RIGHT}
    top_regions = {PreferredRegion.TOP, PreferredRegion.TOP_LEFT, PreferredRegion.TOP_RIGHT}
    bottom_regions = {PreferredRegion.BOTTOM, PreferredRegion.BOTTOM_LEFT, PreferredRegion.BOTTOM_RIGHT}

    if preferred_region in left_regions:
        x = zone.x + margin_x
    elif preferred_region in right_regions:
        x = zone.right - width - margin_x
    else:
        x = zone.x + (zone.width - width) / 2.0

    if preferred_region in top_regions:
        y = zone.y + margin_y
    elif preferred_region in bottom_regions:
        y = zone.bottom - height - margin_y
    else:
        y = zone.y + (zone.height - height) / 2.0

    return Rect(x=round(x, 4), y=round(y, 4), width=round(width, 4), height=round(height, 4))


def _stack_in_zone(
    nodes: Iterable[SceneNode],
    measurements: dict[str, TextMeasurement],
    zone: Rect,
    *,
    gap: float,
    zone_name: str,
) -> list[LayoutBox]:
    """Stack cards using their actual wrapped readable heights, not equal-height slots."""
    ordered = list(nodes)
    if not ordered:
        return []

    specs: list[tuple[SceneNode, float, float]] = []
    for node in ordered:
        measurement = measurements[node.id]
        # Stacked comparison/content cards use a compact 4px outer margin.
        # Measure against the exact maximum outer width that _fit_rect() will
        # actually return so Layout and Renderer cannot disagree about wrapping.
        max_outer_width = max(24.0, zone.width - 8.0)
        preferred_width = max(
            measurement.minimum_readable_width + 20.0,
            min(measurement.width + 40.0, max_outer_width),
        )
        preferred_width = min(preferred_width, max_outer_width)
        required_height = _wrapped_text_height(measurement, preferred_width) + 16.0
        specs.append((node, preferred_width, required_height))

    required_total = sum(item[2] for item in specs) + gap * (len(specs) - 1)
    if required_total > zone.height + 1e-6:
        raise LayoutUnsatisfiableError(
            "Readable stacked content does not fit specialized layout zone",
            {
                "required_height": required_total,
                "zone_height": zone.height,
                "node_ids": [node.id for node, _, _ in specs],
            },
        )

    extra_per_slot = max(0.0, zone.height - required_total) / len(specs)
    boxes: list[LayoutBox] = []
    y = zone.y
    for node, preferred_width, required_height in specs:
        slot_h = required_height + extra_per_slot
        slot = Rect(x=zone.x, y=round(y, 4), width=zone.width, height=round(slot_h, 4))
        rect = _fit_rect(
            slot,
            preferred_width=preferred_width,
            preferred_height=required_height,
            preferred_region=node.layout_hint.preferred_region if node.layout_hint else None,
            margin_x=4.0,
        )
        boxes.append(
            LayoutBox(
                node_id=node.id,
                rect=rect,
                zone=zone_name,
                strategy_role=node.semantic_role or "content",
                semantic_key=node.semantic_key,
            )
        )
        y += slot_h + gap
    return boxes

def _compile_concept_card(
    scene_graph: SceneGraph,
    profile: FrameProfile,
    measurements: dict[str, TextMeasurement],
) -> LayoutGraph:
    title_zone = profile.get_zone("TITLE")
    content_zone = profile.get_zone("CONTENT")
    primary = [
        node for node in scene_graph.nodes
        if node.semantic_role in {"PRIMARY_CONCEPT", "PROCESS_TOPIC", "COMPARISON_TOPIC"}
    ]
    if len(primary) != 1:
        # Stable fallback: most important/first semantic node becomes heading.
        primary = [sorted(scene_graph.nodes, key=lambda n: (-(n.layout_hint.importance if n.layout_hint else 0.5), n.id))[0]]
    primary_node = primary[0]
    title_m = measurements[primary_node.id]
    title_width = min(title_zone.width - 8.0, title_m.width + 36.0)
    title_required_h = _wrapped_text_height(title_m, title_width) + 16.0
    title_box = LayoutBox(
        node_id=primary_node.id,
        rect=_fit_rect(
            title_zone,
            preferred_width=title_width,
            preferred_height=min(title_zone.height - 4.0, max(38.0, title_required_h)),
            preferred_region=primary_node.layout_hint.preferred_region if primary_node.layout_hint else None,
        ),
        zone="TITLE",
        strategy_role="title",
        semantic_key=primary_node.semantic_key,
    )
    support = [node for node in scene_graph.nodes if node.id != primary_node.id]
    support.sort(key=lambda n: ((n.layout_hint.preferred_order if n.layout_hint and n.layout_hint.preferred_order is not None else 9999), n.id))
    boxes = [title_box] + _stack_in_zone(
        support, measurements, content_zone, gap=max(8.0, profile.height * 0.025), zone_name="CONTENT"
    )
    graph = LayoutGraph(
        scene_id=scene_graph.scene_id,
        frame_profile_id=profile.id,
        frame_width=profile.width,
        frame_height=profile.height,
        boxes=boxes,
        routed_edges=[],
        strategy=LayoutStrategy.CONCEPT_CARD,
        feasible=True,
        metadata={"router": "specialized_concept_card_v1"},
    )
    validate_layout_graph(
        graph,
        profile=profile,
        measurements={nid: (m.minimum_readable_width, m.minimum_readable_height) for nid, m in measurements.items()},
        expected_node_ids={n.id for n in scene_graph.nodes},
    )
    return graph


def _column_members(scene_graph: SceneGraph, column_id: str) -> list[SceneNode]:
    child_ids = {
        relation.source
        for relation in scene_graph.relations
        if relation.kind == RelationKind.PART_OF and relation.target == column_id
    }
    by_id = {node.id: node for node in scene_graph.nodes}
    members = [by_id[node_id] for node_id in child_ids if node_id in by_id]
    members.sort(key=lambda n: ((n.layout_hint.preferred_order if n.layout_hint and n.layout_hint.preferred_order is not None else 9999), n.id))
    return members



def _lane_rects(zone: Rect, count: int, *, gap: float) -> list[Rect]:
    if count <= 0:
        return []
    width = (zone.width - gap * (count - 1)) / count
    if width <= 24.0:
        raise LayoutUnsatisfiableError("Compact PROCESS lane cannot fit requested node count")
    return [
        Rect(
            x=round(zone.x + index * (width + gap), 4),
            y=zone.y,
            width=round(width, 4),
            height=zone.height,
        )
        for index in range(count)
    ]


def _route_between(source: Rect, target: Rect) -> list[Point]:
    """Deterministic orthogonal route with endpoints on source/target boundaries."""
    sx, sy = source.center_x, source.center_y
    tx, ty = target.center_x, target.center_y
    if target.top >= source.bottom:
        start = Point(x=round(sx, 4), y=round(source.bottom, 4))
        end = Point(x=round(tx, 4), y=round(target.top, 4))
        mid_y = round((start.y + end.y) / 2.0, 4)
        return [start, Point(x=start.x, y=mid_y), Point(x=end.x, y=mid_y), end]
    if source.top >= target.bottom:
        start = Point(x=round(sx, 4), y=round(source.top, 4))
        end = Point(x=round(tx, 4), y=round(target.bottom, 4))
        mid_y = round((start.y + end.y) / 2.0, 4)
        return [start, Point(x=start.x, y=mid_y), Point(x=end.x, y=mid_y), end]
    if tx >= sx:
        start = Point(x=round(source.right, 4), y=round(sy, 4))
        end = Point(x=round(target.left, 4), y=round(ty, 4))
    else:
        start = Point(x=round(source.left, 4), y=round(sy, 4))
        end = Point(x=round(target.right, 4), y=round(ty, 4))
    mid_x = round((start.x + end.x) / 2.0, 4)
    return [start, Point(x=mid_x, y=start.y), Point(x=mid_x, y=end.y), end]


def _compile_process_compact(
    scene_graph: SceneGraph,
    profile: FrameProfile,
    measurements: dict[str, TextMeasurement],
) -> LayoutGraph:
    """Generic compact PROCESS fallback after directed-graph candidate is infeasible.

    Semantic roles, not lesson IDs, define two visual lanes:
    process actors above and ordered process steps below. The process topic stays
    in TITLE. Every SceneGraph relation is routed as an orthogonal edge.
    """
    topics = [node for node in scene_graph.nodes if node.semantic_role == "PROCESS_TOPIC"]
    actors = [node for node in scene_graph.nodes if node.semantic_role == "PROCESS_ACTOR"]
    steps = [node for node in scene_graph.nodes if node.semantic_role == "PROCESS_STEP"]
    covered = {node.id for node in topics + actors + steps}
    extras = [node.id for node in scene_graph.nodes if node.id not in covered]
    if len(topics) != 1 or not actors or not steps or extras:
        raise LayoutUnsatisfiableError(
            "Compact PROCESS fallback requires one PROCESS_TOPIC plus PROCESS_ACTOR/PROCESS_STEP nodes",
            {"topic_count": len(topics), "actor_count": len(actors), "step_count": len(steps), "extras": sorted(extras)},
        )

    topic = topics[0]
    actors = sorted(actors, key=lambda node: node.id)
    steps = sorted(
        steps,
        key=lambda node: (
            node.layout_hint.preferred_order
            if node.layout_hint and node.layout_hint.preferred_order is not None
            else 9999,
            node.id,
        ),
    )
    title_zone = profile.get_zone("TITLE")
    content = profile.get_zone("CONTENT")
    lane_gap = max(8.0, profile.height * 0.025)
    inter_lane_gap = max(12.0, profile.height * 0.04)
    actor_h = max(44.0, min(content.height * 0.32, 72.0))
    step_y = content.y + actor_h + inter_lane_gap
    step_h = content.bottom - step_y
    if step_h <= 40.0:
        raise LayoutUnsatisfiableError("Compact PROCESS fallback has insufficient step-lane height")

    actor_zone = Rect(x=content.x, y=content.y, width=content.width, height=actor_h)
    step_zone = Rect(x=content.x, y=round(step_y, 4), width=content.width, height=round(step_h, 4))
    actor_slots = _lane_rects(actor_zone, len(actors), gap=lane_gap)
    step_slots = _lane_rects(step_zone, len(steps), gap=lane_gap)

    title_measure = measurements[topic.id]
    boxes: list[LayoutBox] = [
        LayoutBox(
            node_id=topic.id,
            rect=_fit_rect(
                title_zone,
                preferred_width=min(title_zone.width - 8.0, title_measure.width + 30.0),
                preferred_height=min(
                    title_zone.height - 4.0,
                    max(38.0, _wrapped_text_height(title_measure, min(title_zone.width - 8.0, title_measure.width + 30.0)) + 16.0),
                ),
            ),
            zone="TITLE",
            strategy_role="title",
            semantic_key=topic.semantic_key,
        )
    ]

    for node, slot in zip(actors, actor_slots):
        measurement = measurements[node.id]
        if measurement.minimum_readable_width > slot.width + 1e-6:
            raise LayoutUnsatisfiableError(
                f"Actor '{node.id}' cannot fit minimum readable width in compact PROCESS lane"
            )
        preferred_width = min(
            max(measurement.minimum_readable_width + 20.0, min(slot.width * 0.90, measurement.width + 20.0)),
            max(24.0, slot.width - 16.0),
        )
        required_height = _wrapped_text_height(measurement, preferred_width) + 16.0
        if required_height > slot.height - 8.0 + 1e-6:
            raise LayoutUnsatisfiableError(
                f"Actor '{node.id}' wrapped readable text does not fit compact PROCESS lane"
            )
        boxes.append(
            LayoutBox(
                node_id=node.id,
                rect=_fit_rect(
                    slot,
                    preferred_width=preferred_width,
                    preferred_height=required_height,
                    preferred_region=node.layout_hint.preferred_region if node.layout_hint else None,
                ),
                zone="CONTENT",
                strategy_role="process_actor",
                semantic_key=node.semantic_key,
            )
        )

    for node, slot in zip(steps, step_slots):
        measurement = measurements[node.id]
        if measurement.minimum_readable_width > slot.width + 1e-6:
            raise LayoutUnsatisfiableError(
                f"Step '{node.id}' cannot fit minimum readable width in compact PROCESS lane"
            )
        preferred_width = min(
            max(measurement.minimum_readable_width + 20.0, min(slot.width * 0.90, measurement.width + 20.0)),
            max(24.0, slot.width - 16.0),
        )
        required_height = _wrapped_text_height(measurement, preferred_width) + 16.0
        if required_height > slot.height - 8.0 + 1e-6:
            raise LayoutUnsatisfiableError(
                f"Step '{node.id}' wrapped readable text does not fit compact PROCESS lane"
            )
        boxes.append(
            LayoutBox(
                node_id=node.id,
                rect=_fit_rect(
                    slot,
                    preferred_width=preferred_width,
                    preferred_height=required_height,
                    preferred_region=node.layout_hint.preferred_region if node.layout_hint else None,
                ),
                zone="CONTENT",
                strategy_role="process_step",
                semantic_key=node.semantic_key,
            )
        )

    box_map = {box.node_id: box.rect for box in boxes}
    routed = [
        RoutedEdge(
            edge_id=relation.id,
            source=relation.source,
            target=relation.target,
            points=_route_between(box_map[relation.source], box_map[relation.target]),
            routing_style=RoutingStyle.ORTHOGONAL,
            backend=GraphBackendKind.GRAPHVIZ,
        )
        for relation in sorted(scene_graph.relations, key=lambda rel: rel.id)
        if relation.source in box_map and relation.target in box_map
    ]
    if len(routed) != len(scene_graph.relations):
        raise LayoutUnsatisfiableError("Compact PROCESS fallback could not route every semantic relation")

    graph = LayoutGraph(
        scene_id=scene_graph.scene_id,
        frame_profile_id=profile.id,
        frame_width=profile.width,
        frame_height=profile.height,
        boxes=boxes,
        routed_edges=routed,
        strategy=LayoutStrategy.DIRECTED_GRAPH,
        feasible=True,
        metadata={
            "router": "compact_process_v1",
            "graph_backend": GraphBackendKind.GRAPHVIZ.value,
            "graph_kind": "PROCESS",
        },
    )
    validate_layout_graph(
        graph,
        profile=profile,
        measurements={nid: (m.minimum_readable_width, m.minimum_readable_height) for nid, m in measurements.items()},
        expected_node_ids={node.id for node in scene_graph.nodes},
    )
    return graph


def _compile_comparison(
    scene_graph: SceneGraph,
    profile: FrameProfile,
    measurements: dict[str, TextMeasurement],
) -> LayoutGraph:
    title_nodes = [node for node in scene_graph.nodes if node.semantic_role == "COMPARISON_TOPIC"]
    columns = [node for node in scene_graph.nodes if node.semantic_role == "COMPARISON_COLUMN"]
    if len(title_nodes) != 1 or len(columns) < 2:
        raise LayoutUnsatisfiableError("Comparison specialized layout requires one topic and at least two columns")
    title = title_nodes[0]
    title_zone = profile.get_zone("TITLE")
    content = profile.get_zone("CONTENT")
    gap = max(10.0, profile.width * 0.025)
    col_count = len(columns)
    col_w = (content.width - gap * (col_count - 1)) / col_count
    if col_w <= 40:
        raise LayoutUnsatisfiableError("Comparison columns cannot fit content region")

    title_m = measurements[title.id]
    boxes: list[LayoutBox] = [
        LayoutBox(
            node_id=title.id,
            rect=_fit_rect(
                title_zone,
                preferred_width=min(title_zone.width - 8.0, title_m.width + 36.0),
                preferred_height=min(
                    title_zone.height - 4.0,
                    max(38.0, _wrapped_text_height(title_m, min(title_zone.width - 8.0, title_m.width + 36.0)) + 16.0),
                ),
                preferred_region=title.layout_hint.preferred_region if title.layout_hint else None,
            ),
            zone="TITLE",
            strategy_role="title",
            semantic_key=title.semantic_key,
        )
    ]

    columns = sorted(columns, key=lambda n: ((n.layout_hint.preferred_order if n.layout_hint and n.layout_hint.preferred_order is not None else 9999), n.id))
    for idx, column in enumerate(columns):
        x = content.x + idx * (col_w + gap)
        col_zone = Rect(x=round(x, 4), y=content.y, width=round(col_w, 4), height=content.height)
        members = _column_members(scene_graph, column.id)
        column_width = min(col_zone.width - 16.0, measurements[column.id].width + 24.0)
        column_required_h = _wrapped_text_height(measurements[column.id], column_width) + 16.0
        col_title_h = min(max(38.0, column_required_h + 4.0), col_zone.height * 0.30)
        if column_required_h > col_title_h + 1e-6:
            raise LayoutUnsatisfiableError(
                f"Comparison column '{column.id}' title cannot fit readable text"
            )
        title_slot = Rect(x=col_zone.x, y=col_zone.y, width=col_zone.width, height=col_title_h)
        boxes.append(
            LayoutBox(
                node_id=column.id,
                rect=_fit_rect(
                    title_slot,
                    preferred_width=column_width,
                    preferred_height=column_required_h,
                    preferred_region=column.layout_hint.preferred_region if column.layout_hint else None,
                ),
                zone="CONTENT",
                strategy_role="comparison_column",
                semantic_key=column.semantic_key,
            )
        )
        body_y = col_zone.y + col_title_h + 6.0
        body = Rect(
            x=col_zone.x,
            y=round(body_y, 4),
            width=col_zone.width,
            height=round(max(1.0, col_zone.bottom - body_y), 4),
        )
        boxes.extend(_stack_in_zone(members, measurements, body, gap=6.0, zone_name="CONTENT"))

    covered = {box.node_id for box in boxes}
    extras = [node for node in scene_graph.nodes if node.id not in covered]
    if extras:
        raise LayoutUnsatisfiableError(
            "Comparison specialized layout found unsupported ungrouped nodes",
            {"node_ids": sorted(node.id for node in extras)},
        )

    graph = LayoutGraph(
        scene_id=scene_graph.scene_id,
        frame_profile_id=profile.id,
        frame_width=profile.width,
        frame_height=profile.height,
        boxes=boxes,
        routed_edges=[],
        strategy=LayoutStrategy.COMPARISON,
        feasible=True,
        metadata={"router": "specialized_comparison_v1"},
    )
    validate_layout_graph(
        graph,
        profile=profile,
        measurements={nid: (m.minimum_readable_width, m.minimum_readable_height) for nid, m in measurements.items()},
        expected_node_ids={n.id for n in scene_graph.nodes},
    )
    return graph


def compile_scene_layout(
    scene_graph: SceneGraph,
    *,
    profile: FrameProfile | None = None,
    graph_backend: GraphBackendKind = GraphBackendKind.GRAPHVIZ,
    measurement_policy: MeasurementPolicy | None = None,
) -> LayoutGraph:
    """Compile a semantic SceneGraph into one deterministic LayoutGraph.

    Routing policy follows PLAN_V2:
      PROCESS/CAUSAL/HIERARCHY/FLOW -> graph backend
      COMPARISON -> specialized comparison layout
      CONCEPT_CARD -> specialized card layout
    """
    scene_graph = SceneGraph.model_validate(scene_graph.model_dump(mode="json"))
    profile = profile or create_frame_profile_16_9(1280.0, 720.0)
    measurements = measure_scene_nodes(scene_graph, policy=measurement_policy)

    intent = scene_graph.layout_intent.type
    if intent in {LayoutIntent.PROCESS, LayoutIntent.HIERARCHY}:
        try:
            graph = layout_directed_graph(
                scene_graph,
                measurements,
                profile,
                backend=graph_backend,
            )
            validate_layout_graph(
                graph,
                profile=profile,
                measurements={nid: (m.minimum_readable_width, m.minimum_readable_height) for nid, m in measurements.items()},
                expected_node_ids={n.id for n in scene_graph.nodes},
            )
            return graph
        except LayoutUnsatisfiableError:
            if intent == LayoutIntent.PROCESS:
                return _compile_process_compact(scene_graph, profile, measurements)
            raise
    if intent == LayoutIntent.COMPARISON:
        return _compile_comparison(scene_graph, profile, measurements)
    if intent == LayoutIntent.CONCEPT_CARD:
        return _compile_concept_card(scene_graph, profile, measurements)
    raise LayoutUnsatisfiableError(
        f"No production V2 LayoutRouter strategy for layout intent '{intent.value}'"
    )
