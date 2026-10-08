#!/usr/bin/env python3
"""V3-12 offline evidence: real H264 -> true V3 replay -> BLOCK publication."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v3.sequence_renderer import SequenceRenderProfile
from learnflow_v3.publication_gate import (
    CriticObservation,review_binary_publication,review_geometry_publication,
)
from learnflow_v3.temporal_geometry import certify_temporal_layout
from learnflow_v3.temporal_demo_renderer import render_certified_temporal_demo
from scripts.verify_v3_beat_grounding import generate_verified_case
from scripts.verify_v3_temporal_geometry import demo_layout


def evidence_bundle(folder:Path):
    folder.mkdir(parents=True,exist_ok=True)
    profile=SequenceRenderProfile(width=640,height=360,fps=12,seconds_per_step=.75)
    bundle,trace,manifest,renderer,_,video=generate_verified_case(
        directory=folder,case="duplicate",profile=profile)
    binary_args=dict(
        trace=trace,**{k:v for k,v in bundle.items() if k!="verified_trace_refs"},
        manifest=manifest,video_evidence=renderer,video_path=video,profile=profile,
    )
    plan=demo_layout()
    cert=certify_temporal_layout(plan)
    geometry_video=folder/"v3_12_geometry.mp4"
    geometry_evidence=render_certified_temporal_demo(
        plan=plan,certificate=cert,output_path=geometry_video)
    geom_args=dict(plan=plan,certificate=cert,
                   evidence=geometry_evidence,video_path=geometry_video)
    good_binary=review_binary_publication(**binary_args)
    good_geom=review_geometry_publication(**geom_args)
    outage=review_binary_publication(
        **binary_args,critic=CriticObservation(outcome="UNAVAILABLE"))
    spoof=review_binary_publication(
        **binary_args,critic=CriticObservation(outcome="PASS_UNVERIFIED"))
    corrupt=review_binary_publication(
        **{**binary_args,"video_evidence":renderer.model_copy(
            update={"video_sha256":"0"*64})})
    rows={"real_binary_search":good_binary,"real_geometry_demo":good_geom,
          "critic_unavailable":outage,"unverified_critic_pass":spoof,
          "stale_video_evidence":corrupt}
    for key,record in rows.items():
        assert record.publication_status=="PUBLISH_BLOCKED"
        assert record.production_release_executed is False
        print(f"V3_12_POLICY=PASS case={key} "
              f"deterministic={record.deterministic_status.value} "
              f"critic={record.critic_status.value} "
              f"publication={record.publication_status} "
              f"unmet={len(record.blocked_reasons)}")
    assert good_binary.deterministic_status.value=="DETERMINISTIC_PASS"
    assert good_geom.deterministic_status.value=="DETERMINISTIC_PASS"
    assert spoof.critic_status.value=="CRITIC_UNAVAILABLE"
    assert corrupt.deterministic_status.value=="DETERMINISTIC_FAIL"
    output={
        "checkpoint":"V3-12","version":"v3-12-fail-closed-publication-v1",
        "status":"OFFLINE_FAIL_CLOSED_NO_RELEASE",
        "publication_enabled":False,
        "independent_critic":"UNIMPLEMENTED",
        "full_lesson_audio":"UNMEASURED",
        "production_publication":"BLOCKED",
        "cases":{k:v.model_dump(mode="json") for k,v in rows.items()},
    }
    (folder/"v3_12_policy_evidence.json").write_text(
        json.dumps(output,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return output


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",required=True,type=Path)
    args=p.parse_args()
    evidence_bundle(args.output_dir)
    print("V3_12_PUBLICATION_GATE=PASS blocked=5/5 real_mp4s=2")


if __name__=="__main__":
    main()
