#!/usr/bin/env python3
"""V3-86 real-PCM-grounded pedagogical speech and chart phase alignment."""
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
from learnflow_v3.v385_affine_visual_semantics import role_contract
from learnflow_v3.v386_pedagogical_speech_contract import semantic_phases, align_real_wav
from learnflow_v3.v386_phased_affine_manim import finite_source
from learnflow_v3.v386_native_speech_visual_gate import verify_native_phases
from learnflow_v3.v381_generic_semantic_operators import need
from learnflow_v3.v382_query_evidence_bridge import compile_question,registered
from scripts.run_v3_44_semantic_counterfactual import deterministic_mux


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
        visual_role=role_contract(row,result)
        phases=semantic_phases(row,result,visual_role)
        (folder/"source_grounded_contracts.json").write_text(
            json.dumps(result["contracts"],indent=2)+"\n")
        (folder/"generated_operation_plan.json").write_text(
            json.dumps(result["generated_plan"],indent=2)+"\n")
        (folder/"query_to_exact_operator_trace.json").write_text(
            json.dumps(trace,indent=2)+"\n")
        story=SimpleNamespace(beats=[
            SimpleNamespace(narration=phase["narration"],claim_ids=[phase["claim_id"]])
            for phase in phases])
        durations,beats,wav=_audio(folder,story)
        pcm_receipts=align_real_wav(phases,beats)
        host_source=finite_source(trace,durations,visual_role,phases)
        path=folder/"v386_pcm_grounded_pedagogical_manim.py"
        path.write_text(host_source)
        silent,sandbox=_docker_manim(folder,path)
        video=folder/"v386_semantic_narration_native.mp4"
        mux=deterministic_mux(silent,wav,video,beats)
        need(0<=mux["raw_manim_frames"]-mux["output_h264_frames"]<=3,
             "SOURCE_COMPILER_MUX_FRAME_DRIFT")
        av=_codec_and_pixel_gates(video,beats)
        need(av["frames"]==mux["output_h264_frames"]==sum(x["frames"] for x in beats),
             "H264_AAC_AUDIO_FRAME_IDENTITY")
        pixels=verify_native_phases(video,beats,phases,trace,visual_role)
        geometry=visual_role
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
            "voiced_semantic_phase_count":len(phases),
            "opt_in_physical_token_animation":True,
            "v386_pcm_grounded_semantic_narration":True,
            "voice_phase_count":len(pcm_receipts),
            "voice_segments":pcm_receipts,
            "semantic_speech_plan":phases,
            "graph_representation_role":visual_role["role"],
            "graph_representation_interpretation":visual_role["interpretation"],
            "query_operation_families":trace["native_operator_kinds"],
            "research_fact_pedagogy_script_vd_gates":"REUSED_TYPED_CONTRACTS",
            "mp4_sha256":sha(video),"mp4_frames":av["frames"],
            "codec":"H264/AAC","full_native_decode":"PASS",
            "physical_before_after":pixels,
            "semantic_affine_role_receipt":geometry,
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
    need(all(len(x["physical_before_after"])==x["voiced_semantic_phase_count"]==6
             and len(x["voice_segments"])==6 for x in good),
         "MISSING_INDEPENDENT_VOICED_SEMANTIC_FRAME_WITNESS")
    summary={
        "checkpoint":"V3-86","status":"BOUNDED_PCM_GROUNDED_SEMANTIC_SPEECH_VISUAL_ENGINEERING_GATE",
        "base_pr":118,"cases":cases,"source_supported_native":len(good),
        "abstained":len(no),"locked_denominator":len(p["cases"]),
        "heldout_native":sum(x["role"]=="heldout" for x in good),
        "model_api_requests":0,"original_queries_without_storyboards":True,
        "source_family_count":2,"live_research":"NOT_RUN",
        "native_unit_evidence":True,"independent_human_acceptance":"NOT_PASS",
        "semantic_visual_family":"SOURCE_SCOPED_AFFINE_ROLE_NOT_MODEL_AUTONOMY",
        "timing_evidence":"ACTUAL_SIX_TTS_PCM_SEGMENTS_NOT_WORD_LEVEL_ASR",
        "semantic_source_review":"NOT_INDEPENDENTLY_VERIFIED",
        "autonomous_LLM_authoring":"NOT_TESTED",
        "six_domain_generalization":"NOT_PROVEN",
        "independent_human_visual_quality":"NOT_PASS",
        "learner_gain":"NOT_MEASURED","production":"BLOCKED",
    }
    (out/"v386_final_report.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k!="cases"},indent=2))
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",required=True,type=Path)
    run(parser.parse_args().output_dir)
