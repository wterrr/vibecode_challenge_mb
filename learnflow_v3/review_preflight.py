"""V3-23: source-bound *preflight* for REAL V3-20/V3-22 narrated lesson review.

The output is a reproducible evidence inventory and an EMPTY review packet,
not human study data, ASR, independent psychology, accessibility certification,
or a randomized/blinded multi-topic V2/V3 experiment.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

from PIL import ImageStat, ImageDraw, Image

from .blackboard_style import cmu_font
from .lesson_quality import QualityEvidenceError, _frames, _probe, parse_srt
from .native_hd_lesson import verify_hd, _source_evidence

VERSION = "v3-23-independent-review-preflight-v1"
FRAME_SAMPLES = (344, 416, 480, 642, 804, 920)
# Project-authored engineering threshold to prioritize rater inspection,
# NOT an established universal 720p/accessibility or human-perception rule.
PROJECT_MICROTEXT_REVIEW_PX = 28
RUBRIC = (
    "factual_trace_accuracy",
    "bounds_and_midpoint_causality",
    "duplicate_leftmost_explanation",
    "visual_hierarchy",
    "small_index_and_pointer_readability",
    "subtitle_readability",
    "narration_pacing_and_intelligibility",
    "cognitive_load",
    "learner_transfer",
)
CUE_QUESTION = (
    "For the sorted array [1, 3, 3, 3, 8], what is the leftmost zero-based "
    "index of target 3? Briefly explain why the search must check earlier matches."
)
EXPECTED_ANSWER_PRIVATE = "index 1; keep searching left after finding an equal midpoint"


def _fail(condition: bool, reason: str) -> None:
    if not condition:
        raise QualityEvidenceError("V3_23_" + reason)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _word_count(s: str) -> int:
    return len(s.split())


def _paragraph_review(d: dict) -> dict:
    # Source labels from the existing Computer Modern renderer:
    # small = round(17 * height/540), not an independent pixel OCR.
    small_px = round(17 * d["height"] / 540)
    mock = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    font = cmu_font(small_px)
    label = "Verified leftmost-index trace  /  immutable item IDs"
    bounds = mock.textbbox((0,0), label, font=font)
    _fail(small_px < PROJECT_MICROTEXT_REVIEW_PX, "SMALL_FONT_DIAGNOSTIC_MISSING")
    return {
        "label_source": "learnflow_v3/sequence_renderer.py V3-06 small=_font(17*sy)",
        "actual_os_computer_modern_font_px": small_px,
        "project_review_threshold_px": PROJECT_MICROTEXT_REVIEW_PX,
        "measured_font_bbox_width_px": bounds[2] - bounds[0],
        "measured_font_bbox_height_px": bounds[3] - bounds[1],
        "decision": "REVIEW_LOW_PRIORITY_TEXT_AT_ACTUAL_DEVICE_DISTANCE",
        "source_font_conformance_not_proven_by_pixel_ocr": True,
    }


def _frame_band(video: Path) -> list[dict]:
    # Source fixture timepoints were selected prior to observing any ratings.
    frames = _frames(video, 1280, 720, list(FRAME_SAMPLES))
    rows = []
    for number, image in zip(FRAME_SAMPLES, frames, strict=True):
        # Caption region starts below the true semantic action line; report
        # actual pixel luminance/occupancy, not a fabricated OCR reading.
        caption = image.crop((64, 604, 1216, 706))
        pix = caption.convert("L")
        n = sum(1 for value in pix.getdata() if value >= 185)
        fraction = round(n / (caption.width * caption.height), 6)
        rows.append({
            "native_decoded_frame": number,
            "time_seconds": round(number / 24, 3),
            "caption_band_bright_pixel_fraction": fraction,
            "caption_band_has_light_glyphs": n > 75,
            "evidence_type": "DECODED_H264_PIXEL_OCCUPANCY_NOT_OCR",
        })
        _fail(n > 75, "CAPTION_BAND_EMPTY_OR_OFFSCREEN")
    return rows


def _pacing(source_receipt: dict) -> list[dict]:
    rows = []
    for p in source_receipt["segments"]:
        duration = float(p["raw_spoken_duration_seconds"])
        words = _word_count(p["text"])
        wpm = 60 * words / duration
        rows.append({
            "scene_id": p["scene_id"],
            "event_kind": p["event_kind"],
            "start_seconds": round(p["seconds_start"], 3),
            "end_seconds": round(p["seconds_end"], 3),
            "authored_words": words,
            "spoken_wav_duration_seconds": round(duration, 3),
            "nominal_script_words_per_minute": round(wpm, 1),
            "assessment": "DESCRIPTIVE_PACE_ONLY_NOT_SPEECH_RECOGNITION",
        })
    return rows


def _issues(micro: dict, periods: list[dict], frame_rows: list[dict]) -> list[dict]:
    rows = [
        {
            "issue_id": "TYPE_MICROCOPY_AND_ARRAY_INDEX",
            "severity": "P1_REVIEW",
            "time_seconds": 17.333,
            "evidence": "Original V3-06 native small label 23px on 720p; HD main action/captions 32px. Actual decoded frame sampled at 17.333s.",
            "decision": "REQUIRES_DEVICE_DISTANCE_LEGIBILITY_CHECK",
            "claimed_learner_result": "UNMEASURED",
        },
        {
            "issue_id": "BEGINNER_FACING_TECHNICAL_JARGON",
            "severity": "P2_CONTENT_REVIEW",
            "time_seconds": 0.0,
            "evidence": "On-screen helper text 'Verified leftmost-index trace / immutable item IDs' is developer-oriented and distinct from narrated beginner objective.",
            "decision": "INDEPENDENT_REVIEW_OF_INFORMATION_HIERARCHY_REQUIRED",
            "claimed_learner_result": "UNMEASURED",
        },
        {
            "issue_id": "DUPLICATE_LEFTMOST_REASONING",
            "severity": "P1_PEDAGOGY_REVIEW",
            "time_seconds": 22.333,
            "evidence": "Certified example records duplicate match at index 6 then earlier match at 5; requires comprehension/transfer beyond correct pointers.",
            "decision": "ASK_UNSEEN_TRANSFER_QUESTION_AND_RECORD_GROUNDED_FEEDBACK",
            "claimed_learner_result": "UNMEASURED",
        },
        {
            "issue_id": "VOICE_AND_WORD_TIMINGS",
            "severity": "P1_AUDIO_REVIEW",
            "time_seconds": 14.333,
            "evidence": "Original real AAC speech stream reused without source independent ASR/word-level forced alignment; source-aligned WAV utterances only.",
            "decision": "INDEPENDENT_LISTENING_AND_LEXICAL_ASSESSMENT_REQUIRED",
            "claimed_learner_result": "UNMEASURED",
        },
        {
            "issue_id": "VISUAL_STORYTELLING_DENSITY",
            "severity": "P2_AESTHETIC_REVIEW",
            "time_seconds": 17.333,
            "evidence": "Decoded frame at 17.333s has array, pointer labels and action/caption zones, with large unused black vertical regions.",
            "decision": "MANUAL_VISUAL_DIRECTOR_AND_COMPREHENSION_REVIEW",
            "claimed_learner_result": "UNMEASURED",
        },
    ]
    if any(p["nominal_script_words_per_minute"] > 190 for p in periods):
        rows.append({
            "issue_id": "HIGH_NOMINAL_WORD_RATE",
            "severity": "P2_AUDIO_REVIEW",
            "time_seconds": next(p["start_seconds"] for p in periods if p["nominal_script_words_per_minute"] > 190),
            "evidence": "Authored word count divided by real WAV utterance duration exceeds screening rate 190 WPM; not measured ASR speed.",
            "decision": "HUMAN_PACING_LISTENING_REVIEW",
            "claimed_learner_result": "UNMEASURED",
        })
    _fail(all(row["caption_band_has_light_glyphs"] for row in frame_rows),
          "CAPTION_SAMPLE_HAS_NO_VISIBLE_GLYPHS")
    return rows


def _ensure_packet(packet: dict, original_sha: str, hd_sha: str) -> None:
    _fail(packet.get("checkpoint") == "V3-23" and packet.get("version") == VERSION,
          "BAD_REVIEW_SCHEMA")
    _fail(packet.get("source_v3_20_sha256") == original_sha
          and packet.get("source_v3_22_sha256") == hd_sha,
          "MISMATCHED_REAL_VIDEO_HASH")
    _fail(packet.get("rating_count") == 0
          and packet.get("human_participants") == 0
          and packet.get("actual_human_review") == "NOT_RUN_UNAUTHORIZED"
          and packet.get("human_comprehension") == "UNMEASURED"
          and packet.get("student_ready") == "BLOCKED"
          and packet.get("publication") == "BLOCKED",
          "FORGED_HUMAN_OR_RELEASE_GATE")
    _fail(packet.get("blind_comparison") == "NOT_CLAIMED_DIFFERENT_RESOLUTIONS_AND_NO_RANDOMIZATION",
          "INVALID_BLINDNESS_CLAIM")
    _fail(tuple(packet.get("rubric_dimensions", ())) == RUBRIC, "CHANGED_RUBRIC")
    _fail(packet.get("human_scores") == [], "INJECTED_HUMAN_SCORES")
    _fail(packet.get("paid_provider_calls") == 0, "UNAUTHORIZED_PROVIDER_CLAIM")


def preflight(folder: Path) -> dict:
    """One source-matched single-example *preflight*; never report actual learning."""
    root = Path(folder)
    source_folder = root / "source_v3_20"
    target = root / "native_hd" / "v3_22_binary_search_native_720p.mp4"
    receipt_file = root / "native_hd" / "v3_22_native_hd_receipt.json"
    _fail(all(p.is_file() and not p.is_symlink() for p in
              (target, receipt_file, source_folder/"after_v3_20.srt")),
          "REVIEW_EVIDENCE_MISSING")
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    verify_hd(source_folder=source_folder,output=target,receipt=receipt)
    _fail(receipt["human_learning"]=="UNMEASURED" and
          receipt["human_legibility"]=="UNMEASURED" and
          receipt["publication"]=="BLOCKED", "SOURCE_PRODUCTION_AUTHORITY")
    source_mp4 = source_folder/"after_v3_20_real_audio_video.mp4"
    sd = _hash(source_mp4)
    hd = _hash(target)
    video,audio = _probe(target)
    _fail(video["width"] == 1280 and video["height"] == 720
          and video["r_frame_rate"] == "24/1"
          and int(video["nb_frames"]) == 1082,
          "SOURCE_NOT_TRUE_NATIVE_HD")
    _, previous_receipt, proof, _, _ = _source_evidence(source_folder)
    _fail(proof["event_count"] == 10 and
          previous_receipt["source_trace_sha256"] == receipt["source_trace_sha256"],
          "CERTIFIED_SOURCE_DRIFT")
    srt = parse_srt(source_folder/"after_v3_20.srt")
    _fail(len(srt) == 10
          and all(a[2] == p["text"] for a,p in
                  zip(srt,previous_receipt["segments"],strict=True)),
          "SRT_UNGROUNDED_TRANSCRIPT")
    bands = _frame_band(target)
    pacing = _pacing(previous_receipt)
    micro = _paragraph_review({"height": 720})
    report = {
        "checkpoint": "V3-23",
        "version": VERSION,
        "scope": "SINGLE_BINARY_SEARCH_NATIVE_720P_VS_SOURCE_360P_PREFLIGHT_ONLY",
        "source_v3_20_sha256": sd,
        "source_v3_22_sha256": hd,
        "source_trace_sha256": receipt["source_trace_sha256"],
        "event_proof_sha256": receipt["event_proof_sha256"],
        "original_aac_adts_sha256": receipt["audio_adts_sha256"],
        "video": {"width":1280,"height":720,"fps":24,"frames":1082},
        "review_dimensions": list(RUBRIC),
        "microcopy_geometry": micro,
        "actual_decoded_frame_pixels": bands,
        "event_nominal_word_rates": pacing,
        "timestamped_issues": _issues(micro,pacing,bands),
        "reader_viewing_distance": "NOT_SPECIFIED_NOT_MEASURED",
        "listener_transcript_as_heard": "UNMEASURED",
        "word_forced_alignment": "UNMEASURED",
        "learner_understanding": "UNMEASURED",
        "independent_aesthetics": "UNMEASURED",
        "cross_topic_reliability": "UNMEASURED",
        "internal_visual_observation": "SAMPLED_FRAMES_ONLY_NOT_BLINDED_HUMAN_RATINGS",
        "human_participants": 0,
        "rating_count": 0,
        "real_human_review": "NOT_RUN_UNAUTHORIZED",
        "human_scores": [],
        "machine_source_video_gate": "PASS",
        "technical_readability_preflight": "NEEDS_REVIEW_SMALL_TEXT",
        "learner_ready": "BLOCKED",
        "production_release": "BLOCKED",
        "provider_calls": 0,
    }
    packet = {
        "checkpoint": "V3-23","version": VERSION,
        "comparison_scope": "SINGLE_SOURCE_V3_20_360P_VS_V3_22_720P_NOT_V3_16_12_TOPIC_PILOT",
        "source_v3_20_sha256": sd,
        "source_v3_22_sha256": hd,
        "clip_A": "source_v3_20/after_v3_20_real_audio_video.mp4",
        "clip_B": "native_hd/v3_22_binary_search_native_720p.mp4",
        "blind_comparison": "NOT_CLAIMED_DIFFERENT_RESOLUTIONS_AND_NO_RANDOMIZATION",
        "rubric_dimensions": list(RUBRIC),
        "reviewer_task": "Compare the matched source clips for clarity, legibility and cognitive load at stated screen size and viewing distance. No generated or hypothetical scores.",
        "transfer_question": CUE_QUESTION,
        "response_fields": ["reviewer_id","screen_inches","viewing_distance_cm",
                            "clip","dimension","rating_1_to_5","timestamp_seconds",
                            "observed_reason","transfer_answer"],
        "human_participants": 0,"rating_count":0,"human_scores": [],
        "actual_human_review": "NOT_RUN_UNAUTHORIZED",
        "human_comprehension": "UNMEASURED",
        "student_ready": "BLOCKED","publication":"BLOCKED",
        "paid_provider_calls": 0,
    }
    _ensure_packet(packet,sd,hd)
    return {"report":report,"packet":packet}


def verify_packet(*, root: Path, report: dict, packet: dict) -> None:
    expected = preflight(root)
    _fail(report == expected["report"], "UNTRUSTED_OR_SELF_REHASHED_REPORT")
    _fail(packet == expected["packet"], "UNTRUSTED_OR_SELF_REHASHED_REVIEW_PACKET")
    _ensure_packet(packet,expected["report"]["source_v3_20_sha256"],
                   expected["report"]["source_v3_22_sha256"])


def write_packet(*, folder: Path, output: Path) -> dict:
    _fail(output.is_dir() and not output.is_symlink(),
          "UNSAFE_OUTPUT_FOLDER")
    for filename in ("v3_23_readability_evidence.json",
                     "v3_23_review_packet_UNSCORED.json",
                     "v3_23_review_form_BLANK.csv",
                     "v3_23_reviewer_instructions.md"):
        _fail(not (output/filename).exists(), "DO_NOT_OVERWRITE_PRIOR_REVIEW")
    records = preflight(folder)
    report,packet = records["report"],records["packet"]
    (output/"v3_23_readability_evidence.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (output/"v3_23_review_packet_UNSCORED.json").write_text(
        json.dumps(packet,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    with (output/"v3_23_review_form_BLANK.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f)
        writer.writerow(packet["response_fields"])
        # Blank template only; no participants or 1–5 scores.
    instructions = (
        "# V3-23 unexecuted reviewer preflight\n\n"
        "This is a source-matched, **nonblinded** comparison (different "
        "resolution and frame rate) of a single Binary Search example. "
        "It is **not** the V3-16 frozen 12-topic randomized blinded human pilot.\n\n"
        "Open clip A then clip B at the same viewing size and note screen size, "
        "distance, whether captions/index/LOW/HIGH/MID are distinguishable, "
        "whether the duplicate-at-index-6 to earlier-index-5 reasoning is clear, "
        "and whether the source voice is intelligible. "
        "Use 1 (unclear) to 5 (very clear) with timestamps and reasons. "
        "If uncertain, leave the cell blank; never infer missing scores.\n\n"
        f"**Transfer question:** {CUE_QUESTION}\n\n"
        "Rater participation, data collection and commercial publication are NOT "
        "authorized by this document. Expected transfer answer is withheld from "
        "the reviewer packet; analysis must use separate instructor-controlled key. "
        "The only observed result here is machine-checked media and an issue inventory.\n"
    )
    (output/"v3_23_reviewer_instructions.md").write_text(instructions,encoding="utf-8")
    verify_packet(root=folder,report=report,packet=packet)
    return records
