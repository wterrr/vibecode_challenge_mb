"""V3-65 hostile GET-only tests; fake HTTP responses never touch a provider."""
from __future__ import annotations
import json
from urllib.error import HTTPError
import pytest
from learnflow_v3.openrouter_metadata_audit import (
  CATALOG_URL,KEY_URL,MODEL,MAX_KEY_BYTES,MAX_CATALOG_BYTES,
  NeverFollowRedirect,_get,probe_model_endpoints,probe_current_key
)
from scripts.run_v3_65_provider_get_diagnostics import diagnostic,freeze_check,Blocked

FAKE_SECRET="DO_NOT_LOG_SECRET_KEY_VALUE_65"
PRIVATE="PRIVATE_ACCOUNT_IDENTIFIER_SHOULD_NEVER_BE_PERSISTED"
class Response:
    status=200
    def __init__(self,obj):self.raw=json.dumps(obj).encode()
    def __enter__(self):return self
    def __exit__(self,*a):return None
    def read(self,n):return self.raw[:n]
def catalog(providers=None):
    if providers is None:
        providers=[{"provider_name":"OpenAI","supported_parameters":[
          "response_format","structured_outputs","max_tokens"]}]
    return {"data":{"id":MODEL,"endpoints":providers,"sensitive":"DO_NOT_PERSIST"}}
def key_info(remaining=5):
    return {"data":{"is_management_key":False,"is_free_tier":False,
      "limit":100,"limit_remaining":remaining,"expires_at":"2099-01-01T00:00:00Z",
      "creator_user_id":PRIVATE,"label":FAKE_SECRET,"workspace_id":PRIVATE}}
def sender(*,catalog_status=200,key_status=200,providers=None,
           remaining=5,key_override=None):
    observed=[]
    def send(req,timeout):
        assert req.get_method()=="GET"
        assert req.data is None
        assert req.full_url in (CATALOG_URL,KEY_URL)
        assert timeout<=12
        observed.append(req.full_url)
        if req.full_url==CATALOG_URL:
            assert req.headers.get("Authorization") is None
            if catalog_status!=200:
                raise HTTPError(req.full_url,catalog_status,PRIVATE,{},None)
            return Response(catalog(providers))
        assert req.headers["Authorization"]=="Bearer "+FAKE_SECRET
        if key_status!=200:
            raise HTTPError(req.full_url,key_status,PRIVATE,{},None)
        return Response(key_override if key_override is not None else key_info(remaining))
    return send,observed

def test_prereg_frozen_instead_of_redispatching_historical_trial():
    r=freeze_check()
    assert r["parent_pr"]==100
    assert r["historical_live_run"]==38502942783
    assert r["historical_artifact_id"]==11866413693
    assert r["max_network_gets"]==2 and r["max_provider_inference_posts"]==0
    assert all(q["method"]=="GET" for q in r["queries"])

def test_successful_metadata_two_gets_do_not_explain_historical_HTTPError():
    call,seen=sender()
    output=diagnostic(key=FAKE_SECRET,sender=call)
    assert seen==[CATALOG_URL,KEY_URL]
    assert output["get_attempts"]==2 and output["inference_posts"]==0
    assert output["decision"]=="GET_METADATA_AUTHENTICATED_AND_CATALOG_COMPATIBILITY_ADVISORY_ONLY"
    assert output["historical_post_exception"]=="HTTPError"
    assert output["historical_post_http_code"]=="NOT_CAPTURED_CANNOT_RECOVER"
    assert output["historical_root_cause"]=="UNDETERMINED"
    assert output["historical_http_cause_proven"] is False
    assert output["model_exact_routing_proven"] is False
    assert output["key_metadata"]["key_limit_remaining_category"]=="POSITIVE"
    assert output["key_metadata"]["funded_account_credits_proven"] is False
    assert output["public_endpoint_catalog"]["strict_json_schema_guaranteed"] is False
    text=json.dumps(output)
    assert FAKE_SECRET not in text and PRIVATE not in text
    assert "5.0" not in text and "label" not in output["key_metadata"]
    assert output["production"]=="BLOCKED"

def test_missing_secret_gets_public_catalog_once_only():
    call,seen=sender()
    result=diagnostic(key=None,sender=call)
    assert seen==[CATALOG_URL]
    assert result["decision"]=="INCONCLUSIVE_NO_CREDENTIAL"
    assert result["get_attempts"]==1

@pytest.mark.parametrize("key_status,decision",[
    (401,"KEY_AUTH_FAILURE_METADATA_ONLY"),
    (402,"GET_KEY_UNUSABLE_OR_UNVERIFIED"),
    (403,"GET_KEY_UNUSABLE_OR_UNVERIFIED"),
    (429,"GET_KEY_UNUSABLE_OR_UNVERIFIED"),
    (500,"GET_KEY_UNUSABLE_OR_UNVERIFIED")
])
def test_key_status_fail_closed_with_no_error_body(key_status,decision):
    call,seen=sender(key_status=key_status)
    r=diagnostic(key=FAKE_SECRET,sender=call)
    assert seen==[CATALOG_URL,KEY_URL]
    assert r["decision"]==decision
    assert r["key_metadata"]["http_status"]=="HTTP_"+str(key_status)
    assert PRIVATE not in json.dumps(r)
    assert r["inference_posts"]==0

