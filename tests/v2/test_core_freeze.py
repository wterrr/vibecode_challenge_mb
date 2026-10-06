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


def test_git_blob_hash_matches_frozen_known_blob():
    from scripts.verify_v2_core_freeze import git_blob_sha

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    path = Path("benchmarks/baselines/v1/baseline.json")
    assert git_blob_sha(path) == data["rollback"]["baseline_git_blob_sha"]


def test_control_plane_dependencies_can_be_added_without_core_unfreeze():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert "requirements.txt" not in data["protected_exact_paths"]
    assert "package.json" not in data["protected_exact_paths"]
    assert "package-lock.json" not in data["protected_exact_paths"]
    assert "kiwisolver==1.5.1" in data["required_core_dependencies"]["python_requirements"]
    assert data["required_core_dependencies"]["node_dependencies"]["elkjs"] == "0.12.0"
