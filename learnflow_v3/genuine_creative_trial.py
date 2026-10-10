"""V3-37: a single separately registered model-created scene trial.

Do not run inference in unit tests or on normal CI pushes. The one live POST
is authorized only by a unique V3-37 tagged commit after same-HEAD offline CI.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import json
import os

from learnflow_v3.provider_catalog_preflight import probe_public_catalog
from learnflow_v3.creative_evidence_gate import inspect_candidate, EvidenceRejected
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_manim_runner import MODEL, run

REGISTRATION = "benchmarks/learnflowbench/v3/v3_37_first_real_creative_scene_preregister.json"
PARENT_REGISTRATION = "benchmarks/learnflowbench/v3/v3_35_structured_scene_preregister.json"


def verified_preregistration(root: Path) -> dict:
    candidate = json.loads((root / REGISTRATION).read_text(encoding="utf-8"))
    parent = json.loads((root / PARENT_REGISTRATION).read_text(encoding="utf-8"))
    if not (candidate["protocol_frozen_before_implementation"] is True
            and candidate["checkpoint"] == "V3-37"
            and candidate["parent_pr"] == 70
            and candidate["parent_sha"] == "6d4625e91c286d71a9ed72ca197e9aed55d35eb9"
            and candidate["topic_id"] == parent["topic_id"]
            and candidate["topic_query_sha256"] == parent["topic_query_sha256"]
            and candidate["exact_model"] == MODEL
            and candidate["maximum_inference_http_posts"] == 1
            and candidate["provider_fallback"] is False
            and candidate["provider_require_parameters"] is True
            and candidate["retries"] == 0
            and candidate["response_format"] == "json_schema_strict"
            and candidate["api"] == "https://openrouter.ai/api/v1/chat/completions"
            and candidate["scientific_limits"]["production"] == "BLOCKED"):
        raise Blocked("V337_PREREGISTRATION_DRIFT")
    return candidate


def require_public_catalog(*, probe=probe_public_catalog) -> dict:
    """Advisory metadata only; this cannot certify authenticated POST behavior."""
    catalog = probe()
    if not (catalog.get("inference_requests") == 0
            and catalog.get("api_key_used") is False
            and catalog.get("model") == MODEL
            and catalog.get("catalog_status") ==
                "PUBLIC_MODEL_ENDPOINTS_ADVERTISE_STRUCTURED_OUTPUTS"
            and type(catalog.get("matching_endpoint_count")) is int
            and catalog["matching_endpoint_count"] >= 1):
        raise Blocked("V337_CATALOG_UNVERIFIED_NO_PAID_REQUEST")
    return catalog


def run_once(root: Path, out: Path, *, key: str,
             catalog_probe=probe_public_catalog,
             runner=run, evidence_gate=inspect_candidate) -> dict:
    verified_preregistration(root)
    if not out.is_dir() or any(out.iterdir()):
        raise Blocked("V337_OUTPUT_NONEMPTY")
    # This GET uses NO key and does NOT retry a prior model request.
    catalog = require_public_catalog(probe=catalog_probe)
    # No fallback, loop, second request or manual schema repair; the inherited
    # structured client implements exactly ONE model POST and fail-closed render.
    original = runner(root, out, mode="live-structured", key=key)
    if not (original["model_plan_origin"] ==
            "REAL_GPT6_LUNA_STRICT_JSON_SCHEMA_ONE_REQUEST"
            and original["provider_requests"] == 1):
        raise Blocked("V337_NOT_MODEL_ORIGIN")
    gate = evidence_gate(out)
    if gate["status"] != "MODEL_ORIGIN_TECHNICAL_EVIDENCE_PASS_NOT_EDUCATIONAL_PASS":
        raise Blocked("V337_REAL_MODEL_ARTIFACT_NOT_CERTIFIED")
    receipt = {
        "checkpoint": "V3-37",
        "state": "SINGLE_REAL_MODEL_TECHNICAL_PASS_NOT_EDUCATIONAL_PASS",
        "topic_id": original["topic_id"],
        "model": MODEL,
        "provider_http_post_attempts": 1,
        "public_catalog_checked": True,
        "public_catalog_inference_requests": catalog["inference_requests"],
        "model_plan_sha256": original["plan_sha256"],
        "real_video_sha256": gate["video_sha256"],
        "original_v3_35_technical_receipt_preserved": True,
        "external_source_semantic_certification": "NOT_ASSESSED",
        "human_educational_quality": "NOT_ASSESSED",
        "cross_domain_generalization": "NOT_ESTABLISHED",
        "comparison_a_b": "ABSTAIN",
        "production": "BLOCKED",
    }
    (out / "v3_37_genuine_creative_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True, type=Path)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    try:
        outcome = run_once(root, args.output_dir, key=os.getenv("OPENROUTER_API_KEY", ""))
    except (Blocked, EvidenceRejected) as exc:
        reason = str(exc)
        allowed = ("V337_", "V335_", "V334_")
        if not reason.startswith(allowed) or len(reason) > 150:
            reason = "V337_VALIDATION_OR_RUNTIME_BLOCKED"
        (args.output_dir / "v3_37_failure.json").write_text(json.dumps({
            "checkpoint": "V3-37",
            "state": "BLOCKED",
            "sanitized_error_code": reason,
            "actual_http_request_attempts": "REFER_TO_V3_35_REQUEST_ATTEMPT_ARTIFACT",
            "no_retry": True, "no_fallback": True,
            "production": "BLOCKED"
        }, indent=2) + "\n", encoding="utf-8")
        print("V3_37=BLOCKED " + reason, flush=True)
        raise SystemExit(2) from None
    print("V3_37=" + outcome["state"], flush=True)


if __name__ == "__main__":
    main()
