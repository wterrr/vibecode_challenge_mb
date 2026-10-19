#!/usr/bin/env python3
"""V3-14 verified local track restoration across five AUTHOR-SEEDED faults."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v3.temporal_geometry import certify_temporal_layout
from learnflow_v3.temporal_demo_renderer import (
    render_certified_temporal_demo,verify_temporal_render,
)
from learnflow_v3.artifact_refine import (
    intent_for_seeded_defect,refine_single_track,
    defer_nonlocal_issue,
)
from scripts.verify_v3_temporal_geometry import demo_layout


def fault(plan,label):
    raw=plan.model_dump(mode="json")
    tracks={t["object_id"]:t for t in raw["tracks"]}
    if label=="title-font-overflow":
        tracks["title"]["keyframes"][0]["font_px"]=80
        return "title","TEXT_OVERFLOW",raw
    if label=="right-subtitle-intrusion":
        tracks["right-explanation"]["keyframes"][-1]["box"]["y"]=273
        return "right-explanation","SUBTITLE_INTRUSION",raw
    if label=="left-frame-clipping":
        tracks["left-explanation"]["keyframes"][0]["box"]["x"]=-16
        return "left-explanation","FRAME_CLIPPING",raw
    if label=="left-motion-overload":
        tracks["left-explanation"]["keyframes"].insert(1,{
            "frame":1,"box":{"x":450,"y":132,"width":140,"height":54}})
        return "left-explanation","EXCESSIVE_MOTION",raw
    if label=="left-right-occlusion":
        tracks["left-explanation"]["keyframes"][-1]["box"]["y"]=222
        return "left-explanation","TEMPORAL_OCCLUSION",raw
    raise AssertionError(label)


def run(folder:Path):
    from learnflow_v3.temporal_geometry import TemporalLayoutPlan
    folder.mkdir(parents=True,exist_ok=True)
    baseline=demo_layout()
    certificate=certify_temporal_layout(baseline)
    pristine=folder/"original_trusted_geometry.mp4"
    evidence=render_certified_temporal_demo(
        plan=baseline,certificate=certificate,output_path=pristine)
    verify_temporal_render(plan=baseline,certificate=certificate,
                           evidence=evidence,video_path=pristine)
    pristine_hash=hashlib.sha256(pristine.read_bytes()).hexdigest()
    trials={}
    for case in (
        "title-font-overflow","right-subtitle-intrusion",
        "left-frame-clipping","left-motion-overload","left-right-occlusion",
    ):
        target,kind,bad=fault(baseline,case)
        candidate=TemporalLayoutPlan.model_validate(bad)
        intent=intent_for_seeded_defect(
            case_id=case,baseline=baseline,candidate=candidate,
            target_track_id=target,defect_category=kind)
        output=folder/f"repaired_{case}.mp4"
        result=refine_single_track(
            intent=intent,baseline=baseline,baseline_certificate=certificate,
            baseline_evidence=evidence,baseline_video_path=pristine,
            candidate=candidate,output_path=output)
        assert result.status=="LOCAL_REPAIR_VERIFIED",(case,result.reason)
        assert result.publication_blocked
        assert result.full_video_reencoded
        assert result.frame_count_reencoded==baseline.frame_count
        assert len(result.altered_track_ids)==1
        assert len(result.untouched_track_ids)==len(baseline.tracks)-1
        assert hashlib.sha256(output.read_bytes()).hexdigest()==result.repaired_video_sha256
        assert hashlib.sha256(pristine.read_bytes()).hexdigest()==pristine_hash
        trials[case]=result.model_dump(mode="json")
        print(f"V3_14_REPAIR=PASS case={case} target={target} "
              f"status={result.status} reencoded={result.frame_count_reencoded} "
              f"untouched={len(result.untouched_track_ids)} publish=BLOCKED")
    owner_routes={
        c:defer_nonlocal_issue(c).model_dump(mode="json")
        for c in ("FACTUAL_SOURCE_MISMATCH","SCRIPT_CUE_MISMATCH",
                  "PEDAGOGICAL_ALIGNMENT","VISUAL_LEGIBILITY",
                  "STYLE_INCONSISTENCY","SEMANTIC_VISUAL_MISMATCH")
    }
    result={
        "checkpoint":"V3-14","status":"BOUNDED_LOCAL_TRACK_RECOVERY_PASS",
        "fixture_label_origin":"AUTHOR_SEEDED_SYNTHETIC",
        "fault_count":len(trials),"local_track_data_recovery":len(trials),
        "author_seeded_track_recovery_fraction":len(trials)/len(trials),
        "tracked_original_video_sha256":pristine_hash,
        "original_untouched":True,"publication":"PUBLISH_BLOCKED",
        "real_critic_repair_recovery":"UNMEASURED",
        "full_video_regeneration_avoided":False,
        "full_clip_reencoding_per_success":baseline.frame_count,
        "incremental_render_cost_vs_full_regeneration":"NOT_MEASURED",
        "plan_C7_no_full_regeneration_70pct_target":"NOT_ESTABLISHED",
        "independent_human_labeled_issues":"NOT_AVAILABLE",
        "trial_results":trials,"deferred_owners":owner_routes,
    }
    (folder/"v3_14_artifact_refine_evidence.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("V3_14_GOLDEN=PASS synthetic_track_repairs=5/5 "
          "real_h264_clips=6 whole_clip_reencoded=True "
          "actual_critic_repair=UNMEASURED publication=BLOCKED")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    run(args.output_dir)
