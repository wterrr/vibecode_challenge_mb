"""V3-43 reproducible OFFLINE audit of the ONE genuine GPT-6 Luna MP4.

Evidence origin is frozen by preregistered SHA-256 values. A technical PASS
does not certify pedagogical quality. Video metrics are *descriptive*, not
benchmarks. No HTTP client, API provider, model inference, or scene generator.
"""
from __future__ import annotations

import argparse
from array import array
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

REGISTRATION = "benchmarks/learnflowbench/v3/v3_43_genuine_video_quality_preregister.json"
VIDEO_FILE = "creative_manim_with_audio.mp4"
SCENE_FILE = "scene_plan.json"
SOURCE_FILE = "generated_host_compiled_manim.py"
PROVIDER_FILE = "v3_42_portable_provider_receipt.json"
ADAPTER_FILE = "v3_35_ablation_receipt.json"
CAPTION_FILE = "creative_manim.srt"


class AuditRejected(Exception):
    """Invalid/missing/tampered provenance or media: refuse any quality claim."""


def _require(ok: bool, code: str):
    if not ok:
        raise AuditRejected(code)


def _json(path: Path) -> dict:
    _require(path.is_file() and not path.is_symlink(), "V343_MISSING_OR_SYMLINK:" + path.name)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise AuditRejected("V343_UNREADABLE_JSON:" + path.name) from None
    _require(isinstance(value, dict), "V343_BAD_JSON_ROOT:" + path.name)
    return value


def _sha(path: Path) -> str:
    _require(path.is_file() and not path.is_symlink(), "V343_MISSING_OR_SYMLINK:" + path.name)
    return sha256(path.read_bytes()).hexdigest()


def _media_probe(video: Path) -> dict:
    cmd = ["ffprobe", "-v", "error",
           "-show_entries", "stream=codec_type,codec_name,width,height,nb_frames,r_frame_rate",
           "-show_entries", "format=duration",
           "-of", "json", str(video)]
    try:
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        _require(run.returncode == 0, "V343_FFPROBE_FAILED")
        return json.loads(run.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        raise AuditRejected("V343_FFPROBE_FAILED") from None


def _srt_segments(text: str) -> list[dict]:
    def sec(t: str) -> float:
        h, m, s = t.replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    pattern = re.compile(
        r"^\s*(\d+)\s*\n(\d\d:\d\d:\d\d,\d{3}) --> (\d\d:\d\d:\d\d,\d{3})\s*\n(.*?)(?=\n\s*\n|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    parts = [{"index": int(k), "start": sec(a), "end": sec(b),
              "text": " ".join(value.strip().split())}
             for k, a, b, value in pattern.findall(text)]
    _require(len(parts) == 4, "V343_SRT_FOUR_BEATS_REQUIRED")
    return parts


def _source_timeline(source: str, beats: list[dict], authored_beats: list[dict]) -> tuple[list[dict], list[dict]]:
    # Timings are inferred from *host* Manim self.play actions, not ASR words.
    sections = re.split(r"(?=        # BEAT \d+ - exact audio-budget duration )", source)
    sections = [s for s in sections if s.startswith("        # BEAT ")]
    _require(len(sections) == len(beats) == len(authored_beats) == 4, "V343_MANIM_BEAT_COUNT_DRIFT")
    schedule, endings = [], []
    for index, (part, beat, authored) in enumerate(zip(sections, beats, authored_beats)):
        match = re.search(r"# BEAT (\d+) - exact audio-budget duration ([\d.]+)s", part)
        _require(match is not None and int(match.group(1)) == index + 1,
                 "V343_MANIM_BEAT_HEADING_DRIFT")
        plays = re.findall(r"^\s*self\.play\((.+),run_time=([\d.]+)\)\s*$", part, re.MULTILINE)
        _require(len(plays) == len(authored["actions"]), "V343_ACTION_COUNT_DRIFT")
        t = float(beat["start_seconds"])
        for item, seconds in plays:
            dur = float(seconds)
            _require(0 < dur < 30, "V343_ACTION_DURATION_INVALID")
            t += dur
            schedule.append({"beat_index": index, "action": item[:180],
                             "end_seconds": round(t, 3)})
        expected = float(beat["end_seconds"])
        _require(abs(t - expected) < 0.015, "V343_MANIM_VS_NARRATION_TIME_DRIFT")
        endings.append({"beat_index": index, "source_actions": len(plays),
                        "render_end": round(t, 3)})
    return schedule, endings


