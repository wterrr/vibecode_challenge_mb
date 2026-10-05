"""Deterministic, renderer-independent QA analyzer for LearnFlow V2 CP2.11."""

from __future__ import annotations

import math
from typing import Iterable

from learnflow_v2.qa.errors import QAInvalidInputError
from learnflow_v2.layout.collision import detect_box_collisions
from learnflow_v2.layout.graph_metrics import compute_graph_metrics
from learnflow_v2.layout.preflight import validate_graph_layout, validate_layout_graph
from learnflow_v2.layout.profiles import get_frame_profile
from learnflow_v2.layout.schema import FrameProfile, LayoutGraph, LayoutStrategy
from learnflow_v2.qa.schema import (
    DeterministicQAConfig,
    DeterministicQAReport,
    QAIssue,
    QAIssueCode,
    QAIssueSeverity,
    RenderedSceneProbe,
)


def _issue(
    code: QAIssueCode,
    suffix: str,
    message: str,
    *,
    object_ids: Iterable[str] = (),
    evidence: dict | None = None,
    severity: QAIssueSeverity = QAIssueSeverity.ERROR,
) -> QAIssue:
    ids = tuple(sorted(set(object_ids)))
    stable_suffix = suffix or ("__".join(ids) if ids else "scene")
    return QAIssue(
        issue_id=f"{code.value}:{stable_suffix}",
        code=code,
        severity=severity,
        message=message,
        object_ids=ids,
        evidence=evidence or {},
    )


def _validate_measurements(
    layout_graph: LayoutGraph,
    measurements: dict[str, tuple[float, float]] | None,
) -> dict[str, tuple[float, float]] | None:
    if measurements is None:
        return None
    if not isinstance(measurements, dict):
        raise QAInvalidInputError("measurements must be a dict mapping node_id to (width, height)")
    layout_ids = {box.node_id for box in layout_graph.boxes}
    normalized: dict[str, tuple[float, float]] = {}
    for node_id, value in measurements.items():
        if not isinstance(node_id, str) or not node_id:
            raise QAInvalidInputError("measurement keys must be non-empty node IDs")
        if node_id not in layout_ids:
            raise QAInvalidInputError(f"measurement references unknown layout node '{node_id}'")
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise QAInvalidInputError(f"measurement for '{node_id}' must be a (width, height) pair")
        width, height = value
        for field, number in (("width", width), ("height", height)):
            if isinstance(number, bool) or not isinstance(number, (int, float)):
                raise QAInvalidInputError(f"measurement {field} for '{node_id}' must be numeric")
            numeric = float(number)
            if not math.isfinite(numeric) or numeric < 0.0:
                raise QAInvalidInputError(
                    f"measurement {field} for '{node_id}' must be finite and non-negative"
                )
        normalized[node_id] = (float(width), float(height))
    return normalized


def _validate_expected_node_ids(expected_node_ids: set[str] | list[str] | None) -> set[str] | None:
    if expected_node_ids is None:
        return None
    if not isinstance(expected_node_ids, (set, list, tuple)):
        raise QAInvalidInputError("expected_node_ids must be a set/list/tuple of node IDs")
    values = list(expected_node_ids)
    if any(not isinstance(value, str) or not value for value in values):
        raise QAInvalidInputError("expected_node_ids must contain non-empty strings")
    if len(values) != len(set(values)):
        raise QAInvalidInputError("expected_node_ids cannot contain duplicates")
    return set(values)


