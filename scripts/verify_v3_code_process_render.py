#!/usr/bin/env python3
"""V3-07 real MP4 golden generator, no LLM and no arbitrary code execution."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v2.repair import compute_content_hash
from learnflow_v2.scenegraph import SceneGraph
from learnflow_v3.code_process_renderer import (
    CodeLine, CodeStep, CodeWalkthrough, ProcessStep, ProcessWalkthrough,
    draw_code_frame, draw_process_frame, render_code_walkthrough, render_process_walkthrough,
)
from learnflow_v3.sequence_renderer import SequenceRenderProfile


def code_demo():
    lines=(
        CodeLine(line_id="init-low",source="low = 0"),
        CodeLine(line_id="init-high",source="high = 6"),
        CodeLine(line_id="find-mid",source="mid = (low + high) // 2"),
        CodeLine(line_id="shrink",source="high = mid - 1"),
    )
    graph=SceneGraph.model_validate({
        "scene_id":"code-demo","purpose":"DEMONSTRATE",
        "layout_intent":{"type":"GRID","reading_direction":"LEFT_TO_RIGHT"},
        "nodes":[{"id":"source","kind":"CODE","label":"Search bounds",
                  "content":"\n".join(line.source for line in lines)}],
        "relations":[],
    })
    steps=(
        CodeStep(line_id="init-low",variables={"low":0}),
        CodeStep(line_id="init-high",variables={"low":0,"high":6}),
        CodeStep(line_id="find-mid",variables={"low":0,"high":6,"mid":3}),
        CodeStep(line_id="shrink",variables={"low":0,"high":2,"mid":3}),
    )
    return graph,CodeWalkthrough(
        scenegraph_sha256=compute_content_hash(graph),lines=lines,steps=steps,
    )


def process_demo():
    graph=SceneGraph.model_validate({
        "scene_id":"process-demo","purpose":"DEMONSTRATE",
        "layout_intent":{"type":"PROCESS","reading_direction":"LEFT_TO_RIGHT"},
        "nodes":[
            {"id":"start","kind":"TEXT","label":"Input"},
            {"id":"valid","kind":"TEXT","label":"Valid"},
            {"id":"invalid","kind":"TEXT","label":"Invalid"},
            {"id":"finish","kind":"TEXT","label":"Result"},
        ],
        "relations":[
            {"id":"e1","source":"start","target":"valid","kind":"FLOW"},
            {"id":"e2","source":"start","target":"invalid","kind":"FLOW"},
            {"id":"e3","source":"valid","target":"finish","kind":"FLOW"},
            {"id":"e4","source":"invalid","target":"finish","kind":"FLOW"},
        ],
    })
    spec=ProcessWalkthrough(
        scenegraph_sha256=compute_content_hash(graph),
        steps=(
            ProcessStep(active_node_id="start"),
            ProcessStep(active_node_id="valid",via_edge_id="e1"),
            ProcessStep(active_node_id="finish",via_edge_id="e3"),
        ),
    )
    return graph,spec


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--width",type=int,default=960)
    p.add_argument("--height",type=int,default=540)
    p.add_argument("--fps",type=int,default=18)
    p.add_argument("--seconds-per-step",type=float,default=0.75)
    a=p.parse_args()
    prof=SequenceRenderProfile(width=a.width,height=a.height,fps=a.fps,
                                seconds_per_step=a.seconds_per_step)
    a.output_dir.mkdir(parents=True,exist_ok=True)
    metrics={}
    for family,builder,render,draw in (
        ("code",code_demo,render_code_walkthrough,draw_code_frame),
        ("process",process_demo,render_process_walkthrough,draw_process_frame),
    ):
        graph,spec=builder()
        out=a.output_dir/f"{family}_blackboard.mp4"
        evidence=render(spec=spec,graph=graph,output_path=out,profile=prof)
        draw(spec,graph,1,prof).save(a.output_dir/f"{family}_blackboard.png")
        metrics[family]=evidence.model_dump(mode="json")
        print(f"V3_07_RENDER=PASS family={family} frames={evidence.frame_count} "
              f"bytes={evidence.video_bytes} duration={evidence.duration_seconds:.2f}s "
              f"mae_max={max(evidence.decoded_mae):.3f} "
              f"delta_min={min(evidence.semantic_roi_delta):.3f} "
              f"wall={evidence.wall_seconds:.2f}")
    (a.output_dir/"v3_07_render_evidence.json").write_text(
        json.dumps({"status":"OFFLINE_VERIFIED","cases":metrics,
                    "profile":prof.model_dump(mode="json")},indent=2)+"\n",
        encoding="utf-8",
    )
    print("V3_07_GOLDEN=PASS count=2")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
