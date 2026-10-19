#!/usr/bin/env python3
"""V3-93: ONE paid GPT-6 Luna on OpenRouter, no retry/fallback.

External authoring is attributed only to a true network response, not test senders.
The host owns source facts, semantic admission, executable renderer and media QA.
A token-price upper bound on ONE request is NOT a provider-enforced lifetime key cap.
"""
from __future__ import annotations
from decimal import Decimal,InvalidOperation
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
import argparse,json,os,re,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.v364_heldout_storyboard import LEDGER_SHA,QUERY,host_test_baseline
from learnflow_v3.v364_native_array_compiler import build_comparison,probe,file_sha
from learnflow_v3.v392_compact_authoring import (
    strict_parse,host_compile,creative_witness,Rejected
)
from scripts.run_v3_92_free_ai_authoring import safe_finish,safe_model,safe_usage

REG=ROOT/"benchmarks/learnflowbench/v3/v3_93_paid_gpt6_authoring_preregister.json"
MODEL="openai/gpt-6-luna"
ENDPOINT="https://openrouter.ai/api/v1/chat/completions"
CATALOG="https://openrouter.ai/api/v1/models"
KEY_META="https://openrouter.ai/api/v1/key"
TOKENS=16000
MAX_USD=Decimal("0.01")
MAX_INPUT=Decimal("0.10")
MAX_OUTPUT=Decimal("0.50")
class Blocked(ValueError):pass

def need(cond,reason):
    if not cond:raise Blocked("V393_"+reason)

def registered():
    p=json.loads(REG.read_text())
    s=p["provider"]
    need(p["checkpoint"]=="V3-93" and
         p["preregistered"]=="FIRST_CHILD_BEFORE_IMPLEMENTATION_AND_ANY_PAID_POST" and
         p["parent"]=={"pr":129,"head_sha":"2620270f7863efa43b3c0e21a58acda88655fdae"} and
         p["question"]==QUERY and p["no_main_merge"] is True and
         s["model"]==MODEL and s["provider_order"]==["OpenAI"] and
         s["allow_fallbacks"] is False and s["require_parameters"] is True and
         s["strict_structured_outputs"] is True and
         s["max_completion_tokens"]==TOKENS and s["reasoning_effort"]=="low" and
         s["max_paid_http_posts"]==1 and s["no_retry"] is True and
         s["no_alternative_models"] is True and s["no_free_fallback"] is True and
         s["cost_token_ceiling_usd"]=="0.01" and
         s["max_usd_price_prompt_per_million"]=="0.10" and
         s["max_usd_price_completion_per_million"]=="0.50" and
         p["qa"]["production"]=="BLOCKED","PREREG_SCOPE_DRIFT")
    return p

def schema():
    leaf=lambda values:{"type":"string","enum":list(values)}
    focus=leaf(("all_twelve","highlight_first_row","track_corner"))
    beat={"type":"object","additionalProperties":False,"properties":{
        "stage":leaf(("QUESTION","SETUP","TRANSFORM","WITNESS","CLOSE")),
        "narration":{"type":"string"},"visual_focus":focus},
        "required":["stage","narration","visual_focus"]}
    props={
      "opening_strategy":leaf(("predict_first","notice_paradox")),
      "closure_strategy":leaf(("counting_invariant","multiplication_as_groups")),
      "composition":leaf(("single_stage","side_by_side")),
      "motion_method":leaf(("smooth_morph","staggered_morph")),
      "focus":focus,
      "beats":{"type":"array","items":beat}
    }
    return {"type":"object","additionalProperties":False,"properties":props,"required":list(props)}

