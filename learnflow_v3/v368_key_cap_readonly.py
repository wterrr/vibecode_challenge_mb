"""V3-68: one read-only OpenRouter GET /api/v1/key cap observation.

Reuse the already-reviewed V3-38 bounded, no-redirect, allowlisted GET transport
and V3-67 strict lifetime 0.02 USD policy. No model requests, no management API.
No request URL/content, token, account IDs, raw response or actual limit amounts
are ever stored. Real GET proves a cap on the CURRENT credential only, NOT that
the key is dedicated to LearnFlow or that this software can approve a paid POST.
"""
from __future__ import annotations

import json
from datetime import datetime,timezone
from pathlib import Path
from learnflow_v3.openrouter_metadata_audit import KEY_URL,MAX_KEY_BYTES,_get
from learnflow_v3.v367_corrected_wire_budget import policy_for_key,MAX_USD

ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/"benchmarks/learnflowbench/v3/v3_68_readonly_key_cap_preregister.json"
SAFE_STATUSES=frozenset({"HTTP_200","HTTP_400","HTTP_401","HTTP_402","HTTP_403",
    "HTTP_404","HTTP_408","HTTP_422","HTTP_429","HTTP_500","HTTP_502",
    "HTTP_503","HTTP_504","NETWORK_OR_TIMEOUT","RESPONSE_TOO_LARGE",
    "INVALID_JSON","NOT_REQUESTED"})
SAFE_POLICY=frozenset({
    "KEY_CAP_CONDITIONS_SATISFIED_ONLY",
    "DENY_NO_AUTHENTICATED_KEY_SNAPSHOT","DENY_UNVERIFIED_KEY_PROVENANCE",
    "DENY_INVALID_KEY_METADATA","DENY_MISSING_KEY_DATA",
    "DENY_MANAGEMENT_OR_UNKNOWN_KEY_TYPE","DENY_BYOK_SPEND_OUTSIDE_CAP",
    "DENY_RESETTING_OR_UNVERIFIED_KEY_LIMIT","DENY_MISSING_PROVIDER_KEY_CAP",
    "DENY_INVALID_PROVIDER_KEY_CAP",
    "DENY_KEY_CAP_EXCEEDS_FROZEN_USD_BUDGET",
    "DENY_NO_REMAINING_KEY_ALLOWANCE","DENY_KEY_REMAINING_EXCEEDS_CAP"})
class Refused(ValueError):pass

def guard(condition,why):
    if not condition:raise Refused("V368_"+why)

def check_registration():
    r=json.loads(REG.read_text(encoding="utf-8"))
    guard(r["checkpoint"]=="V3-68" and
        r["registration"]=="FIRST_CHILD_COMMIT_BEFORE_ANY_NEW_PROVIDER_CALL" and
        r["parent_pr"]==103 and
        r["parent_sha"]=="c0b6efe0fb1c149d0fb823e579afcf9ff5821d93" and
        r["method"]=="GET" and r["endpoint"]==KEY_URL and
        r["max_provider_gets"]==1 and r["max_model_posts"]==0 and
        r["max_management_mutations"]==0 and r["retries"]==0 and
        r["redirects"] is False and r["budget_usd"]=="0.02" and
        r["output_security"]["no_raw_key"] is True and
        r["disposition"]["real_get_structural_cap_pass_does_not_authorize_post"] is True,
        "PREREG_CHANGED")
    return r

def safe_http(value):
    return value if type(value) is str and value in SAFE_STATUSES else "OTHER_STATUS"

def inspect_metadata(*,key:str|None,sender=None):
    """Exactly one GET if key exists; test sender => TEST_ONLY provenance."""
    check_registration()
    genuine_transport=sender is None
    attempted=0
    status="NOT_REQUESTED"
    body=None
    if type(key) is str and len(key)>=10:
        attempted=1
        status,body=_get(KEY_URL,bearer=key,sender=sender,max_bytes=MAX_KEY_BYTES)
    allowed=safe_http(status)
    if attempted==0:
        policy="DENY_NO_AUTHENTICATED_KEY_SNAPSHOT"
    elif allowed!="HTTP_200":
        policy="DENY_KEY_METADATA_GET_UNAVAILABLE"
    else:
        # Input is from the already authenticated GET parser; body never leaves
        # this function and must never be printed, logged or written to artifact.
        p=policy_for_key(body,trusted_authenticated_get=True)
        policy=p["policy_result"]
        guard(policy in SAFE_POLICY,"UNEXPECTED_PROVIDER_BUDGET_POLICY")
    structural_ok=policy=="KEY_CAP_CONDITIONS_SATISFIED_ONLY"
    return {
        "checkpoint":"V3-68",
        "checked_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "current_credential_provenance":(
            "REAL_AUTHENTICATED_GET_TO_KEY_ENDPOINT" if genuine_transport and
            allowed=="HTTP_200" else
            "TEST_FIXTURE_NOT_PROVIDER_PROOF" if not genuine_transport else
            "NO_AUTHENTICATED_GET_PROOF"),
        "endpoint":"GET_CURRENT_KEY_ONLY",
        "current_key_metadata_http_status":allowed,
        "provider_metadata_get_attempts":attempted,
        "model_http_post_attempts":0,
        "management_key_mutations":0,
        "redirects_followed":0,"retries":0,
        "required_spending_cap_usd":"0.02",
        "budget_gate_result":policy,
        "provider_cap_structurally_satisfies_two_cent_lifetime_policy":bool(
            structural_ok and genuine_transport),
        "synthetic_positive_is_not_provider_proof":not genuine_transport,
        "dedicated_key_identity_established":False,
        "funded_account_credit_established":False,
        "exact_model_routing_established":False,
        "fresh_user_paid_approval":False,
        "may_issue_model_http_post":False,
        "raw_key_or_private_provider_body_persisted":False,
        "raw_account_or_key_identifiers_persisted":False,
        "exact_key_cap_or_balance_persisted":False,
        "historical_v364_http_error_code":"NOT_CAPTURED_CANNOT_RECOVER",
        "historical_v364_root_cause":"UNDETERMINED",
        "genuine_model_storyboard_generated":"NOT_TESTED",
        "independent_human_quality":"UNRATED",
        "learner_improvement":"NOT_MEASURED",
        "production":"BLOCKED",
        "scientific_verdict":(
            "READONLY_CURRENT_KEY_CAP_STRUCTURAL_PASS_DEDICATION_UNPROVEN" if
            structural_ok and genuine_transport else
            "DENY_NO_PROVIDER_CAP_PROOF" if not structural_ok else
            "HOST_TEST_ONLY_NOT_PROVIDER_PROOF"),
    }
