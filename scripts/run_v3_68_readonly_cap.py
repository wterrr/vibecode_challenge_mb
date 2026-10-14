#!/usr/bin/env python3
"""V3-68: one GET /key from pre-existing inference secret, no other provider IO."""
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.v368_key_cap_readonly import inspect_metadata,Refused
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    if a.output.exists():raise Refused("V368_OUTPUT_EXISTS")
    x=inspect_metadata(key=os.getenv("OPENROUTER_API_KEY") or None)
    assert x["model_http_post_attempts"]==0 and x["provider_metadata_get_attempts"]<=1
    assert x["may_issue_model_http_post"] is False
    assert x["production"]=="BLOCKED"
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("V368_READONLY_RESULT="+x["scientific_verdict"])
    print("V368_KEY_STATUS="+x["current_key_metadata_http_status"])
    print("V368_BUDGET_POLICY="+x["budget_gate_result"])
    print("V368_INFERENCE_POSTS=0")
if __name__=="__main__":main()