def data_payload():
    # NOTE: provider pin is OpenAI standard only (no OpenAI Fast/Flex or BYOK).
    from scripts.run_v3_92_free_ai_authoring import prompt_message
    d={"model":MODEL,"max_completion_tokens":TOKENS,"stream":False,
       "reasoning_effort":"low",
       "provider":{"order":["OpenAI"],"allow_fallbacks":False,
                   "require_parameters":True},
       "messages":[
          {"role":"system","content":"You are a thoughtful educational visual-storyboard writer. Write one ORIGINAL concise five-beat storyboard in the exact JSON schema. Never generate runnable code. Host verifies all math and persistent visual objects."},
          {"role":"user","content":prompt_message()}],
       "response_format":{"type":"json_schema",
           "json_schema":{"name":"v393_compact_original_educational_storyboard",
                          "strict":True,"schema":schema()}}}
    raw=json.dumps(d,separators=(",",":"),sort_keys=True,ensure_ascii=True).encode("utf-8")
    need(len(raw)<=7000,"REQUEST_INPUT_TOO_LARGE_FOR_COST_CAP")
    need("models" not in d and "temperature" not in d
         and d["provider"]["allow_fallbacks"] is False,
         "ROUTING_DRIFT")
    return d,raw

def money(raw):
    if type(raw) not in (str,int,float):raise Blocked("V393_INVALID_PRICE")
    try:
        n=Decimal(str(raw))
        if not n.is_finite() or n<0:raise Blocked("V393_INVALID_PRICE")
        return n
    except InvalidOperation as e:raise Blocked("V393_INVALID_PRICE") from e

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*a,**k):raise Blocked("V393_REDIRECT_FORBIDDEN")

def read_json(url,*,key=None,sender=None,limit=9000000):
    headers={"Accept":"application/json"}
    if key:headers["Authorization"]="Bearer "+key
    req=Request(url,headers=headers,method="GET")
    with (sender or build_opener(NoRedirect()).open)(req,timeout=22) as response:
        need(getattr(response,"status",200)==200,"GET_NON_200")
        b=response.read(limit+1)
        need(0<len(b)<=limit,"GET_OVERSIZE")
    return json.loads(b)

def preflight_model_and_key(*,key,catalog_sender=None,key_sender=None):
    need(type(key) is str and len(key)>15 and "\n" not in key and "\r" not in key,
         "MISSING_CREDENTIAL")
    data=read_json(CATALOG,sender=catalog_sender)["data"]
    need(type(data) is list,"CATALOG_BAD_SHAPE")
    rows=[m for m in data if type(m) is dict and m.get("id")==MODEL]
    need(len(rows)==1,"GPT6_LUNA_NOT_IN_CATALOG")
    model=rows[0]
    pricing=model.get("pricing") or {}
    prompt_price=money(pricing.get("prompt"))
    output_price=money(pricing.get("completion"))
    need(prompt_price>0 and output_price>0,
         "MODEL_NOT_CHARGED_AS_EXPECTED")
    need(prompt_price*1_000_000<=MAX_INPUT and
         output_price*1_000_000<=MAX_OUTPUT,"MODEL_PRICE_CHANGED")
    caps=model.get("supported_parameters") or []
    need("response_format" in caps or "structured_outputs" in caps,
         "STRICT_JSON_CAPABILITY_NOT_ADVERTISED")
    # Config pin and max request bytes bound worst-case approximate token spending.
    # Each UTF-8 byte is conservatively charged as a hypothetical input token.
    _,raw=data_payload()
    pessimistic=(Decimal(len(raw))*prompt_price+Decimal(TOKENS)*output_price)
    need(pessimistic<=MAX_USD,"ONE_POST_EXPECTED_MAX_COST_OVER_1_CENT")
    cur=read_json(KEY_META,key=key,sender=key_sender,limit=100000)
    md=cur.get("data")
    need(type(md) is dict,"KEY_METADATA_UNVERIFIED")
    need(md.get("is_management_key") is False,"KEY_IS_MANAGEMENT")
    remaining=md.get("limit_remaining")
    # Key may be uncapped/null; user has explicitly approved paid GPT,
    # but no proof of account credit/routing follows from authenticated key.
    if remaining is not None:
        need(money(remaining)>pessimistic,"KEY_HAS_INSUFFICIENT_REMAINING_ALLOWANCE")
    return {"model_catalog":"HTTP_200_MATCH","key_metadata":"AUTHENTICATED",
            "input_usd_per_million":str(prompt_price*1_000_000),
            "output_usd_per_million":str(output_price*1_000_000),
            "pessimistic_one_post_cost_ceiling_usd":str(pessimistic),
            "is_provider_enforced_dedicated_lifetime_cap":False,
            "routing_entitlement_confirmed":False}

