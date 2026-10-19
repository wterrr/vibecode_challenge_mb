"""V3-23 source-bound real media reviews, explicit no-human/no-fake-score tests."""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import pytest

from learnflow_v3.lesson_quality import QualityEvidenceError
from learnflow_v3.review_preflight import (
    RUBRIC,FRAME_SAMPLES,_ensure_packet, preflight, verify_packet,write_packet,
)

@pytest.fixture(scope="module")
def source_root():
    root=Path(os.environ["V3_23_VIDEO_FOLDER"])
    assert (root/"native_hd/v3_22_binary_search_native_720p.mp4").is_file()
    assert (root/"source_v3_20/after_v3_20_real_audio_video.mp4").is_file()
    return root

@pytest.fixture(scope="module")
def records(source_root):
    return preflight(source_root)

def test_actual_native_h264_frame_pacing_and_legibility_diagnostics(records):
    r=records["report"]
    assert r["machine_source_video_gate"]=="PASS"
    assert r["video"]=={"width":1280,"height":720,"fps":24,"frames":1082}
    assert len(r["event_nominal_word_rates"])==10
    assert r["microcopy_geometry"]["actual_os_computer_modern_font_px"]==23
    assert r["microcopy_geometry"]["project_review_threshold_px"]==28
    assert [x["native_decoded_frame"] for x in r["actual_decoded_frame_pixels"]]==list(FRAME_SAMPLES)
    assert all(x["caption_band_has_light_glyphs"] for x in r["actual_decoded_frame_pixels"])
    assert {"TYPE_MICROCOPY_AND_ARRAY_INDEX","BEGINNER_FACING_TECHNICAL_JARGON",
            "DUPLICATE_LEFTMOST_REASONING","VOICE_AND_WORD_TIMINGS",
            "VISUAL_STORYTELLING_DENSITY"} <= {x["issue_id"] for x in r["timestamped_issues"]}
    assert r["technical_readability_preflight"]=="NEEDS_REVIEW_SMALL_TEXT"
    assert r["production_release"]==r["learner_ready"]=="BLOCKED"
    assert r["learner_understanding"]=="UNMEASURED"

def test_no_blinded_multi_topic_or_fake_comprehension_claim(records):
    p=records["packet"]
    assert p["rating_count"]==p["human_participants"]==0
    assert p["human_scores"]==[]
    assert p["actual_human_review"]=="NOT_RUN_UNAUTHORIZED"
    assert p["student_ready"]==p["publication"]=="BLOCKED"
    assert "NOT_CLAIMED" in p["blind_comparison"]
    assert "SINGLE_SOURCE" in p["comparison_scope"]
    assert set(p["rubric_dimensions"])==set(RUBRIC)
    assert "index 1;" not in p["transfer_question"]

def test_forged_human_scores_or_release_rejected(records):
    p=dict(records["packet"])
    for changed in (
        {**p,"rating_count":2,"human_participants":1,
         "human_scores":[{"reviewer":"fabricated","clarity":5}]},
        {**p,"publication":"PUBLISHED","student_ready":"PASS"},
        {**p,"blind_comparison":"RANDOMIZED_DOUBLE_BLIND"},
        {**p,"rubric_dimensions":["easy five out of five"]},
        {**p,"paid_provider_calls":1},
    ):
        with pytest.raises(QualityEvidenceError,match="V3_23_"):
            _ensure_packet(changed,p["source_v3_20_sha256"],
                           p["source_v3_22_sha256"])

def test_tampered_real_video_identity_rejected(records):
    p=records["packet"]
    changed={**p,"source_v3_22_sha256":"f"*64}
    with pytest.raises(QualityEvidenceError,match="MISMATCHED_REAL_VIDEO_HASH"):
        _ensure_packet(changed,p["source_v3_20_sha256"],p["source_v3_22_sha256"])

def test_output_is_blank_template_and_never_exposes_answer(source_root,tmp_path):
    result=write_packet(folder=source_root,output=tmp_path)
    form=tmp_path/"v3_23_review_form_BLANK.csv"
    rows=list(csv.reader(form.open(encoding="utf-8")))
    assert len(rows)==1
    assert rows[0]==result["packet"]["response_fields"]
    instructions=(tmp_path/"v3_23_reviewer_instructions.md").read_text(encoding="utf-8")
    assert "index 1;" not in instructions
    assert "nonblinded" in instructions
    assert json.loads((tmp_path/"v3_23_review_packet_UNSCORED.json").read_text())==result["packet"]
    with pytest.raises(QualityEvidenceError,match="DO_NOT_OVERWRITE_PRIOR_REVIEW"):
        write_packet(folder=source_root,output=tmp_path)

def test_self_rehashed_synthetic_report_still_fails_source_replay(source_root,records):
    r=json.loads(json.dumps(records["report"]))
    p=json.loads(json.dumps(records["packet"]))
    r["human_participants"]=3
    r["learner_understanding"]="PASS"
    with pytest.raises(QualityEvidenceError,match="UNTRUSTED_OR_SELF_REHASHED_REPORT"):
        verify_packet(root=source_root,report=r,packet=p)

def test_missing_real_video_never_yields_review_packet(tmp_path):
    with pytest.raises(QualityEvidenceError,match="REVIEW_EVIDENCE_MISSING"):
        preflight(tmp_path)
