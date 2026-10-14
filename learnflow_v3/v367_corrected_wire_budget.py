"""V3-67: corrected OpenRouter request + provider-side budget attestation preflight.

This module is purely local and CANNOT authorize an HTTP request. Even if all
fixture values satisfy the policy, a new live trial needs a fresh independent
preregistration, a real authenticated key metadata observation and user consent.

The true USD enforcement point is an OpenRouter-enforced lifetime key limit.
A token ceiling or locally calculated estimate never substitutes for it.
"""
from __future__ import annotations

import copy
from decimal import Decimal,InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

MODEL="openai/gpt-6-luna"
MAX_USD=Decimal("0.02")
FROZEN_V364_SHA="728e32b0bea658a82054184efee840ddb72957851f0ba87d21042d96d4134c0f"
FIXED_FIELDS=("model","max_tokens","stream","messages","response_format")
REQUIRED_ORDER=("OpenAI",)
VERSION="v3-67-corrected-wire-deny-by-default-v1"

class BudgetBlocked(ValueError):
    pass

def deny(message: str):
    raise BudgetBlocked("V367_"+message)

def safe_sha(payload: bytes)->str:
    if type(payload) is not bytes or not 0<len(payload)<=14000:
        deny("UNSAFE_REQUEST_BYTES")
    return sha256(payload).hexdigest()

def original_payload():
    """Import preserved V3-64 factory; never edit that historical function."""
    from scripts.run_v3_64_one_shot_real_model import request_payload
    obj,raw=request_payload()
    if safe_sha(raw)!=FROZEN_V364_SHA:
        deny("ARCHIVED_V364_REQUEST_CHANGED")
    if obj.get("provider")!={"order":["OpenAI"],"allow_fallback":False,
                           "require_parameters":True}:
        deny("ARCHIVED_V364_PROVIDER_DRIFT")
    return obj,raw

def corrected_request():
    """Only change provider.allow_fallback -> provider.allow_fallbacks."""
    old,raw=original_payload()
    corrected=copy.deepcopy(old)
    provider=corrected["provider"]
    prior=provider.pop("allow_fallback")
    if prior is not False:deny("OLD_PROVIDER_ALLOWED_FALLBACK")
    if "allow_fallbacks" in provider:deny("DOUBLE_FALLBACK_FIELDS")
    provider["allow_fallbacks"]=False
    new_raw=json.dumps(corrected,separators=(",",":"),ensure_ascii=True).encode()
    if len(new_raw)>14000:deny("CORRECTED_WIRE_TOO_LARGE")
    if {k:v for k,v in old.items() if k!="provider"}!={
       k:v for k,v in corrected.items() if k!="provider"}:
        deny("UNAUTHORIZED_NONPROVIDER_CHANGE")
    if set(provider)!={"order","require_parameters","allow_fallbacks"}:
        deny("UNAUTHORIZED_PROVIDER_FIELDS")
    if provider["order"]!=list(REQUIRED_ORDER) or provider["require_parameters"] is not True:
        deny("PROVIDER_ROUTING_DRIFT")
    if corrected.get("max_tokens")!=2100 or "temperature" in corrected or "models" in corrected:
        deny("UNREGISTERED_GENERATION_PARAMETERS")
    if corrected["response_format"]["type"]!="json_schema" or (
      corrected["response_format"]["json_schema"]["strict"] is not True):
        deny("STRICT_JSON_SCHEMA_CHANGED")
    return corrected,new_raw

def key_amount(value:object,field:str)->Decimal:
    """Interpret only finite, scalar USD values from an authenticated key GET."""
    if isinstance(value,bool) or value is None or type(value) not in (float,int,str,Decimal):
        deny("KEY_"+field+"_UNVERIFIED")
    try:
        raw=str(value)
        amount=Decimal(raw)
    except (InvalidOperation,ValueError):
        deny("KEY_"+field+"_UNVERIFIED")
    if not amount.is_finite() or amount<0:
        deny("KEY_"+field+"_UNVERIFIED")
    return amount

