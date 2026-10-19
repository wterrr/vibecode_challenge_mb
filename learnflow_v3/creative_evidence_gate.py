"""V3-36: read-only evidence gate for genuine model-authored creative MP4.

This module never sends network requests or reads API keys. A synthetic or
mock plan is always rejected; technical acceptance is NOT an educational study.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from pydantic import ValidationError
from learnflow_v3.creative_manim_ablation import CreativeScene, Blocked, manim_code
from learnflow_v3.creative_manim_runner import FPS

MODEL = "openai/gpt-6-luna"
REAL_ORIGIN = "REAL_GPT6_LUNA_STRICT_JSON_SCHEMA_ONE_REQUEST"
COMPILED_ORIGIN = "HOST_COMPILED_FROM_MODEL_PRIMITIVE_DATA"


class EvidenceRejected(Exception):
    """A missing or conflicting claim prevents a model-authored PASS."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise EvidenceRejected(reason)


def _read_json(path: Path) -> dict:
    _require(path.is_file() and not path.is_symlink(), "MISSING_OR_SYMLINK_JSON")
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise EvidenceRejected("INVALID_JSON") from None
    _require(isinstance(result, dict), "INVALID_JSON_OBJECT")
    return result


def _file(root: Path, name: str) -> Path:
    path = root / name
    _require(path.is_file() and not path.is_symlink(), "MISSING_OR_SYMLINK_ARTIFACT:" + name)
    _require(path.resolve().is_relative_to(root.resolve()), "ARTIFACT_OUTSIDE_DIRECTORY")
    return path


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _ffprobe(path: Path) -> dict:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "stream=codec_type,codec_name,width,height,nb_frames",
             "-show_entries", "format=duration", "-of", "json", str(path)],
            text=True, capture_output=True, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise EvidenceRejected("FFPROBE_UNAVAILABLE") from None
    _require(r.returncode == 0, "FFPROBE_FAILURE")
    try:
        return json.loads(r.stdout)
    except ValueError:
        raise EvidenceRejected("FFPROBE_BAD_JSON") from None


