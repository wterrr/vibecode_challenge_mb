#!/usr/bin/env python3
"""V3-59 strictly offline 3-way semantic reveal repair, no model provider."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from learnflow_v3.matched_pedagogy_ablation import IDS,require
from learnflow_v3.causal_reveal import build_revision,verify_reveal_progression
from learnflow_v3.pedagogical_storytelling_slice import plan

REG=ROOT/"benchmarks/learnflowbench/v3/v3_59_causal_reveal_preregister.json"
PARENT="d9d8830c0486a0c25b0ca924a091084b267425fe"
PREREG="148f1b73cdedce9ed1b1e4af6a9d5251d33903c4"

def registration():
    r=json.loads(REG.read_text(encoding="utf-8"))
    require(r["checkpoint"]=="V3-59" and r["parent_sha"]==PARENT and
            r["registration_kind"]=="FIRST_CHILD_COMMIT" and
            r["registered_before_implementation"] is True, "PREREG_FAILED")
    require(r["cases"]==list(IDS) and
            r["acceptance"]["no_new_model_API"] and
            r["acceptance"]["production"]=="BLOCKED" and
            not r["acceptance"]["no_main_merge"] is False,
            "INVALID_RELEASE_SCOPE")
    return r

def run(src:Path,out:Path):
    registration()
    require(not out.exists(),"FRESH_OUTPUT_REQUIRED")
    out.mkdir(parents=True)
    matches=[]
    for cid in IDS:
        match=build_revision(src/cid/"pedagogical_slice.mp4",
                             src/cid/"receipt.json",out/cid)
        matches.append(match)
    result={
        "checkpoint":"V3-59","parent_pr":92,
        "parent_sha":PARENT,"prereg_commit":PREREG,
        "results":matches,
        "all_semantic_gates_host_pass":all(
            m["semantic_gate"]["semantic_gate"]=="PASS_HOST_ONLY" for m in matches),
        "all_audio_packets_equal":all(
            m["original_AAC_SHA256"]==m["revision_AAC_SHA256"] for m in matches),
        "all_decoded_frames_equal":all(
            m["physical_frames_source"]==m["physical_frames_revision"] for m in matches),
        "zero_model_api_posts":True,
        "external_reviewer_count":0,"native_word_alignment":"UNMEASURED",
        "independent_pedagogical_quality":"UNRATED_NO_REVIEWERS",
        "human_learning_gain":"NOT_MEASURED",
        "model_creativity":"NOT_TESTED",
        "production":"BLOCKED"
    }
    (out/"v359_results.json").write_text(json.dumps(result,indent=2)+"\n",
                                          encoding="utf-8")
    print("V359=BOUNDED_HOST_REVEAL_NATIVE_NOT_PEDAGOGICAL_QUALITY",
          flush=True)
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--v357-dir",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    run(args.v357_dir,args.output_dir)
