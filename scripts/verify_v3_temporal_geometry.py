#!/usr/bin/env python3
"""V3-11 deterministic keyframe geometry demo; actual H264 + saved proof."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v3.temporal_geometry import TemporalLayoutPlan,certify_temporal_layout
from learnflow_v3.temporal_demo_renderer import render_certified_temporal_demo,verify_temporal_render


def demo_layout()->TemporalLayoutPlan:
    return TemporalLayoutPlan(
        layout_id="v3-11-two-moving-objects-and-subtitle",
        source_ref="fixture:v3-11-safe-timeline",
        width=640,height=360,fps=12,frame_count=49,
        edge_inset=10,subtitle_band={"x":35,"y":294,"width":570,"height":54},
        max_pixels_per_frame=24,max_simultaneously_moving=2,
        tracks=(
            {"object_id":"title","role":"TITLE","kind":"TEXT","keyframes":(
                {"frame":0,"box":{"x":50,"y":30,"width":540,"height":50},
                 "text":"TEMPORAL GEOMETRY","font_px":28},
                {"frame":48,"box":{"x":50,"y":30,"width":540,"height":50},
                 "text":"TEMPORAL GEOMETRY","font_px":28})},
            {"object_id":"left-explanation","role":"CONTENT","kind":"RECT",
             "interpolation":"LINEAR","keyframes":(
                {"frame":0,"box":{"x":65,"y":132,"width":140,"height":54}},
                {"frame":48,"box":{"x":265,"y":132,"width":140,"height":54}})},
            {"object_id":"right-explanation","role":"CONTENT","kind":"RECT",
             "interpolation":"SMOOTHSTEP","keyframes":(
                {"frame":0,"box":{"x":420,"y":212,"width":140,"height":54}},
                {"frame":48,"box":{"x":350,"y":212,"width":140,"height":54}})},
            {"object_id":"subtitle","role":"CAPTION","kind":"TEXT","keyframes":(
                {"frame":0,"box":{"x":60,"y":306,"width":520,"height":36},
                 "text":"Source-certified motion avoids the subtitle band.","font_px":18},
                {"frame":48,"box":{"x":60,"y":306,"width":520,"height":36},
                 "text":"Source-certified motion avoids the subtitle band.","font_px":18})},
        ),
    )


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",required=True,type=Path)
    args=parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    plan=demo_layout()
    certificate=certify_temporal_layout(plan)
    path=args.output_dir/"temporal_geometry_safe.mp4"
    render=render_certified_temporal_demo(
        plan=plan,certificate=certificate,output_path=path,
    )
    verify_temporal_render(plan=plan,certificate=certificate,
                           evidence=render,video_path=path)
    result={
        "status":"BOUNDED_SWEPT_TEMPORAL_GEOMETRY_AND_DECODED_VIDEO_PASS",
        "scope":"PROJECT_OWNED_KEYFRAME_DEMO_ONLY",
        "geometry":certificate.model_dump(mode="json"),
        "render":render.model_dump(mode="json"),
        "real_audio_alignment":"UNMEASURED",
        "production_renderer_geometry_integration":"NOT_IMPLEMENTED",
        "nonlinear_uncertain_intervals":"FAIL_CLOSED",
        "code_process_math_coverage":"UNMEASURED",
        "human_comprehension":"UNMEASURED",
    }
    (args.output_dir/"temporal_geometry_evidence.json").write_text(
        json.dumps(result,indent=2)+"\n",encoding="utf-8",
    )
    print(
        f"V3_11_TEMPORAL_GEOMETRY=PASS frames={plan.frame_count} "
        f"analytic={certificate.analytic_pair_segments} "
        f"adaptive={certificate.conservative_pair_subdivisions} "
        f"text_checks={certificate.checked_text_bounds} "
        f"video_bytes={render.video_bytes} "
        f"max_anchor_mae={max(render.decoded_anchor_mae):.3f} "
        f"audio=UNMEASURED"
    )


if __name__=="__main__":
    main()
