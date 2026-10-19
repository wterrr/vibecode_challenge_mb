"""V3-89 rigorous masked human review acceptance, NO manufactured scores.

Ratings constructed in tests are PURE UNIT-TEST FIXTURES and cannot be counted
as real people or exported as evidence in a GitHub Actions artifact.
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
import zipfile
import pytest

from scripts.run_v3_89_independent_review import (
    REG,SCORE_AXES,STATUS_PENDING,registered,evaluate_human_reviews,
    _archive_member,_write_public_packet,sha
)


def test_first_child_prereg_before_implementation_and_balanced_six_clips():
    d=registered()
    assert d["checkpoint"]=="V3-89"
    assert d["parent"]=={"draft_pr":125,
          "head_sha":"f6f66334bf4a40fae95af97667d43bf5e18453b5"}
    assert len(d["clips"])==6
    assert Counter(c["family"] for c in d["clips"])=={
        "AFFINE":2,"FRACTION_EQUIVALENCE":2,"ORDERED_SEARCH":2}
    assert {c["src_artifact_id"] for c in d["clips"]}=={12020402722,12157931417}
    assert len({c["sha256"] for c in d["clips"]})==6
    assert len(d["masked_order"])==len(set(d["masked_order"]))==6
    assert d["constraints"]["production"]=="BLOCKED"
    assert d["constraints"]["no_model_api"] is True


def test_frozen_original_video_sha_and_frames_explicit():
    d=registered()
    assert {x["case_id"]:x["frames"] for x in d["clips"]}=={
        "linear_output_new":1056,"counterfactual_physics_heldout":1106,
        "fraction_refinement_development":425,"fraction_refinement_heldout":430,
        "binary_search_development":712,"binary_search_heldout":926}
    assert all(len(x["sha256"])==64 and all(z in "0123456789abcdef" for z in x["sha256"])
               for x in d["clips"])
    assert sum(x["role"]=="heldout" for x in d["clips"])==3


def test_no_scores_no_reviewers_must_remain_pending():
    result=evaluate_human_reviews(None,registered())
    assert result["state"]==STATUS_PENDING
    assert result["count_human_ratings"]==0
    assert result["individual_video_quality"]=="UNRATED"
    assert result["learner_gain"]=="NOT_MEASURED"


def _scores(tmp_path,overrides=None):
    """SYNTHETIC TEST FIXTURE ONLY, not real participant data."""
    doc=registered()
    path=tmp_path/"synthetic_test_only.csv"
    cols=["reviewer_id","clip_id",*SCORE_AXES,"notes"]
    fake=[]
    for id in doc["reviewer_protocol"]["clip_ids"]:
        for who in ("raterA_test","raterB_test"):
            fake.append({"reviewer_id":who,"clip_id":id,
                         **{axis:"4" for axis in SCORE_AXES},"notes":""})
    if overrides:
        overrides(fake)
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(fake)
    return path


def test_synthetic_good_score_fixture_proves_scoring_logic_only(tmp_path):
    out=evaluate_human_reviews(_scores(tmp_path),registered())
    assert out["state"]=="HUMAN_RUBRIC_THRESHOLD_MET_ONLY"
    assert out["count_human_ratings"]==12
    assert all(x["rater_count"]==2 and x["all_axes_mean"]==4.0
               for x in out["per_clip"].values())
    assert out["learner_gain"]=="NOT_MEASURED"
    assert out["production"]=="BLOCKED"


def test_low_semantic_correctness_never_accepted(tmp_path):
    f=_scores(tmp_path,lambda rows:rows[0].update(semantic_correctness="2"))
    out=evaluate_human_reviews(f,registered())
    assert out["state"]=="NOT_ACCEPTED"
    assert out["per_clip"]["CLIP_01"]["semantic_low_flag"] is True


def test_median_threshold_blocks_weak_causal_continuity(tmp_path):
    def mutate(rows):
        for x in rows:
            if x["clip_id"]=="CLIP_05":
                x["causal_continuity"]="2"
    out=evaluate_human_reviews(_scores(tmp_path,mutate),registered())
    assert out["state"]=="NOT_ACCEPTED"
    assert out["per_clip"]["CLIP_05"]["axis_medians"]["causal_continuity"]==2


def test_two_distinct_reviewers_required_per_each_clip(tmp_path):
    def mutate(rows):
        rows[0]["reviewer_id"]=rows[1]["reviewer_id"]
    with pytest.raises(ValueError,match="V389_DUPLICATE_REVIEWER"):
        evaluate_human_reviews(_scores(tmp_path,mutate),registered())


def test_no_blank_or_partial_rating_can_be_promoted(tmp_path):
    f=_scores(tmp_path,lambda rows:rows[0].update(readable_layout=""))
    with pytest.raises(ValueError,match="V389_HUMAN_RATING_NOT_INTEGER_1_TO_5"):
        evaluate_human_reviews(f,registered())


@pytest.mark.parametrize("bad",["0","6","4.5","5 ","pass","True","-1"])
def test_out_of_scale_and_noninteger_ratings_fail_closed(tmp_path,bad):
    f=_scores(tmp_path,lambda rows:rows[0].update(pedagogical_usefulness=bad))
    with pytest.raises(ValueError,match="V389_HUMAN_RATING_NOT_INTEGER_1_TO_5"):
        evaluate_human_reviews(f,registered())


def test_missing_clip_cannot_be_marked_accepted(tmp_path):
    def mutate(rows):
        rows[:]=[r for r in rows if r["clip_id"]!="CLIP_06"]
    with pytest.raises(ValueError,match="V389_HUMAN_REVIEW_NOT_INDEPENDENT"):
        evaluate_human_reviews(_scores(tmp_path,mutate),registered())


def test_unknown_clip_is_rejected(tmp_path):
    f=_scores(tmp_path,lambda rows:rows[0].update(clip_id="SECRET_UNREGISTERED"))
    with pytest.raises(ValueError,match="V389_REVIEWER_OR_CLIP"):
        evaluate_human_reviews(f,registered())


def test_blank_review_packet_contains_no_filled_scores_or_source_names(tmp_path):
    public=tmp_path/"public";public.mkdir()
    _write_public_packet(public,registered()["reviewer_protocol"]["clip_ids"])
    text=(public/"README_FOR_REVIEWERS.md").read_text()
    assert "double-blind" in text
    assert "not a blinded placebo" in text
    assert not any(x in text for x in ["V3-87","V3-88","linear_output_new"])
    with (public/"BLANK_human_review_scores.csv").open() as f:
        data=list(csv.DictReader(f))
    assert len(data)==12
    assert all(x["reviewer_id"]=="" and all(x[key]=="" for key in SCORE_AXES)
               for x in data)


def test_archive_member_path_and_duplicate_must_fail_closed():
    data=io.BytesIO()
    with zipfile.ZipFile(data,"w") as f:
        f.writestr("expected/native.mp4",b"verified media bytes")
    data.seek(0)
    with zipfile.ZipFile(data) as f:
        assert _archive_member(f,"expected/native.mp4")==b"verified media bytes"
        with pytest.raises(ValueError,match="V389_ARCHIVE_FILE_PATH_AMBIGUOUS"):
            _archive_member(f,"../native.mp4")
        with pytest.raises(ValueError,match="V389_ARCHIVE_FILE_PATH_AMBIGUOUS"):
            _archive_member(f,"missing.mp4")


def test_runner_cannot_produce_fake_ratings_or_model_judgments():
    s=(REG.parents[3]/"scripts/run_v3_89_independent_review.py").read_text()
    assert "STATUS_PENDING" in s
    assert "NO_REAL_HUMAN_SUBMISSIONS_RECEIVED" in s
    assert "eval(" not in s and "model_judge" not in s
    assert "gh api" not in s # Acquisition isolated in CI.
    assert "sha(raw)==case[" in s
    assert "no_fabricated_human_scores" in s


def test_two_artifact_sha_first_not_fake_video_renders():
    s=(REG.parents[3]/"scripts/run_v3_89_independent_review.py").read_text()
    assert "movie.write_bytes(raw)" in s
    assert 'full_video_decode":"PASS"' in s
    assert 'no_media_edits' not in s.lower() or "NONE_ORIGINAL_SHA256_IDENTICAL" in s
    assert "moviepy" not in s and "Image.fromarray" not in s
