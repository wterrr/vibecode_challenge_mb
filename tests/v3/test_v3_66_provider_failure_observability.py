"""V3-66 0-network regression: sanitized prospective HTTP taxonomy and static wire."""
import io
import json
from urllib.error import HTTPError,URLError
import pytest
from learnflow_v3.v366_provider_failure_observability import (
    MODEL,KNOWN_CODES,ContractViolation,NO_ERROR_CAUSE,
    sanitize_code,incident,frozen_compatibility,diagnostic_from_frozen,
    sanitized_report,safe_label)
from scripts.run_v3_64_one_shot_real_model import request_payload

SECRET="sk-private-PASSWORD-HERE-NEVER-LOG"
ACCOUNT="private-account-id-NEVER-LOG"
REQ=b'{"model":"openai/gpt-6-luna","messages":[]}'
def error(code,reason=SECRET,fp=None):
    return HTTPError("https://private.example/"+ACCOUNT,code,reason,
                     {"Authorization":"Bearer "+SECRET,"X-Private":ACCOUNT},
                     fp if fp is not None else io.BytesIO((SECRET+ACCOUNT).encode()))

@pytest.mark.parametrize("status",[
    400,401,402,403,404,408,409,413,422,429,500,502,503,504,524,529
])
def test_allowlisted_http_error_codes_are_captured_without_bodies(status):
    ex=error(status)
    x=incident(ex,request_bytes=REQ,request_attempts=1)
    assert x["http_status_observed"]==f"HTTP_{status}"
    assert x["historical_v364_http_status"]=="NOT_CAPTURED_CANNOT_RECOVER"
    assert x["exact_error_reason"]=="UNDETERMINED_FROM_STATUS_ONLY"
    assert x["retry"]==0 and x["fallback"] is False
    assert x["inference_requests_executed_by_this_module"]==0
    dumped=json.dumps(x)
    assert SECRET not in dumped and ACCOUNT not in dumped
    assert "private.example" not in dumped
    assert "Authorization" not in dumped
    assert x["provider_response_body_recorded"] is False
    assert x["raw_exception_recorded"] is False

@pytest.mark.parametrize("status,expected",[
    (302,"REDIRECT_BLOCKED"),(307,"REDIRECT_BLOCKED"),
    (399,"REDIRECT_BLOCKED"),(418,"HTTP_OTHER"),
    (599,"HTTP_OTHER"),(700,"HTTP_OTHER"),
    (-1,"HTTP_OTHER"),("402","HTTP_UNKNOWN"),
    (True,"HTTP_UNKNOWN"),
])
def test_untrusted_status_not_misclassified(status,expected):
    assert sanitize_code(error(status))==expected

def test_malicious_error_body_never_read_or_reflected():
    class Poison:
        def read(self,*args):raise AssertionError("MUST_NOT_READ_PROVIDER_BODY")
        def __str__(self):raise AssertionError("MUST_NOT_SERIALIZE_PROVIDER_FP")
    x=incident(error(429,reason=SECRET,fp=Poison()),
               request_bytes=REQ,request_attempts=1)
    assert x["http_status_observed"]=="HTTP_429"
    assert SECRET not in json.dumps(x)

@pytest.mark.parametrize("ex,expected",[
    (URLError(SECRET+" private host"),"TRANSPORT_UNAVAILABLE"),
    (TimeoutError(SECRET),"TRANSPORT_UNAVAILABLE"),
    (ConnectionRefusedError(SECRET),"TRANSPORT_UNAVAILABLE"),
    (ValueError(SECRET),"UNKNOWN_EXCEPTION_TYPE"),
    (RuntimeError(SECRET),"UNKNOWN_EXCEPTION_TYPE"),
])
def test_transport_and_unknown_exception_reason_never_logged(ex,expected):
    result=incident(ex,request_bytes=REQ,request_attempts=1)
    assert result["http_status_observed"]==expected
    assert SECRET not in json.dumps(result)

def test_success_and_failure_require_exactly_one_previous_attempt():
    ok=incident(None,request_bytes=REQ,request_attempts=1)
    assert ok["http_status_observed"]=="HTTP_200_OBSERVED"
    for n in (-1,0,2,True,1.0):
        with pytest.raises(ContractViolation,match="V366_"):
            incident(error(400),request_bytes=REQ,request_attempts=n)
    with pytest.raises(ContractViolation,match="V366_SUCCESS_WITHOUT_ATTEMPT"):
        incident(None,request_bytes=REQ,request_attempts=0)

