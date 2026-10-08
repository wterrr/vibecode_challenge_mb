"""V3-16 full-denominator, blinded synthetic-rehearsal and no-authority tests."""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from learnflow_v2.repair import compute_content_hash
from learnflow_v3.models import SemanticContractError
from scripts.verify_v3_benchmark_protocol import PROTOCOL_PATH,TOPIC_IDS
from scripts.verify_v3_evaluation_manifest import run,_seeded_inputs
from learnflow_v3.evaluation_pilot import (
    N,BOOTSTRAP,ARMS,RUBRIC,PRIMARY,
    BlindSlot,PilotManifest,AblationRow,GenerationAttempt,BlindedRating,
    SyntheticRehearsal,
    build_manifest,private_assignment,rehearsal_analysis,forbid_actual_study,
)

@pytest.fixture(scope="module")
def protocol():
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest(protocol):
    return build_manifest(protocol)


@pytest.fixture(scope="module")
def seeded(protocol,manifest):
    attempts,ratings=_seeded_inputs(protocol)
    return attempts,ratings,rehearsal_analysis(
        protocol=protocol,manifest=manifest,attempts=attempts,ratings=ratings,
    )


def test_exact_frozen_12_topic_evaluation_design_unexecuted(manifest,protocol):
    assert manifest.status=="DESIGN_READY_UNEXECUTED"
    assert manifest.study_permissions=="NOT_AUTHORIZED"
    assert not manifest.paid_api_authorized and not manifest.publish_authorized
    assert manifest.subject_count==manifest.evaluated_pair_count==0
    assert manifest.v2_videos==manifest.v3_videos==0
    assert manifest.human_scores_state=="UNMEASURED"
    assert manifest.model_provider_calls==0
    assert tuple(x.topic_id for x in manifest.topic_slots)==TOPIC_IDS
    assert len(manifest.ablation_plan)==10
    assert [x.ablation_id for x in manifest.ablation_plan]==[f"E{i}" for i in range(1,11)]
    assert all(x.status=="NOT_RUN" and x.samples==0 and
               not x.user_authorized for x in manifest.ablation_plan)
    assert manifest==build_manifest(protocol)


def test_immutable_replay_hash_and_topic_substitution_rejected(manifest,protocol):
    values=manifest.model_dump(mode="json")
    values["topic_slots"][0]["topic_id"]="lfb-005-cs"
    values["manifest_sha256"]=compute_content_hash({k:v for k,v in values.items()
                                                    if k!="manifest_sha256"})
    with pytest.raises(ValidationError,match="SELECTED_TOPICS_CHANGED"):
        PilotManifest.model_validate(values)
    changed=json.loads(json.dumps(protocol))
    changed["sampling"]["topic_ids"][0]="lfb-005-cs"
    with pytest.raises(ValueError):
        build_manifest(changed)
    changed=json.loads(json.dumps(protocol))
    changed["permission"]["human_participants_authorized"]=True
    with pytest.raises(ValueError):
        build_manifest(changed)


def test_public_packet_never_reveals_v2_v3_identity(manifest,protocol):
    public=json.dumps(manifest.model_dump(mode="json"))
    assert "v2d_frozen" not in public
    assert "v3_candidate" not in public
    assert "model_slug" not in public
    for topic_id in TOPIC_IDS:
        m=private_assignment(protocol,topic_id)
        assert set(m)=={"A","B"} and set(m.values())==set(ARMS)
        assert private_assignment(protocol,topic_id)==m
    with pytest.raises(SemanticContractError,match="TOPIC_NOT_PREREGISTERED"):
        private_assignment(protocol,"lfb-005-cs")


def test_real_human_and_provider_authority_remains_disabled():
    with pytest.raises(SemanticContractError,match="NOT_AUTHORIZED"):
        forbid_actual_study(protocol="anything")
    with pytest.raises(ValidationError):
        PilotManifest.model_validate({
            "version":"v3-16-blinded-pilot-manifest-v1","study_permissions":"APPROVED",
        })


