#!/usr/bin/env python3
"""V3-77 real creative Manim comparison-layout repair: 3 frozen host mocks.

Create new fully narrated H264/AAC from original pre-existing model-shaped
synthetic candidates, with opt-in generic geometric reflow. Never alter
original frozen video or candidate JSON. Fail closed on missing native QA.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_scene_fixtures import fixtures
from scripts.run_v3_54_model_candidate_quality import case_run,NAMES,registered

REG=ROOT/"benchmarks/learnflowbench/v3/v3_77_extent_aware_comparison_preregister.json"

def run(out:Path):
    reg=json.loads(REG.read_text())
    if (reg["checkpoint"]!="V3-77" or
        reg["kind"]!="FIRST_CHILD_PREREG_BEFORE_IMPLEMENTATION" or
        reg["parent"]["sha"]!="06508f48299fc3098d2f81e8042c4a3a9ce1f20c" or
        reg["boundaries"]["no_model_api"] is not True):
        raise Blocked("V377_PREREGISTER_DRIFT")
    registered()
    if out.exists():raise Blocked("V377_FRESH_VERSIONED_DIRECTORY_REQUIRED")
    out.mkdir(parents=True)
    cases=[]
    fixed=fixtures()
    for name,case_id in NAMES.items():
        dest=out/name
        try:
            proof,_=case_run(name,fixed[case_id],dest,
                             strict_v375=True,runtime_v376=True,reflow_v377=True)
        except Blocked as exc:
            msg=str(exc)
            if not msg.startswith(("V377_","V375_","V373_","V376_","V351_")):
                raise
            native=dest/"mock_candidate_native.mp4"
            cases.append({"id":name,"verdict":"NO_GO",
                          "reason":msg[:240],
                          "candidate_native_exists":native.is_file(),
                          "candidate_native_sha256":sha256(native.read_bytes()).hexdigest()
                            if native.is_file() else None,
                          "native_quality":"NOT_CERTIFIED",
                          "host_fixture":"FROZEN_SYNTHETIC"})
        else:
            x=proof["v377_generated_extent_aware_comparison"]
            a=proof["v375_creative_integrated_quality_gate"]
            b=proof["v376_runtime_native_readability"]
            movie=dest/"mock_candidate_native.mp4"
            if (x["status"]!="GENERATED_GEOMETRY_CERTIFIED" or
                a["status"]!="PASS_BOUNDED_NATIVE_CREATIVE_QUALITY_GATE" or
                b["status"]!="PASS_BOUNDED_RUNTIME_READABILITY" or
                proof["native_mp4_sha256"]!=sha256(movie.read_bytes()).hexdigest()):
                raise Blocked("V377_NATIVE_RENDER_GATE_NOT_CERTIFIED")
            cases.append({"id":name,"verdict":"BOUNDED_TECHNICAL_PASS",
                          "native_frames":proof["av"]["frames"],
                          "runtime_rows":b["actual_runtime"]["runtime_samples"],
                          "decoded_pixel_samples":
                               b["decoded_native_pixels"]["sampled_real_decoded_frames"],
                          "candidate_native_exists":True,
                          "candidate_native_sha256":proof["native_mp4_sha256"],
                          "generated_geometry_sha256":
                            sha256((dest/"v377_generated_layout_receipt.json").read_bytes()).hexdigest(),
                          "host_fixture":"FROZEN_SYNTHETIC"})
    former=next(x for x in cases if x["id"]=="mock_token_network")
    p={"checkpoint":"V3-77",
       "status":"EVIDENCE_READY_NOT_AUTOMATIC_HUMAN_VISUAL_PASS",
       "cases":cases,
       "previously_blocked_case_verdict":former["verdict"],
       "corrected_comparison_accepted":former["verdict"]=="BOUNDED_TECHNICAL_PASS",
       "accepted_count":sum(x["verdict"]=="BOUNDED_TECHNICAL_PASS" for x in cases),
       "failed_closed_count":sum(x["verdict"]=="NO_GO" for x in cases),
       "source":"FROZEN_HOST_SYNTHETIC_NOT_REAL_MODEL",
       "old_study_videos_overwritten":False,
       "model_api_calls":0,
       "human_viewer_quality":"NOT_PASS_PENDING_FRESH_REVIEW",
       "pedagogical_quality":"UNRATED",
       "learning_gain":"NOT_MEASURED",
       "production":"BLOCKED"}
    (out/"v377_native_comparison_layout_repair_receipt.json").write_text(
        json.dumps(p,indent=2,sort_keys=True)+"\n")
    print(json.dumps(p,indent=2,sort_keys=True))
    return p

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",required=True,type=Path)
    args=ap.parse_args()
    run(args.output_dir)
