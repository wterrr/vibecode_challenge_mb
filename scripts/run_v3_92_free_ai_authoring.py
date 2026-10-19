#!/usr/bin/env python3
"""V3-92: one zero-price LIVE AI storyboard POST with exact safe telemetry.

Real network and mock senders have mutually exclusive provenance.
The native renderer is pre-existing HOST code, never arbitrary model Python.
No provider output repair, fallback retry, or speculative human ratings.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError,URLError

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.v364_heldout_storyboard import LEDGER_SHA,QUERY,STAGES,digest,host_test_baseline
from learnflow_v3.v364_native_array_compiler import build_comparison, file_sha,probe
from learnflow_v3.v392_compact_authoring import (
    WIRE_VERSION,ROOT_KEYS,BEAT_KEYS,strict_parse,host_compile,creative_witness,Rejected
)
from scripts.run_v3_91_single_free_ai_pilot import (
    safe_get_catalog, request_once, strictly_zero, Denied
)

REG=ROOT/"benchmarks/learnflowbench/v3/v3_92_one_free_ai_recovery_preregister.json"
MODEL="openrouter/free"
FINISH_TYPES={"stop","length","content_filter","tool_calls","error","null"}
def need(x,reason):
    if not x:raise Denied("V392_"+reason)

def preregistered():
    x=json.loads(REG.read_text())
    need(x["checkpoint"]=="V3-92" and x["registered"]=="FIRST_CHILD_BEFORE_IMPLEMENTATION"
         and x["parent_pr"]==128
         and x["parent_sha"]=="0c8c179caa610443b6a1dbaa384403a18a9f8a75"
         and x["fixed_host_ledger_sha256"]==LEDGER_SHA
         and x["query"]==QUERY
         and x["provider"]["router"]==MODEL
         and x["provider"]["max_posts"]==1 and x["provider"]["max_retries"]==0
         and x["provider"]["paid_fallback"] is False
         and x["provider"]["max_completion_tokens"]==2500
         and x["provider"]["require_verified_zero_prompt_completion_pricing"] is True
         and x["design"]["text_mode_without_provider_strict_json_schema"] is True
         and x["gate"]["only_finished_stop_can_be_accepted"] is True
         and x["gate"]["no_raw_non_accepted_provider_response_in_artifacts"] is True
         and x["gate"]["production"]=="BLOCKED"
         and x["no_v2_core_modifications"] is True
         and x["no_main_merge"] is True, "PREREG_SCOPE_CHANGED")
    return x

def prompt_message():
    # Compact JSON output, deliberately no 12 object identifiers/model source SHA.
    # Correct facts and proof placement are host-validated, not model invented.
    return (
      "You are the educational storyteller and visual director for LearnFlow. "
      "Make your OWN concise pedagogical narration and visual choices to answer: "
      +QUERY+" Use the immutable verified facts 3 rows of 4 squares and "
      "4 rows of 3 squares; the same 12 squares persist through rearrangement. "
      "Return EXACTLY one JSON object (no markdown, no preamble, no code) with "
      "these six fields: "
      'opening_strategy ("predict_first" or "notice_paradox"), '
      'closure_strategy ("counting_invariant" or "multiplication_as_groups"), '
      'composition ("single_stage" or "side_by_side"), '
      'motion_method ("smooth_morph" or "staggered_morph"), '
      'focus ("all_twelve" or "highlight_first_row" or "track_corner"), '
      'beats (five objects each with exactly stage, narration, visual_focus). '
      "Stages in exact order: QUESTION, SETUP, TRANSFORM, WITNESS, CLOSE. "
      "For every beat choose visual_focus from all_twelve, highlight_first_row, track_corner. "
      "Write FIVE DISTINCT ORIGINAL English sentences 18-150 characters long, "
      "ASCII only, no newline inside sentence. "
      "QUESTION and SETUP let learner predict. TRANSFORM retains original squares. "
      "Do NOT disclose 12 in the first three beats; WITNESS and CLOSE each explicitly "
      "say 12 and explain why rearrangement doesn't change count. "
      "Only numerical facts 3, 4, 12. You choose the storytelling strategy and "
      "visual direction; source ledger and animation code belong to the host. "
      "Keep JSON under 2000 bytes. Do not claim measured learner gains."
    )

def payload():
    data={"model":MODEL,"stream":False,"max_tokens":2500,
      "messages":[
        {"role":"system","content":"Produce one short educational storyboard. Exactly one valid JSON object with no extra fields, no markdown and no executable code. Make original narration."},
        {"role":"user","content":prompt_message()}
      ]}
    need("response_format" not in data and "provider" not in data
         and "temperature" not in data and "models" not in data,
         "UNSAFE_PROVIDER_ROUTING_OR_SCHEMA")
    raw=json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
    need(len(raw)<=5000,"PROMPT_OVERLONG")
    return raw

def safe_finish(v):
    if v is None:return "null"
    return v if type(v) is str and v in FINISH_TYPES else "OTHER"

def safe_model(v):
    if type(v) is not str or len(v)>120 or not re.fullmatch("[A-Za-z0-9_.:/-]+",v):
        return "UNVERIFIED_MODEL_ID"
    return v

def safe_usage(usage):
    if type(usage) is not dict:return {}
    out={}
    for k in ("prompt_tokens","completion_tokens","total_tokens"):
        n=usage.get(k)
        if type(n) is int and 0<=n<=1_000_000:out[k]=n
    out["reported_cost"]=(
        "ZERO" if strictly_zero(usage["cost"]) else "NONZERO_OR_INVALID"
        ) if "cost" in usage else "NOT_REPORTED"
    return out

def save(out,d):
    (out/"v392_attempt.json").write_text(json.dumps(d,sort_keys=True,indent=2)+"\n")

def run(out,*,key,post_sender=None,catalog_sender=None,native=True):
    preregistered()
    need(not out.exists(),"OUTPUT_DIR_ALREADY_EXISTS")
    out.mkdir(parents=True)
    actual_network=post_sender is None and catalog_sender is None
    receipt={
      "checkpoint":"V3-92","utc":datetime.now(timezone.utc).isoformat(),
      "provider_post_attempts":0,"router":MODEL,"retry_count":0,"paid_fallbacks":0,
      "actual_model":"UNOBSERVED","finish_reason":"UNOBSERVED",
      "native_finish_reason":"UNOBSERVED","usage":{},"response_id_sha256":"UNOBSERVED",
      "candidate_origin":"NO_ACCEPTED_REAL_PROVIDER_STORYBOARD",
      "model_storyboard":"NOT_ACCEPTED","native_video":"NOT_RUN",
      "learner_quality":"UNRATED","learner_gain":"NOT_MEASURED",
      "quality_3b1b":"NOT_PROVEN","production":"BLOCKED",
      "result":"PREFLIGHT"}
    save(out,receipt)
    if not key:
        receipt["result"]="DENY_MISSING_API_CREDENTIAL"
        save(out,receipt);return receipt
    try:
        catalog=safe_get_catalog(sender=catalog_sender)
        need(catalog["free_input_price_verified"] and catalog["free_output_price_verified"],
             "FREE_PRICE_NOT_VERIFIED")
        receipt["public_zero_price_catalog"]="PASS"
    except (Denied,ValueError,KeyError,TypeError,HTTPError,URLError,TimeoutError) as exc:
        receipt["result"]="DENY_PUBLIC_ZERO_PRICE_NOT_VERIFIED"
        receipt["failure_class"]=type(exc).__name__
        save(out,receipt);return receipt
    raw=payload()
    receipt["request_sha256"]=sha256(raw).hexdigest()
    receipt["provider_post_attempts"]=1
    receipt["result"]="ONE_FREE_POST_ATTEMPTED"
    save(out,receipt)
    print("V392_ONE_FREE_MODEL_POST_ATTEMPT",flush=True)
    try:
        response=request_once(key,raw,send=post_sender)
    except (HTTPError,URLError,TimeoutError,ValueError,TypeError) as exc:
        receipt["result"]="PROVIDER_TRANSPORT_OR_HTTP_NO_RETRY"
        receipt["failure_class"]=type(exc).__name__
        if isinstance(exc,HTTPError):
            receipt["http_status"]=int(exc.code)
        save(out,receipt);return receipt
    # Always capture bounded, sanitized completion telemetry before finish/validation,
    # including a rejected non-stop response. Never persist raw rejected text.
    try:
        need(type(response) is dict,"PROVIDER_ENVELOPE_NOT_OBJECT")
        receipt["actual_model"]=safe_model(response.get("model"))
        receipt["usage"]=safe_usage(response.get("usage"))
        rid=response.get("id")
        if type(rid) is str and len(rid)>=6 and len(rid)<=200:
            receipt["response_id_sha256"]=sha256(rid.encode()).hexdigest()
        choices=response.get("choices")
        need(type(choices) is list and len(choices)==1,"PROVIDER_CHOICE_COUNT_INVALID")
        ch=choices[0]
        need(type(ch) is dict,"PROVIDER_CHOICE_MALFORMED")
        receipt["finish_reason"]=safe_finish(ch.get("finish_reason"))
        receipt["native_finish_reason"]=safe_finish(ch.get("native_finish_reason"))
        save(out,receipt)
        need(receipt["response_id_sha256"]!="UNOBSERVED","RESPONSE_ID_NOT_ATTESTED")
        need(receipt["actual_model"].endswith(":free") or
             receipt["actual_model"]==MODEL,"ACTUAL_MODEL_FREE_NOT_ATTESTED")
        need(receipt["usage"]["reported_cost"] in ("ZERO","NOT_REPORTED"),
             "PROVIDER_REPORTED_NONZERO_CHARGE")
        need(receipt["finish_reason"]=="stop","FINISH_REASON_NOT_STOP")
        msg=ch.get("message")
        need(type(msg) is dict and type(msg.get("content")) is str,
             "PROVIDER_NO_PLAIN_JSON_CONTENT")
        p=strict_parse(msg["content"].encode("utf-8"))
        c=host_compile(p)
        witness=creative_witness(p,c)
        receipt["candidate_origin"]=(
            "REAL_PROVIDER_RESPONSE" if actual_network else "TEST_SENDER_NOT_REAL")
        receipt["model_storyboard"]=(
            "COMPACT_GROUNDED_AUTHORING_ACCEPTED" if actual_network else "TEST_FIXTURE_ONLY")
        receipt["storyboard_receipt"]=witness
        receipt["result"]=(
            "REAL_FREE_MODEL_STORYBOARD_ACCEPTED_NATIVE_PENDING" if actual_network else
            "OFFLINE_TEST_CANDIDATE_ONLY")
        (out/"accepted_candidate_not_human_rated.json").write_text(
           json.dumps(p,sort_keys=True,indent=2)+"\n")
        save(out,receipt)
    except (Denied,Rejected,ValueError,KeyError,IndexError,TypeError) as exc:
        receipt["result"]="MODEL_COMPLETION_REJECTED_NO_RETRY"
        receipt["failure_type"]=type(exc).__name__
        if isinstance(exc,(Denied,Rejected)):
            receipt["reason"]=str(exc)[:90]
        save(out,receipt);return receipt
    if not native:
        receipt["result"]="NATIVE_NOT_RUN_MODEL_ACCEPTANCE_ONLY"
        save(out,receipt);return receipt
    try:
        native_receipt=build_comparison(host_test_baseline(),c,out/"native_pair")
        need(native_receipt["matched_video_frame_counts"] is True,
             "NATIVE_FRAME_COUNT_FAILURE")
        for m in native_receipt["native_mp4s"]:
            film=out/"native_pair"/m["name"]
            need(film.exists() and file_sha(film)==m["sha256"]
                 and probe(film)==m["native_frames"],"NATIVE_MP4_SHA_CODEC_FAILURE")
        need(native_receipt["candidate_vs_baseline_midpoint_MAD"]>0,
             "NO_VISIBLE_CANDIDATE_VS_HOST_CHANGE")
        receipt["native_video"]="COMPLETE_H264_AAC_DECODE_CONFIRMED"
        receipt["native_frames"]=native_receipt["native_mp4s"][1]["native_frames"]
        receipt["result"]=(
            "REAL_FREE_AI_STORYBOARD_TO_NATIVE_TECHNICAL_PASS" if actual_network else
            "TEST_ONLY_NATIVE_NOT_MODEL_EVIDENCE")
    except Exception as exc:
        receipt["result"]="MODEL_STORYBOARD_NATIVE_RENDER_FAILED"
        receipt["native_failure_type"]=type(exc).__name__
    save(out,receipt)
    return receipt

if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--live-once",action="store_true")
    cli.add_argument("--output",type=Path,required=True)
    args=cli.parse_args()
    need(args.live_once,"EXPLICIT_SINGLE_INFERENCE_REQUIRED")
    r=run(args.output,key=os.getenv("OPENROUTER_API_KEY",""))
    print("V392_FINAL",r["result"],"posts",r["provider_post_attempts"],
          "finish",r["finish_reason"],flush=True)
    if r["result"]!="REAL_FREE_AI_STORYBOARD_TO_NATIVE_TECHNICAL_PASS":
        raise SystemExit(2)
