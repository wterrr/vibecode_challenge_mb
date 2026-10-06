from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

MANIFEST = Path("benchmarks/core_freeze/manifest.json")


def test_core_freeze_verifier_passes_repository_snapshot():
    proc = subprocess.run(
        [sys.executable, "scripts/verify_v2_core_freeze.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "CORE_FREEZE=PASS" in proc.stdout


def test_core_freeze_pins_gate_engine_evidence_and_rollback():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["state"] == "COMPLETE"
    assert data["accepted_engine_commit"] == "fdad3db1340d8b28175ab5382d800ff79df9a8a0"
    assert data["evidence_freeze_commit"] == "4b2cc7887773a8fb81dee36010fcae3bc2015ccb"
    assert data["core_gate"]["benchmark_id"] == "v2-core-gate-v2"
    assert data["core_gate"]["decision"] == "PASS"
    assert data["rollback"]["v1_freeze_commit"] == "f6dae0e8510a6db8fc49a761eddc2a055ffaefda"
    assert data["rollback"]["baseline_version"] == "v1-cp10"


def test_hermes_is_outside_frozen_core_namespaces():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert all("hermes" not in prefix.lower() for prefix in data["protected_namespaces"])
    assert "outside protected Core namespaces" in data["change_policy"]["hermes_allowed"]
