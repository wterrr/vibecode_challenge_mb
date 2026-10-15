#!/usr/bin/env python3
"""V3-84 preregistered spatial pedagogical composition native replay, opt-in."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_manim_runner import (
    _audio,_docker_manim,_codec_and_pixel_gates,sha
)
from learnflow_v3.v381_finite_manim_compiler import source
from learnflow_v3.v381_generic_semantic_operators import need
from learnflow_v3.v382_query_evidence_bridge import compile_question,registered
from scripts.run_v3_44_semantic_counterfactual import deterministic_mux
from learnflow_v3.v384_native_composition_gate import native_three_phase
from learnflow_v3.v384_pedagogical_scene_composer import plan
from learnflow_v3.v383_semantic_unit_storytelling import receipts


def run(out:Path):
    p=registered(ROOT)
    need(not out.exists(),"NEW_VERSIONED_ARTIFACT_OUTPUT_REQUIRED")
    out.mkdir(parents=True)
    cases=[]
    for row in p["cases"]:
        result=compile_question(row,ROOT)
        folder=out/row["id"]
        folder.mkdir()
        if result["status"]=="ABSTAIN":
            (folder/"abstain_receipt.json").write_text(json.dumps(result,indent=2)+"\n")
            cases.append(result)
            continue
        trace=result["trace"]
        (folder/"source_grounded_contracts.json").write_text(
            json.dumps(result["contracts"],indent=2)+"\n")
        (folder/"generated_operation_plan.json").write_text(
            json.dumps(result["generated_plan"],indent=2)+"\n")
        (folder/"query_to_exact_operator_trace.json").write_text(
            json.dumps(trace,indent=2)+"\n")
        story=SimpleNamespace(beats=[
            SimpleNamespace(narration=e["narration"],claim_ids=[e["claim_id"]])
            for e in trace["events"]])
        durations,beats,wav=_audio(folder,story)
        host_source=source(trace,durations,no_upscale_text=True,pedagogical_composition=True)
        path=folder/"v384_pedagogical_scene_manim.py"
        path.write_text(host_source)
        silent,sandbox=_docker_manim(folder,path)
        video=folder/"v384_composed_lesson_native.mp4"
        mux=deterministic_mux(silent,wav,video,beats)
        need(0<=mux["raw_manim_frames"]-mux["output_h264_frames"]<=3,
             "SOURCE_COMPILER_MUX_FRAME_DRIFT")
        av=_codec_and_pixel_gates(video,beats)
        need(av["frames"]==mux["output_h264_frames"]==sum(x["frames"] for x in beats),
             "H264_AAC_AUDIO_FRAME_IDENTITY")
        pixels=native_three_phase(video,beats,trace)
        geometry=plan(trace)
        units=receipts(trace)
        decoded=subprocess.run(
            ["ffmpeg","-nostdin","-v","error","-xerror","-i",str(video),
             "-map","0:v:0","-f","null","-"],
            stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=180)
        need(decoded.returncode==0,"NOT_FULL_DECODED_NATIVE_MP4")
        case={
            "id":row["id"],"domain":row["domain"],"role":row["role"],
            "status":"BOUNDED_SOURCE_GROUNDED_NATIVE_TECHNICAL_PASS_ONLY",
            "original_question":row["question"],
            "original_question_sha256":sha256(row["question"].encode()).hexdigest(),
            "source_provenance":result["source_reference_kind"],
            "source_url":result["source_url"],
            "source_reference_sha256":result["source_sha256"],
            "generated_plan_sha256":result["generated_case_sha256"],
            "generated_operation_count":len(trace["events"]),
            "opt_in_physical_token_animation":True,
            "v384_opt_in_scene_composition":True,
            "query_operation_families":trace["native_operator_kinds"],
            "research_fact_pedagogy_script_vd_gates":"REUSED_TYPED_CONTRACTS",
            "mp4_sha256":sha(video),"mp4_frames":av["frames"],
            "codec":"H264/AAC","full_native_decode":"PASS",
            "physical_before_after":pixels,
            "semantic_unit_count_certificates":units,
            "semantic_scene_geometry":geometry,
            "three_phase_native_visual_evidence":pixels,
            "mux":mux,"sandbox":sandbox,
            "native_codec_and_pixel":av,"model_api_calls":0,
            "real_agent_generated":False,"human_visual_quality":"NOT_PASS",
            "production":"BLOCKED",
        }
        (folder/"native_result_receipt.json").write_text(json.dumps(case,indent=2)+"\n")
        cases.append(case)
    good=[x for x in cases if x["status"]=="BOUNDED_SOURCE_GROUNDED_NATIVE_TECHNICAL_PASS_ONLY"]
    no=[x for x in cases if x["status"]=="ABSTAIN"]
    need(len(good)==p["acceptance"]["native_positive_exact"]==3
         and len(no)==p["acceptance"]["negative_abstain_exact"]==2
         and sum(x["role"]=="heldout" for x in good)==1,
         "PRELOCKED_DENOMINATOR_REPLACED")
    need(all(len(x["physical_before_after"])==x["generated_operation_count"]
             for x in good),"MISSING_NATIVE_SEMANTIC_FRAME_WITNESS")
    summary={
        "checkpoint":"V3-84","status":"BOUNDED_STAGED_SCENE_COMPOSITION_NATIVE_TECHNICAL_GATE",
        "base_pr":118,"cases":cases,"source_supported_native":len(good),
        "abstained":len(no),"locked_denominator":len(p["cases"]),
        "heldout_native":sum(x["role"]=="heldout" for x in good),
        "model_api_requests":0,"original_queries_without_storyboards":True,
        "source_family_count":2,"live_research":"NOT_RUN",
        "native_unit_evidence":True,"independent_human_acceptance":"NOT_PASS",
        "scene_composition":"TOPIC_NEUTRAL_STAGED_EXACT_HOST_PICTORIAL",
        "semantic_source_review":"NOT_INDEPENDENTLY_VERIFIED",
        "autonomous_LLM_authoring":"NOT_TESTED",
        "six_domain_generalization":"NOT_PROVEN",
        "independent_human_visual_quality":"NOT_PASS",
        "learner_gain":"NOT_MEASURED","production":"BLOCKED",
    }
    (out/"v384_final_report.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k!="cases"},indent=2))
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",required=True,type=Path)
    run(parser.parse_args().output_dir)
