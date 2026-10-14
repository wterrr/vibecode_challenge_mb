#!/usr/bin/env python3
"""V3-62 preregistered held-out native comparison; NO MODEL API."""
from __future__ import annotations
import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.creative_pedagogical_director import (
    CASES, ORIGIN, ACTS, candidate, exact_facts, digest, receipt
)
from learnflow_v3.creative_pedagogical_native import (
    build_pair, render_frame, W,H,FPS
)

REG=ROOT/"benchmarks/learnflowbench/v3/v3_62_creative_storytelling_preregister.json"
PARENT="a9473bef73f0dbf63a921bdbdb9bcacf2f1321f2"
STYLE={"probability_complement_3_of_8":"focus_first",
       "constant_speed_distance":"witness_first",
       "water_reaction_balance":"focus_first"}

def require(ok,code):
    if not ok:raise AssertionError("V362_"+code)

def registration():
    d=json.loads(REG.read_text(encoding="utf-8"))
    require(d["checkpoint"]=="V3-62" and
            d["reference_parent_sha"]==PARENT and
            d["registration"]=="FIRST_CHILD_COMMIT" and
            d["registered_before_implementation"] is True,"PREREG_DRIFT")
    require(tuple(x["id"] for x in d["frozen_heldout_topics"])==CASES,
            "HELDOUT_SELECTION_CHANGED")
    require(d["physical_frozen_acceptance"]["video_cases"]==3 and
            d["physical_frozen_acceptance"]["matched_control_pairs"]==3 and
            d["physical_frozen_acceptance"]["model_authorship"]=="NOT_TESTED" and
            d["physical_frozen_acceptance"]["human_visual_quality"]=="UNRATED" and
            d["physical_frozen_acceptance"]["production"]=="BLOCKED",
            "UNSUPPORTED_ACCEPTANCE")
    held=d["frozen_heldout_topics"]
    for row in held:
        x=exact_facts(row["id"])
        if row["id"]==CASES[0]:
            require(x["total"]==row["exact_facts"]["total"] and
                x["remaining"]==row["exact_facts"]["complement"] and
                x["selected"]==row["exact_facts"]["favorable"],"PROB_TRUTH_DRIFT")
        elif row["id"]==CASES[1]:
            require(x["velocity_m_per_s"]==row["exact_facts"]["speed_units_per_second"] and
                x["elapsed_s"]==row["exact_facts"]["elapsed_seconds"] and
                x["final_distance_m"]==row["exact_facts"]["displacement_units"],
                "PHYSICS_TRUTH_DRIFT")
        else:
            require(x["reactant_atoms"]==row["exact_facts"]["reactants"] and
                x["product_atoms"]==row["exact_facts"]["products"],
                "CHEM_TRUTH_DRIFT")
    return d

def run(out:Path):
    d=registration()
    require(not out.exists(),"OUTPUT_ALREADY_EXISTS")
    out.mkdir(parents=True)
    results=[]
    for case in CASES:
        plan=candidate(case,STYLE[case])
        r=receipt(plan)
        require(r["precondition_before_result"] is True and
                r["result_after_transformation"] is True,
                "CAUSAL_STORY_CLAIM_GATE")
        dest=out/case
        result=build_pair(plan,dest)
        results.append(result)
        print("V362_NATIVE_CASE",case, "FRAME",result["timeline"]["total_frames"],
              "CAUSAL_DELTA",result["causal_pre_to_witness_decoded_mean_RGB_abs_diff"],
              flush=True)
        # Share lightweight still evidence; not a complete video visual audit.
        for act,name in ((1,"setup"),(2,"transformation"),(3,"witness")):
            render_frame(plan,act,.25 if act==2 else 1).save(
                dest/(name+"_reference.png"))
    require(len(results)==d["physical_frozen_acceptance"]["video_cases"],
            "EXPECTED_CASE_COUNT")
    require(len({r["source_story"]["layout"] for r in results})==3,
            "ALL_HELDOUTS_SAME_LAYOUT")
    require(all(r["matched_audio_AAC"] and r["matched_physical_frames"]
                for r in results),"NATIVE_MATCHED_CONTROL_FAILURE")
    bundle={
        "checkpoint":"V3-62",
        "parent_sha":PARENT,
        "prereg_sha256":sha256(REG.read_bytes()).hexdigest(),
        "native_cases":results,
        "native_movie_count":6,
        "distinct_object_layouts":3,
        "creative_storytelling_method":"FINITE_HOST_GROUNDED_WITNESS_FIRST_OR_FOCUS_FIRST",
        "result":"TECHNICAL_BOUND_NATIVE_CANDIDATES_NOT_QUALITY_GO",
        "agent_genuine_freeform_creativity":"NOT_TESTED",
        "independent_human_pedagogical_quality":"UNRATED",
        "word_level_alignment":"UNMEASURED",
        "human_learning_effect":"NOT_MEASURED",
        "model_api_posts":0,
        "production":"BLOCKED"
    }
    (out/"v362_summary.json").write_text(json.dumps(bundle,indent=2)+"\n")
    return bundle

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(run(a.output_dir),indent=2))
