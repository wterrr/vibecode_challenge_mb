"""V3-68 adversarial checks: all fake metadata, never contact OpenRouter."""
from __future__ import annotations
import io,json
from urllib.error import HTTPError,URLError
import pytest
from learnflow_v3.openrouter_metadata_audit import KEY_URL,MAX_KEY_BYTES
from learnflow_v3.v368_key_cap_readonly import (
    check_registration,inspect_metadata,Refused)

FAKE_TOKEN="FAKE_SECRET_TOKEN_NEVER_IN_REPORT"
PRIVATE="PRIVATE_ACCOUNT_ID_DO_NOT_EMIT"
class Response:
    def __init__(self,data): self.data=json.dumps(data).encode()
    def __enter__(self):return self
    def __exit__(self,*a):return None
    def read(self,n):return self.data[:n]
def provider(*,limit=0.02,remaining=0.01,reset=None,byok=True,
             management=False):
    return {"data":{"limit":limit,"limit_remaining":remaining,
        "limit_reset":reset,"include_byok_in_limit":byok,
        "is_management_key":management,
        "creator_user_id":PRIVATE,"workspace_id":PRIVATE,
        "label":FAKE_TOKEN,"usage":201.01010,
        "byok_usage":100.02020,"is_free_tier":False}}
def sender(obj=None,*,error=None):
    seen=[]
    def transport(req,timeout):
        assert req.get_method()=="GET" and req.data is None
        assert req.full_url==KEY_URL
        assert req.headers["Authorization"]=="Bearer "+FAKE_TOKEN
        assert timeout<=12
        seen.append(req.full_url)
        if error is not None: raise error
        return Response(obj if obj is not None else provider())
    return transport,seen
def run(obj=None,*,err=None):
    transport,seen=sender(obj,error=err)
    receipt=inspect_metadata(key=FAKE_TOKEN,sender=transport)
    assert len(seen)==1
    assert receipt["provider_metadata_get_attempts"]==1
    assert receipt["model_http_post_attempts"]==0
    assert receipt["management_key_mutations"]==0
    assert receipt["may_issue_model_http_post"] is False
    serialized=json.dumps(receipt)
    for forbidden in (FAKE_TOKEN,PRIVATE,"creator_user_id","workspace_id",
                      "usage","label","Bearer","limit_remaining"):
        assert forbidden not in serialized
    return receipt

def test_frozen_registration_first_child_and_exact_endpoint():
    r=check_registration()
    assert r["registration"]=="FIRST_CHILD_COMMIT_BEFORE_ANY_NEW_PROVIDER_CALL"
    assert r["parent_pr"]==103
    assert r["max_model_posts"]==0
    assert r["endpoint"]==KEY_URL

def test_no_secret_makes_no_provider_get():
    result=inspect_metadata(key=None,sender=lambda *_a,**_kw:
                            pytest.fail("Should not GET"))
    assert result["provider_metadata_get_attempts"]==0
    assert result["current_key_metadata_http_status"]=="NOT_REQUESTED"
    assert result["budget_gate_result"]=="DENY_NO_AUTHENTICATED_KEY_SNAPSHOT"
    assert not result["provider_cap_structurally_satisfies_two_cent_lifetime_policy"]

def test_lifetime_two_cent_cap_fixture_pass_is_not_provider_proof():
    r=run()
    assert r["budget_gate_result"]=="KEY_CAP_CONDITIONS_SATISFIED_ONLY"
    assert r["synthetic_positive_is_not_provider_proof"] is True
    assert r["current_credential_provenance"]=="TEST_FIXTURE_NOT_PROVIDER_PROOF"
    assert r["provider_cap_structurally_satisfies_two_cent_lifetime_policy"] is False
    assert r["dedicated_key_identity_established"] is False
    assert r["funded_account_credit_established"] is False
    assert r["scientific_verdict"]=="HOST_TEST_ONLY_NOT_PROVIDER_PROOF"

@pytest.mark.parametrize("amount,expected",[
    (None,"DENY_MISSING_PROVIDER_KEY_CAP"),
    (100,"DENY_KEY_CAP_EXCEEDS_FROZEN_USD_BUDGET"),
    (0.0200001,"DENY_KEY_CAP_EXCEEDS_FROZEN_USD_BUDGET"),
    (0,"DENY_KEY_CAP_EXCEEDS_FROZEN_USD_BUDGET"),
    (-1,"DENY_INVALID_PROVIDER_KEY_CAP"),
    ("NaN","DENY_INVALID_PROVIDER_KEY_CAP"),
    ("Infinity","DENY_INVALID_PROVIDER_KEY_CAP"),
    (True,"DENY_INVALID_PROVIDER_KEY_CAP"),
    ("fake","DENY_INVALID_PROVIDER_KEY_CAP"),
])
def test_realistic_unsafe_key_limits_deny(amount,expected):
    r=run(provider(limit=amount))
    assert r["budget_gate_result"]==expected
    assert r["scientific_verdict"]=="DENY_NO_PROVIDER_CAP_PROOF"

