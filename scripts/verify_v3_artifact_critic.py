#!/usr/bin/env python3
"""V3-13 bounded proof: verified actual MP4 frame samples and typed reviewer faults."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v2.repair import compute_content_hash
from learnflow_v3.sequence_renderer import SequenceRenderProfile
from learnflow_v3.temporal_geometry import certify_temporal_layout
from learnflow_v3.temporal_demo_renderer import render_certified_temporal_demo
from learnflow_v3.artifact_critic import (
    binary_request,geometry_request,run_artifact_critic,
    SeededLabel,evaluate_seeded_labels,CATEGORY_OWNER,
)
from scripts.verify_v3_beat_grounding import generate_verified_case
from scripts.verify_v3_temporal_geometry import demo_layout


def _response(request,issues):
    return {
        "request_sha256":compute_content_hash(request.model_dump(mode="json")),
        "summary":"Author-injected offline critic proposal, NOT verified real VLM output",
        "issues":issues,
    }


def demo(directory:Path):
    directory.mkdir(parents=True,exist_ok=True)
    profile=SequenceRenderProfile(width=640,height=360,fps=12,seconds_per_step=.75)
    bundle,trace,manifest,render,_,video=generate_verified_case(
        directory=directory,case="duplicate",profile=profile,
    )
    binary=binary_request(
        trace=trace,**{k:v for k,v in bundle.items() if k!="verified_trace_refs"},
        manifest=manifest,video_evidence=render,video_path=video,profile=profile,
    )
    plan=demo_layout()
    cert=certify_temporal_layout(plan)
    geo_path=directory/"critic_temporal_geometry.mp4"
    evidence=render_certified_temporal_demo(
        plan=plan,certificate=cert,output_path=geo_path,
    )
    geometry=geometry_request(
        plan=plan,certificate=cert,evidence=evidence,video_path=geo_path,
    )
    base=run_artifact_critic(binary)
    geometry_unavailable=run_artifact_critic(geometry)

    sampled=binary.frame_samples[1]
    issue={
        "issue_id":"author-synthetic-visual-concern",
        "category":"VISUAL_LEGIBILITY","severity":"MEDIUM",
        "first_frame":sampled.frame_index,"last_frame":sampled.frame_index,
        "object_ids":[binary.allowed_object_ids[0]],
        "evidence_frame_indices":[sampled.frame_index],
        "evidence_rgb_sha256":[sampled.rgb_sha256],
        "confidence":0.80,
        "rationale":"Author-seeded perceptual question; independent reviewer has NOT confirmed it",
        "repair_route":CATEGORY_OWNER["VISUAL_LEGIBILITY"],
    }
    seeded=run_artifact_critic(binary,reviewer=lambda r:_response(r,[issue]))
    altered={**issue,"object_ids":["invented_object"]}
    invalid=run_artifact_critic(binary,reviewer=lambda r:_response(r,[altered]))
    unavailable=run_artifact_critic(binary,reviewer=lambda r:(_ for _ in ()).throw(TimeoutError("injected")))
    labels=(
        SeededLabel(case_id="known-author-seed",expected_issue_ids=("author-synthetic-visual-concern",)),
        SeededLabel(case_id="known-good-seed",expected_issue_ids=()),
        SeededLabel(case_id="author-negative",expected_issue_ids=("synthetic-missed-issue",)),
    )
    metrics=evaluate_seeded_labels(labels,{
        "known-author-seed":("author-synthetic-visual-concern",),
        "known-good-seed":(),
        "author-negative":(),
    })
    results={
        "binary_no_provider":base,
        "geometry_no_provider":geometry_unavailable,
        "binary_author_seeded_review":seeded,
        "invented_object_rejected":invalid,
        "provider_timeout":unavailable,
    }
    expected_statuses={
        "binary_no_provider":"CRITIC_UNAVAILABLE",
        "geometry_no_provider":"CRITIC_UNAVAILABLE",
        "binary_author_seeded_review":"CRITIC_REVIEW_REQUIRED",
        "invented_object_rejected":"CRITIC_REJECTED",
        "provider_timeout":"CRITIC_UNAVAILABLE",
    }
    for case,out in results.items():
        assert out.status==expected_statuses[case],(case,out.status)
        assert out.publication_blocked and not out.critic_pass_certified
        print(f"V3_13_CRITIC=PASS case={case} status={out.status} "
              f"reviewer_calls={out.reviewer_calls} source={out.video_sha256[:12]}")
    assert metrics.human_labeled_recall=="UNMEASURED"
    assert metrics.improvement_vs_v2_percent_points=="NOT_ESTABLISHED"
    summary={
        "checkpoint":"V3-13",
        "status":"BOUNDED_SOURCE_PIXEL_GROUNDED_CRITIC_ADAPTER_PASS",
        "provider_live_critic":"NOT_RUN",
        "human_labeled_corpus":"NOT_AVAILABLE",
        "independent_human_quality":"UNMEASURED",
        "plus_10_percentage_points_vs_v2":"NOT_ESTABLISHED",
        "publication":"PUBLISH_BLOCKED",
        "binary_request":binary.model_dump(mode="json"),
        "geometry_request":geometry.model_dump(mode="json"),
        "results":{k:r.model_dump(mode="json") for k,r in results.items()},
        "author_seeded_only_metrics":metrics.model_dump(mode="json"),
    }
    (directory/"v3_13_artifact_critic_evidence.json").write_text(
        json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("V3_13_GOLDEN=PASS real_h264=2 critic_proposals=5 "
          "critic_pass=UNMEASURED human_recall=UNMEASURED publication=BLOCKED")
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    demo(args.output_dir)
