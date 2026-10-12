"""V3-42 separately preregistered ONE genuine GPT-6 Luna POST only.

DO NOT use from tests or ordinary CI pushes. The unique opt-in workflow enforces
exact branch, first run attempt and special one-off activation marker.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path

from learnflow_v3.creative_evidence_gate import EvidenceRejected, inspect_candidate
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_manim_runner import MODEL, run
from learnflow_v3.compatible_scene_protocol import VERSION, portable_wire_schema, candidate_request_body
from learnflow_v3.compatible_creative_trial import exact_public_capability
from learnflow_v3.openrouter_metadata_audit import probe_model_endpoints

PREREG = "benchmarks/learnflowbench/v3/v3_42_single_genuine_portable_trial_preregister.json"
PARENT = "benchmarks/learnflowbench/v3/v3_41_provider_compatible_protocol_preregister.json"
PARENT_SHA = "a7610bd5fcfb892bebd1bb6838de8841d5041820"


def frozen_protocol(root: Path) -> dict:
    m = json.loads((root / PREREG).read_text(encoding="utf-8"))
    p = json.loads((root / PARENT).read_text(encoding="utf-8"))
    q = m.get("one_shot_budget", {})
    body = candidate_request_body()
    if not (
        m.get("checkpoint") == "V3-42"
        and m.get("preregistered_before_implementation") is True
        and m.get("parent_pr") == 75
        and m.get("frozen_parent_head") == PARENT_SHA
        and m.get("parent_ci_run") == 38025538022
        and m.get("frozen_topic_id") == p.get("frozen_topic_id") == "lfb-018-math"
        and m.get("exact_model") == MODEL
        and m.get("wire_protocol") == VERSION
        and m.get("activation_marker") == "[v3-42-single-genuine-portable-post]"
        and m.get("no_inference_until_tagged_activation") is True
        and q.get("maximum_new_model_http_posts") == 1
        and q.get("retries") == 0
        and q.get("provider_fallback") is False
        and q.get("temperature_parameter_present") is False
        and q.get("provider_require_parameters") is True
        and q.get("max_tokens") == 6500
        and body["model"] == MODEL
        and body["response_format"]["json_schema"]["schema"] == portable_wire_schema()
        and "temperature" not in body
        and m.get("production") == "BLOCKED"
    ):
        raise Blocked("V342_PREREGISTRATION_OR_REQUEST_DRIFT")
    return m


def one_trial(root: Path, out: Path, *, key: str,
              public_probe=probe_model_endpoints, runner=run,
              evidence_gate=inspect_candidate) -> dict:
    frozen_protocol(root)
    if not out.is_dir() or any(out.iterdir()):
        raise Blocked("V342_OUTPUT_NOT_EMPTY")
    catalog = exact_public_capability(probe=public_probe)
    result = runner(root,out,mode="live-v342-portable",key=key)
    receipt = result.get("provider_receipt") if isinstance(result, dict) else None
    if not (
        result.get("model_plan_origin") == "REAL_GPT6_LUNA_STRICT_JSON_SCHEMA_ONE_REQUEST"
        and result.get("manim_source_origin") == "HOST_COMPILED_FROM_MODEL_PRIMITIVE_DATA"
        and result.get("provider_requests") == 1
        and isinstance(receipt, dict)
        and receipt.get("stage") == "REAL_MODEL_SCHEMA_CONSTRAINED_SCENE"
        and receipt.get("protocol") == "V3-42_PREREGISTERED_V3-41_PORTABLE"
        and receipt.get("actual_provider_requests") == 1
        and receipt.get("temperature_parameter_sent") is False
        and receipt.get("provider_require_parameters") is True
        and receipt.get("no_retry") is True
        and receipt.get("no_fallback") is True
    ):
        raise Blocked("V342_WRONG_PROVIDER_OR_SYNTHETIC_PROVENANCE")
    proof = evidence_gate(out)
    if proof.get("status") != "MODEL_ORIGIN_TECHNICAL_EVIDENCE_PASS_NOT_EDUCATIONAL_PASS":
        raise Blocked("V342_REAL_MODEL_MEDIA_NOT_CERTIFIED")
    report = {
        "checkpoint": "V3-42",
        "status": "REAL_MODEL_MANIM_TECHNICAL_PASS_NOT_EDUCATIONAL_PASS",
        "model": MODEL, "topic_id": result["topic_id"],
        "model_response_sha256": receipt["model_response_sha256"],
        "video_sha256": proof["video_sha256"],
        "model_http_posts": 1, "fallback": False, "retry_count": 0,
        "temperature_parameter_sent": False, "strict_json_schema": True,
        "endpoint_capability": "OBSERVED_MODEL_RESPONSE_AND_MEDIA_GATE_PASS",
        "public_endpoint_count": catalog["schema_and_max_tokens_count"],
        "six_unseen_domain_generalization": "NOT_RETESTED",
        "blinded_educational_quality": "NOT_ASSESSED",
        "production": "BLOCKED",
    }
    (out / "v3_42_single_genuine_outcome.json").write_text(
        json.dumps(report, indent=2) + "\n",encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True,type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[1]
    try:
        r=one_trial(root,args.output_dir,key=os.getenv("OPENROUTER_API_KEY",""))
    except (Blocked,EvidenceRejected) as exc:
        code = str(exc)
        if not (len(code) <= 120 and code.startswith(("V342_", "V339_", "V334_"))):
            code = "V342_RUNTIME_BLOCKED"
        (args.output_dir / "v3_42_failure.json").write_text(
            json.dumps({"checkpoint":"V3-42","state":"BLOCKED",
                        "sanitized_error_code":code,"retry_count":0,
                        "provider_fallback":False,"production":"BLOCKED"},
                       indent=2) + "\n",encoding="utf-8")
        print("V3_42=BLOCKED " + code,flush=True)
        raise SystemExit(2) from None
    print("V3_42=" + r["status"],flush=True)


if __name__ == "__main__":
    main()
