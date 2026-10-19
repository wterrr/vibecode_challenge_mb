#!/usr/bin/env python3
"""V3-15 frozen-demand coverage audit and two real state-machine H264 goldens.

Only topic-bound AUTHOR_CURATED state traces. Never convert a cyclic machine
into the existing DAG PROCESS_FLOW or CONCEPT_CARD. No production auto routing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_bench import load_corpus,corpus_sha256
from learnflow_v2.repair import compute_content_hash
from learnflow_v3.sequence_renderer import SequenceRenderProfile
from learnflow_v3.state_machine_renderer import (
    StateMachineLesson,ELIGIBLE_PREREG_TOPICS,render_state_machine,
    verify_state_machine_video,
)
from scripts.verify_v3_benchmark_protocol import PROTOCOL_PATH,SOURCE_SHA256,validate

PROFILE=SequenceRenderProfile(width=640,height=360,fps=12,seconds_per_step=.8)


def _spec(topic_id:str,query_hash:str)->StateMachineLesson:
    if topic_id=="lfb-006-cs":
        return StateMachineLesson(
            topic_id=topic_id,topic_query_sha256=query_hash,
            concept_title="HTTP request with retry",
            states=(
                {"state_id":"created","label":"CREATED"},
                {"state_id":"sent","label":"SENT"},
                {"state_id":"waiting","label":"WAITING"},
                {"state_id":"retry","label":"RETRY"},
                {"state_id":"done","label":"RESPONSE","terminal":True},
            ),
            transitions=(
                {"transition_id":"send","source_id":"created","target_id":"sent","trigger":"send"},
                {"transition_id":"await","source_id":"sent","target_id":"waiting","trigger":"await"},
                {"transition_id":"timeout","source_id":"waiting","target_id":"retry","trigger":"timeout"},
                {"transition_id":"resend","source_id":"retry","target_id":"sent","trigger":"resend"},
                {"transition_id":"response","source_id":"waiting","target_id":"done","trigger":"response"},
            ),
            beats=(
                {"beat_id":"begin","state_id":"created"},
                {"beat_id":"send","state_id":"sent","via_transition_id":"send","trigger":"send"},
                {"beat_id":"await","state_id":"waiting","via_transition_id":"await","trigger":"await"},
                {"beat_id":"timeout","state_id":"retry","via_transition_id":"timeout","trigger":"timeout"},
                {"beat_id":"resend","state_id":"sent","via_transition_id":"resend","trigger":"resend"},
                {"beat_id":"await-again","state_id":"waiting","via_transition_id":"await","trigger":"await"},
                {"beat_id":"response","state_id":"done","via_transition_id":"response","trigger":"response"},
            ),
            initial_state_id="created",
        )
    if topic_id=="lfb-016-cs":
        return StateMachineLesson(
            topic_id=topic_id,topic_query_sha256=query_hash,
            concept_title="Transactions: vote, retry",
            states=(
                {"state_id":"prepare","label":"PREPARE"},
                {"state_id":"waiting","label":"WAITING"},
                {"state_id":"retry","label":"RETRY"},
                {"state_id":"commit","label":"COMMIT","terminal":True},
                {"state_id":"abort","label":"ABORT","terminal":True},
            ),
            transitions=(
                {"transition_id":"votes","source_id":"prepare","target_id":"waiting","trigger":"request votes"},
                {"transition_id":"timeout","source_id":"waiting","target_id":"retry","trigger":"timeout"},
                {"transition_id":"resend","source_id":"retry","target_id":"waiting","trigger":"resend"},
                {"transition_id":"commit","source_id":"waiting","target_id":"commit","trigger":"all yes"},
                {"transition_id":"abort","source_id":"waiting","target_id":"abort","trigger":"any no"},
            ),
            beats=(
                {"beat_id":"start","state_id":"prepare"},
                {"beat_id":"votes","state_id":"waiting","via_transition_id":"votes","trigger":"request votes"},
                {"beat_id":"timedout","state_id":"retry","via_transition_id":"timeout","trigger":"timeout"},
                {"beat_id":"resend","state_id":"waiting","via_transition_id":"resend","trigger":"resend"},
                {"beat_id":"commit","state_id":"commit","via_transition_id":"commit","trigger":"all yes"},
            ),
            initial_state_id="prepare",
        )
    raise ValueError("V3_15_UNSUPPORTED_NEW_TOPIC_NO_EVIDENCE")


def curated_spec(topic)->StateMachineLesson:
    if topic.topic_id not in ELIGIBLE_PREREG_TOPICS:
        raise ValueError("V3_15_ABSTAIN_UNREGISTERED_TOPIC")
    return _spec(topic.topic_id,compute_content_hash({"topic_id":topic.topic_id,"query":topic.query}))


def run(output_dir:Path)->dict:
    protocol=json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    validate(protocol)  # same immutable 12/100; NEVER edit prereg outcomes.
    if corpus_sha256()!=SOURCE_SHA256:
        raise ValueError("V3_15_FROZEN_CORPUS_SHA_DRIFT")
    corpus=load_corpus()
    ids=tuple(protocol["sampling"]["topic_ids"])
    lookup={topic.topic_id:topic for topic in corpus.topics}
    statuses=[{
        "topic_id":topic_id,
        "scope":"FROZEN_PREREG_12_ONLY",
        "decision":"AUTHOR_CURATED_STATE_MACHINE_CANDIDATE"
                   if topic_id in ELIGIBLE_PREREG_TOPICS else "NO_NEW_FAMILY_EVIDENCE_ABSTAIN",
        "status":"NOT_PRODUCTION_ROUTED",
    } for topic_id in ids]
    if len(ids)!=12 or sum(x["decision"]=="AUTHOR_CURATED_STATE_MACHINE_CANDIDATE"
                           for x in statuses)!=2:
        raise ValueError("V3_15_FROZEN_DEMAND_AUDIT_MISMATCH")
    output_dir.mkdir(parents=True,exist_ok=True)
    goldens=[]
    for topic_id in ELIGIBLE_PREREG_TOPICS:
        topic=lookup[topic_id]
        spec=curated_spec(topic)
        dest=output_dir/f"state_machine_{topic_id}.mp4"
        evidence=render_state_machine(spec=spec,topic=topic,output_path=dest,profile=PROFILE)
        verify_state_machine_video(spec=spec,topic=topic,video_path=dest,
                                   evidence=evidence,profile=PROFILE)
        goldens.append({
            "topic_id":topic_id,
            "lesson_source_model":spec.model_dump(mode="json"),
            "render_evidence":evidence.model_dump(mode="json"),
            "real_video_sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
        })
        print(f"V3_15_GOLDEN=PASS topic={topic_id} family=STATE_MACHINE "
              f"frames={evidence.frame_count} size={dest.stat().st_size} "
              f"min_state_delta={min(evidence.decoded_state_roi_delta):.3f} "
              f"min_inside_motion={min(evidence.decoded_within_beat_motion):.3f}")
    result={
        "checkpoint":"V3-15",
        "status":"BOUNDED_FROZEN_TOPIC_STATE_MACHINE_GOLDENS_PASS",
        "prereg_topics_total":12,"candidate_evidence_count":2,
        "not_candidate_evidence_count":10,
        "eligible_topic_ids":list(ELIGIBLE_PREREG_TOPICS),
        "new_candidate_families":["STATE_MACHINE"],
        "previous_family_process_flow_limitation":"ACYCLIC_DAG_ONLY",
        "distinct_new_semantic_property":"DIRECTED_CYCLES_AND_GUARDED_BRANCHING",
        "frozen_pilot_unmodified":True,
        "all_twelve_success_rate":"UNMEASURED",
        "c5_seventy_percent_usage":"UNMEASURED",
        "human_representation_adequacy":"UNMEASURED",
        "production_router_registered":False,
        "production_lesson_narration":"NOT_IMPLEMENTED",
        "autofallback_to_concept_card":False,
        "publication":"PUBLISH_BLOCKED",
        "topic_demand_audit":statuses,
        "real_golden_clips":goldens,
    }
    (output_dir/"v3_15_pattern_coverage_evidence.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("V3_15_PATTERN_COVERAGE=PASS locked_topics=12 eligible=2 abstain=10 "
          "golden_mp4=2 router=NOT_REGISTERED C5_70_PERCENT=UNMEASURED")
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    run(args.output_dir)
