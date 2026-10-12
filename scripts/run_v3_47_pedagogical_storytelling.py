"""V3-47 host-only paired + one geometry-heldout synthetic native lesson audit."""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import wave
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_manim_runner import _audio,_docker_manim,_codec_and_pixel_gates,sha
from learnflow_v3.semantic_scene_wire import decode_model_facing_scene,compile_scene
from learnflow_v3.semantic_scene_offline_fixtures import fixture_cases
from learnflow_v3.pedagogical_visual_grammar import (
    offline_host_plan,validate_transformations,SYNTHETIC_GRAMMAR_ORIGIN)
from learnflow_v3.process_edge_visual_qa import inspect_first_edge,_frame
from learnflow_v3.creative_evidence_gate import EvidenceRejected,inspect_candidate
from scripts.run_v3_44_semantic_counterfactual import deterministic_mux
from scripts.run_v3_46_visual_quality import _frames as sampled_frames,_samples as audio_samples,_sheet as comparison_sheet,_sha

PRE="benchmarks/learnflowbench/v3/v3_47_pedagogical_grammar_preregister.json"
ORIGIN="SYNTHETIC_OFFLINE_JSON_MODEL_FACING_NOT_LIVE_MODEL"

def heldout_process(src:dict)->dict:
    """Frozen deterministic source-preserving identity/layout perturbation.

    This is held-out GEOMETRY, not a new concept, curriculum domain or new
    evaluation text. Edge endpoints and event references are fully rekeyed.
    """
    s=deepcopy(src)
    rename={g["id"]:"h_"+g["id"] for g in s["graphics"]}
    for g in s["graphics"]:
        old=g["id"]
        g["id"]=rename[old]
        if g["kind"]=="edge":
            g["src"]=rename[g["src"]];g["dst"]=rename[g["dst"]]
        if g["kind"]=="node":
            # Geometry changes while preserving reading order and node bounds.
            offsets={"start":(-.5,.2),"verify":(-.3,0.),"finish":(.2,.2)}
            dx,dy=offsets.get(old,(0,0))
            g["x"]=round(g["x"]+dx,2);g["y"]=round(g["y"]+dy,2)
    for beat in s["beats"]:
        for e in beat["events"]:
            if e["target"]:e["target"]=rename[e["target"]]
            if e["source"]:e["source"]=rename[e["source"]]
    return s

def _pixel(point):
    return int(round(640+90*point[0])),int(round(360-90*point[1]))

def _yellow_count(rgb:np.ndarray,x:float,y:float,radius_x:int,radius_y:int)->int:
    xx,yy=_pixel((x,y))
    zone=rgb[max(0,yy-radius_y):min(720,yy+radius_y),
             max(0,xx-radius_x):min(1280,xx+radius_x),:]
    if zone.size==0:raise Blocked("V347_EMPTY_SEMANTIC_PIXEL_REGION")
    # Saturated yellow vs white/TEAL. Source V3-45 has no yellow cut lines.
    return int(np.count_nonzero((zone[:,:,0]>145)&
            (zone[:,:,1]>120)&(zone[:,:,2]<135)))

def _semantic_frame_proofs(mp4:Path,scene,beats:list[dict])->dict:
    whole=sum(int(x["frames"]) for x in beats)
    if scene.family=="fraction_equivalence":
        pair=next((i,e) for i,b in enumerate(scene.beats)
                  for e in b.events if e.kind=="morph_partition")
        i,e=pair
        at=sum(int(x["frames"]) for x in beats[:i])
        frame=min(whole-1,at+round(beats[i]["frames"]*(e.at+e.span*.77)))
        decoded=_frame(mp4,frame)
        tilemap={g.id:g for g in scene.graphics}
        src=next(p for p in scene.partitions if p.id==e.source)
        regions=[]
        for id in src.part_ids:
            tile=tilemap[id]
            regions.append(_yellow_count(decoded,tile.x,tile.y,12,55))
        if len(regions)<2 or any(v<8 for v in regions):
            raise Blocked("V347_SUBDIVISION_NOT_VISIBLE_IN_NATIVE_MP4")
        return {"semantic":"explicit_each_source_cell_subdivision",
                "native_sample_frame":frame,"per_source_cell_yellow_guide_pixels":regions,
                "status":"RENDERED_PIXEL_EVIDENCE_NOT_EDUCATIONAL_LEARNING"}
    i=next(i for i,b in enumerate(scene.beats) if
           "P2" in b.claim_ids and any(e.kind=="traverse_edge" for e in b.events))
    event=next(e for e in scene.beats[i].events if e.kind=="traverse_edge")
    edge=next(g for g in scene.graphics if g.id==event.target)
    dest=next(g for g in scene.graphics if g.id==edge.dst)
    at=sum(int(x["frames"]) for x in beats[:i])
    frame=min(whole-1,at+round(beats[i]["frames"]*(event.at+event.span*.5)))
    decoded=_frame(mp4,frame)
    # CHECK ? appears below target rectangle; no fabricated PASS/FAIL.
    check_y=dest.y-dest.height/2-.38
    found=_yellow_count(decoded,dest.x,check_y,55,28)
    if found<10:
        raise Blocked("V347_UNRESOLVED_CONDITION_CUE_MISSING_IN_MP4")
    return {"semantic":"unresolved_condition_check_not_truth_claim",
            "native_sample_frame":frame,"yellow_check_cue_pixels":found,
            "outcome":"UNKNOWN_NOT_VERIFIED","status":"RENDERED_PIXEL_EVIDENCE_NOT_PREDICATE_TRUTH"}

