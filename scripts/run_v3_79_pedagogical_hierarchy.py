#!/usr/bin/env python3
"""V3-79 rerender 3 FROZEN host-synthetic scenes with a bounded composition.

No provider, model, human rating, or source video edits. Emit real versioned
H264/AAC and compare Manim SVG native statistics against prereg V3-78.
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
from scripts.run_v3_54_model_candidate_quality import case_run,NAMES,registered

REG=ROOT/"benchmarks/learnflowbench/v3/v3_79_visual_hierarchy_preregister.json"

def run(out):
    reg=json.loads(REG.read_text())
    if (reg["checkpoint"]!="V3-79" or reg["kind"]!="FIRST_CHILD_PREREG_BEFORE_CODE"
        or reg["parent"]["sha"]!="de011bad4e76c7dd15110ac0085384fbd931e3b9"
        or reg["restrictions"]["model_api_calls"]!=0):
        raise Blocked("V379_PREREG_INVALID")
    if out.exists():raise Blocked("V379_FRESH_DIR_REQUIRED")
    registered()
    out.mkdir(parents=True)
    baselines={c["id"]:dict(c) for c in reg["baseline"]["host_synthetic_fixtures"]} if isinstance(reg["baseline"]["host_synthetic_fixtures"][0],dict) else {}
    names=list(NAMES)
    med=dict(zip(names,reg["baseline"]["native_content_bbox_median_fraction"]))
    small=dict(zip(names,reg["baseline"]["small_text_groups_native_under_24px"]))
    originals=fixtures()
    cases=[]
    for name,source_id in NAMES.items():
        folder=out/name
        receipt,_=case_run(name,originals[source_id],folder,
                           strict_v375=True,runtime_v376=True,
                           reflow_v377=True,hierarchy_v379=True)
        movie=folder/"mock_candidate_native.mp4"
        telemetry=folder/"manim_output"/"v376_runtime_geometry.jsonl"
        assert receipt["v379_visual_hierarchy_source"]["evidence_claims_modified"] is False
        physical=inspect(movie,telemetry,receipt["av"]["frames"])
        metrics=physical["visual_salience_measurements"]
        if physical["native_movie_sha256"]!=receipt["native_mp4_sha256"]:
            raise Blocked("V379_PHYSICAL_MOVIE_SHA_DRIFT")
        if len(physical["native"]["decoded_samples"])!=9:
            raise Blocked("V379_NATIVE_FRAME_WITNESSES_MISSING")
        if receipt["v376_runtime_native_readability"]["status"]!="PASS_BOUNDED_RUNTIME_READABILITY":
            raise Blocked("V379_EXISTING_CMU_GLYPH_GATE_FAILED")
        (folder/"v379_native_visual_hierarchy_receipt.json").write_text(
            json.dumps(physical,indent=2,sort_keys=True)+"\n")
        cases.append({
            "id":name,"native_h264_frames":receipt["av"]["frames"],
            "native_mp4_sha256":physical["native_movie_sha256"],
            "v3_78_old_median_bbox_fraction":med[name],
            "v3_79_new_median_bbox_fraction":metrics["bbox_union_area_fraction_median"],
            "old_text_groups_under24px":small[name],
            "new_text_groups_under24px":metrics["text_groups_below_24px_native"],
            "native_text_groups":metrics["effective_native_text_groups"],
            "physical_pixel_samples":len(physical["native"]["decoded_samples"]),
            "runtime_ticks":metrics["runtime_ticks"],
            "visual_difference":"MEASURED_NOT_HUMAN_RATED",
            "model_authorship":"HOST_SYNTHETIC_ONLY"})
    out_receipt={"checkpoint":"V3-79",
                 "status":"NATIVE_COMPOSITION_COMPARISON_READY_FOR_HUMAN_REVIEW",
                 "cases":cases,"accepted_native_video_count":len(cases),
                 "new_physical_decoded_frame_witnesses":sum(x["physical_pixel_samples"] for x in cases),
                 "semantic_beat_order":"ORIGINAL_NOT_CHANGED",
                 "original_mp4_and_study_controls_overwritten":False,
                 "provider_model_api_calls":0,
                 "learning_gain":"NOT_MEASURED",
                 "3blue1brown_parity":"NOT_PROVEN",
                 "final_visual_quality":"NOT_PASS_PENDING_HUMAN_REVIEW",
                 "production":"BLOCKED"}
    (out/"v379_native_pedagogical_hierarchy_comparison.json").write_text(
        json.dumps(out_receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out_receipt,indent=2,sort_keys=True))
    return out_receipt

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",required=True,type=Path)
    run(p.parse_args().output_dir)
