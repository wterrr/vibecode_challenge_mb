#!/usr/bin/env python3
"""V3-44 host-authored semantic event counterfactual, using ORIGINAL narration.

Input must be SHA-frozen authentic V3-42 artifacts, but these NEW visuals
are host designed. This is NOT an LLM generated video / rerender of model
intent, and no HTTP POST or authenticated GET is performed here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_manim_runner import (
    _audio, _docker_manim, _codec_and_pixel_gates, _clock, sha,
)
from learnflow_v3.semantic_visual_events import (
    HOST_ORIGIN, create_counterfactual_from_real_scene, compile_manim,
    compiled_event_windows, verify_source_artifact,
)

REGISTRATION="benchmarks/learnflowbench/v3/v3_44_semantic_visual_redesign_preregister.json"


def run(root:Path,source:Path,out:Path)->dict:
    register=json.loads((root/REGISTRATION).read_text())
    if not (register.get("checkpoint")=="V3-44"
            and register.get("preregistered_before_implementation") is True
            and register.get("parent_pr")==77
            and register.get("parent_sha")=="cf6a813842e1d5928a7cefb6efe34ce190155252"
            and register.get("measured_gates",{}).get("model_http_posts")==0):
        raise Blocked("V344_PREREGISTRATION_DRIFT")
    if not out.is_dir() or any(out.iterdir()):
        raise Blocked("V344_OUTPUT_NONEMPTY")
    real=verify_source_artifact(source)
    lesson=create_counterfactual_from_real_scene(real)
    if [b.narration for b in lesson.beats]!=[b.narration for b in real.beats]:
        raise Blocked("V344_NARRATION_WAS_REWRITTEN")
    # The original model plan supplies ONLY the original narration/claims.
    # All new tiles/events are explicitly host-curated declarative inputs.
    (out/"v3_44_host_curated_plan.json").write_text(lesson.model_dump_json(indent=2)+"\n")
    durations,beats,wav=_audio(out,real)
    source_text=compile_manim(lesson,durations)
    manim_source=out/"v3_44_host_compiled_manim.py"
    manim_source.write_text(source_text,encoding="utf-8")
    manim_mp4,sandbox=_docker_manim(out,manim_source)
    video=out/"v3_44_host_counterfactual_with_audio.mp4"
    cmd=["ffmpeg","-nostdin","-hide_banner","-v","error","-y",
         "-i",str(manim_mp4),"-i",str(wav),
         "-map","0:v:0","-map","1:a:0",
         "-c:v","copy","-c:a","aac","-b:a","128k",
         "-shortest","-movflags","+faststart",str(video)]
    rv=subprocess.run(cmd,capture_output=True,timeout=100)
    if rv.returncode!=0 or not video.is_file():
        raise Blocked("V344_FFMPEG_NATIVE_MUX_FAILURE")
    qa=_codec_and_pixel_gates(video,beats)
    expected_frames=sum(b["frames"] for b in beats)
    if abs(qa["frames"]-expected_frames)>1:
        raise Blocked("V344_AUDIO_CLIPPED_OR_FRAME_COUNT_DRIFT")
    srt=out/"v3_44_original_narration_per_beat.srt"
    srt.write_text("\n".join(
        f"{i+1}\n{_clock(b['start_seconds'])} --> "
        f"{_clock(b['start_seconds'] + b['wav_samples']/b['wav_rate'])}\n"
        f"{b['narration']}\n" for i,b in enumerate(beats))+"\n",encoding="utf-8")
    events=compiled_event_windows(lesson,durations)
    timing={}
    for group in ("halves","quarters"):
        found=[e for e in events if e["kind"] in ("reveal_partition","morph_partition")
               and e["target"]==group]
        if len(found)!=1:
            raise Blocked("V344_MISSING_PARTITION_REVEAL")
        target=found[0]
        beatstart=next(b["start_seconds"] for b in beats if b["index"]+1==target["beat"])
        timing[group]=round(target["end_seconds"]-beatstart,3)
    if max(timing.values())>register["measured_gates"]["complete_partition_reveal_delay_seconds_max"]:
        raise Blocked("V344_PARTITION_LAG_NOT_FIXED")
    proof=next(e for e in events if e["kind"]=="show_label" and e["target"]=="proof")
    if proof["beat"]!=3:
        raise Blocked("V344_PROOF_NOT_VISIBLE_IN_ARITHMETIC_BEAT")
    tiles={x.id:x for x in lesson.tiles}
    groups={g.id:g for g in lesson.partitions}
    area=lambda gid:sum(tiles[x].width*tiles[x].height for x in groups[gid].part_ids)
    wholearea={"halves":area("halves"),"quarters":area("quarters")}
    diff=abs(wholearea["halves"]-wholearea["quarters"])/wholearea["quarters"]
    if diff>register["measured_gates"]["partition_whole_relative_area_diff_max"]:
        raise Blocked("V344_PARTITION_GEOMETRY_DRIFT")
    if not all(name in source_text for name in
               ("TransformFromCopy","LaggedStart","(1×2)/(2×2) = 2/4")):
        raise Blocked("V344_SEMANTIC_TRANSFORM_OR_PROOF_ABSENT")
    verdict={
        "checkpoint":"V3-44",
        "status":"OFFLINE_HOST_CURATED_NATIVE_COUNTERFACTUAL_PASS_NOT_MODEL_EDUCATIONAL_PASS",
        "model_plan_origin":HOST_ORIGIN,
        "input_model_scene_sha256":register["source"]["v342_model_response_sha256"],
        "input_original_video_sha256":register["source"]["v342_mp4_sha256"],
        "source_original_authorship":"REAL_MODEL_NARRATION_REUSED_UNMODIFIED",
        "new_graphics_and_semantic_event_authorship":"HOST_CURATED_NOT_GPT6",
        "no_second_model_http_posts":True,
        "provider_requests_this_checkpoint":0,
        "counterfactual_not_a_fair_model_A_B":True,
        "old_video_unchanged":True,
        "audio_alignment":"BEAT_RELATIVE_TIMING_NO_WORD_LEVEL_ASR",
        "partition_complete_lag_seconds":timing,
        "whole_rectangle_areas":wholearea,
        "relative_whole_area_difference":round(diff,5),
        "explicit_arithmetic_proof":"(1×2)/(2×2) = 2/4",
        "source_compiled_by_host_sha256":sha(manim_source),
        "event_count":len(events),
        "event_timeline":events,
        "video":qa,
        "sandbox":sandbox,
        "pedagogical_learning_gain":"NOT_MEASURED",
        "blinded_human_preference":"NOT_MEASURED",
        "genuine_new_model_scene":"NO",
        "production":"BLOCKED",
    }
    (out/"v3_44_semantic_redesign_receipt.json").write_text(
        json.dumps(verdict,indent=2)+"\n",encoding="utf-8")
    # Compatibility adapter solely for V3-36's mandatory anti-false-provenance
    # negative control. No sentence in this adapter claims REAL_MODEL origin.
    (out/"v3_35_ablation_receipt.json").write_text(json.dumps({
        "checkpoint":"V3-35","model_plan_origin":HOST_ORIGIN,
        "manim_source_origin":"HOST_CURATED_SEMANTIC_EVENT_COMPILER",
        "status":"TECHNICAL_SMOKE_NOT_EDUCATIONAL_PASS",
        "provider_requests":0,
        "production":"BLOCKED"
    },indent=2)+"\n")
    from learnflow_v3.creative_evidence_gate import EvidenceRejected,inspect_candidate
    try:
        inspect_candidate(out)
    except EvidenceRejected as exc:
        if str(exc)!="NOT_REAL_MODEL_SCENE":
            raise Blocked("V344_WRONG_MODEL_PROVENANCE_REJECTION") from None
    else:
        raise Blocked("V344_HOST_VIDEO_MISATTRIBUTED_TO_MODEL")
    print("V3_44=OFFLINE_HOST_CURATED_NATIVE_MP4_PASS_NOT_NEW_GPT6_MODEL",flush=True)
    return verdict


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-dir",required=True,type=Path)
    parser.add_argument("--output-dir",required=True,type=Path)
    opts=parser.parse_args()
    opts.output_dir.mkdir(parents=True,exist_ok=False)
    try:
        run(ROOT,opts.source_dir,opts.output_dir)
    except (Blocked,ValueError,KeyError) as exc:
        (opts.output_dir/"v3_44_failure.json").write_text(
            json.dumps({"status":"BLOCKED","exception_class":type(exc).__name__,
              "new_model_http_posts":0,"production":"BLOCKED"},indent=2)+"\n")
        print("V3_44=BLOCKED "+type(exc).__name__,flush=True)
        raise SystemExit(2) from None


if __name__=="__main__":
    main()
