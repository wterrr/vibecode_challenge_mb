#!/usr/bin/env python3
"""V3-34 conservative offline or ONE model call, then sandboxed Manim media."""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.creative_manim_runner import run
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=["offline-smoke","live-model","live-structured"],required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=False)
    try:
        r=run(ROOT,args.output_dir,mode=args.mode,key=os.getenv("OPENROUTER_API_KEY",""))
        assert r["production"]=="BLOCKED"
        assert r["provider_requests"]==(0 if args.mode=="offline-smoke" else 1)
    except Exception as exc:
        # No model text or key copied into CI. One live request may already
        # have been billed; do not claim no cost on failed attempts.
        fail={"checkpoint":"V3-34","status":"BLOCKED",
              "mode":args.mode,"error_type":type(exc).__name__,
              "error_code":str(exc) if str(exc).startswith("V334_") else "V334_VALIDATION_OR_RUNTIME_BLOCKED",
              "model_request_attempt_limit":0 if args.mode=="offline-smoke" else 1,
              "actual_provider_request_count_if_failed":"NOT_VERIFIABLE",
              "production":"BLOCKED"}
        (args.output_dir/"v3_34_failure.json").write_text(json.dumps(fail,indent=2)+"\n")
        print("V3_34="+fail["status"]+" code="+fail["error_code"],flush=True)
        raise SystemExit(2) from None
if __name__=="__main__":main()
