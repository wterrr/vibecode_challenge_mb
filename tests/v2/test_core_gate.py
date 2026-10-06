from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from learnflow_v2.core_gate import (
    CoreGateError,
    CoreGateEvidence,
    CoreGateEvidenceBundle,
    CoreGateMetric,
    CoreGateState,
    CriterionState,
    EvidenceKind,
    evaluate_core_gate,
)

COMMIT = "a" * 40


def ev(metric, value, *, kind=EvidenceKind.BENCHMARK):
    kwargs = dict(metric=metric, kind=kind, value=value, source=("benchmark.json",))
    if kind == EvidenceKind.BENCHMARK:
        kwargs.update(sample_count=100, benchmark_id="bench-v1-v2")
    return CoreGateEvidence(**kwargs)


def complete_passing_bundle():
    return CoreGateEvidenceBundle(
        repo_commit=COMMIT,
        evidence=(
            ev(CoreGateMetric.RENDER_SUCCESS_RATE, 0.98),
            ev(CoreGateMetric.FATAL_CLIPPING_COUNT, 0),
            ev(CoreGateMetric.FATAL_OVERLAP_COUNT, 0),
            ev(CoreGateMetric.INVALID_MOTION_PLAN_COUNT, 0),
            ev(CoreGateMetric.SELECTIVE_REPAIR_SUCCESS_RATE, 0.90),
            ev(CoreGateMetric.REPRODUCIBILITY_RATE, 1.0),
            ev(CoreGateMetric.V1_V2_CRITICAL_REGRESSION_COUNT, 0),
            ev(CoreGateMetric.V2_STATIC_QUALITY_DELTA, 0.01),
            ev(CoreGateMetric.VLM_UNAVAILABLE_DETERMINISTIC_OK, True, kind=EvidenceKind.CONTRACT_TEST),
            ev(CoreGateMetric.LOCAL_REPAIR_SCOPE_OK, True, kind=EvidenceKind.CONTRACT_TEST),
        ),
    )


def test_complete_threshold_evidence_passes_core_gate():
    report = evaluate_core_gate(complete_passing_bundle())
    assert report.state == CoreGateState.PASS
    assert all(item.state == CriterionState.PASS for item in report.criteria)


def test_missing_evidence_is_blocked_never_implicitly_passed():
    report = evaluate_core_gate(CoreGateEvidenceBundle(repo_commit=COMMIT, evidence=()))
    assert report.state == CoreGateState.BLOCKED
    assert len([item for item in report.criteria if item.state == CriterionState.BLOCKED]) == 10


def test_repository_blocker_blocks_even_when_metrics_pass():
    report = evaluate_core_gate(complete_passing_bundle(), repository_blockers=("missing V2 renderer",))
    assert report.state == CoreGateState.BLOCKED


@pytest.mark.parametrize(
    "metric,value",
    [
        (CoreGateMetric.RENDER_SUCCESS_RATE, 0.9799),
        (CoreGateMetric.FATAL_CLIPPING_COUNT, 1),
        (CoreGateMetric.FATAL_OVERLAP_COUNT, 1),
        (CoreGateMetric.INVALID_MOTION_PLAN_COUNT, 1),
        (CoreGateMetric.SELECTIVE_REPAIR_SUCCESS_RATE, 0.8999),
        (CoreGateMetric.REPRODUCIBILITY_RATE, 0.9999),
        (CoreGateMetric.V1_V2_CRITICAL_REGRESSION_COUNT, 1),
        (CoreGateMetric.V2_STATIC_QUALITY_DELTA, 0.0),
    ],
)
def test_failed_benchmark_threshold_fails_gate(metric, value):
    bundle = complete_passing_bundle()
    records = [item for item in bundle.evidence if item.metric != metric]
    records.append(ev(metric, value))
    report = evaluate_core_gate(CoreGateEvidenceBundle(repo_commit=COMMIT, evidence=tuple(records)))
    assert report.state == CoreGateState.FAIL
    result = next(item for item in report.criteria if item.metric == metric)
    assert result.state == CriterionState.FAIL


