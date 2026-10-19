#!/usr/bin/env python3
"""V3-27: six locked source attempts; one finite, generic math A/V candidate.

Never silently treat standalone renderer outputs or ABSTAIN as full lessons.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.multidomain_coverage import run_coverage

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",required=True,type=Path)
    a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=True)
    result=run_coverage(root=ROOT,output=a.output_dir)
    assert len(result["dev_topics"])==6
    assert result["full_end_to_end_count"]==0
    assert result["full_end_to_end_gate"]=="NO_GO_MULTI_DOMAIN"
    assert not result["used_paid_provider"]
    assert result["production"]=="BLOCKED"
    print("V3_27_RESEARCH_TO_RENDERER=PARTIAL_NOT_FULL_CROSS_DOMAIN",flush=True)
    print("V3_27_V3_16_CONFIRMATORY=UNTOUCHED",flush=True)

if __name__=="__main__":
    main()
