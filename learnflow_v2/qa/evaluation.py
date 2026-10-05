"""Fixture-corpus evaluation helpers for deterministic QA acceptance metrics."""

from __future__ import annotations

from learnflow_v2.qa.errors import QAInvalidInputError
from learnflow_v2.qa.schema import QAFixtureEvaluation, QAFixtureResult


def evaluate_fixture_results(results: tuple[QAFixtureResult, ...] | list[QAFixtureResult]) -> QAFixtureEvaluation:
    """Measure case-level detection rate and false-positive rate.

    A broken fixture is detected only when all expected deterministic issue codes
    are present in its report. A known-good fixture is a false positive when the
    report contains any ERROR and therefore fails the gate.
    """
    if isinstance(results, list):
        results = tuple(results)
    if not isinstance(results, tuple) or not results:
        raise QAInvalidInputError("fixture evaluation requires at least one result")

    ids = [result.fixture_id for result in results]
    if len(ids) != len(set(ids)):
        raise QAInvalidInputError("fixture_id values must be unique")

    broken = [result for result in results if result.expected_issue_codes]
    good = [result for result in results if not result.expected_issue_codes]
    missed: list[str] = []
    false_positive: list[str] = []

    detected = 0
    for result in broken:
        actual = {issue.code for issue in result.report.issues}
        expected = set(result.expected_issue_codes)
        if expected.issubset(actual):
            detected += 1
        else:
            missed.append(result.fixture_id)

    for result in good:
        if not result.report.passed:
            false_positive.append(result.fixture_id)

    detection_rate = detected / len(broken) if broken else 1.0
    false_positive_rate = len(false_positive) / len(good) if good else 0.0

    return QAFixtureEvaluation(
        total_fixtures=len(results),
        broken_fixtures=len(broken),
        good_fixtures=len(good),
        detected_broken_fixtures=detected,
        missed_broken_fixtures=tuple(sorted(missed)),
        false_positive_fixtures=tuple(sorted(false_positive)),
        detection_rate=detection_rate,
        false_positive_rate=false_positive_rate,
    )
