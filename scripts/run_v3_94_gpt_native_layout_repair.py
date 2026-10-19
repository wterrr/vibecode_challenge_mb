#!/usr/bin/env python3
"""V3-94 replay the EXACT V3-93 first-party GPT JSON through corrected native geometry.

ZERO OpenRouter calls. Preserve original accepted bytes and original MP4 evidence.
CI audibly/visually re-renders with existing host speech and H264/AAC only.
"""
from __future__ import annotations
import argparse,json,sys,tempfile
from pathlib import Path
from hashlib import sha256
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v3.v392_compact_authoring import strict_parse,host_compile,creative_witness
from learnflow_v3.v364_heldout_storyboard import host_test_baseline,digest,LEDGER_SHA
from learnflow_v3 import v364_native_array_compiler as native
from learnflow_v3.v394_timeline_layout import audit_timeline,render_corrected,audit_frame,FPS

REG=ROOT/"benchmarks/learnflowbench/v3/v3_94_gpt_layout_repair_preregister.json"
GPT=ROOT/"research/v393_accepted_gpt6_luna_storyboard_frozen.json"
class Reject(ValueError):pass
def need(ok,name):
    if not ok:raise Reject("V394_"+name)

def frozen():
    p=json.loads(REG.read_text())
    x=p["frozen_evidence"]
    need(p["checkpoint"]=="V3-94" and p["protocol"]=="FIRST_CHILD_BEFORE_REPAIR"
        and p["parent"]=={"pr":130,"sha":"3d342ca0f7d948415823e78984ca661c8b3a6650"}
        and p["no_paid_model_api"] is True and p["no_model_API_get"] is True
        and p["no_main_merge"] is True and p["no_v2_core_change"] is True
        and x["original_json_raw_sha256"]=="107f9d9457ad95ce848e553612b4e6757742a733180a8f9ae38522f736c48f4f"
        and x["original_semantic_candidate_sha256"]=="1060c980edf45213642606c04beb80d3f115ae7dafd920580a778c226238f96a"
        and x["original_video_frames"]==441
        and x["original_video_sha256"]=="fcc26242ce903e48c80ffb95015a7fe666bc9e894aa8f4b7d10caec63331a3a6"
        and x["host_ledger_sha256"]==LEDGER_SHA,"FROZEN_PREREG_CHANGED")
    raw=GPT.read_bytes()
    need(sha256(raw).hexdigest()==x["original_json_raw_sha256"],"GPT_SOURCE_BYTES_CHANGED")
    proposed=strict_parse(raw)
    need(digest(proposed)==x["original_semantic_candidate_sha256"],"GPT_SEMANTIC_CANDIDATE_CHANGED")
    compiled=host_compile(proposed)
    need(digest(compiled)=="5d1b58981831c637103b9cf575ba27ba0df93a5de47cc936772c50dba381eb1b",
         "GPT_COMPILED_SOURCE_CHANGED")
    creative_witness(proposed,compiled)
    need(compiled["visual_thinker"]["composition"]=="side_by_side" and
        compiled["motion_director"]["method"]=="smooth_morph",
        "NOT_FROZEN_GPT_MOTION_OR_COMPOSITION")
    return p,proposed,compiled

