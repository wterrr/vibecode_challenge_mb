#!/usr/bin/env python3
"""V3-67 zero-network, deny-by-default corrected-wire budget receipt."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from learnflow_v3.v367_corrected_wire_budget import registered_report,BudgetBlocked

REG=ROOT/"benchmarks/learnflowbench/v3/v3_67_corrected_provider_budget_preregister.json"

def run(out:Path)->dict:
    if out.exists():raise BudgetBlocked("V367_OUTPUT_ALREADY_EXISTS")
    r=registered_report(REG)
    assert r["preflight_result"]=="DENY_NO_AUTHENTICATED_KEY_SNAPSHOT"
    assert r["can_authorize_paid_POST"] is False
    assert r["new_model_inference_posts"]==r["new_provider_gets"]==0
    assert r["original_v364_request_sha256"]!=r["corrected_request_sha256"]
    assert r["provider_allow_fallbacks"] is False
    assert r["usd_budget_frozen"]=="0.02"
    assert r["production"]=="BLOCKED"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("V367_NEW_REQUEST_WIRE_CORRECTED_OFFLINE")
    print("V367_LIFETIME_PROVIDER_USD_HARD_CAP_MISSING_DENY")
    print("V367_OLD_V364_SHA_PRESERVED")
    print("V367_INFERENCE_GET_MANAGEMENT_REQUESTS=0")
    return r

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    run(args.output)
