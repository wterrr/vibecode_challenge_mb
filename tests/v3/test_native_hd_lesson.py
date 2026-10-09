"""V3-22 real decoded native 720p/video+AAC tests, evidence fraud mutations."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil

import pytest

from learnflow_v3.lesson_quality import QualityEvidenceError
from learnflow_v3.native_hd_lesson import (
    _native_frame, _pacing, _source_evidence, _wrapped,
    verify_hd, render_hd, WIDTH, HEIGHT, FPS,
)

@pytest.fixture(scope="module")
def evidence():
    p=Path(os.environ["V3_22_OUTPUT_DIR"])
    folder=p/"source_v3_20"
    out=p/"native_hd"
    video=out/"v3_22_binary_search_native_720p.mp4"
    receipt=json.loads((out/"v3_22_native_hd_receipt.json").read_text())
    assert video.is_file() and (folder/"after_v3_20.event_proof.json").is_file()
    return folder,out,video,receipt

def test_true_native_render_and_unchanged_aac_speech(evidence):
    folder,_,video,receipt=evidence
    result=verify_hd(source_folder=folder,output=video,receipt=receipt)
    assert receipt["width"]==1280 and receipt["height"]==720
    assert receipt["fps"]==24 and receipt["frames"]==1082
    assert receipt["caption_px"]>=32 and receipt["action_px"]>=32
    assert len(result["pointer_continuity"])==3
    assert result["max_decoded_expected_mae"]<15
    assert receipt["publication"]=="BLOCKED"
    assert receipt["human_legibility"]==receipt["human_learning"]=="UNMEASURED"
    assert receipt["word_alignment"]=="UNMEASURED"
    assert receipt["audio_adts_sha256"]
    assert receipt["source_video_sha256"] != receipt["video_sha256"]

def test_no_fabricated_forced_word_timing_or_rushed_oracle_state(evidence):
    folder,_,_,_=evidence
    _,rec,_,source,_=_source_evidence(folder)
    assert len(rec["segments"])==10
    assert _pacing("APPLY",0.)==0.0
    assert _pacing("APPLY",.15)==0.0
    assert 0 < _pacing("APPLY",.5) < .32
    assert _pacing("APPLY",.9)==.32
    assert _pacing("OBSERVE",0.0)==1.0
    assert _pacing("RESULT",0.0)==1.0
    first=next(x for x in rec["segments"] if x["event_kind"]=="OBSERVE")
    app=next(x for x in rec["segments"] if x["event_kind"]=="APPLY")
    assert app["frame_start"]==first["frame_end_exclusive"]
    assert app["step"]==first["step"]
    f=_native_frame(source,first,fraction=0.0,caption_visible=True)
    assert f.size==(WIDTH,HEIGHT)

def test_missing_720p_output_rejected(evidence,tmp_path):
    folder,_,_,receipt=evidence
    with pytest.raises(QualityEvidenceError,match="HD_VIDEO_HASH_CHANGED"):
        verify_hd(source_folder=folder,output=tmp_path/"absent.mp4",receipt=receipt)

def test_tampered_frame_and_self_rehashed_receipt_rejected(evidence,tmp_path):
    folder,_,video,receipt=evidence
    damaged=tmp_path/"damaged.mp4"
    content=video.read_bytes()
    damaged.write_bytes(content[:-1]+bytes([content[-1]^1]))
    with pytest.raises(QualityEvidenceError,match="HD_VIDEO_HASH_CHANGED"):
        verify_hd(source_folder=folder,output=damaged,receipt=receipt)

def test_forged_audience_or_publication_pass_rejected(evidence):
    folder,_,video,receipt=evidence
    fake=dict(receipt)
    fake["publication"]="PUBLISHED"
    fake["human_legibility"]="PASS"
    fake["human_learning"]="PASS"
    with pytest.raises(QualityEvidenceError,match="FORGED_QUALITY_RELEASE_CLAIM"):
        verify_hd(source_folder=folder,output=video,receipt=fake)

def test_forged_event_proof_and_baseline_source_rejected(evidence,tmp_path):
    folder,_,video,receipt=evidence
    counterfeit=tmp_path/"source"
    shutil.copytree(folder,counterfeit)
    p=counterfeit/"after_v3_20.event_proof.json"
    doc=json.loads(p.read_text());doc["proof_sha256"]="f"*64
    p.write_text(json.dumps(doc))
    with pytest.raises(QualityEvidenceError):
        verify_hd(source_folder=counterfeit,output=video,receipt=receipt)

def test_overwritten_hd_output_not_allowed(evidence):
    folder,out,_,_=evidence
    with pytest.raises(QualityEvidenceError,match="OUTPUT_NO_CLOBBER"):
        render_hd(source_folder=folder,output_dir=out)

def test_speech_text_too_long_must_not_truncate(evidence):
    from PIL import Image, ImageDraw
    from learnflow_v3.blackboard_style import cmu_font
    d=ImageDraw.Draw(Image.new("RGB",(WIDTH,HEIGHT)))
    with pytest.raises(QualityEvidenceError,match="UNBREAKABLE_CAPTION_WORD"):
        _wrapped(d,"A"*1000,cmu_font(32),WIDTH-128)
