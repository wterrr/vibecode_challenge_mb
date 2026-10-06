#!/usr/bin/env python3
"""Fail-closed verification for the LearnFlow V2 Core Freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "benchmarks" / "core_freeze" / "manifest.json"

EXPECTED_FREEZE_ID = "learnflow-v2-core-freeze-2026-10-06"
EXPECTED_ENGINE_COMMIT = "fdad3db1340d8b28175ab5382d800ff79df9a8a0"
EXPECTED_EVIDENCE_COMMIT = "4b2cc7887773a8fb81dee36010fcae3bc2015ccb"
EXPECTED_V1_FREEZE_COMMIT = "f6dae0e8510a6db8fc49a761eddc2a055ffaefda"
EXPECTED_BENCHMARK_ID = "v2-core-gate-v2"
EXPECTED_RESULT_SHA256 = "16ee5c9f5684b53596f890e3978147e11c7df33f281bd48955a8bd01e2fe2609"
EXPECTED_SPEC_SHA256 = "e20ab43e2a7622af8dc47c00c0c5692b42cceb05723ec93a70981effd62a9cfd"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = b"blob " + str(len(data)).encode("ascii") + bytes([0])
    return hashlib.sha1(header + data).hexdigest()


def _source_files_under(prefix: str) -> set[str]:
    base = ROOT / prefix
    if not base.exists():
        return set()
    result: set[str] = set()
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        result.add(path.relative_to(ROOT).as_posix())
    return result


def verify() -> list[str]:
    errors: list[str] = []
    if not MANIFEST_PATH.exists():
        return [f"missing freeze manifest: {MANIFEST_PATH}"]

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    fixed = {
        "freeze_id": EXPECTED_FREEZE_ID,
        "accepted_engine_commit": EXPECTED_ENGINE_COMMIT,
        "evidence_freeze_commit": EXPECTED_EVIDENCE_COMMIT,
    }
    for key, expected in fixed.items():
        if manifest.get(key) != expected:
            errors.append(f"{key}: expected {expected!r}, got {manifest.get(key)!r}")

    if manifest.get("state") != "COMPLETE":
        errors.append(f"state must be COMPLETE, got {manifest.get('state')!r}")
    if manifest.get("core_gate", {}).get("benchmark_id") != EXPECTED_BENCHMARK_ID:
        errors.append("benchmark_id is not the corrected frozen v2-core-gate-v2")
    if manifest.get("core_gate", {}).get("decision") != "PASS":
        errors.append("Core Gate decision is not PASS")
    if manifest.get("core_gate", {}).get("raw_result_sha256") != EXPECTED_RESULT_SHA256:
        errors.append("official raw result SHA-256 changed")
    if manifest.get("core_gate", {}).get("frozen_spec_sha256") != EXPECTED_SPEC_SHA256:
        errors.append("frozen spec SHA-256 changed")
    if manifest.get("rollback", {}).get("v1_freeze_commit") != EXPECTED_V1_FREEZE_COMMIT:
        errors.append("V1 rollback commit changed")

    required_deps = manifest.get("required_core_dependencies", {})
    req_path = ROOT / "requirements.txt"
    if not req_path.is_file():
        errors.append("requirements.txt is missing")
    else:
        requirement_lines = {
            line.strip()
            for line in req_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        for requirement in required_deps.get("python_requirements", []):
            if requirement not in requirement_lines:
                errors.append(f"required Core Python dependency changed or missing: {requirement}")

    package_path = ROOT / "package.json"
    if not package_path.is_file():
        errors.append("package.json is missing")
    else:
        package = json.loads(package_path.read_text(encoding="utf-8"))
        dependencies = package.get("dependencies", {})
        for name, expected_version in required_deps.get("node_dependencies", {}).items():
            if dependencies.get(name) != expected_version:
                errors.append(
                    f"required Core Node dependency changed or missing: "
                    f"{name}={expected_version}"
                )

    package_lock_path = ROOT / "package-lock.json"
    if not package_lock_path.is_file():
        errors.append("package-lock.json is missing")
    else:
        package_lock = json.loads(package_lock_path.read_text(encoding="utf-8"))
        locked_packages = package_lock.get("packages", {})
        for name, expected_version in required_deps.get("node_lock_versions", {}).items():
            locked = locked_packages.get(f"node_modules/{name}", {})
            if locked.get("version") != expected_version:
                errors.append(
                    f"required Core Node lock changed or missing: "
                    f"{name}={expected_version}"
                )

    protected = manifest.get("protected_files", {})
    expected_paths = set(protected)
    actual_paths: set[str] = set(manifest.get("protected_exact_paths", []))
    for prefix in manifest.get("protected_namespaces", []):
        actual_paths.update(_source_files_under(prefix))

    missing_or_extra = expected_paths ^ actual_paths
    if missing_or_extra:
        errors.append(
            "protected Core file set changed: " + ", ".join(sorted(missing_or_extra))
        )

    for rel_path, expected_sha in sorted(protected.items()):
        path = ROOT / rel_path
        if not path.is_file():
            errors.append(f"missing protected file: {rel_path}")
            continue
        actual_sha = git_blob_sha(path)
        if actual_sha != expected_sha:
            errors.append(
                f"protected file changed: {rel_path} "
                f"(expected blob {expected_sha}, got {actual_sha})"
            )

    for rel_path, expected_sha in sorted(manifest.get("frozen_evidence_files", {}).items()):
        path = ROOT / rel_path
        if not path.is_file():
            errors.append(f"missing frozen evidence file: {rel_path}")
            continue
        actual_sha = git_blob_sha(path)
        if actual_sha != expected_sha:
            errors.append(
                f"frozen evidence changed: {rel_path} "
                f"(expected blob {expected_sha}, got {actual_sha})"
            )

    active_evidence = ROOT / "benchmarks/core_gate/evidence.json"
    frozen_evidence = ROOT / "benchmarks/baselines/v2/core_gate_evidence.json"
    if active_evidence.is_file() and frozen_evidence.is_file():
        if json.loads(active_evidence.read_text(encoding="utf-8")) != json.loads(
            frozen_evidence.read_text(encoding="utf-8")
        ):
            errors.append("active Core Gate evidence no longer equals frozen evidence")

    return errors


def main() -> int:
    errors = verify()
    if errors:
        print("CORE_FREEZE=FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("CORE_FREEZE=PASS")
    print(f"freeze_id={EXPECTED_FREEZE_ID}")
    print(f"accepted_engine_commit={EXPECTED_ENGINE_COMMIT}")
    print(f"evidence_freeze_commit={EXPECTED_EVIDENCE_COMMIT}")
    print(f"rollback_v1_commit={EXPECTED_V1_FREEZE_COMMIT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