@pytest.mark.parametrize("reset",["daily","weekly","monthly","lifetime","",False])
def test_periodically_resetting_caps_not_lifetime(reset):
    r=run(provider(reset=reset))
    assert r["budget_gate_result"]=="DENY_RESETTING_OR_UNVERIFIED_KEY_LIMIT"

@pytest.mark.parametrize("byok",[False,None,0,1,"true"])
def test_provider_limit_must_include_BYOK(byok):
    r=run(provider(byok=byok))
    assert r["budget_gate_result"]=="DENY_BYOK_SPEND_OUTSIDE_CAP"

@pytest.mark.parametrize("management",[True,None,1,"false"])
def test_only_inference_key_allowed(management):
    r=run(provider(management=management))
    assert r["budget_gate_result"]=="DENY_MANAGEMENT_OR_UNKNOWN_KEY_TYPE"

@pytest.mark.parametrize("remaining,expected",[
    (0,"DENY_NO_REMAINING_KEY_ALLOWANCE"),
    (0.021,"DENY_KEY_REMAINING_EXCEEDS_CAP"),
    (None,"DENY_INVALID_PROVIDER_KEY_CAP"),
    ("oops","DENY_INVALID_PROVIDER_KEY_CAP"),
    (-0.1,"DENY_INVALID_PROVIDER_KEY_CAP")
])
def test_remaining_limit_validation(remaining,expected):
    r=run(provider(remaining=remaining))
    assert r["budget_gate_result"]==expected

@pytest.mark.parametrize("code", [400,401,402,403,404,408,429,500,502,503])
def test_http_error_status_codes_only_no_private_error_body(code):
    error=HTTPError("https://private.example/"+PRIVATE,code,FAKE_TOKEN,{"raw":PRIVATE},
                    io.BytesIO(FAKE_TOKEN.encode()))
    r=run(err=error)
    assert r["current_key_metadata_http_status"]==f"HTTP_{code}"
    assert r["budget_gate_result"]=="DENY_KEY_METADATA_GET_UNAVAILABLE"

def test_redirect_never_follows():
    error=HTTPError("https://private.example/"+PRIVATE,302,FAKE_TOKEN,{"location":"https://evil.example"},None)
    result=run(err=error)
    assert result["current_key_metadata_http_status"]=="OTHER_STATUS"
    assert result["budget_gate_result"]=="DENY_KEY_METADATA_GET_UNAVAILABLE"

@pytest.mark.parametrize("bad",[
    {"wrong":"shape"},{"data":[]},{"data":{}},
    {"data":{"limit":0.02,"limit_remaining":0.01}},
])
def test_provider_malformed_envelope_cannot_pass(bad):
    r=run(bad)
    assert r["budget_gate_result"].startswith("DENY_")

def test_body_account_metadata_is_not_in_receipt():
    p=provider()
    p["data"]["exact_private_balance"]=201.484849393
    p["data"]["api_key"]=FAKE_TOKEN
    result=run(p)
    assert "201.484849393" not in json.dumps(result)

def test_urlerror_transport_is_categorized_without_exception_text():
    error=URLError("connection failed token="+FAKE_TOKEN)
    result=run(err=error)
    assert result["current_key_metadata_http_status"]=="NETWORK_OR_TIMEOUT"
    assert FAKE_TOKEN not in json.dumps(result)

def test_real_transport_flag_still_does_not_prove_dedicated_key_identity(monkeypatch):
    import learnflow_v3.v368_key_cap_readonly as module
    def stub(*args,**kwargs):
        assert args[0]==KEY_URL and kwargs["bearer"]==FAKE_TOKEN
        return "HTTP_200",provider()
    monkeypatch.setattr(module,"_get",stub)
    r=module.inspect_metadata(key=FAKE_TOKEN)
    assert r["provider_cap_structurally_satisfies_two_cent_lifetime_policy"] is True
    assert r["dedicated_key_identity_established"] is False
    assert r["may_issue_model_http_post"] is False
    # This is monkeypatch simulation, NOT real provider evidence.