def post_once(*,key,raw,sender=None):
    req=Request(ENDPOINT,data=raw,method="POST",headers={
        "Authorization":"Bearer "+key,
        "Content-Type":"application/json","Accept":"application/json",
        "HTTP-Referer":"https://github.com/wterrr/vibecode_challenge_mb",
        "X-Title":"LearnFlow V3-93 One Paid GPT-6 Luna Authoring Trial"})
    with (sender or build_opener(NoRedirect()).open)(req,timeout=220) as response:
        need(getattr(response,"status",200)==200,"INFERENCE_NON_200")
        b=response.read(250001)
        need(0<len(b)<=250000,"INFERENCE_BODY_OVERSIZE")
    return json.loads(b)

def save(path,receipt):
    (path/"v393_attempt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")

def run(out:Path,*,key:str,catalog_sender=None,key_sender=None,post_sender=None,native=True):
    registered()
    need(not out.exists(),"OUTPUT_EXISTS")
    out.mkdir(parents=True)
    genuine=(catalog_sender is None and key_sender is None and post_sender is None)
    receipt={"checkpoint":"V3-93","utc":datetime.now(timezone.utc).isoformat(),
      "router_requested":MODEL,"provider_post_attempts":0,"retry_count":0,
      "requested_output_max":TOKENS,"actual_model":"UNOBSERVED",
      "finish_reason":"UNOBSERVED","native_finish_reason":"UNOBSERVED",
      "usage":{},"response_id_sha256":"UNOBSERVED",
      "candidate_origin":"NO_ADMITTED_PROVIDER_STORYBOARD",
      "model_storyboard":"NOT_ACCEPTED","native_video":"NOT_RUN",
      "human_review":"UNRATED","learning_gain":"NOT_MEASURED",
      "quality_3b1b":"NOT_PROVEN","production":"BLOCKED","result":"PRESTART"}
    save(out,receipt)
    try:
        receipt["cost_preflight"]=preflight_model_and_key(
            key=key,catalog_sender=catalog_sender,key_sender=key_sender)
    except (Blocked,HTTPError,URLError,TimeoutError,TypeError,ValueError,KeyError) as exc:
        receipt["result"]="DENY_PAID_REQUEST_PREFLIGHT"
        receipt["failure_type"]=type(exc).__name__
        if isinstance(exc,Blocked):receipt["reason"]=str(exc)[:120]
        if isinstance(exc,HTTPError):receipt["http_status"]=exc.code
        save(out,receipt);return receipt
    _,raw=data_payload()
    receipt["request_sha256"]=sha256(raw).hexdigest()
    receipt["provider_post_attempts"]=1
    receipt["result"]="SINGLE_PAID_GPT_POST_ATTEMPTED"
    save(out,receipt)
    print("V393_GENUINE_ONE_GPT6_LUNA_POST_ATTEMPT",flush=True)
    try:
        result=post_once(key=key,raw=raw,sender=post_sender)
    except (Blocked,HTTPError,URLError,TimeoutError,TypeError,ValueError) as exc:
        receipt["result"]="PROVIDER_TRANSPORT_OR_HTTP_NO_RETRY"
        receipt["failure_type"]=type(exc).__name__
        if isinstance(exc,HTTPError):receipt["http_status"]=exc.code
        save(out,receipt);return receipt
    try:
        need(type(result) is dict,"ENVELOPE_BAD_SHAPE")
        receipt["actual_model"]=safe_model(result.get("model"))
        receipt["usage"]=safe_usage(result.get("usage"))
        sid=result.get("id")
        if type(sid) is str and 6<=len(sid)<=200:
            receipt["response_id_sha256"]=sha256(sid.encode()).hexdigest()
        choices=result.get("choices")
        need(type(choices) is list and len(choices)==1,"BAD_CHOICE_COUNT")
        item=choices[0]
        need(type(item) is dict,"BAD_CHOICE_SHAPE")
        receipt["finish_reason"]=safe_finish(item.get("finish_reason"))
        receipt["native_finish_reason"]=safe_finish(item.get("native_finish_reason"))
        save(out,receipt)
        need(receipt["response_id_sha256"]!="UNOBSERVED","PROVIDER_ID_MISSING")
        need(receipt["actual_model"]==MODEL,"PAID_MODEL_ID_NOT_EXACT_GPT6_LUNA")
        # Cost actually returned by provider is trusted only as its own report, not bank settlement.
        if "cost" in (result.get("usage") or {}):
            reported=money(result["usage"]["cost"])
            need(reported<=MAX_USD,"PROVIDER_REPORTED_COST_OVER_1_CENT")
        need(receipt["finish_reason"]=="stop","OUTPUT_NOT_FINISHED")
        msg=item.get("message") or {}
        need(type(msg) is dict and type(msg.get("content")) is str,"MISSING_MODEL_JSON")
        payload=strict_parse(msg["content"].encode("utf-8"))
        compiled=host_compile(payload)
        witness=creative_witness(payload,compiled)
        receipt["candidate_origin"]="GENUINE_GPT6_LUNA_NETWORK" if genuine else "TEST_MOCK_NOT_GENUINE"
        receipt["model_storyboard"]="HOST_ADMITTED_ORIGINAL" if genuine else "TEST_ONLY"
        receipt["creative_witness"]=witness
        receipt["result"]="REAL_GPT_STORYBOARD_ACCEPTED_NATIVE_PENDING" if genuine else "MOCK_ACCEPTED_NO_REAL_AI"
        (out/"accepted_GPT_storyboard_not_human_approved.json").write_text(
            json.dumps(payload,indent=2,sort_keys=True)+"\n")
        save(out,receipt)
    except (Blocked,Rejected,TypeError,ValueError,KeyError,IndexError) as exc:
        receipt["result"]="MODEL_STORYBOARD_REJECTED_NO_RETRY"
        receipt["failure_type"]=type(exc).__name__
        if isinstance(exc,(Blocked,Rejected)):
            receipt["reason"]=str(exc)[:120]
        save(out,receipt);return receipt
    if not native:
        receipt["result"]="ACCEPTED_MODEL_BUT_NATIVE_NOT_RUN"
        save(out,receipt);return receipt
    try:
        video=build_comparison(host_test_baseline(),compiled,out/"native_pair")
        need(video["matched_video_frame_counts"] is True and
             video["candidate_vs_baseline_midpoint_MAD"]>0,
             "NATIVE_SEMANTIC_DIFFERENCE_OR_FRAME_FAILURE")
        for m in video["native_mp4s"]:
            f=out/"native_pair"/m["name"]
            need(file_sha(f)==m["sha256"] and probe(f)==m["native_frames"],
                 "BAD_REAL_NATIVE_MP4_SHA_CODEC")
        receipt["native_video"]="FULL_DECODED_NATIVE_H264_AAC"
        receipt["native_video_frames"]=video["native_mp4s"][1]["native_frames"]
        receipt["result"]="ONE_GENUINE_PAID_GPT_STORYBOARD_TO_NATIVE_TECHNICAL_PASS" if genuine else "TEST_MOCK_NATIVE_NOT_AI"
    except Exception as exc:
        receipt["result"]="GPT_CANDIDATE_NATIVE_RENDER_FAILED"
        receipt["native_failure_type"]=type(exc).__name__
    save(out,receipt)
    return receipt

if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--paid-gpt-one-shot",action="store_true")
    cli.add_argument("--output",type=Path,required=True)
    args=cli.parse_args()
    need(args.paid_gpt_one_shot,"MISSING_EXPLICIT_PAID_GPT_ONE_SHOT")
    r=run(args.output,key=os.getenv("OPENROUTER_API_KEY",""))
    print("V393_FINAL",r["result"],"posts",r["provider_post_attempts"],
          "finish",r["finish_reason"],flush=True)
    if r["result"]!="ONE_GENUINE_PAID_GPT_STORYBOARD_TO_NATIVE_TECHNICAL_PASS":
        sys.exit(2)
