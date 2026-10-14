#!/usr/bin/env python3
"""V3-64: fixed prompt, EXACTLY one authorized OpenRouter POST, no retry/fallback.

Online only on explicit unique one-time GitHub workflow trigger. Unit tests inject
fake senders; never treat them as real inference provenance.
"""
from __future__ import annotations
import argparse,json,os,sys,urllib.request,urllib.error,datetime
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.v364_heldout_storyboard import (
    SCHEMA,LEDGER,LEDGER_SHA,TOPIC,QUERY,MAX_WIRE,
    accept,strict_load,host_test_baseline,assert_prereg,digest
)
from learnflow_v3.v364_native_array_compiler import build_comparison
REG=ROOT/"benchmarks/learnflowbench/v3/v3_64_one_shot_genuine_storyboard_preregister.json"
MODEL="openai/gpt-6-luna"
URL="https://openrouter.ai/api/v1/chat/completions"

def need(value,msg):
    if not value:raise ValueError("V364_"+msg)
def provider_schema(obj):
    """Strip nonportable JSON-Schema validation keywords before native strict mode.
    Local host validator still enforces all constraints after response.
    """
    if isinstance(obj,list):return [provider_schema(x) for x in obj]
    if isinstance(obj,dict):
        skip={"minLength","maxLength","minItems","maxItems","pattern","minimum","maximum"}
        return {k:provider_schema(v) for k,v in obj.items() if k not in skip}
    return obj
def prompt():
    return (
      "You are a research-stage five-role educational storyboard team for LearnFlow. "
      "The output is a new STORYBOARD IDEA, not executable instructions. "
      "It must contain all five specialist roles: cognitive designer chooses the probable "
      "learner misconception and a precise probe; narrative designer chooses a strong "
      "question and how the understanding is closed; visual thinker selects a clear "
      "spatial presentation and semantic focus; motion director orchestrates physically "
      "observable change while keeping 12 identical object IDs; visual critic acknowledges "
      "identity-loss risk and demands observable evidence. This is NOT copyrighted "
      "3Blue1Brown source reproduction. The host fact ledger is immutable: "
      +json.dumps(LEDGER,sort_keys=True)+"; SHA256="+LEDGER_SHA+". "
      "New heldout question: "+QUERY+". "
      "Return exactly five ordered beats QUESTION, SETUP, TRANSFORM, WITNESS, CLOSE. "
      "Each caption is original concise English teacher narration, 18-150 characters. "
      "Before WITNESS, do not say the answer 12 or the full equation; let viewer predict. "
      "At WITNESS and CLOSE explicitly state 12. "
      "The same IDs unit_00 through unit_11 must appear in ascending order, "
      "never created/destroyed. Layout columns must be 4 for first two beats and "
      "3 for the last three; only beat 3 TRANSFORM interpolates the layout. "
      "No unverified maths, invented references, model-generated code or arbitrary video "
      "timestamps. Full correct source ledger SHA and protocol version are required. "
      "Choose the five role strategies in the JSON schema and make the sequence "
      "engaging but rigorously accurate. Any output may be rejected by the host; "
      "the host will not repair your answer."
    )
def request_payload():
    schema=provider_schema(SCHEMA)
    data={"model":MODEL,"max_tokens":2100,"stream":False,
      "provider":{"order":["OpenAI"],"allow_fallback":False,"require_parameters":True},
      "messages":[
        {"role":"system","content":"Produce one original grounded pedagogical storyboard in STRICT JSON only. Do not make up facts."},
        {"role":"user","content":prompt()}
      ],
      "response_format":{"type":"json_schema","json_schema":{
          "name":"learnflow_v364_genuine_five_role","strict":True,"schema":schema}}}
    raw=json.dumps(data,separators=(",",":"),ensure_ascii=True).encode()
    need(len(raw)<=14000,"PROMPT_BYTES_TOO_LARGE")
    need("temperature" not in data,"TEMPERATURE_MUST_BE_OMITTED")
    return data,raw
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise ValueError("V364_REDIRECT_BLOCKED")
def post_once(key,raw,send=None):
    need(bool(key) and len(key)>15 and "\n" not in key,"API_KEY_MISSING")
    req=urllib.request.Request(URL,data=raw,headers={
      "Authorization":"Bearer "+key,
      "Content-Type":"application/json",
      "HTTP-Referer":"https://github.com/wterrr/vibecode_challenge_mb",
      "X-Title":"LearnFlow V3-64 One-Shot Scientific Study"
    },method="POST")
    with (send or urllib.request.build_opener(NoRedirect()).open)(req,timeout=125) as res:
        need(getattr(res,"status",200)==200,"MODEL_NON_200")
        payload=res.read(250000)
        need(0<len(payload)<250000,"RESPONSE_TOO_LARGE")
        return json.loads(payload)

