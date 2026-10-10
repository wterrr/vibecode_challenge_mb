"""V3-39: new preregistered ONE-POST compatibility-correct creative lesson trial.

The V3-37 provider HTTP 404 was observed, not retried. V3-39 alters only
one independently preregistered wire element: omit unsupported temperature.
No inference runs during tests, PRs or normal pushes.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from learnflow_v3.creative_evidence_gate import EvidenceRejected, inspect_candidate
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_manim_runner import MODEL, run
from learnflow_v3.openrouter_metadata_audit import probe_model_endpoints

PREREG = "benchmarks/learnflowbench/v3/v3_39_compatible_structured_scene_preregister.json"
V335 = "benchmarks/learnflowbench/v3/v3_35_structured_scene_preregister.json"


def frozen_protocol(root: Path) -> dict:
    record = json.loads((root / PREREG).read_text(encoding="utf-8"))
    earlier = json.loads((root / V335).read_text(encoding="utf-8"))
    expected = record.get("frozen_intervention", {}).get("keep", {})
    if not (
        record.get("checkpoint") == "V3-39"
        and record.get("preregistered_before_implementation") is True
        and record.get("parent_pr") == 72
        and record.get("parent_sha") == "e5b0b4fb5cf8bc1e82be428c368ab5e947a54c1e"
        and record.get("topic_id") == earlier["topic_id"]
        and record.get("topic_query_sha256") == earlier["topic_query_sha256"]
        and record.get("exact_model") == MODEL
        and record.get("frozen_intervention", {}).get("remove_only") == ["temperature"]
        and expected.get("max_tokens") == 6500
        and expected.get("provider.require_parameters") is True
        and expected.get("provider.allow_fallbacks") is False
        and expected.get("response_format.json_schema.strict") is True
        and record["requests"]["maximum_new_model_http_posts"] == 1
        and record["requests"]["retry"] == 0
        and record["requests"]["fallback"] is False
        and record["production"] == "BLOCKED"
    ):
        raise Blocked("V339_PREREGISTRATION_DRIFT")
    return record


def exact_public_capability(*, probe=probe_model_endpoints) -> dict:
    """Advisory GET only; testable 0->4 provider-parameter-filter hypothesis."""
    candidate = probe()
    if not (
        candidate.get("model") == MODEL
        and candidate.get("http_status") == "HTTP_200"
        and candidate.get("model_id_matched") is True
        and type(candidate.get("schema_and_max_tokens_count")) is int
        and candidate["schema_and_max_tokens_count"] >= 1
        and candidate.get("v337_all_advertised_generation_params_count") == 0
        and candidate.get("metadata_cannot_certify_json_schema_strict") is True
        and candidate.get("inference_requests") == 0
        and candidate.get("account_eligibility_certified") is False
    ):
        raise Blocked("V339_PUBLIC_CAPABILITY_UNVERIFIED_NO_PAID_POST")
    return candidate


def one_trial(root: Path, out: Path, *, key: str,
              public_probe=probe_model_endpoints, runner=run,
              evidence_gate=inspect_candidate) -> dict:
    frozen_protocol(root)
    if not out.is_dir() or any(out.iterdir()):
        raise Blocked("V339_OUTPUT_NOT_EMPTY")
    catalog = exact_public_capability(probe=public_probe)
    result = runner(root, out, mode="live-structured-no-temperature", key=key)
    receipt = result.get("provider_receipt") if isinstance(result, dict) else None
    if not (
        result.get("model_plan_origin") ==
            "REAL_GPT6_LUNA_STRICT_JSON_SCHEMA_ONE_REQUEST"
        and result.get("provider_requests") == 1
        and isinstance(receipt, dict)
        and receipt.get("temperature_parameter_sent") is False
        and receipt.get("actual_provider_requests") == 1
        and receipt.get("provider_require_parameters") is True
        and receipt.get("no_retry") is True
        and receipt.get("no_fallback") is True
    ):
        raise Blocked("V339_NOT_VERIFIED_ONE_MODEL_POST_OR_CHANGED_WIRE")
    gate = evidence_gate(out)
    if gate.get("status") != "MODEL_ORIGIN_TECHNICAL_EVIDENCE_PASS_NOT_EDUCATIONAL_PASS":
        raise Blocked("V339_REAL_MODEL_MP4_NOT_CERTIFIED")
    verdict = {
        "checkpoint": "V3-39",
        "status": "ONE_MODEL_ORIGIN_MP4_TECHNICAL_PASS_NOT_EDUCATIONAL_PASS",
        "model": MODEL,
        "topic_id": result["topic_id"],
        "inference_http_posts": 1,
        "temperature_parameter_sent": False,
        "schema_strict": True,
        "provider_require_parameters": True,
        "no_retry": True, "no_fallback": True,
        "v337_model_http404": True,
        "public_candidate_count_without_temperature": catalog["schema_and_max_tokens_count"],
        "model_response_sha256": receipt["model_response_sha256"],
        "video_sha256": gate["video_sha256"],
        "human_educational_quality": "NOT_ASSESSED",
        "six_unseen_domains": "NOT_RETESTED",
        "a_b_comparison": "ABSTAIN",
        "production": "BLOCKED",
    }
    (out / "v3_39_compatible_luna_receipt.json").write_text(
        json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
    return verdict


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True, type=Path)
    opts = p.parse_args()
    opts.output_dir.mkdir(parents=True, exist_ok=False)
    try:
        result = one_trial(root, opts.output_dir,
                           key=os.getenv("OPENROUTER_API_KEY", ""))
    except (Blocked, EvidenceRejected) as exc:
        code = str(exc)
        if len(code) > 160 or not code.startswith(("V339_", "V335_", "V334_")):
            code = "V339_RUNTIME_BLOCKED"
        (opts.output_dir / "v3_39_failure.json").write_text(
            json.dumps({
                "checkpoint": "V3-39", "state": "BLOCKED",
                "sanitized_error_code": code,
                "attempts": "INSPECT_V3_35_REQUEST_ATTEMPT_IF_PRESENT",
                "retry": 0, "fallback": False,
                "production": "BLOCKED"
            }, indent=2) + "\n", encoding="utf-8")
        print("V3_39=BLOCKED " + code, flush=True)
        raise SystemExit(2) from None
    print("V3_39=" + result["status"], flush=True)


if __name__ == "__main__":
    main()
