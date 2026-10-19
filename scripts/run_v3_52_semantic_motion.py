#!/usr/bin/env python3
"""V3-52 native host-only causal Attention motion; no API credentials ever used."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

import numpy as np

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_manim_runner import _audio,_docker_manim,_codec_and_pixel_gates,sha
from learnflow_v3.creative_scene_graph import digest
from learnflow_v3.semantic_attention_motion import (
    VERSION,ORIGIN,Case,ground,check,narration,compile_manim,OP_SEQUENCE)
from learnflow_v3.process_edge_visual_qa import _frame
from scripts.run_v3_44_semantic_counterfactual import deterministic_mux

PRE="benchmarks/learnflowbench/v3/v3_52_semantic_motion_preregister.json"


def prereg():
    m=json.loads((ROOT/PRE).read_text())
    if not (
        m["checkpoint"]=="V3-52" and
        m["preregistered_before_implementation"] and
        m["parent_sha"]=="7da60601998529208cbc19f8189c373f0244cec2" and
        m["video_requirements"]["native_count"]==2 and
        m["safety"]["provider_requests"]==0 and
        len(m["cases"])==2):
        raise Blocked("V352_PREREGISTRATION_CHANGED")
    return m


def classify_colors(frame):
    """Counts only physically decoded output-segment pixels, never source text.

    Rectangles occupy ±2.5 world x, around world y=-2.16.
    At 1280x720 Manim mapping, x=[400,880], y=[533,576].
    """
    roi=frame[538:574,415:867,:3].astype("int16")
    red,green,blue=roi[:,:,0],roi[:,:,1],roi[:,:,2]
    teal=(green>150)&(blue>155)&(blue>red+22)&(red<175)
    amber=(red>172)&(green>119)&(blue<159)&(red>blue+65)
    return {"teal_pixels":int(teal.sum()),"amber_pixels":int(amber.sum()),
            "total_causal_pixels":int(teal.sum()+amber.sum())}


def pixel_gate(movie:Path,beat_info:list[dict],plan):
    required=sum(b["frames"] for b in beat_info)
    # before: end of NORMALIZE, weighted bars are at y=0 not yet in context.
    before_idx=sum(b["frames"] for b in beat_info[:2])-3
    # after: the value-weight transport operation has completed.
    after_idx=sum(b["frames"] for b in beat_info[:3])-3
    if not 0<before_idx<after_idx<required:
        raise Blocked("V352_BAD_REAL_FRAME_CUE_INDEX")
    prior=classify_colors(_frame(movie,before_idx))
    after=classify_colors(_frame(movie,after_idx))
    from learnflow_v3.semantic_attention_motion import facts
    weights=facts(plan.case)["weights"]
    if prior["total_causal_pixels"]>65:
        raise Blocked("V352_CONTEXT_PRESENT_BEFORE_CAUSAL_TRANSPORT")
    if (after["teal_pixels"]<200 or after["amber_pixels"]<200 or
        after["total_causal_pixels"]<900):
        raise Blocked("V352_WEIGHTED_TRANSPORT_NOT_VISIBLE_IN_H264")
    actual=after["teal_pixels"]/after["total_causal_pixels"]
    if abs(actual-weights[0])>.13:
        raise Blocked("V352_RENDERED_CONTEXT_RATIO_DISAGREES_WITH_MATH")
    return {"negative_frame":before_idx,"after_transport_frame":after_idx,
       "negative":prior,"after":after,
       "actual_teal_area_fraction":round(actual,6),
       "expected_weight_a":weights[0],
       "max_fraction_error_allowed":.13,
       "meaning":"PIXEL_AREA_EVIDENCE_OF_WEIGHTED_HOST_TRANSPORT_NOT_STUDENT_COMPREHENSION"}


def make_case(row,out:Path):
    out.mkdir()
    case=Case(topic_id=row["id"],query=tuple(row["query"]),
       keys=tuple(tuple(k) for k in row["keys"]),
       values=tuple(tuple(v) for v in row["values"]),
       dim=row["dim"])
    plan=ground(case)
    ev,graph=check(plan)
    (out/"verified_motion_plan.json").write_text(plan.model_dump_json(indent=2)+"\n")
    (out/"v2_motion_graph.json").write_text(graph.model_dump_json(indent=2)+"\n")
    (out/"verified_arithmetic.json").write_text(json.dumps(ev,indent=2)+"\n")
    durations,beats,wav=_audio(out,narration(plan))
    script=out/"host_compiled_semantic_motion.py"
    script.write_text(compile_manim(plan,durations))
    manim_source,sandbox=_docker_manim(out,script)
    mp4=out/"attention_semantic_motion.mp4"
    mux=deterministic_mux(manim_source,wav,mp4,beats)
    av=_codec_and_pixel_gates(mp4,beats)
    if av["frames"]!=mux["output_h264_frames"] or av["frames"]!=sum(b["frames"] for b in beats):
        raise Blocked("V352_AV_FRAME_COUNT_DIFFERENT_FROM_AUDIO")
    pixels=pixel_gate(mp4,beats,plan)
    receipt={
       "checkpoint":"V3-52","case":row["id"],"role":row["role"],
       "origin":ORIGIN,"model_post_count":0,
       "version":VERSION,
       "Q":ev["q"],"K":ev["keys"],"V":ev["values"],"d_k":ev["dk"],
       "score":ev["scaled_scores"],"softmax_weights":ev["weights"],
       "context":ev["context"],
       "motion_ops":list(OP_SEQUENCE),"claim_binding":["A2","A3","A4","A4"],
       "host_facts_sha256":digest(ev),"motion_plan_sha256":sha(out/"verified_motion_plan.json"),
       "native_video_sha256":sha(mp4),"manim_source_sha256":sha(script),
       "v2_scenegraph_sha256":sha(out/"v2_motion_graph.json"),
       "native_media":av,"exact_audio_mux":mux,
       "physical_motion":pixels,
       "sandbox":sandbox,"human_pedagogical_quality":"UNRATED",
       "model_authored":False,"production":"BLOCKED"}
    (out/"semantic_motion_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    return receipt


def run(out:Path):
    reg=prereg()
    if out.exists():raise Blocked("V352_FRESH_OUTPUT_REQUIRED")
    out.mkdir(parents=True)
    cases=[make_case(row,out/row["id"]) for row in reg["cases"]]
    if len(cases)!=2 or {x["case"] for x in cases}!={r["id"] for r in reg["cases"]}:
        raise Blocked("V352_PREREGISTERED_CASES_NOT_COMPLETE")
    left,right=cases
    if not(left["softmax_weights"][0]>left["softmax_weights"][1] and
           right["softmax_weights"][0]<right["softmax_weights"][1]):
        raise Blocked("V352_COUNTERFACTUAL_FLIP_MISSING")
    if not (left["context"][0]>left["context"][1] and
            right["context"][0]<right["context"][1]):
        raise Blocked("V352_CONTEXT_CAUSAL_FLIP_MISSING")
    if abs(left["physical_motion"]["actual_teal_area_fraction"]-
           right["physical_motion"]["actual_teal_area_fraction"])<reg[
               "video_requirements"]["minimum_counterfactual_weight_difference"]:
        raise Blocked("V352_PHYSICAL_AREA_COUNTERFACTUAL_DID_NOT_FLIP")
    if left["native_video_sha256"]==right["native_video_sha256"]:
        raise Blocked("V352_NATIVE_COUNTERFACTUAL_VIDEO_IDENTICAL")
    result={"checkpoint":"V3-52","status":"TWO_CAUSALLY_DISTINCT_NATIVE_HOST_MOTION_VIDEOS_TECHNICAL_PASS_ONLY",
       "cases":cases,"actual_model_calls":0,"real_model_result":False,
       "counterfactual_difference":abs(left["physical_motion"]["actual_teal_area_fraction"]-
            right["physical_motion"]["actual_teal_area_fraction"]),
       "domain_generalization":"NOT_CERTIFIED","human_learning":"UNRATED",
       "source_claims":"HOST_VERIFIED_NUMERICAL_ATTENTION_ONLY",
       "production":"BLOCKED"}
    (out/"v352_final_semantic_motion_receipt.json").write_text(json.dumps(result,indent=2)+"\n")
    print("V3_52=TWO_NATIVE_SEMANTIC_CAUSAL_MOTION_HOST_ONLY_PASS_HUMAN_UNRATED")
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",required=True,type=Path)
    args=p.parse_args()
    run(args.output_dir)
