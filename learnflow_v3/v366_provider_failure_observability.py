"""V3-66: prospective, *pure offline* provider HTTP observability contract.

Never opens a socket, reads response bodies, collects API keys, or retries.
Use with a FUTURE separately authorized transport by passing caught exceptions.
V3-64's historical status cannot be reconstructed by this prospective module.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
from typing import Any
import json
from urllib.error import HTTPError,URLError

MODEL="openai/gpt-6-luna"
KNOWN_CODES=frozenset({400,401,402,403,404,408,409,413,422,429,500,502,503,504,524,529})
NO_ERROR_CAUSE="UNDETERMINED_FROM_STATUS_ONLY"
HISTORICAL_RUN=38502942783
COST_STATE="TOKEN_CEILING_ONLY_NOT_HARD_DOLLAR_CAP"
VERSION="v3-66-offline-http-observability-v1"

class ContractViolation(ValueError):
    pass

def need(test,reason):
    if not test: raise ContractViolation("V366_"+reason)

def sanitize_code(error:BaseException)->str:
    """Only retrieve HTTPError.code; NEVER str(error), headers, URL, reason or body."""
    if isinstance(error,HTTPError):
        value=error.code
        if type(value) is not int: return "HTTP_UNKNOWN"
        if value in KNOWN_CODES:return "HTTP_"+str(value)
        if 300<=value<400:return "REDIRECT_BLOCKED"
        return "HTTP_OTHER"
    if isinstance(error,(TimeoutError,ConnectionError)):
        return "TRANSPORT_UNAVAILABLE"
    if isinstance(error,URLError):
        # error.reason may embed token, hostname, private endpoint, etc.
        return "TRANSPORT_UNAVAILABLE"
    return "UNKNOWN_EXCEPTION_TYPE"

def safe_label(value:object)->str:
    """Store a safe, fixed-vocabulary label; never echo arbitrary caller input."""
    return value if value in ("HTTP","TRANSPORT","NO_ERROR") else "OTHER"

def incident(error:BaseException|None,*,request_bytes:bytes,
             request_attempts:int, model:str=MODEL)->dict[str,Any]:
    """Prospective sanitized *local* event: one explicit prior attempt, no networking."""
    need(type(request_bytes) is bytes and 0<len(request_bytes)<=14000,
         "BAD_FROZEN_REQUEST_BYTES")
    need(type(request_attempts) is int and request_attempts in (0,1),
         "MULTIPLE_POST_ATTEMPTS_NOT_ALLOWED")
    need(model==MODEL,"UNREGISTERED_MODEL")
    if error is None:need(request_attempts==1,"SUCCESS_WITHOUT_ATTEMPT")
    if error is not None:need(request_attempts==1,"FAILURE_WITHOUT_ATTEMPT")
    status="HTTP_200_OBSERVED" if error is None else sanitize_code(error)
    return {
        "contract_version":VERSION,
        "request_body_sha256":sha256(request_bytes).hexdigest(),
        "requested_model":MODEL,
        "attempts_on_client":request_attempts,
        "http_status_observed":status,
        "provider_response_body_recorded":False,
        "error_headers_recorded":False,
        "raw_exception_recorded":False,
        "authorization_header_recorded":False,
        "error_url_recorded":False,
        "retry":0,"fallback":False,
        "exact_error_reason":NO_ERROR_CAUSE,
        "historical_v364_http_status":"NOT_CAPTURED_CANNOT_RECOVER",
        "historical_v364_run":HISTORICAL_RUN,
        "further_paid_calls_authorized":False,
        "inference_requests_executed_by_this_module":0,
        "human_pedagogy":"UNRATED",
        "model_authored_storyboard":"NOT_TESTED_IN_V366",
        "production":"BLOCKED",
    }

def frozen_compatibility(original:dict,*,catalog:dict|None=None)->dict:
    """Pure analysis of the V3-64 wire. This never silently repairs a request.

    Public catalog metadata is advisory; missing advertised fields are not a
    proof of historical rejection, and provider order is not account entitlement.
    """
    need(type(original) is dict and original.get("model")==MODEL,
         "FROZEN_MODEL_MISMATCH")
    provider=original.get("provider")
    need(type(provider) is dict,"MISSING_PROVIDER_WIRE")
    need(original.get("max_tokens")==2100 and
         original.get("response_format",{}).get("type")=="json_schema" and
         original.get("response_format",{}).get("json_schema",{}).get("strict") is True,
         "FROZEN_STRUCTURED_WIRE_CHANGED")
    need(provider.get("order")==["OpenAI"] and
         provider.get("require_parameters") is True and
         provider.get("allow_fallback") is False and
         "allow_fallbacks" not in provider and
         "temperature" not in original,
         "HISTORICAL_PROVIDER_SHAPE_CHANGED")
    issues=[
        {"code":"LEGACY_PROVIDER_ALLOW_FALLBACK_FIELD",
         "actual":"allow_fallback","documented":"allow_fallbacks",
         "class":"REQUEST_SHAPE_POTENTIAL_INCOMPATIBILITY",
         "proven_caused_v364_error":False},
        {"code":"STRICT_SCHEMA_ENDPOINT_ROUTING_NOT_PROVEN",
         "class":"METADATA_INSUFFICIENT",
         "proven_caused_v364_error":False},
        {"code":"MODEL_ACCOUNT_FUNDS_NOT_ESTABLISHED",
         "class":"METADATA_INSUFFICIENT",
         "proven_caused_v364_error":False},
        {"code":"TOKEN_LIMIT_NOT_DOLLAR_CAP",
         "class":"COST_BUDGET_UNENFORCED_AS_DOLLAR_CAP",
         "proven_caused_v364_error":False},
    ]
    supported=None
    if catalog is not None:
        need(type(catalog) is dict,"UNTRUSTED_CATALOG")
        pc=catalog.get("public_endpoint_catalog")
        need(type(pc) is dict,"UNTRUSTED_CATALOG_ENVELOPE")
        # Do not trust catalog to prove exact schema/provider/account authorization.
        supported=pc.get("http_status")=="HTTP_200" and pc.get("matched_model_id") is True
    return {
        "checkpoint":"V3-66","analysis_mode":"STATIC_ONLY",
        "source_request_sha256":sha256(json.dumps(original,separators=(",",":"),ensure_ascii=True).encode()).hexdigest(),
        "model":MODEL,
        "provider_order":["OpenAI"],
        "provider_options_observed":sorted(provider),
        "public_metadata_present":catalog is not None,
        "catalog_id_matched":supported,
        "findings":issues,
        "prospective_recommendation":"Use documented allow_fallbacks:false in a NEW request if later explicitly authorized; DO NOT MODIFY_OR_REPLAY V3-64.",
        "historical_HTTP_error_code":"NOT_CAPTURED_CANNOT_RECOVER",
        "historical_root_cause":NO_ERROR_CAUSE,
        "provider_api_requests_by_analysis":0,
        "hard_dollar_budget_enforced":False,
        "account_entitlement_certified":False,
        "production":"BLOCKED"
    }

def diagnostic_from_frozen(*,catalog:dict|None=None)->dict:
    """Read frozen V3-64 request builder locally; never import a live runner."""
    from scripts.run_v3_64_one_shot_real_model import request_payload
    payload,_=request_payload()
    return frozen_compatibility(payload,catalog=catalog)

def sanitized_report()->dict:
    """A complete zero-request V3-66 audit (all tests may use this)."""
    original=diagnostic_from_frozen()
    return {
        "checkpoint":"V3-66","scope":"OFFLINE_NO_PROVIDER_CALLS",
        "static_diagnostic":original,"live_model_posts":0,
        "live_provider_gets":0,"automated_retries":0,
        "prospective_error_capture_preflight":"TEST_ONLY_NO_NEW_HTTP_OBSERVATIONS",
        "legacy_trial_unchanged":True,
        "human_visual_quality":"UNRATED",
        "genuine_model_creativity":"NOT_TESTED",
        "learning_gain":"NOT_MEASURED",
        "production":"BLOCKED",
    }
