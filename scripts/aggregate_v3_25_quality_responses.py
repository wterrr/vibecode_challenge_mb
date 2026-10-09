#!/usr/bin/env python3
"""Fail-closed import of independently collected anonymous V3-25 submissions.

Never certifies human independence, informed consent or a 12-topic V3-16
experiment. Reports self-reported scores descriptively ONLY.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.independent_quality_pilot import inspect_submissions

def run(admin_manifest:Path,responses:Path,output:Path)->dict:
    m=json.loads(admin_manifest.read_text(encoding="utf-8"))
    if not responses.is_dir() or responses.is_symlink():
        raise ValueError("RESPONSE_DIR_MUST_BE_LOCAL_DIRECTORY")
    paths=sorted(responses.glob("*.json"))
    samples=[json.loads(x.read_text(encoding="utf-8")) for x in paths]
    report=inspect_submissions(admin_manifest=m,responses=samples)
    if output.exists():raise FileExistsError("NO_CLOBBER_EVALUATION_REPORT")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(f"V3_25_RESPONSES={len(paths)} state={report['state']}")
    print("V3_25_HUMAN_INDEPENDENCE=UNVERIFIED student_ready=BLOCKED production=BLOCKED")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--admin-manifest",required=True,type=Path)
    p.add_argument("--responses-dir",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    v=p.parse_args()
    run(v.admin_manifest,v.responses_dir,v.output)