def _rubric(out:Path):
    import csv
    target=out/"v3_47_INDEPENDENT_PEDAGOGICAL_REVIEW_UNRATED.csv"
    with target.open("w",newline="") as f:
        wr=csv.writer(f)
        wr.writerow(["case_id","criterion","before_1to5","after_1to5",
                     "blind_reviewer_id","reason_and_timestamp","review_status"])
        for case in ("fraction","process","heldout_process"):
            for label in ("object_continuity","mathematical_or_graph_truth",
                          "causal_or_condition_precision","temporal_explanation",
                          "visual_readability","learner_comprehension"):
                wr.writerow([case,label,"","","","","AWAITING_EXTERNAL_REVIEW"])
    return target

def _run_one(out:Path,case:str,raw:dict):
    dest=out/case;dest.mkdir()
    wire=dest/"synthetic_model_facing_wire.json"
    wire.write_text(json.dumps(raw,indent=2,ensure_ascii=False)+"\n")
    scene=decode_model_facing_scene(raw)
    grammar=offline_host_plan(scene)
    windows=validate_transformations(scene,grammar)
    (dest/"host_synthetic_grammar.json").write_text(grammar.model_dump_json(indent=2)+"\n")
    durations,beats,wav=_audio(dest,scene)
    source=dest/"generated_host_manim.py"
    source.write_text(compile_scene(scene,durations,visual_quality=True,
                                    pedagogical_plan=grammar))
    manim,sandbox=_docker_manim(dest,source)
    mp4=dest/"storytelling_host_with_audio.mp4"
    mux=deterministic_mux(manim,wav,mp4,beats)
    qa=_codec_and_pixel_gates(mp4,beats)
    if qa["frames"]!=sum(b["frames"] for b in beats):
        raise Blocked("V347_AUDIO_FRAME_BUDGET_MISMATCH")
    if qa["max_decoded_sample_delta"]<=.9:
        raise Blocked("V347_STATIC_OUTPUT_REJECTED")
    process_qa=(inspect_first_edge(mp4,scene,[b["frames"] for b in beats],True)
        if scene.family=="ordered_process" else {"status":"FRACTION_NO_PROCESS_EDGE"})
    visual=_semantic_frame_proofs(mp4,scene,beats)
    (dest/"v3_35_ablation_receipt.json").write_text(json.dumps({
      "checkpoint":"V3-35","model_plan_origin":ORIGIN,
      "status":"OFFLINE_HOST_FIXTURE_NOT_EDUCATIONAL_PASS",
      "manim_source_origin":"HOST_PEDAGOGICAL_COMPILER","provider_requests":0},indent=2)+"\n")
    try:inspect_candidate(dest)
    except EvidenceRejected as e:
        if str(e)!="NOT_REAL_MODEL_SCENE":
            raise Blocked("V347_FALSE_PROVENANCE_GATE_REJECTION") from None
    else:raise Blocked("V347_SYNTHETIC_ACCEPTED_AS_MODEL_ORIGIN")
    item={"id":case,"family":scene.family,"synthetic_source":ORIGIN,
          "source_wire_sha256":sha(wire),"host_compiler_sha256":sha(source),
          "output_mp4_sha256":sha(mp4),
          "grammar_origin":SYNTHETIC_GRAMMAR_ORIGIN,
          "grammar_actions":len(grammar.actions),"event_windows":windows,
          "frame_proof":visual,"process_node_overlap":process_qa,
          "beat_frames":[b["frames"] for b in beats],
          "actual_video":qa,"mux":mux,"sandbox":sandbox,
          "word_alignment":"NOT_MEASURED","human_learning":"NOT_MEASURED",
          "production":"BLOCKED","model_api_posts":0}
    (dest/"offline_storytelling_receipt.json").write_text(json.dumps(item,indent=2)+"\n")
    return item

