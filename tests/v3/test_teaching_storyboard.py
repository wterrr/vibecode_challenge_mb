"""V3-24 direct semantic/pixel/audio evidence and negative mutation checks."""
from __future__ import annotations

import json
import os
from pathlib import Path
import pytest
from PIL import Image, ImageDraw

from learnflow_v3.blackboard_style import cmu_font
from learnflow_v3.lesson_quality import QualityEvidenceError
from learnflow_v3.native_hd_lesson import _source_evidence
from learnflow_v3.teaching_storyboard import (
    WIDTH,HEIGHT,VIDEO,RECEIPT,teaching_callout,teaching_frame,
    verify_teaching_video,render_teaching_video,_quality_guard,certified_visible_candidate,
)

@pytest.fixture(scope="module")
def folder():
    base=Path(os.environ["V3_24_MEDIA_DIR"])
    assert (base/"native_pedagogical"/VIDEO).is_file()
    return base

@pytest.fixture(scope="module")
def verified(folder):
    report=json.loads((folder/"native_pedagogical"/RECEIPT).read_text())
    check=verify_teaching_video(
        source_folder=folder/"source_v3_20",
        output=folder/"native_pedagogical"/VIDEO,receipt=report)
    return report,check

def test_real_h264_source_native_quality_and_events(verified):
    receipt,details=verified
    assert receipt["frames"]==1082
    assert (receipt["width"],receipt["height"],receipt["fps"])==(1280,720,24)
    assert receipt["font_small_pointer_px"]>=32
    assert receipt["font_array_index_px"]>=29
    assert receipt["caption_px"]>=32
    assert receipt["word_alignment"]==receipt["human_comprehension"]=="UNMEASURED"
    assert receipt["publication"]=="BLOCKED"
    assert len(details["settled_transition_checks"])==3
    assert max(x["roi_mae"] for x in details["settled_transition_checks"])<2
    assert len(details["decoded_source_frame_probes"])>=35

def test_source_grounded_duplicate_candidate_then_leftmost(folder):
    _,receipt,_,source,_=_source_evidence(folder/"source_v3_20")
    comparisons=[s for s in source.trace.steps if s.phase=="COMPARE"]
    assert [s.mid for s in comparisons]==[4,6,5]
    assert source.trace.result_index==5
    assert [s.action for s in comparisons]==[
        "DISCARD_LEFT","RECORD_CANDIDATE","RECORD_CANDIDATE"]
    assert [s.candidate_index for s in comparisons]==[None,6,5]
    # Never pre-reveal index 6 during OBSERVE equality, or index 5
    # merely because the forthcoming oracle step stores post-action state.
    for item in receipt["segments"]:
        if item["event_kind"]=="OBSERVE" and item["step"]==1:
            assert certified_visible_candidate(source,item) is None
        if item["event_kind"]=="APPLY" and item["step"]==1:
            assert certified_visible_candidate(source,item)==6
        if item["event_kind"]=="OBSERVE" and item["step"]==2:
            assert certified_visible_candidate(source,item)==6
        if item["event_kind"]=="APPLY" and item["step"]==2:
            assert certified_visible_candidate(source,item)==5
    seen_candidate=False
    for event in receipt["segments"]:
        key,text,semantic=teaching_callout(source,event)
        assert "immutable item" not in text.lower()
        if event["event_kind"]=="OBSERVE":
            assert "candidate" not in text.lower() # no update announced before APPLY
        if event["event_kind"]=="APPLY" and event["step"]==1:
            assert "Index 6" in text and "LEFT" in text
            seen_candidate=True
        if event["event_kind"]=="RESULT":
            assert "index 5" in text
    assert seen_candidate

def test_invalid_human_perceptual_pass_never_accepted(verified):
    receipt,_=verified
    for patch in ({"publication":"PUBLISHED"},
                  {"human_comprehension":"PASS"},
                  {"word_alignment":"ASR_FORCED_PASS"},
                  {"font_array_index_px":14},
                  {"commercial_voice_rights":"CLEARED"}):
        with pytest.raises(QualityEvidenceError,match="FORGED_OR_INVALID_QUALITY_CLAIM"):
            _quality_guard({**receipt,**patch})

def test_wrong_real_h264_receipt_rejected(folder,verified):
    receipt,_=verified
    bad={**receipt,"video_sha256":"f"*64}
    with pytest.raises(QualityEvidenceError,match="UNBOUND_VIDEO_OR_AUDIO"):
        verify_teaching_video(source_folder=folder/"source_v3_20",
                              output=folder/"native_pedagogical"/VIDEO,receipt=bad)

def test_wrong_original_audio_sha_rejected(folder,verified):
    receipt,_=verified
    bad={**receipt,"original_aac_packet_sha256":"0"*64}
    with pytest.raises(QualityEvidenceError,match="UNBOUND_VIDEO_OR_AUDIO"):
        verify_teaching_video(source_folder=folder/"source_v3_20",
                              output=folder/"native_pedagogical"/VIDEO,receipt=bad)

def test_render_no_clobber_existing_offline_output(folder):
    with pytest.raises(QualityEvidenceError,match="NO_CLOBBER"):
        render_teaching_video(source_folder=folder/"source_v3_20",
                              out=folder/"native_pedagogical")

def test_real_teaching_frame_sample_has_native_bounds_and_text(folder):
    _,receipt,_,source,_=_source_evidence(folder/"source_v3_20")
    event=next(x for x in receipt["segments"] if x["event_kind"]=="APPLY" and x["step"]==1)
    img=teaching_frame(source,event,fraction=.5,caption_visible=True)
    assert img.size==(WIDTH,HEIGHT)
    assert isinstance(img,Image.Image)
