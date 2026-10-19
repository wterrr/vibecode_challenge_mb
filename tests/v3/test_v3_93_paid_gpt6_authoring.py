"""V3-93 hostile offline paid GPT-6 Luna source/price/attribution gates.
All fake provider responses are explicitly NOT genuine GPT authorship.
"""
from __future__ import annotations
from copy import deepcopy
import io,json,pytest
from decimal import Decimal
from learnflow_v3.v392_compact_authoring import pilot_case
from scripts.run_v3_93_paid_gpt6_authoring import (
    registered,schema,data_payload,preflight_model_and_key,run,MODEL,
    MAX_USD,Blocked,TOKENS,safe_finish,money
)
class Response(io.BytesIO):
    status=200
def sender(obj,calls):
    def call(req,timeout=None):
        calls.append(req)
        return Response(json.dumps(obj).encode())
    return call
def cat(price="0.0000001",out="0.0000005",cap=True):
    return {"data":[{"id":MODEL,"pricing":{"prompt":price,"completion":out},
             "supported_parameters":(["response_format","max_completion_tokens"] if cap else [])}]}
def keymeta(remain=1):
    return {"data":{"limit_remaining":remain,"is_management_key":False,
            "include_byok_in_limit":False,"is_management_key":False}}
def answer(*,content=None,finish="stop",actual=MODEL,cost=".005",usage=None):
    return {"id":"gen_paid_gpt_mock_no_real_provider","model":actual,
      "usage":usage if usage is not None else
         {"prompt_tokens":450,"completion_tokens":2044,
          "total_tokens":2494,"cost":cost},
      "choices":[{"finish_reason":finish,"message":{"content":json.dumps(content or pilot_case())}}]}
KEY="k"*30
def trial(tmp_path,name,reply=None,catdata=None,keydata=None,native=False):
    calls=[]
    r=run(tmp_path/name,key=KEY,
          catalog_sender=sender(catdata or cat(),calls),
          key_sender=sender(keydata or keymeta(),calls),
          post_sender=sender(reply or answer(),calls),native=native)
    return r,calls

def test_exact_prereg_not_free_and_no_retry():
    p=registered()
    assert p["provider"]["model"]=="openai/gpt-6-luna"
    assert p["provider"]["max_completion_tokens"]==16000
    assert p["provider"]["reasoning_effort"]=="low"
    assert p["provider"]["max_paid_http_posts"]==1
    assert p["provider"]["allow_fallbacks"] is False
    assert p["provider"]["cost_token_ceiling_usd"]=="0.01"

def test_strict_compact_schema_and_host_validator():
    s=schema()
    assert s["additionalProperties"] is False
    assert set(s["properties"])==set(s["required"])
    assert s["properties"]["beats"]["items"]["additionalProperties"] is False

def test_paid_request_has_correct_provider_pin_tokens_reasoning_schema():
    d,raw=data_payload()
    assert d["model"]==MODEL and d["max_completion_tokens"]==TOKENS
    assert d["reasoning_effort"]=="low"
    assert "max_tokens" not in d and "temperature" not in d
    assert d["response_format"]["json_schema"]["strict"] is True
    assert d["provider"]=={"order":["OpenAI"],"allow_fallbacks":False,"require_parameters":True}
    assert "models" not in d
    assert len(raw)<=7000

def test_current_price_and_key_gets_must_be_read_only_and_bounded():
    calls=[]
    p=preflight_model_and_key(key=KEY,catalog_sender=sender(cat(),calls),
                              key_sender=sender(keymeta(),calls))
    assert p["model_catalog"]=="HTTP_200_MATCH" and p["key_metadata"]=="AUTHENTICATED"
    assert Decimal(p["pessimistic_one_post_cost_ceiling_usd"])<MAX_USD
    assert all(q.get_method()=="GET" for q in calls)
    assert len(calls)==2