def run(root:Path,baseline:Path,out:Path):
    register=json.loads((root/PRE).read_text())
    if (register.get("checkpoint")!="V3-47" or
        not register.get("registered_before_implementation") or
        register.get("parent_sha")!="6a3a980258c52bd9b83b58b6eaf042cb3f908694" or
        register["acceptance"].get("model_http_posts")!=0):
        raise Blocked("V347_REGISTRATION_DRIFT")
    if out.exists():raise Blocked("V347_NONEMPTY_OR_EXISTING_OUTPUT")
    out.mkdir(parents=True)
    frozen=fixture_cases()
    cases={"fraction":frozen["v345-synthetic-fractions"],
           "process":frozen["v345-synthetic-process"],
           "heldout_process":heldout_process(frozen["v345-synthetic-process"])}
    items=[]
    for case,raw in cases.items():
        items.append(_run_one(out,case,raw))
    comparisons=[]
    baseline_map={"fraction":"v345-synthetic-fractions",
                  "process":"v345-synthetic-process"}
    for case,oldname in baseline_map.items():
        item=next(x for x in items if x["id"]==case)
        olddir=baseline/oldname
        original=olddir/"offline_host_semantic_with_audio.mp4"
        oldreceipt=olddir/"offline_case_receipt.json"
        if not original.is_file() or not oldreceipt.is_file():
            raise Blocked("V347_MISSING_FROZEN_V346_SOURCE")
        oldsha=sha(original)
        expected=(register["baseline"]["fraction_sha256"] if case=="fraction" else
                  register["baseline"]["process_sha256"])
        if oldsha!=expected or json.loads(oldreceipt.read_text())["output_video_sha256"]!=expected:
            raise Blocked("V347_FROZEN_BASELINE_TAMPERED")
        if item["source_wire_sha256"]!=json.loads(oldreceipt.read_text())["input_wire_sha256"]:
            raise Blocked("V347_SOURCE_WIRE_DRIFT")
        # Narration WAV itself should be byte-identical, not merely same
        # approximate length or a new TTS response with the same words.
        for i in range(4):
            if sha(olddir/f"beat_{i}.wav")!=sha(out/case/f"beat_{i}.wav"):
                raise Blocked("V347_FROZEN_ORIGINAL_NARRATION_DRIFT")
        beat_frames,idx=audio_samples(out/case)
        if sum(beat_frames)!=item["actual_video"]["frames"]:
            raise Blocked("V347_SAMPLING_CLOCK_DRIFT")
        before=sampled_frames(original,idx)
        after=sampled_frames(out/case/"storytelling_host_with_audio.mp4",idx)
        dest=out/(case+"_storyboard_before_after.jpg")
        receipt_sha=comparison_sheet(before,after,idx,dest,case)
        comparisons.append({"case":case,"old_sha":oldsha,
                            "new_sha":item["output_mp4_sha256"],
                            "matched_frames":idx,"contact_sha256":receipt_sha,
                            "human_rated":"NO","labelled_not_blinded":True})
    # Held-out has no V3-46 baseline by design. Export timeline and twelve
    # actual decoded frames against a blackboard; NEVER label as blind AB.
    held=out/"heldout_process"
    beat_frames,idx=audio_samples(held)
    frames=sampled_frames(held/"storytelling_host_with_audio.mp4",idx)
    black=np.zeros_like(frames)
    contact=comparison_sheet(black,frames,idx,out/"heldout_process_storyboard_new_only.jpg",
                             "heldout_geometry_NO_BASELINE")
    rubric=_rubric(out)
    receipt={"checkpoint":"V3-47",
       "status":"TECHNICAL_3_NATIVE_SEMANTIC_GRAMMAR_VIDEOS_HUMAN_UNRATED",
       "preregistered_baseline_run":register["baseline"]["run_id"],
       "origin":SYNTHETIC_GRAMMAR_ORIGIN,
       "cases":items,"comparisons":comparisons,
       "heldout_storyboard_sha256":contact,
       "heldout_limit":"REKEYED_AND_SHIFTED_GEOMETRY_NOT_NEW_DOMAIN",
       "human_review_csv":rubric.name,"human_scores":None,
       "model_api_posts":0,"model_authenticated_gets":0,
       "provider_schema_unchanged":True,"word_level_alignment":"NOT_MEASURED",
       "educational_learning_improvement":"NOT_ESTABLISHED",
       "verified_condition_truth":"UNAVAILABLE_IN_V3_45_SOURCE",
       "production":"BLOCKED"}
    (out/"v3_47_semantic_storytelling_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print("V3_47=THREE_NATIVE_TECHNICAL_VIDEOS_HUMAN_PEDAGOGY_UNRATED",flush=True)
    return receipt

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--baseline-dir",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    a=p.parse_args()
    run(ROOT,a.baseline_dir,a.output_dir)
