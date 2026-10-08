"""Offline tests for frozen V3-01 protocol; no rendering, LLM or human ratings."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify_v3_benchmark_protocol import PROTOCOL_PATH, TOPIC_IDS, recompute_sample, validate
from learnflow_bench import load_corpus


def protocol():
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_preregistration_is_structurally_frozen_and_unrun():
    item = protocol()
    result = validate(item)
    assert result["selected_topics"] == 12
    assert item["comparisons"]["mode"] == "FUTURE_NOT_RUN"
    assert all(m["status"] == "UNMEASURED" for m in item["metrics"])
    assert item["permission"]["live_generation_authorized"] is False


def test_locked_selection_is_deterministic_and_diagnostic_excluded():
    p = protocol()
    assert tuple(p["sampling"]["topic_ids"]) == TOPIC_IDS == recompute_sample(load_corpus())
    assert "lfb-005-cs" not in TOPIC_IDS
    assert p["sampling"]["excluded_diagnostic_ids"] == ["lfb-005-cs"]


@pytest.mark.parametrize("change,error", [
    (lambda p: p["source"].update(corpus_sha256="0"*64), "pinned corpus hash"),
    (lambda p: p["source"].update(baseline_commit="f"*40), "baseline revision"),
    (lambda p: p["sampling"].update(seed="posthoc"), "sampling rule"),
    (lambda p: p["sampling"]["topic_ids"].__setitem__(0, "lfb-005-cs"), "TOPIC_SELECTION_CHANGED"),
    (lambda p: p["sampling"]["topic_ids"].__setitem__(1, p["sampling"]["topic_ids"][0]), "TOPIC_SELECTION_CHANGED"),
    (lambda p: p["sampling"]["strata"].pop(), "stratification"),
    (lambda p: p["sampling"].update(replacements_allowed=True), "replacements enabled"),
    (lambda p: p["comparisons"].update(denominator="SUCCESS_ONLY"), "survivor-biased"),
    (lambda p: p["comparisons"]["free_model_policy"].update(allow_paid=True), "paid model"),
    (lambda p: p["comparisons"]["free_model_policy"].update(auto_retry=True), "retry bias"),
    (lambda p: p["comparisons"]["free_model_policy"].update(availability="YES"), "unverified availability"),
    (lambda p: p["human"].update(identity_key_kept_blind=False), "blinding"),
    (lambda p: p["human"].update(score_invalid_video=5), "invalid/missing"),
    (lambda p: p["metrics"][0].update(status="MEASURED", value=4.9), "outcome leakage"),
    (lambda p: p["metrics"][0].update(primary=False), "primary endpoint drift"),
    (lambda p: p["analysis"].update(min_topic_wins_each=1), "threshold posthoc"),
    (lambda p: p["hard_gates"].update(critical_semantic_errors_max=1), "safety threshold"),
    (lambda p: p["outcome_records"].update(drop_failures=True), "failed trial omission"),
    (lambda p: p["permission"].update(paid_api_authorized=True), "unapproved activity"),
    (lambda p: p["permission"].update(cost_cap_usd=10), "cost budget"),
])
def test_mutation_must_fail_closed(change, error):
    p = deepcopy(protocol())
    change(p)
    with pytest.raises(ValueError, match=error):
        validate(p)


def test_no_provider_secret_no_quality_score_no_artifact_production():
    raw = json.dumps(protocol()).lower()
    assert "openrouter_api_key" not in raw
    assert "sk-or-v1-" not in raw
    code = (ROOT / "scripts/verify_v3_benchmark_protocol.py").read_text()
    assert "run_live_v2d_pilot" not in code
    assert "OPENROUTER_API_KEY" not in code
    assert "render_video(" not in code


def test_frozen_corpus_is_only_read_not_modified():
    from learnflow_bench import corpus_sha256
    assert corpus_sha256() == protocol()["source"]["corpus_sha256"]
