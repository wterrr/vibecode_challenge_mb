"""V3-29 opt-in FREE-only real OpenRouter Research/Script witness.

This does NOT let an LLM create unchecked domain facts or rewrite renderer
states. Real Research stage selects a source-verified relation; real Script stage
must emit exact source-authorized spoken claims and ordered IDs. Each provider
call is separate, bounded and evidenced by SHA only. No model-generated
research pack/pedagogy/director is claimed without actual evidence.
"""
from __future__ import annotations
from hashlib import sha256
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request,urlopen

from openrouter_policy import require_free_openrouter_model
from learnflow_v3.independent_source_gate import fetch_textbook
from learnflow_v3.multidomain_coverage import read_source,render_math
from learnflow_v3.source_grounded_compiler import (
  SEED_FILE,author_seeded_contracts,compile_linear_source_bound
)
from learnflow_v2.repair import compute_content_hash

VERSION="v3-29-free-model-source-to-script-witness-v1"
URL="https://openrouter.ai/api/v1/chat/completions"
CONTEXT={
  "LINEAR_SLOPE":{"relation":"rise_over_run",
                  "source_evidence":"Slope is the ratio of rise to run."},
  "CONSTANT_ACCELERATION_VELOCITY":{
    "relation":"v_equals_v0_plus_at",
    "source_evidence":"Under constant acceleration, final velocity is initial velocity plus acceleration times time."},
}
class ProviderBlocked(RuntimeError):pass

def _text(response:dict)->str:
    if not isinstance(response,dict) or not isinstance(response.get("choices"),list):
        raise ProviderBlocked("MODEL_NO_CHOICES")
    choices=response["choices"]
    if len(choices)!=1:
        raise ProviderBlocked("MODEL_AMBIGUOUS_CHOICES")
    item=choices[0]
    if item.get("finish_reason") not in ("stop",None):
        raise ProviderBlocked("MODEL_INCOMPLETE_OUTPUT")
    data=item.get("message",{}).get("content")
    if not isinstance(data,str) or len(data)>12000:
        raise ProviderBlocked("MODEL_INVALID_MESSAGE")
    return data

def _json_message(response:dict)->dict:
    s=_text(response).strip()
    try:
        parsed=json.loads(s)
    except (ValueError,TypeError) as e:
        raise ProviderBlocked("MODEL_NOT_STRICT_JSON") from e
    if not isinstance(parsed,dict):
        raise ProviderBlocked("MODEL_JSON_NOT_OBJECT")
    return parsed

def post_free(*,model:str,key:str,stage:str,system:str,user:str,
              sender=None)->dict:
    model=require_free_openrouter_model(model)
    if stage not in ("RESEARCH","SCRIPT"):
        raise ValueError("V3_29_INVALID_STAGE")
    if not key or len(key.strip())<5:
        raise ProviderBlocked("KEY_NOT_CONFIGURED")
    if len(user)>8500:
        raise ValueError("V3_29_PROMPT_TOO_LONG")
    payload={"model":model,"temperature":0,"max_tokens":1450,
             "messages":[{"role":"system","content":system},
                         {"role":"user","content":user}]}
    # One HTTP attempt only. No paid model fallback, no retry/parallel fanout.
    request=Request(URL,data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization":"Bearer "+key,"Content-Type":"application/json",
                 "HTTP-Referer":"https://github.com/wterrr/vibecode_challenge_mb",
                 "X-Title":"LearnFlow V3-29 One-shot Free Source Witness"},
        method="POST")
    handler=sender or urlopen
    try:
        with handler(request,timeout=50) as resp:
            raw=resp.read(50_000)
    except HTTPError as exc:
        # No echoing untrusted provider body, headers or secrets.
        raise ProviderBlocked(f"MODEL_HTTP_{exc.code}") from None
    except (URLError, TimeoutError) as exc:
        raise ProviderBlocked("MODEL_NETWORK_OR_TIMEOUT") from None
    try:
        obj=json.loads(raw.decode("utf-8"))
    except (ValueError,UnicodeDecodeError) as exc:
        raise ProviderBlocked("MODEL_BODY_NOT_JSON") from exc
    out=_json_message(obj)
    return {"stage":stage,"response":out,"model":model,
            "output_sha256":sha256(json.dumps(out,sort_keys=True,
                    separators=(",",":")).encode()).hexdigest(),
            "provider_response_id_sha256":sha256(str(obj.get("id","")).encode()).hexdigest()}

def _validate_research(payload:dict,seed:dict)->None:
    expected=CONTEXT[seed["model_kind"]]
    if (set(payload)!={"model_kind","source_url","supported_relation"} or
        payload["model_kind"]!=seed["model_kind"] or
        payload["source_url"]!=seed["source_url"] or
        payload["supported_relation"]!=expected["relation"]):
        raise ProviderBlocked("RESEARCH_WITNESS_UNGROUNDED_OR_UNRECOGNIZED")
