"""V3-67: strict source hashing, documented wire and *deny-by-default* USD key gate.

No network or real credential is accessed. All metadata in these tests is
TEST_ONLY and cannot be counted as provider attestations or paid authorization.
"""
from __future__ import annotations
import copy,json
from decimal import Decimal
import pytest
from learnflow_v3.v367_corrected_wire_budget import (
    MODEL,MAX_USD,FROZEN_V364_SHA,BudgetBlocked,original_payload,
    corrected_request,key_amount,policy_for_key,budget_preflight,registered_report
)
from scripts.run_v3_64_one_shot_real_model import request_payload
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/"benchmarks/learnflowbench/v3/v3_67_corrected_provider_budget_preregister.json"
PRIVATE="SECRET_key_and_workspace_NO_LEAK"
def fixture(*,limit="0.02",remaining="0.02",reset=None,include=True,management=False):
    return {"data":{
        "limit":limit,"limit_remaining":remaining,"limit_reset":reset,
        "include_byok_in_limit":include,"is_management_key":management,
        "creator_user_id":PRIVATE,"label":PRIVATE,"workspace_id":PRIVATE,
        "usage":100,"byok_usage":100,"other_sensitive":PRIVATE}}

def test_first_child_prereg_and_frozen_host_history():
    r=registered_report(REG)
    assert r["checkpoint"]=="V3-67"
    assert r["original_v364_request_sha256"]==FROZEN_V364_SHA
    assert r["new_model_inference_posts"]==0
    assert r["new_provider_gets"]==0
    assert r["can_authorize_paid_POST"] is False
    assert r["current_key_budget_attestation"]["policy_result"]=="DENY_NO_AUTHENTICATED_KEY_SNAPSHOT"
    assert r["production"]=="BLOCKED"

def test_original_request_is_bitwise_unchanged_and_new_diff_one_field():
    old,raw=original_payload()
    previous,prior_bytes=request_payload()
    assert prior_bytes==raw and previous==old
    changed,changed_raw=corrected_request()
    assert changed_raw!=raw
    assert set(changed)==set(old)
    assert old["provider"]=={
        "order":["OpenAI"],"allow_fallback":False,"require_parameters":True}
    assert changed["provider"]=={
        "order":["OpenAI"],"require_parameters":True,"allow_fallbacks":False}
    assert "allow_fallback" not in changed["provider"]
    assert {k:v for k,v in old.items() if k!="provider"}=={
        k:v for k,v in changed.items() if k!="provider"}
    assert changed["response_format"]==old["response_format"]
    assert changed["messages"]==old["messages"]
    assert changed["max_tokens"]==2100
    assert changed["model"]==MODEL
    assert "temperature" not in changed and "models" not in changed
    assert len(changed_raw)<14000
    assert json.loads(changed_raw)==changed

def test_provider_fixed_no_fallback_new_or_old_shapes_and_json_schema():
    changed,_=corrected_request()
    assert changed["provider"]["allow_fallbacks"] is False
    assert changed["provider"]["order"]==["OpenAI"]
    assert changed["provider"]["require_parameters"] is True
    assert changed["response_format"]["type"]=="json_schema"
    assert changed["response_format"]["json_schema"]["strict"] is True
    assert changed["stream"] is False
    assert changed.get("retries",0)==0

@pytest.mark.parametrize("field,value",[
    ("limit",None),("limit_remaining",None),
    ("limit",""),("limit_remaining",""),
    ("limit","NaN"),("limit_remaining","NaN"),
    ("limit","Infinity"),("limit_remaining","Infinity"),
    ("limit",True),("limit_remaining",False),
    ("limit",-1),("limit_remaining",-0.01),
    ("limit",[]),("limit_remaining",{}),
])
def test_malformed_cap_or_remaining_denied(field,value):
    d=fixture();d["data"][field]=value
    x=policy_for_key(d,trusted_authenticated_get=True)
    assert x["policy_result"]=="DENY_INVALID_PROVIDER_KEY_CAP"
    assert x["live_post_permitted"] is False
    assert PRIVATE not in json.dumps(x)

@pytest.mark.parametrize("reset",["daily","weekly","monthly","lifetime","",False,0])
def test_resetting_or_unverified_provider_limit_denied(reset):
    x=policy_for_key(fixture(reset=reset),trusted_authenticated_get=True)
    assert x["policy_result"]=="DENY_RESETTING_OR_UNVERIFIED_KEY_LIMIT"

@pytest.mark.parametrize("include", [False,None,0,"true",1])
def test_byok_outside_provider_cap_denied(include):
    result=policy_for_key(fixture(include=include),trusted_authenticated_get=True)
    assert result["policy_result"]=="DENY_BYOK_SPEND_OUTSIDE_CAP"

@pytest.mark.parametrize("management", [True,None,1,"false"])
def test_management_or_unknown_key_is_not_inference_cap(management):
    x=policy_for_key(fixture(management=management),trusted_authenticated_get=True)
    assert x["policy_result"]=="DENY_MANAGEMENT_OR_UNKNOWN_KEY_TYPE"

