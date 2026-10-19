#!/usr/bin/env python3
"""V3-31 offline only: replay V3-30 actual model receipt."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from learnflow_v3.cs_code_state_lesson import render_v331
def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",required=True,type=Path)
    args=parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=False)
    result=render_v331(ROOT,ROOT/"reports"/"v3_31_v330_real_receipt_subset.json",args.output_dir)
    print("V3_31_OFFLINE="+result["status"],flush=True)
    print("V3_31_PROVIDER_CALLS="+str(result["v331_provider_requests"]),flush=True)
    print("V3_31_PRODUCTION="+result["production"],flush=True)
    return 0
if __name__=="__main__":
    raise SystemExit(main())
