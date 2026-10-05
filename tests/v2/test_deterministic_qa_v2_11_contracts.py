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

def test_scene_id_mismatch_rejected():
    with pytest.raises(QAInvalidInputError):
        analyze_deterministic_qa(_good_layout("a"), _good_probe("b"))


def test_expected_audio_requires_samples():
    with pytest.raises((QAInvalidInputError, ValidationError)):
        AudioProbe(duration=1.0, rms_windows=(), expected_audio=True)


def test_probe_rejects_nan_and_infinity():
    with pytest.raises((QAInvalidInputError, ValidationError)):
        FrameProbe(timestamp=0.0, mean_luma=float("nan"), non_black_fraction=0.0)
    with pytest.raises((QAInvalidInputError, ValidationError)):
        TextElementProbe(element_id="x", font_size_px=float("inf"))


def test_duplicate_probe_identifiers_rejected():
    with pytest.raises((QAInvalidInputError, ValidationError)):
        _good_probe(
            assets=(
                AssetProbe(asset_id="same", exists=True),
                AssetProbe(asset_id="same", exists=True),
            )
        )


def test_issue_evidence_is_deeply_immutable_and_json_safe():
    issue = QAIssue(
        issue_id="INVALID_GEOMETRY:1",
        code=QAIssueCode.INVALID_GEOMETRY,
        message="test",
        evidence={"nested": {"values": [1, 2]}},
    )
    with pytest.raises(TypeError):
        issue.evidence["x"] = 1
    with pytest.raises(TypeError):
        issue.evidence["nested"]["x"] = 1
    with pytest.raises(AttributeError):
        issue.evidence["nested"]["values"].append(3)
    with pytest.raises((QAInvalidInputError, ValidationError)):
        QAIssue(
            issue_id="INVALID_GEOMETRY:2",
            code=QAIssueCode.INVALID_GEOMETRY,
            message="test",
            evidence={"bad": {1, 2}},
        )


def test_report_passed_flag_cannot_contradict_error_issues():
    issue = QAIssue(issue_id="BBOX_OVERLAP:x", code=QAIssueCode.BBOX_OVERLAP, message="bad")
    with pytest.raises((QAInvalidInputError, ValidationError)):
        DeterministicQAReport(scene_id="s", passed=True, issues=(issue,))


def test_report_canonical_round_trip_and_determinism():
    layout = _layout(
        _box("b", 420.0, 240.0, 320.0, 120.0),
        _box("a", 200.0, 220.0, 320.0, 120.0),
    )
    probe = _good_probe(
        text_elements=(
            TextElementProbe(element_id="z", font_size_px=12),
            TextElementProbe(element_id="a", font_size_px=13),
        )
    )
    report1 = analyze_deterministic_qa(layout, probe)
    report2 = analyze_deterministic_qa(layout, probe)
    assert report1.to_canonical_json() == report2.to_canonical_json()
    restored = DeterministicQAReport.from_canonical_json(report1.to_canonical_json())
    assert restored == report1


def test_analyzer_does_not_mutate_source_artifacts():
    layout = _good_layout()
    probe = _good_probe()
    layout_before = canonical_json(layout)
    probe_before = canonical_json(probe)
    analyze_deterministic_qa(layout, probe)
    assert canonical_json(layout) == layout_before
    assert canonical_json(probe) == probe_before


def test_probe_requires_frame_and_explicit_audio_evidence():
    base = dict(
        scene_id="scene_qa",
        expected_duration=5.0,
        rendered_duration=5.0,
        text_elements=(),
        visual_elements=(),
        assets=(),
        subtitles=(),
    )
    with pytest.raises((QAInvalidInputError, ValidationError)):
        RenderedSceneProbe(**base, frames=(), audio=AudioProbe(duration=5.0, rms_windows=(), expected_audio=False))
    with pytest.raises((QAInvalidInputError, ValidationError, TypeError)):
        RenderedSceneProbe(**base, frames=(FrameProbe(timestamp=0.0, mean_luma=10.0, non_black_fraction=0.1),))


def test_probe_rejects_duplicate_or_out_of_range_frame_timestamps():
    with pytest.raises((QAInvalidInputError, ValidationError)):
        _good_probe(frames=(
            FrameProbe(timestamp=1.0, mean_luma=10.0, non_black_fraction=0.1),
            FrameProbe(timestamp=1.0, mean_luma=20.0, non_black_fraction=0.2),
        ))
    with pytest.raises((QAInvalidInputError, ValidationError)):
        _good_probe(frames=(FrameProbe(timestamp=6.0, mean_luma=10.0, non_black_fraction=0.1),))


def test_probe_rejects_all_samples_marked_expected_blank():
    with pytest.raises((QAInvalidInputError, ValidationError)):
        _good_probe(frames=(FrameProbe(
            timestamp=0.0, mean_luma=0.0, non_black_fraction=0.0, expected_blank=True
        ),))


def test_audio_non_silent_fraction_cannot_be_zero_config():
    with pytest.raises(ValidationError):
        DeterministicQAConfig(min_non_silent_audio_fraction=0.0)

def test_issue_id_must_be_namespaced_by_code():
    with pytest.raises((QAInvalidInputError, ValidationError)):
        QAIssue(issue_id="wrong", code=QAIssueCode.BBOX_OVERLAP, message="bad")


def test_fixture_evaluation_artifact_rejects_inconsistent_rates():
    from learnflow_v2.qa import QAFixtureEvaluation
    with pytest.raises((QAInvalidInputError, ValidationError)):
        QAFixtureEvaluation(
            total_fixtures=2,
            broken_fixtures=1,
            good_fixtures=1,
            detected_broken_fixtures=1,
            missed_broken_fixtures=(),
            false_positive_fixtures=(),
            detection_rate=0.5,
            false_positive_rate=0.0,
        )
