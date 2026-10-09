"""V3-21 negative/fabrication checks, exercised on two real decoded H264/AAC MP4s in CI."""
from __future__ import annotations

from array import array
import json
import os
from pathlib import Path
import shutil

import pytest
from learnflow_v3.lesson_quality import (
    QualityEvidenceError, _audio_metrics, _frames, audit_media, parse_srt,
)

@pytest.fixture(scope="module")
def evidence_dir():
    assert "V3_21_MEDIA_DIR" in os.environ, "V3-21 CI must supply actual video artifacts"
    folder=Path(os.environ["V3_21_MEDIA_DIR"])
    assert (folder/"after_v3_20_real_audio_video.mp4").is_file()
    return folder

@pytest.fixture(scope="module")
def evaluated(evidence_dir):
    return audit_media(evidence_dir)

def test_actual_video_has_measured_media_not_human_quality_pass(evaluated):
    r=evaluated
    assert r["integrity_gate"]=="PASS"
    assert r["student_ready_gate"]=="BLOCKED"
    assert r["production_release"]=="BLOCKED"
    assert r["measured_word_alignment"]==r["human_visual_quality"]=="UNMEASURED"
    assert r["before"]["frame_count"]==538 and r["after"]["frame_count"]==541
    assert r["before"]["video_sha256"]!=r["after"]["video_sha256"]
    assert r["after"]["width"]==640 and r["after"]["height"]==360
    assert r["after"]["utterance_count"]==10
    assert len(r["apply_to_next_observe_continuity"])==3
    assert max(x["decoded_roi_mae"] for x in r["apply_to_next_observe_continuity"])<2
    assert r["after"]["speech"]["over_95pct_full_scale_samples"]==0
    assert all(x["decoded_aac_rms"]>=.004 for x in r["after"]["speech"]["utterances"])
    assert {"LEGIBILITY_PREVIEW_ONLY","PEDAGOGY_AND_AESTHETIC_PREFERENCE_UNMEASURED",
            "WORD_LEVEL_AND_PRONUNCIATION_UNVERIFIED","VOICE_OUTPUT_COMMERCIAL_RIGHTS"} <= \
        {x["id"] for x in r["issues"]}

def _copy(source:Path,tmp_path:Path)->Path:
    dest=tmp_path/"tampered"
    shutil.copytree(source,dest)
    return dest

def test_source_bound_subtitle_text_tampering_rejected(evidence_dir,tmp_path):
    dest=_copy(evidence_dir,tmp_path)
    srt=dest/"after_v3_20.srt"
    srt.write_text(srt.read_text().replace("Move the low bound to index 5.",
                                          "Move the low bound to index 4."),
                   encoding="utf-8")
    with pytest.raises(QualityEvidenceError,match="RECEIPT_SOURCE_OR_HASH_MISMATCH"):
        audit_media(dest)

def test_source_video_receipt_tampering_rejected(evidence_dir,tmp_path):
    dest=_copy(evidence_dir,tmp_path)
    p=dest/"after_v3_20.receipt.json"
    d=json.loads(p.read_text());d["video_sha256"]="f"*64
    p.write_text(json.dumps(d),encoding="utf-8")
    with pytest.raises(QualityEvidenceError,match="RECEIPT_SOURCE_OR_HASH_MISMATCH"):
        audit_media(dest)

def test_fabricated_quality_claim_rejected(evidence_dir,tmp_path):
    dest=_copy(evidence_dir,tmp_path)
    p=dest/"v3_20_before_after_qa.json"
    d=json.loads(p.read_text());d["word_level_alignment"]="FORCED_ASR_PASS"
    p.write_text(json.dumps(d),encoding="utf-8")
    with pytest.raises(QualityEvidenceError,match="FABRICATED_BASELINE_CLAIMS"):
        audit_media(dest)

def test_forged_event_proof_identity_rejected(evidence_dir,tmp_path):
    dest=_copy(evidence_dir,tmp_path)
    p=dest/"after_v3_20.event_proof.json"
    d=json.loads(p.read_text());d["proof_sha256"]="fake-self-rehash"
    p.write_text(json.dumps(d),encoding="utf-8")
    with pytest.raises(QualityEvidenceError,match="UNTRUSTED_EVENT_PROOF"):
        audit_media(dest)

def test_self_rehashed_proof_and_updated_receipts_still_rejected(evidence_dir,tmp_path):
    from learnflow_v2.repair import compute_content_hash
    dest=_copy(evidence_dir,tmp_path)
    proof_path=dest/"after_v3_20.event_proof.json"
    receipt_path=dest/"after_v3_20.receipt.json"
    cmp_path=dest/"v3_20_before_after_qa.json"
    proof=json.loads(proof_path.read_text())
    proof["events"][3]["expected_oracle_step"]+=1
    proof["proof_sha256"]=compute_content_hash({
        k:v for k,v in proof.items() if k!="proof_sha256"})
    proof_path.write_text(json.dumps(proof),encoding="utf-8")
    receipt=json.loads(receipt_path.read_text())
    receipt["event_proof_sha256"]=proof["proof_sha256"]
    receipt_path.write_text(json.dumps(receipt),encoding="utf-8")
    comparison=json.loads(cmp_path.read_text())
    comparison["comparison_attestation_sha256"]=proof["proof_sha256"]
    cmp_path.write_text(json.dumps(comparison),encoding="utf-8")
    with pytest.raises(QualityEvidenceError,match="REPLAYED_EVENT_PROOF_REJECTED"):
        audit_media(dest)

def test_malformed_srt_timestamp_rejected(evidence_dir,tmp_path):
    dest=_copy(evidence_dir,tmp_path)
    p=dest/"after_v3_20.srt"
    p.write_text(p.read_text().replace("00:00:17,333","00:99:17,333"),encoding="utf-8")
    with pytest.raises(QualityEvidenceError,match="RECEIPT_SOURCE_OR_HASH_MISMATCH"):
        audit_media(dest)
    with pytest.raises(QualityEvidenceError,match="BAD_SRT_CLOCK"):
        parse_srt(p)

def test_audio_silence_mutation_rejected(evaluated):
    assert len(evaluated["after"]["speech"]["utterances"])==10
    synthetic=array("h",[0])*16000*2
    with pytest.raises(QualityEvidenceError,match="SILENT_SPOKEN_EVENT"):
        _audio_metrics(synthetic,[{"seconds_start":0.,
                                   "raw_spoken_duration_seconds":1.5,
                                   "text":"Hello there","event_kind":"OBSERVE",
                                   "role":"WORKED_EXAMPLE"}])

def test_bad_native_frame_sample_rejected(evidence_dir):
    video=evidence_dir/"after_v3_20_real_audio_video.mp4"
    with pytest.raises(QualityEvidenceError,match="INVALID_SAMPLING_REQUEST"):
        _frames(video,640,360,[20,10,10])
