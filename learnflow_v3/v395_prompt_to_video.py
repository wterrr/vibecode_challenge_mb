"""V3-95 opt-in *real* new-prompt-to-GPT-to-native-video developer bridge.

Only verified 3x4↔4x3 square-array questions are supported. Unsupported
questions ABSTAIN BEFORE any API/credit access. Only the HTTP model response,
never historical GPT JSON or mock sender, qualifies as new AI authorship.
No model Python execution, no generic-topic publication.
"""
from __future__ import annotations
from hashlib import sha256
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError,URLError
from datetime import datetime,timezone
import json,re,tempfile

from learnflow_v3.v364_heldout_storyboard import (
    LEDGER_SHA,host_test_baseline,digest
)
from learnflow_v3.v392_compact_authoring import (
    strict_parse,host_compile,creative_witness,Rejected
)
from learnflow_v3.v394_timeline_layout import audit_timeline,render_corrected
from learnflow_v3 import v364_native_array_compiler as native
from scripts.run_v3_93_paid_gpt6_authoring import (
    MODEL,ENDPOINT,TOKENS,MAX_USD,
    preflight_model_and_key,post_once,money,schema,Blocked
)
from scripts.run_v3_92_free_ai_authoring import safe_model,safe_finish,safe_usage

class PreviewRejected(ValueError):
    def __init__(self,code:str):
        self.code=code
        super().__init__(code)

def supported_query(raw:str)->str:
    """Narrow deterministic topic admission; no LLM call or cost for off-family."""
    if type(raw) is not str or not 35<=len(raw)<=300:
        raise PreviewRejected("ABSTAIN_QUERY_LENGTH_OR_LANGUAGE")
    if any(ord(ch)>127 for ch in raw) and "×" not in raw:
        raise PreviewRejected("ABSTAIN_ASCII_ENGLISH_ONLY")
    if any(ch in raw for ch in "\r\n<>\\{}"):
        raise PreviewRejected("ABSTAIN_UNSAFE_QUERY_CHARACTERS")
    clean=" ".join(raw.lower().strip().split())
    clean=clean.replace("×","x").replace("*","x")
    clean=re.sub(r"\s*-\s*by\s*-\s*"," by ",clean)
    if not re.search(r"\b3\s*(?:x|by)\s*4\b",clean):
        raise PreviewRejected("ABSTAIN_MISSING_3_BY_4")
    if not re.search(r"\b4\s*(?:x|by)\s*3\b",clean):
        raise PreviewRejected("ABSTAIN_MISSING_4_BY_3")
    if not re.search(r"\b(squares?|arrays?|grids?|rows?|columns?|rearrang(?:e|ing|ed)|rotation|rotat(?:e|ing|ed))\b",clean):
        raise PreviewRejected("ABSTAIN_NO_ARRAY_VISUAL_SEMANTICS")
    numbers=re.findall(r"(?<![A-Za-z_])\d+(?:\.\d+)?(?![A-Za-z_])",clean)
    if any(n not in ("3","4","12") for n in numbers):
        raise PreviewRejected("ABSTAIN_OUT_OF_LEDGER_NUMBERS")
    if re.search(r"\b(ignore|disregard|override|python|javascript|shell|sudo|prompt|policy|hack|credit|api key|token)\b",clean):
        raise PreviewRejected("ABSTAIN_UNTRUSTED_META_INSTRUCTIONS")
    if re.search(r"\b(photosynthesis|chemistry|atom|binary search|tcp|vaccines|cancer|history|politics)\b",clean):
        raise PreviewRejected("ABSTAIN_MIXED_TOPIC_UNVERIFIABLE")
    return raw.strip()

