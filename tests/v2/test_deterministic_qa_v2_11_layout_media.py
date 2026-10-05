from __future__ import annotations

import math
import pytest
from pydantic import ValidationError

from learnflow_v2.qa.errors import QAInvalidInputError
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.layout.profiles import get_frame_profile
from learnflow_v2.layout.schema import (
    GraphBackendKind, LayoutStrategy, Point, Rect, RoutedEdge, RoutingStyle,
)
from learnflow_v2.qa import (
    AssetProbe, AudioProbe, DeterministicQAConfig, DeterministicQAReport, FrameProbe,
    QAFixtureResult, QAIssue, QAIssueCode, QAIssueSeverity, RenderedSceneProbe,
    SubtitleCueProbe, TextElementProbe, VisualElementProbe, analyze_deterministic_qa,
    evaluate_fixture_results,
)
from tests.v2.qa_v2_11_helpers import _box, _codes, _good_layout, _good_probe, _layout

def test_clean_scene_passes_deterministic_qa():
    report = analyze_deterministic_qa(_good_layout(), _good_probe())
    assert report.passed is True
    assert report.issues == ()


def test_bbox_overlap_detected():
    layout = _layout(
        _box("a", 200.0, 220.0, 320.0, 120.0),
        _box("b", 420.0, 240.0, 320.0, 120.0),
    )
    report = analyze_deterministic_qa(layout, _good_probe())
    assert QAIssueCode.BBOX_OVERLAP in _codes(report)


def test_content_clipping_detected_from_measurements():
    layout = _good_layout()
    report = analyze_deterministic_qa(layout, _good_probe(), measurements={"n1": (400.0, 120.0)})
    assert QAIssueCode.CONTENT_CLIPPING in _codes(report)


def test_safe_zone_and_frame_overflow_detected():
    layout = _layout(_box("bad", 1200.0, 200.0, 70.0, 100.0))
    report = analyze_deterministic_qa(layout, _good_probe())
    codes = _codes(report)
    assert QAIssueCode.SAFE_ZONE_VIOLATION in codes
    assert QAIssueCode.FRAME_OVERFLOW not in codes

    overflow = _layout(_box("bad", 1230.0, 200.0, 80.0, 100.0))
    report2 = analyze_deterministic_qa(overflow, _good_probe())
    assert QAIssueCode.FRAME_OVERFLOW in _codes(report2)


def test_edge_node_intersection_detected():
    boxes = (
        _box("source", 100.0, 250.0, 100.0, 80.0),
        _box("blocker", 400.0, 250.0, 100.0, 80.0),
        _box("target", 700.0, 250.0, 100.0, 80.0),
    )
    edge = RoutedEdge(
        edge_id="e1",
        source="source",
        target="target",
        points=[Point(x=200.0, y=290.0), Point(x=700.0, y=290.0)],
        routing_style=RoutingStyle.ORTHOGONAL,
        backend=GraphBackendKind.GRAPHVIZ,
    )
    layout = _layout(*boxes, strategy=LayoutStrategy.DIRECTED_GRAPH, routed_edges=(edge,))
    report = analyze_deterministic_qa(layout, _good_probe())
    assert QAIssueCode.EDGE_NODE_INTERSECTION in _codes(report)


def test_minimum_font_size_detected():
    probe = _good_probe(text_elements=(TextElementProbe(element_id="tiny", font_size_px=12.0),))
    report = analyze_deterministic_qa(_good_layout(), probe)
    assert QAIssueCode.MIN_FONT_SIZE in _codes(report)


def test_configurable_font_threshold():
    probe = _good_probe(text_elements=(TextElementProbe(element_id="small", font_size_px=17.0),))
    report = analyze_deterministic_qa(
        _good_layout(), probe, config=DeterministicQAConfig(min_font_size_px=16.0)
    )
    assert report.passed


@pytest.mark.parametrize("alpha", [-0.1, 1.1])
def test_invalid_alpha_detected(alpha):
    probe = _good_probe(visual_elements=(VisualElementProbe(element_id="v", alpha=alpha),))
    report = analyze_deterministic_qa(_good_layout(), probe)
    assert QAIssueCode.INVALID_ALPHA in _codes(report)


