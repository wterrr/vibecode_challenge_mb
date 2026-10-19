#!/usr/bin/env python3
"""V3-91: one real, zero-priced OpenRouter free-router storyboard trial.

A single authorized network POST is the only source of external model authorship.
Offline senders can exercise schema/transport tests but NEVER establish provenance.
The old V3-64 array compiler is trusted HOST render code, not model-authored Python.
"""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
import argparse
import json
import os
import sys
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.v364_heldout_storyboard import (
    LEDGER_SHA,QUERY,TOPIC,SCHEMA,strict_load,accept,host_test_baseline,digest
)
from learnflow_v3.v364_native_array_compiler import build_comparison,probe,file_sha
from scripts.run_v3_64_one_shot_real_model import provider_schema,prompt

REG=ROOT/"benchmarks/learnflowbench/v3/v3_91_live_free_model_preregister.json"
FREE="openrouter/free"
POST="https://openrouter.ai/api/v1/chat/completions"
CATALOG="https://openrouter.ai/api/v1/models"
class Denied(ValueError):pass

def need(x,why):
    if not x:raise Denied("V391_"+why)

def registered():
    x=json.loads(REG.read_text())
    need(x["checkpoint"]=="V3-91" and
         x["protocol"]=="FIRST_CHILD_PREREG_BEFORE_IMPLEMENTATION" and
         x["parent"]=={"pr":127,"head_sha":"f3e22a686cb7548743def0db9e036e47877b5d88"} and
         x["topic_id"]==TOPIC and x["prompt"]==QUERY and
         x["ledger_sha256"]==LEDGER_SHA,"PREREG_LEDGER_CHANGED")
    p=x["provider"]
    need(p["model"]==FREE and p["url"]==POST and p["max_inference_posts"]==1
         and p["max_retries"]==0 and p["max_fallback_retries"]==0
         and p["max_output_tokens"]==3500 and p["strict_structured_json"] is True
         and p["no_paid_models"] is True and p["no_paid_fallback"] is True
         and p["check_public_model_catalog_for_zero_price_before_post"] is True
         and p["token_price_input_usd_per_million"]==0
         and p["token_price_output_usd_per_million"]==0
         and x["acceptance"]["production"]=="BLOCKED"
         and x["no_main_merge"] is True,"INFERENCE_SAFETY_DRIFT")
    return x

def strictly_zero(value):
    # Do not coerce booleans, NaN or missing pricing to a zero-cost assertion.
    if type(value) not in (int,float,str):return False
    try:return Decimal(str(value))==0 and Decimal(str(value)).is_finite()
    except (InvalidOperation,ValueError):return False

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise Denied("V391_REDIRECT_DENIED")

def safe_get_catalog(sender=None):
    req=Request(CATALOG,headers={"Accept":"application/json"},method="GET")
    with (sender or build_opener(NoRedirect()).open)(req,timeout=18) as response:
        need(getattr(response,"status",200)==200,"CATALOG_HTTP_NOT_200")
        data=response.read(9_000_001)
        need(0<len(data)<=9_000_000,"CATALOG_SIZE_INVALID")
    items=json.loads(data)["data"]
    need(isinstance(items,list) and len(items)>0,"CATALOG_SHAPE_INVALID")
    choices=[i for i in items if isinstance(i,dict) and i.get("id")==FREE]
    need(len(choices)==1,"FREE_ROUTER_NOT_FOUND_IN_PUBLIC_CATALOG")
    row=choices[0]
    pricing=row.get("pricing") or {}
    need(strictly_zero(pricing.get("prompt")) and
         strictly_zero(pricing.get("completion")),
         "FREE_ROUTER_PRICE_NOT_CONFIRMED_ZERO")
    return {"catalog_http":"HTTP_200","router_id":FREE,
            "free_input_price_verified":True,"free_output_price_verified":True}