def _hex_digest(s) -> bool:
    return isinstance(s, str) and len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def inspect_candidate(root: Path, *, probe=None) -> dict:
    """Require real model receipt, real files, semantic/media and provenance.

    probe injection exists ONLY for negative/unit tests. Production CLI always
    invokes real ffprobe against actual MP4 bytes.
    """
    root = root.resolve()
    # The original offline-smoke runner writes a *V3-34* receipt even when
    # launched from the V3-35 workflow. Recognize that exact legacy format
    # rather than mislabeling a synthetic fixture as a missing-model error.
    legacy = root / "v3_34_ablation_receipt.json"
    if not (root / "v3_35_ablation_receipt.json").exists() and legacy.is_file():
        prior = _read_json(legacy)
        if prior.get("model_plan_origin") in ("SYNTHETIC_HOST_FIXTURE_NOT_REAL_MODEL",
            "SYNTHETIC_V341_COMPAT_WIRE_FIXTURE_NOT_REAL_MODEL"):
            raise EvidenceRejected("NOT_REAL_MODEL_SCENE")
    receipt = _read_json(root / "v3_35_ablation_receipt.json")
    _require(receipt.get("checkpoint") == "V3-35", "WRONG_OR_MISSING_CHECKPOINT")
    _require(receipt.get("model_plan_origin") == REAL_ORIGIN, "NOT_REAL_MODEL_SCENE")
    _require(receipt.get("manim_source_origin") == COMPILED_ORIGIN,
             "WRONG_MANIM_SOURCE_PROVENANCE")
    _require(receipt.get("status") == "TECHNICAL_MODEL_SCENE_PASS_NOT_EDUCATIONAL_PASS",
             "NO_TECHNICAL_MODEL_SCENE_PASS")
    provider = receipt.get("provider_receipt")
    _require(isinstance(provider, dict), "NO_REAL_PROVIDER_RECEIPT")
    _require(provider.get("model") == MODEL
             and provider.get("stage") == "REAL_MODEL_SCHEMA_CONSTRAINED_SCENE"
             and provider.get("actual_provider_requests") == 1
             and provider.get("no_retry") is True
             and provider.get("no_fallback") is True
             and provider.get("provider_require_parameters") is True,
             "PROVIDER_PROVENANCE_NOT_CERTIFIED")
    _require(_hex_digest(provider.get("model_response_sha256"))
             and _hex_digest(provider.get("strict_json_schema_sha256"))
             and _hex_digest(provider.get("validated_plan_canonical_sha256")),
             "MODEL_OR_SCHEMA_HASH_MISSING")
    _require(receipt.get("provider_requests") == 1
             and receipt.get("production") == "BLOCKED"
             and receipt.get("model_generated_unrestricted_python") is False
             and receipt.get("human_blinded_educational_quality") == "NOT_ASSESSED"
             and receipt.get("creative_advantage_proven") == "NO_UNBALANCED_A_B_ABSTAIN",
             "SCIENTIFIC_SCOPE_OR_SAFETY_DRIFT")
    sandbox = receipt.get("sandbox")
    _require(isinstance(sandbox, dict)
             and sandbox.get("network") == "none"
             and sandbox.get("read_only_root") is True
             and sandbox.get("host_secrets_mounted") is False
             and sandbox.get("model_python_executed") is False
             and sandbox.get("all_capabilities_dropped") is True,
             "SANDBOX_ATTESTATION_MISSING")
    plan = _file(root, "scene_plan.json")
    code = _file(root, "generated_host_compiled_manim.py")
    mp4 = _file(root, "creative_manim_with_audio.mp4")
    srt = _file(root, "creative_manim.srt")
    plan_json = _read_json(plan)
    _require(plan_json.get("model_author") == MODEL, "PLAN_AUTHOR_UNVERIFIED")
    canonical = json.dumps(plan_json, sort_keys=True, separators=(",", ":")).encode("utf-8")
    _require(sha256(canonical).hexdigest() ==
             provider["validated_plan_canonical_sha256"], "PROVIDER_PLAN_BRIDGE_MISMATCH")
    try:
        validated_plan = CreativeScene.model_validate(plan_json)
    except (ValidationError, Blocked, ValueError, TypeError):
        raise EvidenceRejected("SCENE_SEMANTICS_NOT_CERTIFIED") from None
    _require(_sha(plan) == receipt.get("plan_sha256")
             and _sha(code) == receipt.get("scene_sha256"),
             "PLAN_OR_SOURCE_DIGEST_MISMATCH")
    media = receipt.get("video")
    _require(isinstance(media, dict) and _sha(mp4) == media.get("video_sha256"),
             "VIDEO_DIGEST_MISMATCH")
    _require(srt.stat().st_size > 0, "MISSING_CAPTIONS")
    beats = receipt.get("audio_sampled_beats")
    rms = media.get("aac_rms_per_beat")
    _require(isinstance(beats, list) and len(beats) == 4
             and isinstance(rms, list) and len(rms) == 4
             and all(isinstance(x, (int, float)) and x >= 0.002 for x in rms)
             and all(isinstance(b, dict) and type(b.get("frames")) is int
                     and b["frames"] > 0 for b in beats),
             "PHYSICAL_AUDIO_BEAT_EVIDENCE_MISSING")
    durations = [b["frames"] / FPS for b in beats]
    try:
        rebuilt = manim_code(validated_plan, durations)
    except (Blocked, ValueError, TypeError):
        raise EvidenceRejected("MANIM_SOURCE_REPLAY_FAILED") from None
    _require(code.read_text(encoding="utf-8") == rebuilt,
             "MANIM_SOURCE_REPLAY_MISMATCH")
    _require(isinstance(media.get("max_decoded_sample_delta"), (float, int))
             and media["max_decoded_sample_delta"] > 0.9
             and media.get("replayed_decoded_samples") == 5,
             "VISUAL_CHANGE_EVIDENCE_MISSING")
    stream_data = (probe or _ffprobe)(mp4)
    streams = stream_data.get("streams", [])
    video = [s for s in streams if s.get("codec_type") == "video"]
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    _require(len(video) == 1 and len(audio) >= 1
             and video[0].get("codec_name") == "h264"
             and audio[0].get("codec_name") == "aac"
             and (video[0].get("width"), video[0].get("height")) == (1280, 720),
             "ACTUAL_AV_CODEC_OR_RESOLUTION_MISMATCH")
    try:
        frames = int(video[0].get("nb_frames") or 0)
        duration = float(stream_data.get("format", {}).get("duration") or 0)
    except (ValueError, TypeError):
        raise EvidenceRejected("MALFORMED_MEDIA_METADATA") from None
    _require(frames >= 120 and frames == media.get("frames")
             and abs(frames - sum(b["frames"] for b in beats)) <= 20,
             "ACTUAL_FRAME_COUNT_MISMATCH")
    _require(duration > 0, "MISSING_MEDIA_DURATION")
    return {
        "checkpoint": "V3-36",
        "status": "MODEL_ORIGIN_TECHNICAL_EVIDENCE_PASS_NOT_EDUCATIONAL_PASS",
        "topic_id": receipt.get("topic_id"),
        "video_sha256": media["video_sha256"],
        "model_response_sha256": provider["model_response_sha256"],
        "inference_requests_in_this_inspection": 0,
        "semantic_generalization": "NOT_ESTABLISHED",
        "blinded_educational_quality": "NOT_ASSESSED",
        "production": "BLOCKED",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--artifact-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--expect-synthetic-rejection", action="store_true")
    a = p.parse_args()
    try:
        result = inspect_candidate(a.artifact_dir)
    except EvidenceRejected as exc:
        result = {"checkpoint": "V3-36", "status": "REJECTED",
                  "reason": str(exc), "inference_requests_in_this_inspection": 0,
                  "educational_quality": "NOT_ASSESSED", "production": "BLOCKED"}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("V3_36_EVIDENCE=" + result["status"], flush=True)
    if a.expect_synthetic_rejection:
        _require(result["status"] == "REJECTED"
                 and result.get("reason") == "NOT_REAL_MODEL_SCENE",
                 "SYNTHETIC_FIXTURE_WAS_NOT_REJECTED")
    elif result["status"] == "REJECTED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