def _validate_script(payload:dict,bundle:dict)->None:
    if set(payload)!={"segments"} or not isinstance(payload["segments"],list):
        raise ProviderBlocked("SCRIPT_MISSING_SEGMENTS")
    if len(payload["segments"])!=len(bundle["script"].segments):
        raise ProviderBlocked("SCRIPT_DROPPED_OR_EXTRA_SEGMENT")
    for got,expected in zip(payload["segments"],bundle["script"].segments,strict=True):
        if (not isinstance(got,dict) or
            set(got)!={"segment_id","spoken_text","claim_ids"} or
            got["segment_id"]!=expected.segment_id or
            got["spoken_text"]!=expected.spoken_text or
            got["claim_ids"]!=list(expected.claim_ids)):
            raise ProviderBlocked("SCRIPT_SEMANTIC_CLAIM_OR_TEXT_DRIFT")
def run_one(*,root:Path,out:Path,model:str,key:str,
            fetcher=fetch_textbook,sender=None,do_render=True)->dict:
    if not out.is_dir() or any(out.iterdir()):
        raise ValueError("V3_29_OUTPUT_MUST_BE_EMPTY")
    # Model selection/price policy is checked BEFORE any network activity.
    model=require_free_openrouter_model(model)
    topic_index={x["topic_id"]:x for x in read_source(root)[0]}
    seeds=json.loads((root/SEED_FILE).read_text())["cases"]
    # Pre-registered bounded *single* source/topic pilot only; no cherry-pick.
    seed=next(x for x in seeds if x["topic_id"]=="lfb-020-math")
    topic=topic_index[seed["topic_id"]]
    source_receipt=fetcher(seed)
    if source_receipt.get("status")!="SOURCE_HTML_ANCHOR_VERIFIED_NOT_INDEPENDENT_SEMANTIC_REVIEW":
        raise ProviderBlocked("EXTERNAL_SOURCE_ANCHOR_NOT_VERIFIED")
    bundle=author_seeded_contracts(topic=topic,seed=seed)
    prompts=CONTEXT[seed["model_kind"]]
    research_prompt=json.dumps({
      "source_url":seed["source_url"],"published_anchor":prompts["source_evidence"],
      "allowed_model_kind":seed["model_kind"],
      "allowed_relation":prompts["relation"],
      "response_format":{"model_kind":"...", "source_url":"...",
                         "supported_relation":"..."}
    })
    research=post_free(model=model,key=key,stage="RESEARCH",
        system="You are a research agent validating one published relation. Return ONLY a JSON object with the three requested fields. Do not invent other sources or claims.",
        user=research_prompt,sender=sender)
    _validate_research(research["response"],seed)
    expected=[{"segment_id":s.segment_id,"spoken_text":s.spoken_text,
               "claim_ids":list(s.claim_ids)} for s in bundle["script"].segments]
    script=post_free(model=model,key=key,stage="SCRIPT",
        system="You are a lesson script agent. Return ONLY JSON {\"segments\": [...]} faithfully preserving every supplied segment_id, spoken_text and claim_ids in order. Do not add facts, instructions or commentary.",
        user=json.dumps({"source_verified_relation":research["response"],
                         "source_grounded_script_segments":expected},
                        ensure_ascii=False),sender=sender)
    _validate_script(script["response"],bundle)
    # The *provider response*, not a fixture, now supplies the original script
    # literal words/claim IDs (strict identity required). The existing
    # Hermes→V3-09→Visual Director→graph/speech certificate actually runs.
    original=bundle["script"]
    actual=original.model_copy(update={
       "segments":tuple(original_seg.model_copy(
         update={"spoken_text":model_seg["spoken_text"]})
         for original_seg,model_seg in zip(original.segments,
                                          script["response"]["segments"],strict=True))})
    checked={**bundle,"script":actual}
    events,proof=compile_linear_source_bound(bundle=checked)
    if do_render:
        folder=out/"lfb-020-math";folder.mkdir()
        video=render_math(topic=topic,output=folder,
                          compiled_spec=(bundle["graph"],bundle["spec"]),
                          compiled_events=events,compiler_provenance=proof)
        mp4sha=video["video_sha256"]
    else:
        mp4sha=None
    result={"checkpoint":"V3-29","status":"LIVE_FREE_SOURCE_RESEARCH_AND_SCRIPT_WITNESS_PASS",
            "model":model,"topic_id":topic["topic_id"],"real_provider_requests":2,
            "research_output_sha256":research["output_sha256"],
            "script_output_sha256":script["output_sha256"],
            "source_receipt":source_receipt,
            "claim_script_graph_certificate_sha256":compute_content_hash(proof),
            "bounded_real_mp4_sha256":mp4sha,
            "research_pack_and_script_origin":"AUTHOR_SEEDED_BOUNDS_REAL_MODEL_CONFIRMED_RELATION_AND_EMITTED_WORDS",
            "independent_full_semantic_fact_review":"UNMEASURED",
            "model_produced_novel_scientific_claims":False,
            "model_produced_creative_lesson":"NO_FIXED_SAFE_NARRATION",
            "live_pedagogy_or_visual_agent":False,
            "full_autonomous_lesson":"NO",
            "frozen_v3_16":"UNCHANGED","paid_api":"PROHIBITED",
            "human_quality":"UNMEASURED","production":"BLOCKED"}
    (out/"v3_29_live_witness_receipt.json").write_text(json.dumps(result,indent=2)+"\n")
    return result
