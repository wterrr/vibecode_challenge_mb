#!/usr/bin/env python3
"""V3-72 versioned native H264/AAC repairs from frozen V3-57 source bytes.

Two NEW named MP4s; no modification to original V3-57/58/59/61 experiments,
no model API, no script-side network or treatment-key access.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learnflow_v3.pedagogical_storytelling_slice import WIDTH, HEIGHT, FPS, plan, font
from learnflow_v3.v372_timeline_safe_renderer import (
    SAFE_CASES, render_safe_frame, verify_entire_timeline, frame_geometry,
)

REG = ROOT / "benchmarks/learnflowbench/v3/v3_72_collision_repair_preregister.json"


def require(ok, code):
    if not ok:
        raise AssertionError("V372_" + code)


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for b in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def ffprobe(video: Path) -> dict:
    obj = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-count_frames", "-show_entries",
        "stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames",
        "-show_entries", "format=duration", "-of", "json", str(video)
    ], timeout=45))
    streams = {s["codec_type"]: s for s in obj["streams"]}
    v, a = streams["video"], streams["audio"]
    require((v["codec_name"], a["codec_name"], v["width"], v["height"],
             v["r_frame_rate"]) == ("h264", "aac", WIDTH, HEIGHT, f"{FPS}/1"),
            "VIDEO_CODEC_OR_SHAPE")
    return {"frames": int(v["nb_read_frames"]),
            "duration_s": round(float(obj["format"]["duration"]), 3)}


def aac_sha(video: Path) -> str:
    packet = subprocess.check_output([
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-i", str(video), "-map", "0:a:0", "-c:a", "copy",
        "-f", "adts", "-"
    ], timeout=60)
    return hashlib.sha256(packet).hexdigest()


def full_decode(video: Path):
    subprocess.run([
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-xerror", "-i", str(video), "-map", "0:v:0",
        "-f", "null", "-"
    ], check=True, stdout=subprocess.DEVNULL, timeout=120)


def decode_frame(video: Path, second: float) -> Image.Image:
    data = subprocess.check_output([
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-ss", f"{second:.3f}", "-i", str(video), "-frames:v", "1",
        "-f", "image2pipe", "-c:v", "png", "-"
    ], timeout=60)
    im = Image.open(io.BytesIO(data)).convert("RGB")
    require(im.size == (WIDTH, HEIGHT), "DECODED_IMAGE_SHAPE")
    return im


def timeline_boundaries(receipt: dict, frames: int) -> list[int]:
    beats = receipt["beat_receipts"]
    require(len(beats) == 5 and beats[0]["start_s"] == 0,
            "FROZEN_TIMING_INCOMPLETE")
    boundaries = [0]
    for b in beats[:-1]:
        end = round(float(b["end_s"])*FPS)
        boundaries.append(end)
    boundaries.append(frames)
    require(all(b > a for a, b in zip(boundaries, boundaries[1:])),
            "INVALID_ACTUAL_FRAME_BOUNDS")
    return boundaries


def native_render(case: str, src_mp4: Path, receipt: dict, dest: Path):
    evidence = ffprobe(src_mp4)
    n = evidence["frames"]
    bounds = timeline_boundaries(receipt, n)
    sweep = verify_entire_timeline(case, bounds)
    p = plan(case)
    tmp = dest.parent / f"{case}_video_no_audio.mp4"
    cmd = ["ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel",
           "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-",
           "-an", "-c:v", "libx264", "-preset", "ultrafast",
           "-crf", "27", "-pix_fmt", "yuv420p", str(tmp)]
    with subprocess.Popen(cmd, stdin=subprocess.PIPE,
                          stderr=subprocess.PIPE) as proc:
        for beat in range(5):
            first, last = bounds[beat], bounds[beat+1]
            for j in range(last-first):
                progress = min(1.0, j/max(1, int((last-first)*.58)))
                image = render_safe_frame(p, beat, progress)
                proc.stdin.write(image.tobytes())
        proc.stdin.close()
        proc.stdin = None
        stderr = proc.stderr.read().decode(errors="replace")
        exit_code = proc.wait()
        require(exit_code == 0, "ENCODER_FAILED_" + stderr[-150:])
    subprocess.run([
        "ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(tmp), "-i", str(src_mp4),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
        "-c:a", "copy", "-movflags", "+faststart", str(dest)
    ], check=True, timeout=120)
    tmp.unlink()
    new_media = ffprobe(dest)
    require(new_media["frames"] == n, "FINAL_VIDEO_FRAME_DRIFT")
    require(aac_sha(dest) == aac_sha(src_mp4), "FINAL_AAC_DRIFT")
    require(file_sha(dest) != file_sha(src_mp4), "NO_VIDEO_DIFFERENCE")
    full_decode(dest)
    return {"case_id": case, "old_mp4_sha256": file_sha(src_mp4),
            "new_mp4_sha256": file_sha(dest),
            "original_frames": n, "new_frames": new_media["frames"],
            "aac_elementary_sha256": aac_sha(dest),
            "audio_bitstream_parity": True, "full_decode": "PASS",
            "all_frame_geometry_checks": sweep["validated_frames"],
            "layout_gate": "PASS_TIMELINE_GEOMETRY_ONLY",
            "narration_claim_ids_unchanged": True,
            "process_condition": "UNKNOWN_NOT_VERIFIED" if "process" in case else "NOT_APPLICABLE",
            "human_quality": "UNRATED", "release": "BLOCKED"}


def comparison_sheet(case: str, original: Path, candidate: Path, out: Path):
    """Independent screenshots, not video post-processing or OCR."""
    times = ([4.2, 8.5, 11.0, 12.1, 15.0]
             if case.startswith("attention") else
             [8.6, 9.3, 10.8, 11.0, 12.4])
    width = 640
    height = 360
    sheet = Image.new("RGB", (width*len(times), height*2 + 48), (16, 18, 23))
    d = ImageDraw.Draw(sheet)
    for j, sec in enumerate(times):
        before = decode_frame(original, sec).resize((width, height))
        after = decode_frame(candidate, sec).resize((width, height))
        sheet.paste(before, (width*j, 22))
        sheet.paste(after, (width*j, height+44))
        d.text((width*j+8, 1), f"ORIGINAL {sec:.1f}s",
               fill=(240, 240, 240), font=font(14))
        d.text((width*j+8, height+23), f"V3-72 NEW {sec:.1f}s",
               fill=(180, 240, 190), font=font(14))
    sheet.save(out)
    return times


def run(source_zip: Path, output: Path) -> dict:
    require(not output.exists(), "FRESH_OUTPUT_REQUIRED")
    original = json.loads(REG.read_text(encoding="utf-8"))
    require(original["checkpoint"] == "V3-72" and
            original["parent"]["sha"] ==
            "67738eb4ea9d007841da53ab204157972b8328c0",
            "PREREG_DRIFT")
    expected = original["original_physical_sources"]
    with zipfile.ZipFile(source_zip) as zipped:
        with tempfile.TemporaryDirectory(prefix="v372-original-") as folder:
            raw = Path(folder)
            outcome = []
            # Select the two declared sources by exact path, never use an
            # unblinded V3-59 treatment key or mutate the archive.
            output.mkdir(parents=True)
            for case in SAFE_CASES:
                path = f"{case}/pedagogical_slice.mp4"
                original_receipt_path = f"{case}/receipt.json"
                require(path in zipped.namelist() and
                        original_receipt_path in zipped.namelist(),
                        "ORIGINAL_SOURCE_ARCHIVE_MISSING")
                old = raw / f"{case}-original.mp4"
                old.write_bytes(zipped.read(path))
                baseline = json.loads(zipped.read(original_receipt_path))
                require(file_sha(old) == expected[case]["sha256"] and
                        baseline["native_mp4_sha256"] == file_sha(old),
                        "FROZEN_SOURCE_SHA_DRIFT")
                new_path = output / f"v372_{case}_corrected.mp4"
                receipt = native_render(case, old, baseline, new_path)
                require(receipt["original_frames"] ==
                        expected[case]["video_frames_expected"], "SOURCE_FRAME_DRIFT")
                evidence_png = output / f"v372_{case}_before_after.png"
                receipt["comparison_timestamps_s"] = comparison_sheet(
                    case, old, new_path, evidence_png)
                receipt["comparison_png_sha256"] = file_sha(evidence_png)
                outcome.append(receipt)
            result = {
                "checkpoint": "V3-72",
                "status": "TECHNICAL_NATIVE_GEOMETRY_REPAIR_CHECKED",
                "versioned_video_count": 2,
                "cases": outcome, "original_9_masked_mp4_modified": False,
                "real_human_reviewers": 0,
                "viewer_final_review": "NOT_PASS_PENDING_INDEPENDENT_REVIEW",
                "human_quality": "UNRATED",
                "learning_gain": "NOT_MEASURED",
                "model_creativity": "NOT_TESTED",
                "provider_requests": 0,
                "main_merge": False, "production": "BLOCKED",
            }
            (output / "v372_native_receipt.json").write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n",
                encoding="utf-8")
            return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--v357-source-zip", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.v357_source_zip, args.output_dir),
                     indent=2, sort_keys=True))