def analyze_deterministic_qa(
    layout_graph: LayoutGraph,
    rendered_probe: RenderedSceneProbe,
    *,
    measurements: dict[str, tuple[float, float]] | None = None,
    expected_node_ids: set[str] | list[str] | None = None,
    config: DeterministicQAConfig | None = None,
    profile: FrameProfile | str | None = None,
) -> DeterministicQAReport:
    """Run the deterministic QA gate before any optional VLM critic.

    The function is pure with respect to all input artifacts. It consumes solved
    geometry plus renderer-neutral numeric probes; it never calls an LLM/VLM,
    modifies layout/motion state, or performs repair.
    """
    if not isinstance(layout_graph, LayoutGraph):
        raise QAInvalidInputError("layout_graph must be a LayoutGraph")
    if not isinstance(rendered_probe, RenderedSceneProbe):
        raise QAInvalidInputError("rendered_probe must be a RenderedSceneProbe")
    if rendered_probe.scene_id != layout_graph.scene_id:
        raise QAInvalidInputError(
            f"rendered probe scene_id '{rendered_probe.scene_id}' does not match layout scene_id '{layout_graph.scene_id}'"
        )

    if config is not None and not isinstance(config, DeterministicQAConfig):
        raise QAInvalidInputError("config must be a DeterministicQAConfig")
    cfg = config or DeterministicQAConfig()
    normalized_measurements = _validate_measurements(layout_graph, measurements)
    normalized_expected_node_ids = _validate_expected_node_ids(expected_node_ids)
    frame_profile = get_frame_profile(profile or layout_graph.frame_profile_id)
    issues: list[QAIssue] = []

    if not layout_graph.feasible:
        issues.append(_issue(
            QAIssueCode.INVALID_GEOMETRY,
            "layout_feasibility",
            "LayoutGraph is marked infeasible and cannot pass deterministic QA",
            evidence={"feasible": False},
        ))

    preflight = validate_layout_graph(
        layout_graph,
        profile=frame_profile,
        measurements=normalized_measurements,
        expected_node_ids=normalized_expected_node_ids,
        tol=cfg.layout_tolerance,
        raise_on_error=False,
    )
    if preflight.frame_overflow_count:
        issues.append(_issue(QAIssueCode.FRAME_OVERFLOW, "layout", f"Layout has {preflight.frame_overflow_count} frame overflow violation(s)", evidence={"count": preflight.frame_overflow_count}))
    if preflight.safe_zone_violation_count:
        issues.append(_issue(QAIssueCode.SAFE_ZONE_VIOLATION, "layout", f"Layout has {preflight.safe_zone_violation_count} safe-zone violation(s)", evidence={"count": preflight.safe_zone_violation_count}))
    if preflight.content_clipping_count:
        issues.append(_issue(QAIssueCode.CONTENT_CLIPPING, "layout", f"Layout has {preflight.content_clipping_count} content clipping violation(s)", evidence={"count": preflight.content_clipping_count}))
    if preflight.invalid_geometry_count or preflight.missing_node_count:
        issues.append(_issue(QAIssueCode.INVALID_GEOMETRY, "layout", "Layout has invalid or missing geometry", evidence={"invalid_geometry_count": preflight.invalid_geometry_count, "missing_node_count": preflight.missing_node_count}))

    for collision in detect_box_collisions(layout_graph, tol=cfg.layout_tolerance):
        issues.append(_issue(QAIssueCode.BBOX_OVERLAP, f"{collision.first_node_id}__{collision.second_node_id}", f"Bounding boxes '{collision.first_node_id}' and '{collision.second_node_id}' overlap", object_ids=(collision.first_node_id, collision.second_node_id), evidence={"overlap_width": collision.overlap_width, "overlap_height": collision.overlap_height, "overlap_area": collision.overlap_area}))

    if layout_graph.routed_edges:
        box_map = {box.node_id: box.rect for box in layout_graph.boxes}
        invalid_edge_refs = [edge.edge_id for edge in layout_graph.routed_edges if edge.source not in box_map or edge.target not in box_map]
        if invalid_edge_refs:
            issues.append(_issue(QAIssueCode.INVALID_GEOMETRY, "edge_refs", "Routed edges reference missing source/target nodes", object_ids=tuple(invalid_edge_refs), evidence={"edge_ids": sorted(invalid_edge_refs)}))
        edge_metrics = compute_graph_metrics(layout_graph.routed_edges, box_map)
        if edge_metrics.edge_node_intersection_count:
            issues.append(_issue(QAIssueCode.EDGE_NODE_INTERSECTION, "routed_edges", f"{edge_metrics.edge_node_intersection_count} routed edge(s) intersect unrelated nodes", evidence={"count": edge_metrics.edge_node_intersection_count}))

    if layout_graph.strategy == LayoutStrategy.DIRECTED_GRAPH:
        graph_report = validate_graph_layout(layout_graph, profile=frame_profile, tol=cfg.layout_tolerance, raise_on_error=False)
        if graph_report.endpoint_violation_count or graph_report.orthogonal_violation_count:
            issues.append(_issue(QAIssueCode.INVALID_GEOMETRY, "routed_edges", "Routed graph has invalid endpoint or orthogonality geometry", evidence={"endpoint_violation_count": graph_report.endpoint_violation_count, "orthogonal_violation_count": graph_report.orthogonal_violation_count}))

    for text in rendered_probe.text_elements:
        if text.font_size_px < cfg.min_font_size_px:
            issues.append(_issue(QAIssueCode.MIN_FONT_SIZE, text.element_id, f"Text element '{text.element_id}' font size {text.font_size_px}px is below {cfg.min_font_size_px}px", object_ids=(text.element_id,), evidence={"font_size_px": text.font_size_px, "minimum_px": cfg.min_font_size_px}))
        if not 0.0 <= text.alpha <= 1.0:
            issues.append(_issue(QAIssueCode.INVALID_ALPHA, text.element_id, f"Text element '{text.element_id}' has invalid alpha {text.alpha}", object_ids=(text.element_id,), evidence={"alpha": text.alpha}))
    for visual in rendered_probe.visual_elements:
        if not 0.0 <= visual.alpha <= 1.0:
            issues.append(_issue(QAIssueCode.INVALID_ALPHA, visual.element_id, f"Visual element '{visual.element_id}' has invalid alpha {visual.alpha}", object_ids=(visual.element_id,), evidence={"alpha": visual.alpha}))

    for asset in rendered_probe.assets:
        if asset.required and not asset.exists:
            issues.append(_issue(QAIssueCode.MISSING_ASSET, asset.asset_id, f"Required asset '{asset.asset_id}' is missing", object_ids=(asset.asset_id,)))

    if abs(rendered_probe.rendered_duration - rendered_probe.expected_duration) > cfg.duration_tolerance_seconds:
        issues.append(_issue(QAIssueCode.DURATION_MISMATCH, "rendered_expected", "Rendered duration does not match expected scene duration", evidence={"rendered_duration": rendered_probe.rendered_duration, "expected_duration": rendered_probe.expected_duration, "tolerance_seconds": cfg.duration_tolerance_seconds}))
    audio = rendered_probe.audio
    if abs(audio.duration - rendered_probe.rendered_duration) > cfg.duration_tolerance_seconds:
        issues.append(_issue(QAIssueCode.DURATION_MISMATCH, "audio_video", "Audio duration does not match rendered scene duration", evidence={"audio_duration": audio.duration, "rendered_duration": rendered_probe.rendered_duration, "tolerance_seconds": cfg.duration_tolerance_seconds}))
    if audio.expected_audio:
        non_silent_count = sum(1 for rms in audio.rms_windows if rms > cfg.audio_silence_rms_threshold)
        non_silent_fraction = non_silent_count / len(audio.rms_windows)
        if non_silent_fraction < cfg.min_non_silent_audio_fraction:
            issues.append(_issue(QAIssueCode.AUDIO_SILENCE, "audio", "Expected scene audio is effectively silent across sampled RMS windows", evidence={"max_rms": max(audio.rms_windows, default=0.0), "rms_threshold": cfg.audio_silence_rms_threshold, "window_count": len(audio.rms_windows), "non_silent_fraction": non_silent_fraction, "minimum_non_silent_fraction": cfg.min_non_silent_audio_fraction}))

    for frame_index, frame in enumerate(rendered_probe.frames):
        if frame.expected_blank:
            continue
        if frame.mean_luma <= cfg.blank_mean_luma_threshold and frame.non_black_fraction <= cfg.blank_non_black_fraction_threshold:
            issues.append(_issue(QAIssueCode.BLANK_FRAME, f"{frame_index:06d}_{frame.timestamp:.9f}", f"Unexpected blank/black sampled frame at {frame.timestamp:.3f}s", evidence={"timestamp": frame.timestamp, "mean_luma": frame.mean_luma, "non_black_fraction": frame.non_black_fraction, "mean_luma_threshold": cfg.blank_mean_luma_threshold, "non_black_fraction_threshold": cfg.blank_non_black_fraction_threshold}))

    caption_zone = frame_profile.get_zone("CAPTION")
    for cue in rendered_probe.subtitles:
        temporal_bad = cue.start_time < 0.0 or cue.end_time > rendered_probe.rendered_duration + cfg.duration_tolerance_seconds
        geometry_bad = not caption_zone.contains_rect(cue.rect, tol=cfg.layout_tolerance)
        if temporal_bad or geometry_bad:
            issues.append(_issue(QAIssueCode.SUBTITLE_BOUNDS, cue.cue_id, f"Subtitle cue '{cue.cue_id}' exceeds temporal or caption-safe bounds", object_ids=(cue.cue_id,), evidence={"temporal_bad": temporal_bad, "geometry_bad": geometry_bad, "start_time": cue.start_time, "end_time": cue.end_time, "rendered_duration": rendered_probe.rendered_duration}))

    ordered = tuple(sorted(issues, key=lambda item: item.issue_id))
    return DeterministicQAReport(scene_id=layout_graph.scene_id, passed=not any(issue.severity == QAIssueSeverity.ERROR for issue in ordered), issues=ordered)
