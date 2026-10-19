"""V3-35 public non-inference endpoint capability diagnostic.

This probes only unauthenticated OpenRouter *catalog metadata* and never
submits a chat/completion, charges an inference request, reads a user secret
or claims authorization on behalf of a key. An endpoint catalogue snapshot
cannot resolve an earlier POST 404 after provider/account filtering.
"""
from __future__ import annotations

from datetime import datetime,timezone
import json
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

CATALOG_URL="https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints"
EXPECTED_MODEL="openai/gpt-6-luna"
REQUIRED_CAPABILITIES={"response_format","structured_outputs"}


def probe_public_catalog(*,sender=None)->dict:
    checked=datetime.now(timezone.utc).isoformat(timespec="seconds")
    base={"checkpoint":"V3-35","query_kind":"PUBLIC_METADATA_GET_ONLY",
          "model":EXPECTED_MODEL,"url":CATALOG_URL,
          "checked_at_utc":checked,"inference_requests":0,
          "api_key_used":False,"model_response_created":False,
          "historical_post_404_root_cause":"UNDETERMINED",
          "account_entitlement_tested":False,
          "region_or_workspace_guardrails_tested":False}
    req=Request(CATALOG_URL,headers={"Accept":"application/json"},method="GET")
    try:
        with (sender or urlopen)(req,timeout=10) as response:
            data=json.loads(response.read(900_000))
    except (HTTPError,URLError,TimeoutError,ValueError,UnicodeError,KeyError):
        return {**base,"catalog_status":"UNAVAILABLE_UNVERIFIED",
                "endpoints_total":None,"matching_endpoint_count":None,
                "evidence_interpretation":"Inconclusive; do not retry paid inference"}
    record=data.get("data") if isinstance(data,dict) else None
    if not isinstance(record,dict) or record.get("id")!=EXPECTED_MODEL:
        return {**base,"catalog_status":"RESPONSE_ID_MISMATCH",
                "endpoints_total":None,"matching_endpoint_count":None,
                "evidence_interpretation":"Untrusted metadata; do not retry"}
    endpoints=record.get("endpoints")
    if not isinstance(endpoints,list) or len(endpoints)>200:
        return {**base,"catalog_status":"MALFORMED_CATALOG_ENDPOINTS",
                "endpoints_total":None,"matching_endpoint_count":None,
                "evidence_interpretation":"Unverified"}
    matching=[]
    for endpoint in endpoints:
        if not isinstance(endpoint,dict):
            continue
        params=endpoint.get("supported_parameters")
        if not isinstance(params,list):
            continue
        if not REQUIRED_CAPABILITIES.issubset(set(p for p in params if isinstance(p,str))):
            continue
        matching.append({"provider_name":str(endpoint.get("provider_name",""))[:70],
                         "tag":str(endpoint.get("tag",""))[:80],
                         "status":endpoint.get("status") if isinstance(endpoint.get("status"),int) else None})
    return {**base,
            "catalog_status":"PUBLIC_MODEL_ENDPOINTS_ADVERTISE_STRUCTURED_OUTPUTS" if matching else "NO_PUBLIC_MATCHING_ENDPOINT",
            "endpoints_total":len(endpoints),
            "matching_endpoint_count":len(matching),
            "candidate_providers":matching,
            "evidence_interpretation":"Catalog support only. No authenticated account check; does not explain original POST HTTP 404."}


def main():
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    d=probe_public_catalog()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8")
    print("V3_35_PUBLIC_CATALOG="+d["catalog_status"],flush=True)
    print("V3_35_INFERENCE_REQUESTS=0",flush=True)


if __name__=="__main__":
    main()
