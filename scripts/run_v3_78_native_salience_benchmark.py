#!/usr/bin/env python3
"""V3-78 evidence-first native salience benchmark (never a human quality grade).

Reuses original V3-77 render+geometry/native-A3 gates unmodified, then adds
a separate host-read-only visual footprint/legibility audit on the *new*
physical H264 MP4s and Manim SVG telemetry. No source/video manipulation.
"""
from __future__ import annotations

import argparse,hashlib,json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.v378_native_visual_salience import inspect
from scripts.run_v3_77_native_comparison_layout import run as old_run

REG=ROOT/"benchmarks/learnflowbench/v3/v3_78_native_salience_preregister.json"


def main(output:Path):
    r=json.loads(REG.read_text())
    if (r["checkpoint"]!="V3-78"
        or r["kind"]!="FIRST_CHILD_PREREG_BEFORE_IMPLEMENTATION"
        or r["parent"]["sha"]!="cd821f1dbbd0abb343d5f99538713853bd964ddd"
        or r["restrictions"]["model_calls"]!=0):
        raise Blocked("V378_PREREG_CHANGED")
    old=old_run(output)
    if old["accepted_count"]!=3:
        raise Blocked("V378_UPSTREAM_V377_PHYSICAL_VIDEO_REGRESSION")
    cases=[]
    for record in old["cases"]:
        folder=output/record["id"]
        movie=folder/"mock_candidate_native.mp4"
        telemetry=folder/"manim_output"/"v376_runtime_geometry.jsonl"
        # Deny a "PASS" if V3-77 native receipt differs from physical MP4.
        if (record["verdict"]!="BOUNDED_TECHNICAL_PASS" or
            record["candidate_native_sha256"]!=hashlib.sha256(movie.read_bytes()).hexdigest()):
            raise Blocked("V378_UPSTREAM_MOVIE_SHA_DRIFT")
        report=inspect(movie,telemetry,record["native_frames"])
        if report["status"]!="PHYSICAL_MEASUREMENTS_REVIEW_READY_NOT_VISUAL_PASS":
            raise Blocked("V378_AUDIT_RECEIPT_INVALID")
        (folder/"v378_native_visual_salience_receipt.json").write_text(
            json.dumps(report,indent=2,sort_keys=True)+"\n")
        m=report["visual_salience_measurements"]
        cases.append({
            "id":record["id"],
            "native_h264_frames":record["native_frames"],
            "mp4_sha256":report["native_movie_sha256"],
            "telemetry_sha256":report["runtime_telemetry_sha256"],
            "content_bbox_union_area_median":m["bbox_union_area_fraction_median"],
            "content_bbox_union_area_p10":m["bbox_union_area_fraction_p10"],
            "longest_no_scene_content_approx_seconds":
                m["longest_chrome_only_streak_approx_seconds"],
            "native_text_groups_under_24px":m["text_groups_below_24px_native"],
            "verified_native_pixel_samples":len(report["native"]["decoded_samples"]),
            "scope":"QUANTITATIVE_REVIEW_ONLY_NOT_PEDAGOGICAL_RATING"})
    final={"checkpoint":"V3-78",
           "verdict":"RESEARCH_MEASUREMENTS_READY_HUMAN_REVIEW_REQUIRED",
           "original_host_fixtures":[x["id"] for x in cases],
           "cases":cases,
           "actual_new_Manim_native_mp4_count":len(cases),
           "native_h264_pixel_sample_count_total":
               sum(x["verified_native_pixel_samples"] for x in cases),
           "model_api_calls":0,
           "historical_media_overwritten":False,
           "real_model_authorship":"NOT_TESTED",
           "human_visual_quality":"NOT_PASS_PENDING_REVIEW",
           "learning_gain":"NOT_MEASURED",
           "production":"BLOCKED"}
    (output/"v378_final_native_salience_scorecard.json").write_text(
        json.dumps(final,indent=2,sort_keys=True)+"\n")
    print(json.dumps(final,indent=2,sort_keys=True))
    return final


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    main(p.parse_args().output_dir)
