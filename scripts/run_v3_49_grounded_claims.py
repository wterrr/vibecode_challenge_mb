#!/usr/bin/env python3
"""V3-49 three NEW ratio topics, offline host-native video + per-topic claims.

No provider requests, no model auth, no modified V3-48 fixed claim bank.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.grounded_fraction_claims import (
    VERSION,ORIGIN,FractionTopic,ground,verify,build,digest)
from learnflow_v3.semantic_visual_events import compile_manim
from learnflow_v3.creative_manim_runner import _audio,_docker_manim,_codec_and_pixel_gates,sha
from learnflow_v3.creative_evidence_gate import EvidenceRejected,inspect_candidate
from scripts.run_v3_44_semantic_counterfactual import deterministic_mux
from scripts.run_v3_47_pedagogical_storytelling import _semantic_frame_proofs,_yellow_count
from learnflow_v3.process_edge_visual_qa import _frame

PRE="benchmarks/learnflowbench/v3/v3_49_grounded_claims_preregister.json"
SOURCE_ORIGIN="V349_HOST_SYNTHETIC_NEW_RATIO_NOT_MODEL_AUTHORED"


def _run_case(root:Path,out:Path,row:dict):
    case=row["id"]
    if not case.startswith(("dev_","heldout_")):
        raise Blocked("V349_BAD_PREREGISTERED_CASE_ID")
    d=out/case
    d.mkdir()
    topic=FractionTopic(
      topic_id=case,numerator=row["source"][0],denominator=row["source"][1],
      factor=row["factor"],target_numerator=row["target"][0],
      target_denominator=row["target"][1])
    evidence=ground(topic)
    verify(evidence)
    evidence_path=d/"verified_topic_claims.json"
    evidence_path.write_text(evidence.model_dump_json(indent=2)+"\n")
    lesson,adapter,plan=build(evidence)
    typed_path=d/"host_derived_semantic_lesson.json"
    typed_path.write_text(lesson.model_dump_json(indent=2)+"\n")
    grammar_path=d/"host_derived_semantic_grammar.json"
    grammar_path.write_text(plan.model_dump_json(indent=2)+"\n")
    durations,beats,wav=_audio(d,lesson)
    py=d/"compiled_host_manim.py"
    code=compile_manim(lesson,durations,visual_quality=True,pedagogical_plan=plan)
    if any(x in code for x in ("__import__","eval(","exec(","subprocess","os.system")):
        raise Blocked("V349_UNSAFE_HOST_CODE")
    compile(code,"<v349 trusted host manim>","exec")
    py.write_text(code)
    manim,sandbox=_docker_manim(d,py)
    movie=d/"host_grounded_lesson.mp4"
    mux=deterministic_mux(manim,wav,movie,beats)
    media=_codec_and_pixel_gates(movie,beats)
    if media["frames"]!=sum(x["frames"] for x in beats):
        raise Blocked("V349_FRAME_AUDIO_NOT_EXACT")
    if media["max_decoded_sample_delta"]<=.9:
        raise Blocked("V349_STATIC_OUTPUT")
    fraction_cues=_semantic_frame_proofs(movie,adapter,beats)
    # Explicit decoded evidence that the numerical proof itself is ON SCREEN
    # in the third narrated beat; not merely present in the Manim source.
    proof_beat=beats[2]
    proof_frame=(sum(x["frames"] for x in beats[:2])+
                 round(proof_beat["frames"]*.55))
    decoded=_frame(movie,proof_frame)
    proof_pixels=_yellow_count(decoded,0.,-2.1,290,42)
    if proof_pixels<24:
        raise Blocked("V349_NUMERIC_PROOF_MISSING_FROM_H264")
    if len(fraction_cues["per_source_cell_yellow_guide_pixels"])!=topic.denominator:
        raise Blocked("V349_NOT_ALL_SOURCE_CELLS_DIVIDED")
    # Existing genuine source gate MUST reject this entirely synthetic output.
    (d/"v3_35_ablation_receipt.json").write_text(json.dumps({
       "checkpoint":"V3-35","model_plan_origin":SOURCE_ORIGIN,
       "status":"OFFLINE_HOST_FIXTURE_NOT_EDUCATIONAL_PASS",
       "manim_source_origin":"HOST_GROUNDED_FRACTION_COMPILER",
       "provider_requests":0},indent=2)+"\n")
    try:
        inspect_candidate(d)
    except EvidenceRejected as e:
        if str(e)!="NOT_REAL_MODEL_SCENE":
            raise Blocked("V349_EVIDENCE_GATE_UNEXPECTED_OUTCOME") from None
    else:
        raise Blocked("V349_SYNTHETIC_ACCEPTED_AS_GENUINE_MODEL")
    result={
      "case":case,"role":row["role"],"fraction":[topic.numerator,topic.denominator],
      "target":[topic.target_numerator,topic.target_denominator],
      "factor":topic.factor,
      "topic_sha256":evidence.source_sha256,
      "evidence_sha256":sha(evidence_path),
      "semantic_graph_sha256":sha(typed_path),
      "host_compiler_sha256":sha(py),
      "native_mp4_sha256":sha(movie),
      "claimed_local_roles":[x.claim_id for x in evidence.claims],
      "evidence_verified":True,"origin":SOURCE_ORIGIN,
      "video":media,"mux":mux,
      "semantic_cues":fraction_cues,
      "verified_numeric_proof_h264":{"frame":proof_frame,
                    "pixel_count":proof_pixels,"expected_expression":evidence.proof},
      "safety":sandbox,"provider_posts":0,
      "human_learning":"UNRATED","production":"BLOCKED"}
    (d/"grounded_case_receipt.json").write_text(json.dumps(result,indent=2)+"\n")
    return result


def run(root:Path,out:Path)->dict:
    reg=json.loads((root/PRE).read_text())
    if (reg["checkpoint"]!="V3-49" or
        reg["parent_sha"]!="ed201a4cd31c429a6a979e3b857716c8afe0fa0d" or
        reg["registration_kind"]!="PREREGISTRATION_BEFORE_IMPLEMENTATION" or
        len(reg["cases"])!=3 or
        reg["acceptance"]["zero_provider_requests"] is not True):
        raise Blocked("V349_PREREGISTRATION_DRIFT")
    if out.exists():
        raise Blocked("V349_OUTPUT_MUST_BE_FRESH")
    out.mkdir(parents=True)
    results=[_run_case(root,out,row) for row in reg["cases"]]
    if {x["case"] for x in results}!={r["id"] for r in reg["cases"]}:
        raise Blocked("V349_CASE_COVERAGE_DRIFT")
    status={"checkpoint":"V3-49","schema_version":VERSION,"claim_origin":ORIGIN,
      "status":"THREE_NATIVE_NEW_RATIO_TOPICS_HOST_GROUNDED_HUMAN_UNRATED",
      "source_preregister_sha256":sha(root/PRE),"cases":results,
      "new_topic_holdouts":[x["case"] for x in results if x["role"]=="heldout_new_topic"],
      "genuine_provider_scene":False,"model_http_posts":0,"model_authenticated_gets":0,
      "provider_support":"NOT_TESTED","six_domain_generalization":"NOT_CERTIFIED",
      "human_pedagogy":"UNRATED","word_level_alignment":"NOT_MEASURED",
      "legacy_fixed_claim_bank":"PRESERVED_NOT_MODIFIED",
      "production":"BLOCKED"}
    (out/"v3_49_native_grounded_receipt.json").write_text(json.dumps(status,indent=2)+"\n")
    print("V3_49=THREE_NATIVE_NEW_RATIOS_HOST_GROUNDED_PEDAGOGY_UNRATED",flush=True)
    return status


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    run(ROOT,args.output_dir)
