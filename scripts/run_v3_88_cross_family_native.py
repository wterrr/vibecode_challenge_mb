#!/usr/bin/env python3
"""V3-88 offline proof-of-transfer from non-affine host-verified questions to MP4."""
from __future__ import annotations
import argparse,csv,json,subprocess,sys
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v3.creative_manim_runner import _audio,_docker_manim,_codec_and_pixel_gates,sha
from learnflow_v3.v388_cross_family_planner import registered,compile_case,check
from learnflow_v3.v388_cross_family_manim import finite_source
from learnflow_v3.v388_native_cross_family_gate import verify_native
from scripts.run_v3_44_semantic_counterfactual import deterministic_mux

FILENAME="v388_native_cross_family.mp4"


def run(out:Path):
    manifest=registered(ROOT)
    check(not out.exists(),"OUTPUT_DIRECTORY_MUST_BE_NEW_AND_VERSIONED")
    out.mkdir(parents=True)
    receipts=[]
    for row in manifest["cases"]:
        pre=compile_case(row)
        folder=out/row["id"]
        folder.mkdir()
        if pre["status"]=="ABSTAIN":
            check(row["role"]=="negative","SUPPORTED_PREREG_NATIVE_CASE_UNEXPECTEDLY_ABSTAINED")
            receipt={**pre,"role":row["role"],"model_api_requests":0,
                     "production":"BLOCKED"}
            (folder/"abstain_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
            receipts.append(receipt)
            continue
        check(row["role"] in ("development","heldout"),
              "NEGATIVE_CASE_SILENTLY_REPLACED_WITH_NATIVE_RENDER")
        plan=pre["plan"]
        check(len(plan["scripted_semantic_events"])>=3 and
              plan["family"] in manifest["acceptance"]["semantic_families"],
              "FROZEN_CROSS_FAMILY_SEMANTIC_PLAN_MISSING")
        (folder/"host_verified_evidence.json").write_text(json.dumps(plan,indent=2)+"\n")
        story=SimpleNamespace(beats=[
            SimpleNamespace(narration=e["narration"],claim_ids=e["claim_ids"])
            for e in plan["scripted_semantic_events"]
        ])
        durations,beats,wav=_audio(folder,story)
        source=finite_source(row,plan,durations)
        src=folder/"v388_host_trusted_manim.py"
        src.write_text(source)
        silent,sandbox=_docker_manim(folder,src)
        movie=folder/FILENAME
        mux=deterministic_mux(silent,wav,movie,beats)
        check(0<=mux["raw_manim_frames"]-mux["output_h264_frames"]<=3,
              "UNBOUNDED_MANIM_PCM_FRAME_DRIFT")
        av=_codec_and_pixel_gates(movie,beats)
        check(av["frames"]==sum(e["frames"] for e in beats)==mux["output_h264_frames"],
              "H264_AAC_VOICE_FRAMES_NOT_EXACT")
        visual=verify_native(movie,beats,plan)
        decoded=subprocess.run(
            ["ffmpeg","-nostdin","-v","error","-xerror","-i",str(movie),
             "-map","0:v:0","-f","null","-"],
            stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=180)
        check(decoded.returncode==0,"FULL_H264_DECODE_FAILED")
        receipt={
            "id":row["id"],"family":row["family"],"role":row["role"],
            "status":"BOUNDED_HOST_SEMANTIC_NATIVE_TECHNICAL_PASS_ONLY",
            "question":row["question"],"question_sha256":sha256(row["question"].encode()).hexdigest(),
            "semantic_plan_origin":plan["origin"],
            "source_semantic_sha256":plan["source_semantic_proof_sha256"],
            "visual_operator":plan["visual_operator"],
            "source_scoped_host_verification":"PASS",
            "semantic_event_count":len(plan["scripted_semantic_events"]),
            "wav_utterance_count":len(beats),
            "real_wav_derived_voice_segments":beats,
            "physical_semantic_H264_witnesses":visual,
            "native_codec_pixel_gate":av,"native_audio_mux":mux,
            "native_mp4_frames":av["frames"],"native_mp4_sha256":sha(movie),
            "codec":"H264/AAC","full_native_decode":"PASS",
            "manim_sandbox":sandbox,"model_api_requests":0,
            "source_curated_host_not_live_researched":True,
            "visual_quality_human_review":"NOT_PASS",
            "learner_gain":"NOT_MEASURED","production":"BLOCKED",
        }
        (folder/"native_result_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
        receipts.append(receipt)
    pos=[x for x in receipts if x["status"]=="BOUNDED_HOST_SEMANTIC_NATIVE_TECHNICAL_PASS_ONLY"]
    no=[x for x in receipts if x["status"]=="ABSTAIN"]
    expected=manifest["acceptance"]
    check(len(receipts)==expected["locked_denominator"]==8 and
          len(pos)==expected["native_exact"]==4 and
          len(no)==expected["abstain_exact"]==4 and
          sum(x["role"]=="heldout" for x in pos)==expected["heldout_exact"]==2 and
          set(x["family"] for x in pos)==set(expected["semantic_families"]),
          "FROZEN_CROSS_FAMILY_DENOMINATOR_OR_HELDOUT_REPLACED")
    # Empty quality questionnaire: NEVER infer/blind-label a human response.
    with (out/"independent_masked_quality_rubric_UNRATED.csv").open("w",newline="") as stream:
        writer=csv.writer(stream)
        writer.writerow(["masked_clip","semantic_correctness_1to5",
                         "causal_continuity_1to5","readable_layout_1to5",
                         "narration_visual_timing_1to5","pedagogical_usefulness_1to5",
                         "reviewer_id","review_notes"])
        for index,_ in enumerate(pos):
            writer.writerow([f"BLINDED_CLIP_{index+1:02d}"]+[""]*7)
    summary={
        "checkpoint":"V3-88","status":"BOUNDED_TWO_NEW_NON_AFFINE_NATIVE_FAMILIES_TECHNICAL_GATE",
        "parent_pr":124,"case_count":len(receipts),"native_pass":len(pos),
        "negative_abstain":len(no),"heldout_pass":2,
        "verified_families":sorted({x["family"] for x in pos}),
        "cases":receipts,"model_api_requests":0,
        "older_affine_baseline":"PR_124_FROZEN_NOT_REGENERATED",
        "new_research_sources":"NONE_HISTORICAL_HOST_ONLY",
        "autonomous_model_planning":"NOT_TESTED",
        "six_domain_generalization":"NOT_PROVEN",
        "quality_rubric":"EMPTY_UNRATED_NO_REVIEWERS",
        "independent_human_visual_quality":"NOT_PASS",
        "learner_gain":"NOT_MEASURED",
        "production":"BLOCKED"
    }
    (out/"v388_final_report.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k!="cases"},indent=2))
    return summary


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",required=True,type=Path)
    run(p.parse_args().output_dir)