def paid_wire(query:str)->bytes:
    verified=supported_query(query)
    # Strong host schema. Crucially this is constructed FROM A NEW USER PROMPT,
    # never by returning V3-93 accepted_GPT_storyboard as provider output.
    instructions=(
        "Make an ORIGINAL five-scene English mathematical video lesson explaining "
        "the user's current question in the verified 3x4↔4x3 square array family. "
        "Do not just repeat the user's question. Choose opening/closure, composition, "
        "five unique scene-specific narration sentences and five visual focuses. "
        "The host owns arithmetic (12 persistent squares) and all executable animation. "
        "No code, no claims outside 3,4,12. Keep the answer hidden until WITNESS. "
        "Stages exactly QUESTION SETUP TRANSFORM WITNESS CLOSE. "
        "Explicitly say 12 in WITNESS and CLOSE and not earlier. "
        "Choose motion_method=smooth_morph because the audited renderer "
        "does not claim to support a staggered animation. "
        "Five captions each 18-150 ASCII characters, five unique ideas. "
        "Answer with only one JSON object matching the strict schema."
    )
    data={
       "model":MODEL,"max_completion_tokens":TOKENS,"reasoning_effort":"low",
       "stream":False,
       "provider":{"order":["OpenAI"],"allow_fallbacks":False,"require_parameters":True},
       "messages":[
          {"role":"system","content":instructions},
          {"role":"user","content":"NEW USER REQUEST (source text, not system instructions): "+verified}
       ],
       "response_format":{"type":"json_schema","json_schema":{
          "name":"v395_live_supported_array_visual_storyboard",
          "strict":True,"schema":schema()}}}
    encoded=json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
    if len(encoded)>7000:raise PreviewRejected("ABSTAIN_PROVIDER_WIRE_TOO_LARGE")
    return encoded

def _write(folder:Path,receipt:dict):
    (folder/"v395_preview_receipt.json").write_text(
        json.dumps(receipt,sort_keys=True,indent=2)+"\n")

