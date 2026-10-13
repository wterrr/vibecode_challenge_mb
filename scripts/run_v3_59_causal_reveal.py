#!/usr/bin/env python3
"""V3-59 strictly offline 3-way semantic reveal repair, no model provider."""
from __future__ import annotations
import argparse
import json
import sys
import csv
import shutil
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from learnflow_v3.matched_pedagogy_ablation import IDS,require,sha,probe,aac_sha,CRITERIA,RATINGS_FIELDS
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
            r["acceptance"]["no_main_merge"] is True,
            "INVALID_RELEASE_SCOPE")
    return r

def create_three_arm_packet(src:Path, v358:Path, out:Path, results):
    """All three arms share source narration, count & facts; mask CONDITIONS, not visuals."""
    target=out/"reviewer_blinded"
    require(not target.exists(),"REVIEW_PACKET_EXISTS")
    target.mkdir(parents=True)
    mapping={"checkpoint":"V3-59","reviewer_key_separate":True,
             "independent_reviewers":0,"quality":"UNRATED","cases":{}}
    records=[]
    for case in IDS:
        original=src/case/"pedagogical_slice.mp4"
        static=v358/"paired"/case/"static_control.mp4"
        repair=out/case/"causal_revision.mp4"
        paths={"original_motion":original,"static_end_state":static,
               "causal_reveal":repair}
        require(all(p.is_file() for p in paths.values()),"ARM_MISSING")
        audio={name:aac_sha(p) for name,p in paths.items()}
        frames={name:probe(p)["video_frames"] for name,p in paths.items()}
        require(len(set(audio.values()))==1,"THREE_ARM_AUDIO_MISMATCH")
        require(len(set(frames.values()))==1,"THREE_ARM_FRAME_MISMATCH")
        order=sorted(paths,key=lambda name: sha256(
            (PARENT+case+name).encode()).hexdigest())
        mapping["cases"][case]={}
        for j,arm in enumerate(order):
            clip=f"{case}_{chr(65+j)}.mp4"
            shutil.copyfile(paths[arm],target/clip)
            mapping["cases"][case][clip]={"treatment":arm,
                    "sha256":sha(target/clip)}
            records.append({"rater_id":"","case_id":case,"clip_id":clip,
                  **{criterion:"" for criterion in CRITERIA},
                  "confidence":"","failure_notes":""})
    with (target/"blank_review.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=RATINGS_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    (target/"REVIEWER_INSTRUCTIONS.txt").write_text(
        "V3-59 review packet: three condition-masked native videos per topic.\n"
        "Please rate all nine clips independently for clarity, causal witness,\n"
        "referent continuity, readability and pacing (ordinal 1-5), or leave blank.\n"
        "Log specific seconds for early answers or misleading transformations.\n"
        "All clips within a topic preserve factual host evidence, narration and duration.\n"
        "Treatment is visually inferable; this is NOT double-blind.\n"
        "No data have been collected; scores are blank by design.\n"
        "No rating alone proves a student learning improvement.\n",
        encoding="utf-8")
    (out/"admin_treatment_key.json").write_text(
        json.dumps(mapping,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return {"masked_clips":len(records),"complete_external_raters":0,
            "quality":"UNRATED_NO_REVIEWERS",
            "all_three_arms_native_AAC_and_video_frames_matched":True}



def validate_three_arm_reviews(rows, admin_key, minimum_raters=3):
    """Quality cannot be declared rated without a real complete masked panel."""
    expected={(case,clip) for case,clips in admin_key["cases"].items()
              for clip in clips}
    if not rows:
        return {"quality":"UNRATED_NO_REVIEWERS","independent_raters":0,
                "student_learning_gain":"NOT_MEASURED","gate":"NO_GO"}
    seen=set()
    raters=set()
    for r in rows:
        rid=str(r.get("rater_id","")).strip()
        pair=(r.get("case_id"),r.get("clip_id"))
        require(bool(rid) and pair in expected,"REVIEW_CASE_OR_RATER_INVALID")
        require((rid,pair) not in seen,"DUPLICATE_REVIEW")
        seen.add((rid,pair))
        raters.add(rid)
        for criterion in CRITERIA:
            val=str(r.get(criterion,"")).strip()
            require(val in ("","1","2","3","4","5"),
                    "INVALID_SUBJECTIVE_RATING")
    for rid in raters:
        require({pair for r,pair in seen if r==rid}==expected,
                "INCOMPLETE_NINE_VIDEO_PANEL")
    if len(raters)<minimum_raters:
        return {"quality":"INSUFFICIENT_INDEPENDENT_REVIEWERS",
                "independent_raters":len(raters),
                "student_learning_gain":"NOT_MEASURED","gate":"NO_GO"}
    return {"quality":"RATINGS_RECEIVED_PENDING_PROVENANCE_AUDIT",
            "independent_raters":len(raters),
            "student_learning_gain":"NOT_MEASURED",
            "gate":"PANEL_PRESENT_NOT_LEARNING_PROOF"}

def run(src:Path, v358:Path, out:Path):
    registration()
    require(not out.exists(),"FRESH_OUTPUT_REQUIRED")
    out.mkdir(parents=True)
    matches=[]
    for cid in IDS:
        match=build_revision(src/cid/"pedagogical_slice.mp4",
                             src/cid/"receipt.json",out/cid)
        matches.append(match)
    packet=create_three_arm_packet(src,v358,out,matches)
    result={
        "checkpoint":"V3-59","parent_pr":92,
        "parent_sha":PARENT,"prereg_commit":PREREG,
        "results":matches,
        "masked_three_arm_reviewer_packet":packet,
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
    parser.add_argument("--v358-dir",type=Path,required=True,
                        help="Fresh, verified V3-58 static control output")
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    run(args.v357_dir,args.v358_dir,args.output_dir)