def test_full_24_attempt_denominator_including_failures_and_unmeasured_cost(seeded):
    attempts,ratings,result=seeded
    assert len(attempts)==24
    assert len({(x.topic_id,x.system) for x in attempts})==24
    assert len(result.topic_pairs)==12
    assert result.attempts_included==24 and result.denominator==12
    assert result.failed_attempts==2
    assert result.complete_valid_mp4_count==22
    assert result.provider_cost_total_usd is None
    assert result.wall_seconds_total is None
    assert result.critical_safety_errors is None
    assert result.primary_quadratic_weighted_kappa is not None
    assert 0<=result.primary_quadratic_weighted_kappa<=1
    assert len(result.stratified_effects)==9
    assert sum(x.topic_count for x in result.stratified_effects if x.group=="domain")==12
    assert sum(x.topic_count for x in result.stratified_effects if x.group=="difficulty")==12
    assert result.provider_cost_p50_usd is None and result.provider_cost_p95_usd is None
    assert result.wall_seconds_p50 is None and result.wall_seconds_p95 is None
    assert result.independent_human_data is False
    assert result.real_pilot_pass is False and result.publication_blocked
    assert result.actual_human_quality_effect=="UNMEASURED"
    assert [x.topic_id for x in result.topic_pairs]==list(TOPIC_IDS)
    assert result.topic_pairs[2].failed_systems==("v2d_frozen",)
    assert result.topic_pairs[8].failed_systems==("v3_candidate",)
    assert all(x.score_origin=="AUTHOR_SEEDED_SYNTHETIC" for x in result.topic_pairs)


def test_fixed_co_primary_thresholds_and_topic_level_bootstrap(seeded):
    _,_,result=seeded
    assert len(result.co_primary_effects)==2
    assert tuple(x.metric for x in result.co_primary_effects)==PRIMARY
    assert all(x.bootstrap_resamples==BOOTSTRAP for x in result.co_primary_effects)
    assert all(x.ci_low<=x.mean_paired_delta<=x.ci_high for x in result.co_primary_effects)
    assert all(0<=x.wins<=12 and 0<=x.ties<=12 for x in result.co_primary_effects)
    assert all(x.threshold_mean_reached and x.threshold_wins_reached for x in result.co_primary_effects)
    assert not result.real_pilot_pass  # even when all seeded thresholds are met


def test_bootstrap_and_adjudication_seed_reproducibility(seeded,protocol,manifest):
    attempts,ratings,result=seeded
    again=rehearsal_analysis(protocol=protocol,manifest=manifest,
                             attempts=attempts,ratings=ratings)
    assert result.model_dump(mode="json")==again.model_dump(mode="json")
    assert result.mean_absolute_rater_disagreement is not None
    assert result.mean_absolute_rater_disagreement>0


def test_ablation_contrast_freeze_and_no_outcome_spoof(manifest):
    rec=manifest.ablation_plan[1].model_dump(mode="json")
    rec["controlled_contrast"]="ONLY_RENDERER_CHANGED_AND_AUDIO_TOO"
    with pytest.raises(ValidationError):
        AblationRow.model_validate(rec)
    rec=manifest.ablation_plan[1].model_dump(mode="json")
    rec["status"]="PASS"
    rec["effect_size"]=2.0
    with pytest.raises(ValidationError):
        AblationRow.model_validate(rec)
    bad=manifest.model_dump(mode="json")
    bad["ablation_plan"]=bad["ablation_plan"][:-1]
    bad["manifest_sha256"]=compute_content_hash({k:v for k,v in bad.items()
                                                 if k!="manifest_sha256"})
    with pytest.raises(ValidationError):
        PilotManifest.model_validate(bad)


def test_invalid_video_floor_is_one_but_unrun_is_not_one(seeded,protocol,manifest):
    attempts,ratings,result=seeded
    floor=result.topic_pairs[2].v2_scores
    assert all(floor[k]==1.0 for k in RUBRIC)
    floor=result.topic_pairs[8].v3_scores
    assert all(floor[k]==1.0 for k in RUBRIC)
    unrun=list(attempts)
    unrun[1]=unrun[1].model_copy(update={
        "state":"NOT_RUN","failure_code":None,"real_video_sha256":None,
        "provenance":"UNEXECUTED"})
    with pytest.raises(SemanticContractError,match="PILOT_UNEXECUTED_CANNOT_BE_ANALYZED"):
        rehearsal_analysis(protocol=protocol,manifest=manifest,
                           attempts=tuple(unrun),ratings=ratings)