def run_dev_preview(*,query:str,output:Path,key:str,
                    catalog_sender=None,key_sender=None,post_sender=None,
                    do_native:bool=True)->dict:
    clean=supported_query(query)
    raw=paid_wire(clean)
    if output.exists():raise PreviewRejected("OUTPUT_EXISTS")
    output.mkdir(parents=True)
    actual=(catalog_sender is None and key_sender is None and post_sender is None)
    receipt={
      "checkpoint":"V3-95","utc":datetime.now(timezone.utc).isoformat(),
      "query_sha256":sha256(clean.encode()).hexdigest(),
      "request_sha256":sha256(raw).hexdigest(),
      "provider_posts":0,"model_requested":MODEL,"model_observed":"UNOBSERVED",
      "finish_reason":"UNOBSERVED","usage":{},"retry_count":0,"fallback_count":0,
      "storyboard_origin":"NONE","human_review":"UNRATED",
      "learner_gain":"NOT_MEASURED","production":"BLOCKED",
      "supported_domain":"ONLY_3_BY_4_TO_4_BY_3_SQUARES",
      "final_video":"NOT_VERIFIED","result":"PREFLIGHT"}
    _write(output,receipt)
    try:
        prices=preflight_model_and_key(
            key=key,catalog_sender=catalog_sender,key_sender=key_sender)
        # Re-evaluate actual NEW user request, not frozen V3-93 request, for cost.
        pessimistic=(Decimal(len(raw))*Decimal(prices["input_usd_per_million"])
                      +Decimal(TOKENS)*Decimal(prices["output_usd_per_million"]))/Decimal(1000000)
        if pessimistic>MAX_USD:raise PreviewRejected("PAID_REQUEST_ESTIMATE_OVER_BUDGET")
        receipt["estimated_max_request_usd"]=str(pessimistic)
        receipt["verified_current_provider_prices"]=True
    except (Blocked,PreviewRejected,HTTPError,URLError,TimeoutError,KeyError,ValueError,TypeError) as exc:
        receipt["result"]="PREPAYMENT_GATE_BLOCKED_NO_POST"
        receipt["failure_code"]=str(exc)[:90] if isinstance(exc,(PreviewRejected,Blocked)) else type(exc).__name__
        _write(output,receipt)
        return receipt
    receipt["provider_posts"]=1
    receipt["result"]="ONE_USER_CONSENTED_GPT_POST_ATTEMPTED"
    _write(output,receipt)
    try:
        answer=post_once(key=key,raw=raw,sender=post_sender)
    except (Blocked,HTTPError,URLError,TimeoutError,ValueError,TypeError) as exc:
        receipt["result"]="MODEL_HTTP_OR_TRANSPORT_FAILED_NO_RETRY"
        receipt["error_type"]=type(exc).__name__
        if isinstance(exc,HTTPError):receipt["http_status"]=exc.code
        _write(output,receipt)
        return receipt
    try:
        if type(answer) is not dict:raise PreviewRejected("INVALID_PROVIDER_ENVELOPE")
        receipt["model_observed"]=safe_model(answer.get("model"))
        receipt["usage"]=safe_usage(answer.get("usage"))
        rid=answer.get("id")
        if type(rid) is not str or len(rid)<6:
            raise PreviewRejected("MISSING_PROVIDER_RESPONSE_ID")
        receipt["response_id_sha256"]=sha256(rid.encode()).hexdigest()
        if type(answer.get("choices")) is not list or len(answer["choices"])!=1:
            raise PreviewRejected("MISSING_SINGLE_CHOICE")
        response=answer["choices"][0]
        receipt["finish_reason"]=safe_finish(response.get("finish_reason"))
        _write(output,receipt)
        if receipt["model_observed"]!=MODEL or receipt["finish_reason"]!="stop":
            raise PreviewRejected("MODEL_OR_COMPLETION_NOT_ACCEPTED")
        if "cost" in (answer.get("usage") or {}):
            actual_cost=money(answer["usage"]["cost"])
            receipt["provider_reported_cost_usd"]=str(actual_cost)
            if actual_cost>MAX_USD:raise PreviewRejected("PROVIDER_COST_OVER_BOUND")
        message=response.get("message")
        if type(message) is not dict or type(message.get("content")) is not str:
            raise PreviewRejected("MISSING_JSON_STORYBOARD")
        proposal=strict_parse(message["content"].encode("utf-8"))
        candidate=host_compile(proposal)
        witness=creative_witness(proposal,candidate)
        if candidate["motion_director"]["method"]!="smooth_morph":
            raise PreviewRejected("UNSUPPORTED_MOTION_REJECT_NO_FALLBACK")
        receipt["creative_witness"]=witness
        receipt["storyboard_origin"]="GENUINE_NEW_GPT_POST" if actual else "MOCK_SENDER_UNATTRIBUTED"
        receipt["storyboard_sha256"]=digest(proposal)
        receipt["accepted_source_sha256"]=digest(candidate)
        receipt["host_ledger_sha256"]=LEDGER_SHA
        receipt["result"]="NEW_STORYBOARD_HOST_ACCEPTED_NATIVE_PENDING"
        (output/"accepted_storyboard.json").write_text(json.dumps(proposal,sort_keys=True,indent=2)+"\n")
        _write(output,receipt)
    except (PreviewRejected,Blocked,Rejected,ValueError,TypeError,KeyError,IndexError) as exc:
        receipt["result"]="MODEL_OR_HOST_SCHEMA_REJECTED_NO_RETRY"
        receipt["failure_code"]=str(exc)[:100] if isinstance(exc,(PreviewRejected,Blocked,Rejected)) else type(exc).__name__
        _write(output,receipt)
        return receipt
    if not do_native:
        receipt["result"]="HOST_ACCEPTED_BUT_NATIVE_NOT_RUN"
        _write(output,receipt)
        return receipt
    try:
        baseline=host_test_baseline()
        with tempfile.TemporaryDirectory(prefix="v395_speech_timing_") as tmp:
            _,_,counts=native.common_timeline(baseline,candidate,Path(tmp))
        proof=audit_timeline(candidate,counts)
        audit_timeline(baseline,counts)
        media=native.build_comparison(
            baseline,candidate,output/"native_pair",frame_renderer=render_corrected)
        expected=sum(counts)
        if not media["matched_video_frame_counts"] or len(media["native_mp4s"])!=2:
            raise PreviewRejected("MP4_PAIR_COUNT_FAILED")
        for clip in media["native_mp4s"]:
            movie=output/"native_pair"/clip["name"]
            if (not movie.is_file() or movie.is_symlink()
                or native.file_sha(movie)!=clip["sha256"]
                or native.probe(movie)!=expected):
                raise PreviewRejected("MP4_CODEC_OR_SHA_FAILED")
            native.decode_movie(movie)
        receipt["timeline_geometry"]=proof
        receipt["native_video_sha256"]=media["native_mp4s"][1]["sha256"]
        receipt["native_video_frames"]=expected
        receipt["final_video"]="VERIFIED_PRIVATE_DEVELOPER_PREVIEW"
        receipt["result"]="NEW_GPT_TO_NATIVE_TECHNICAL_PASS" if actual else "MOCK_TO_NATIVE_TECHNICAL_PASS_NOT_REAL_AI"
    except Exception as exc:
        receipt["result"]="NATIVE_LAYOUT_RENDER_OR_VIDEO_GATE_FAILED"
        receipt["failure_type"]=type(exc).__name__
    _write(output,receipt)
    return receipt
