#!/usr/bin/env python3
"""V3-08 golden MP4 fixture renderer: blackboard function graph and algebra."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from learnflow_v2.repair import compute_content_hash
from learnflow_v2.scenegraph import SceneGraph
from learnflow_v3.math_renderer import (
    EquationDerivation, EquationStep, FunctionGraph, GraphPoint, graph_source,
    draw_equation_frame, draw_function_frame,
    render_equation_derivation, render_function_graph,
)
from learnflow_v3.sequence_renderer import SequenceRenderProfile


def function_demo():
    coefficients=(-4,0,1)
    domain=(-2,2)
    graph=SceneGraph.model_validate({
        "scene_id":"v3-08-quadratic",
        "purpose":"DEMONSTRATE",
        "layout_intent":{"type":"ILLUSTRATION","reading_direction":"LEFT_TO_RIGHT"},
        "nodes":[{
            "id":"quadratic-curve","kind":"CHART","label":"Quadratic curve",
            "content":graph_source(coefficients,domain),
        }],
        "relations":[],
    })
    points=tuple(GraphPoint(point_id=f"point-{x+3}",x=x,y=x*x-4)
                 for x in range(-2,3))
    return graph,FunctionGraph(scenegraph_sha256=compute_content_hash(graph),
                               coefficients=coefficients,x_domain=domain,steps=points)


def equation_demo():
    steps=(
        EquationStep(step_id="factored",expression="(x+2)*(x+2)"),
        EquationStep(step_id="distributed",expression="x*x+2*x+2*x+4"),
        EquationStep(step_id="collected",expression="x**2+4*x+4"),
    )
    graph=SceneGraph.model_validate({
        "scene_id":"v3-08-equivalence",
        "purpose":"EXPLAIN",
        "layout_intent":{"type":"PROCESS","reading_direction":"TOP_TO_BOTTOM"},
        "nodes":[{"id":s.step_id,"kind":"EQUATION","label":s.step_id,
                  "content":s.expression} for s in steps],
        "relations":[
            {"id":"equiv-1","kind":"EQUIVALENT_TO","source":"factored","target":"distributed"},
            {"id":"equiv-2","kind":"EQUIVALENT_TO","source":"distributed","target":"collected"},
        ],
    })
    return graph,EquationDerivation(scenegraph_sha256=compute_content_hash(graph),steps=steps)


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--width",type=int,default=960)
    parser.add_argument("--height",type=int,default=540)
    parser.add_argument("--fps",type=int,default=18)
    parser.add_argument("--seconds-per-step",type=float,default=0.75)
    args=parser.parse_args()
    profile=SequenceRenderProfile(width=args.width,height=args.height,fps=args.fps,
                                  seconds_per_step=args.seconds_per_step)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    records={}
    for family,builder,renderer,drawer in (
        ("function_graph",function_demo,render_function_graph,draw_function_frame),
        ("equation_derivation",equation_demo,render_equation_derivation,draw_equation_frame),
    ):
        graph,spec=builder()
        out=args.output_dir/f"{family}.mp4"
        evidence=renderer(spec=spec,graph=graph,output_path=out,profile=profile)
        drawer(spec,graph,1,profile).save(args.output_dir/f"{family}.png")
        records[family]=evidence.model_dump(mode="json")
        print(f"V3_08_RENDER=PASS family={family} frames={evidence.frame_count} "
              f"bytes={evidence.video_bytes} "
              f"mae_max={max(evidence.decoded_frame_mae):.3f} "
              f"step_delta_min={min(evidence.semantic_roi_deltas):.3f} "
              f"motion_min={min(evidence.within_beat_motion_deltas):.3f}")
    (args.output_dir/"v3_08_render_evidence.json").write_text(
        json.dumps({"status":"OFFLINE_VERIFIED_NO_NARRATION_AUDIO",
                    "profile":profile.model_dump(mode="json"),
                    "cases":records},indent=2)+"\n",encoding="utf-8")
    print("V3_08_GOLDEN=PASS count=2")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
