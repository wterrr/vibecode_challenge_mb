#!/usr/bin/env python3
"""V3-51 OFFLINE-only, exact audio native H264/AAC and scene freedom receipt."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

import numpy as np

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_manim_runner import _audio,_docker_manim,_codec_and_pixel_gates,sha
from learnflow_v3.creative_scene_graph import (
    validate,ledger,digest,audio_proxy,manim,ORIGIN,VERSION)
from learnflow_v3.creative_scene_fixtures import fixtures
from learnflow_v3.process_edge_visual_qa import _frame
from scripts.run_v3_44_semantic_counterfactual import deterministic_mux

REG="benchmarks/learnflowbench/v3/v3_51_creative_scene_preregister.json"


def check_manifest():
    p=json.loads((ROOT/REG).read_text())
    if (p["checkpoint"]!="V3-51" or
       not p["preregistered_before_implementation"] or
       p["parent_sha"]!="1ef31e132659b2a7d07e351f0810824c91bc28ee" or
       p["quality_gates"]["required_native_count"]!=3 or
       p["scope"].find("OFFLINE_ONLY")<0):
        raise Blocked("V351_PREREGISTRATION_DRIFT")
    return p


def _case(name:str,raw:dict,path:Path):
    path.mkdir()
    st,evidence,graphs,positions=validate(raw)
    (path/"storyboard_host_synthetic.json").write_text(
        json.dumps(raw,indent=2)+"\n")
    (path/"v2_scenegraph_adapter.json").write_text(json.dumps(
        [g.model_dump(mode="json") for g in graphs],indent=2)+"\n")
    voice,beats,wav=_audio(path,audio_proxy(st))
    source=path/"finite_host_compiled_scene.py"
    code=manim(st,evidence,graphs,positions,voice)
    source.write_text(code)
    full,sandbox=_docker_manim(path,source)
    output=path/"creative_graph_native.mp4"
    mux=deterministic_mux(full,wav,output,beats)
    media=_codec_and_pixel_gates(output,beats)
    expected=sum(x["frames"] for x in beats)
    if media["frames"]!=expected or mux["output_h264_frames"]!=expected:
        raise Blocked("V351_AUDIO_NATIVE_FRAME_BUDGET_DRIFT")
    if media["max_decoded_sample_delta"]<=.9:
        raise Blocked("V351_STATIC_CARD")
    # Actual decoded frames; not source-code search or synthetic pixel counters.
    mid=max(1,round(expected*.49))
    earlier=max(1,round(expected*.15))
    late=min(expected-2,round(expected*.82))
    frames=[_frame(output,k) for k in (earlier,mid,late)]
    diff=[float(np.mean(np.abs(frames[i].astype("int16")-
                                frames[i-1].astype("int16"))))
          for i in (1,2)]
    if max(diff)<2:
        raise Blocked("V351_DECODED_STORY_STATIC")
    action_counts=Counter(a.kind for b in st.beats for a in b.actions)
    evidence_count=sum(node.fact_ref is not None for s in st.scenes for node in s.nodes)
    receipt={
      "case":name,"origin":ORIGIN,"version":VERSION,
      "model_inference_http_posts":0,"real_model_storyboard":False,
      "factual_ledger_sha256":digest(evidence),
      "storyboard_sha256":digest(raw),
      "v2_graph_sha256":sha(path/"v2_scenegraph_adapter.json"),
      "trusted_host_source_sha256":sha(source),
      "native_h264_aac_sha256":sha(output),
      "native_codec":media,"exact_mux":mux,
      "scene_count":len(st.scenes),"scene_layouts":[s.layout for s in st.scenes],
      "node_count":sum(len(s.nodes) for s in st.scenes),
      "edge_count":sum(len(s.relations) for s in st.scenes),
      "fact_evidence_nodes":evidence_count,
      "beat_count":len(st.beats),"action_counts":dict(action_counts),
      "decoded_frames":[earlier,mid,late],
      "decoded_frame_differences":diff,
      "physical_semantics":"HOST_VERIFIED_LABELS_AND_RELATION_WHITELIST;NARRATION_NOT_FACT_CHECKED",
      "human_quality":"UNRATED",
      "provider_schema":"NOT_TESTED","production":"BLOCKED","sandbox":sandbox}
    (path/"creative_graph_case_receipt.json").write_text(
      json.dumps(receipt,indent=2)+"\n")
    return receipt,frames


def run(out:Path):
    p=check_manifest()
    if out.exists():raise Blocked("V351_OUTPUT_MUST_BE_NEW")
    out.mkdir(parents=True)
    expected=[v["id"] for v in p["frozen_offline_variants"]]
    cases=fixtures()
    if list(cases)!=expected:raise Blocked("V351_CASE_SET_OR_ORDER_DRIFT")
    results=[];frame_groups={}
    for name,raw in cases.items():
        result,decoded=_case(name,raw,out/name)
        results.append(result);frame_groups[name]=decoded
    if len({r["native_h264_aac_sha256"] for r in results})!=3:
        raise Blocked("V351_NATIVE_VIDEOS_IDENTICAL")
    pairwise=[]
    keys=list(frame_groups)
    for i in range(len(keys)):
        for j in range(i+1,len(keys)):
            left,right=frame_groups[keys[i]],frame_groups[keys[j]]
            mae=[float(np.mean(np.abs(a.astype("int16")-b.astype("int16"))))
                 for a,b in zip(left,right)]
            if max(mae)<2.5:
                raise Blocked("V351_VISUAL_STORYBOARDS_NOT_DISTINCT")
            pairwise.append({"first":keys[i],"second":keys[j],
                 "per_normalized_frame_mae":mae,
                 "observation":"RENDER_DIFFERENCE_ONLY_NO_STUDENT_EFFECTIVENESS"})
    doc={
       "checkpoint":"V3-51",
       "status":"THREE_VISUALLY_DISTINCT_NATIVE_HOST_SCENEGRAPHS_TECHNICAL_PASS_ONLY",
       "cases":results,"pairs":pairwise,
       "frozen_case_count":3,"model_api_posts":0,
       "old_v3_50_real_failure":"UNCHANGED_CONSUMED_NO_RERUN",
       "human_pedagogy":"UNRATED",
       "model_provider_compatibility":"NOT_TESTED",
       "general_domains":"NOT_CERTIFIED",
       "production":"BLOCKED"}
    (out/"v351_offline_three_scenegraphs_receipt.json").write_text(
        json.dumps(doc,indent=2)+"\n")
    print("V3_51=THREE_DISTINCT_NATIVE_HOST_SCENEGRAPHS_TECHNICAL_PASS_HUMAN_UNRATED")
    return doc


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",required=True,type=Path)
    opts=parser.parse_args()
    run(opts.output_dir)
