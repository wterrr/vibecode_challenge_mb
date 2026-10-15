#!/usr/bin/env python3
"""V3-80 one bounded native semantic-transform render/quality experiment.

Frozen synthetic host 3 lessons from V3-54, V3-79 exact visual hierarchy,
same TTS/narration/audio timing and actual V3-75/76/78 Manim gates.
No external model calls, no video editing or composited demonstration.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_scene_fixtures import fixtures
from learnflow_v3.v378_native_visual_salience import inspect
from learnflow_v3.v380_native_semantic_witness import check_growth
from scripts.run_v3_54_model_candidate_quality import case_run,NAMES,registered

REG=ROOT/"benchmarks/learnflowbench/v3/v3_80_semantic_transformations_preregister.json"

def run(directory:Path):
    p=json.loads(REG.read_text())
    if (p["checkpoint"]!="V3-80" or
        p["kind"]!="FIRST_CHILD_PREREG_BEFORE_CODE" or
        p["parent"]["sha"]!="2f98efaeabb21440aafdafa9d5bfb31e98d4e9f2" or
        p["restrictions"]["model_api_calls"]!=0):
        raise Blocked("V380_PREREG_DRIFT")
    if directory.exists():raise Blocked("V380_REQUIRES_NEW_VERSIONED_ARTIFACT")
    registered();directory.mkdir(parents=True)
    original=fixtures()
    summary=[]
    for name,source_id in NAMES.items():
        folder=directory/name
        doc,_=case_run(name,original[source_id],folder,
                       strict_v375=True,runtime_v376=True,reflow_v377=True,
                       hierarchy_v379=True,semantic_v380=True)
        movie=folder/"mock_candidate_native.mp4"
        telemetry=folder/"manim_output"/"v376_runtime_geometry.jsonl"
        event=doc["v380_semantic_transformations"]
        need=event.get("status")=="HOST_GROUNDED_FINITE_TRANSFORM_CONTRACT"
        if not need or event["verified_bar_growth_count"]<1 or event["verified_causal_route_count"]<1:
            raise Blocked("V380_SEMANTIC_HOST_EVENT_COVERAGE_MISSING")
        quality=inspect(movie,telemetry,doc["av"]["frames"])
        physical=check_growth(movie,event["events"],doc["av"]["frames"])
        if quality["native_movie_sha256"]!=doc["native_mp4_sha256"]:
            raise Blocked("V380_NEW_H264_SHA_DRIFT")
        if (len(quality["native"]["decoded_samples"])!=9 or
            physical["status"]!="DECODABLE_GROWTH_ATTESTED"):
            raise Blocked("V380_VIDEO_SEMANTIC_WITNESS_INCOMPLETE")
        (folder/"v380_independent_semantic_pixel_receipt.json").write_text(
            json.dumps({"content_readability":quality,
                        "growth_witness":physical},indent=2,sort_keys=True)+"\n")
        summary.append({
          "id":name,"native_video_sha256":quality["native_movie_sha256"],
          "encoded_h264_frames":doc["av"]["frames"],
          "verified_chart_growth_events":event["verified_bar_growth_count"],
          "verified_causal_routes":event["verified_causal_route_count"],
          "decoded_real_growth_witnesses":physical["witness_count"],
          "native_svg_glyph_qa":doc["v376_runtime_native_readability"]["status"],
          "native_visual_bbox_occupancy_median":
              quality["visual_salience_measurements"]["bbox_union_area_fraction_median"],
          "native_text_groups_under24px":
              quality["visual_salience_measurements"]["text_groups_below_24px_native"],
          "verified_content_pixel_samples":len(quality["native"]["decoded_samples"]),
          "narration_beat_total_seconds":event["narration_beat_total_seconds"],
          "provenance":"FROZEN_HOST_SYNTHETIC_NOT_MODEL"})
    summary_doc={
        "checkpoint":"V3-80",
        "status":"NATIVE_GROUNDED_TRANSFORMATIONS_READY_FOR_VIEWER_REVIEW",
        "cases":summary,
        "native_mp4_count":len(summary),
        "scalar_growth_events":sum(c["verified_chart_growth_events"] for c in summary),
        "host_ledger_causal_routes":sum(c["verified_causal_routes"] for c in summary),
        "independent_physical_growth_witnesses":sum(c["decoded_real_growth_witnesses"] for c in summary),
        "decoded_h264_visual_pixel_witnesses":sum(c["verified_content_pixel_samples"] for c in summary),
        "narration_storyboard_and_claims":"UNCHANGED",
        "moving_marker_may_enter_node":False,
        "model_provider_requests":0,
        "frozen_prior_mp4s_overwritten":False,
        "student_learning":"NOT_MEASURED",
        "visual_quality":"NOT_PASS_UNTIL_INDEPENDENT_HUMAN_REVIEW",
        "3blue1brown_parity":"NOT_PROVEN",
        "production":"BLOCKED"}
    if len(summary)!=3:raise Blocked("V380_MISSING_ORIGINAL_HELDOUT_CASE")
    (directory/"v380_final_host_semantic_video_report.json").write_text(
        json.dumps(summary_doc,indent=2,sort_keys=True)+"\n")
    print(json.dumps(summary_doc,indent=2,sort_keys=True))
    return summary_doc

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",type=Path,required=True)
    run(ap.parse_args().output_dir)
