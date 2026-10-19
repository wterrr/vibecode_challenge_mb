"""V3-91 hostile offline test: no test sender is ever real provider provenance."""
from __future__ import annotations
from copy import deepcopy
import io
import json
import pytest
from pathlib import Path
from learnflow_v3.v364_heldout_storyboard import host_test_baseline
from scripts.run_v3_91_single_free_ai_pilot import (
    registered,safe_get_catalog,request_once,payload,run,FREE,Denied
)

class Response(io.BytesIO):
    status=200

def sender_of(obj, calls):
    def send(req,timeout=None):
        calls.append(req)
        return Response(json.dumps(obj).encode())
    return send

def catalog(price="0",exists=True):
    return {"data":[{"id":FREE if exists else "unsupported/other",
                     "pricing":{"prompt":price,"completion":"0"}}]}

def candidate():
    c=deepcopy(host_test_baseline())
    c["beats"][0]["caption"]="Can we rearrange these rows while preserving the same small squares?"
    c["beats"][1]["caption"]="Follow each of the original squares and predict their new group positions."
    return c

def answer(*,c=None,model="nvidia/some-genuine-model:free",cost=0):
    return {"id":"gen-very-real-but-test-fixture","model":model,
            "usage":{"cost":cost,"prompt_tokens":50,"completion_tokens":40},
            "choices":[{"finish_reason":"stop",
                        "message":{"content":json.dumps(c or candidate())}}]}

def test_prereg_free_contract_and_frozen_array_source():
    p=registered()
    assert p["provider"]["model"]=="openrouter/free"
    assert p["provider"]["max_inference_posts"]==1
    assert p["provider"]["max_retries"]==0
    assert p["provider"]["no_paid_models"] is True
    assert p["acceptance"]["human_pedagogy"]=="UNRATED"
    assert p["acceptance"]["production"]=="BLOCKED"

@pytest.mark.parametrize("price",["0","0.0",0])
def test_current_public_router_zero_price_must_be_confirmed(price):
    calls=[]
    x=safe_get_catalog(sender=sender_of(catalog(price),calls))
    assert x["free_input_price_verified"]
    assert len(calls)==1 and calls[0].get_method()=="GET"

@pytest.mark.parametrize("bad",["0.00001","0.1","nan",None,True])
def test_nonzero_or_missing_catalog_price_is_denied(bad):
    with pytest.raises(Denied,match="FREE_ROUTER_PRICE_NOT_CONFIRMED_ZERO"):
        safe_get_catalog(sender=sender_of(catalog(bad),[]))

def test_missing_catalog_identity_fails_closed():
    with pytest.raises(Denied,match="FREE_ROUTER_NOT_FOUND"):
        safe_get_catalog(sender=sender_of(catalog(exists=False),[]))

def test_post_is_free_router_not_paid_with_strict_json_and_no_silent_fallback():
    wire=json.loads(payload())
    assert wire["model"]==FREE
    assert wire["max_tokens"]==3500 and wire["stream"] is False
    assert wire["response_format"]["json_schema"]["strict"] is True
    assert "provider" not in wire
    calls=[]
    request_once("f"*24,payload(),send=sender_of(answer(),calls))
    assert len(calls)==1 and calls[0].get_method()=="POST"
    assert calls[0].full_url=="https://openrouter.ai/api/v1/chat/completions"

def test_missing_key_never_sends_request(tmp_path):
    r=run(tmp_path/"missing",key="")
    assert r["provider_post_attempts"]==0
    assert r["outcome"]=="BLOCKED_MISSING_OPENROUTER_KEY"

def test_refuse_nonfree_catalog_before_post(tmp_path):
    calls=[]
    r=run(tmp_path/"no-price",key="f"*24,
          catalog_sender=sender_of(catalog("0.5"),calls),
          post_sender=sender_of(answer(),calls),do_native=False)
    assert r["provider_post_attempts"]==0 and len(calls)==1
    assert r["outcome"]=="BLOCKED_ZERO_PRICE_PUBLIC_CATALOG_NOT_VERIFIED"

def test_fake_sender_candidate_valid_but_never_real_model_authorship(tmp_path):
    calls=[]
    r=run(tmp_path/"simulated",key="f"*24,
          catalog_sender=sender_of(catalog(),calls),
          post_sender=sender_of(answer(),calls),do_native=False)
    assert r["provider_post_attempts"]==1
    assert r["candidate_origin"]=="SIMULATED_TEST_SENDER"
    assert r["model_authored_storyboard"]=="NOT_ESTABLISHED_TEST_ONLY"
    assert r["outcome"]=="CANDIDATE_ACCEPTED_BUT_NATIVE_NOT_RUN"
    assert not list((tmp_path/"simulated").glob("**/*.mp4"))
    assert len(calls)==2

@pytest.mark.parametrize("bad",[
    {"model":"paid/provider","cost":0,"changes":True},
    {"model":"fake/free:free","cost":0.002,"changes":True},
    {"model":"fake/free:free","cost":0,"changes":False},
])
def test_paid_model_cost_and_unchanged_host_baseline_cannot_get_credit(tmp_path,bad):
    c=candidate() if bad["changes"] else host_test_baseline()
    r=run(tmp_path/("bad-"+str(bad["cost"])+("-changed" if bad["changes"] else "-same")),
          key="f"*24,catalog_sender=sender_of(catalog(),[]),
          post_sender=sender_of(answer(c=c,model=bad["model"],cost=bad["cost"]),[]),
          do_native=False)
    assert r["outcome"]=="PROVIDER_RESPONSE_REJECTED_BY_HOST"
    assert r["model_authored_storyboard"]=="NOT_ESTABLISHED"

def test_integrity_rejects_host_forgery(tmp_path):
    c=candidate();c["host_ledger_sha256"]="0"*64
    r=run(tmp_path/"forged",key="f"*24,
          catalog_sender=sender_of(catalog(),[]),
          post_sender=sender_of(answer(c=c),[]),do_native=False)
    assert r["outcome"]=="PROVIDER_RESPONSE_REJECTED_BY_HOST"

def test_no_automatic_retry_no_production_or_human_pass():
    from pathlib import Path
    src=(Path(__file__).resolve().parents[2]/
         "scripts/run_v3_91_single_free_ai_pilot.py").read_text()
    assert src.count("request_once(key,raw,send=post_sender)")==1
    assert "OPENROUTER_API_KEY" in src
    assert "REAL_PROVIDER_RESPONSE" in src
    assert "build_comparison(" in src
    assert "UNRATED" in src and "BLOCKED" in src
