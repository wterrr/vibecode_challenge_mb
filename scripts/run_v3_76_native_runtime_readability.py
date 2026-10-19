#!/usr/bin/env python3
"""V3-76 true compiled Manim font/shape telemetry on three frozen host mocks.

NO-GO is a VALID evidence outcome, never mislabeled as geometry or quality
success. Native MP4s stay versioned and are never patched after rendering.
"""
from __future__ import annotations

import argparse,hashlib,json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_scene_fixtures import fixtures
from scripts.run_v3_54_model_candidate_quality import case_run,NAMES,registered
from learnflow_v3.v376_native_runtime_readability import RUNTIME_FILENAME

PREREG=ROOT/"benchmarks/learnflowbench/v3/v3_76_native_runtime_readability_preregister.json"

def run(output:Path)->dict:
    reg=json.loads(PREREG.read_text())
    if (reg["checkpoint"]!="V3-76" or
        reg["kind"]!="FIRST_CHILD_PREREG_BEFORE_IMPLEMENTATION" or
        reg["parent"]["sha"]!="612600ff1558a0e398bb19a96ac857d67a3b04a2" or
        reg["restrictions"]["no_model_api_post"] is not True):
        raise Blocked("V376_PREREGISTRATION_DRIFT")
    registered()
    if output.exists():raise Blocked("V376_FRESH_OUTPUT_REQUIRED")
    output.mkdir(parents=True)
    old=fixtures()
    cases=[]
    for name,source in NAMES.items():
        folder=output/name
        try:
            receipt,_=case_run(name,old[source],folder,
                               strict_v375=True,runtime_v376=True)
        except Blocked as e:
            code=str(e)
            if not code.startswith(("V375_","V376_","V373_","V351_")):
                raise
            video=folder/"mock_candidate_native.mp4"
            telemetry=folder/"manim_output"/RUNTIME_FILENAME
            cases.append({"id":name,"verdict":"NO_GO",
                          "reason":code[:240],
                          "physical_video_created":video.is_file(),
                          "runtime_telemetry_created":telemetry.is_file(),
                          "candidate_mp4_sha256":hashlib.sha256(
                             video.read_bytes()).hexdigest() if video.is_file() else None,
                          "candidate_visual_quality":"NOT_CERTIFIED",
                          "source":"HOST_SYNTHETIC_NOT_PROVIDER"})
        else:
            proof=receipt["v376_runtime_native_readability"]
            movie=folder/"mock_candidate_native.mp4"
            if (proof["movie_sha256"]!=hashlib.sha256(movie.read_bytes()).hexdigest()
                or proof["status"]!="PASS_BOUNDED_RUNTIME_READABILITY"):
                raise Blocked("V376_SUCCESS_RECEIPT_INVALID")
            cases.append({"id":name,"verdict":"TECHNICAL_BOUNDED_PASS",
                          "runtime_samples":proof["actual_runtime"]["runtime_samples"],
                          "native_video_frames":receipt["av"]["frames"],
                          "physical_video_created":True,
                          "runtime_telemetry_created":True,
                          "candidate_mp4_sha256":proof["movie_sha256"],
                          "native_pixel_samples":
                          proof["decoded_native_pixels"]["sampled_real_decoded_frames"],
                          "source":"HOST_SYNTHETIC_NOT_PROVIDER"})
    final={"checkpoint":"V3-76",
           "status":"EVIDENCE_READY_NOT_AUTOMATIC_VISUAL_PASS",
           "cases":cases,"accepted_cases":sum(x["verdict"]=="TECHNICAL_BOUNDED_PASS" for x in cases),
           "rejected_cases":sum(x["verdict"]=="NO_GO" for x in cases),
           "all_frame_exact_native_pixel_correspondence":False,
           "replaced_original_MP4s":False,
           "model_api_calls":0,"real_model_authorship":"NOT_TESTED",
           "pedagogical_quality":"UNRATED","learning_gain":"NOT_MEASURED",
           "human_final_visual_review":"NOT_PASS_PENDING_NEW_REVIEW",
           "production":"BLOCKED"}
    (output/"v376_research_gate_receipt.json").write_text(
        json.dumps(final,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(final,indent=2,sort_keys=True))
    return final

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",required=True,type=Path)
    args=parser.parse_args()
    run(args.output_dir)