def run(out:Path,*,key:str,send=None):
    r=assert_prereg(REG)
    need(not out.exists(),"OUTPUT_EXISTS")
    out.mkdir(parents=True)
    manifest={"checkpoint":"V3-64","start_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "preregistered_ledger_sha":LEDGER_SHA,"requested_model":MODEL,
      "max_new_model_posts":1,"retry":0,"fallback":False,
      "candidate_origin":"NOT_YET_OBSERVED",
      "provider_post_attempts":0,"outcome":"PREFLIGHT","production":"BLOCKED"}
    (out/"attempt_receipt.json").write_text(json.dumps(manifest,indent=2))
    if not key:
        manifest.update(outcome="BLOCKED_MISSING_API_KEY",provider_post_attempts=0)
        (out/"attempt_receipt.json").write_text(json.dumps(manifest,indent=2))
        print("V364_BLOCKED_MISSING_API_KEY",flush=True)
        return manifest
    payload,raw=request_payload()
    manifest.update(provider_post_attempts=1,
      request_body_sha256=sha256(raw).hexdigest(),
      output_token_limit=2100,outcome="POST_ATTEMPTED")
    (out/"attempt_receipt.json").write_text(json.dumps(manifest,indent=2))
    print("V364_ONE_AUTHORIZED_POST_ATTEMPT",flush=True)
    try:
        response=post_once(key,raw,send=send)
    except (urllib.error.HTTPError,urllib.error.URLError,ValueError,TimeoutError,TimeoutError) as e:
        # Provider may charge even on transport interruption; never retry.
        manifest.update(outcome="PROVIDER_TRANSPORT_OR_HTTP_FAILURE_NO_RETRY",
                        error_type=type(e).__name__)
        (out/"attempt_receipt.json").write_text(json.dumps(manifest,indent=2))
        print("V364_PROVIDER_FAILURE_NO_RETRY",type(e).__name__,flush=True)
        return manifest
    # Never treat a local fake send() as a real provider response.
    true_provider=send is None
    manifest["provider_http_response_observed"]=True
    manifest["provider_response_id"]=str(response.get("id",""))[:90]
    manifest["actual_returned_model"]=str(response.get("model",""))[:95]
    usage=response.get("usage") or {}
    manifest["usage"]={field:usage.get(field) for field in
      ("prompt_tokens","completion_tokens","total_tokens","cost") if field in usage}
    if true_provider and (not manifest["provider_response_id"] or
       MODEL not in manifest["actual_returned_model"]):
        manifest["outcome"]="PROVIDER_IDENTITY_NOT_VERIFIED"
        (out/"attempt_receipt.json").write_text(json.dumps(manifest,indent=2))
        return manifest
    try:
        choice=response["choices"][0]
        message=choice["message"]
        need(choice.get("finish_reason")=="stop","PROVIDER_TRUNCATED_OR_REFUSED")
        body=message["content"]
        need(isinstance(body,str),"NO_PROVIDER_JSON_TEXT")
        candidate=strict_load(body.encode("utf-8"))
        acceptance=accept(candidate)
    except (KeyError,IndexError,TypeError,ValueError) as e:
        manifest.update(outcome="PROVIDER_RESPONSE_REJECTED_BY_HOST",
            schema_validation_reason=str(e)[:150])
        (out/"attempt_receipt.json").write_text(json.dumps(manifest,indent=2))
        return manifest
    # This is a genuine external response only when the real network path was used.
    (out/"candidate_UNVERIFIED_AUTHORING.json").write_text(
        json.dumps(candidate,indent=2,sort_keys=True)+"\n")
    manifest.update(outcome="MODEL_CANDIDATE_ACCEPTED_NATIVE_NOT_YET_VERIFIED",
        candidate_sha256=digest(candidate),native_pending=True,
        candidate_origin="REAL_PROVIDER_RESPONSE" if true_provider else
          "HOST_TEST_SENDER_NOT_REAL_PROVIDER",
        external_model_authorship="PROVIDER_RESPONSE_OBSERVED" if true_provider else
          "NOT_TESTED_FAKE_SENDER",semantic_truth="HOST_GROUNDED_BOUNDED_NO_HUMAN_REVIEW")
    (out/"attempt_receipt.json").write_text(json.dumps(manifest,indent=2))
    try:
        video=build_comparison(host_test_baseline(),candidate,out/"native_pair")
    except Exception as e:
        manifest.update(outcome="NATIVE_RENDER_OR_SOURCE_GATE_FAILED",
                        native_error_type=type(e).__name__)
        (out/"attempt_receipt.json").write_text(json.dumps(manifest,indent=2))
        return manifest
    manifest.update(outcome="BOUNDED_REAL_MODEL_AUTHORING_AND_NATIVE_TECHNICAL_PASS"
                        if true_provider else "TEST_ONLY_NATIVE_TECHNICAL_PASS",
      native_pending=False,
      native_movies=2,
      native_frame_count=video["native_mp4s"][0]["native_frames"],
      native_candidate_witness_MAD=video["early_to_witness_MAD"],
      human_quality="UNRATED",learning_gain="NOT_MEASURED",
      user_generalization="NOT_ESTABLISHED",production="BLOCKED")
    (out/"attempt_receipt.json").write_text(json.dumps(manifest,indent=2))
    print("V364_FINAL",manifest["outcome"],"native",manifest["native_movies"],flush=True)
    return manifest

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--live",action="store_true")
    args=p.parse_args()
    need(args.live,"EXPLICIT_LIVE_FLAG_REQUIRED")
    run(args.output,key=os.getenv("OPENROUTER_API_KEY",""))
if __name__=="__main__":main()
