#!/usr/bin/env python3
"""Bounded five-stage CS offline lesson from pinned certified publisher claims."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.grounded_lesson_video import render_offline
def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",type=Path,required=True)
    x=parser.parse_args()
    x.output_dir.mkdir(parents=True,exist_ok=False)
    r=render_offline(ROOT,x.output_dir)
    print("V3_32="+r["status"],flush=True)
    print("V3_32_PROVIDER_REQUESTS="+str(r["v332_provider_requests"]),flush=True)
    print("V3_32_PRODUCTION="+r["production"],flush=True)
    return 0
if __name__=="__main__":raise SystemExit(main())
