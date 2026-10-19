"""V3-36 no-inference adversarial evidence and provenance regressions.

All fixture model receipts and media in this file are MOCKS, never actual AI
evidence. Production CLI always invokes ffprobe on actual media bytes.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from learnflow_v3.creative_evidence_gate import (
    EvidenceRejected, inspect_candidate, REAL_ORIGIN, COMPILED_ORIGIN,
)
from learnflow_v3 import creative_manim_runner as runner
from learnflow_v3.creative_manim_ablation import fixture_plan, manim_code

MODEL = "openai/gpt-6-luna"


def _sha(b: bytes) -> str:
    return sha256(b).hexdigest()


def _mock_probe(_path):
    return {
        "streams": [
            {"codec_type": "video", "codec_name": "h264",
             "width": 1280, "height": 720, "nb_frames": "240"},
            {"codec_type": "audio", "codec_name": "aac"}
        ],
        "format": {"duration": "10.0"}
    }


def _fake_candidate(root: Path) -> dict:
    model_plan = fixture_plan().model_copy(update={"model_author": MODEL})
    plan_dict = model_plan.model_dump(mode="json")
    plan = json.dumps(plan_dict).encode()
    source = manim_code(model_plan, [4.0] * 4).encode()
    mp4 = b"FAKE_MP4_BYTES_NOT_AN_ACTUAL_VIDEO"
    (root / "scene_plan.json").write_bytes(plan)
    (root / "generated_host_compiled_manim.py").write_bytes(source)
    (root / "creative_manim_with_audio.mp4").write_bytes(mp4)
    (root / "creative_manim.srt").write_text("1\n00:00:00,000 --> 00:00:02,000\nHalf\n")
    receipt = {
        "checkpoint": "V3-35",
        "topic_id": "lfb-018-math",
        "status": "TECHNICAL_MODEL_SCENE_PASS_NOT_EDUCATIONAL_PASS",
        "model_plan_origin": REAL_ORIGIN,
        "manim_source_origin": COMPILED_ORIGIN,
        "provider_requests": 1,
        "provider_receipt": {
            "model": MODEL, "stage": "REAL_MODEL_SCHEMA_CONSTRAINED_SCENE",
            "actual_provider_requests": 1, "no_retry": True,
            "no_fallback": True, "provider_require_parameters": True,
            "model_response_sha256": "a" * 64,
            "strict_json_schema_sha256": "b" * 64,
            "validated_plan_canonical_sha256": _sha(json.dumps(
                plan_dict, sort_keys=True, separators=(",", ":")).encode())
        },
        "model_generated_unrestricted_python": False,
        "human_blinded_educational_quality": "NOT_ASSESSED",
        "creative_advantage_proven": "NO_UNBALANCED_A_B_ABSTAIN",
        "production": "BLOCKED",
        "sandbox": {
            "network": "none", "read_only_root": True,
            "all_capabilities_dropped": True, "host_secrets_mounted": False,
            "model_python_executed": False
        },
        "plan_sha256": _sha(plan),
        "scene_sha256": _sha(source),
        "audio_sampled_beats": [{"index": x, "frames": 60} for x in range(4)],
        "video": {
            "video_sha256": _sha(mp4), "frames": 240,
            "max_decoded_sample_delta": 2.1,
            "replayed_decoded_samples": 5,
            "aac_rms_per_beat": [0.05] * 4
        }
    }
    (root / "v3_35_ablation_receipt.json").write_text(json.dumps(receipt))
    return receipt


def _write_receipt(root: Path, receipt: dict):
    (root / "v3_35_ablation_receipt.json").write_text(json.dumps(receipt))


def test_mock_attestation_contract_not_a_real_video(tmp_path):
    _fake_candidate(tmp_path)
    result = inspect_candidate(tmp_path, probe=_mock_probe)
    assert result["status"] == "MODEL_ORIGIN_TECHNICAL_EVIDENCE_PASS_NOT_EDUCATIONAL_PASS"
    assert result["blinded_educational_quality"] == "NOT_ASSESSED"
    assert result["inference_requests_in_this_inspection"] == 0
    # The mocked ffprobe is NEVER used from the production CLI.
    with pytest.raises(EvidenceRejected, match="FFPROBE_FAILURE|FFPROBE_UNAVAILABLE"):
        inspect_candidate(tmp_path)


@pytest.mark.parametrize("mutation,expected", [
    ("synthetic", "NOT_REAL_MODEL_SCENE"),
    ("wrong_compiler_origin", "WRONG_MANIM_SOURCE_PROVENANCE"),
    ("response_hash_missing", "MODEL_OR_SCHEMA_HASH_MISSING"),
    ("provider_bridge", "PROVIDER_PLAN_BRIDGE_MISMATCH"),
    ("semantic_mutation", "SCENE_SEMANTICS_NOT_CERTIFIED"),
    ("compiler_replay", "MANIM_SOURCE_REPLAY_MISMATCH"),
    ("retries", "PROVIDER_PROVENANCE_NOT_CERTIFIED"),
    ("no_one_shot", "PROVIDER_PROVENANCE_NOT_CERTIFIED"),
    ("sandbox_network", "SANDBOX_ATTESTATION_MISSING"),
    ("host_secrets", "SANDBOX_ATTESTATION_MISSING"),
    ("silent_audio", "PHYSICAL_AUDIO_BEAT_EVIDENCE_MISSING"),
    ("zero_motion", "VISUAL_CHANGE_EVIDENCE_MISSING"),
    ("claim_education_pass", "SCIENTIFIC_SCOPE_OR_SAFETY_DRIFT"),
    ("release_true", "SCIENTIFIC_SCOPE_OR_SAFETY_DRIFT"),
    ("video_hash", "VIDEO_DIGEST_MISMATCH"),
    ("scene_hash", "PLAN_OR_SOURCE_DIGEST_MISMATCH"),
    ("plan_author", "PLAN_AUTHOR_UNVERIFIED"),
    ("codec_wrong", "ACTUAL_AV_CODEC_OR_RESOLUTION_MISMATCH"),
    ("frame_count_wrong", "ACTUAL_FRAME_COUNT_MISMATCH"),
])
def test_mutations_rejected_without_inference(tmp_path, mutation, expected):
    receipt = _fake_candidate(tmp_path)
    data = deepcopy(receipt)
    probe = _mock_probe
    if mutation == "synthetic":
        data["model_plan_origin"] = "SYNTHETIC_HOST_FIXTURE_NOT_REAL_MODEL"
    elif mutation == "wrong_compiler_origin":
        data["manim_source_origin"] = "HOST_FIXTURE_FROM_HOST_PRIMITIVE_DATA"
    elif mutation == "response_hash_missing":
        data["provider_receipt"]["model_response_sha256"] = None
    elif mutation == "provider_bridge":
        data["provider_receipt"]["validated_plan_canonical_sha256"] = "0" * 64
    elif mutation == "semantic_mutation":
        p = json.loads((tmp_path / "scene_plan.json").read_text())
        p["beats"][0]["actions"][0]["target"] = "missing_graphic_id"
        (tmp_path / "scene_plan.json").write_text(json.dumps(p))
        data["plan_sha256"] = _sha((tmp_path / "scene_plan.json").read_bytes())
        data["provider_receipt"]["validated_plan_canonical_sha256"] = _sha(
            json.dumps(p, sort_keys=True, separators=(",", ":")).encode())
    elif mutation == "compiler_replay":
        (tmp_path / "generated_host_compiled_manim.py").write_text("# changed")
        data["scene_sha256"] = _sha((tmp_path / "generated_host_compiled_manim.py").read_bytes())
    elif mutation == "retries":
        data["provider_receipt"]["no_retry"] = False
    elif mutation == "no_one_shot":
        data["provider_receipt"]["actual_provider_requests"] = 2
    elif mutation == "sandbox_network":
        data["sandbox"]["network"] = "bridge"
    elif mutation == "host_secrets":
        data["sandbox"]["host_secrets_mounted"] = True
    elif mutation == "silent_audio":
        data["video"]["aac_rms_per_beat"][0] = 0
    elif mutation == "zero_motion":
        data["video"]["max_decoded_sample_delta"] = 0.0
    elif mutation == "claim_education_pass":
        data["human_blinded_educational_quality"] = "PASS"
    elif mutation == "release_true":
        data["production"] = "GO"
    elif mutation == "video_hash":
        (tmp_path / "creative_manim_with_audio.mp4").write_bytes(b"tampered")
    elif mutation == "scene_hash":
        (tmp_path / "generated_host_compiled_manim.py").write_text("tampered")
    elif mutation == "plan_author":
        (tmp_path / "scene_plan.json").write_text('{"model_author":"other"}')
        data["plan_sha256"] = _sha((tmp_path / "scene_plan.json").read_bytes())
    elif mutation == "codec_wrong":
        def probe(_):
            p = _mock_probe(_)
            p["streams"][0]["codec_name"] = "vp9"
            return p
    elif mutation == "frame_count_wrong":
        def probe(_):
            p = _mock_probe(_)
            p["streams"][0]["nb_frames"] = "239"
            return p
    _write_receipt(tmp_path, data)
    with pytest.raises(EvidenceRejected, match=expected):
        inspect_candidate(tmp_path, probe=probe)


def test_missing_video_and_symlink_block(tmp_path):
    _fake_candidate(tmp_path)
    (tmp_path / "creative_manim_with_audio.mp4").unlink()
    with pytest.raises(EvidenceRejected, match="MISSING_OR_SYMLINK_ARTIFACT"):
        inspect_candidate(tmp_path, probe=_mock_probe)
    outside = tmp_path.parent / (tmp_path.name + "_untrusted.mp4")
    outside.write_bytes(b"fake")
    (tmp_path / "creative_manim_with_audio.mp4").symlink_to(outside)
    with pytest.raises(EvidenceRejected, match="MISSING_OR_SYMLINK_ARTIFACT"):
        inspect_candidate(tmp_path, probe=_mock_probe)


def test_actual_runner_live_structured_provenance(monkeypatch, tmp_path):
    """Exercise the actual runner branch, but MOCK provider, media and Docker."""
    from learnflow_v3 import structured_scene_authoring as auth
    from learnflow_v3.creative_manim_ablation import fixture_plan
    mock_usage = {
        "stage": "REAL_MODEL_SCHEMA_CONSTRAINED_SCENE", "model": MODEL,
        "actual_provider_requests": 1, "no_retry": True, "no_fallback": True
    }
    monkeypatch.setattr(auth, "preflight", lambda root: {})
    monkeypatch.setattr(auth, "one_shot_structured",
                        lambda key, out, sender=None: ({}, mock_usage))
    monkeypatch.setattr(runner, "checked_manifest", lambda root: {"topic_id": "lfb-018-math"})
    monkeypatch.setattr(runner, "checked_live_plan", lambda raw, usage, out: fixture_plan())
    monkeypatch.setattr(runner, "ablation_baselines",
                        lambda root, plan: {"A": {"status": "ABSTAIN"}, "B": {"status": "ABSTAIN"}})
    monkeypatch.setattr(runner, "_audio", lambda out, plan: (
        [1.] * 4,
        [{"start_seconds": k, "wav_samples": 16000, "wav_rate": 16000,
          "frames": 15, "claim_ids": ["F1"], "narration": "mock"} for k in range(4)],
        out / "narration.wav"))
    monkeypatch.setattr(runner, "manim_code", lambda *args: "# safe mocked source")
    def docker(out, source):
        p = out / "manim_output_mock.mp4"
        p.write_bytes(b"mock video")
        return p, {"network": "none"}
    monkeypatch.setattr(runner, "_docker_manim", docker)
    def mux(cmd, **kwargs):
        Path(cmd[-1]).write_bytes(b"mock h264+aac bytes")
        class Process:
            returncode = 0
        return Process()
    monkeypatch.setattr(runner.subprocess, "run", mux)
    monkeypatch.setattr(runner, "_codec_and_pixel_gates",
                        lambda mp4, beats: {
                            "video_sha256": runner.sha(mp4), "frames": 150,
                            "aac_rms_per_beat": [0.05] * 4,
                            "max_decoded_sample_delta": 2, "replayed_decoded_samples": 5
                        })
    out = tmp_path / "out"
    out.mkdir()
    receipt = runner.run(tmp_path, out, mode="live-structured", key="FAKE_KEY_FOR_TEST_ONLY")
    assert receipt["model_plan_origin"] == REAL_ORIGIN
    assert receipt["manim_source_origin"] == COMPILED_ORIGIN
    assert receipt["status"] == "TECHNICAL_MODEL_SCENE_PASS_NOT_EDUCATIONAL_PASS"
    assert receipt["provider_requests"] == 1
    # The mock candidate has no actual real provider receipt or real MP4.
    with pytest.raises(EvidenceRejected):
        inspect_candidate(out)


def test_cli_preserves_sanitized_v335_http_code(monkeypatch, tmp_path):
    import sys
    from scripts import run_v3_34_ablation as cli
    from learnflow_v3.creative_manim_ablation import Blocked
    def fail(*args, **kwargs):
        raise Blocked("V335_HTTP_404")
    monkeypatch.setattr(cli, "run", fail)
    monkeypatch.setattr(sys, "argv", ["run", "--mode", "live-structured",
                                      "--output-dir", str(tmp_path / "candidate")])
    with pytest.raises(SystemExit) as x:
        cli.main()
    assert x.value.code == 2
    state = json.loads((tmp_path / "candidate/v3_35_failure.json").read_text())
    assert state["error_code"] == "V335_HTTP_404"
    assert state["production"] == "BLOCKED"


def test_actual_legacy_offline_fixture_receipt_name_rejected(tmp_path):
    """V3-34 offline-smoke really writes v3_34_ablation_receipt.json."""
    (tmp_path / "v3_34_ablation_receipt.json").write_text(json.dumps({
        "checkpoint": "V3-34",
        "model_plan_origin": "SYNTHETIC_HOST_FIXTURE_NOT_REAL_MODEL",
        "status": "TECHNICAL_SMOKE_NOT_EDUCATIONAL_PASS",
        "provider_requests": 0,
    }))
    with pytest.raises(EvidenceRejected, match="NOT_REAL_MODEL_SCENE"):
        inspect_candidate(tmp_path)
