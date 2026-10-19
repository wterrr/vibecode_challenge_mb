#!/usr/bin/env python3
"""V3-23: score NO humans; produce actual-video-based review preflight."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from learnflow_v3.review_preflight import write_packet


def run(source_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True,exist_ok=True)
    result=write_packet(folder=source_dir,output=output_dir)
    r=result["report"];packet=result["packet"]
    assert r["machine_source_video_gate"]=="PASS"
    assert r["technical_readability_preflight"]=="NEEDS_REVIEW_SMALL_TEXT"
    assert r["learner_ready"]=="BLOCKED" and r["production_release"]=="BLOCKED"
    assert packet["human_participants"]==packet["rating_count"]==0
    assert packet["blind_comparison"].startswith("NOT_CLAIMED")
    print("V3_23_MEDIA=PASS actual_native_h264_aac_source_certified=True")
    print("V3_23_READABILITY=NEEDS_REVIEW_SMALL_TEXT derived_font_px="+str(r["microcopy_geometry"]["actual_os_computer_modern_font_px"]))
    print("V3_23_HUMAN_STUDY=NOT_RUN scores=0 blind_rct_claim=False")
    print("V3_23_RELEASE=BLOCKED")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-dir",required=True,type=Path)
    parser.add_argument("--output-dir",required=True,type=Path)
    args=parser.parse_args()
    run(args.source_dir,args.output_dir)
