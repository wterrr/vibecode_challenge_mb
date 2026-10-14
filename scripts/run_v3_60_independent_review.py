"""V3-60: native, masked pedagogical review with fail-closed human provenance.

Research-only. Video authenticity is machine-verifiable; independent human
quality, learner comprehension and model creativity are NOT machine-proven.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import statistics
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "benchmarks/learnflowbench/v3/v3_60_independent_review_preregister.json"
CRITERIA = ("clarity", "causal_witness", "semantic_continuity", "legibility", "pacing")
FIELDS = ("rater_id", "case_id", "clip_id", *CRITERIA,
          "confidence", "watched_full_video", "replay_count", "timestamp_failure_notes")
EXPECTED = {"original_motion", "static_end_state", "causal_reveal"}


class ReviewBlocked(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise ReviewBlocked("V360_" + code)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def spec():
    v = json.loads(REG.read_text(encoding="utf-8"))
    require(v["checkpoint"] == "V3-60" and
            v["registration_kind"] == "FIRST_CHILD_COMMIT" and
            v["registered_before_implementation"] is True and
            v["parent_sha"] == "506b3ccf3bf23aa3163d585496f1e91046109b18",
            "REGISTRATION_DRIFT")
    clips = v["masked_clips_sha256"]
    require(len(clips) == 9 and len(set(clips.values())) == 9 and
            all(len(x) == 64 for x in clips.values()), "MANIFEST_INVALID")
    require(v["acceptance"]["record_reviewers_currently"] == 0 and
            v["acceptance"]["production"] == "BLOCKED", "RELEASE_SCOPE_DRIFT")
    return v


def ffprobe(movie: Path) -> dict:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-show_entries",
         "stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames,nb_frames,duration",
         "-of", "json", str(movie)],
        capture_output=True, text=True, timeout=40, check=True)
    streams = json.loads(proc.stdout)["streams"]
    video = next((s for s in streams if s["codec_type"] == "video"), None)
    audio = next((s for s in streams if s["codec_type"] == "audio"), None)
    require(video and audio, "MISSING_MEDIA_STREAM")
    require((video["codec_name"], audio["codec_name"]) == ("h264", "aac") and
            (video["width"], video["height"], video["r_frame_rate"]) ==
            (1280, 720, "15/1"), "CODEC_OR_GEOMETRY_DRIFT")
    frames = int(video.get("nb_read_frames") or video.get("nb_frames") or 0)
    require(frames >= 100, "VIDEO_TRUNCATED")
    return {"frames": frames, "video_duration_s": float(video["duration"]),
            "audio_duration_s": float(audio["duration"])}


def aac_sha(movie: Path) -> str:
    out = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(movie), "-map", "0:a:0",
         "-c:a", "copy", "-f", "adts", "-"],
        capture_output=True, timeout=90, check=True)
    return sha_bytes(out.stdout)


def decode_video(movie: Path):
    # Decode all frames, not merely check container/header metadata.
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i",
                    str(movie), "-map", "0:v:0", "-f", "null", "-"],
                   capture_output=True, timeout=120, check=True)


def verify_packet(clips_dir: Path, *, decode: bool = False) -> dict:
    reg = spec()
    expected = reg["masked_clips_sha256"]
    found = {p.name for p in clips_dir.glob("*.mp4")}
    require(found == set(expected), "MISSING_EXTRA_OR_RENAMED_CLIPS")
    observations = {}
    groups = defaultdict(list)
    for name, digest in sorted(expected.items()):
        video = clips_dir / name
        require(sha(video) == digest, "CLIP_SHA256_DRIFT_" + name)
        media = ffprobe(video)
        if decode:
            decode_video(video)
        audio = aac_sha(video)
        case, label = name.removesuffix(".mp4").rsplit("_", 1)
        require(case in reg["frozen_cases"] and label in ("A", "B", "C"),
                "UNREGISTERED_MASKED_ID")
        groups[case].append((media["frames"], audio, media["video_duration_s"]))
        observations[name] = {
            "sha256": digest, "bytes": video.stat().st_size,
            "frames_decoded_by_probe": media["frames"],
            "video_duration_s": media["video_duration_s"],
            "audio_duration_s": media["audio_duration_s"],
            "audio_packet_sha256": audio,
            "full_decode_completed": decode,
        }
    for case, group in groups.items():
        require(len(group) == 3 and len(set(x[0] for x in group)) == 1,
                "THREE_ARM_FRAME_MISMATCH_" + case)
        require(len(set(x[1] for x in group)) == 1,
                "THREE_ARM_AUDIO_MISMATCH_" + case)
        require(max(x[2] for x in group) - min(x[2] for x in group) < 1/15,
                "THREE_ARM_DURATION_MISMATCH_" + case)
    require(len(groups) == 3, "CASE_COUNT")
    return {
        "checkpoint": "V3-60", "media_integrity": "PASS_NATIVE_MASKED",
        "decoded_full_movie": decode, "clips": observations,
        "treatments": "BLINDED_NOT_IN_REVIEWER_PACKET",
        "independent_human_raters": 0, "quality": "UNRATED",
        "learning_gain": "NOT_MEASURED", "production": "BLOCKED",
    }


def template_rows(reg: dict, form_index: int) -> list[dict]:
    require(form_index in (0, 1, 2), "UNKNOWN_FORM_ORDER")
    cases = reg["frozen_cases"][form_index:] + reg["frozen_cases"][:form_index]
    rows = []
    for case in cases:
        labels = ["A", "B", "C"]
        labels = labels[form_index:] + labels[:form_index]
        for label in labels:
            row = {field: "" for field in FIELDS}
            row.update(case_id=case, clip_id=f"{case}_{label}.mp4")
            rows.append(row)
    return rows


def write_csv(dest: Path, rows: list[dict]):
    with dest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepare_packet(clips_dir: Path, output: Path, *, decode: bool = False) -> dict:
    require(not output.exists(), "OUTPUT_EXISTS")
    receipt = verify_packet(clips_dir, decode=decode)
    reg = spec()
    output.mkdir(parents=True)
    for name in reg["masked_clips_sha256"]:
        shutil.copy2(clips_dir / name, output / name)
    for i in range(3):
        write_csv(output / f"reviewer_form_template_{i+1:02d}.csv",
                  template_rows(reg, i))
    (output / "REVIEWER_INSTRUCTIONS.md").write_text(
        "# V3-60 — Independent masked video review\n\n"
        "You are reviewing 9 prerecorded lessons: 3 per topic. "
        "Each filename A/B/C masks a treatment, NOT a rank. "
        "Videos may reveal their condition through visuals: this is NOT double-blind.\n\n"
        "Play each clip in the order shown in your assigned blank template; "
        "watch fully, then replay if necessary and record replay_count. "
        "Use headphones, a legible screen and the same viewing conditions for all clips. "
        "Do not compare results with other raters or open any ADMIN file.\n\n"
        "For EACH of the 9 clips enter an anonymous assigned rater_id, "
        "five integer scores (1=very poor/misleading; 2=major defects; "
        "3=adequate; 4=good; 5=very clear), confidence 1..5, "
        "watched_full_video=YES, and replay_count=0 or more. "
        "Criteria: clarity (can you follow the claim?), causal_witness "
        "(does the cause visibly precede the result?), semantic_continuity "
        "(do object/reference identities stay coherent?), legibility "
        "(can text/diagram be read?), pacing (time to see/understand each event?). "
        "If any score <=2, add a timestamp such as '6.5s: ACTION activates early' "
        "and a concrete explanation in timestamp_failure_notes. "
        "Leave no scores blank; if unable to rate, STOP and tell the coordinator "
        "(missingness is reported, never imputed).\n\n"
        "The coordinator must keep your ratings immutable and lock their checksum "
        "BEFORE treatment labels are opened. No real human ratings exist in this "
        "template. Reviewer IDs and consent/conflict checks are coordinated "
        "outside this public package. No learner learning outcome is measured.\n",
        encoding="utf-8")
    # Only approved names are written. No admin mapping, treatment names or keys.
    (output / "MASKED_MEDIA_MANIFEST.json").write_text(json.dumps({
        "checkpoint": "V3-60", "clips": reg["masked_clips_sha256"],
        "video_source_run": reg["artifact_provenance"]["native_run_id"],
        "treatments": "WITHHELD", "reviewer_count": 0,
        "quality": "UNRATED", "production": "BLOCKED"
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"kit": str(output), "media": receipt["media_integrity"],
            "masked_clips": 9, "templates": 3, "rater_count": 0,
            "quality": "UNRATED", "production": "BLOCKED"}


def load_ratings(path: Path) -> tuple[list[dict], list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require(tuple(reader.fieldnames or ()) == FIELDS, "RATINGS_SCHEMA")
        rows = list(reader)
    valid = set(spec()["masked_clips_sha256"])
    require(rows, "NO_RATINGS")
    seen, raters = set(), set()
    for r in rows:
        rid = r["rater_id"].strip()
        require(bool(re.fullmatch(r"[A-Za-z0-9_-]{3,40}", rid)), "REVIEWER_PSEUDONYM")
        clip = r["clip_id"].strip()
        require(clip in valid, "UNKNOWN_CLIP")
        case = clip.rsplit("_", 1)[0]
        require(r["case_id"] == case, "CASE_LABEL_MISMATCH")
        require((rid, clip) not in seen, "DUPLICATE_RATING")
        seen.add((rid, clip))
        raters.add(rid)
        for criterion in (*CRITERIA, "confidence"):
            require(r[criterion].strip() in {"1", "2", "3", "4", "5"},
                    "MISSING_OR_INVALID_ORDINAL_" + criterion)
        require(r["watched_full_video"].strip() == "YES", "PARTIAL_WATCH")
        require(re.fullmatch(r"\d{1,2}", r["replay_count"].strip()) is not None,
                "REPLAY_COUNT")
        if any(int(r[c]) <= 2 for c in CRITERIA):
            require(re.search(r"\b\d+(?:\.\d+)?s\b", r["timestamp_failure_notes"])
                    is not None, "LOW_SCORE_NEEDS_TIMESTAMP")
    for rid in raters:
        require({clip for rat, clip in seen if rat == rid} == valid,
                "INCOMPLETE_PANEL_REVIEWER_" + rid)
    require(len(raters) >= 3, "LESS_THAN_THREE_REVIEWERS")
    require(len(rows) == len(raters) * 9, "NOT_NINE_PER_REVIEWER")
    return rows, sorted(raters)


def seal_ratings(ratings_path: Path, destination: Path) -> dict:
    require(not destination.exists(), "LOCK_EXISTS")
    rows, raters = load_ratings(ratings_path)
    result = {
        "checkpoint": "V3-60", "lock_state": "BLIND_SCORES_LOCKED",
        "sha256_raw_csv": sha(ratings_path),
        "reviewer_ids": raters, "ratings": len(rows),
        "locked_at_utc": datetime.now(timezone.utc).isoformat(),
        "treatment_mapping_seen": False,
        "external_independence": "MANUAL_ATTESTATION_NOT_AUTOMATICALLY_PROVEN",
        "learning_gain": "NOT_MEASURED", "production": "BLOCKED",
    }
    destination.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n",
                           encoding="utf-8")
    return result


def validate_admin(admin: dict):
    reg = spec()
    cases = admin.get("cases")
    require(isinstance(cases, dict) and set(cases) == set(reg["frozen_cases"]),
            "ADMIN_CASE_DRIFT")
    for case, info in cases.items():
        subset = {k:v for k,v in reg["masked_clips_sha256"].items()
                  if k.startswith(case + "_")}
        require(set(info) == set(subset), "ADMIN_CLIP_DRIFT")
        require({v["treatment"] for v in info.values()} == EXPECTED,
                "ADMIN_TREATMENT_INCOMPLETE")
        require(all(info[name]["sha256"] == digest
                    for name,digest in subset.items()), "ADMIN_HASH_DRIFT")


def analyze(ratings_path: Path, lock_path: Path, admin_path: Path,
            attestations_path: Path, report_path: Path) -> dict:
    require(not report_path.exists(), "REPORT_EXISTS")
    rows, raters = load_ratings(ratings_path)
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    require(lock.get("checkpoint") == "V3-60" and
            lock.get("lock_state") == "BLIND_SCORES_LOCKED" and
            lock.get("sha256_raw_csv") == sha(ratings_path) and
            sorted(lock.get("reviewer_ids", [])) == raters and
            lock.get("treatment_mapping_seen") is False,
            "UNSEALED_OR_EDITED_RATINGS")
    attest = json.loads(attestations_path.read_text(encoding="utf-8"))
    require(set(attest.get("reviewers", {})) == set(raters), "ATTESTATION_IDS")
    for reviewer, value in attest["reviewers"].items():
        require(value.get("consented") is True and
                value.get("external_human") is True and
                value.get("conflict_disclosed") is True and
                value.get("reviewer_confirmed_no_collaboration") is True,
                "ATTESTATION_INCOMPLETE_" + reviewer)
    admin = json.loads(admin_path.read_text(encoding="utf-8"))
    validate_admin(admin)
    indexed = {(r["rater_id"], r["clip_id"]): r for r in rows}
    pairs = []
    for reviewer in raters:
        for case in spec()["frozen_cases"]:
            by_arm = {}
            for name, meta in admin["cases"][case].items():
                by_arm[meta["treatment"]] = indexed[(reviewer, name)]
            entry = {"reviewer_id": reviewer, "case_id": case}
            for criterion in CRITERIA:
                causal = int(by_arm["causal_reveal"][criterion])
                entry[criterion + "_causal_minus_original"] = (
                    causal - int(by_arm["original_motion"][criterion]))
                entry[criterion + "_causal_minus_static"] = (
                    causal - int(by_arm["static_end_state"][criterion]))
            pairs.append(entry)
    deltas = {}
    for criterion in CRITERIA:
        deltas[criterion] = {}
        for comparison in ("original", "static"):
            key = criterion + "_causal_minus_" + comparison
            deltas[criterion][comparison] = {
                "descriptive_median": statistics.median(p[key] for p in pairs),
                "range": [min(p[key] for p in pairs), max(p[key] for p in pairs)],
                "per_topic_medians": {case: statistics.median(
                    p[key] for p in pairs if p["case_id"] == case)
                    for case in spec()["frozen_cases"]},
            }
    direction = spec()["analysis"]["directional_screen"]
    topic_positive = sum(
        deltas["causal_witness"]["original"]["per_topic_medians"][case] >= 0 and
        deltas["causal_witness"]["static"]["per_topic_medians"][case] >= 0
        for case in spec()["frozen_cases"]
    )
    screen = (
        deltas["causal_witness"]["original"]["descriptive_median"] >=
        direction["median_primary_vs_original_at_least"] and
        deltas["causal_witness"]["static"]["descriptive_median"] >=
        direction["median_primary_vs_static_at_least"] and
        topic_positive >= direction["topics_nonnegative_vs_both_at_least"] and
        deltas["legibility"]["original"]["descriptive_median"] >=
        direction["median_legibility_causal_vs_original_at_least"]
    )
    result = {
        "checkpoint": "V3-60", "origin": "USER_SUBMITTED_HUMAN_RATINGS_NOT_AI",
        "rater_count_claimed": len(raters),
        "rater_independence": "ATTESTED_NOT_INDEPENDENTLY_VERIFIED_BY_SCRIPT",
        "unblind_after_score_lock_sha256": lock["sha256_raw_csv"],
        "rating_pairs": pairs, "ordinal_descriptive_deltas": deltas,
        "prespecified_directional_screen": "PASS" if screen else "FAIL",
        "quality_gate": "PENDING_MANUAL_PROVENANCE_AND_REVIEWER_AUDIT",
        "inferential_p_value": "NOT_ESTIMATED_SMALL_NONINDEPENDENT_PANEL",
        "student_learning_gain": "NOT_MEASURED",
        "model_pedagogy": "NOT_TESTED", "production": "BLOCKED"
    }
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n",
                           encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    ver = sub.add_parser("verify")
    ver.add_argument("--clips-dir", type=Path, required=True)
    ver.add_argument("--full-decode", action="store_true")
    prep = sub.add_parser("prepare")
    prep.add_argument("--clips-dir", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--full-decode", action="store_true")
    seal = sub.add_parser("seal")
    seal.add_argument("--ratings-csv", type=Path, required=True)
    seal.add_argument("--lock-json", type=Path, required=True)
    report = sub.add_parser("analyze")
    for name in ("ratings-csv", "lock-json", "admin-key",
                 "attestations-json", "output"):
        report.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.cmd == "verify":
        outcome = verify_packet(args.clips_dir, decode=args.full_decode)
    elif args.cmd == "prepare":
        outcome = prepare_packet(args.clips_dir, args.output, decode=args.full_decode)
    elif args.cmd == "seal":
        outcome = seal_ratings(args.ratings_csv, args.lock_json)
    else:
        outcome = analyze(args.ratings_csv, args.lock_json,
                          args.admin_key, args.attestations_json, args.output)
    print(json.dumps(outcome, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
