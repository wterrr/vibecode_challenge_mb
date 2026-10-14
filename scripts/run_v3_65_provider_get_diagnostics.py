"""V3-65 zero-inference retrospective OpenRouter failure triage.
Reuse V3-38 allowlisted GET-only metadata functions and intentionally export
no raw token, error body, exact balance, account identifiers or HTTP POST.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json,os,sys
from pathlib import Path
from hashlib import sha256

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from learnflow_v3.openrouter_metadata_audit import run_audit, MODEL
from learnflow_v3.v364_heldout_storyboard import assert_prereg as check_v364
from scripts.run_v3_64_one_shot_real_model import request_payload

REG=ROOT/"benchmarks/learnflowbench/v3/v3_65_provider_get_diagnostics_preregister.json"
OLD=ROOT/"benchmarks/learnflowbench/v3/v3_64_one_shot_genuine_storyboard_preregister.json"
SAFE_HTTP=frozenset(("HTTP_200","HTTP_400","HTTP_401","HTTP_402","HTTP_403","HTTP_404",
"HTTP_408","HTTP_409","HTTP_422","HTTP_429","HTTP_500","HTTP_502","HTTP_503",
"HTTP_504","NOT_REQUESTED","NETWORK_OR_TIMEOUT","RESPONSE_TOO_LARGE","INVALID_JSON"))
class Blocked(ValueError):pass
def need(cond,why):
    if not cond:raise Blocked("V365_"+why)

def freeze_check():
    x=json.loads(REG.read_text())
    need(x["checkpoint"]=="V3-65" and
        x["registration"]=="FIRST_CHILD_COMMIT_BEFORE_DIAGNOSTICS" and
        x["parent_pr"]==100 and
        x["parent_sha"]=="f8d4e150f2b3e9c3003d3aa6aba30261a36b92dd" and
        x["historical_live_run"]==38502942783 and
        x["historical_artifact_id"]==11866413693 and
        x["historical_outcome"]=="PROVIDER_TRANSPORT_OR_HTTP_FAILURE_NO_RETRY" and
        x["historical_http_status"]=="NOT_CAPTURED" and
        x["historical_http_body"]=="NOT_CAPTURED","PREREG_DRIFT")
    need(x["max_network_gets"]==2 and
        x["max_provider_inference_posts"]==0 and
        x["retries"]==0 and x["redirects"] is False and
        x["no_raw_responses_saved"] is True and
        x["no_exact_account_balance_saved"] is True and
        x["frozen_acceptance"]["no_new_model_trial"] is True,"NETWORK_SCOPE_DRIFT")
    need(tuple((q["method"],q["url"]) for q in x["queries"])==(
        ("GET","https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints"),
        ("GET","https://openrouter.ai/api/v1/key")),"ENDPOINT_NOT_ALLOWLISTED")
    check_v364(OLD)
    return x

def diagnostic(*,key=None,sender=None):
    freeze_check()
    payload,raw=request_payload()
    need(payload["model"]==MODEL and
        payload["provider"]["order"]==["OpenAI"] and
        payload["provider"]["allow_fallback"] is False and
        payload["provider"]["require_parameters"] is True and
        payload["max_tokens"]==2100 and
        payload["response_format"]["type"]=="json_schema" and
        payload["response_format"]["json_schema"]["strict"] is True and
        "temperature" not in payload,"FROZEN_WIRE_DRIFT")
    audit=run_audit(key,sender=sender)
    need(audit["inference_http_posts"]==0 and
         audit["get_requests_attempted"]<=2 and
         audit["model"]==MODEL,"V338_GET_ONLY_CONTRACT_DRIFT")
    cat= audit["public_catalog"]; auth=audit["key_metadata"]
    public=(cat["http_status"]=="HTTP_200" and cat["model_id_matched"] is True)
    auth_ok=(auth["key_authenticated"] is True and auth["key_type"]=="INFERENCE")
    advertised=(public and "OpenAI" in cat.get("schema_provider_names",[]))
    token_param=(public and isinstance(cat.get("schema_and_max_tokens_count"),int)
                 and cat["schema_and_max_tokens_count"]>0)
    if auth["state"]=="KEY_NOT_CONFIGURED":
        decision="INCONCLUSIVE_NO_CREDENTIAL"
    elif auth["state"]=="KEY_UNAUTHORIZED":
        decision="KEY_AUTH_FAILURE_METADATA_ONLY"
    elif not public:
        decision="PUBLIC_MODEL_ENDPOINTS_NOT_VERIFIED"
    elif not auth_ok:
        decision="GET_KEY_UNUSABLE_OR_UNVERIFIED"
    elif advertised and token_param:
        decision="GET_METADATA_AUTHENTICATED_AND_CATALOG_COMPATIBILITY_ADVISORY_ONLY"
    else:
        decision="PUBLIC_OPENAI_STRICT_WIRE_MATCH_NOT_ESTABLISHED"
    result={
        "checkpoint":"V3-65",
        "checked_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "historical_run_id":38502942783,
        "historical_inference_post_attempts":1,
        "historical_post_exception":"HTTPError",
        "historical_post_http_code":"NOT_CAPTURED_CANNOT_RECOVER",
        "historical_post_error_body":"NOT_CAPTURED_CANNOT_RECOVER",
        "historical_root_cause":"UNDETERMINED",
        "historical_request_sha256":sha256(raw).hexdigest(),
        "model":MODEL,
        "public_endpoint_catalog":{
            "state":cat["state"],
            "http_status":cat["http_status"] if cat["http_status"] in SAFE_HTTP else "UNVERIFIED",
            "matched_model_id":cat["model_id_matched"],
            "endpoint_count":cat["endpoint_count"],
            "structured_json_advertised_endpoint_count":cat["schema_advertised_count"],
            "structured_json_and_max_tokens_advertised_count":cat["schema_and_max_tokens_count"],
            "OpenAI_advertises_structured_json":bool(advertised),
            "strict_json_schema_guaranteed":False},
        "key_metadata":{
            "state":auth["state"],
            "http_status":auth["http_status"] if auth["http_status"] in SAFE_HTTP else "UNVERIFIED",
            "authenticated":auth["key_authenticated"],
            "type":auth["key_type"],
            "free_tier":auth["free_tier"],
            "key_limit_remaining_category":auth["key_limit_remaining_state"],
            "expiry_category":auth["expiry_state"],
            "funded_account_credits_proven":False,
            "model_entitlement_proven":False},
        "frozen_V364_wire":{
            "model_id":MODEL,
            "provider_order":["OpenAI"],
            "strict_json_schema_requested":True,
            "max_tokens":2100,
            "temperature_parameter_present":False,
            "require_parameters":True,
            "fallback":False,
            "original_POST_not_repeated":True},
        "get_attempts":audit["get_requests_attempted"],
        "inference_posts":0,"retries":0,
        "raw_key_or_provider_response_persisted":False,
        "exact_account_balance_persisted":False,
        "historical_http_cause_proven":False,
        "model_exact_routing_proven":False,
        "decision":decision,
        "genuine_model_creativity":"NOT_TESTED",
        "human_quality":"UNRATED","learner_effect":"NOT_MEASURED",
        "production":"BLOCKED",
        "next_action":"Never rerun V3-64. New paid inference requires separate preregistration and user approval."}
    need(result["inference_posts"]==0 and
         result["historical_root_cause"]=="UNDETERMINED","NO_GO_BOUNDARY_CHANGED")
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    need(not args.output.exists(),"OUTPUT_EXISTS")
    data=diagnostic(key=os.getenv("OPENROUTER_API_KEY") or None)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print("V365_DECISION="+data["decision"])
    print("V365_PUBLIC_GET="+data["public_endpoint_catalog"]["http_status"])
    print("V365_KEY_STATE="+data["key_metadata"]["state"])
    print("V365_INFERENCE_POSTS=0")
if __name__=="__main__":
    main()
