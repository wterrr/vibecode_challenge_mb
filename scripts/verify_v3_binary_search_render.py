#!/usr/bin/env python3
"""V3-06 offline rendered golden artifacts; no LLM, TTS or paid API.

Reuses existing V3-04 typed fixture construction for an isolated pilot.
All demo inputs/outputs are local and deterministic; no production fixture data
or V2 frozen benchmark is modified.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from learnflow_v3.binary_search_trace import (
    make_binary_search_trace, to_binary_search_state_ledger,
)
from learnflow_v3.sequence_renderer import (
    SequenceRenderProfile, draw_binary_search_frame, render_certified_binary_search_video,
)
from tests.v3.test_pattern_router import _fixture_worked

CASES = {
    "duplicate": ((1,3,5,7,9,12,12,14,18), 12),
    "missing": ((1,3,5,7,9,12,14,18), 11),
    "singleton": ((12,), 12),
    "empty": ((), 7),
    "boundary": ((-9,-4,0,2,2,10), -9),
}


def create_certified_demo_bundle(*, values:tuple[int,...], target:int):
    """One beat per trace step, including an explicit terminal beat."""
    bundle=_fixture_worked(steps=1,budget=6)
    trace=make_binary_search_trace(values=values,target=target,source_ref="trace:trace-01")
    wording=f"Binary search for {target} in [{', '.join(map(str,values))}]"
    plans=bundle["plan"].model_dump(mode="json")
    script=bundle["script"].model_dump(mode="json")
    segments=[]
    for i,step in enumerate(trace.steps):
        beat=dict(plans["beats"][0])
        beat["beat_id"]=f"beat-{i+1:02d}"
        beat["script_segment_ref"]=f"seg-{i+1:02d}"
        beat["expected_visible_state_change"]=(
            f"Compare midpoint at index {step.mid} and update inclusive bounds"
            if step.phase=="COMPARE" else None
        )
        beat["allowed_static_justification"]=(
            "Show certified terminal result" if step.phase=="COMPLETE" else None
        )
        if i==0: plans["beats"]=[]
        plans["beats"].append(beat)
        seg=dict(script["segments"][0])
        seg["segment_id"]=beat["script_segment_ref"]
        seg["spoken_text"]=wording + f". {step.action.replace('_',' ').lower()}."
        seg["subtitle_text"]=wording
        segments.append(seg)
    script["segments"]=segments
    pat=bundle["pattern"].model_dump(mode="json")
    pat["source_refs"]=[f"script:{s['segment_id']}" for s in segments]+["trace:trace-01"]
    sb=bundle["storyboard"].model_dump(mode="json")
    sb["scenes"][0]["script_segment_ids"]=[s["segment_id"] for s in segments]
    sb["scenes"][0]["visual_intent"]=wording
    bundle["plan"]=type(bundle["plan"]).model_validate(plans)
    bundle["script"]=type(bundle["script"]).model_validate(script)
    bundle["pattern"]=type(bundle["pattern"]).model_validate(pat)
    bundle["storyboard"]=type(bundle["storyboard"]).model_validate(sb)
    refs=tuple(b.beat_id for b in bundle["plan"].beats)
    bundle["ledger"]=to_binary_search_state_ledger(trace=trace,pattern=bundle["pattern"],beat_refs=refs)
    return bundle,trace


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",required=True,type=Path)
    ap.add_argument("--case",choices=("all",*CASES),default="all")
    ap.add_argument("--width",type=int,default=960)
    ap.add_argument("--height",type=int,default=540)
    ap.add_argument("--fps",type=int,default=18)
    ap.add_argument("--seconds-per-step",type=float,default=0.8)
    args=ap.parse_args()
    profile=SequenceRenderProfile(
        width=args.width,height=args.height,fps=args.fps,
        seconds_per_step=args.seconds_per_step,
    )
    output_dir=args.output_dir.resolve()
    output_dir.mkdir(parents=True,exist_ok=True)
    metrics={}
    for key,(values,target) in CASES.items():
        if args.case!="all" and args.case!=key:continue
        bundle,trace=create_certified_demo_bundle(values=values,target=target)
        out=output_dir/f"binary_search_{key}.mp4"
        evidence=render_certified_binary_search_video(
            trace=trace,**{k:v for k,v in bundle.items() if k!="verified_trace_refs"},
            output_path=out,profile=profile,
        )
        image=draw_binary_search_frame(
            trace=trace,step_index=0,progress=1.0,
            subtitle=bundle["script"].segments[0].spoken_text,profile=profile,
        )
        image.save(output_dir/f"binary_search_{key}_poster.png")
        metrics[key]=evidence.model_dump(mode="json")
        print(f"V3_06_RENDER=PASS case={key} steps={len(trace.steps)} "
              f"frames={evidence.frame_count} bytes={evidence.video_bytes} "
              f"duration={evidence.duration_seconds:.2f}s "
              f"max_anchor_mae={max(evidence.decoded_anchor_mae):.2f} "
              f"min_step_delta={min(evidence.decoded_step_deltas,default=-1):.2f} "
              f"wall_seconds={evidence.render_wall_seconds:.2f}")
    (output_dir/"v3_06_render_evidence.json").write_text(
        json.dumps({"status":"OFFLINE_VERIFIED","profile":profile.model_dump(mode="json"),
                    "cases":metrics},indent=2)+"\n",encoding="utf-8")
    print("V3_06_GOLDEN=PASS count="+str(len(metrics)))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
