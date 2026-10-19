#!/usr/bin/env python3
"""V3-29 offline safety regression, real source verification, opt-in FREE live."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.independent_source_gate import fetch_textbook
from learnflow_v3.live_source_producer import run_one,ProviderBlocked
from learnflow_v3.source_grounded_compiler import SEED_FILE

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=["source-check","free-live"],required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    target=args.output_dir
    if any(target.iterdir()):
        raise ValueError("V3_29_TARGET_NOT_EMPTY")
    seeds=json.loads((ROOT/SEED_FILE).read_text())["cases"]
    if args.mode=="source-check":
        results=[]
        for seed in seeds:
            try:
                proof=fetch_textbook(seed)
            except Exception as exc:
                # Source down must NOT be certified.
                proof={"status":"SOURCE_NOT_VERIFIED",
                       "reason":type(exc).__name__,
                       "external_semantic_fact_review":"UNMEASURED"}
            results.append({"topic_id":seed["topic_id"],**proof})
        result={"mode":"INDEPENDENT_REAL_SOURCE_FETCH",
                "results":results,
                "source_anchor_pass_count":sum(x["status"].startswith("SOURCE_HTML_ANCHOR_VERIFIED")
                                               for x in results),
                "independent_semantic_fact_review":"UNMEASURED",
                "production":"BLOCKED"}
        (target/"v3_29_source_evidence.json").write_text(json.dumps(result,indent=2)+"\n")
        print(f"V3_29_SOURCE_FETCH={result['source_anchor_pass_count']}/2 "+
              "(not independent semantic review)",flush=True)
        return 0
    key=os.environ.get("OPENROUTER_API_KEY","").strip()
    model=os.environ.get("LEARNFLOW_V329_FREE_MODEL","nvidia/nemotron-3.5-lightning:free")
    if not key:
        receipt={"status":"NOT_RUN_NO_SECRET","source_model_generated":False,
                 "full_autonomous_lesson":"NO","production":"BLOCKED"}
        (target/"v3_29_live_witness_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
        print("V3_29_FREE_LIVE=NOT_RUN_NO_SECRET",flush=True)
        return 0
    try:
        result=run_one(root=ROOT,out=target,model=model,key=key)
    except Exception as exc:
        # Protect credentials/provider response. Retain reason code only;
        # even Python exception messages from network can contain secrets.
        receipt={"status":"BLOCKED_NO_LIVE_PASS",
                 "failure_type":type(exc).__name__,
                 "model":model,
                 "source_model_generated":False,
                 "full_autonomous_lesson":"NO","production":"BLOCKED"}
        (target/"v3_29_live_witness_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
        print("V3_29_FREE_LIVE=BLOCKED_NO_LIVE_PASS",flush=True)
        return 0
    print("V3_29_FREE_LIVE="+result["status"]+" model="+model,flush=True)
    return 0
if __name__=="__main__":
    raise SystemExit(main())
