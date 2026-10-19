#!/usr/bin/env python3
"""V3-74 strict process-only REAL host Manim -> Docker -> FFmpeg native QA.

Synthetic source JSON, actual narrated H264/AAC native video, no LLM API.
The old V3-45 two-family default remains unchanged and uninstrumented.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from learnflow_v3.creative_manim_ablation import Blocked
from scripts.run_v3_45_semantic_offline import run as run_real_manim

PREREG=ROOT/"benchmarks/learnflowbench/v3/v3_74_native_manim_qa_preregister.json"
FIXTURE="v345-synthetic-process"


def run(destination:Path)->dict:
    frozen=json.loads(PREREG.read_text())
    if (frozen["checkpoint"]!="V3-74" or
        frozen["parent"]["sha"]!="0eb88ad7116637799fa662af9ebafbbff6127341" or
        frozen["kind"]!="FIRST_CHILD_PREREG_BEFORE_CODE" or
        frozen["prohibitions"]["model_api_post"]!=0):
        raise Blocked("V374_PREREGISTRATION_DRIFT")
    if destination.exists():
        raise Blocked("V374_OUTPUT_MUST_BE_NEW")
    destination.mkdir(parents=True)
    report=run_real_manim(ROOT,destination,quality_gate_v374=True,
                          selected_fixtures={FIXTURE})
    if len(report["cases"])!=1 or report["cases"][0]["fixture_id"]!=FIXTURE:
        raise Blocked("V374_UNEXPECTED_VIDEO_PATH")
    item=report["cases"][0]
    verdict=item["v374_strict_native_visual_quality_gate"]
    movie=destination/FIXTURE/"offline_host_semantic_with_audio.mp4"
    if (not movie.is_file() or
        verdict["status"]!="PASS_BOUNDED_REAL_MANIM_PROCESS_ROUTE" or
        verdict["output_mp4_sha256"]!=hashlib.sha256(movie.read_bytes()).hexdigest() or
        verdict["post_render_native"]["full_decode"]!="PASS"):
        raise Blocked("V374_NATIVE_INTEGRATION_NOT_CERTIFIED")
    # Preserve actual H264/AAC metadata in evidence, not the toy V3-73 silent clips.
    streams=json.loads(subprocess.check_output(
        ["ffprobe","-v","error","-show_streams","-of","json",str(movie)],
        timeout=50))["streams"]
    video=next(x for x in streams if x["codec_type"]=="video")
    audio=next(x for x in streams if x["codec_type"]=="audio")
    if (video["codec_name"],video["width"],video["height"],
        video["r_frame_rate"],audio["codec_name"])!=("h264",1280,720,"15/1","aac"):
        raise Blocked("V374_NATIVE_VIDEO_AUDIO_CODEC_DRIFT")
    beats=verdict["pre_render_geometry"]["traversal_segments"]
    if len(beats)!=2 or sum(x["frames"] for x in beats)<10:
        raise Blocked("V374_TRAVERSAL_COVERAGE_MISSING")
    lock={
        "checkpoint":"V3-74",
        "status":"TECHNICAL_PASS_BOUNDED_MANIM_PROCESS_PATH",
        "route":"HOST_JSON->STRICT_PYDANTIC->MANIM_DOCKER->FFMPEG->DECODED_NATIVE_QA",
        "input_origin":"SYNTHETIC_OFFLINE_JSON_MODEL_FACING_NOT_LIVE_MODEL",
        "family":"ordered_process",
        "codec":"H264/AAC","resolution":[1280,720],"fps":15,
        "native_video_frames":int(video["nb_frames"]),
        "output_mp4_sha256":verdict["output_mp4_sha256"],
        "generic_geometry_traversal_frames":sum(x["frames"] for x in beats),
        "decoded_native_process_pixel_witness":
            verdict["post_render_native"]["decoded_pixel_witness"],
        "pipeline_gate":"FAIL_CLOSED_PROCESS_ONLY",
        "not_supported":["fraction_equivalence","oblique_process",
                         "arbitrary_creative_renderer","whole_video_ocr_or_aesthetics"],
        "other_study_clips_modified":False,
        "model_calls":0,"pedagogical_quality":"UNRATED",
        "learning_gain":"NOT_MEASURED","production":"BLOCKED",
    }
    (destination/"v374_integrated_native_receipt.json").write_text(
        json.dumps(lock,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return lock


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",required=True,type=Path)
    a=ap.parse_args()
    print(json.dumps(run(a.output_dir),indent=2,sort_keys=True))
