"""TEST_ONLY V3-70 synthetic CSV mutations, never actual human scores."""
from __future__ import annotations
import copy
import csv
import json
from pathlib import Path

import pytest

from scripts.run_v3_60_independent_review import (
    CRITERIA, FIELDS, ReviewBlocked, load_ratings, spec, template_rows
)
from scripts import run_v3_70_review_intake as intake


def simulated_private_panel(tmp_path: Path):
    """Fake in-memory/test-temp submissions only, never uploaded as evidence."""
    source = tmp_path / "TEST_ONLY_SCORES_NOT_REAL"
    source.mkdir()
    attest = {
        "checkpoint": "V3-70",
        "coordinator_confirmed_no_admin_mapping_seen": True,
        "reviewers": {},
    }
    for i in range(3):
        rid = f"reviewer_{i + 1:02d}"  # fictional names, test scope only
        rows = template_rows(spec(), i)
        for row in rows:
            row["rater_id"] = rid
            row.update({criterion: "3" for criterion in CRITERIA})
            row["confidence"] = "3"
            row["watched_full_video"] = "YES"
            row["replay_count"] = "0"
        with (source / f"synthetic_{i + 1}.csv").open(
                "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        attest["reviewers"][rid] = {
            "form_number": i + 1,
            **{flag: True for flag in intake.FLAGS},
        }
    attest_path = tmp_path / "TEST_ONLY_DECLARATIONS.json"
    attest_path.write_text(json.dumps(attest), encoding="utf-8")
    return source, attest_path


def mutate_csv(path: Path, function):
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    function(rows)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_parent_and_source_protocols_frozen():
    reg = intake.verified_prereg()
    assert reg["parent"]["draft_pr"] == 105
    assert reg["frozen_inputs"]["source_clips"] == 9
    assert reg["limitations"]["real_reviewers"] == 0
    assert reg["safety"]["model_posts"] == 0


def test_fake_positive_only_checks_structure_not_real_humans(tmp_path):
    source, declaration = simulated_private_panel(tmp_path)
    out = tmp_path / "TEST_ONLY_LOCAL_SEAL_NOT_HUMAN_EVIDENCE"
    result = intake.collect(source, declaration, out)
    assert result["intake"] == "LOCAL_BLIND_SCORES_LOCKED"
    assert not result["human_independence_verified_by_code"]
    assert result["pedagogical_quality"] == "UNRATED"
    ratings = out / "complete_ratings.csv"
    rows, raters = load_ratings(ratings)
    assert len(rows) == 27 and len(raters) == 3
    lock = json.loads((out / "locked_scores.json").read_text())
    assert lock["sha256_raw_csv"] == intake.hashlib.sha256(ratings.read_bytes()).hexdigest()
    receipt = json.loads((out / "intake_receipt.json").read_text())
    assert receipt["treatment_mapping"] == "WITHHELD"
    assert receipt["treatment_key_access"] == 0
    assert len(list(out.iterdir())) == 3


@pytest.mark.parametrize("mutation,expected", [
    (lambda r: r.pop(), "NINE_VALID_ROWS"),
    (lambda r: r.append(copy.deepcopy(r[0])), "NINE_VALID_ROWS"),
    (lambda r: r[0].update(clarity=""), "MISSING_OR_INVALID_ORDINAL"),
    (lambda r: r[0].update(clarity="6"), "MISSING_OR_INVALID_ORDINAL"),
    (lambda r: r[0].update(clarity="1", timestamp_failure_notes=""), "LOW_SCORE_NEEDS_TIMESTAMP"),
    (lambda r: r[0].update(watched_full_video="NO"), "PARTIAL_WATCH"),
    (lambda r: r[0].update(timestamp_failure_notes="=HYPERLINK(0)"), "CSV_FORMULA_INJECTION"),
    (lambda r: r[0].update(clip_id="forged_A.mp4"), "FROZEN_FORM_ORDER_DRIFT"),
    (lambda r: r.reverse(), "FROZEN_FORM_ORDER_DRIFT"),
    (lambda r: r[0].update(rater_id="TEST_ONLY_R1"), "ONE_REVIEWER_PER_FILE"),
])
def test_malformed_review_packet_blocks_without_output(tmp_path, mutation, expected):
    source, declaration = simulated_private_panel(tmp_path)
    mutate_csv(source / "synthetic_1.csv", mutation)
    output = tmp_path / "must_not_exist"
    with pytest.raises(ReviewBlocked, match=expected):
        intake.collect(source, declaration, output)
    assert not output.exists()