def test_reject_wrong_model_bad_payload_and_no_attempt():
    for model in ("fake","openai/gpt-5.2",None,MODEL.upper()):
        with pytest.raises(ContractViolation,match="V366_UNREGISTERED_MODEL"):
            incident(error(403),request_bytes=REQ,request_attempts=1,model=model)
    for bad in (b"",b"a"*14001,"string",None):
        with pytest.raises(ContractViolation,match="V366_BAD_FROZEN_REQUEST_BYTES"):
            incident(error(403),request_bytes=bad,request_attempts=1)
    with pytest.raises(ContractViolation,match="V366_FAILURE_WITHOUT_ATTEMPT"):
        incident(error(403),request_bytes=REQ,request_attempts=0)

def test_original_v364_provider_shape_reuses_unmodified_frozen_request():
    payload,raw=request_payload()
    assert payload["provider"]["allow_fallback"] is False
    assert "allow_fallbacks" not in payload["provider"]
    x=frozen_compatibility(payload)
    assert x["model"]==MODEL
    assert "allow_fallback" in x["provider_options_observed"]
    assert "allow_fallbacks" not in x["provider_options_observed"]
    assert x["historical_HTTP_error_code"]=="NOT_CAPTURED_CANNOT_RECOVER"
    assert x["historical_root_cause"]==NO_ERROR_CAUSE
    assert x["hard_dollar_budget_enforced"] is False
    assert x["provider_api_requests_by_analysis"]==0
    assert x["source_request_sha256"]=="728e32b0bea658a82054184efee840ddb72957851f0ba87d21042d96d4134c0f"
    codes={f["code"] for f in x["findings"]}
    assert "LEGACY_PROVIDER_ALLOW_FALLBACK_FIELD" in codes
    assert "TOKEN_LIMIT_NOT_DOLLAR_CAP" in codes
    assert all(f["proven_caused_v364_error"] is False for f in x["findings"])
    assert x==diagnostic_from_frozen()

def test_future_corrected_request_must_not_be_relabeled_as_v364_original():
    payload,_=request_payload()
    payload["provider"]["allow_fallbacks"]=payload["provider"].pop("allow_fallback")
    with pytest.raises(ContractViolation,match="V366_HISTORICAL_PROVIDER_SHAPE_CHANGED"):
        frozen_compatibility(payload)
    payload["provider"]["allow_fallback"]=False
    with pytest.raises(ContractViolation,match="V366_HISTORICAL_PROVIDER_SHAPE_CHANGED"):
        frozen_compatibility(payload)

@pytest.mark.parametrize("mutation,code",[
    (("model","fake"),"FROZEN_MODEL_MISMATCH"),
    (("max_tokens",2200),"FROZEN_STRUCTURED_WIRE_CHANGED"),
    (("response_format",{"type":"text"}),"FROZEN_STRUCTURED_WIRE_CHANGED"),
    (("provider",{"order":["other"]}),"HISTORICAL_PROVIDER_SHAPE_CHANGED"),
])
def test_mutated_frozen_request_drift_is_rejected(mutation,code):
    data,_=request_payload()
    data[mutation[0]]=mutation[1]
    with pytest.raises(ContractViolation,match="V366_"+code):
        frozen_compatibility(data)

def test_current_catalog_is_advisory_not_provider_account_certification():
    data,_=request_payload()
    fake={"public_endpoint_catalog":{
        "http_status":"HTTP_200","matched_model_id":True,
        "OpenAI_advertises_structured_json":True,
        "structured_json_advertised_endpoint_count":7,
        "structured_json_and_max_tokens_advertised_count":4}}
    r=frozen_compatibility(data,catalog=fake)
    assert r["catalog_id_matched"] is True
    assert r["account_entitlement_certified"] is False
    assert r["historical_root_cause"]==NO_ERROR_CAUSE
    bad={"public_endpoint_catalog":{"http_status":"HTTP_404","matched_model_id":False}}
    assert frozen_compatibility(data,catalog=bad)["catalog_id_matched"] is False
    with pytest.raises(ContractViolation,match="V366_UNTRUSTED_CATALOG"):
        frozen_compatibility(data,catalog="injected raw body")

def test_whole_report_has_no_live_execution_or_claims_of_3b1b_quality():
    x=sanitized_report()
    assert x["scope"]=="OFFLINE_NO_PROVIDER_CALLS"
    assert x["live_model_posts"]==x["live_provider_gets"]==0
    assert x["automated_retries"]==0
    assert x["genuine_model_creativity"]=="NOT_TESTED"
    assert x["human_visual_quality"]=="UNRATED"
    assert x["production"]=="BLOCKED"
    assert x["static_diagnostic"]["historical_root_cause"]==NO_ERROR_CAUSE

@pytest.mark.parametrize("value,expected",[
    ("HTTP","HTTP"),("TRANSPORT","TRANSPORT"),("NO_ERROR","NO_ERROR"),
    (SECRET,"OTHER"),({"text":SECRET},"OTHER"),(None,"OTHER")])
def test_fixed_vocabulary_for_any_future_classification(value,expected):
    assert safe_label(value)==expected
