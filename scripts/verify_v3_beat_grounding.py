#!/usr/bin/env python3
"""V3-10 golden renderer-synthetic beat-to-pixel evidence, no provider calls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from learnflow_v3.beat_grounding import compile_binary_beat_manifest, verify_binary_beat_video
from learnflow_v3.sequence_renderer import SequenceRenderProfile, render_certified_binary_search_video
from scripts.verify_v3_binary_search_render import CASES,create_certified_demo_bundle


def generate_verified_case(*,directory:Path,case:str,profile:SequenceRenderProfile):
    values,target=CASES[case]
    bundle,trace=create_certified_demo_bundle(values=values,target=target)
    params={k:v for k,v in bundle.items() if k!="verified_trace_refs"}
    video=directory/f"grounded_{case}.mp4"
    renderer=render_certified_binary_search_video(
        trace=trace,**params,output_path=video,profile=profile,
    )
    manifest=compile_binary_beat_manifest(trace=trace,**params,profile=profile)
    evidence=verify_binary_beat_video(
        trace=trace,**params,manifest=manifest,
        video_evidence=renderer,video_path=video,profile=profile,
    )
    return bundle,trace,manifest,renderer,evidence,video


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",required=True,type=Path)
    parser.add_argument("--fps",type=int,default=12)
    parser.add_argument("--width",type=int,default=640)
    parser.add_argument("--height",type=int,default=360)
    parser.add_argument("--seconds-per-step",type=float,default=.75)
    a=parser.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=True)
    profile=SequenceRenderProfile(width=a.width,height=a.height,fps=a.fps,
                                 seconds_per_step=a.seconds_per_step)
    summary={}
    for case in ("duplicate","missing","empty"):
        _,_,manifest,renderer,evidence,_=generate_verified_case(
            directory=a.output_dir,case=case,profile=profile,
        )
        assert evidence.observable_coverage==1.0
        assert evidence.audio_sync_verified is False
        summary[case]={
            "grounding":evidence.model_dump(mode="json"),
            "manifest":manifest.model_dump(mode="json"),
            "renderer_sha256":renderer.video_sha256,
        }
        print(
            f"V3_10_GROUNDING=PASS case={case} beats={evidence.beat_count} "
            f"dynamic={evidence.dynamic_beat_count} "
            f"pixels={evidence.dynamic_beat_pass_count} "
            f"coverage={evidence.observable_coverage:.3f} "
            f"audio=UNMEASURED"
        )
    report={
        "status":"BOUNDED_RENDERER_SYNTHETIC_BEAT_PIXEL_PASS",
        "claim_scope":"ONLY_V3_06_CERTIFIED_BINARY_SEARCH_NO_AUDIO",
        "pixel_proof":"ACTUAL_DECODED_FRAME_ROI_ANCHORS",
        "audio_sync":"UNMEASURED",
        "independent_semantic_video_understanding":"UNMEASURED",
        "human_learning":"UNMEASURED",
        "cases":summary,
    }
    (a.output_dir/"v3_10_grounding_proof.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
    )
    print("V3_10_GOLDEN=PASS count=3")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
