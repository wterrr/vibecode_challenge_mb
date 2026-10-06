#!/usr/bin/env python3
"""Evaluate LearnFlow V2 Core Gate from explicit evidence; fail closed on missing evidence."""

from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from learnflow_v2.core_gate import CoreGateEvidenceBundle, CoreGateState, evaluate_core_gate


def repository_blockers(root: Path, bundle: CoreGateEvidenceBundle) -> tuple[str, ...]:
    blockers: list[str] = []
    if not (root / "benchmarks" / "baselines" / "v1" / "baseline.json").exists():
        blockers.append("Frozen V1 benchmark baseline is missing")
    if not (root / "learnflow_v2" / "render").exists():
        blockers.append("V2 renderer package/integration is missing; end-to-end V2 render-success evidence cannot be produced")
    if not (root / "benchmarks" / "baselines" / "v2").exists():
        blockers.append("No frozen V2 end-to-end benchmark baseline/results exist")
    if not (root / "benchmarks" / "core_gate" / "static_quality_metric.json").exists():
        blockers.append("No agreed V1-vs-V2 static-quality metric/threshold artifact exists")
    for item in bundle.evidence:
        for source in item.source:
            if not (root / source).exists():
                blockers.append(f"Evidence source is missing: {source}")
    return tuple(blockers)


def main() -> int:
    evidence_path = REPO_ROOT / "benchmarks" / "core_gate" / "evidence.json"
    bundle = CoreGateEvidenceBundle.model_validate(json.loads(evidence_path.read_text(encoding="utf-8")))
    report = evaluate_core_gate(bundle, repository_blockers=repository_blockers(REPO_ROOT, bundle))

    print("=" * 78)
    print("LearnFlow V2 CORE GATE")
    print(f"Commit: {report.repo_commit}")
    print(f"Decision: {report.state.value}")
    print("=" * 78)
    for item in report.criteria:
        print(f"{item.state.value:7} {item.metric.value:38} {item.requirement}")
        print(f"        observed: {item.observed}")
    if report.blockers:
        print("\nRepository blockers:")
        for blocker in report.blockers:
            print(f"- {blocker}")
    print("\nCanonical report:")
    print(report.to_canonical_json())

    return 0 if report.state == CoreGateState.PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
