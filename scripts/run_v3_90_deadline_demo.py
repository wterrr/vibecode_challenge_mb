#!/usr/bin/env python3
"""V3-90 offline deadline demo: bounded question -> genuinely rendered native MP4.

Host-verifiable Fraction and ordered search only. No LLM, provider, API keys,
independent human quality rating, production promotion, or general-domain claim.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from learnflow_v3.creative_manim_runner import _audio,_docker_manim,_codec_and_pixel_gates
from learnflow_v3.v388_cross_family_planner import FRACTION,SEARCH,compile_case
from learnflow_v3.v388_cross_family_manim import finite_source
from learnflow_v3.v388_native_cross_family_gate import verify_native
from scripts.run_v3_44_semantic_counterfactual import deterministic_mux

REG=ROOT/"benchmarks/learnflowbench/v3/v3_90_deadline_demo_preregister.json"
VIDEO="v390_native.mp4"

def check(x,why):
    if not x: raise ValueError("V390_"+why)

def sha(b): return sha256(b).hexdigest()

def registered():
    doc=json.loads(REG.read_text())
    check(doc["checkpoint"]=="V3-90" and doc["protocol"]=="FIRST_CHILD_PREREG_BEFORE_IMPLEMENTATION"
        and doc["parent"]=={"pr":126,"sha":"7f5dd5145af53a07f38c8bfd138a863475e86943"},
        "PARENT_PREREG_DRIFT")
    check(doc["locked_denominator"]==4 and doc["expected_native"]==2
          and doc["expected_abstain"]==2 and
          len(set(doc["positive_queries"]+doc["negative_queries"]))==4,
          "DENOMINATOR_DRIFT")
    a=doc["acceptance"]
    check(a["model_api_requests"]==0 and a["external_human_scores"]==0
          and a["production"]=="BLOCKED" and a["final_visual_quality"]=="NOT_PASS"
          and a["autonomous_model_storyboard"]=="NOT_TESTED"
          and doc["constraints"]["no_model_calls"] is True,
          "RELEASE_BOUNDARY_DRIFT")
    v388=json.loads((ROOT/"benchmarks/learnflowbench/v3/v3_88_cross_family_preregister.json").read_text())
    check(not {x["question"] for x in v388["cases"]}.intersection(doc["positive_queries"]),
          "HISTORICAL_INPUT_REUSE")
    return doc

def prepare(question):
    check(type(question) is str and 1<=len(question)<=300
          and question==question.strip()
          and all(ord(c)>=32 for c in question),"QUERY_MALFORMED")
    family=("FRACTION_EQUIVALENCE" if FRACTION.fullmatch(question)
            else "ORDERED_SEARCH" if SEARCH.fullmatch(question) else "UNSUPPORTED")
    row={"id":"demo_"+sha(question.encode())[:16],
         "question":question,"family":family,"role":"heldout"}
    r=compile_case(row)
    check(r["status"] in ("ABSTAIN","SUPPORTED_HOST_ONLY"),"INVALID_ORACLE_STATUS")
    return row,r

def native(folder,row,plan):
    events=plan["scripted_semantic_events"]
    check(len(events)>=3 and all(e.get("claim_ids") and e.get("narration") for e in events),
          "MISSING_CLAIM_OR_NARRATION")
    story=SimpleNamespace(beats=[SimpleNamespace(narration=e["narration"],
                     claim_ids=e["claim_ids"]) for e in events])
    durations,beats,wav=_audio(folder,story)
    src=folder/"v390_finite_host_manim.py"
    src.write_text(finite_source(row,plan,durations))
    silent,sandbox=_docker_manim(folder,src)
    movie=folder/VIDEO
    mux=deterministic_mux(silent,wav,movie,beats)
    check(0<=mux["raw_manim_frames"]-mux["output_h264_frames"]<=3,"FRAME_DRIFT")
    av=_codec_and_pixel_gates(movie,beats)
    check(av["frames"]==sum(b["frames"] for b in beats)==mux["output_h264_frames"],
          "AUDIO_VIDEO_FRAME_MISMATCH")
    witnesses=verify_native(movie,beats,plan)
    decoded=subprocess.run(["ffmpeg","-nostdin","-v","error","-xerror","-i",str(movie),
                            "-map","0:v:0","-f","null","-"],
                           stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=180)
    check(decoded.returncode==0,"FULL_H264_DECODING_FAILED")
    return {"status":"TECHNICAL_NATIVE_PASS_ONLY","video":f"{row['id']}/{VIDEO}",
            "video_sha256":sha(movie.read_bytes()),"codec":"H264/AAC",
            "native_frames":av["frames"],"source_verified":True,
            "source_semantic_sha256":plan["source_semantic_proof_sha256"],
            "model_authorship":False,"semantic_event_count":len(events),
            "real_pcm_phases":len(beats),"native_visual_witnesses":witnesses,
            "native_audio_mux":mux,"native_codec_pixel_gate":av,
            "full_decode":"PASS","manim_sandbox":sandbox}

def gallery(root,report):
    cards=[]
    for c in report["cases"]:
        title=escape(c["question"])
        if c["status"]=="TECHNICAL_NATIVE_PASS_ONLY":
            content=('<video controls playsinline preload="metadata" src="'
                     +escape(c["video"],quote=True)+'"></video>')
            foot="Real narrated Manim MP4 — verified native render, not human approved"
        elif c["status"]=="ABSTAIN":
            content='<p class="blocked">ABSTAIN — no video generated</p>'
            foot="Unsupported topic or invalid knowledge claim correctly rejected"
        else:
            content='<p class="blocked">PREFLIGHT ONLY — not a video</p>'
            foot="Not rendered and not approved"
        cards.append('<article><h2>'+title+'</h2>'+content+
                     '<p class="secondary">'+escape(foot)+'</p></article>')
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LearnFlow · bounded offline demo</title><style>
*{box-sizing:border-box}body{margin:0;background:#f9f6ff;color:#292439;
font:16px/1.6 system-ui,sans-serif}.wrap{max-width:1080px;margin:auto;padding:40px 20px}
h1{font-size:clamp(2rem,5vw,3.4rem);line-height:1.14;margin:12px 0}
h2{font-size:1.1rem;line-height:1.4}.eyebrow{font-weight:700;letter-spacing:.12em;
color:#6751ad;font-size:.8rem;text-transform:uppercase}.grid{display:grid;
grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:18px}
article{padding:22px;border-radius:20px;background:white;border:1px solid #ebe2fb}
video{display:block;width:100%;aspect-ratio:16/9;background:#080a11;border-radius:12px}
.blocked{background:#eee9f7;border-radius:12px;text-align:center;padding:30px 12px}
.secondary,footer{color:#6e647c;font-size:.9rem}footer{margin-top:28px}
</style></head><body><main class="wrap"><header>
<div class="eyebrow">LearnFlow — technical demo, not production</div>
<h1>A bounded question becomes a real explained video.</h1>
<p>These lessons use finite host-verified visual semantics, not autonomous
AI storyboards. Unsupported queries abstain instead of fabricating an explanation.</p>
</header><section class="grid">'''+''.join(cards)+'''</section><footer>
Video integrity does not prove learning outcomes, human acceptance, or
3Blue1Brown parity. Production and main merge remain blocked.</footer>
</main></body></html>'''
    (root/"index.html").write_text(page,encoding="utf-8")

def run(out,questions,*,locked=False,preflight_only=False):
    manifest=registered()
    if locked:
        check(questions==manifest["positive_queries"]+manifest["negative_queries"],
              "LOCKED_QUESTIONS_SUBSTITUTED")
    check(0<len(questions)<=4 and len(set(questions))==len(questions),"DUPLICATE_OR_TOO_MANY")
    check(not out.exists(),"OUTPUT_DIRECTORY_MUST_BE_NEW")
    out.mkdir(parents=True)
    results=[]
    for question in questions:
        row,pre=prepare(question)
        folder=out/row["id"]
        folder.mkdir()
        entry={"id":row["id"],"question":question,
               "question_sha256":sha(question.encode()),"family":row["family"],
               "model_api_requests":0,"human_review":"UNRATED","production":"BLOCKED"}
        if pre["status"]=="ABSTAIN":
            entry.update(status="ABSTAIN",video=None,reason=pre["reason"])
        elif preflight_only:
            entry.update(status="PREFLIGHT_ONLY",video=None,
                    source_semantic_sha256=pre["plan"]["source_semantic_proof_sha256"])
        else:
            entry.update(native(folder,row,pre["plan"]))
        (folder/"receipt.json").write_text(json.dumps(entry,indent=2)+"\n")
        results.append(entry)
    positives=sum(c["status"]=="TECHNICAL_NATIVE_PASS_ONLY" for c in results)
    negatives=sum(c["status"]=="ABSTAIN" for c in results)
    if locked and not preflight_only:
        check(positives==2 and negatives==2 and len(results)==4 and
              {c["family"] for c in results if c["status"]=="TECHNICAL_NATIVE_PASS_ONLY"}
              =={"FRACTION_EQUIVALENCE","ORDERED_SEARCH"},"NATIVE_DENOMINATOR_FAIL")
    report={"checkpoint":"V3-90","kind":"BOUNDED_DEADLINE_OFFLINE_DEMO_ONLY",
            "machine_native_evidence":"PASS" if positives and not preflight_only
                    else "NOT_RUN_OR_ALL_ABSTAIN",
            "native_verified":positives,"abstained":negatives,"total":len(results),
            "cases":results,"model_api_requests":0,
            "autonomous_model_storyboard":"NOT_TESTED",
            "independent_human_quality":"PENDING_HUMAN_REVIEW_ZERO_REAL_SCORES",
            "final_visual_quality":"NOT_PASS","learner_gain":"NOT_MEASURED",
            "source_retrieval":"NO_LIVE_SOURCE_RETRIEVAL",
            "production":"BLOCKED","main_merge":False}
    (out/"v390_report.json").write_text(json.dumps(report,indent=2)+"\n")
    gallery(out,report)
    print(json.dumps({k:v for k,v in report.items() if k!="cases"},indent=2))
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--query")
    mode.add_argument("--locked-demo",action="store_true")
    parser.add_argument("--output-dir",required=True,type=Path)
    parser.add_argument("--preflight-only",action="store_true")
    a=parser.parse_args()
    doc=registered()
    questions=(doc["positive_queries"]+doc["negative_queries"] if a.locked_demo
               else [a.query])
    run(a.output_dir,questions,locked=a.locked_demo,preflight_only=a.preflight_only)
