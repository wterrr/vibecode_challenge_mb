#!/usr/bin/env python3
"""Generate ONLY static V3-66 diagnostic report; never query any provider."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.v366_provider_failure_observability import sanitized_report,ContractViolation
REG=ROOT/"benchmarks/learnflowbench/v3/v3_66_provider_failure_preregister.json"

def run(output:Path):
    r=json.loads(REG.read_text(encoding="utf-8"))
    assert r["checkpoint"]=="V3-66"
    assert r["registration"]=="FIRST_CHILD_COMMIT" and r["parent_pr"]==101
    assert r["parent_sha"]=="3dddad2dcaebbccf3df4c03d3bf5e52882b421be"
    assert r["request_policy"]["live_HTTP_calls"]==0
    assert r["request_policy"]["model_POST"]==0
    assert r["request_policy"]["GET_calls"]==0
    assert r["request_policy"]["never_modify_frozen_v364_request"] is True
    assert r["prior_evidence"]["historical_failure_cause"]=="UNDETERMINED"
    assert r["acceptance"]["zero_inference"] is True
    if output.exists():raise ContractViolation("V366_OUTPUT_ALREADY_EXISTS")
    packet=sanitized_report()
    assert packet["live_provider_gets"]==packet["live_model_posts"]==0
    assert packet["static_diagnostic"]["historical_root_cause"]=="UNDETERMINED_FROM_STATUS_ONLY"
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(packet,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("V366_STATIC_COMPATIBILITY_CAPTURE_READY_NO_HTTP")
    print("V366_LEGACY_ALLOW_FALLBACK_FIELD_FLAGGED")
    print("V366_V364_HISTORICAL_HTTP_CAUSE_UNDETERMINED")
    print("V366_PROVIDER_CALLS=0")
    return packet

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    opts=p.parse_args()
    run(opts.output)
