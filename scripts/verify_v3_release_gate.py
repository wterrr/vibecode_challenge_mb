#!/usr/bin/env python3
"""V3-17 offline exact-source candidate-readiness proof, NOT a production deploy.

Two independently encoded H264 runs, full decoded RGB stream parity, genuine
V3-12 blocked reviews, frozen Core/V1 fallback blob and ephemeral V2 route.
No real user/LLM/VLM/API calls; no bypass of human study authorization.
"""
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
from learnflow_v3.release_gate import (
    ReplayProof,audit_release_candidate,verify_release_audit,
    _rgb_stream_sha256,VERSION,
)
from scripts.verify_v3_beat_grounding import generate_verified_case
from scripts.verify_v3_temporal_geometry import demo_layout
from scripts.verify_v3_benchmark_protocol import PROTOCOL_PATH


def _pair(folder:Path):
    # The same certified source is independently encoded in distinct temp paths.
    profile=SequenceRenderProfile(width=640,height=360,fps=12,seconds_per_step=.75)
    source,trace,manifest,renderer,_,binary=generate_verified_case(
        directory=folder,case="duplicate",profile=profile)
    binary_args=dict(
        trace=trace,**{k:v for k,v in source.items() if k!="verified_trace_refs"},
        manifest=manifest,video_evidence=renderer,
        video_path=binary,profile=profile)
    plan=demo_layout()
    cert=certify_temporal_layout(plan)
    geometry=folder/"release_geometry.mp4"
    evidence=render_certified_temporal_demo(
        plan=plan,certificate=cert,output_path=geometry)
    geometry_args=dict(plan=plan,certificate=cert,
                       evidence=evidence,video_path=geometry)
    return binary_args,geometry_args


def produce(folder:Path):
    folder.mkdir(parents=True,exist_ok=True)
    primary=folder/"primary"
    independent=folder/"independent"
    primary.mkdir();independent.mkdir()
    binary_args,geometry_args=_pair(primary)
    b2,g2=_pair(independent)
    # The *input* source has to be identical, independent of filename and encoder.
    assert (compute_content_hash(binary_args["trace"].model_dump(mode="json"))==
            compute_content_hash(b2["trace"].model_dump(mode="json")))
    assert (compute_content_hash(binary_args["manifest"].model_dump(mode="json"))==
            compute_content_hash(b2["manifest"].model_dump(mode="json")))
    assert (compute_content_hash(geometry_args["plan"].model_dump(mode="json"))==
            compute_content_hash(g2["plan"].model_dump(mode="json")))
    paths=(Path(b2["video_path"]),Path(g2["video_path"]))
    scenes=(
        ("BINARY_SEARCH_SAMPLE",binary_args["video_path"],paths[0],
         binary_args["profile"].width,binary_args["profile"].height,
         binary_args["profile"].frames_per_step()*len(binary_args["trace"].steps)),
        ("TEMPORAL_GEOMETRY_DEMO",geometry_args["video_path"],paths[1],
         geometry_args["plan"].width,geometry_args["plan"].height,
         geometry_args["plan"].frame_count),
    )
    replays=[]
    for subject,p,q,w,h,n in scenes:
        primary_digest=_rgb_stream_sha256(video=Path(p),width=w,height=h,count=n)
        independent_digest=_rgb_stream_sha256(video=q,width=w,height=h,count=n)
        replays.append(ReplayProof(
            subject=subject,primary_sha256=primary_digest,
            independent_sha256=independent_digest))
        print(f"V3_17_PIXELS=PASS subject={subject} decoded_frames={n} "
              f"pixel_sha256={primary_digest} publication=BLOCKED")
    protocol=json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    audit=audit_release_candidate(
        root=ROOT,protocol=protocol,binary_args=binary_args,geometry_args=geometry_args,
        pixel_replays=tuple(replays),independent_video_paths=paths)
    verify_release_audit(candidate=audit,root=ROOT,protocol=protocol,
                         binary_args=binary_args,geometry_args=geometry_args,
                         pixel_replays=tuple(replays),independent_video_paths=paths)
    assert len(audit.gates)==12
    assert sum(g.state=="PASS_COMPONENT_ONLY" for g in audit.gates)==5
    assert sum(g.state=="BLOCKED_UNMEASURED" for g in audit.gates)==7
    assert not audit.v3_released and not audit.release_authorized
    assert audit.stage=="BLOCKED_NO_RELEASE"
    assert audit.local_rollback.state=="LOCAL_EPHEMERAL_V2_RESTORE_PASS"
    result={
        "checkpoint":"V3-17",
        "execution_kind":"OFFLINE_BOUNDED_RELEASE_READINESS_REHEARSAL",
        "live_human_participants":0,
        "provider_calls":0,
        "actual_release":"BLOCKED",
        "real_paired_pilot":"UNMEASURED",
        "reproducible_full_application_build":"NOT_ESTABLISHED",
        "demonstration_reencoded_h264_count":4,
        "offline_replay_decoded_rgb_verified":True,
        "local_route_rollback_only":True,
        "rollback_restored_a_running_service":False,
        "release_audit":audit.model_dump(mode="json"),
        "gate_id_sequence":list(g.name for g in audit.gates),
    }
    (folder/"v3_17_RELEASE_BLOCKED_evidence.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("V3_17_ROLLBACK=PASS local_ephemeral=True actual_service_rollback=False "
          f"baseline_blob={audit.local_rollback.v1_baseline_blob_sha}")
    print("V3_17_RELEASE_GATE=PASS engineering_rows=5/5 blocked_gates=7/7 "
          "real_videos=4 pixel_replay=2/2 publication=BLOCKED human=UNMEASURED")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",required=True,type=Path)
    args=parser.parse_args()
    produce(args.output_dir)
