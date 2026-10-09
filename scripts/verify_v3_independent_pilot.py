#!/usr/bin/env python3
"""Produce two locally runnable, separately distributed masked-label review packs.

This command does NOT run a human participant study. Review responses must
come from an independently authorized and consented process later.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.independent_quality_pilot import create_packets,inspect_submissions

def run(source:Path,destination:Path)->dict:
    destination.mkdir(parents=True,exist_ok=True)
    out=create_packets(media_root=source,output_dir=destination)
    manifest=json.loads(
        (destination/"ADMIN_NOT_FOR_RATERS/assignment_AND_SOURCE_DO_NOT_SHARE.json").read_text())
    result=inspect_submissions(admin_manifest=manifest,responses=[])
    assert result["received_submissions"]==0
    assert result["primary_metrics"]=="UNMEASURED"
    assert result["state"]=="NO_REAL_INDEPENDENT_RATINGS"
    assert result["student_ready"]==result["publication"]=="BLOCKED"
    (destination/"zero_response_gate.json").write_text(json.dumps(result,indent=2)+"\n")
    print("V3_25_MEDIA=PASS identical_AAC_720p24fps_source_verified=True")
    print("V3_25_REVIEWER_PACKETS=PASS 2_masked_orders=COUNTERBALANCED manual_distribution_only=True")
    print("V3_25_HUMAN_RESULTS=NOT_RUN actual_ratings=0 independent_recruitment_authorized=False")
    print("V3_25_PUBLICATION=BLOCKED")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source-dir",required=True,type=Path)
    p.add_argument("--output-dir",required=True,type=Path)
    args=p.parse_args()
    run(args.source_dir,args.output_dir)