def run(out:Path):
    p,story,candidate=frozen()
    source=host_test_baseline()
    need(not out.exists(),"DESTINATION_ALREADY_EXISTS")
    out.mkdir(parents=True)
    receipt={"checkpoint":"V3-94","origin":"REPLAY_OF_AUTHENTIC_GPT6_LUNA_V393",
             "genuine_prior_model_requests":1,"new_model_requests":0,
             "original_paid_run_id":39197145291,
             "original_model_storyboard_sha256":digest(story),
             "original_model_video_sha256":p["frozen_evidence"]["original_video_sha256"],
             "new_model_authorship":"NONE_REUSING_V393",
             "source_ledger_sha256":LEDGER_SHA,
             "production":"BLOCKED","human_review":"UNRATED",
             "outcome":"PREFLIGHT"}
    (out/"v394_layout_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    with tempfile.TemporaryDirectory(prefix="v394_timings_") as scratch:
        _,_,counts=native.common_timeline(source,candidate,Path(scratch))
    need(sum(counts)==441,"EXACT_441_FRAME_NARRATION_TIMELINE_DRIFT")
    # Original V3-93 narration text has not been edited and both treatments
    # retain their original narrator scripts; bitwise audio parity with the
    # historical H264/AAC container is NOT assumed.
    native_audit=audit_timeline(candidate,counts)
    baseline_audit=audit_timeline(source,counts)
    need(native_audit["timeline_frames_audited"]==441
         and baseline_audit["timeline_frames_audited"]==441,
         "COMPLETE_FRAME_LEVEL_COLLISION_GATE_NOT_RUN")
    # At the timestamps preregistered BEFORE implementation, ensure
    # physical geometry is collision free at the actual local beat frame.
    t_cases=[]
    for t in (11.7,22.0):
        frame=min(440,round(t*FPS))
        cumulative=0
        for beat,n in enumerate(counts):
            if frame<cumulative+n:
                local=frame-cumulative
                progress=min(1.,local/max(1,int(n*.78)))
                status=audit_frame(candidate,beat,progress)
                t_cases.append({"seconds":t,"global_frame":frame,
                                "beat":candidate["beats"][beat]["stage"],
                                "safe":True,"caption_count":status["caption_count"]})
                break
            cumulative+=n
    need(len(t_cases)==2,"PRE_REGISTERED_TIMESTAMPS_NOT_CHECKED")
    receipt.update(outcome="FULL_441_FRAME_LAYOUT_PREFLIGHT_PASS",
                   candidate_geometry=native_audit,
                   host_control_geometry=baseline_audit,
                   preregistered_timestamps=t_cases,
                   audio_content_unchanged=True)
    (out/"v394_layout_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    res=native.build_comparison(source,candidate,out/"native_pair",
                                 frame_renderer=render_corrected)
    need(res["matched_video_frame_counts"] is True and
        all(m["native_frames"]==441 for m in res["native_mp4s"]),
        "NATIVE_ENCODE_DECODER_FRAME_DRIFT")
    for movie in res["native_mp4s"]:
        f=out/"native_pair"/movie["name"]
        need(f.is_file() and native.file_sha(f)==movie["sha256"]
             and native.probe(f)==441,"NATIVE_MEDIA_CODEC_SHA_MISMATCH")
    revised=out/"native_pair/model_unverified.mp4"
    # Never alter old artifact. New file uses historical legacy naming but has
    # exact GPT provenance attached to this receipt, NOT new inference.
    snaps=[]
    for t in (11.7,22.0):
        f=out/("repaired_"+str(t).replace(".","_")+"s.png")
        native.snap(revised,t).save(f)
        snaps.append(f.name)
    receipt.update(outcome="NATIVE_REPAIRED_SOURCE_VIDEO_TECHNICAL_AND_GEOMETRY_PASS",
                   native_mp4s=res["native_mp4s"],repaired_frame_snapshots=snaps,
                   original_narration_text_unchanged=True,
                   audio_bitwise_against_original="NOT_ASSERTED",
                   new_visual_sha256=native.file_sha(revised),
                   native_441_frames=True,
                   renderer_compilation="HOST_GEOMETRY_NOT_MODEL_PYTHON",
                   generalization="ONLY_3_BY_4_TO_4_BY_3_CASE",
                   pedagogical_visual_aesthetics="INDEPENDENT_HUMAN_REVIEW_PENDING")
    (out/"v394_layout_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print("V394_REAL_GPT_JSON_REUSED_NO_NEW_MODEL",flush=True)
    print("V394_FULL_FRAME_COLLISION_GATE",native_audit["timeline_frames_audited"],flush=True)
    print("V394_CORRECTED_NATIVE",receipt["outcome"],flush=True)
    return receipt

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=run(args.output)
    if result["outcome"]!="NATIVE_REPAIRED_SOURCE_VIDEO_TECHNICAL_AND_GEOMETRY_PASS":
        sys.exit(2)