def policy_for_key(snapshot:dict|None,*,trusted_authenticated_get:bool=False)->dict:
    """A fail-closed gate requiring a server-enforced key cap.

    trusted_authenticated_get=True is ONLY meaningful when the caller has
    actually performed authenticated GET /api/v1/key from a trusted transport.
    V3-67 never performs it, and this function never grants POST permission.
    Test mocks are tagged as hypothetical, not provider or budget evidence.
    """
    if snapshot is None:
        return blocked("DENY_NO_AUTHENTICATED_KEY_SNAPSHOT")
    if type(snapshot) is not dict:
        return blocked("DENY_INVALID_KEY_METADATA")
    if trusted_authenticated_get is not True:
        return blocked("DENY_UNVERIFIED_KEY_PROVENANCE")
    entry=snapshot.get("data")
    if type(entry) is not dict:
        return blocked("DENY_MISSING_KEY_DATA")
    if entry.get("is_management_key") is not False:
        return blocked("DENY_MANAGEMENT_OR_UNKNOWN_KEY_TYPE")
    if entry.get("include_byok_in_limit") is not True:
        return blocked("DENY_BYOK_SPEND_OUTSIDE_CAP")
    if "limit_reset" not in entry or entry["limit_reset"] is not None:
        return blocked("DENY_RESETTING_OR_UNVERIFIED_KEY_LIMIT")
    if "limit" not in entry or "limit_remaining" not in entry:
        return blocked("DENY_MISSING_PROVIDER_KEY_CAP")
    try:
        cap=key_amount(entry["limit"],"LIMIT")
        left=key_amount(entry["limit_remaining"],"REMAINING")
    except BudgetBlocked:
        return blocked("DENY_INVALID_PROVIDER_KEY_CAP")
    if cap<=0 or cap>MAX_USD:
        return blocked("DENY_KEY_CAP_EXCEEDS_FROZEN_USD_BUDGET")
    if left<=0:
        return blocked("DENY_NO_REMAINING_KEY_ALLOWANCE")
    if left>cap:
        return blocked("DENY_KEY_REMAINING_EXCEEDS_CAP")
    # Critically: no live POST can be issued by this module.
    return {
        "policy_result":"KEY_CAP_CONDITIONS_SATISFIED_ONLY",
        "provider_cap_category":"AT_OR_BELOW_REGISTERED_LIFETIME_2_CENTS",
        "byok_spend_included":True,
        "key_limit_is_lifetime":True,
        "remaining_allowance":"POSITIVE_WITHIN_PROVIDER_KEY_CAP",
        "auth_snapshot_used":"CALLER_ASSERTED_TRUE_NOT_INDEPENDENTLY_VERIFIED_HERE",
        "live_post_permitted":False,
        "is_genuine_provider_cap_proof":False,
        "actual_charge_guaranteed_by_this_software":False,
        "approval":"SEPARATE_PREREG_AND_USER_AUTH_REQUIRED",
    }

def blocked(why:str)->dict:
    return {
        "policy_result":why,
        "live_post_permitted":False,
        "is_genuine_provider_cap_proof":False,
        "actual_charge_guaranteed_by_this_software":False,
        "approval":"SEPARATE_PREREG_AND_USER_AUTH_REQUIRED",
    }

def budget_preflight(snapshot:dict|None=None,*,trusted_authenticated_get:bool=False)->dict:
    request,raw=corrected_request()
    approved=policy_for_key(snapshot,trusted_authenticated_get=trusted_authenticated_get)
    return {
        "checkpoint":"V3-67",
        "contract_version":VERSION,
        "original_v364_request_sha256":FROZEN_V364_SHA,
        "corrected_request_sha256":safe_sha(raw),
        "corrected_provider_keys":sorted(request["provider"]),
        "request_still_frozen_in_other_fields":True,
        "provider_allow_fallbacks":False,
        "provider_require_parameters":True,
        "provider_order":["OpenAI"],
        "model":MODEL,
        "output_token_ceiling":2100,
        "usd_budget_frozen":"0.02",
        "token_ceiling_is_usd_hard_cap":False,
        "real_hard_limit_requires_provider_configuration":True,
        "current_key_budget_attestation":approved,
        "preflight_result":approved["policy_result"],
        "new_model_inference_posts":0,
        "new_provider_gets":0,
        "new_management_key_actions":0,
        "can_authorize_paid_POST":False,
        "can_claim_provider_cap_verified_in_v367":False,
        "historical_v364_http_cause":"UNDETERMINED",
        "model_authorship":"NOT_TESTED",
        "human_pedagogical_quality":"UNRATED",
        "learning_gain":"NOT_MEASURED",
        "production":"BLOCKED",
    }

def registered_report(prereg_path:Path)->dict:
    doc=json.loads(prereg_path.read_text())
    if (doc.get("checkpoint")!="V3-67" or
        doc.get("registration")!="FIRST_CHILD_COMMIT_BEFORE_IMPLEMENTATION" or
        doc.get("parent_pr")!=102 or
        doc.get("parent_sha")!="b637e8783560aad02d9d3353f981fb22731fc9a8" or
        doc["budget"]["total_usd_cap"]!="0.02" or
        doc["budget"]["allow_live_api_posts"]!=0 or
        doc["protocol_controls"]["no_network_reads"] is not True or
        doc["protocol_controls"]["no_network_writes"] is not True):
        deny("PREREG_DRIFT")
    return budget_preflight()