def test_boolean_contract_failure_fails_gate():
    bundle = complete_passing_bundle()
    records = [item for item in bundle.evidence if item.metric != CoreGateMetric.LOCAL_REPAIR_SCOPE_OK]
    records.append(ev(CoreGateMetric.LOCAL_REPAIR_SCOPE_OK, False, kind=EvidenceKind.CONTRACT_TEST))
    assert evaluate_core_gate(CoreGateEvidenceBundle(repo_commit=COMMIT, evidence=tuple(records))).state == CoreGateState.FAIL


def test_benchmark_only_metric_rejects_contract_test_evidence():
    with pytest.raises((CoreGateError, ValidationError)):
        ev(CoreGateMetric.RENDER_SUCCESS_RATE, 1.0, kind=EvidenceKind.CONTRACT_TEST)


def test_benchmark_evidence_requires_sample_count_and_benchmark_id():
    with pytest.raises((CoreGateError, ValidationError)):
        CoreGateEvidence(metric=CoreGateMetric.RENDER_SUCCESS_RATE, kind=EvidenceKind.BENCHMARK, value=1.0, source=("x",))


def test_duplicate_metric_evidence_rejected():
    item = ev(CoreGateMetric.RENDER_SUCCESS_RATE, 1.0)
    with pytest.raises((CoreGateError, ValidationError)):
        CoreGateEvidenceBundle(repo_commit=COMMIT, evidence=(item, item))


def test_bool_cannot_smuggle_into_numeric_metric():
    bundle = complete_passing_bundle()
    records = [item for item in bundle.evidence if item.metric != CoreGateMetric.RENDER_SUCCESS_RATE]
    records.append(ev(CoreGateMetric.RENDER_SUCCESS_RATE, True))
    report = evaluate_core_gate(CoreGateEvidenceBundle(repo_commit=COMMIT, evidence=tuple(records)))
    assert report.state == CoreGateState.FAIL


def test_nonfinite_evidence_rejected():
    with pytest.raises((CoreGateError, ValidationError)):
        ev(CoreGateMetric.RENDER_SUCCESS_RATE, float("nan"))


def test_canonical_roundtrip_deterministic():
    bundle = complete_passing_bundle()
    assert CoreGateEvidenceBundle.from_canonical_json(bundle.to_canonical_json()) == bundle


def test_current_repository_evidence_is_explicitly_blocked():
    payload = json.loads(Path("benchmarks/core_gate/evidence.json").read_text(encoding="utf-8"))
    bundle = CoreGateEvidenceBundle.model_validate(payload)
    report = evaluate_core_gate(bundle)
    assert report.state == CoreGateState.BLOCKED
    passed = {item.metric for item in report.criteria if item.state == CriterionState.PASS}
    assert passed == {
        CoreGateMetric.VLM_UNAVAILABLE_DETERMINISTIC_OK,
        CoreGateMetric.LOCAL_REPAIR_SCOPE_OK,
    }


def test_cli_fails_closed_for_current_repository():
    proc = subprocess.run([sys.executable, "scripts/evaluate_v2_core_gate.py"], capture_output=True, text=True, check=False)
    assert proc.returncode == 2
    assert "Decision: BLOCKED" in proc.stdout
    assert "V2 renderer package/integration is missing" in proc.stdout


def test_model_construct_cannot_bypass_evidence_validation():
    forged = CoreGateEvidence.model_construct(
        metric=CoreGateMetric.RENDER_SUCCESS_RATE,
        kind=EvidenceKind.CONTRACT_TEST,
        value=True,
        source=("x",),
        sample_count=None,
        benchmark_id=None,
        notes="",
    )
    bundle = CoreGateEvidenceBundle.model_construct(schema_version="2.1", repo_commit=COMMIT, evidence=(forged,))
    with pytest.raises(Exception):
        evaluate_core_gate(bundle)


def test_repository_blocker_input_is_strict_and_canonical():
    report = evaluate_core_gate(complete_passing_bundle(), repository_blockers=(" b ", "a", "b"))
    assert report.blockers == ("a", "b")
    with pytest.raises(ValueError):
        evaluate_core_gate(complete_passing_bundle(), repository_blockers=("",))
