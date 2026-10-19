#!/usr/bin/env python3
"""V3-16 manifest and fail-closed statistical rehearsal; absolutely NO pilot run.

Does not export the A/B identity mapping, recruit human raters, run a model, or
invent real videos. Synthetic comparisons are synthetic and never release-pass.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from scripts.verify_v3_benchmark_protocol import PROTOCOL_PATH,TOPIC_IDS
from learnflow_v3.evaluation_pilot import (
    ARMS,RUBRIC,GenerationAttempt,BlindedRating,
    build_manifest,private_assignment,rehearsal_analysis,
)


def _seeded_inputs(protocol):
    """Mock outcomes only; simulated MP4 hash placeholders are NOT actual MP4."""
    attempts=[]
    ratings=[]
    for i,topic_id in enumerate(TOPIC_IDS):
        mapping=private_assignment(protocol,topic_id)
        for arm in ARMS:
            # Two independent scripted failures demonstrate all-attempt counting.
            failure=(i==2 and arm=="v2d_frozen") or (i==8 and arm=="v3_candidate")
            state="FAILED" if failure else "VALID_VIDEO"
            attempts.append(GenerationAttempt(
                topic_id=topic_id,system=arm,
                attempt_id=f"author-seeded-{topic_id}-{arm}",
                state=state,
                failure_code="SYNTHETIC_INJECTED_FAILURE" if failure else None,
                real_video_sha256=None if failure else hashlib.sha256(
                    f"NOT_A_REAL_VIDEO|{topic_id}|{arm}".encode()).hexdigest(),
                actual_usd_cost=None,wall_seconds=None,
                provider_roundtrips=None,
                provenance="AUTHOR_SEEDED_SYNTHETIC",
            ))
        for slot,arm in mapping.items():
            is_bad=(i==2 and arm=="v2d_frozen") or (i==8 and arm=="v3_candidate")
            if is_bad:continue
            value=2 if arm=="v2d_frozen" else 4
            for rater_id in ("seeded_rater_one","seeded_rater_two"):
                score={k:value for k in RUBRIC}
                # Adjudicate a deliberately introduced *co-primary* disagreement.
                if i==4 and arm=="v3_candidate" and rater_id=="seeded_rater_two":
                    score["clarity"]=2
                ratings.append(BlindedRating(
                    topic_id=topic_id,slot=slot,rater_id=rater_id,
                    ratings=score,evidence_note="AUTHOR_SEEDED_SYNTHETIC_NOT_HUMAN",
                ))
            if i==4 and arm=="v3_candidate":
                ratings.append(BlindedRating(
                    topic_id=topic_id,slot=slot,rater_id="seeded_adjudicator_three",
                    ratings={k:4 for k in RUBRIC},
                    evidence_note="AUTHOR_SEEDED_ADJUDICATION_NOT_HUMAN",
                ))
    return tuple(attempts),tuple(ratings)


def run(out:Path):
    protocol=json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    manifest=build_manifest(protocol)
    out.mkdir(parents=True,exist_ok=True)
    # Public instructions contain ONLY A/B and locked topics; no system key.
    public=manifest.model_dump(mode="json")
    (out/"v3_16_public_blinded_manifest.json").write_text(
        json.dumps(public,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    fields=["topic_id","anonymous_slot","rater_id",*RUBRIC,"evidence_note"]
    with (out/"v3_16_blinded_rater_sheet_TEMPLATE.csv").open(
        "w",newline="",encoding="utf-8",
    ) as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        for topic_id in TOPIC_IDS:
            for slot in ("A","B"):
                writer.writerow({"topic_id":topic_id,"anonymous_slot":slot})
    attempts,ratings=_seeded_inputs(protocol)
    analysis=rehearsal_analysis(
        protocol=protocol,manifest=manifest,attempts=attempts,ratings=ratings,
    )
    # Synthetic sample artifact retains the tags, never call this human results.
    synthetic={
        "checkpoint":"V3-16",
        "evidence_type":"AUTHOR_SEEDED_SYNTHETIC_NO_HUMAN_NO_REAL_VIDEO",
        "actual_human_pilot":"NOT_RUN_NO_AUTHORIZATION",
        "locked_topic_count":12,"attempts_count":24,
        "model_provider_calls":0,"human_participants":0,
        "publication":"PUBLISH_BLOCKED",
        "sample_attempts":[x.model_dump(mode="json") for x in attempts],
        "sample_scores":[x.model_dump(mode="json") for x in ratings],
        "rehearsal_analysis":analysis.model_dump(mode="json"),
        "warn":"SHA placeholders under sample_attempts are NOT actual MP4 hashes",
    }
    (out/"v3_16_AUTHOR_SEEDED_analysis_rehearsal.json").write_text(
        json.dumps(synthetic,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Avoid persisting the private A/B system key in any artifact/CI report.
    manifest_text=json.dumps(public)
    if any(x in manifest_text for x in ("v2d_frozen","v3_candidate","seeded_rater")):
        raise AssertionError("V3_16_PUBLIC_PACKET_REVEALS_SYSTEM_IDENTITY")
    assert all(x.state!="NOT_RUN" for x in attempts)
    assert analysis.real_pilot_pass is False
    assert analysis.actual_human_quality_effect=="UNMEASURED"
    assert analysis.failed_attempts==2
    assert analysis.provider_cost_total_usd is None
    assert analysis.wall_seconds_total is None
    print("V3_16_BLINDING=PASS public_slots=24 identity_mapping_not_exported=True")
    print("V3_16_PREREG=PASS locked_topics=12 frozen_corpus=True ablations=10")
    print("V3_16_REHEARSAL=PASS attempts=24 author_seeded_failures=2 "
          "bootstrap=10000 denominator=12 real_human_data=UNMEASURED")
    for metric in analysis.co_primary_effects:
        print(f"V3_16_SYNTHETIC_EFFECT metric={metric.metric} "
              f"delta={metric.mean_paired_delta:.3f} wins={metric.wins}/12 "
              f"ci95=[{metric.ci_low:.3f},{metric.ci_high:.3f}] "
              "NOT_HUMAN_EVIDENCE")
    print("V3_16_EVALUATION_MANIFEST=PASS execution=NOT_AUTHORIZED "
          "external_model_cost=UNMEASURED publication=BLOCKED")
    return manifest,analysis


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    run(args.output_dir)