def test_no_survivor_only_22_of_24_pairs(seeded,protocol,manifest):
    attempts,ratings,_=seeded
    with pytest.raises(SemanticContractError,match="ALL_12_PAIRED"):
        rehearsal_analysis(protocol=protocol,manifest=manifest,
                           attempts=attempts[:-1],ratings=ratings)
    with pytest.raises(SemanticContractError,match="ALL_12_PAIRED"):
        rehearsal_analysis(protocol=protocol,manifest=manifest,
                           attempts=attempts+(attempts[-1],),ratings=ratings)


def test_duplicate_or_missing_two_independent_raters_blocked(seeded,protocol,manifest):
    attempts,ratings,_=seeded
    with pytest.raises(SemanticContractError,match="RATERS_NOT_INDEPENDENT_OR_MISSING"):
        rehearsal_analysis(protocol=protocol,manifest=manifest,
                           attempts=attempts,ratings=ratings[:-1])
    with pytest.raises(SemanticContractError,match="DUPLICATE_OR_FOREIGN_RATING"):
        rehearsal_analysis(protocol=protocol,manifest=manifest,
                           attempts=attempts,ratings=ratings+(ratings[0],))


def test_adjudicator_mandatory_for_primary_disagreement(seeded,protocol,manifest):
    attempts,ratings,_=seeded
    no_third=tuple(r for r in ratings if r.rater_id!="seeded_adjudicator_three")
    with pytest.raises(SemanticContractError,match="ADJUDICATION_NOT_MATCHED"):
        rehearsal_analysis(protocol=protocol,manifest=manifest,
                           attempts=attempts,ratings=no_third)
    extra=ratings+(ratings[0].model_copy(update={"rater_id":"extra_rater_three"}),)
    with pytest.raises(SemanticContractError,match="ADJUDICATION_NOT_MATCHED"):
        rehearsal_analysis(protocol=protocol,manifest=manifest,
                           attempts=attempts,ratings=extra)


def test_ratings_for_failed_video_are_not_laundered_as_human(seeded,protocol,manifest):
    attempts,ratings,_=seeded
    failed=next(x for x in attempts if x.state=="FAILED")
    slot=next(s for s,system in private_assignment(protocol,failed.topic_id).items()
              if system==failed.system)
    forged=BlindedRating(topic_id=failed.topic_id,slot=slot,
                         rater_id="fake_rater",
                         ratings={k:5 for k in RUBRIC},evidence_note="seeded_bad_floor")
    with pytest.raises(SemanticContractError,match="INVALID_VIDEO_FLOOR"):
        rehearsal_analysis(protocol=protocol,manifest=manifest,
                           attempts=attempts,ratings=ratings+(forged,))


def test_rating_validation_and_identity_blind_contract(seeded):
    r=seeded[1][0]
    with pytest.raises(ValidationError):
        BlindedRating.model_validate({**r.model_dump(mode="json"),
                                      "system_identity_disclosed":True})
    with pytest.raises(ValidationError):
        BlindedRating.model_validate({**r.model_dump(mode="json"),
                                      "ratings":{**r.ratings,"clarity":6}})
    with pytest.raises(ValidationError):
        BlindedRating.model_validate({**r.model_dump(mode="json"),
                                      "ratings":{**r.ratings,"clarity":2.5}})
    with pytest.raises(ValidationError):
        BlindedRating.model_validate({**r.model_dump(mode="json"),
                                      "origin":"INDEPENDENT_HUMAN"})


def test_actual_cost_never_inferred_from_missing_cost(seeded,protocol,manifest):
    attempts,ratings,_=seeded
    a=list(attempts)
    a[0]=a[0].model_copy(update={"actual_usd_cost":0.50,"wall_seconds":3.0})
    res=rehearsal_analysis(protocol=protocol,manifest=manifest,
                           attempts=tuple(a),ratings=ratings)
    assert res.provider_cost_total_usd is None
    assert res.wall_seconds_total is None
    assert not res.real_pilot_pass
    with pytest.raises(ValidationError):
        GenerationAttempt.model_validate({**a[0].model_dump(mode="json"),
                                          "actual_usd_cost":-3.0})
    with pytest.raises(ValidationError):
        GenerationAttempt.model_validate({**a[0].model_dump(mode="json"),
                                          "wall_seconds":float("nan")})


