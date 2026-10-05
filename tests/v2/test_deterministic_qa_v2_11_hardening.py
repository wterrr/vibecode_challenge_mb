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

def test_fixture_evaluator_counts_missing_expected_code_as_miss():
    result = QAFixtureResult(
        fixture_id="miss",
        expected_issue_codes=(QAIssueCode.BLANK_FRAME,),
        report=analyze_deterministic_qa(_good_layout(), _good_probe()),
    )
    evaluation = evaluate_fixture_results((result,))
    assert evaluation.detection_rate == 0.0
    assert evaluation.missed_broken_fixtures == ("miss",)


def test_fixture_evaluator_measures_false_positive_case_rate():
    issue = QAIssue(issue_id="MIN_FONT_SIZE:x", code=QAIssueCode.MIN_FONT_SIZE, message="bad")
    report = DeterministicQAReport(scene_id="s", passed=False, issues=(issue,))
    evaluation = evaluate_fixture_results((QAFixtureResult(fixture_id="good", expected_issue_codes=(), report=report),))
    assert evaluation.false_positive_rate == 1.0
    assert evaluation.false_positive_fixtures == ("good",)


def test_fixture_evaluator_rejects_duplicate_ids_and_empty_input():
    with pytest.raises(QAInvalidInputError):
        evaluate_fixture_results(())
    good = QAFixtureResult(
        fixture_id="same",
        expected_issue_codes=(),
        report=analyze_deterministic_qa(_good_layout(), _good_probe()),
    )
    with pytest.raises(QAInvalidInputError):
        evaluate_fixture_results((good, good))


def test_single_audio_spike_does_not_hide_mostly_silent_track():
    windows = (0.1,) + (0.0,) * 99
    probe = _good_probe(audio=AudioProbe(duration=5.0, rms_windows=windows, expected_audio=True))
    report = analyze_deterministic_qa(_good_layout(), probe)
    assert QAIssueCode.AUDIO_SILENCE in _codes(report)


def test_routed_edge_missing_endpoint_node_is_invalid_geometry():
    edge = RoutedEdge(
        edge_id="ghost_edge",
        source="ghost",
        target="n1",
        points=[Point(x=100.0, y=200.0), Point(x=180.0, y=220.0)],
        routing_style=RoutingStyle.POLYLINE,
        backend=GraphBackendKind.GRAPHVIZ,
    )
    layout = _layout(*_good_layout().boxes, routed_edges=(edge,))
    report = analyze_deterministic_qa(layout, _good_probe())
    assert QAIssueCode.INVALID_GEOMETRY in _codes(report)


def test_fixture_evaluation_rejects_duplicate_metric_fixture_ids():
    from learnflow_v2.qa import QAFixtureEvaluation
    with pytest.raises((QAInvalidInputError, ValidationError)):
        QAFixtureEvaluation(
            total_fixtures=2, broken_fixtures=2, good_fixtures=0,
            detected_broken_fixtures=0, missed_broken_fixtures=("x", "x"),
            false_positive_fixtures=(), detection_rate=0.0, false_positive_rate=0.0,
        )


def test_public_probe_boolean_fields_are_strict():
    with pytest.raises((QAInvalidInputError, ValidationError)):
        AssetProbe(asset_id="a", required=1, exists=True)
    with pytest.raises((QAInvalidInputError, ValidationError)):
        FrameProbe(timestamp=0.0, mean_luma=1.0, non_black_fraction=0.1, expected_blank="false")
    with pytest.raises((QAInvalidInputError, ValidationError)):
        AudioProbe(duration=1.0, rms_windows=(0.1,), expected_audio=1)


def test_fixture_result_rejects_duplicate_expected_issue_codes():
    with pytest.raises((QAInvalidInputError, ValidationError)):
        QAFixtureResult(
            fixture_id="dup",
            expected_issue_codes=(QAIssueCode.BLANK_FRAME, QAIssueCode.BLANK_FRAME),
            report=analyze_deterministic_qa(_good_layout(), _good_probe()),
        )


def test_fixture_evaluation_counts_are_strict_and_false_positive_count_bounded():
    from learnflow_v2.qa import QAFixtureEvaluation
    with pytest.raises((QAInvalidInputError, ValidationError)):
        QAFixtureEvaluation(
            total_fixtures=True,
            broken_fixtures=0,
            good_fixtures=1,
            detected_broken_fixtures=0,
            detection_rate=1.0,
            false_positive_rate=0.0,
        )
    with pytest.raises((QAInvalidInputError, ValidationError)):
        QAFixtureEvaluation(
            total_fixtures=1,
            broken_fixtures=1,
            good_fixtures=0,
            detected_broken_fixtures=1,
            false_positive_fixtures=("not_a_good_fixture",),
            detection_rate=1.0,
            false_positive_rate=0.0,
        )


def test_invalid_routed_edge_geometry_is_detected():
    edge = RoutedEdge(
        edge_id="bad_ref",
        source="n1",
        target="ghost",
        points=[Point(x=440.0, y=280.0), Point(x=620.0, y=280.0)],
        routing_style=RoutingStyle.ORTHOGONAL,
        backend=GraphBackendKind.GRAPHVIZ,
    )
    layout = _layout(
        _box("n1", 180.0, 220.0, 260.0, 120.0),
        _box("n2", 620.0, 220.0, 260.0, 120.0),
        strategy=LayoutStrategy.DIRECTED_GRAPH,
        routed_edges=(edge,),
    )
    report = analyze_deterministic_qa(layout, _good_probe())
    assert QAIssueCode.INVALID_GEOMETRY in _codes(report)


def test_infeasible_layout_cannot_pass_deterministic_qa():
    layout = _good_layout().model_copy(update={"feasible": False})
    report = analyze_deterministic_qa(layout, _good_probe())
    assert report.passed is False
    assert QAIssueCode.INVALID_GEOMETRY in _codes(report)


@pytest.mark.parametrize(
    "measurements",
    [
        {"n1": (float("nan"), 10.0)},
        {"n1": (-1.0, 10.0)},
        {"n1": (10.0,)},
        {"ghost": (10.0, 10.0)},
    ],
)
def test_malformed_or_stale_measurements_rejected(measurements):
    with pytest.raises(QAInvalidInputError):
        analyze_deterministic_qa(_good_layout(), _good_probe(), measurements=measurements)


def test_expected_node_ids_input_is_strict():
    with pytest.raises(QAInvalidInputError):
        analyze_deterministic_qa(_good_layout(), _good_probe(), expected_node_ids="n1")
    with pytest.raises(QAInvalidInputError):
        analyze_deterministic_qa(_good_layout(), _good_probe(), expected_node_ids=["n1", "n1"])


def test_config_input_must_be_validated_artifact():
    with pytest.raises(QAInvalidInputError):
        analyze_deterministic_qa(_good_layout(), _good_probe(), config={"min_font_size_px": 18})
