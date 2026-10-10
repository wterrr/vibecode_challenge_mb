"""V3-38: zero-inference model catalog / key metadata adversarial tests."""
from __future__ import annotations

from io import BytesIO
from urllib.error import HTTPError
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

# Metadata diagnostics are self-contained stdlib source. Import this FILE by
# path, not `learnflow_v3.openrouter_metadata_audit`: package __init__ eagerly
# imports the V2 layout/QA stack (and kiwisolver), which is irrelevant here.
ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "learnflow_v3" / "openrouter_metadata_audit.py"
spec = importlib.util.spec_from_file_location("v3_38_metadata_standalone", AUDIT)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
MODEL, CATALOG_URL, KEY_URL, MetadataInvalid = (
    audit.MODEL, audit.CATALOG_URL, audit.KEY_URL, audit.MetadataInvalid
)
probe_model_endpoints = audit.probe_model_endpoints
probe_current_key = audit.probe_current_key
run_audit = audit.run_audit
_get = audit._get
SECRET = "sk-or-v1-FAKE_DO_NOT_STORE_SECRET_123"


def _response(obj):
    class Response:
        def __enter__(self):
            return BytesIO(json.dumps(obj).encode())
        def __exit__(self, *args):
            return False
    return Response()


def _catalog():
    return {
        "data": {
            "id": MODEL,
            "endpoints": [
                {"provider_name": "OpenAI",
                 "tag": "openai",
                 "supported_parameters": [
                     "response_format", "structured_outputs", "max_tokens"]},
                {"provider_name": "Azure",
                 "tag": "azure",
                 "supported_parameters": [
                     "response_format", "structured_outputs",
                     "max_completion_tokens"]},
                {"provider_name": "Other",
                 "supported_parameters": ["tools"]},
            ],
        }
    }


def _key():
    return {
        "data": {
            "creator_user_id": "SENSITIVE_USER_ID_DO_NOT_PERSIST",
            "label": "SENSITIVE_LABEL_DO_NOT_PERSIST",
            "workspace_id": "SENSITIVE_WORKSPACE_DO_NOT_PERSIST",
            "is_free_tier": False,
            "is_management_key": False,
            "limit": 50,
            "limit_remaining": 12.5,
            "usage": 15.5,
            "expires_at": "2099-12-31T00:00:00Z",
        }
    }


def test_module_loads_with_python_no_site_packages_and_no_learnflow_import():
    # -S disables site packages. This catches accidental dependency creep.
    command = [
        sys.executable, "-S", "-c",
        ("import importlib.util, sys; "
         "p = sys.argv[1]; "
         "s = importlib.util.spec_from_file_location('metadata_only', p); "
         "m = importlib.util.module_from_spec(s); "
         "s.loader.exec_module(m); "
         "assert m.MODEL == 'openai/gpt-6-luna'; "
         "assert 'learnflow_v3' not in sys.modules; "
         "assert 'learnflow_v2' not in sys.modules; "
         "assert 'kiwisolver' not in sys.modules; "
         "assert 'pydantic' not in sys.modules"),
        str(AUDIT),
    ]
    result = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, timeout=10,
        check=False
    )
    assert result.returncode == 0, result.stderr


def test_preregistration_before_code_and_no_post():
    p=json.loads((ROOT/"benchmarks/learnflowbench/v3/v3_38_openrouter_metadata_audit_preregister.json").read_text())
    assert p["checkpoint"]=="V3-38"
    assert p["inference_budget_authorized"]==0
    assert p["pre_registered_before_implementation"] if "pre_registered_before_implementation" in p else p["preregistered_before_implementation"]
    assert p["max_requests_per_run"]==2
    assert p["allowed_http_methods"]==["GET"]
    assert "/api/v1/chat/completions" not in p["allowed_paths"]


def test_exact_two_gets_no_secret_in_receipt():
    calls=[]
    def sender(req,timeout):
        calls.append(req)
        assert req.get_method()=="GET"
        assert req.data is None
        assert req.full_url in (KEY_URL, CATALOG_URL)
        assert timeout<=12
        if req.full_url==CATALOG_URL:
            assert req.get_header("Authorization") is None
            return _response(_catalog())
        assert req.get_header("Authorization")=="Bearer "+SECRET
        return _response(_key())
    r=run_audit(SECRET,sender=sender)
    assert len(calls)==2
    assert r["inference_http_posts"]==0
    assert r["get_requests_attempted"]==2
    assert r["public_catalog"]["schema_advertised_count"]==2
    assert r["public_catalog"]["schema_and_max_tokens_count"]==1
    assert r["public_catalog"]["schema_and_max_completion_tokens_count"]==1
    assert r["key_metadata"]["state"]=="KEY_AUTHENTICATED_METADATA_ONLY"
    assert r["key_metadata"]["key_limit_remaining_state"]=="POSITIVE"
    assert r["key_metadata"]["key_type"]=="INFERENCE"
    assert r["key_metadata"]["account_credits_verified"] is False
    assert r["historical_v3_37_http_404_root_cause"]=="UNDETERMINED"
    artifact=json.dumps(r)
    for sensitive in [SECRET,"SENSITIVE_USER_ID","SENSITIVE_LABEL",
                      "SENSITIVE_WORKSPACE","12.5","15.5"]:
        assert sensitive not in artifact