@pytest.mark.parametrize("catalog_status", [404,429,500])
def test_public_catalog_failure_inconclusive(catalog_status):
    call,seen=sender(catalog_status=catalog_status)
    r=diagnostic(key=FAKE_SECRET,sender=call)
    assert r["decision"]=="PUBLIC_MODEL_ENDPOINTS_NOT_VERIFIED"
    assert seen==[CATALOG_URL,KEY_URL]
    assert r["historical_root_cause"]=="UNDETERMINED"

def test_public_openai_endpoint_not_advertised_cannot_certify_exact_route():
    call,_=sender(providers=[{"provider_name":"Azure",
      "supported_parameters":["response_format","structured_outputs","max_tokens"]}])
    r=diagnostic(key=FAKE_SECRET,sender=call)
    assert r["decision"]=="PUBLIC_OPENAI_STRICT_WIRE_MATCH_NOT_ESTABLISHED"
    assert r["public_endpoint_catalog"]["OpenAI_advertises_structured_json"] is False

def test_only_parameter_names_not_actual_json_schema_strict_guarantee():
    call,_=sender(providers=[{"provider_name":"OpenAI",
       "supported_parameters":["response_format","structured_outputs"]}])
    r=diagnostic(key=FAKE_SECRET,sender=call)
    assert r["decision"]=="PUBLIC_OPENAI_STRICT_WIRE_MATCH_NOT_ESTABLISHED"
    assert r["public_endpoint_catalog"]["strict_json_schema_guaranteed"] is False

def test_zero_key_limit_not_assumed_zero_account_credit():
    call,_=sender(remaining=0)
    r=diagnostic(key=FAKE_SECRET,sender=call)
    assert r["key_metadata"]["key_limit_remaining_category"]=="ZERO_OR_NEGATIVE"
    assert r["key_metadata"]["funded_account_credits_proven"] is False
    assert r["historical_root_cause"]=="UNDETERMINED"

def test_unlimited_key_limit_not_assumed_positive_credit():
    call,_=sender(key_override={**key_info(),"data":{
       **key_info()["data"],"limit":None,"limit_remaining":None}})
    r=diagnostic(key=FAKE_SECRET,sender=call)
    assert r["key_metadata"]["key_limit_remaining_category"]=="NO_EXPLICIT_KEY_CAP_REPORTED"
    assert r["key_metadata"]["funded_account_credits_proven"] is False

def test_management_key_never_considered_inference_entitlement():
    call,_=sender(key_override={"data":{
       **key_info()["data"],"is_management_key":True}})
    r=diagnostic(key=FAKE_SECRET,sender=call)
    assert r["key_metadata"]["type"]=="MANAGEMENT"
    assert r["decision"]=="GET_KEY_UNUSABLE_OR_UNVERIFIED"

def test_raw_private_body_never_written_even_when_successful():
    call,_=sender()
    a=diagnostic(key=FAKE_SECRET,sender=call)
    encoded=json.dumps(a)
    for unwanted in (FAKE_SECRET,PRIVATE,"creator_user_id","workspace_id",
        '"limit_remaining": 5',"byok_usage","billing_email"):
        assert unwanted not in encoded

def test_legacy_get_rejects_unallowlisted_url_and_credentials_route():
    from learnflow_v3.openrouter_metadata_audit import MetadataInvalid
    with pytest.raises(MetadataInvalid):
        _get("https://openrouter.ai/api/v1/credits",bearer=FAKE_SECRET,max_bytes=100)
    with pytest.raises(MetadataInvalid):
        _get(CATALOG_URL,bearer=FAKE_SECRET,max_bytes=100)
    with pytest.raises(MetadataInvalid):
        _get(KEY_URL,bearer=None,max_bytes=100)

def test_redirect_not_followed_to_leak_token():
    no=NeverFollowRedirect()
    assert no.redirect_request(None,None,302,"Found",{},
        "https://evil.example/steal") is None


def test_direct_script_invocation_imports_repo_without_network():
    """Replicates GitHub's python scripts/... entrypoint, not pytest import mode."""
    from pathlib import Path
    import sys,subprocess
    root=Path(__file__).resolve().parents[2]
    cmd=[sys.executable,str(root/"scripts/run_v3_65_provider_get_diagnostics.py"),
         "--help"]
    result=subprocess.run(cmd,cwd=root,capture_output=True,text=True,
                          timeout=20,check=False)
    assert result.returncode==0, result.stderr[-300:]
    assert "--output" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr
