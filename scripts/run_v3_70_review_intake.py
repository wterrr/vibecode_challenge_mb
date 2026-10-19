#!/usr/bin/env python3
"""Offline V3-70 coordinator intake; cannot independently prove human identity.

Never handles the unblinding admin key or sends network requests. Real human
consent and independent review must be audited outside software.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_v3_60_independent_review import (
    FIELDS, ReviewBlocked, load_ratings, seal_ratings, spec, template_rows, write_csv
)

REG = ROOT / "benchmarks/learnflowbench/v3/v3_70_review_intake_preregister.json"
V360 = ROOT / "benchmarks/learnflowbench/v3/v3_60_independent_review_preregister.json"
V361 = ROOT / "benchmarks/learnflowbench/v3/v3_61_offline_review_ui_preregister.json"
SOURCE_V360_BLOB = "dbf16ee2bbf1e338cab73c8e521551637044c952"
SOURCE_V361_BLOB = "d2ced41d097f9b691ae5fec538aaa149c6169543"
FLAGS = (
    "consented", "external_human", "eligible", "conflict_disclosed",
    "reviewer_confirmed_no_collaboration",
    "coordinator_checked_original_consent_privately",
    "coordinator_checked_distinct_individual_privately",
)
BANNED_ID = ("TEST_ONLY", "SIMULAT", "FAKE_", "BOT_", "AUTOMATED")


def require(ok: bool, code: str) -> None:
    if not ok:
        raise ReviewBlocked("V370_" + code)


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def verified_prereg() -> dict:
    reg = json.loads(REG.read_text(encoding="utf-8"))
    require(reg["checkpoint"] == "V3-70" and
            reg["registration_kind"] == "FIRST_CHILD_COMMIT_BEFORE_IMPLEMENTATION" and
            reg["parent"]["sha"] == "0af94a9da619caaffd0c43959d5109fd0058bf48",
            "PREREG_DRIFT")
    require(git_blob_sha(V360.read_bytes()) == SOURCE_V360_BLOB and
            git_blob_sha(V361.read_bytes()) == SOURCE_V361_BLOB,
            "ORIGINAL_PROTOCOL_DRIFT")
    frozen = reg["frozen_inputs"]
    require(frozen["v360_prereg_blob_sha"] == SOURCE_V360_BLOB and
            frozen["v361_prereg_blob_sha"] == SOURCE_V361_BLOB and
            frozen["source_clips"] == 9 and frozen["expected_raters"] == 3,
            "SOURCE_FREEZE_DRIFT")
    require(spec()["acceptance"]["record_reviewers_currently"] == 0,
            "UNVERIFIED_RATINGS_LAUNDERED")
    return reg


def read_one(path: Path) -> tuple[str, list[dict], str]:
    require(path.is_file() and not path.is_symlink() and path.suffix == ".csv",
            "BAD_INPUT_FILE")
    require(0 < path.stat().st_size <= 65536, "INPUT_SIZE")
    raw = path.read_bytes()
    try:
        with io.StringIO(raw.decode("utf-8-sig"), newline="") as stream:
            reader = csv.DictReader(stream)
            require(tuple(reader.fieldnames or ()) == FIELDS, "RATINGS_SCHEMA")
            rows = list(reader)
    except (UnicodeError, csv.Error) as exc:
        raise ReviewBlocked("V370_CSV_PARSE") from exc
    require(len(rows) == 9 and all(None not in row for row in rows),
            "NINE_VALID_ROWS")
    ids = {row["rater_id"].strip() for row in rows if row["rater_id"] is not None}
    require(len(ids) == 1, "ONE_REVIEWER_PER_FILE")
    rid = next(iter(ids))
    require(rid and not any(token in rid.upper() for token in BANNED_ID),
            "TEST_OR_AUTOMATED_REVIEWER")
    for row in rows:
        require(row["rater_id"] == rid, "REVIEWER_WHITESPACE_OR_MIXED")
        notes = row["timestamp_failure_notes"]
        require(notes is not None and
                not notes.lstrip(" \t\r\n\ufeff").startswith(("=", "+", "-", "@")),
                "CSV_FORMULA_INJECTION")
    return rid, rows, hashlib.sha256(raw).hexdigest()


def audited(submissions: Path, declarations: Path) -> dict:
    verified_prereg()
    require(submissions.is_dir() and not submissions.is_symlink(),
            "MISSING_SUBMISSIONS")
    files = sorted(submissions.iterdir())
    require(len(files) == 3 and all(p.is_file() and not p.is_symlink() and
                                      p.suffix == ".csv" for p in files),
            "EXACT_THREE_ORIGINAL_CSVS_ONLY")
    require(declarations.is_file() and not declarations.is_symlink() and
            0 < declarations.stat().st_size <= 65536,
            "MISSING_PRIVATE_COORDINATOR_DECLARATIONS")
    try:
        attest = json.loads(declarations.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ReviewBlocked("V370_ATTESTATION_JSON") from exc
    require(isinstance(attest, dict) and
            set(attest) == {"checkpoint", "coordinator_confirmed_no_admin_mapping_seen", "reviewers"} and
            attest["checkpoint"] == "V3-70" and
            attest["coordinator_confirmed_no_admin_mapping_seen"] is True and
            isinstance(attest["reviewers"], dict),
            "ATTESTATION_SCHEMA_OR_PREMATURE_UNBLIND")
    all_rows, ids, forms, originals = [], set(), set(), {}
    frozen = spec()
    for path in files:
        rid, rows, digest = read_one(path)
        require(rid not in ids, "DUPLICATE_REVIEWER_ID")
        ids.add(rid)
        require(rid in attest["reviewers"], "REVIEWER_ATTESTATION_MISSING")
        info = attest["reviewers"][rid]
        require(isinstance(info, dict) and set(info) == {"form_number", *FLAGS},
                "ATTESTATION_FIELDS")
        require(all(info[k] is True for k in FLAGS),
                "CONSENT_ELIGIBILITY_OR_INDEPENDENCE_UNCONFIRMED")
        form = info["form_number"]
        require(type(form) is int and form in (1, 2, 3) and form not in forms,
                "UNIQUE_COUNTERBALANCED_FORM")
        forms.add(form)
        expected = [r["clip_id"] for r in template_rows(frozen, form - 1)]
        require([r["clip_id"] for r in rows] == expected,
                "FROZEN_FORM_ORDER_DRIFT")
        require(all(r["case_id"] == r["clip_id"].rsplit("_", 1)[0] for r in rows),
                "CASE_LABEL_DRIFT")
        all_rows.extend(rows)
        originals[rid] = digest
    require(set(attest["reviewers"]) == ids and forms == {1, 2, 3},
            "REVIEWER_OR_FORM_SET_DRIFT")
    # V3-60 remains the ONLY score and completeness specification. Technical
    # acceptance of even test data cannot prove a reviewer exists.
    with tempfile.TemporaryDirectory(prefix="v370-validate-") as folder:
        merged = Path(folder) / "combined.csv"
        write_csv(merged, all_rows)
        rows_checked, raters = load_ratings(merged)
        require(len(rows_checked) == 27 and len(raters) == 3,
                "V360_VALIDATION_MISMATCH")
    return {"rows": all_rows, "original_shas": originals}


def collect(submissions: Path, declarations: Path, destination: Path) -> dict:
    require(not destination.exists() and destination.parent.is_dir(),
            "DESTINATION_MUST_BE_NEW")
    require(not destination.resolve().is_relative_to(submissions.resolve()),
            "OUTPUT_INSIDE_SUBMISSIONS")
    checked = audited(submissions, declarations)
    temp = Path(tempfile.mkdtemp(prefix=".v370-private-", dir=destination.parent))
    try:
        os.chmod(temp, 0o700)
        combined = temp / "complete_ratings.csv"
        locked = temp / "locked_scores.json"
        write_csv(combined, checked["rows"])
        os.chmod(combined, 0o600)
        seal = seal_ratings(combined, locked)
        os.chmod(locked, 0o600)
        receipt = {
            "checkpoint": "V3-70", "state": "BLIND_SCORES_LOCKED",
            "submission_sha256_by_pseudonym": checked["original_shas"],
            "locked_combined_sha256": seal["sha256_raw_csv"],
            "reviewer_count_claimed": 3, "ratings_count": 27,
            "coordinator_flags": "DECLARED_NOT_INDEPENDENTLY_AUTHENTICATED",
            "treatment_key_access": 0, "treatment_mapping": "WITHHELD",
            "pedagogical_quality": "UNRATED_PENDING_MANUAL_AUDIT",
            "learning_gain": "NOT_MEASURED", "production": "BLOCKED",
        }
        path = temp / "intake_receipt.json"
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        os.chmod(path, 0o600)
        require(not destination.exists(), "DESTINATION_RACE")
        os.replace(temp, destination)
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    # Never echo raw scores, pseudonyms, private attestations, or filenames.
    return {"checkpoint": "V3-70", "intake": "LOCAL_BLIND_SCORES_LOCKED",
            "reviewer_count_claimed": 3, "rating_rows": 27,
            "human_independence_verified_by_code": False,
            "treatment_key_access": 0, "pedagogical_quality": "UNRATED",
            "learning_gain": "NOT_MEASURED", "production": "BLOCKED"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submissions-dir", type=Path, required=True)
    parser.add_argument("--attestations-json", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(collect(args.submissions_dir, args.attestations_json,
                             args.out_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