def test_failed_attempt_without_reason_and_unrun_with_fake_metrics_rejected(seeded):
    a=seeded[0][0]
    with pytest.raises(ValidationError):
        GenerationAttempt.model_validate({**a.model_dump(mode="json"),
                                          "state":"FAILED","failure_code":None,
                                          "real_video_sha256":None})
    with pytest.raises(ValidationError):
        GenerationAttempt.model_validate({**a.model_dump(mode="json"),
                                          "state":"NOT_RUN","provider_roundtrips":1})


def test_analysis_self_rehash_cannot_promote_synthetic_to_human(seeded):
    result=seeded[2]
    data=result.model_dump(mode="json")
    data["real_pilot_pass"]=True
    data["actual_human_quality_effect"]="MEASURED"
    data["result_sha256"]=compute_content_hash({k:v for k,v in data.items() if k!="result_sha256"})
    with pytest.raises(ValidationError):
        SyntheticRehearsal.model_validate(data)
    data=result.model_dump(mode="json")
    data["result_sha256"]="f"*64
    with pytest.raises(ValidationError,match="FORGED_ANALYSIS"):
        SyntheticRehearsal.model_validate(data)


def test_actual_cli_outputs_only_public_blind_template_and_seeded_analysis(tmp_path):
    man,analysis=run(tmp_path)
    names={p.name for p in tmp_path.iterdir()}
    assert names=={
        "v3_16_public_blinded_manifest.json",
        "v3_16_blinded_rater_sheet_TEMPLATE.csv",
        "v3_16_AUTHOR_SEEDED_analysis_rehearsal.json",
    }
    public=(tmp_path/"v3_16_public_blinded_manifest.json").read_text()
    assert "v2d_frozen" not in public and "v3_candidate" not in public
    with (tmp_path/"v3_16_blinded_rater_sheet_TEMPLATE.csv").open(newline="") as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==24 and all(not x["rater_id"] for x in rows)
    seeded_text=(tmp_path/"v3_16_AUTHOR_SEEDED_analysis_rehearsal.json").read_text()
    seeded_data=json.loads(seeded_text)
    assert seeded_data["human_participants"]==0
    assert seeded_data["model_provider_calls"]==0
    assert seeded_data["evidence_type"]=="AUTHOR_SEEDED_SYNTHETIC_NO_HUMAN_NO_REAL_VIDEO"
    assert seeded_data["rehearsal_analysis"]["real_pilot_pass"] is False
    assert analysis.status=="AUTHOR_SEEDED_REHEARSAL_ONLY_NOT_HUMAN_EVIDENCE"


def test_complete_synthetic_cost_and_runtime_percentiles_are_transparent(
    seeded,protocol,manifest
):
    attempts,ratings,_=seeded
    all_observed=tuple(a.model_copy(update={
        "actual_usd_cost":1.25,"wall_seconds":2.5,
    }) for a in attempts)
    analysis=rehearsal_analysis(
        protocol=protocol,manifest=manifest,attempts=all_observed,ratings=ratings,
    )
    assert analysis.provider_cost_total_usd==30.0
    assert analysis.wall_seconds_total==60.0
    assert analysis.provider_cost_p50_usd==analysis.provider_cost_p95_usd==1.25
    assert analysis.wall_seconds_p50==analysis.wall_seconds_p95==2.5
    assert analysis.real_pilot_pass is False


def test_kappa_and_strata_are_fixed_to_primary_human_scoring_structure(seeded):
    result=seeded[2]
    assert result.primary_quadratic_weighted_kappa is not None
    assert len(result.stratified_effects)==9
    assert {s.group for s in result.stratified_effects}=={"domain","difficulty"}
    assert all(set((s.clarity_mean_paired_delta,s.representation_mean_paired_delta))
               for s in result.stratified_effects)
    assert result.independent_human_data is False