def test_all_rows_with_test_only_identity_rejected(tmp_path):
    source, declaration = simulated_private_panel(tmp_path)
    mutate_csv(source / "synthetic_1.csv",
               lambda rows: [x.update(rater_id="TEST_ONLY_R1") for x in rows])
    d = json.loads(declaration.read_text())
    d["reviewers"]["TEST_ONLY_R1"] = d["reviewers"].pop("reviewer_01")
    declaration.write_text(json.dumps(d))
    with pytest.raises(ReviewBlocked, match="TEST_OR_AUTOMATED_REVIEWER"):
        intake.collect(source, declaration, tmp_path / "result")


@pytest.mark.parametrize("modify,expected", [
    (lambda a: a.update(coordinator_confirmed_no_admin_mapping_seen=False),
     "ATTESTATION_SCHEMA_OR_PREMATURE_UNBLIND"),
    (lambda a: a["reviewers"]["reviewer_01"].update(consented=False),
     "CONSENT_ELIGIBILITY_OR_INDEPENDENCE_UNCONFIRMED"),
    (lambda a: a["reviewers"]["reviewer_01"].update(external_human=False),
     "CONSENT_ELIGIBILITY_OR_INDEPENDENCE_UNCONFIRMED"),
    (lambda a: a["reviewers"]["reviewer_01"].update(eligible=False),
     "CONSENT_ELIGIBILITY_OR_INDEPENDENCE_UNCONFIRMED"),
    (lambda a: a["reviewers"]["reviewer_02"].update(form_number=1),
     "UNIQUE_COUNTERBALANCED_FORM"),
    (lambda a: a["reviewers"].pop("reviewer_01"),
     "REVIEWER_ATTESTATION_MISSING"),
])
def test_false_or_missing_private_assertion_blocks(tmp_path, modify, expected):
    source, declaration = simulated_private_panel(tmp_path)
    a = json.loads(declaration.read_text())
    modify(a)
    declaration.write_text(json.dumps(a))
    with pytest.raises(ReviewBlocked, match=expected):
        intake.collect(source, declaration, tmp_path / "result")


def test_incomplete_duplicate_and_admin_files_block(tmp_path):
    source, declaration = simulated_private_panel(tmp_path)
    (source / "synthetic_1.csv").unlink()
    with pytest.raises(ReviewBlocked, match="EXACT_THREE_ORIGINAL_CSVS_ONLY"):
        intake.collect(source, declaration, tmp_path / "result")
    (source / "synthetic_1.csv").write_bytes((source / "synthetic_2.csv").read_bytes())
    with pytest.raises(ReviewBlocked, match="DUPLICATE_REVIEWER_ID"):
        intake.collect(source, declaration, tmp_path / "result")
    (source / "admin_treatment_key.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ReviewBlocked, match="EXACT_THREE_ORIGINAL_CSVS_ONLY"):
        intake.collect(source, declaration, tmp_path / "result")


def test_symlink_and_preexisting_output_block(tmp_path):
    source, declaration = simulated_private_panel(tmp_path)
    p = source / "synthetic_1.csv"
    p.unlink()
    p.symlink_to(source / "synthetic_2.csv")
    with pytest.raises(ReviewBlocked, match="EXACT_THREE_ORIGINAL_CSVS_ONLY"):
        intake.collect(source, declaration, tmp_path / "result")
    result = tmp_path / "existing"
    result.mkdir()
    with pytest.raises(ReviewBlocked, match="DESTINATION_MUST_BE_NEW"):
        intake.collect(source, declaration, result)


def test_zero_human_inputs_never_creates_receipt(tmp_path):
    src = tmp_path / "empty"
    src.mkdir()
    with pytest.raises(ReviewBlocked, match="EXACT_THREE_ORIGINAL_CSVS_ONLY"):
        intake.collect(src, tmp_path / "none.json", tmp_path / "out")
    assert not (tmp_path / "out").exists()
