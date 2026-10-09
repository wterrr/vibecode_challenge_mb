#!/usr/bin/env python3
"""V3-28 real evidence-backed offline Hermes/V3-09/VD→renderer compiler smoke."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.source_grounded_compiler import run
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    report=run(ROOT,args.output_dir)
    assert len(report["six_attempt_ledger"])==6
    assert report["full_six_domain_release_gate"]=="NO_GO"
    assert report["autonomous_research_script_director_end_to_end_count"]==0
    assert report["production"]=="BLOCKED"
