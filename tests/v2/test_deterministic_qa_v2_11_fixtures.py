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

def test_fixture_corpus_detects_every_known_broken_case_and_measures_fpr():
    good_layout = _good_layout()
    cases: list[QAFixtureResult] = []

    cases.append(QAFixtureResult(fixture_id="good_default", expected_issue_codes=(), report=analyze_deterministic_qa(good_layout, _good_probe())))
    cases.append(QAFixtureResult(
        fixture_id="good_dark",
        expected_issue_codes=(),
        report=analyze_deterministic_qa(
            good_layout,
            _good_probe(frames=(FrameProbe(timestamp=1.0, mean_luma=1.0, non_black_fraction=0.08),)),
        ),
    ))
    cases.append(QAFixtureResult(
        fixture_id="good_intentional_silence",
        expected_issue_codes=(),
        report=analyze_deterministic_qa(
            good_layout,
            _good_probe(audio=AudioProbe(duration=5.0, rms_windows=(), expected_audio=False)),
        ),
    ))
    cases.append(QAFixtureResult(
        fixture_id="good_expected_blank",
        expected_issue_codes=(),
        report=analyze_deterministic_qa(
            good_layout,
            _good_probe(frames=(FrameProbe(timestamp=0.0, mean_luma=0.0, non_black_fraction=0.0, expected_blank=True), FrameProbe(timestamp=1.0, mean_luma=18.0, non_black_fraction=0.08))),
        ),
    ))

    overlapping = _layout(_box("a", 200, 220, 300, 100), _box("b", 400, 220, 300, 100))
    cases.append(QAFixtureResult(
        fixture_id="broken_bbox",
        expected_issue_codes=(QAIssueCode.BBOX_OVERLAP,),
        report=analyze_deterministic_qa(overlapping, _good_probe()),
    ))
    cases.append(QAFixtureResult(
        fixture_id="broken_clipping",
        expected_issue_codes=(QAIssueCode.CONTENT_CLIPPING,),
        report=analyze_deterministic_qa(good_layout, _good_probe(), measurements={"n1": (999.0, 120.0)}),
    ))
    cases.append(QAFixtureResult(
        fixture_id="broken_safe_zone",
        expected_issue_codes=(QAIssueCode.SAFE_ZONE_VIOLATION,),
        report=analyze_deterministic_qa(_layout(_box("x", 10, 200, 100, 80)), _good_probe()),
    ))
    cases.append(QAFixtureResult(
        fixture_id="broken_frame_overflow",
        expected_issue_codes=(QAIssueCode.FRAME_OVERFLOW,),
        report=analyze_deterministic_qa(_layout(_box("x", 1230, 200, 80, 80)), _good_probe()),
    ))
    cases.append(QAFixtureResult(
        fixture_id="broken_font",
        expected_issue_codes=(QAIssueCode.MIN_FONT_SIZE,),
        report=analyze_deterministic_qa(good_layout, _good_probe(text_elements=(TextElementProbe(element_id="tiny", font_size_px=8),))),
    ))
    cases.append(QAFixtureResult(
        fixture_id="broken_duration",
        expected_issue_codes=(QAIssueCode.DURATION_MISMATCH,),
        report=analyze_deterministic_qa(good_layout, _good_probe(rendered_duration=4.0, audio=AudioProbe(duration=4.0, rms_windows=(0.1,)))),
    ))
    cases.append(QAFixtureResult(
        fixture_id="broken_audio",
        expected_issue_codes=(QAIssueCode.AUDIO_SILENCE,),
        report=analyze_deterministic_qa(good_layout, _good_probe(audio=AudioProbe(duration=5.0, rms_windows=(0.0, 0.0)))),
    ))
    cases.append(QAFixtureResult(
        fixture_id="broken_blank",
        expected_issue_codes=(QAIssueCode.BLANK_FRAME,),
        report=analyze_deterministic_qa(good_layout, _good_probe(frames=(FrameProbe(timestamp=1.0, mean_luma=0.0, non_black_fraction=0.0),))),
    ))
    cases.append(QAFixtureResult(
        fixture_id="broken_asset",
        expected_issue_codes=(QAIssueCode.MISSING_ASSET,),
        report=analyze_deterministic_qa(good_layout, _good_probe(assets=(AssetProbe(asset_id="missing", exists=False),))),
    ))
    cases.append(QAFixtureResult(
        fixture_id="broken_alpha",
        expected_issue_codes=(QAIssueCode.INVALID_ALPHA,),
        report=analyze_deterministic_qa(good_layout, _good_probe(visual_elements=(VisualElementProbe(element_id="v", alpha=1.2),))),
    ))

    edge = RoutedEdge(
        edge_id="e1", source="source", target="target",
        points=[Point(x=200.0, y=290.0), Point(x=700.0, y=290.0)],
        routing_style=RoutingStyle.ORTHOGONAL, backend=GraphBackendKind.GRAPHVIZ,
    )
    edge_layout = _layout(
        _box("source", 100.0, 250.0, 100.0, 80.0),
        _box("blocker", 400.0, 250.0, 100.0, 80.0),
        _box("target", 700.0, 250.0, 100.0, 80.0),
        strategy=LayoutStrategy.DIRECTED_GRAPH, routed_edges=(edge,),
    )
    cases.append(QAFixtureResult(
        fixture_id="broken_edge_node",
        expected_issue_codes=(QAIssueCode.EDGE_NODE_INTERSECTION,),
        report=analyze_deterministic_qa(edge_layout, _good_probe()),
    ))

    invalid_ref_edge = RoutedEdge(
        edge_id="bad_ref", source="source", target="ghost",
        points=[Point(x=200.0, y=290.0), Point(x=700.0, y=290.0)],
        routing_style=RoutingStyle.ORTHOGONAL, backend=GraphBackendKind.GRAPHVIZ,
    )
    invalid_geometry_layout = _layout(
        _box("source", 100.0, 250.0, 100.0, 80.0),
        _box("target", 700.0, 250.0, 100.0, 80.0),
        strategy=LayoutStrategy.DIRECTED_GRAPH, routed_edges=(invalid_ref_edge,),
    )
    cases.append(QAFixtureResult(
        fixture_id="broken_invalid_geometry",
        expected_issue_codes=(QAIssueCode.INVALID_GEOMETRY,),
        report=analyze_deterministic_qa(invalid_geometry_layout, _good_probe()),
    ))

    cases.append(QAFixtureResult(
        fixture_id="broken_subtitle",
        expected_issue_codes=(QAIssueCode.SUBTITLE_BOUNDS,),
        report=analyze_deterministic_qa(
            good_layout,
            _good_probe(subtitles=(SubtitleCueProbe(
                cue_id="s1", start_time=4.9, end_time=5.5,
                rect=Rect(x=200, y=200, width=300, height=50),
            ),)),
        ),
    ))

    assert {code for case in cases for code in case.expected_issue_codes} == set(QAIssueCode)

    evaluation = evaluate_fixture_results(cases)
    assert evaluation.broken_fixtures == 13
    assert evaluation.good_fixtures == 4
    assert evaluation.detected_broken_fixtures == 13
    assert evaluation.missed_broken_fixtures == ()
    assert evaluation.detection_rate == 1.0
    assert evaluation.false_positive_fixtures == ()
    assert evaluation.false_positive_rate == 0.0
