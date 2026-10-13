"""Fail-closed offline audit for the LearnFlow V3 GitHub Actions fan-out regression.

Contract:
* Research-specific V3 PR workflows must not depend on shared PLAN/NOTES edits.
* Legacy expensive catch-all V3 checks run on main integration PRs, not all stacked PRs.
* A simulated V3-59 stacked-PR change triggers V3-59 but no older broad V3 suite.
* This does not cancel already-queued runs or attest native V3-59 media quality.
"""
from __future__ import annotations

import fnmatch
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
DOCUMENTS = {"PLAN_V3.md", "LEARNFLOW_V3_RESEARCH_NOTES.md"}
BROAD_V3 = {"learnflow_v3/**", "tests/v3/**", "benchmarks/**", "app/**"}
EXEMPT = {"v3-ci-scope-audit.yml"}
EXPECTED_PRIMARY = {
    "v3-57-pedagogical-storytelling.yml",
    "v3-58-matched-pedagogy.yml",
    "v3-59-causal-reveal.yml",
}


def config(path: Path) -> dict:
    raw = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    if not isinstance(raw, dict) or not isinstance(raw.get("on"), dict):
        raise AssertionError(f"Malformed on: {path.name}")
    return raw


def pulls(cfg: dict) -> dict | None:
    value = cfg["on"].get("pull_request")
    if value is None:
        return None
    if value == "":
        return {}
    if not isinstance(value, dict):
        raise AssertionError(f"Malformed pull_request mapping: {value!r}")
    return value


def selected(cfg: dict, *, base_branch: str, changed: tuple[str, ...]) -> bool:
    pr = pulls(cfg)
    if pr is None:
        return False
    branches = pr.get("branches")
    if branches is not None and not any(fnmatch.fnmatchcase(base_branch, glob) for glob in branches):
        return False
    ignored = pr.get("branches-ignore", [])
    if any(fnmatch.fnmatchcase(base_branch, glob) for glob in ignored):
        return False
    patterns = pr.get("paths")
    if patterns is None:
        return not any(fnmatch.fnmatchcase(path, glob) for path in changed for glob in pr.get("paths-ignore", []))
    # The scoped workflows currently use positive path patterns only.
    if not isinstance(patterns, list):
        raise AssertionError("Non-list pull_request.paths")
    if any(p.startswith("!") for p in patterns):
        raise AssertionError("Negated paths require a dedicated ordered GitHub glob evaluator")
    return any(fnmatch.fnmatchcase(path, pattern) for path in changed for pattern in patterns)


def audit() -> dict:
    filenames = sorted(WORKFLOWS.glob("v3-*.yml"))
    errors = []
    result = {}
    document_triggers = []
    broad_unscoped = []
    missing_concurrency = []
    for path in filenames:
        cfg = config(path)
        result[path.name] = cfg
        pr = pulls(cfg)
        if pr is None or path.name in EXEMPT:
            continue
        paths = set(pr.get("paths", []))
        if paths & DOCUMENTS:
            document_triggers.append(path.name)
        if paths & BROAD_V3 and "main" not in pr.get("branches", []):
            broad_unscoped.append(path.name)
        if (paths & DOCUMENTS or paths & BROAD_V3 or path.name in EXPECTED_PRIMARY) and not cfg.get("concurrency"):
            missing_concurrency.append(path.name)
    if document_triggers:
        errors.append(f"SHARED_DOC_FANOUT: {document_triggers}")
    if broad_unscoped:
        errors.append(f"LEGACY_UNSCOPED_CATCHALL: {broad_unscoped}")
    if missing_concurrency:
        errors.append(f"MISSING_CONCURRENCY: {missing_concurrency}")

    target = (
        "PLAN_V3.md",
        "LEARNFLOW_V3_RESEARCH_NOTES.md",
        "learnflow_v3/causal_reveal.py",
        "tests/v3/test_v3_59_causal_reveal.py",
        "reports/v3_59_causal_reveal_audit.md",
    )
    triggered = sorted(
        name for name, cfg in result.items()
        if selected(cfg, base_branch="chatgpt/v3-58-matched-pedagogy-evaluation", changed=target)
    )
    if "v3-59-causal-reveal.yml" not in triggered:
        errors.append("V359_PRIMARY_TRIGGER_MISSING")
    if len(triggered) > 3:
        errors.append(f"FANOUT_TOO_LARGE: {triggered}")

    docs_only = tuple(sorted(DOCUMENTS))
    docs_triggered = sorted(
        name for name, cfg in result.items()
        if selected(cfg, base_branch="chatgpt/v3-58-matched-pedagogy-evaluation", changed=docs_only)
    )
    if docs_triggered:
        errors.append(f"DOCS_ONLY_STILL_TRIGGER_V3: {docs_triggered}")

    for name in EXPECTED_PRIMARY:
        if name not in result or pulls(result[name]) is None:
            errors.append(f"MISSING_PRIMARY_CI: {name}")
    # Regression: integration PR on main MUST still execute legacy broad contract.
    if not selected(result["v3-canonical-contracts.yml"],
                    base_branch="main",
                    changed=("learnflow_v3/semantic_scene_wire.py",)):
        errors.append("MAIN_INTEGRATION_REGRESSION_LOST")

    summary = {
        "checkpoint": "CI Recovery & Workflow Fan-out Remediation",
        "workflows_scanned": len(filenames),
        "legacy_broad_only_on_main": not broad_unscoped,
        "shared_docs_not_in_specific_v3_paths": not document_triggers,
        "stacked_v359_simulation": triggered,
        "stacked_docs_only_simulation": docs_triggered,
        "main_integration_regression_present": "MAIN_INTEGRATION_REGRESSION_LOST" not in errors,
        "errors": errors,
        "gate": "PASS_OFFLINE_SIMULATION" if not errors else "FAIL",
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)
    return summary


if __name__ == "__main__":
    audit()
