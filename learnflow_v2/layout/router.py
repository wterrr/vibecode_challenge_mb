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
    Rect,
)
from learnflow_v2.scenegraph.enums import LayoutIntent, NodeKind, RelationKind
from learnflow_v2.scenegraph.schema import SceneGraph, SceneNode


_DEFAULT_POLICY = MeasurementPolicy(
    preferred_font_size=18.0,
    minimum_font_size=14.0,
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


def _fit_rect(
    zone: Rect,
    *,
    preferred_width: float,
    preferred_height: float,
    margin_x: float = 8.0,
    margin_y: float = 4.0,
) -> Rect:
    width = min(max(24.0, preferred_width), max(24.0, zone.width - margin_x * 2.0))
    height = min(max(20.0, preferred_height), max(20.0, zone.height - margin_y * 2.0))
    return Rect(
        x=round(zone.x + (zone.width - width) / 2.0, 4),
        y=round(zone.y + (zone.height - height) / 2.0, 4),
        width=round(width, 4),
        height=round(height, 4),
    )


def _stack_in_zone(
    nodes: Iterable[SceneNode],
    measurements: dict[str, TextMeasurement],
    zone: Rect,
    *,
    gap: float,
    zone_name: str,
) -> list[LayoutBox]:
    ordered = list(nodes)
    if not ordered:
        return []
    available = zone.height - gap * (len(ordered) - 1)
    if available <= 0:
        raise LayoutUnsatisfiableError("Not enough vertical space for stacked layout")
    slot_h = available / len(ordered)
    boxes: list[LayoutBox] = []
    for index, node in enumerate(ordered):
        measurement = measurements[node.id]
        if measurement.minimum_readable_height > slot_h + 1e-6:
            raise LayoutUnsatisfiableError(
                f"Node '{node.id}' minimum readable height does not fit specialized layout",
                {"minimum_height": measurement.minimum_readable_height, "slot_height": slot_h},
            )
        y = zone.y + index * (slot_h + gap)
        slot = Rect(x=zone.x, y=round(y, 4), width=zone.width, height=round(slot_h, 4))
        rect = _fit_rect(
            slot,
            preferred_width=min(measurement.width + 28.0, slot.width),
            preferred_height=max(measurement.minimum_readable_height + 12.0, min(measurement.height + 12.0, slot.height)),
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
    title_box = LayoutBox(
        node_id=primary_node.id,
        rect=_fit_rect(
            title_zone,
            preferred_width=min(title_zone.width, title_m.width + 36.0),
            preferred_height=min(title_zone.height, max(26.0, title_m.height + 14.0)),
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
                preferred_width=min(title_zone.width, title_m.width + 36.0),
                preferred_height=min(title_zone.height, max(26.0, title_m.height + 14.0)),
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
        col_title_h = min(max(34.0, measurements[column.id].minimum_readable_height + 14.0), col_zone.height * 0.25)
        title_slot = Rect(x=col_zone.x, y=col_zone.y, width=col_zone.width, height=col_title_h)
        boxes.append(
            LayoutBox(
                node_id=column.id,
                rect=_fit_rect(
                    title_slot,
                    preferred_width=min(col_zone.width, measurements[column.id].width + 20.0),
                    preferred_height=min(col_title_h, measurements[column.id].height + 12.0),
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
    if intent == LayoutIntent.COMPARISON:
        return _compile_comparison(scene_graph, profile, measurements)
    if intent == LayoutIntent.CONCEPT_CARD:
        return _compile_concept_card(scene_graph, profile, measurements)
    raise LayoutUnsatisfiableError(
        f"No production V2 LayoutRouter strategy for layout intent '{intent.value}'"
    )
