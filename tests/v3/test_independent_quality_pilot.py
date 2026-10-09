"""V3-25 actual pair provenance & anti-fabrication; synthetic scoring only in tests."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import pytest
from learnflow_v3.independent_quality_pilot import (
    RATERS,DIMS,PRIMARY,STUDY,VERSION,assignment,make_manifest,
    _rater_config,_validate_manifest,create_packets,inspect_submissions,
)
from learnflow_v3.lesson_quality import QualityEvidenceError

@pytest.fixture(scope="module")
def source():
    p=Path(os.environ["V3_25_MEDIA_DIR"])
    assert (p/"native_hd/v3_22_binary_search_native_720p.mp4").is_file()
    assert (p/"native_pedagogical/v3_24_leftmost_teaching_720p.mp4").is_file()
    return p

@pytest.fixture(scope="module")
def manifest(source):
    return make_manifest(source)

def test_true_source_controlled_visual_only_comparison(manifest):
    m=manifest
    assert m["scope"]=="EXPLORATORY_KNOWN_BINARY_SEARCH_SINGLE_TOPIC_ONLY"
    assert m["excluded_from_frozen_v3_16_confirmatory_12_topic_benchmark"] is True
    assert m["media"]["size"]==[1280,720] and m["media"]["fps"]==24
    assert m["media"]["frames"]==1082
    assert m["media"]["baseline_sha256"]!=m["media"]["refined_sha256"]
    assert m["media"]["audio_packet_sha256"] and m["media"]["event_proof_sha256"]
    assert m["media"]["visual_only_change"] is True
    assert m["participants_observed"]==m["scores_observed"]==0
    assert m["production"]==m["student_ready"]=="BLOCKED"
    assert m["independent_review_verified"]=="NOT_RUN"

def test_counterbalanced_disjoint_variant_labels_without_rater_identity_key(manifest):
    a=manifest["rater_assignment"]
    assert set(a)==set(RATERS)
    assert a["R01"]["A"]==a["R02"]["B"]
    assert a["R01"]["B"]==a["R02"]["A"]
    assert len(set(a["R01"].values()))==2
    for rid in RATERS:
        c=_rater_config(manifest,rid)
        assert c["media_sha256"]["A"]!=c["media_sha256"]["B"]
        assert len(c["package_sha256"])==64
        assert set(c["rubric_dimensions"])==set(DIMS)
        assert set(c["transfer_items"])=={"A","B"}

def test_create_real_playable_unscored_packets(source,tmp_path):
    out=tmp_path/"packet"
    out.mkdir()
    receipt=create_packets(media_root=source,output_dir=out)
    assert receipt["human_ratings"]==receipt["human_participants"]==0
    assert receipt["publish"]=="BLOCKED"
    for rid in RATERS:
        p=out/("REVIEWER_"+rid)
        html=(p/"review.html").read_text()
        assert (p/"clip_A.mp4").is_file() and (p/"clip_B.mp4").is_file()
        assert '<video' not in html or "createElement('video')" in html
        assert "Download JSON response" in html
        assert "baseline" not in html and "refined" not in html
        assert "crypto proof" not in html
        assert "NOT_YET_AUTHORIZED" in (p/"packet_metadata.json").read_text()
    admin=out/"ADMIN_NOT_FOR_RATERS"
    assert json.loads((admin/"assignment_AND_SOURCE_DO_NOT_SHARE.json").read_text())==manifest_source_agnostic(receipt,admin)
    with pytest.raises(QualityEvidenceError,match="DO_NOT_OVERWRITE_REVIEW_PACKET"):
        create_packets(media_root=source,output_dir=out)

def manifest_source_agnostic(receipt,admin):
    # Test that an explicit admin manifest exists and its provenance is the same.
    m=json.loads((admin/"assignment_AND_SOURCE_DO_NOT_SHARE.json").read_text())
    assert m["media"]==receipt["media"]
    return m

def _synthetic_submission(m,rid,delta=1):
    """SYNTHETIC UNIT FIXTURE, NEVER USED AS EXPERIMENTAL OR HUMAN RESULTS."""
    c=_rater_config(m,rid)
    outcomes={}
    for label,variant in m["rater_assignment"][rid].items():
        k=3+(delta if variant=="refined" else 0)
        outcomes[label]={
            "ratings":{dimension:k for dimension in DIMS},
            "critical_error":"no","observation_seconds":26.75,
            "observation":"All pointer movements are legible at sample time",
            "transfer_answer":"The first equal value is at index 1 because earlier matches must be checked",
            "player_reached_end":True,"media_sha256":c["media_sha256"][label],
        }
    return {"schema_version":"v3-25-rater-response-v1",
            "study_id":STUDY,"reviewer_id":rid,
            "package_sha256":c["package_sha256"],
            "self_reported_consent":True,
            "self_reported_independent_review":True,
            "viewing_screen_inches":15.6,"viewing_distance_cm":60,
            "submitted_at_utc":"2026-10-09T00:00:00Z",
            "mechanism":"OFFLINE_BROWSER_SELF_REPORT_NOT_IDENTITY_PROOF",
            "submissions":outcomes}

def test_no_submissions_means_no_human_result(manifest):
    result=inspect_submissions(admin_manifest=manifest,responses=[])
    assert result["state"]=="NO_REAL_INDEPENDENT_RATINGS"
    assert result["primary_metrics"]=="UNMEASURED"
    assert result["student_ready"]==result["publication"]=="BLOCKED"

def test_single_response_is_incomplete_not_pass(manifest):
    report=inspect_submissions(admin_manifest=manifest,
                               responses=[_synthetic_submission(manifest,"R01")])
    assert report["state"]=="INCOMPLETE_SELF_REPORTED_DATA"
    assert report["primary_metrics"]=="UNMEASURED"

def test_two_synthetic_responses_are_still_not_human_approval(manifest):
    reports=[_synthetic_submission(manifest,rid) for rid in RATERS]
    result=inspect_submissions(admin_manifest=manifest,responses=reports)
    assert result["received_submissions"]==2
    assert result["state"]=="TWO_UNVERIFIED_SELF_REPORTS_NOT_HUMAN_STUDY_PASS"
    assert result["descriptive_deltas_refined_minus_baseline"]["clarity"]["mean"]==1
    assert result["descriptive_deltas_refined_minus_baseline"]["representation_adequacy"]["values"]==[1,1]
    assert result["human_independence_verified"] is False
    assert result["student_ready"]==result["publication"]=="BLOCKED"

def test_adjudicator_trigger_is_explicit_not_fake_blind_rater(manifest):
    x=_synthetic_submission(manifest,"R01",delta=1)
    y=_synthetic_submission(manifest,"R02",delta=-1)
    # Difference in primary ratings between the rater slots for the refined
    # video reaches 2; no adjudicator exists, so no adjudicated result.
    result=inspect_submissions(admin_manifest=manifest,responses=[x,y])
    assert result["third_independent_adjudicator_required"] is True
    assert "clarity" in result["primary_rater_disagreements"]["refined"]
    assert result["student_ready"]=="BLOCKED"

@pytest.mark.parametrize("mutator",[
    lambda x: x.update({"reviewer_id":"R99"}),
    lambda x: x.update({"package_sha256":"f"*64}),
    lambda x: x.update({"self_reported_consent":False}),
    lambda x: x["submissions"]["A"]["ratings"].update({"clarity":6}),
    lambda x: x["submissions"]["A"].update({"media_sha256":"0"*64}),
    lambda x: x["submissions"]["B"].update({"player_reached_end":False}),
    lambda x: x["submissions"]["B"].update({"observation_seconds":99}),
    lambda x: x["submissions"].pop("A"),
])
def test_fraud_and_incomplete_input_rejected(manifest,mutator):
    x=_synthetic_submission(manifest,"R01")
    mutator(x)
    with pytest.raises(QualityEvidenceError,match="V3_25_"):
        inspect_submissions(admin_manifest=manifest,responses=[x])

def test_duplicate_rater_and_forged_manifest_rejected(manifest):
    x=_synthetic_submission(manifest,"R01")
    with pytest.raises(QualityEvidenceError,match="DUPLICATE_REVIEWER"):
        inspect_submissions(admin_manifest=manifest,responses=[x,copy.deepcopy(x)])
    f=copy.deepcopy(manifest)
    f["human_recruitment_authorized"]=True
    with pytest.raises(QualityEvidenceError,match="FALSE_HUMAN_OR_BLINDING_CLAIM"):
        inspect_submissions(admin_manifest=f,responses=[])
