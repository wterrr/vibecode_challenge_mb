#!/usr/bin/env python3
"""V3-53 three independently authored synthetic director plans → native Manim.

No model connection, no replay of V3-50 API trial. All mathematical assertions
are derived from host QKV ledger. Evidence is independently decoded from H264.
"""
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
from learnflow_v3.creative_motion_director import plan_for,validated,narration,compile_manim,VERSION,ORIGIN
from learnflow_v3.semantic_attention_motion import Case
from learnflow_v3.process_edge_visual_qa import _frame
from scripts.run_v3_44_semantic_counterfactual import deterministic_mux
from scripts.run_v3_52_semantic_motion import classify_colors

REG="benchmarks/learnflowbench/v3/v3_53_creative_director_preregister.json"


def manifest():
    m=json.loads((ROOT/REG).read_text())
    if not (m["checkpoint"]=="V3-53" and m["parent_sha"]=="2be42bdfe4d0c242b67e8bfed3bae4f4e19ec9ff"
            and m["preregistration"]=="BEFORE_IMPLEMENTATION" and
            m["acceptance"]["three_real_h264_aac"] and
            m["acceptance"]["no_provider_requests"] and len(m["preselected_fixtures"])==3):
        raise Blocked("V353_PREREGISTRATION_CHANGED")
    return m


def _case(row,folder:Path):
    folder.mkdir()
    q=tuple(row["query"])
    case=Case(topic_id=("query_matches_token_a" if q==(1,0) else "heldout_query_matches_token_b"),
              query=q,keys=((1,0),(0,1)),values=((1,0),(0,1)),dim=2)
    plan=plan_for(case,row["emphasis"],row["stages"])
    p,ev,g=validated(plan)
    (folder/"director_plan_host_synthetic.json").write_text(plan.model_dump_json(indent=2)+"\n")
    (folder/"v2_verified_graph.json").write_text(g.model_dump_json(indent=2)+"\n")
    (folder/"host_math_evidence.json").write_text(json.dumps(ev,indent=2)+"\n")
    durations,beats,wav=_audio(folder,narration(plan))
    source=folder/"trusted_composed_manim.py"
    source.write_text(compile_manim(plan,durations))
    raw,sandbox=_docker_manim(folder,source)
    output=folder/"composed_attention_native.mp4"
    mux=deterministic_mux(raw,wav,output,beats)
    qa=_codec_and_pixel_gates(output,beats)
    if qa["frames"]!=sum(b["frames"] for b in beats) or qa["frames"]!=mux["output_h264_frames"]:
        raise Blocked("V353_AUDIO_VIDEO_NOT_EXACT")
    ops=[b.op for b in plan.beats]
    start_transport=ops.index("transport")
    prior_idx=sum(b["frames"] for b in beats[:start_transport])-4
    after_idx=sum(b["frames"] for b in beats[:start_transport+1])-4
    if prior_idx<=0 or after_idx<=prior_idx or after_idx>=qa["frames"]:
        raise Blocked("V353_CAUSAL_NATIVE_FRAME_SELECTION_INVALID")
    before=classify_colors(_frame(output,prior_idx))
    after=classify_colors(_frame(output,after_idx))
    if before["total_causal_pixels"]>65 or min(after["teal_pixels"],after["amber_pixels"])<200:
        raise Blocked("V353_CAUSAL_WEIGHT_TRANSPORT_NOT_PRESENT")
    total=after["total_causal_pixels"]
    frac=after["teal_pixels"]/total
    if abs(frac-ev["weights"][0])>0.13:
        raise Blocked("V353_VISIBLE_CONTEXT_DISAGREES_WITH_CERTIFIED_WEIGHTS")
    third=min(qa["frames"]-2,max(1,round(.24*qa["frames"])))
    f0=_frame(output,third).astype("int16")
    f1=_frame(output,after_idx).astype("int16")
    semantic_diff=float(np.mean(np.abs(f0-f1)))
    if semantic_diff<2.0:
        raise Blocked("V353_NO_VISIBLE_STORY_BEAT_DIFFERENCE")
    receipt={
      "checkpoint":"V3-53","case":row["id"],"role":row["role"],
      "origin":ORIGIN,"version":VERSION,
      "model_http_posts":0,"genuine_model_authored":False,
      "plan_sha256":sha(folder/"director_plan_host_synthetic.json"),
      "arithmetic_evidence_sha256":digest(ev),
      "v2_scene_graph_sha256":sha(folder/"v2_verified_graph.json"),
      "compiled_source_sha256":sha(source),
      "native_video_sha256":sha(output),
      "stages":ops,"style":plan.story_style,
      "op_focus":[b.focus_ref for b in plan.beats],
      "weights":ev["weights"],"context":ev["context"],
      "native_media":qa,"mux":mux,
      "causal_frames":{"negative":prior_idx,"after_transport":after_idx},
      "causal_pixel_evidence":{"before":before,"after":after,
          "observed_teal_fraction":frac,"target_weight_a":ev["weights"][0]},
      "beat_frame_difference":semantic_diff,
      "sandbox":sandbox,"human_pedagogy":"UNRATED",
      "scope":"ONE_TOPIC_HOST_SYNTHETIC_ONLY",
      "production":"BLOCKED"}
    (folder/"creative_director_native_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    return receipt


def run(out:Path):
    r=manifest()
    if out.exists():raise Blocked("V353_FRESH_OUTPUT_REQUIRED")
    out.mkdir(parents=True)
    artifacts=[_case(entry,out/entry["id"]) for entry in r["preselected_fixtures"]]
    if not len({a["native_video_sha256"] for a in artifacts})==3:
        raise Blocked("V353_THREE_COMPOSITIONS_SAME_VIDEO")
    if len({tuple(x["stages"]) for x in artifacts})!=3 or len({x["style"] for x in artifacts})!=3:
        raise Blocked("V353_DIRECTOR_DID_NOT_COMPOSE_DIFFERENT_SCENES")
    dev,_,counter=artifacts
    if not(dev["weights"][0]>.5 and counter["weights"][0]<.5):
        raise Blocked("V353_MISSING_CAUSAL_Q_COUNTERFACTUAL")
    drift=abs(dev["causal_pixel_evidence"]["observed_teal_fraction"]-
              counter["causal_pixel_evidence"]["observed_teal_fraction"])
    if drift<r["acceptance"]["counterfactual_real_area_difference_at_least"]:
        raise Blocked("V353_NO_PHYSICAL_COUNTERFACTUAL")
    summary={"checkpoint":"V3-53",
       "status":"THREE_COMPOSED_NATIVE_HOST_DIRECTOR_PLANS_OFFLINE_TECHNICAL_PASS",
       "cases":artifacts,"counterfactual_pixel_fraction_delta":drift,
       "native_video_count":3,"model_http_posts":0,
       "real_model_plan_validated":False,"human_learning":"UNRATED",
       "future_model_freedom":"MODEL_FACING_TYPED_IR_UNTESTED_WITH_REAL_PROVIDER",
       "production":"BLOCKED"}
    (out/"v353_final_creative_director_receipt.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("V3_53=THREE_COMPOSABLE_CAUSAL_NATIVE_HOST_VIDEOS_PASS_HUMAN_UNRATED")
    return summary


if __name__=="__main__":
    args=argparse.ArgumentParser()
    args.add_argument("--output-dir",required=True,type=Path)
    parsed=args.parse_args()
    run(parsed.output_dir)
