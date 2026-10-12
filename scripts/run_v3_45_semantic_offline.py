#!/usr/bin/env python3
"""V3-45 offline model-facing semantic JSON→host validation→Manim→MP4.

TWO local mock-source JSON fixtures, NEVER a GPT-6 Luna/Gemini/other model
response. Reuse the native V3-44 hardened deterministic frame mux, existing
Manim Docker isolation, physical espeak audio and decoded media QA gates.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_manim_runner import _audio,_docker_manim,_codec_and_pixel_gates,sha
from learnflow_v3.semantic_scene_wire import (
    VERSION,SYNTHETIC_ORIGIN,portable_semantic_schema,
    decode_model_facing_scene,compile_scene,
)
from learnflow_v3.semantic_scene_offline_fixtures import fixture_cases
from scripts.run_v3_44_semantic_counterfactual import deterministic_mux
from learnflow_v3.creative_evidence_gate import EvidenceRejected,inspect_candidate

PREREG="benchmarks/learnflowbench/v3/v3_45_semantic_scene_protocol_preregister.json"


def _read_prereg(root:Path)->dict:
    p=json.loads((root/PREREG).read_text())
    if not (p.get("checkpoint")=="V3-45"
            and p.get("preregistered_before_implementation") is True
            and p.get("parent_sha")=="734f212af4326e589674b1df9d1af152587ba9bd"
            and p.get("acceptance",{}).get("families_rendered_native_mp4")==2
            and p.get("acceptance",{}).get("model_http_requests")==0):
        raise Blocked("V345_PREREGISTRATION_DRIFT")
    return p


def run(root:Path,out:Path)->dict:
    p=_read_prereg(root)
    if not out.is_dir() or any(out.iterdir()):
        raise Blocked("V345_NONEMPTY_OUTPUT_DIRECTORY")
    schema=portable_semantic_schema()
    (out/"v3_45_provider_portable_semantic_schema.json").write_text(
        json.dumps(schema,indent=2)+"\n")
    cases=fixture_cases()
    if set(cases)!={x["fixture_id"] for x in p["frozen_topics"]}:
        raise Blocked("V345_FIXTURE_SELECTION_DRIFT")
    records=[]
    for fixture_id,raw in cases.items():
        dest=out/fixture_id
        dest.mkdir()
        # Persist exact authored JSON and explicit synthetic declaration;
        # never decorate it with simulated provider IDs, usage or model tags.
        (dest/"synthetic_model_facing_wire.json").write_text(
            json.dumps(raw,indent=2,ensure_ascii=False)+"\n")
        typed=decode_model_facing_scene(raw)
        if typed.family!=next(x["kind"] for x in p["frozen_topics"]
                              if x["fixture_id"]==fixture_id):
            raise Blocked("V345_FAMILY_SELECTION_DRIFT")
        durations,beats,wav=_audio(dest,typed)
        source=dest/"generated_host_manim.py"
        source.write_text(compile_scene(typed,durations),encoding="utf-8")
        raw_manim,sandbox=_docker_manim(dest,source)
        mp4=dest/"offline_host_semantic_with_audio.mp4"
        mux=deterministic_mux(raw_manim,wav,mp4,beats)
        video=_codec_and_pixel_gates(mp4,beats)
        if video["frames"]!=sum(b["frames"] for b in beats):
            raise Blocked("V345_EXACT_VOICE_FRAMES_REQUIRED")
        if video["max_decoded_sample_delta"]<=.9:
            raise Blocked("V345_STATIC_VIDEO_REJECTED")
        (dest/"v3_35_ablation_receipt.json").write_text(json.dumps({
          "checkpoint":"V3-35",
          "model_plan_origin":SYNTHETIC_ORIGIN,
          "status":"OFFLINE_HOST_FIXTURE_NOT_EDUCATIONAL_PASS",
          "manim_source_origin":"HOST_SAFE_SEMANTIC_COMPILER",
          "provider_requests":0
        },indent=2)+"\n")
        try:
            inspect_candidate(dest)
        except EvidenceRejected as exc:
            if str(exc)!="NOT_REAL_MODEL_SCENE":
                raise Blocked("V345_PROVENANCE_GATE_UNEXPECTED_REJECTION") from None
        else:
            raise Blocked("V345_SYNTHETIC_ACCEPTED_AS_GENUINE_MODEL")
        item={
            "fixture_id":fixture_id,"family":typed.family,
            "origin":SYNTHETIC_ORIGIN,
            "model_requests":0,
            "schema_and_host_validation":"PASS",
            "host_compiled_source_sha256":sha(source),
            "input_wire_sha256":sha(dest/"synthetic_model_facing_wire.json"),
            "output_video_sha256":sha(mp4),
            "mux":mux,"native_video":video,
            "sandbox":sandbox,"production":"BLOCKED",
            "word_alignment":"NOT_MEASURED",
            "pedagogical_learning_gain":"NOT_MEASURED",
        }
        (dest/"offline_case_receipt.json").write_text(json.dumps(item,indent=2)+"\n")
        records.append(item)
    report={"checkpoint":"V3-45",
            "status":"OFFLINE_TWO_FAMILY_NATIVE_PASS_NOT_REAL_MODEL_OUTPUT",
            "schema_version":VERSION,"schema_sha256":sha256(json.dumps(
                schema,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
            "origin":SYNTHETIC_ORIGIN,
            "cases":records,"num_native_videos":len(records),
            "model_http_posts":0,"model_authenticated_gets":0,
            "provider_support":"UNVERIFIED_WITHOUT_LIVE_PROVIDER_CALL",
            "schema_is_domain_general":"NO_ONLY_TWO_EXPLICIT_EVENT_FAMILIES",
            "human_quality":"NOT_ASSESSED",
            "no_static_card_fallback":True,
            "production":"BLOCKED"}
    (out/"v3_45_protocol_receipt.json").write_text(json.dumps(report,indent=2)+"\n")
    print("V3_45=OFFLINE_TWO_FAMILY_NATIVE_VIDEO_PASS_NOT_MODEL_PROOF")
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",required=True,type=Path)
    args=parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=False)
    try:
        run(ROOT,args.output_dir)
    except (Blocked,ValueError,KeyError,TypeError) as e:
        (args.output_dir/"v3_45_blocked.json").write_text(json.dumps({
            "status":"BLOCKED","error_class":type(e).__name__,
            "model_http_posts":0,"production":"BLOCKED"},indent=2)+"\n")
        print("V3_45=BLOCKED "+type(e).__name__)
        raise SystemExit(2) from None


if __name__=="__main__":
    main()
