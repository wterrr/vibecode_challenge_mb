"""V3-50: one genuine OpenRouter GPT-6 Luna model POST after prior offline gates.

LIVE only from unique commit marker in a dedicated GitHub job. No secrets
or network inside Docker; no retries, model fallback or unbounded model code.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_manim_runner import (
    API,MODEL,_audio,_docker_manim,_codec_and_pixel_gates,sha as file_sha)
from learnflow_v3.model_authored_attention import (
    ROOT,REG,prereg,request_body,portable_schema,verify_storyboard,
    synthetic_fixture,beat_object,compile_manim,sha,exact_example)
from scripts.run_v3_44_semantic_counterfactual import deterministic_mux


def _json(path,data):
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\\n")


def _failure(out,code,requests,model_sha=None):
    _json(out/"v350_failure.json",{
      "checkpoint":"V3-50-ONE-QUERY-ATTENTION","code":code,
      "attempted_model_http_posts":requests,
      "model_response_sha256":model_sha,
      "no_retry":True,"no_fallback":True,"production":"BLOCKED"})


def model_once(out,key,*,sender=urlopen):
    """Sender injected in OFFLINE tests; only live CLI uses urllib.request."""
    if not isinstance(key,str) or len(key)<10:
        _failure(out,"V350_API_KEY_MISSING",0)
        raise Blocked("V350_API_KEY_MISSING")
    body=request_body()
    payload=json.dumps(body).encode()
    request=Request(API,data=payload,method="POST",headers={
        "Authorization":"Bearer "+key,"Content-Type":"application/json",
        "HTTP-Referer":"https://github.com/wterrr/vibecode_challenge_mb",
        "X-Title":"LearnFlow V3-50 single attention query"})
    _json(out/"v350_request_attempt.json",{
      "attempted_model_http_posts":1,"model":MODEL,
      "request_body_sha256":sha(body),
      "schema_sha256":sha(portable_schema()),
      "temperature_sent":False,"fallback":False,
      "retries":0,"raw_key_saved":False})
    try:
        with sender(request,timeout=125) as conn:
            b=conn.read(180000)
    except HTTPError as exc:
        code="V350_PROVIDER_HTTP_"+str(exc.code)
        _failure(out,code,1)
        raise Blocked(code) from None
    except (OSError,URLError,TimeoutError):
        _failure(out,"V350_PROVIDER_TRANSPORT_BLOCKED",1)
        raise Blocked("V350_PROVIDER_TRANSPORT_BLOCKED") from None
    try:
        envelope=json.loads(b.decode("utf-8"))
        choices=envelope["choices"]
        if not isinstance(choices,list) or len(choices)!=1 or choices[0].get("finish_reason")!="stop":
            raise Blocked("V350_TRUNCATED_OR_AMBIGUOUS_MODEL")
        reply=choices[0]["message"]["content"]
        if not isinstance(reply,str) or len(reply)>35000:
            raise Blocked("V350_CONTENT_INVALID")
        if envelope.get("model") not in (None,MODEL):
            raise Blocked("V350_MODEL_ID_MISMATCH")
    except (KeyError,IndexError,ValueError,TypeError,UnicodeError):
        _failure(out,"V350_BAD_PROVIDER_ENVELOPE",1)
        raise Blocked("V350_BAD_PROVIDER_ENVELOPE") from None
    h=sha256(reply.encode()).hexdigest()
    try:
        raw=json.loads(reply)
    except (TypeError,ValueError):
        _failure(out,"V350_JSON_DECODE_FAILURE",1,h)
        raise Blocked("V350_JSON_DECODE_FAILURE") from None
    try:
        story=verify_storyboard(raw)
    except (Blocked,KeyError,ValueError,TypeError):
        _failure(out,"V350_SCHEMA_OR_CLAIM_REJECTED",1,h)
        raise Blocked("V350_SCHEMA_OR_CLAIM_REJECTED") from None
    meta={
      "model":MODEL,"provider_echo":envelope.get("model"),
      "source":"REAL_OPENROUTER_ONE_AUTHORING_ATTEMPT",
      "provider_response_id_sha256":sha256(str(envelope.get("id","")).encode()).hexdigest(),
      "model_response_sha256":h,"validated_storyboard_sha256":sha(story),
      "schema_sha256":sha(portable_schema()),"request_body_sha256":sha(body),
      "usage":envelope.get("usage",{}),
      "http_post_attempts":1,"provider_fallback":False,"retry_count":0,
      "model_authored_python":False,"production":"BLOCKED"}
    _json(out/"v350_provider_receipt.json",meta)
    _json(out/"v350_validated_model_storyboard.json",story)
    return story,meta


def render(out,raw,origin,provider_receipt=None):
    if origin not in ("HOST_SYNTHETIC_OFFLINE","REAL_MODEL_ONE_ATTEMPT"):
        raise Blocked("V350_INVALID_PROVENANCE")
    verify_storyboard(raw)
    durations,beat_info,wav=_audio(out,beat_object(raw))
    source=out/"compiled_host_attention_manim.py"
    source.write_text(compile_manim(raw,durations),encoding="utf-8")
    raw_native,sandbox=_docker_manim(out,source)
    mp4=out/"attention_one_query_with_audio.mp4"
    mux=deterministic_mux(raw_native,wav,mp4,beat_info)
    qa=_codec_and_pixel_gates(mp4,beat_info)
    if qa["frames"]!=sum(b["frames"] for b in beat_info):
        raise Blocked("V350_EXACT_AUDIO_FRAME_DRIFT")
    if qa["max_decoded_sample_delta"]<=.9:
        raise Blocked("V350_STATIC_OUTPUT_REJECTED")
    evidence={
      "checkpoint":"V3-50-ONE-QUERY-ATTENTION",
      "result":"NATIVE_TECHNICAL_PASS_NOT_PEDAGOGICAL_PASS",
      "origin":origin,
      "model_authored_storyboard":origin=="REAL_MODEL_ONE_ATTEMPT",
      "model_http_posts":1 if origin=="REAL_MODEL_ONE_ATTEMPT" else 0,
      "provider_receipt_sha256":file_sha(out/"v350_provider_receipt.json") if provider_receipt else None,
      "model_storyboard_sha256":sha(raw),
      "host_compiler_sha256":file_sha(source),
      "video_sha256":file_sha(mp4),
      "audio_sha256":file_sha(wav),
      "grounded_example":exact_example(),
      "claims":["A1","A2","A3","A4"],"native_video":qa,
      "beats":beat_info,"mux":mux,"sandbox":sandbox,
      "math_truth":"HOST_COMPUTED_APPROVED_EXAMPLE",
      "model_prose_truth":"ONLY_RESTRICTED_BY_LOCAL_SCOPE_AND_SYNTAX",
      "human_learning":"NOT_MEASURED",
      "production":"BLOCKED"}
    _json(out/"v350_attention_video_receipt.json",evidence)
    return evidence


def run(out,mode,key=""):
    m=prereg()
    if out.exists():
        raise Blocked("V350_FRESH_OUTPUT_REQUIRED")
    out.mkdir(parents=True)
    _json(out/"v350_test_manifest.json",{
      "frozen_query":m["user_query"],
      "query_sha256":sha(m["user_query"]),
      "source":m["source"],
      "one_time_model_budget":m["one_shot_budget"],
      "requested_mode":mode})
    if mode=="offline":
        fixture=synthetic_fixture()
        _json(out/"v350_SYNTHETIC_FIXTURE_NOT_MODEL.json",fixture)
        result=render(out,fixture,"HOST_SYNTHETIC_OFFLINE")
    elif mode=="live":
        story,receipt=model_once(out,key)
        result=render(out,story,"REAL_MODEL_ONE_ATTEMPT",receipt)
    else:
        raise Blocked("V350_UNSUPPORTED_MODE")
    print("V3_50="+result["result"]+"_"+result["origin"],flush=True)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=["offline","live"],required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    a=parser.parse_args()
    try:
        run(a.output_dir,a.mode,key=os.environ.get("OPENROUTER_API_KEY",""))
    except Blocked as e:
        code=str(e)
        if not code.startswith("V350_"):
            code="V350_NATIVE_OR_PROVIDER_BLOCKED"
        if a.output_dir.is_dir() and not (a.output_dir/"v350_failure.json").exists():
            _failure(a.output_dir,code,1 if (a.output_dir/"v350_request_attempt.json").exists() else 0)
        print("V3_50=BLOCKED "+code,flush=True)
        raise SystemExit(2) from None


if __name__=="__main__":
    main()
