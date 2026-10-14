#!/usr/bin/env python3
"""Offline mock model-candidate SceneGraph acceptance & real native video QA."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_manim_runner import _audio,_docker_manim,_codec_and_pixel_gates,sha
from learnflow_v3.creative_scene_graph import manim,audio_proxy,digest
from learnflow_v3.creative_scene_fixtures import fixtures
from learnflow_v3.creative_candidate_acceptance import (
    MOCK_ORIGIN,candidate_schema,mock_candidate_bytes,accept)
from learnflow_v3.creative_visual_quality_gate import inspect_native,distinguish
from scripts.run_v3_44_semantic_counterfactual import deterministic_mux

REGISTER="benchmarks/learnflowbench/v3/v3_54_model_candidate_quality_preregister.json"
NAMES={
    "mock_token_network":"tokens_as_network",
    "mock_score_comparison":"scores_as_comparison",
    "mock_symbolic_equivalence":"heldout_symbolic_rewrite"
}


def registered()->dict:
    r=json.loads((ROOT/REGISTER).read_text())
    if (r["checkpoint"]!="V3-54" or
        r["parent_sha"]!="f5556e89199dc95fc00c4f7b82d17b8f19850e65" or
        r["safety"]["max_model_provider_posts"]!=0 or
        r["physical_quality"]["native_video_count"]!=3 or
        r["case_ids"]!=list(NAMES)):
        raise Blocked("V354_PREREGISTRATION_MISMATCH")
    return r


def case_run(name:str,raw:dict,folder:Path,*,strict_v375:bool=False):
    folder.mkdir()
    packet=mock_candidate_bytes(raw)
    accepted,diag=accept(packet)
    (folder/"sanitized_admission_receipt.json").write_text(
        json.dumps(diag,indent=2)+"\n")
    if accepted is None:
        raise Blocked("V354_MOCK_CANDIDATE_DID_NOT_PASS_OFFLINE_CONTRACT")
    story,facts,graphs,layout=(accepted[k] for k in
                              ("storyboard","facts","graphs","layout"))
    # Store only host-normalized trusted structures, never raw 'model' text.
    (folder/"trusted_scene_graph.json").write_text(
        story.model_dump_json(indent=2)+"\n")
    (folder/"actual_v2_scenegraphs.json").write_text(
        json.dumps([g.model_dump(mode="json") for g in graphs],indent=2)+"\n")
    voice,beats,wav=_audio(folder,audio_proxy(story))
    v375_preflight=None
    if strict_v375:
        from learnflow_v3.v375_creative_native_gate import preflight
        v375_preflight=preflight(story,facts,layout,
                                 [int(b["frames"]) for b in beats])
    source=folder/"host_compiled_finite_manim.py"
    source.write_text(manim(story,facts,graphs,layout,voice))
    render,sandbox=_docker_manim(folder,source)
    movie=folder/"mock_candidate_native.mp4"
    mux=deterministic_mux(render,wav,movie,beats)
    media=_codec_and_pixel_gates(movie,beats)
    if media["frames"]!=mux["output_h264_frames"] or media["frames"]!=sum(x["frames"] for x in beats):
        raise Blocked("V354_NATIVE_AUDIO_FRAME_MISMATCH")
    quality,samples=inspect_native(movie,media["frames"])
    v375_native=None
    if strict_v375:
        from learnflow_v3.v375_creative_native_gate import native_gate
        v375_native=native_gate(movie,media["frames"],v375_preflight)
        if v375_native["native_sha256"]!=sha(movie):
            raise Blocked("V375_VIDEO_HASH_MISMATCH")
    signature=digest({
        "scene_layouts":[s.layout for s in story.scenes],
        "scene_node_kinds":[[n.kind for n in s.nodes] for s in story.scenes],
        "relations":[[r.kind for r in s.relations] for s in story.scenes],
        "actions":[[a.kind for a in b.actions] for b in story.beats]})
    doc={
       "checkpoint":"V3-54","case":name,"origin":MOCK_ORIGIN,
       "model_provider_http_posts":0,"genuine_model_storyboard":False,
       "candidate_sha256":diag["input_sha256"],
       "host_ledger_sha256":digest(facts),
       "trusted_storyboard_sha256":sha(folder/"trusted_scene_graph.json"),
       "host_manim_sha256":sha(source),
       "native_mp4_sha256":sha(movie),
       "v2_scenegraph_adapter_sha256":sha(folder/"actual_v2_scenegraphs.json"),
       "structure_signature_sha256":signature,
       **({"v375_creative_integrated_quality_gate":v375_native} if strict_v375 else {}),
       "graph_count":len(graphs),"beat_count":len(story.beats),
       "av":media,"mux":mux,"visual_quality_proxy":quality,
       "sandbox":sandbox,"visual_educational_quality":"UNRATED",
       "provider_schema_compliance":"NOT_TESTED",
       "production":"BLOCKED"}
    (folder/"native_quality_receipt.json").write_text(
        json.dumps(doc,indent=2)+"\n")
    return doc,samples


def run(out:Path):
    registered()
    if out.exists():raise Blocked("V354_FRESH_OUTPUT_REQUIRED")
    out.mkdir(parents=True)
    (out/"offline_candidate_json_schema.json").write_text(
        json.dumps(candidate_schema(),indent=2)+"\n")
    existing=fixtures()
    evidence=[];pairs=[]
    for name,fixture_id in NAMES.items():
        receipt,frames=case_run(name,existing[fixture_id],out/name)
        evidence.append(receipt)
        pairs.append((name,frames,receipt["structure_signature_sha256"]))
    differences=distinguish(pairs)
    if len({c["native_mp4_sha256"] for c in evidence})!=3:
        raise Blocked("V354_IDENTICAL_MP4_VIDEOS")
    summary={
       "checkpoint":"V3-54",
       "result":"THREE_MOCK_MODEL_SHAPED_SCENEGRAPHS_NATIVE_OFFLINE_TECHNICAL_PASS_ONLY",
       "cases":evidence,"pairwise_decoded_quality":differences,
       "tested_candidate_source":"V3-51_REUSED_HOST_SYNTHETIC_FIXTURES_NOT_REAL_MODEL",
       "actual_model_api_posts":0,"genuine_model_authoring":"NOT_TESTED",
       "human_visual_and_pedagogical_quality":"UNRATED",
       "model_provider_schema_compatibility":"NOT_TESTED",
       "production":"BLOCKED"}
    (out/"v354_offline_acceptance_final_receipt.json").write_text(
        json.dumps(summary,indent=2)+"\n")
    print("V3_54=THREE_NATIVE_MOCK_SCENEGRAPHS_OFFLINE_QUALITY_PASS_NOT_MODEL")
    return summary


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",required=True,type=Path)
    args=p.parse_args()
    run(args.output_dir)