@pytest.mark.parametrize("limit,remaining,reason", [
    ("0.020001","0.020001","DENY_KEY_CAP_EXCEEDS_FROZEN_USD_BUDGET"),
    ("100","99","DENY_KEY_CAP_EXCEEDS_FROZEN_USD_BUDGET"),
    ("0","0","DENY_KEY_CAP_EXCEEDS_FROZEN_USD_BUDGET"),
    ("0.02","0","DENY_NO_REMAINING_KEY_ALLOWANCE"),
    ("0.02","0.021","DENY_KEY_REMAINING_EXCEEDS_CAP"),
])
def test_cap_over_budget_empty_or_inconsistent_denied(limit,remaining,reason):
    r=policy_for_key(fixture(limit=limit,remaining=remaining),
         trusted_authenticated_get=True)
    assert r["policy_result"]==reason

def test_unconfigured_shared_or_misproven_key_denied():
    assert policy_for_key(None)["policy_result"]=="DENY_NO_AUTHENTICATED_KEY_SNAPSHOT"
    assert policy_for_key([],trusted_authenticated_get=True)["policy_result"]=="DENY_INVALID_KEY_METADATA"
    assert policy_for_key(fixture())["policy_result"]=="DENY_UNVERIFIED_KEY_PROVENANCE"
    assert policy_for_key(fixture(),trusted_authenticated_get="yes")["policy_result"]=="DENY_UNVERIFIED_KEY_PROVENANCE"
    for key in ("data","is_management_key","include_byok_in_limit","limit","limit_remaining","limit_reset"):
        broken=fixture()
        if key=="data": del broken["data"]
        else: del broken["data"][key]
        result=policy_for_key(broken,trusted_authenticated_get=True)
        assert result["policy_result"].startswith("DENY_")

def test_test_only_provider_cap_candidate_can_pass_math_but_cannot_authorize_post():
    d=fixture(limit="0.02",remaining="0.019",reset=None)
    x=policy_for_key(d,trusted_authenticated_get=True)
    assert x["policy_result"]=="KEY_CAP_CONDITIONS_SATISFIED_ONLY"
    assert x["live_post_permitted"] is False
    assert x["is_genuine_provider_cap_proof"] is False
    assert x["actual_charge_guaranteed_by_this_software"] is False
    assert x["approval"]=="SEPARATE_PREREG_AND_USER_AUTH_REQUIRED"
    assert PRIVATE not in json.dumps(x)
    preflight=budget_preflight(d,trusted_authenticated_get=True)
    assert preflight["can_authorize_paid_POST"] is False
    assert preflight["can_claim_provider_cap_verified_in_v367"] is False
    assert preflight["new_model_inference_posts"]==0
    assert preflight["real_hard_limit_requires_provider_configuration"] is True
    assert preflight["token_ceiling_is_usd_hard_cap"] is False

def test_bare_positive_key_cap_from_v365_is_not_spend_cap_evidence():
    # V3-65 only reported POSITIVE key-specific remaining allowance,
    # NOT actual <=2-cent lifetime cap, BYOK protection or usable credits.
    d={"data":{"limit_remaining":"positive"}}
    r=policy_for_key(d,trusted_authenticated_get=True)
    assert r["policy_result"].startswith("DENY_")
    assert r["live_post_permitted"] is False

def test_frozen_002_usd_cap_exact_decimal_and_caller_does_not_see_key_secret():
    assert MAX_USD==Decimal("0.02")
    assert key_amount("0.0200","LIMIT")==Decimal("0.0200")
    r=budget_preflight(fixture(limit="0.02",remaining="0.01"),
         trusted_authenticated_get=True)
    serialized=json.dumps(r)
    assert "0.02" in serialized
    assert PRIVATE not in serialized
    assert "label" not in serialized and "creator_user_id" not in serialized
    assert r["usd_budget_frozen"]=="0.02"
    assert r["human_pedagogical_quality"]=="UNRATED"
    assert r["learning_gain"]=="NOT_MEASURED"
    assert r["model_authorship"]=="NOT_TESTED"

def test_no_live_spend_can_be_claimed_from_synthetic_metadata():
    for trusted in (False,True):
        for key in (None,fixture(),fixture(limit="100",remaining="99")):
            r=budget_preflight(key,trusted_authenticated_get=trusted)
            assert r["can_authorize_paid_POST"] is False
            assert r["new_provider_gets"]==r["new_model_inference_posts"]==0
            assert r["new_management_key_actions"]==0
            assert r["production"]=="BLOCKED"

def test_source_provenance_local_only_and_does_not_modify_real_endpoint():
    corrected,_=corrected_request()
    assert "Authorization" not in json.dumps(corrected)
    assert corrected["provider"]["allow_fallbacks"] is False
    assert "OPENROUTER_API_KEY" not in json.dumps(corrected)
    assert not any("password" in k.lower() for k in corrected)
