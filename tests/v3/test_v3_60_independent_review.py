"""V3-60 offline tests: no synthetic rows are represented as human evidence."""
from __future__ import annotations

import copy
import csv
import json
from pathlib import Path

import pytest

from scripts.run_v3_60_independent_review import (
    CRITERIA, FIELDS, ReviewBlocked, spec, template_rows, load_ratings,
    seal_ratings, validate_admin, analyze, write_csv, verify_packet
)


def fake_ratings():
    """Counterfeit TEST-ONLY inputs; never save them as evidence."""
    x = spec()
    lines = []
    for i in range(3):
        rater = f"TEST_ONLY_R{i+1}"
        for row in template_rows(x, i):
            row["rater_id"] = rater
            row.update({criterion: "3" for criterion in CRITERIA})
            row["confidence"] = "3"
            row["watched_full_video"] = "YES"
            row["replay_count"] = "0"
            lines.append(row)
    return lines


def stub_admin():
    """Arbitrary synthetic permutation, explicitly NOT the real admin key."""
    reg = spec()
    groups = {}
    for case in reg["frozen_cases"]:
        groups[case] = {}
        for i, label in enumerate("ABC"):
            clip = f"{case}_{label}.mp4"
            groups[case][clip] = {
                "treatment": ("original_motion", "static_end_state",
                              "causal_reveal")[i],
                "sha256": reg["masked_clips_sha256"][clip]
            }
    return {"cases": groups}


def test_v360_first_commit_fixed_native_provenance_and_nonclaims():
    r = spec()
    assert r["registered_before_implementation"] is True
    assert r["parent_sha"].startswith("506b3ccf")
    assert r["frozen_clip_count"] == 9
    assert r["reviewer_protocol"]["min_independent_external_reviewers"] == 3
    assert r["acceptance"]["record_reviewers_currently"] == 0
    assert r["acceptance"]["learning_gain"] == "NOT_MEASURED"
    assert r["acceptance"]["human_quality"] == "UNRATED_PENDING_EXTERNAL_PANEL"
    assert r["acceptance"]["production"] == "BLOCKED"


def test_masked_forms_rotate_without_exposing_treatments():
    reg = spec()
    groups = [template_rows(reg, i) for i in range(3)]
    assert len({tuple(row["clip_id"] for row in group) for group in groups}) == 3
    assert all(len(group) == 9 for group in groups)
    for group in groups:
        assert set(row["clip_id"] for row in group) == set(reg["masked_clips_sha256"])
        assert all(row["rater_id"] == "" and
                   all(row[c] == "" for c in CRITERIA) for row in group)
        assert all("causal_reveal" not in json.dumps(row) for row in group)


def test_strict_complete_9_clips_x_3_rater_panel_and_blind_score_lock(tmp_path):
    ratings = tmp_path/"TEST_ONLY_DO_NOT_SHIP.csv"
    rows = fake_ratings()
    write_csv(ratings, rows)
    actual, rater_ids = load_ratings(ratings)
    assert len(actual) == 27 and len(rater_ids) == 3
    lock_path = tmp_path/"sealed.json"
    lock = seal_ratings(ratings, lock_path)
    assert lock["lock_state"] == "BLIND_SCORES_LOCKED"
    assert lock["treatment_mapping_seen"] is False
    assert "learning_gain" in lock and lock["production"] == "BLOCKED"
    with pytest.raises(ReviewBlocked, match="LOCK_EXISTS"):
        seal_ratings(ratings, lock_path)


@pytest.mark.parametrize("mutate,error", [
    (lambda rows: rows.pop(), "INCOMPLETE_PANEL_REVIEWER"),
    (lambda rows: rows.append(copy.deepcopy(rows[0])), "DUPLICATE_RATING"),
    (lambda rows: rows[0].update(clarity=""), "MISSING_OR_INVALID_ORDINAL"),
    (lambda rows: rows[0].update(clarity="6"), "MISSING_OR_INVALID_ORDINAL"),
    (lambda rows: rows[0].update(watched_full_video="NO"), "PARTIAL_WATCH"),
    (lambda rows: rows[0].update(confidence="unverified"), "MISSING_OR_INVALID_ORDINAL"),
    (lambda rows: rows[0].update(replay_count="-1"), "REPLAY_COUNT"),
    (lambda rows: rows[0].update(clarity="1",timestamp_failure_notes=""),
     "LOW_SCORE_NEEDS_TIMESTAMP"),
    (lambda rows: rows[0].update(clip_id="fake_A.mp4"), "UNKNOWN_CLIP"),
    (lambda rows: rows[0].update(rater_id="Bad Name"), "REVIEWER_PSEUDONYM"),
])
def test_negative_malformed_reviews_fail_closed(tmp_path, mutate, error):
    rows = fake_ratings()
    mutate(rows)
    path = tmp_path/"invalid.csv"
    write_csv(path, rows)
    with pytest.raises(ReviewBlocked, match=error):
        load_ratings(path)


