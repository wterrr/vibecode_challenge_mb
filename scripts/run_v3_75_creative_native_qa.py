#!/usr/bin/env python3
"""V3-75 real creative SceneGraph-Manim-H264/AAC strict visual QA trial.

The three V3-54 historical mocks are separately accepted/rejected. Never
silently skip a failed scene or replace a frozen experiment: NO-GO cases
remain explicit and versioned. Zero model API calls.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_scene_fixtures import fixtures
from scripts.run_v3_54_model_candidate_quality import case_run,NAMES
from scripts.run_v3_54_model_candidate_quality import registered as v354_registered

REG=ROOT/"benchmarks/learnflowbench/v3/v3_75_creative_native_qa_preregister.json"


def main(out:Path):
    reg=json.loads(REG.read_text())
    if (reg["checkpoint"]!="V3-75" or
        reg["kind"]!="FIRST_CHILD_BEFORE_IMPLEMENTATION" or
        reg["parent"]["sha"]!="daace9c14ad51fc08f150e44692885da2a325fce" or
        reg["boundary"]["model_api_post"]!=0):
        raise Blocked("V375_PREREGISTRATION_DRIFT")
    v354_registered()
    if out.exists():raise Blocked("V375_OUTPUT_ALREADY_EXISTS")
    out.mkdir(parents=True)
    existing=fixtures()
    cases=[]
    for name,original_id in NAMES.items():
        path=out/name
        try:
            receipt,_=case_run(name,existing[original_id],path,strict_v375=True)
        except Blocked as exc:
            reason=str(exc)
            if not reason.startswith(("V375_","V351_","V373_")):
                # Unexpected render/codec error is NOT a registered layout
                # abstention and should break CI loudly rather than hide.
                raise
            cases.append({"id":name,"status":"NO_GO_FAIL_CLOSED",
                          "block_code":reason[:200],
                          "source":"HOST_SYNTHETIC_NOT_MODEL"})
        else:
            qa=receipt["v375_creative_integrated_quality_gate"]
            if qa["status"]!="PASS_BOUNDED_NATIVE_CREATIVE_QUALITY_GATE":
                raise Blocked("V375_NATIVE_CASE_NOT_CERTIFIED")
            cases.append({"id":name,"status":"TECHNICAL_BOUNDED_PASS",
                          "native_video_sha256":receipt["native_mp4_sha256"],
                          "video_frames":receipt["av"]["frames"],
                          "preframe_checked":qa["reserved_source"]["all_physical_frame_times_reserved"],
                          "native_decoded_proxy":qa["native_decoded_proxy"],
                          "source":"HOST_SYNTHETIC_NOT_MODEL"})
    report={"checkpoint":"V3-75","status":("BOUNDED_PASS_WITH_REJECTED_CASES" if
              any(x["status"]=="TECHNICAL_BOUNDED_PASS" for x in cases)
              else "NO_GO_NO_CERTIFIED_CREATIVE_NATIVE_OUTPUT"),
            "cases":cases,"original_v354_experiment_unchanged":True,
            "model_api_calls":0,"real_model_authorship":"NOT_TESTED",
            "all_renderer_pipelines_covered":False,
            "all_frame_actual_manim_glyph_collision_certified":False,
            "production":"BLOCKED","learning_gain":"NOT_MEASURED",
            "human_quality":"UNRATED"}
    (out/"v375_final_creative_native_qa_receipt.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,indent=2,sort_keys=True))
    return report


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",type=Path,required=True)
    main(ap.parse_args().output_dir)
