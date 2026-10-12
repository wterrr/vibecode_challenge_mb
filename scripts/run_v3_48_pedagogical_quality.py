#!/usr/bin/env python3
"""V3-48: frozen offline A/B evaluation harness. Not a human outcome study.

Strictly separate reviewer material from unblinding/provenance. A valid render
or a yellow pixel is not a comprehension or educational effectiveness score.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.process_edge_visual_qa import _frame
from learnflow_v3.semantic_scene_wire import decode_model_facing_scene
from scripts.run_v3_46_visual_quality import _samples, _frames
from scripts.run_v3_47_pedagogical_storytelling import _yellow_count

REG = "benchmarks/learnflowbench/v3/v3_48_quality_transfer_preregister.json"
RUBRIC = ("object_continuity", "mathematical_or_graph_truth",
          "causal_or_condition_precision", "temporal_explanation",
          "visual_readability", "learner_comprehension")
OLD = {"fraction": "v345-synthetic-fractions",
       "process": "v345-synthetic-process"}
NEW = ("fraction", "process", "heldout_process")


def require(condition, code):
    if not condition:
        raise Blocked(code)


def sha(path: Path) -> str:
    require(path.is_file(), "V348_MISSING_INPUT")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def media_receipt(path: Path, expected_frames: int) -> dict:
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-show_streams",
         "-of", "json", str(path)],
        text=True, capture_output=True, timeout=60)
    require(p.returncode == 0, "V348_BAD_FFPROBE")
    streams = json.loads(p.stdout).get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    require(v is not None and a is not None, "V348_MISSING_NATIVE_AUDIO_VIDEO")
    require(v.get("codec_name") == "h264" and a.get("codec_name") == "aac",
            "V348_BAD_NATIVE_CODEC")
    require((v.get("width"), v.get("height"), v.get("avg_frame_rate")) ==
            (1280, 720, "15/1"), "V348_BAD_NATIVE_DIMENSIONS")
    count = int(v.get("nb_read_frames", "-1"))
    require(count == expected_frames, "V348_FRAME_BUDGET_DRIFT")
    video_secs = float(v.get("duration", count / 15))
    audio_secs = float(a.get("duration", count / 15))
    require(abs(video_secs - expected_frames / 15) <= 1/15,
            "V348_VIDEO_DURATION_DRIFT")
    require(abs(audio_secs - video_secs) <= 1/15,
            "V348_AUDIO_DURATION_DRIFT")
    return {"frames": count, "video_seconds": video_secs,
            "audio_seconds": audio_secs, "codec": "H264_AAC_1280_720_15fps"}


def semantic_evidence(old_mp4: Path, new_mp4: Path, new_dir: Path,
                      case: str, receipt: dict) -> dict:
    sample = receipt["frame_proof"]["native_sample_frame"]
    before, after = _frame(old_mp4, sample), _frame(new_mp4, sample)
    scene = decode_model_facing_scene(json.loads(
        (new_dir / "synthetic_model_facing_wire.json").read_text()))
    counts = []
    if case == "fraction":
        e = next(e for beat in scene.beats for e in beat.events
                 if e.kind == "morph_partition")
        partition = next(p for p in scene.partitions if p.id == e.source)
        tiles = {g.id: g for g in scene.graphics if g.kind == "tile"}
        for tile_id in partition.part_ids:
            tile = tiles[tile_id]
            counts.append({"source_tile": tile_id,
                "before": _yellow_count(before, tile.x, tile.y, 12, 55),
                "after": _yellow_count(after, tile.x, tile.y, 12, 55)})
    else:
        beat = next(b for b in scene.beats if "P2" in b.claim_ids)
        e = next(e for e in beat.events if e.kind == "traverse_edge")
        edge = next(g for g in scene.graphics if g.id == e.target)
        node = next(g for g in scene.graphics if g.id == edge.dst)
        y = node.y - node.height/2 - .38
        counts.append({"condition": "UNKNOWN",
                       "before": _yellow_count(before, node.x, y, 55, 28),
                       "after": _yellow_count(after, node.x, y, 55, 28)})
        require(receipt["frame_proof"]["outcome"] == "UNKNOWN_NOT_VERIFIED",
                "V348_FABRICATED_CONDITION_TRUTH")
    require(len(counts) >= 1 and all(
        x["after"] >= 10 and x["after"] - x["before"] >= 8 for x in counts),
        "V348_NO_ADDED_SEMANTIC_FRAME_EVIDENCE")
    return {"frame": sample, "physical_seconds": round(sample/15, 4),
            "color_cue_counts": counts,
            "inference": "VISUAL_CUE_ONLY_NOT_LEARNING_GAIN"}


def blind_order(case: str, old_sha: str, new_sha: str) -> tuple[str, str]:
    digest = hashlib.sha256(
        ("V3-48-FROZEN-PAIR|" + case + "|" + old_sha + "|" + new_sha)
        .encode()).digest()
    return ("baseline", "grammar") if digest[0] % 2 == 0 else ("grammar", "baseline")


def make_contact(a_mp4: Path, b_mp4: Path, indices: list[int], out: Path):
    # Samples are physical beat-relative frames, NOT cherry-picked improvements.
    aa, bb = _frames(a_mp4, indices), _frames(b_mp4, indices)
    require(len(indices) == 12, "V348_NOT_12_FROZEN_BEAT_SAMPLES")
    sheet = Image.new("RGB", (6*320, 4*210), "black")
    draw = ImageDraw.Draw(sheet)
    for beat in range(4):
        for j in range(3):
            index = 3*beat + j
            for half, samples in enumerate((aa, bb)):
                x = (half*3 + j)*320
                y = beat*210 + 22
                sheet.paste(Image.fromarray(samples[index]), (x, y))
        draw.text((4, beat*210+3), f"BEAT {beat+1} - A", fill="white")
        draw.text((3*320+4, beat*210+3), f"BEAT {beat+1} - B", fill="white")
    sheet.save(out, quality=94)
    return sha(out)


def run(root: Path, baseline: Path, current: Path, output: Path):
    reg = json.loads((root / REG).read_text())
    require(reg["parent_sha"] == "f6b3919e304482f8b2691dcf877c15b8990f31ca"
            and reg["registration_kind"] == "PREREGISTRATION_BEFORE_IMPLEMENTATION",
            "V348_REGISTRATION_DRIFT")
    require(not output.exists(), "V348_OUTPUT_ALREADY_EXISTS")
    v347 = json.loads((current / "v3_47_semantic_storytelling_receipt.json").read_text())
    require(v347["checkpoint"] == "V3-47" and v347["human_scores"] is None
            and v347["model_api_posts"] == 0,
            "V348_NON_FROZEN_OR_FAKE_HUMAN_ORIGIN")
    require(len(v347["cases"]) == 3 and len(v347["comparisons"]) == 2,
            "V348_SOURCE_CASES_DRIFT")
    cases = {c["id"]: c for c in v347["cases"]}
    require(set(cases) == set(NEW), "V348_CASE_SET_DRIFT")
    packet = output / "rater_packet"
    private = output / "research_audit"
    packet.mkdir(parents=True)
    private.mkdir(parents=True)
    manifests, objective = {}, {}
    for case in NEW:
        file = current / case / "storytelling_host_with_audio.mp4"
        expected = reg["sources"]["current_v347"]["case_sha256"][case]
        require(sha(file) == expected == cases[case]["output_mp4_sha256"],
                "V348_TAMPERED_V347_MP4")
        require(cases[case]["synthetic_source"] ==
                "SYNTHETIC_OFFLINE_JSON_MODEL_FACING_NOT_LIVE_MODEL",
                "V348_SYNTHETIC_ORIGIN_MISLABELED")
        frames = cases[case]["actual_video"]["frames"]
        require(frames == sum(cases[case]["beat_frames"]),
                "V348_NARRATION_FRAME_COUNT_DRIFT")
        objective[case] = {"new_sha256": expected,
                           "media": media_receipt(file, frames),
                           "source": "HOST_SYNTHETIC_NOT_MODEL"}
    for case, olddir in OLD.items():
        base_dir = baseline / olddir
        old_file = base_dir / "offline_host_semantic_with_audio.mp4"
        new_file = current / case / "storytelling_host_with_audio.mp4"
        frozen = reg["sources"]["baseline_v346"]["case_sha256"][case]
        require(sha(old_file) == frozen, "V348_TAMPERED_V346_MP4")
        base_receipt = json.loads(
            (base_dir / "offline_case_receipt.json").read_text())
        require(base_receipt["output_video_sha256"] == frozen,
                "V348_BASELINE_RECEIPT_DRIFT")
        require(cases[case]["source_wire_sha256"] ==
                base_receipt["input_wire_sha256"],
                "V348_UNMATCHED_SCENE_WIRES")
        for i in range(4):
            require(sha(base_dir / f"beat_{i}.wav") ==
                    sha(current / case / f"beat_{i}.wav"),
                    "V348_UNMATCHED_NARRATION_WAV")
        media_receipt(old_file, cases[case]["actual_video"]["frames"])
        evidence = semantic_evidence(old_file, new_file, current / case,
                                     case, cases[case])
        frames, indices = _samples(current / case)
        require(sum(frames) == cases[case]["actual_video"]["frames"],
                "V348_TIMELINE_NOT_MATCHED")
        seq = blind_order(case, frozen, cases[case]["output_mp4_sha256"])
        choices = {"baseline": old_file, "grammar": new_file}
        dirname = packet / case
        dirname.mkdir()
        for label, assignment in zip(("A", "B"), seq):
            shutil.copyfile(choices[assignment], dirname / f"{label}.mp4")
        contact_sha = make_contact(dirname/"A.mp4", dirname/"B.mp4",
                                   indices, dirname/"AB_contact.jpg")
        manifests[case] = {"A": seq[0], "B": seq[1],
                           "A_sha256": sha(dirname/"A.mp4"),
                           "B_sha256": sha(dirname/"B.mp4"),
                           "contact_sha256": contact_sha}
        objective[case]["frozen_baseline_sha256"] = frozen
        objective[case]["added_rendered_cue"] = evidence
    require(sha(current / "process" / "beat_0.wav") ==
            sha(current / "heldout_process" / "beat_0.wav"),
            "V348_GEOMETRY_HOLDOUT_AUDIO_DRIFT")
    with (packet / "blind_quality_review_UNRATED.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(("pair", "criterion", "reviewer_id", "A_score_1to5",
                         "B_score_1to5", "evidence_timestamp", "reason"))
        for case in OLD:
            for axis in RUBRIC:
                writer.writerow((case, axis, "", "", "", "", ""))
    with (packet / "learner_transfer_UNCOLLECTED.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(("pair", "counterbalanced_assignment", "learner_id",
                         "answer", "reviewed_by", "collected_at"))
        for case in OLD:
            writer.writerow((case, "", "", "", "", ""))
    (packet/"REVIEWER_INSTRUCTIONS.txt").write_text(
        "V3-48 prospective evaluation. Open each pair's A.mp4 and B.mp4 in "
        "counterbalanced order. Use the same source narration. Complete the "
        "blank CSV with an independent review of SIX axes. Do NOT consult "
        "research_audit/unblinding_key.json. For learners use unseen "
        "comprehension/transfer questions and obtain consent first. "
        "These files contain NO participant data or claimed preference.\n")
    (private/"unblinding_key.json").write_text(json.dumps(manifests, indent=2)+"\n")
    (private/"answer_key_and_method.json").write_text(json.dumps({
        "fraction": {"question": "Why is one half equivalent to two quarters?",
                     "expected": "Multiply numerator and denominator by two; shaded share is unchanged."},
        "process": {"question": "Did verification PASS or FAIL?",
                    "expected": "Neither is known; the source provides no predicate outcome."},
        "limitation": "No external blind reviewers or learners have been assessed."
    }, indent=2)+"\n")
    summary = {"checkpoint": "V3-48",
        "technical_status": "FROZEN_PAIR_OFFLINE_AUDIT_PASS_ONLY",
        "human_quality": "UNRATED", "learner_gain": "NOT_MEASURED",
        "generalization": "NOT_CERTIFIED_FIXED_CLAIM_BANK",
        "genuine_model": False, "model_http_posts": 0,
        "model_authenticated_gets": 0, "production": "BLOCKED",
        "frozen_parent": reg["parent_sha"], "cases": objective,
        "paired_sources": list(OLD), "geometry_only_holdout": True,
        "min_independent_reviewers": reg["cohort_protocol"]["min_independent_reviewers"],
        "min_learner_participants": reg["cohort_protocol"]["learner_study_minimum"]}
    (private/"v3_48_evaluation_receipt.json").write_text(
        json.dumps(summary, indent=2)+"\n")
    print("V3_48=OFFLINE_PAIRED_SEMANTIC_CUES_PASS_HUMAN_UNRATED_TRANSFER_NOT_CERTIFIED",
          flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--current-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    a = parser.parse_args()
    run(ROOT, a.baseline_dir, a.current_dir, a.output_dir)
