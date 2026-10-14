#!/usr/bin/env python3
"""V3-63 offline-host 5-role candidate admission/native impact, no model API."""
from __future__ import annotations
import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.five_role_creative_admission import (
    admit,test_only_packet,CASES,ROLE_NAMES,MAX_BYTES
)
from learnflow_v3.five_role_creative_native import native_compare
REG=ROOT/"benchmarks/learnflowbench/v3/v3_63_five_role_creativity_preregister.json"
PARENT="66671cecf8c11779cf5f5041df9254726a3d2de6"

def require(cond,code):
    if not cond:raise ValueError("V363_"+code)

def registration():
    d=json.loads(REG.read_text(encoding="utf-8"))
    require(d["checkpoint"]=="V3-63" and d["registration"]=="FIRST_CHILD_COMMIT" and
      d["parent_sha"]==PARENT and d["acceptance"]["no_llm_api"] is True and
      d["acceptance"]["model_authorship"]=="NOT_TESTED_NO_PROVIDER_RESPONSE" and
      d["acceptance"]["production"]=="BLOCKED","PREREG_CHANGED")
    require(tuple(d["allowed_cases"])==CASES and
            tuple(d["role_order"])==ROLE_NAMES and
            d["max_candidate_bytes"]==MAX_BYTES,"TEST_SCOPE_DRIFT")
    return d

def run(src:Path,out:Path):
    d=registration()
    require(not out.exists(),"OUTPUT_EXISTS")
    # Three independent host ledgers. Two test-only decisions each are admitted,
    # but no one claims six provider-generated creative proposals.
    family=[]
    for case in CASES:
        proposals=[]
        for variant in (0,1):
            raw=test_only_packet(case,variant)
            typed,decision=admit(raw)
            proposals.append({"wire_sha256":sha256(raw).hexdigest(),
                 "test_only":True,"case_id":case,
                 "visual_focus":decision["focus_mode"],
                 "transformation_profile":decision["transformation_profile"]})
        require(proposals[0]["visual_focus"]!=proposals[1]["visual_focus"] and
                proposals[0]["transformation_profile"]!=proposals[1]["transformation_profile"],
                "DECISIONS_NOT_DISTINCT")
        family.append({"case_id":case,"variants":proposals})
    # Native evidence on one preregistered heldout topic; other two only undergo
    # candidate validation and direct frame tests (see strict Python tests).
    case=CASES[1]
    result=native_compare(src,out,(test_only_packet(case,0),test_only_packet(case,1)))
    result.update({"prereg_sha256":sha256(REG.read_bytes()).hexdigest(),
      "five_role_cases_admitted":family,
      "actual_model_generated_proposals":0,"model_provider_calls":0,
      "quality":"UNRATED","student_learning":"NOT_MEASURED",
      "production":"BLOCKED"})
    (out/"v363_receipt.json").write_text(json.dumps(result,indent=2)+"\n")
    print("V363_BOUNDED_FIVE_ROLE_NATIVE_TECHNICAL",json.dumps({
      "cases":len(family),"candidate_proposals_test_only":6,
      "native_count":result["native_candidate_count"],
      "native_candidate_MAD":result["cross_candidate_frame_MAD_at_transform"],
      "actual_model_generated":0,"production":"BLOCKED"}),flush=True)
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--frozen-v362-artifact",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    run(args.frozen_v362_artifact,args.output)