@pytest.mark.parametrize("catalog",[
    cat(price="0.0000002"),cat(out="0.000001"),cat(price="0"),
    cat(cap=False),cat(price="NaN")])
def test_price_drift_or_no_schema_cap_blocks_before_paid_post(catalog,tmp_path):
    r,calls=trial(tmp_path,"unsafe_"+str(len(json.dumps(catalog))),catdata=catalog)
    assert r["result"]=="DENY_PAID_REQUEST_PREFLIGHT"
    assert r["provider_post_attempts"]==0
    assert len(calls)==1

@pytest.mark.parametrize("meta",[
    {"data":{"limit_remaining":0,"is_management_key":False}},
    {"data":{"limit_remaining":.0001,"is_management_key":False}},
    {"data":{"limit_remaining":1,"is_management_key":True}},
    {"data":{"limit_remaining":1}},
    {"data":{}}
])
def test_readonly_key_must_be_admissible_or_no_post(meta,tmp_path):
    calls=[]
    p=tmp_path/("k"+str(len(list(tmp_path.iterdir()))))
    r=run(p,key=KEY,catalog_sender=sender(cat(),calls),
          key_sender=sender(meta,calls),post_sender=sender(answer(),calls),native=False)
    assert r["result"]=="DENY_PAID_REQUEST_PREFLIGHT"
    assert r["provider_post_attempts"]==0 and len(calls)==2

def test_missing_key_blocks_paid_post(tmp_path):
    r=run(tmp_path/"none",key="")
    assert r["result"]=="DENY_PAID_REQUEST_PREFLIGHT" and r["provider_post_attempts"]==0

def test_fake_good_json_never_counts_as_real_paid_gpt_and_does_not_render(tmp_path):
    r,calls=trial(tmp_path,"good")
    assert r["provider_post_attempts"]==1 and len(calls)==3
    assert r["candidate_origin"]=="TEST_MOCK_NOT_GENUINE"
    assert r["model_storyboard"]=="TEST_ONLY"
    assert r["result"]=="ACCEPTED_MODEL_BUT_NATIVE_NOT_RUN"
    assert "creative_witness" in r
    assert r["finish_reason"]=="stop"
    assert not list((tmp_path/"good").glob("**/*.mp4"))
    assert [c.get_method() for c in calls]==["GET","GET","POST"]

@pytest.mark.parametrize("finish",["length","content_filter",None])
def test_nonstop_always_captures_telemetry_before_safe_rejection(tmp_path,finish):
    name="finish_"+str(finish)
    r,c=trial(tmp_path,name,answer(finish=finish))
    assert r["provider_post_attempts"]==1 and r["retry_count"]==0
    assert r["actual_model"]==MODEL
    assert r["finish_reason"]==safe_finish(finish)
    assert r["usage"]["completion_tokens"]==2044
    assert r["result"]=="MODEL_STORYBOARD_REJECTED_NO_RETRY"
    assert r["candidate_origin"]=="NO_ADMITTED_PROVIDER_STORYBOARD"

@pytest.mark.parametrize("bad",[
    answer(actual="openai/other-model"),
    answer(content={"hello":"not-a-storyboard"}),
    answer(cost=".10"),
])
def test_invalid_model_story_or_excessive_billing_must_reject(bad,tmp_path):
    name="invalid"+str(len(list(tmp_path.iterdir())))
    r,_=trial(tmp_path,name,bad)
    assert r["result"]=="MODEL_STORYBOARD_REJECTED_NO_RETRY"

def test_exactly_one_post_site_never_fake_human_quality():
    from pathlib import Path
    p=(Path(__file__).resolve().parents[2]/"scripts/run_v3_93_paid_gpt6_authoring.py").read_text()
    assert p.count("result=post_once(key=key,raw=raw,sender=post_sender)")==1
    assert p.count("build_comparison(")==1
    assert "UNRATED" in p and "BLOCKED" in p