def test_missing_required_asset_detected_but_optional_missing_asset_allowed():
    probe = _good_probe(
        assets=(
            AssetProbe(asset_id="required", required=True, exists=False),
            AssetProbe(asset_id="optional", required=False, exists=False),
        )
    )
    report = analyze_deterministic_qa(_good_layout(), probe)
    missing = [issue for issue in report.issues if issue.code == QAIssueCode.MISSING_ASSET]
    assert len(missing) == 1
    assert missing[0].object_ids == ("required",)


def test_render_duration_mismatch_detected():
    probe = _good_probe(rendered_duration=4.5, audio=AudioProbe(duration=4.5, rms_windows=(0.1,)))
    report = analyze_deterministic_qa(_good_layout(), probe)
    assert QAIssueCode.DURATION_MISMATCH in _codes(report)


def test_audio_video_duration_mismatch_detected():
    probe = _good_probe(audio=AudioProbe(duration=4.5, rms_windows=(0.1,)))
    report = analyze_deterministic_qa(_good_layout(), probe)
    assert QAIssueCode.DURATION_MISMATCH in _codes(report)


def test_duration_tolerance_boundary_is_not_false_positive():
    probe = _good_probe(rendered_duration=5.05, audio=AudioProbe(duration=5.05, rms_windows=(0.1,)))
    report = analyze_deterministic_qa(
        _good_layout(), probe, config=DeterministicQAConfig(duration_tolerance_seconds=0.08)
    )
    assert QAIssueCode.DURATION_MISMATCH not in _codes(report)


def test_audio_silence_detected_when_audio_expected():
    probe = _good_probe(audio=AudioProbe(duration=5.0, rms_windows=(0.0, 0.0, 0.0), expected_audio=True))
    report = analyze_deterministic_qa(_good_layout(), probe)
    assert QAIssueCode.AUDIO_SILENCE in _codes(report)


def test_intentional_silent_scene_not_false_positive():
    probe = _good_probe(audio=AudioProbe(duration=5.0, rms_windows=(), expected_audio=False))
    report = analyze_deterministic_qa(_good_layout(), probe)
    assert QAIssueCode.AUDIO_SILENCE not in _codes(report)


def test_unexpected_blank_frame_detected():
    probe = _good_probe(frames=(FrameProbe(timestamp=2.0, mean_luma=0.1, non_black_fraction=0.0),))
    report = analyze_deterministic_qa(_good_layout(), probe)
    assert QAIssueCode.BLANK_FRAME in _codes(report)


def test_expected_blank_frame_is_not_false_positive():
    probe = _good_probe(frames=(
        FrameProbe(timestamp=0.0, mean_luma=0.0, non_black_fraction=0.0, expected_blank=True),
        FrameProbe(timestamp=1.0, mean_luma=18.0, non_black_fraction=0.08),
    ))
    report = analyze_deterministic_qa(_good_layout(), probe)
    assert QAIssueCode.BLANK_FRAME not in _codes(report)


def test_dark_background_with_visible_content_is_not_blank():
    probe = _good_probe(frames=(FrameProbe(timestamp=2.0, mean_luma=1.0, non_black_fraction=0.05),))
    report = analyze_deterministic_qa(_good_layout(), probe)
    assert QAIssueCode.BLANK_FRAME not in _codes(report)


def test_subtitle_temporal_bounds_detected():
    caption = get_frame_profile("16:9").get_zone("CAPTION")
    probe = _good_probe(subtitles=(SubtitleCueProbe(cue_id="s1", start_time=4.8, end_time=5.5, rect=caption),))
    report = analyze_deterministic_qa(_good_layout(), probe)
    assert QAIssueCode.SUBTITLE_BOUNDS in _codes(report)


def test_subtitle_caption_safe_zone_detected():
    probe = _good_probe(
        subtitles=(SubtitleCueProbe(cue_id="s1", start_time=1.0, end_time=2.0, rect=Rect(x=200, y=200, width=300, height=50)),)
    )
    report = analyze_deterministic_qa(_good_layout(), probe)
    assert QAIssueCode.SUBTITLE_BOUNDS in _codes(report)


def test_valid_subtitle_passes():
    caption = get_frame_profile("16:9").get_zone("CAPTION")
    cue_rect = Rect(x=caption.x + 20, y=caption.y + 10, width=caption.width - 40, height=caption.height - 20)
    probe = _good_probe(subtitles=(SubtitleCueProbe(cue_id="s1", start_time=1.0, end_time=2.0, rect=cue_rect),))
    report = analyze_deterministic_qa(_good_layout(), probe)
    assert QAIssueCode.SUBTITLE_BOUNDS not in _codes(report)
