#!/usr/bin/env python3
"""V3-41 OFFLINE-only: native H264/AAC from a clearly synthetic compatible wire.

No API URL, key, GET or POST. This cannot certify a real-model video.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.compatible_scene_protocol import (
    audit_protocol, candidate_request_body, offline_synthetic_wire_fixture,
    portable_wire_schema)
from learnflow_v3.creative_manim_runner import run
from learnflow_v3.creative_evidence_gate import EvidenceRejected, inspect_candidate

REGISTRATION = "benchmarks/learnflowbench/v3/v3_41_provider_compatible_protocol_preregister.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", required=True, type=Path)
    args = ap.parse_args()
    prereg = json.loads((ROOT / REGISTRATION).read_text())
    if not (
        prereg.get("checkpoint") == "V3-41"
        and prereg.get("preregistered_before_implementation") is True
        and prereg.get("current_authorization", {}).get("model_inference_http_posts") == 0
        and prereg.get("current_authorization", {}).get("authenticated_provider_gets") == 0
        and prereg.get("future_live_trial", {}).get("implemented_in_this_phase") is False
    ):
        raise SystemExit("V3_41=BLOCKED_PREREGISTRATION_DRIFT")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    if list(args.output_dir.iterdir()):
        raise SystemExit("V3_41=BLOCKED_NONEMPTY_OUTPUT")
    preview = candidate_request_body()
    if "temperature" in preview or preview["provider"] != {
        "allow_fallbacks": False, "require_parameters": True
    }:
        raise SystemExit("V3_41=BLOCKED_PARAMETER_DRIFT")
    try:
        receipt = run(ROOT, args.output_dir, mode="offline-v341-compatible",
                      compatible_wire=offline_synthetic_wire_fixture())
    except (Blocked, OSError, ValueError) as exc:
        (args.output_dir / "v3_41_offline_failure.json").write_text(
            json.dumps({
                "checkpoint": "V3-41", "status": "BLOCKED",
                "error_class": type(exc).__name__,
                "inference_requests": 0,
                "production": "BLOCKED",
            }, indent=2) + "\n")
        raise SystemExit("V3_41=BLOCKED_NATIVE_SYNTHETIC_REPLAY") from None
    if (receipt["model_plan_origin"] !=
        "SYNTHETIC_V341_COMPAT_WIRE_FIXTURE_NOT_REAL_MODEL"
        or receipt["provider_requests"] != 0):
        raise SystemExit("V3_41=BLOCKED_FALSE_PROVENANCE")
    try:
        inspect_candidate(args.output_dir)
    except EvidenceRejected as exc:
        if str(exc) != "NOT_REAL_MODEL_SCENE":
            raise SystemExit("V3_41=BLOCKED_WRONG_EVIDENCE_REJECTION") from None
    else:
        raise SystemExit("V3_41=BLOCKED_SYNTHETIC_ACCEPTED_AS_MODEL")
    (args.output_dir / "v3_41_candidate_strict_wire_schema.json").write_text(
        json.dumps(portable_wire_schema(), indent=2) + "\n")
    report = {
        **audit_protocol(),
        "native_h264_aac_synthetic_host_fixture": "PASS_NOT_MODEL",
        "decoded_video_sha256": receipt["video"]["video_sha256"],
        "decoded_sample_count": receipt["video"]["replayed_decoded_samples"],
        "synthetic_provenance_gate": "REJECTED_NOT_REAL_MODEL_SCENE",
        "model_inference_http_posts": 0,
        "strict_endpoint_native_enforcement": "NOT_VERIFIED",
        "production": "BLOCKED",
    }
    (args.output_dir / "v3_41_offline_compatibility_receipt.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print("V3_41=OFFLINE_NATIVE_SYNTHETIC_PASS_NOT_REAL_MODEL")


if __name__ == "__main__":
    main()
