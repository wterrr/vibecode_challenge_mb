"""Fail-closed LearnFlow V2 Core Gate evaluator."""

from __future__ import annotations

from collections.abc import Mapping

from learnflow_v2.core_gate.schema import (
    CoreGateEvidence,
    CoreGateEvidenceBundle,
    CoreGateMetric,
    CoreGateReport,
    CoreGateState,
    CriterionResult,
    CriterionState,
)


_REQUIREMENTS: dict[CoreGateMetric, str] = {
    CoreGateMetric.RENDER_SUCCESS_RATE: "Render success >= 98%",
    CoreGateMetric.FATAL_CLIPPING_COUNT: "Fatal clipping = 0",
    CoreGateMetric.FATAL_OVERLAP_COUNT: "Fatal overlap ~= 0 (operationalized conservatively as 0)",
    CoreGateMetric.INVALID_MOTION_PLAN_COUNT: "Invalid MotionPlan = 0",
    CoreGateMetric.SELECTIVE_REPAIR_SUCCESS_RATE: "Selective repair success >= 90%",
    CoreGateMetric.REPRODUCIBILITY_RATE: "Reproducibility = 100% for deterministic scenes",
    CoreGateMetric.V1_V2_CRITICAL_REGRESSION_COUNT: "V1→V2 regression = 0 critical product regressions",
    CoreGateMetric.V2_STATIC_QUALITY_DELTA: "V2 static quality > V1 baseline on the agreed benchmark",
    CoreGateMetric.VLM_UNAVAILABLE_DETERMINISTIC_OK: "VLM unavailable does not break deterministic mode",
    CoreGateMetric.LOCAL_REPAIR_SCOPE_OK: "Local repair does not rebuild unaffected scenes",
}


def _strict_number(evidence: CoreGateEvidence) -> float:
    if isinstance(evidence.value, bool):
        raise ValueError(f"{evidence.metric.value} requires numeric evidence")
    return float(evidence.value)


def _strict_bool(evidence: CoreGateEvidence) -> bool:
    if not isinstance(evidence.value, bool):
        raise ValueError(f"{evidence.metric.value} requires boolean evidence")
    return evidence.value


def _evaluate(evidence: CoreGateEvidence) -> bool:
    metric = evidence.metric
    if metric == CoreGateMetric.RENDER_SUCCESS_RATE:
        value = _strict_number(evidence)
        return 0.0 <= value <= 1.0 and value >= 0.98
    if metric in {
        CoreGateMetric.FATAL_CLIPPING_COUNT,
        CoreGateMetric.FATAL_OVERLAP_COUNT,
        CoreGateMetric.INVALID_MOTION_PLAN_COUNT,
        CoreGateMetric.V1_V2_CRITICAL_REGRESSION_COUNT,
    }:
        value = _strict_number(evidence)
        return value == 0.0
    if metric == CoreGateMetric.SELECTIVE_REPAIR_SUCCESS_RATE:
        value = _strict_number(evidence)
        return 0.0 <= value <= 1.0 and value >= 0.90
    if metric == CoreGateMetric.REPRODUCIBILITY_RATE:
        value = _strict_number(evidence)
        return 0.0 <= value <= 1.0 and value == 1.0
    if metric == CoreGateMetric.V2_STATIC_QUALITY_DELTA:
        return _strict_number(evidence) > 0.0
    if metric in {
        CoreGateMetric.VLM_UNAVAILABLE_DETERMINISTIC_OK,
        CoreGateMetric.LOCAL_REPAIR_SCOPE_OK,
    }:
        return _strict_bool(evidence)
    raise AssertionError(f"unhandled metric {metric}")


def evaluate_core_gate(
    bundle: CoreGateEvidenceBundle,
    *,
    repository_blockers: tuple[str, ...] = (),
) -> CoreGateReport:
    """Evaluate every PLAN_V2 Core Gate criterion. Missing evidence is BLOCKED, never PASS."""
    if not isinstance(bundle, CoreGateEvidenceBundle):
        raise ValueError("bundle must be CoreGateEvidenceBundle")
    # Revalidate public input so model_construct() cannot bypass evidence contracts.
    bundle = CoreGateEvidenceBundle.model_validate(bundle.model_dump(mode="json"))
    if not isinstance(repository_blockers, tuple):
        raise ValueError("repository_blockers must be a tuple")
    normalized_blockers: list[str] = []
    for blocker in repository_blockers:
        if not isinstance(blocker, str) or not blocker.strip():
            raise ValueError("repository_blockers must contain non-empty strings")
        normalized_blockers.append(blocker.strip())
    blockers = tuple(sorted(set(normalized_blockers)))

    index: Mapping[CoreGateMetric, CoreGateEvidence] = {item.metric: item for item in bundle.evidence}
    results: list[CriterionResult] = []

    for metric in CoreGateMetric:
        evidence = index.get(metric)
        if evidence is None:
            results.append(
                CriterionResult(
                    metric=metric,
                    state=CriterionState.BLOCKED,
                    requirement=_REQUIREMENTS[metric],
                    observed="No admissible evidence supplied",
                    source=(),
                )
            )
            continue
        try:
            passed = _evaluate(evidence)
            observed = f"value={evidence.value!r}; kind={evidence.kind.value}; sample_count={evidence.sample_count}"
            state = CriterionState.PASS if passed else CriterionState.FAIL
        except ValueError as exc:
            observed = str(exc)
            state = CriterionState.FAIL
        results.append(
            CriterionResult(
                metric=metric,
                state=state,
                requirement=_REQUIREMENTS[metric],
                observed=observed,
                source=evidence.source,
            )
        )

    any_fail = any(item.state == CriterionState.FAIL for item in results)
    any_blocked = any(item.state == CriterionState.BLOCKED for item in results) or bool(blockers)
    if any_fail:
        state = CoreGateState.FAIL
    elif any_blocked:
        state = CoreGateState.BLOCKED
    else:
        state = CoreGateState.PASS

    return CoreGateReport(
        repo_commit=bundle.repo_commit,
        state=state,
        criteria=tuple(results),
        blockers=blockers,
    )
