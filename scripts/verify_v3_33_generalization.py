#!/usr/bin/env python3
"""V3-33 unseen six and real prior-source control MP4 with 0 provider requests."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.unseen_domain_quality_audit import run
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    x=p.parse_args()
    x.output_dir.mkdir(parents=True,exist_ok=False)
    r=run(ROOT,x.output_dir)
    assert r["unseen"]["denominator"]==6 and r["unseen"]["abstain"]==6
    assert r["provider_requests"]==0 and r["production"]=="BLOCKED"
