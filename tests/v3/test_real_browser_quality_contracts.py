"""V3-26 review issue taxonomy, source-bound negative cases and no invented human result."""
from __future__ import annotations
import copy
import os
from pathlib import Path
import pytest

from learnflow_v3.independent_quality_pilot import (
    DIMS,RATERS,make_manifest,_rater_config,inspect_submissions,
    ISSUE_CATEGORIES,attest_source_manifest
)
from learnflow_v3.lesson_quality import QualityEvidenceError

@pytest.fixture(scope="module")
def actual_media():
    return Path(os.environ["V3_25_MEDIA_DIR"])

@pytest.fixture(scope="module")
def manifest(actual_media):
    return make_manifest(actual_media)

def fake_browser_record(manifest,rid):
    """Never export these synthetic fixtures as any human study outcome."""
    config=_rater_config(manifest,rid)
    clips={}
    for label,variant in manifest["rater_assignment"][rid].items():
        clips[label]={
            "ratings":{k:3 for k in DIMS},
            "critical_error":"no",
            "issue_category":"readability" if label=="A" else "pedagogy",
            "observation_seconds":26.75,
            "observation":"Synthetic browser testing, not a real human rating",
            "transfer_answer":"Synthetic only: examine leftmost index",
            "player_reached_end":True,
            "media_sha256":config["media_sha256"][label]
        }
    return {
        "schema_version":"v3-25-rater-response-v1",
        "study_id":manifest["study_id"],
        "reviewer_id":rid,
        "package_sha256":config["package_sha256"],
        "self_reported_consent":True,
        "self_reported_independent_review":True,
        "viewing_screen_inches":15.6,
        "viewing_distance_cm":60,
        "submitted_at_utc":"2026-10-09T00:00:00Z",
        "mechanism":"OFFLINE_BROWSER_SELF_REPORT_NOT_IDENTITY_PROOF",
        "submissions":clips
    }

def test_issue_taxonomy_explicit_covers_all_required_categories():
    assert set(("aesthetic","readability","pedagogy","technical","audio"))<=set(ISSUE_CATEGORIES)
    assert "no_issue" in ISSUE_CATEGORIES
    assert set(DIMS)>=set(("clarity","representation_adequacy"))

def test_real_source_video_provenance_and_frozen_scope(actual_media,manifest):
    attest_source_manifest(admin_manifest=manifest,media_root=actual_media)
    assert manifest["media"]["visual_only_change"] is True
    assert manifest["media"]["size"]==[1280,720]
    assert manifest["human_recruitment_authorized"] is False
    assert manifest["excluded_from_frozen_v3_16_confirmatory_12_topic_benchmark"] is True

def test_two_synthetic_browser_responses_produce_only_self_report_inventory(manifest):
    rows=[fake_browser_record(manifest,r) for r in RATERS]
    result=inspect_submissions(admin_manifest=manifest,responses=rows)
    assert result["state"]=="TWO_UNVERIFIED_SELF_REPORTS_NOT_HUMAN_STUDY_PASS"
    assert result["issue_counts_by_category_self_reported"]["readability"]==2
    assert result["issue_counts_by_category_self_reported"]["pedagogy"]==2
    assert len(result["timestamped_issue_inventory_self_reported"])==4
    assert {x["timestamp_seconds"] for x in result["timestamped_issue_inventory_self_reported"]}=={26.75}
    assert {x["variant_admin_only"] for x in result["timestamped_issue_inventory_self_reported"]}=={"baseline","refined"}
    assert result["student_ready"]==result["publication"]=="BLOCKED"
    assert result["human_independence_verified"] is False
    assert result["unseen_learning_gain"]=="UNMEASURED"

def test_legacy_v325_rater_data_cannot_be_silently_called_new_category(manifest):
    rows=[fake_browser_record(manifest,r) for r in RATERS]
    for row in rows:
        for video in row["submissions"].values():
            del video["issue_category"]
    result=inspect_submissions(admin_manifest=manifest,responses=rows)
    assert result["issue_counts_by_category_self_reported"]["unclassified_legacy"]==4
    assert result["student_ready"]=="BLOCKED"

@pytest.mark.parametrize("tampered",["nonsense","injection","human_verified",""])
def test_invalid_issue_categories_rejected(manifest,tampered):
    record=fake_browser_record(manifest,"R01")
    record["submissions"]["A"]["issue_category"]=tampered
    with pytest.raises(QualityEvidenceError,match="V3_25_MISSING_TIMESTAMP_OR_RATIONALE"):
        inspect_submissions(admin_manifest=manifest,responses=[record])

def test_missing_rating_or_source_sha_rejected(manifest):
    x=fake_browser_record(manifest,"R01")
    del x["submissions"]["A"]["ratings"]["clarity"]
    with pytest.raises(QualityEvidenceError,match="V3_25_MISSING_OR_INVALID_RUBRIC"):
        inspect_submissions(admin_manifest=manifest,responses=[x])
    x=fake_browser_record(manifest,"R01")
    x["submissions"]["B"]["media_sha256"]="f"*64
    with pytest.raises(QualityEvidenceError,match="V3_25_VIDEO_SHA_OR_UNWATCHED"):
        inspect_submissions(admin_manifest=manifest,responses=[x])

def test_unrun_is_explicitly_unmeasured(manifest):
    report=inspect_submissions(admin_manifest=manifest,responses=[])
    assert report["received_submissions"]==0
    assert report["state"]=="NO_REAL_INDEPENDENT_RATINGS"
    assert report["primary_metrics"]=="UNMEASURED"
    assert report["human_independence_verified"] is False
    assert report["student_ready"]==report["publication"]=="BLOCKED"