def payload():
    wire={"model":FREE,"max_tokens":3500,"stream":False,
          "messages":[
            {"role":"system","content":"Design a unique, mathematically grounded five-role educational storyboard. Return only valid strict JSON. Do not output code, invented learning outcomes, or fake sources."},
            {"role":"user","content":prompt()}
          ],
          "response_format":{"type":"json_schema","json_schema":{
              "name":"v391_genuine_free_model_storyboard",
              "strict":True,"schema":provider_schema(SCHEMA)}}}
    need("provider" not in wire and "temperature" not in wire,
         "PAID_ROUTING_OR_UNSUPPORTED_PARAMETER")
    raw=json.dumps(wire,sort_keys=True,separators=(",",":")).encode()
    need(len(raw)<=18000,"REQUEST_SIZE_EXCEEDED")
    return raw

def request_once(key,raw,send=None):
    need(type(key) is str and len(key)>=16 and "\n" not in key and "\r" not in key,
         "NO_SAFE_API_KEY")
    request=Request(POST,data=raw,method="POST",headers={
        "Authorization":"Bearer "+key,"Content-Type":"application/json",
        "Accept":"application/json",
        "HTTP-Referer":"https://github.com/wterrr/vibecode_challenge_mb",
        "X-Title":"LearnFlow V3-91 FREE one-shot"})
    with (send or build_opener(NoRedirect()).open)(request,timeout=130) as response:
        need(getattr(response,"status",200)==200,"POST_NON_200")
        result=response.read(250_001)
        need(0<len(result)<=250_000,"RESPONSE_SIZE_EXCEEDED")
    return json.loads(result)

def _save(out,record):
    (out/"v391_attempt.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")