def test_no_real_scores_and_no_admin_key_means_no_inference(tmp_path):
    with pytest.raises(ReviewBlocked, match="NO_RATINGS"):
        path = tmp_path/"empty.csv"
        write_csv(path, [])
        load_ratings(path)
    # Missing frozen physical clips cannot be substituted with mock media.
    with pytest.raises(ReviewBlocked, match="MISSING_EXTRA_OR_RENAMED_CLIPS"):
        verify_packet(tmp_path)


def test_admin_key_rejects_forged_shas_treatment_or_unregistered_clips():
    key = stub_admin()
    validate_admin(key)
    example = next(iter(key["cases"]))
    clip = next(iter(key["cases"][example]))
    forged = copy.deepcopy(key)
    forged["cases"][example][clip]["sha256"] = "0"*64
    with pytest.raises(ReviewBlocked, match="ADMIN_HASH_DRIFT"):
        validate_admin(forged)
    forged = copy.deepcopy(key)
    forged["cases"][example][clip]["treatment"] = "static_end_state"
    with pytest.raises(ReviewBlocked, match="ADMIN_TREATMENT_INCOMPLETE"):
        validate_admin(forged)


def test_after_lock_report_is_only_provisional_even_for_test_only_rows(tmp_path):
    ratings = tmp_path/"DO_NOT_USE_AS_HUMAN_EVIDENCE.csv"
    write_csv(ratings, fake_ratings())
    lock_path = tmp_path/"lock.json"
    seal_ratings(ratings, lock_path)
    rater_ids = [f"TEST_ONLY_R{i+1}" for i in range(3)]
    attest_path = tmp_path/"TEST_ONLY_ATTESTATIONS.json"
    attest_path.write_text(json.dumps({"reviewers": {i: {
        "consented": True, "external_human": True,
        "conflict_disclosed": True, "reviewer_confirmed_no_collaboration": True
    } for i in rater_ids}}))
    admin_path = tmp_path/"TEST_ONLY_ADMIN.json"
    admin_path.write_text(json.dumps(stub_admin()))
    output = tmp_path/"TEST_ONLY_REPORT.json"
    result = analyze(ratings, lock_path, admin_path, attest_path, output)
    assert result["rater_count_claimed"] == 3
    assert result["prespecified_directional_screen"] == "FAIL"
    assert result["quality_gate"] == "PENDING_MANUAL_PROVENANCE_AND_REVIEWER_AUDIT"
    assert result["student_learning_gain"] == "NOT_MEASURED"
    assert result["production"] == "BLOCKED"
    # Mutating submitted review file after unblinding invalidates its seal.
    corrupted = list(csv.DictReader(ratings.open()))
    corrupted[0]["pacing"] = "5"
    write_csv(ratings, corrupted)
    with pytest.raises(ReviewBlocked, match="UNSEALED_OR_EDITED_RATINGS"):
        analyze(ratings, lock_path, admin_path, attest_path, tmp_path/"other.json")


def test_no_artifactual_audit_if_missing_provenance(tmp_path):
    ratings = tmp_path/"TEST_ONLY.csv"
    write_csv(ratings, fake_ratings())
    lock_path = tmp_path/"lock.json"
    seal_ratings(ratings, lock_path)
    bad = tmp_path/"bad.json"
    bad.write_text(json.dumps({"reviewers": {}}))
    admin = tmp_path/"admin.json"
    admin.write_text(json.dumps(stub_admin()))
    with pytest.raises(ReviewBlocked, match="ATTESTATION_IDS"):
        analyze(ratings, lock_path, admin, bad, tmp_path/"out.json")
