#!/usr/bin/env python3
"""Static acceptance verifier for LearnFlowBench."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learnflow_bench import BenchmarkCandidateId, load_candidates, load_corpus
from learnflow_bench.corpus import CORE_ABLATION_PATH


def main() -> int:
    corpus = load_corpus()
    if not corpus.frozen:
        raise SystemExit("LEARNFLOW_BENCH_CONTRACT=FAIL corpus must be frozen")
    if len(corpus.topics) != 100:
        raise SystemExit(f"LEARNFLOW_BENCH_CONTRACT=FAIL topic_count={len(corpus.topics)}")

    domains = Counter(topic.domain.value for topic in corpus.topics)
    expected_domains = {
        "cs": 17,
        "math": 17,
        "physics": 17,
        "biology": 17,
        "chemistry": 16,
        "history_general": 16,
    }
    if dict(domains) != expected_domains:
        raise SystemExit(f"LEARNFLOW_BENCH_CONTRACT=FAIL domain_counts={dict(domains)!r}")

    difficulty = Counter(topic.difficulty.value for topic in corpus.topics)
    if dict(difficulty) != {"easy": 34, "medium": 33, "hard": 33}:
        raise SystemExit(f"LEARNFLOW_BENCH_CONTRACT=FAIL difficulty_counts={dict(difficulty)!r}")

    candidates = load_candidates()
    if tuple(item.candidate_id for item in candidates) != tuple(BenchmarkCandidateId):
        raise SystemExit("LEARNFLOW_BENCH_CONTRACT=FAIL candidate order/membership")

    config = json.loads(CORE_ABLATION_PATH.read_text(encoding="utf-8"))
    baseline = json.loads(
        (ROOT / "benchmarks" / "baselines" / "v1" / "baseline.json").read_text(encoding="utf-8")
    )
    if config["legacy_v1_fixture_ids"] != sorted(baseline["lessons"].keys()):
        raise SystemExit("LEARNFLOW_BENCH_CONTRACT=FAIL core fixtures drift from frozen V1 baseline")
    if config["claim_policy"]["sota_claim_allowed"] is not False:
        raise SystemExit("LEARNFLOW_BENCH_CONTRACT=FAIL SOTA claim must remain blocked")
    if config["claim_policy"]["full_system_fixture_is_contract_evidence_only"] is not True:
        raise SystemExit("LEARNFLOW_BENCH_CONTRACT=FAIL V2D fixture replay must be labeled contract-only")
    if config["claim_policy"]["learning_outcome_requires_external_or_human_evaluation"] is not True:
        raise SystemExit("LEARNFLOW_BENCH_CONTRACT=FAIL learning outcome policy")

    runner = (ROOT / "learnflow_bench" / "runner.py").read_text(encoding="utf-8")
    for forbidden in ("OPENROUTER_API_KEY", "sota_claim_allowed=True", "learnflow_v2.render.backend"):
        if forbidden in runner:
            raise SystemExit(f"LEARNFLOW_BENCH_CONTRACT=FAIL forbidden runner surface: {forbidden}")

    print("LEARNFLOW_BENCH_CONTRACT=PASS")
    print("frozen_topic_count=100")
    print("domain_distribution=17,17,17,17,16,16")
    print("difficulty_distribution=34,33,33")
    print("candidates=V1,V2A,V2B,V2C,V2D")
    print("same_core_fixtures=PASS")
    print("unmeasured_metric_policy=PASS")
    print("sota_claim_gate=BLOCKED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
