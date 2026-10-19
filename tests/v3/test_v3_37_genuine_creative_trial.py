"""V3-37 preregistration, catalog gating and one-shot orchestration negatives.

Fake runner/evidence objects in this file are not provider or media evidence.
"""
from __future__ import annotations
from pathlib import Path
import json

import pytest

from learnflow_v3.genuine_creative_trial import (
    Blocked, verified_preregistration, require_public_catalog, run_once,
)

ROOT = Path(__file__).resolve().parents[2]
MODEL = "openai/gpt-6-luna"


def advertised():
    return {
        "model": MODEL,
        "inference_requests": 0,
        "api_key_used": False,
        "catalog_status": "PUBLIC_MODEL_ENDPOINTS_ADVERTISE_STRUCTURED_OUTPUTS",
        "matching_endpoint_count": 1,
    }


def test_preregistered_before_implementation_and_no_adaptive_retry():
    p = verified_preregistration(ROOT)
    assert p["checkpoint"] == "V3-37"
    assert p["maximum_inference_http_posts"] == 1
    assert p["exact_model"] == MODEL
    assert p["retries"] == 0 and p["provider_fallback"] is False
    assert p["parent_sha"] == "6d4625e91c286d71a9ed72ca197e9aed55d35eb9"
    assert p["scientific_limits"]["human_educational_quality"] == "NOT_ASSESSED"


@pytest.mark.parametrize("mutation", [
    {"model": "other"},
    {"api_key_used": True},
    {"inference_requests": 1},
    {"catalog_status": "UNAVAILABLE_UNVERIFIED"},
    {"matching_endpoint_count": 0},
    {"matching_endpoint_count": None},
])
def test_unknown_or_mismatched_public_catalog_never_authorizes_post(mutation):
    entry = {**advertised(), **mutation}
    with pytest.raises(Blocked, match="V337_CATALOG_UNVERIFIED_NO_PAID_REQUEST"):
        require_public_catalog(probe=lambda: entry)


def test_missing_catalog_blocks_without_runner_call(tmp_path):
    called = []
    def fake_runner(*args, **kwargs):
        called.append("POST")
        raise AssertionError("model POST called despite unavailable metadata")
    with pytest.raises(Blocked, match="V337_CATALOG_UNVERIFIED_NO_PAID_REQUEST"):
        run_once(ROOT, tmp_path, key="fake-test-key",
                 catalog_probe=lambda: {**advertised(),
                     "catalog_status": "UNAVAILABLE_UNVERIFIED"},
                 runner=fake_runner)
    assert called == []


def test_mock_contract_calls_runner_once_and_preserves_blocked_state(tmp_path):
    calls = []
    def runner(root, out, *, mode, key):
        calls.append((mode, key))
        assert mode == "live-structured"
        return {
            "model_plan_origin": "REAL_GPT6_LUNA_STRICT_JSON_SCHEMA_ONE_REQUEST",
            "provider_requests": 1, "topic_id": "lfb-018-math",
            "plan_sha256": "a" * 64
        }
    def evidence(out):
        return {
            "status": "MODEL_ORIGIN_TECHNICAL_EVIDENCE_PASS_NOT_EDUCATIONAL_PASS",
            "video_sha256": "b" * 64
        }
    r = run_once(ROOT, tmp_path, key="fake-test-key",
                 catalog_probe=advertised, runner=runner, evidence_gate=evidence)
    assert calls == [("live-structured", "fake-test-key")]
    assert r["state"] == "SINGLE_REAL_MODEL_TECHNICAL_PASS_NOT_EDUCATIONAL_PASS"
    assert r["human_educational_quality"] == "NOT_ASSESSED"
    assert r["production"] == "BLOCKED"
    assert json.loads((tmp_path / "v3_37_genuine_creative_receipt.json").read_text()) == r


def test_synthetic_runner_is_rejected_even_with_mock_positive_evidence(tmp_path):
    def host_fixture(*args, **kwargs):
        return {"model_plan_origin": "SYNTHETIC_HOST_FIXTURE_NOT_REAL_MODEL",
                "provider_requests": 0}
    with pytest.raises(Blocked, match="V337_NOT_MODEL_ORIGIN"):
        run_once(ROOT, tmp_path, key="fake-test-key",
                 catalog_probe=advertised, runner=host_fixture,
                 evidence_gate=lambda _: {"status": "MODEL_ORIGIN_TECHNICAL_EVIDENCE_PASS_NOT_EDUCATIONAL_PASS"})


def test_invalid_media_proof_never_passes(tmp_path):
    def fake_runner(*args, **kwargs):
        return {"model_plan_origin": "REAL_GPT6_LUNA_STRICT_JSON_SCHEMA_ONE_REQUEST",
                "provider_requests": 1}
    with pytest.raises(Blocked, match="V337_REAL_MODEL_ARTIFACT_NOT_CERTIFIED"):
        run_once(ROOT, tmp_path, key="fake-test-key",
                 catalog_probe=advertised, runner=fake_runner,
                 evidence_gate=lambda _: {"status": "REJECTED"})


def test_existing_output_artifact_is_not_overwritten(tmp_path):
    (tmp_path / "previous_request_receipt.json").write_text("{}")
    with pytest.raises(Blocked, match="V337_OUTPUT_NONEMPTY"):
        run_once(ROOT, tmp_path, key="fake-test-key", catalog_probe=advertised)