def _complete_reveal(schedule: list[dict], token: str) -> float:
    hits = [s["end_seconds"] for s in schedule if "FadeIn(" + token + "," in s["action"]]
    _require(len(hits) == 1, "V343_MISSING_EXPECTED_REVEAL:" + token)
    return hits[0]


def _words(value: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", value))


def _wave_evidence(root: Path, beats: list[dict]) -> list[dict]:
    out = []
    for i, beat in enumerate(beats):
        path = root / ("beat_" + str(i) + ".wav")
        _require(path.is_file() and not path.is_symlink(), "V343_AUDIO_BEAT_MISSING")
        try:
            with wave.open(str(path), "rb") as wav:
                rate, frames, chans, width = wav.getframerate(), wav.getnframes(), wav.getnchannels(), wav.getsampwidth()
                raw = wav.readframes(frames)
        except (OSError, EOFError, wave.Error):
            raise AuditRejected("V343_AUDIO_WAV_UNREADABLE") from None
        _require(chans == 1 and width == 2 and rate == beat["wav_rate"]
                 and frames == beat["wav_samples"], "V343_AUDIO_WAV_RECEIPT_MISMATCH")
        a = np.frombuffer(raw, dtype="<i2").astype(np.float64)
        rms = float(np.sqrt(np.mean(a * a)) / 32768.0) if len(a) else 0.0
        _require(rms > 0.001, "V343_AUDIO_SILENT_BEAT")
        out.append({"beat": i + 1, "duration_seconds": round(frames / rate, 3),
                    "rms_normalized": round(rms, 5)})
    return out


def _frames(video: Path, *, fps: int, width: int, height: int) -> np.ndarray:
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
           "-i", str(video), "-vf", f"fps={fps},scale={width}:{height}",
           "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
    try:
        run = subprocess.run(cmd, capture_output=True, timeout=100)
    except (OSError, subprocess.TimeoutExpired):
        raise AuditRejected("V343_FFMPEG_DECODE_FAILED") from None
    _require(run.returncode == 0, "V343_FFMPEG_DECODE_FAILED")
    frame_bytes = width * height * 3
    _require(len(run.stdout) >= 12 * frame_bytes
             and len(run.stdout) % frame_bytes == 0, "V343_INSUFFICIENT_DECODED_FRAMES")
    return np.frombuffer(run.stdout, dtype=np.uint8).reshape((-1, height, width, 3))


def _frame_metrics(frames: np.ndarray, *, luminance_threshold: int,
                   low_activity_threshold: float) -> dict:
    f = frames.astype(np.float32)
    gray = f[:, :, :, 0] * .299 + f[:, :, :, 1] * .587 + f[:, :, :, 2] * .114
    occupancy = np.mean(gray > luminance_threshold, axis=(1, 2))
    deltas = np.mean(np.abs(np.diff(gray, axis=0)), axis=(1, 2)) / 255.0
    return {
        "sampled_frames": int(len(frames)),
        "foreground_occupancy_median_pct": round(float(np.median(occupancy) * 100), 3),
        "foreground_occupancy_p90_pct": round(float(np.percentile(occupancy, 90) * 100), 3),
        "adjacent_sample_delta_median_normalized": round(float(np.median(deltas)), 7),
        "adjacent_sample_delta_p90_normalized": round(float(np.percentile(deltas, 90)), 7),
        "low_activity_sample_pairs_fraction": round(float(np.mean(deltas < low_activity_threshold)), 4),
        "motion_measurement": "samplewise mean-absolute luminance, not optical flow or visual quality score",
    }


def _filmstrip(frames: np.ndarray, *, fps: int, target_seconds: list[float],
               out: Path) -> list[float]:
    # This is intentionally REAL MP4 decoded pixels, never generated illustrative art.
    frames_chosen = []
    times = []
    for second in target_seconds:
        ix = min(len(frames) - 1, max(0, int(round(second * fps))))
        times.append(round(ix / fps, 2))
        image = Image.fromarray(frames[ix]).resize((480, 270), Image.Resampling.BILINEAR)
        panel = Image.new("RGB", (480, 294), (22, 22, 22))
        panel.paste(image, (0, 24))
        ImageDraw.Draw(panel).text((8, 5), f"{ix / fps:.1f}s", fill="white")
        frames_chosen.append(panel)
    ncol = 4
    sheet = Image.new("RGB", (480 * ncol, 294 * math.ceil(len(frames_chosen) / ncol)), (16, 16, 16))
    for i, panel in enumerate(frames_chosen):
        sheet.paste(panel, ((i % ncol) * 480, (i // ncol) * 294))
    sheet.save(out, quality=88)
    return times


def audit_video(root: Path, registration: Path, output_dir: Path) -> dict:
    root = root.resolve()
    _require(root.is_dir() and not root.is_symlink(), "V343_SOURCE_DIR_NOT_FOUND")
    manifest = _json(registration)
    _require(manifest.get("checkpoint") == "V3-43"
             and manifest.get("preregistered_before_implementation") is True
             and manifest.get("parent_sha") == "72cb5942ec1f889ddcf79ff57247a3e4d366a24f",
             "V343_FROZEN_REGISTRATION_DRIFT")
    origin = manifest["source"]
    mapping = {
        VIDEO_FILE: "video_sha256",
        SCENE_FILE: "scene_sha256",
        SOURCE_FILE: "source_sha256",
        PROVIDER_FILE: "provider_receipt_sha256",
        CAPTION_FILE: "srt_sha256",
    }
    for name, key in mapping.items():
        _require(_sha(root / name) == origin[key], "V343_SOURCE_SHA_MISMATCH:" + name)
    provider = _json(root / PROVIDER_FILE)
    receipt = _json(root / ADAPTER_FILE)
    scene = _json(root / SCENE_FILE)
    _require(provider.get("model") == "openai/gpt-6-luna"
             and provider.get("model_response_sha256") == origin["model_response_sha256"]
             and provider.get("actual_provider_requests") == 1
             and provider.get("no_retry") is True
             and provider.get("no_fallback") is True
             and receipt.get("model_plan_origin") == "REAL_GPT6_LUNA_STRICT_JSON_SCHEMA_ONE_REQUEST"
             and receipt.get("manim_source_origin") == "HOST_COMPILED_FROM_MODEL_PRIMITIVE_DATA"
             and receipt.get("provider_requests") == 1
             and receipt.get("video", {}).get("video_sha256") == origin["video_sha256"]
             and receipt.get("plan_sha256") == origin["scene_sha256"]
             and receipt.get("scene_sha256") == origin["source_sha256"],
             "V343_GENUINE_PROVENANCE_NOT_CERTIFIED")
    canonical_sha = sha256(json.dumps(scene, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    _require(canonical_sha == provider.get("validated_plan_canonical_sha256"),
             "V343_SCENE_MODEL_HASH_BRIDGE_BROKEN")
    _require(scene.get("model_author") == "openai/gpt-6-luna"
             and len(scene.get("beats", [])) == 4, "V343_MODEL_SCENE_INVALID")

    probe = _media_probe(root / VIDEO_FILE)
    video_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
    audio_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
    _require(len(video_streams) == 1 and len(audio_streams) >= 1
             and video_streams[0].get("codec_name") == "h264"
             and audio_streams[0].get("codec_name") == "aac"
             and [video_streams[0].get("width"), video_streams[0].get("height")] == origin["resolution"]
             and int(video_streams[0].get("nb_frames") or 0) == origin["expected_frames"]
             and video_streams[0].get("r_frame_rate") == str(origin["fps"]) + "/1",
             "V343_REAL_MEDIA_CODEC_DRIFT")
    duration = float(probe["format"]["duration"])
    _require(abs(duration - origin["expected_frames"] / origin["fps"]) < .08,
             "V343_REAL_MEDIA_DURATION_DRIFT")

    beats = receipt.get("audio_sampled_beats")
    _require(isinstance(beats, list) and len(beats) == 4, "V343_NARRATION_RECEIPT_INVALID")
    schedule, render_ends = _source_timeline((root / SOURCE_FILE).read_text(), beats, scene["beats"])
    segments = _srt_segments((root / CAPTION_FILE).read_text())
    beats_summary = []
    for index, (beat, srt, authored) in enumerate(zip(beats, segments, scene["beats"])):
        _require(srt["index"] == index + 1
                 and abs(srt["start"] - float(beat["start_seconds"])) < .005
                 and 0 <= float(beat["end_seconds"]) - srt["end"] < .4
                 and " ".join(authored["narration"].split()) == srt["text"],
                 "V343_SRT_BEAT_TIMELINE_DRIFT")
        window = float(beat["end_seconds"]) - float(beat["start_seconds"])
        beats_summary.append({
            "index": index + 1, "start_seconds": round(float(beat["start_seconds"]), 3),
            "end_seconds": round(float(beat["end_seconds"]), 3),
            "render_actions": render_ends[index]["source_actions"],
            "narration_words": _words(authored["narration"]),
            "narration_rate_wpm_approx": round(_words(authored["narration"]) / window * 60, 1),
            "alignment_granularity": "BEAT_ONLY; no word-level speech timestamps",
        })
    audio = _wave_evidence(root, beats)

    src = (root / SOURCE_FILE).read_text()
    half_full = _complete_reveal(schedule, "half_unshaded_piece")
    quarters_full = _complete_reveal(schedule, "quarter_bottom_right")
    quarter_onset = float(beats[1]["start_seconds"])
    half_onset = float(beats[0]["start_seconds"])
    half_delay, quarter_delay = half_full - half_onset, quarters_full - quarter_onset

    objects = {o["id"]: o for o in scene["objects"]}
    half_ids = ("half_shaded_piece", "half_unshaded_piece")
    quarter_ids = ("quarter_top_left", "quarter_top_right", "quarter_bottom_left", "quarter_bottom_right")
    _require(all(k in objects and objects[k]["kind"] == "rectangle" for k in (*half_ids, *quarter_ids)),
             "V343_EXPECTED_FRACTION_SHAPES_NOT_PRESENT")
    area = lambda ids: sum(float(objects[k]["width"]) * float(objects[k]["height"]) for k in ids)
    half_area, quarter_area = area(half_ids), area(quarter_ids)
    half_filled = area(("half_shaded_piece",)) / half_area
    quarter_filled = area(("quarter_top_left", "quarter_bottom_left")) / quarter_area
    area_diff = abs(half_area - quarter_area) / quarter_area
    cflags = manifest["frozen_quality_flags"]
    _require(abs(half_filled - .5) < 1e-6 and abs(quarter_filled - .5) < 1e-6,
             "V343_COLORED_FRACTION_SEMANTIC_MISMATCH")
    visible_strings = [o["text"] for o in scene["objects"] if o["kind"] == "text"]
    explicit_multiply = any(re.search(r"(?:×|\\times|[*xX])\s*2", s) for s in visible_strings)
    # Presence in narration alone does NOT count as graphical arithmetic.
    issues = []
    def issue(code, severity, start, end, why, anchor):
        issues.append({"code": code, "severity": severity,
                       "start_seconds": round(start, 3), "end_seconds": round(end, 3),
                       "observed": why, "evidence_anchor": anchor})
    if area_diff > cflags["whole_area_mismatch_warn_ratio"]:
        issue("V343_DIFFERENT_SIZED_WHOLES", "P1", 17.15, duration,
              f"Two-piece whole area {half_area:.3f} vs four-piece whole area {quarter_area:.3f}; relative mismatch {area_diff:.4%}. Both shaded fractions correctly equal 0.5; visual units differ.",
              "scene_plan.json objects: 2 half_* rectangles vs 4 quarter_* rectangles")
    if half_delay > cflags["narration_to_complete_partition_lag_warn_seconds"]:
        issue("V343_FIRST_WHOLE_VISUAL_LAG", "P1", half_onset, half_full,
              "The first whole is not fully visible until after the initial narration begins.",
              "generated_host_compiled_manim.py BEAT 1 + v3_35_ablation_receipt.json beat 0")
    if quarter_delay > cflags["narration_to_complete_partition_lag_warn_seconds"]:
        issue("V343_FOUR_PIECE_REVEAL_LAG", "P1", quarter_onset, quarters_full,
              "The four-part partition is not complete until well after narration starts describing it.",
              "generated_host_compiled_manim.py BEAT 2 + v3_35_ablation_receipt.json beat 1")
    if not explicit_multiply:
        issue("V343_ARITHMETIC_EXPLANATION_NOT_SHOWN", "P1",
              float(beats[2]["start_seconds"]), float(beats[2]["end_seconds"]),
              "Narration explains multiplying numerator and denominator by 2, but no explicit times-two transformation is displayed.",
              "scene_plan.json text objects + BEAT 3; visual strings: " + repr(visible_strings))
    metric_frames = _frames(root / VIDEO_FILE,
                           fps=cflags["frame_sample_fps"],
                           width=cflags["frame_scale"][0],
                           height=cflags["frame_scale"][1])
    metrics = _frame_metrics(metric_frames,
                             luminance_threshold=cflags["foreground_luma_threshold"],
                             low_activity_threshold=cflags["low_activity_pairwise_luma_mean_delta_threshold"])
    # We DO NOT assert foreground is "too low": there is no independently
    # validated industry norm. Report measured value and manual visual gap.
    _require(metrics["sampled_frames"] >= 60, "V343_FRAME_SAMPLING_UNEXPECTED")
    output_dir.mkdir(parents=True, exist_ok=True)
    sample_times = _filmstrip(
        metric_frames, fps=cflags["frame_sample_fps"],
        target_seconds=[.5, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 27, 30, 33, 36, 39],
        out=output_dir / "v3_43_real_video_timeline.jpg")
    report = {
        "checkpoint": "V3-43", "scope": "ONE_FROZEN_GENUINE_VIDEO_OFFLINE",
        "media_origin": "V3-42_REAL_MODEL_AUTHORED_SCENE_REVALIDATED",
        "source_sha256": origin["video_sha256"],
        "model_response_sha256": origin["model_response_sha256"],
        "technical_provenance": "PASS_REVALIDATED",
        "duration_seconds": round(duration, 3), "frame_count": origin["expected_frames"],
        "beats": beats_summary, "audio_physical_signal": audio,
        "claim_coverage": sorted({x for b in scene["beats"] for x in b["claim_ids"]}),
        "actual_fraction_shaded_ratios": {
            "half": round(half_filled, 6), "quarters": round(quarter_filled, 6)},
        "whole_area": {"two_piece": round(half_area, 4), "four_piece": round(quarter_area, 4),
                       "relative_difference_vs_four_piece": round(area_diff, 5)},
        "claim_to_complete_visual_delay_seconds": {
            "two_piece": round(half_delay, 3), "four_piece": round(quarter_delay, 3)},
        "explicit_visual_numerator_denominator_times_two": explicit_multiply,
        "visual_metrics": metrics,
        "sampled_timeline_seconds": sample_times,
        "issues": issues,
        "rubric_coverage": {
            "fraction_visual": "YES_BOTH_SHARES_50_PERCENT",
            "same_sized_whole": "NO_RELATIVE_AREA_MISMATCH",
            "narration_to_completed_visual": "DELAYED_IN_FIRST_TWO_BEATS",
            "multiplication_rule_visual": "NOT_DEMONSTRATED",
            "full_audio_word_alignment": "NOT_MEASURED",
            "voice_intelligibility_prosody": "NOT_HUMAN_ASSESSED",
            "human_learning_gain": "NOT_MEASURED",
            "human_blinded_quality": "NOT_EVALUATED",
            "visual_comparison_3b1b": "NOT_CERTIFIED",
        },
        "quality_decision": "REQUIRES_VISUAL_AND_PEDAGOGICAL_REDESIGN",
        "model_http_posts_in_audit": 0, "provider_authenticated_gets_in_audit": 0,
        "synthetic_video_substitution": False,
        "production": "BLOCKED",
    }
    (output_dir / "v3_43_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--artifact-dir", type=Path, required=True)
    p.add_argument("--registration", type=Path,
                   default=Path(__file__).resolve().parents[1] / REGISTRATION)
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    try:
        r = audit_video(a.artifact_dir, a.registration, a.output_dir)
    except AuditRejected as exc:
        print("V3_43=REJECTED " + str(exc), flush=True)
        raise SystemExit(2) from None
    print("V3_43=GENUINE_VIDEO_AUDIT_COMPLETE_NOT_PEDAGOGICAL_PASS "
          + str(len(r["issues"])) + "_ISSUES", flush=True)


if __name__ == "__main__":
    main()
