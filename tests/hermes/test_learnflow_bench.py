from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learnflow_bench import (
    BenchmarkCandidateId,
    BenchmarkMetricCategory,
    BenchmarkObservation,
    BenchmarkReport,
    MeasurementState,
    core_ablation_fixture_ids,
    core_fixture_sha256,
    load_candidates,
    load_corpus,
)


def test_corpus_is_exactly_100_and_frozen():
    corpus = load_corpus()
    assert corpus.frozen is True
    assert len(corpus.topics) == 100


def test_corpus_domain_distribution_is_fixed():
    counts = Counter(topic.domain.value for topic in load_corpus().topics)
    assert counts == {
        "cs": 17,
        "math": 17,
        "physics": 17,
        "biology": 17,
        "chemistry": 16,
        "history_general": 16,
    }


def test_corpus_difficulty_distribution_is_fixed():
    counts = Counter(topic.difficulty.value for topic in load_corpus().topics)
    assert counts == {"easy": 34, "medium": 33, "hard": 33}


def test_topic_ids_and_queries_are_unique():
    corpus = load_corpus()
    assert len({topic.topic_id for topic in corpus.topics}) == 100
    assert len({topic.query.casefold() for topic in corpus.topics}) == 100


def test_candidate_matrix_contains_exact_milestones():
    candidates = load_candidates()
    assert tuple(item.candidate_id for item in candidates) == tuple(BenchmarkCandidateId)


def test_v2_milestones_are_cumulative():
    by_id = {item.candidate_id: item for item in load_candidates()}
    assert by_id[BenchmarkCandidateId.V2A].scenegraph
    assert by_id[BenchmarkCandidateId.V2A].layout_solver
    assert not by_id[BenchmarkCandidateId.V2A].motion
    assert by_id[BenchmarkCandidateId.V2B].motion
    assert by_id[BenchmarkCandidateId.V2B].transitions
    assert by_id[BenchmarkCandidateId.V2C].deterministic_qa
    assert by_id[BenchmarkCandidateId.V2C].repair
    assert by_id[BenchmarkCandidateId.V2D].hermes_control_plane


def test_core_ablation_uses_exact_frozen_v1_fixtures():
    baseline = json.loads(
        (ROOT / "benchmarks" / "baselines" / "v1" / "baseline.json").read_text(encoding="utf-8")
    )
    assert core_ablation_fixture_ids() == tuple(sorted(baseline["lessons"].keys()))


def test_core_fixture_hash_is_stable_length():
    value = core_fixture_sha256()
    assert len(value) == 64
    int(value, 16)


def test_measured_observation_requires_evidence():
    with pytest.raises(ValidationError, match="requires evidence"):
        BenchmarkObservation(
            metric_id="bad",
            category=BenchmarkMetricCategory.STRUCTURAL,
            state=MeasurementState.MEASURED,
            value=1.0,
        )


def test_unmeasured_observation_cannot_carry_value():
    with pytest.raises(ValidationError, match="cannot carry a value"):
        BenchmarkObservation(
            metric_id="bad",
            category=BenchmarkMetricCategory.LEARNING_OUTCOME,
            state=MeasurementState.UNMEASURED,
            value=0.9,
        )


def test_report_cannot_authorize_sota_claim():
    fixture_hash = "a" * 64
    result = {
        "candidate_id": "v1",
        "execution_mode": "test",
        "fixture_set_sha256": fixture_hash,
        "observations": [],
    }
    all_results = [
        {**result, "candidate_id": candidate.value}
        for candidate in BenchmarkCandidateId
    ]
    with pytest.raises(ValidationError, match="cannot authorize a SOTA claim"):
        BenchmarkReport(
            benchmark_id="test",
            source_commit="b" * 40,
            corpus_sha256="c" * 64,
            core_fixture_sha256=fixture_hash,
            corpus_topic_count=100,
            core_ablation_topic_count=3,
            full_system_fixture_count=1,
            results=all_results,
            benchmark_execution_passed=True,
            sota_claim_allowed=True,
        )


def test_report_requires_all_five_candidates():
    with pytest.raises(ValidationError, match="exactly V1"):
        BenchmarkReport(
            benchmark_id="test",
            source_commit="b" * 40,
            corpus_sha256="c" * 64,
            core_fixture_sha256="d" * 64,
            corpus_topic_count=100,
            core_ablation_topic_count=3,
            full_system_fixture_count=1,
            results=[
                {
                    "candidate_id": "v1",
                    "execution_mode": "test",
                    "fixture_set_sha256": "e" * 64,
                    "observations": [],
                }
            ],
            benchmark_execution_passed=True,
        )


def test_claim_policy_explicitly_marks_v2d_fixture_as_noncomparable():
    config = json.loads(
        (ROOT / "benchmarks" / "learnflowbench" / "core_ablation_v1.json").read_text(encoding="utf-8")
    )
    assert config["full_system_fixture"]["comparable_to_core_ablation"] is False
    assert config["claim_policy"]["full_system_fixture_is_contract_evidence_only"] is True
    assert config["claim_policy"]["sota_claim_allowed"] is False


def test_runner_has_no_live_provider_secret_dependency():
    source = (ROOT / "learnflow_bench" / "runner.py").read_text(encoding="utf-8")
    assert "OPENROUTER_API_KEY" not in source
    assert ".env" not in source


def test_runner_does_not_import_renderer_backend():
    source = (ROOT / "learnflow_bench" / "runner.py").read_text(encoding="utf-8")
    assert "learnflow_v2.render.backend" not in source