def run(out,*,key,post_sender=None,catalog_sender=None,do_native=True):
    registered()
    need(not out.exists(),"OUTPUT_EXISTS")
    out.mkdir(parents=True)
    real=(post_sender is None and catalog_sender is None)
    record={"checkpoint":"V3-91","utc":datetime.now(timezone.utc).isoformat(),
        "requested_model":FREE,"actual_model":"UNOBSERVED","provider_post_attempts":0,
        "retry_count":0,"paid_fallbacks":0,"usage_cost_usd":"UNOBSERVED",
        "candidate_origin":"NO_REAL_PROVIDER_RESPONSE",
        "model_authored_storyboard":"NOT_ESTABLISHED",
        "native_candidate":"NOT_RUN","human_quality":"UNRATED",
        "learning_gain":"NOT_MEASURED","production":"BLOCKED",
        "outcome":"PREFLIGHT"}
    _save(out,record)
    if not key:
        record["outcome"]="BLOCKED_MISSING_OPENROUTER_KEY"
        _save(out,record);return record
    try:
        free=safe_get_catalog(sender=catalog_sender)
        record["public_catalog"]=free
    except (Denied,KeyError,ValueError,TypeError,HTTPError,URLError,TimeoutError) as exc:
        record["outcome"]="BLOCKED_ZERO_PRICE_PUBLIC_CATALOG_NOT_VERIFIED"
        record["error_class"]=type(exc).__name__
        _save(out,record);return record
    raw=payload()
    record["request_sha256"]=sha256(raw).hexdigest()
    record["provider_post_attempts"]=1
    record["outcome"]="ONE_FREE_PROVIDER_POST_ATTEMPTED"
    _save(out,record)
    print("V391_ONE_ZERO_PRICE_ROUTER_POST_ATTEMPT",flush=True)
    try:
        answer=request_once(key,raw,send=post_sender)
    except (HTTPError,URLError,TimeoutError,ValueError,TypeError) as exc:
        record["outcome"]="PROVIDER_REQUEST_FAILED_NO_RETRY"
        record["error_class"]=type(exc).__name__
        if isinstance(exc,HTTPError):
            record["http_status"]=int(exc.code)
        _save(out,record);return record
    try:
        need(isinstance(answer,dict) and
             isinstance(answer.get("id"),str) and len(answer["id"])>5,
             "REAL_RESPONSE_ID_MISSING")
        choice=answer["choices"][0]
        need(choice.get("finish_reason")=="stop","MODEL_TRUNCATED_OR_REFUSED")
        returned=answer.get("model")
        need(isinstance(returned,str) and
             (returned.endswith(":free") or returned==FREE),
             "RETURNED_MODEL_NOT_CONFIRMED_FREE")
        record["actual_model"]=returned[:100]
        # A nonzero reported charge makes the trial unsafe to certify as free,
        # even if the router advertised zero pricing.
        usage=answer.get("usage") or {}
        if "cost" in usage:
            need(strictly_zero(usage["cost"]),"PROVIDER_REPORTED_NONZERO_COST")
            record["usage_cost_usd"]="0"
        else:
            record["usage_cost_usd"]="NOT_RETURNED"
        record["response_id_sha256"]=sha256(answer["id"].encode()).hexdigest()
        for field in ("prompt_tokens","completion_tokens","total_tokens"):
            if type(usage.get(field)) is int and usage[field]>=0:
                record[field]=usage[field]
        content=choice["message"]["content"]
        need(isinstance(content,str),"NO_PROVIDER_JSON_TEXT")
        candidate=strict_load(content.encode())
        accepted=accept(candidate)
        baseline=host_test_baseline()
        changed=sum(candidate["beats"][i]["caption"]!=baseline["beats"][i]["caption"]
                    for i in range(5))
        need(changed>=2,"MODEL_DID_NOT_AUTHOR_DISTINCT_NARRATIVE")
        record["original_caption_count"]=changed
        record["candidate_sha256"]=digest(candidate)
        record["host_ledger_sha256"]=accepted["host_ledger_sha256"]
        record["candidate_origin"]="REAL_PROVIDER_RESPONSE" if real else "SIMULATED_TEST_SENDER"
        record["model_authored_storyboard"]=(
            "VALIDATED_REAL_FREE_MODEL" if real else "NOT_ESTABLISHED_TEST_ONLY")
        record["outcome"]=("REAL_FREE_MODEL_STORYBOARD_ACCEPTED"
                           if real else "TEST_SENDER_STORYBOARD_ACCEPTED_NOT_REAL")
        # Only accepted, source-scoped semantic data, not provider raw response or tokens.
        (out/"candidate_validated_not_human_approved.json").write_text(
            json.dumps(candidate,indent=2,sort_keys=True)+"\n")
        _save(out,record)
    except (Denied,ValueError,KeyError,TypeError,IndexError) as exc:
        record["outcome"]="PROVIDER_RESPONSE_REJECTED_BY_HOST"
        record["error_class"]=type(exc).__name__
        if isinstance(exc,Denied): record["host_reason"]=str(exc)[:100]
        _save(out,record);return record
    if not do_native:
        record["outcome"]="CANDIDATE_ACCEPTED_BUT_NATIVE_NOT_RUN"
        _save(out,record);return record
    try:
        result=build_comparison(baseline,candidate,out/"native_pair")
        need(result["matched_video_frame_counts"] is True,"NATIVE_FRAME_MISMATCH")
        for movie in result["native_mp4s"]:
            path=out/"native_pair"/movie["name"]
            need(file_sha(path)==movie["sha256"]
                 and probe(path)==movie["native_frames"],
                 "NATIVE_MP4_PROVENANCE_OR_CODEC_FAILURE")
        record["native_candidate"]="REAL_H264_AAC_FULL_DECODE_PASS"
        record["native_count"]=len(result["native_mp4s"])
        record["outcome"]=("REAL_FREE_MODEL_TO_NATIVE_TECHNICAL_PASS"
                           if real else "TEST_ONLY_NATIVE_NOT_PROVIDER_PROOF")
        record["human_quality"]="UNRATED"
        _save(out,record)
    except Exception as exc:
        record["outcome"]="REAL_MODEL_CANDIDATE_NATIVE_RENDER_FAILED"
        record["native_error_class"]=type(exc).__name__
        _save(out,record)
    return record

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--live-once",action="store_true")
    args=p.parse_args()
    need(args.live_once,"EXPLICIT_LIVE_ONE_SHOT_REQUIRED")
    d=run(args.output,key=os.environ.get("OPENROUTER_API_KEY",""))
    print("V391_RESULT",d["outcome"],"post_attempts",d["provider_post_attempts"])
    if d["outcome"]!="REAL_FREE_MODEL_TO_NATIVE_TECHNICAL_PASS":
        sys.exit(2)