@pytest.mark.parametrize("url,bearer",[
    ("https://untrusted.example/a","fake"),
    ("https://openrouter.ai/api/v1/chat/completions",None),
    ("https://openrouter.ai/api/v1/keys",SECRET),
    (KEY_URL,None),
    (CATALOG_URL,SECRET),
])
def test_only_allowlisted_get_urls_and_auth_split(url,bearer):
    called=[]
    with pytest.raises(MetadataInvalid):
        _get(url,bearer=bearer,sender=lambda *a,**k:called.append(1),
             max_bytes=1000)
    assert not called


def test_missing_key_only_one_public_get():
    calls=[]
    def sender(request,timeout):
        calls.append(request.full_url)
        return _response(_catalog())
    r=run_audit(None,sender=sender)
    assert calls==[CATALOG_URL]
    assert r["key_metadata"]["state"]=="KEY_NOT_CONFIGURED"
    assert r["inference_http_posts"]==0


@pytest.mark.parametrize("http_code,expected", [
    (401,"KEY_UNAUTHORIZED"),
    (403,"KEY_METADATA_ACCESS_DENIED_OR_RATE_LIMITED"),
    (404,"KEY_ENDPOINT_UNAVAILABLE"),
    (429,"KEY_METADATA_ACCESS_DENIED_OR_RATE_LIMITED"),
])
def test_http_key_errors_no_body_leak(http_code,expected):
    def reject(request,timeout):
        raise HTTPError(request.full_url,http_code,
                        "SENSITIVE_SERVER_MESSAGE_SHOULD_NOT_LEAK",{},None)
    result=probe_current_key(SECRET,sender=reject)
    assert result["state"]==expected
    assert result["key_authenticated"] is False
    assert "SENSITIVE_SERVER_MESSAGE" not in json.dumps(result)


def test_malformed_untrusted_provider_name_and_catalog_mismatch():
    evil=_catalog()
    evil["data"]["endpoints"][0]["provider_name"]={"evil":"value"}
    r=probe_model_endpoints(sender=lambda *a,**k:_response(evil))
    assert r["schema_advertised_count"]==2
    assert r["schema_provider_names"]==["Azure"]
    evil["data"]["id"]="some-other-model"
    r=probe_model_endpoints(sender=lambda *a,**k:_response(evil))
    assert r["state"]=="CATALOG_INVALID_MODEL_ID"


@pytest.mark.parametrize("case", ["negative_limit","no_cap","missing_limit_remaining",
                                   "key_expired","ambiguous_type","missing_role"])
def test_key_sanitizes_limit_and_expiry(case):
    data=_key()
    if case=="negative_limit":data["data"]["limit_remaining"]=-1
    if case=="no_cap":data["data"]["limit"]=None
    if case=="missing_limit_remaining":data["data"]["limit_remaining"]="incorrect"
    if case=="key_expired":data["data"]["expires_at"]="2000-01-01T00:00:00Z"
    if case=="ambiguous_type":data["data"]["is_free_tier"]="false"
    if case=="missing_role":data["data"].pop("is_management_key")
    r=probe_current_key(SECRET,sender=lambda *a,**k:_response(data))
    if case=="negative_limit":assert r["key_limit_remaining_state"]=="ZERO_OR_NEGATIVE"
    if case=="no_cap":assert r["key_limit_remaining_state"]=="NO_EXPLICIT_KEY_CAP_REPORTED"
    if case=="missing_limit_remaining":assert r["key_limit_remaining_state"]=="UNKNOWN"
    if case=="key_expired":assert r["expiry_state"]=="EXPIRED"
    if case=="ambiguous_type":assert r["free_tier"]=="UNKNOWN"
    if case=="missing_role":assert r["key_type"]=="UNKNOWN"
    assert "creator_user_id" not in json.dumps(r)


def test_network_catalog_failure_does_not_claim_deleted_model():
    def fails(req,timeout):
        raise HTTPError(req.full_url,404,"public unavailable",{},None)
    x=probe_model_endpoints(sender=fails)
    assert x["state"]=="CATALOG_UNVERIFIED"
    assert x["http_status"]=="HTTP_404"
    assert x["account_eligibility_certified"] is False


def test_all_get_metadata_never_proves_route_or_post_success():
    def sender(req,timeout):
        return _response(_key() if req.full_url==KEY_URL else _catalog())
    result=run_audit(SECRET,sender=sender)
    assert result["key_metadata"]["model_entitlement_verified"] is False
    assert result["routing_compatibility_exact_post"]=="NOT_TESTED"
    assert result["production"]=="BLOCKED"
