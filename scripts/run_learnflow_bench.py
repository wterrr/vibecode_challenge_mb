#!/usr/bin/env python3
"""Run executable LearnFlowBench tracks and write a typed report."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learnflow_bench.runner import run_learnflow_bench


async def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "benchmark_output" / "learnflowbench"
    report = await run_learnflow_bench(output)
    summary = {
        "benchmark_id": report.benchmark_id,
        "source_commit": report.source_commit,
        "corpus_topic_count": report.corpus_topic_count,
        "core_ablation_topic_count": report.core_ablation_topic_count,
        "full_system_fixture_count": report.full_system_fixture_count,
        "benchmark_execution_passed": report.benchmark_execution_passed,
        "sota_claim_allowed": report.sota_claim_allowed,
        "candidates": {},
    }
    for result in report.results:
        summary["candidates"][result.candidate_id.value] = {
            item.metric_id: {
                "state": item.state.value,
                "value": item.value,
                "unit": item.unit,
                "sample_count": item.sample_count,
            }
            for item in result.observations
        }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print("LEARNFLOW_BENCH=PASS" if report.benchmark_execution_passed else "LEARNFLOW_BENCH=FAIL")
    print(f"SOTA_CLAIM_ALLOWED={str(report.sota_claim_allowed).lower()}")
    return 0 if report.benchmark_execution_passed else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
