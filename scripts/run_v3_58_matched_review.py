#!/usr/bin/env python3
"""V3-58 matched native 3-family motion-vs-static review packet, zero model API."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.matched_pedagogy_ablation import (
    IDS,VERSION,require,sha,probe,aac_sha,source_case,
    render_static_control,make_review_packet,QUALITY
)
from learnflow_v3.pedagogical_authoring_readiness import (
    synthetic_candidate,certify_candidate
)

REG=ROOT/"benchmarks/learnflowbench/v3/v3_58_matched_pedagogy_preregister.json"
PARENT="48a7b8d955a442b5f693c7e8fcaae0f8c44effa8"

def check_registration():
    d=json.loads(REG.read_text(encoding="utf-8"))
    require(d["checkpoint"]=="V3-58" and d["parent_sha"]==PARENT and
            d["registered_before_implementation"] is True and
            d["registration_kind"]=="FIRST_CHILD_COMMIT","PREREG_DRIFT")
    require(d["cases"]==list(IDS) and
            d["acceptance"]["no_new_external_video_or_text_data"] is True and
            d["acceptance"]["zero_model_api_calls"] is True and
            d["acceptance"]["main_merge"] is False and
            d["acceptance"]["production"]=="BLOCKED","UNAPPROVED_STUDY")
    return d

def validate_agent_readiness():
    out={}
    for case in IDS:
        candidate=synthetic_candidate(case)
        proof=certify_candidate(candidate)
        require(proof["origin"]=="OFFLINE_SYNTHETIC_NOT_MODEL_AUTHORED" and
                proof["real_model_authoring"]=="NOT_TESTED" and
                proof["pedagogical_quality"]=="UNRATED","AUTHORING_NOT_QUALIFIED")
        out[case]=proof
    return {"origin":"OFFLINE_SYNTHETIC_NOT_MODEL_AUTHORED",
            "model_api_posts":0,"model_authorship":"NOT_TESTED",
            "synthetic_schema_validations":out,"production":"BLOCKED"}

def run(src:Path,output:Path):
    reg=check_registration()
    require(not output.exists(),"FRESH_OUTPUT_REQUIRED")
    output.mkdir(parents=True)
    res=[]
    for case in IDS:
        source=src/case/"pedagogical_slice.mp4"
        receipt=src/case/"receipt.json"
        match=render_static_control(source,receipt,output/"paired"/case)
        res.append(match)
    key=make_review_packet(res,output/"reviewer_blinded",PARENT)
    (output/"admin_unblind_key.json").write_text(
        json.dumps(key,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    ready=validate_agent_readiness()
    result={
      "checkpoint":"V3-58","parent_sha":PARENT,
      "first_preregister_commit":"9a2c0b0881e2ca9451888ae09b0cf5ecb560b50d",
      "source":"HOST_SYNTHETIC_NOT_MODEL_AUTHORED",
      "condition_a":"MOTION_AS_V357",
      "condition_b":"STATIC_END_STATE_WITHIN_BEAT",
      "matches":res,"pairs":len(res),"blinded_video_count":6,
      "intervention_confound":"STATIC_END_STATE_REVEALED_EARLY",
      "source_receipt_frame_discrepancies":[x["receipt_frame_delta"] for x in res],
      "equal_native_frames":all(x["source_receipt_frames"]-x["receipt_frame_delta"] ==
                      x["source_actually_decoded_frames"] for x in res),
      "audio_bitstream_equal_per_pair":all(x["source_audio_packet_sha256"]==
                                  x["control_audio_packet_sha256"] for x in res),
      "original_3b1b_media_used":False,"external_reviewer_count":0,
      "independent_quality":QUALITY,"human_learning_effect":"NOT_MEASURED",
      "genuine_llm_pedagogical_authoring":"NOT_TESTED",
      "authoring_ready_for_synthetic_fixtures":ready,
      "model_api_posts":0,"main_merge":False,"production":"BLOCKED"
    }
    (output/"v358_results.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("V358=THREE_MATCHED_PAIRS_NATIVE_CODEC_AUDIO_PARITY_REVIEW_UNRATED",
          flush=True)
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--v357-dir",type=Path,required=True,
                        help="Existing exact V3-57 native source output directory")
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    run(args.v357_dir,args.output_dir)
