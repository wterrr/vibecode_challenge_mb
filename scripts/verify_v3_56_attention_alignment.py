#!/usr/bin/env python3
"""V3-56 native uploaded film + external caption proxy research integrity.

Does not read source copyrighted MP4 from git, perform ASR, or claim native word sync.
This test is designed to FAIL CLOSED when a caption proxy is laundered into observed speech.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PREG=Path("research/v3_56_attention_alignment_preregister.json")
DATA=Path("research/v3_56_attention_native_caption_alignment.json")
VIDEO_SHA="439e154fffbb8696a37753d765c4f64bc06d25fbb17cb3d98bcc842045d85cb9"
PRECOMMIT="377d1d03d47135a1b6c113e4e529d9a5ac6bc42c"

def load(path:Path)->dict:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def assert_ok(test:bool,code:str)->None:
    if not test: raise AssertionError("V356_ALIGN_"+code)

def validate(preg:dict, receipt:dict)->dict:
    assert_ok(preg["work_package"]=="ATTENTION_NATIVE_CAPTION_TO_VISUAL_ALIGNMENT",
              "WRONG_SCOPE")
    assert_ok(preg["input"]["sha256"]==VIDEO_SHA and
              receipt["original_file_sha256"]==VIDEO_SHA,
              "VIDEO_SHA_MISMATCH")
    assert_ok(receipt["preregister_first_commit"]==PRECOMMIT,"PREREG_LAUNDERED")
    assert_ok(preg["acceptance"]["model_provider_calls"]==0 and
              preg["acceptance"]["no_main_merge"] is True and
              preg["acceptance"]["core_mutations"]==0,
              "PRODUCTION_GUARD")
    assert_ok(receipt["source"]["caption_origin"].startswith("third-party mirror") and
              receipt["source"]["caption_url"]=="https://2outube.com/watch?v=eMlx5fFNoYc",
              "CAPTION_SOURCE_UNTRUSTED")
    assert_ok("NOT_NATIVE_AUDIO_ASR" in preg["transcript_sources"][0]["reliability"],
              "PROXY_BECAME_NATIVE_SPEECH")
    media=receipt["native_media"]
    assert_ok(media["actual_input_file_measured"] is True and
              media["original_video_sha256"]==VIDEO_SHA and
              media["actual_visual_sample_count"]==60 and
              media["number_of_anchor_groups"]==12 and
              media["pcm_decode_sample_rate"]==8000 and
              abs(media["mono_audio_decoded_seconds"]-1569.16)<0.1 and
              abs(media["video_duration_s"]-1569.19)<0.1,
              "NATIVE_MEDIA_BOUNDS")
    rows=receipt["alignment_rows"]
    assert_ok(len(rows)==12 and
              {x["anchor_id"] for x in rows}==set(preg["anchor_ids"]) and
              len({x["anchor_id"] for x in rows})==12,
              "MISSING_OR_DUPLICATE_ANCHORS")
    assert_ok(all(x in receipt["evidence_levels"]["caption"] for x in ["EXTERNAL","NOT_NATIVE"]),
              "CAPTION_EVIDENCE_LAUNDERED")
    assert_ok("CANNOT_RELIABLY_IDENTIFY_WORDS" in receipt["evidence_levels"]["audio"],
              "RMS_SPEECH_LAUNDERED")
    assert_ok(receipt["outcome"]["native_word_level_alignment"]=="NOT_MEASURED" and
              receipt["outcome"]["full_15_films"]=="NO_GO" and
              receipt["outcome"]["human_outcome"]=="NOT_TESTED" and
              receipt["outcome"]["production"]=="BLOCKED" and
              receipt["outcome"]["paid_model_api_calls"]==0,
              "FABRICATED_GAIN_OR_AUDIO")
    assert_ok(len(receipt["negative_case_notes"])>=4,"MISSING_NEGATIVE_CONTROLS")
    for row in rows:
        assert_ok(set(preg["required_fields"]).issubset(row.keys()),
                  "REQUIRED_FIELDS")
        assert_ok(row["caption_source"]=="2outube original-caption mirror",
                  "MISMATCHED_CAPTION_ORIGIN")
        assert_ok(isinstance(row["transcript_proxy_start_s"],int) and
                  0<=row["transcript_proxy_start_s"]<media["video_duration_s"],
                  "INVALID_CAPTION_TIME")
        t=row["native_frame_seconds"]
        assert_ok(len(t)==5 and t==sorted(t) and len(set(t))==5 and
                  all(isinstance(x,int) and 0<=x<media["video_duration_s"] for x in t),
                  "INVALID_NATIVE_FRAME_TIMES")
        assert_ok(t[0]>=row["transcript_proxy_start_s"]-15 and
                  t[-1]<=row["transcript_proxy_start_s"]+48,
                  "CAPTION_FRAME_WINDOW_TOO_BROAD")
        assert_ok(re.fullmatch("[0-9a-f]{64}",row["native_frame_first_sha256"]) is not None,
                  "INVALID_FIRST_FRAME_SHA")
        assert_ok(len(row["native_gray_mean_abs_differences_320x180"])==4 and
                  all(isinstance(x,(int,float)) and 0<=x<=255 for x in row["native_gray_mean_abs_differences_320x180"]),
                  "PIXEL_MEASUREMENT_INVALID")
        assert_ok(len(row["audio_rms_sample_points"])==5 and
                  all(isinstance(x,(int,float)) and 0<=x<=1 for x in row["audio_rms_sample_points"]),
                  "AUDIO_RMS_INVALID")
        assert_ok(len(row["verified_scope"])==3 and
                  len(row["unverified_scope"])>=3 and
                  any("spoken words" in x for x in row["unverified_scope"]) and
                  len(row["transcript_claim_paraphrase"])>=30 and
                  len(row["native_frame_description"])>=40 and
                  len(row["cross_modal_relation"])>=10,
                  "SOURCE_AND_INTERPRETATION_GAP")
    by_id={x["anchor_id"]:x for x in rows}
    assert_ok(by_id["mole"]["transcript_proxy_start_s"]==109 and
              by_id["query_motivating"]["transcript_proxy_start_s"]==357 and
              by_id["score_matrix"]["transcript_proxy_start_s"]==514 and
              by_id["mask"]["transcript_proxy_start_s"]==691 and
              by_id["weighting"]["transcript_proxy_start_s"]==862 and
              by_id["multihead"]["transcript_proxy_start_s"]==1231,
              "FROZEN_CAPTION_ANCHORS_CHANGED")
    return {
        "checkpoint":"V3-56","alignment_scope":"CAPTION_PROXY_TO_ORIGINAL_NATIVE_FRAMES",
        "status":"BOUNDED_RESEARCH_PASS_NOT_NATIVE_WORD_SYNC",
        "anchors":len(rows),"decoded_native_frame_samples":sum(len(x["native_frame_seconds"]) for x in rows),
        "decoded_original_audio_seconds":media["mono_audio_decoded_seconds"],
        "word_level_alignment":"NOT_MEASURED",
        "native_uploaded_films_visual":1,"fifteen_video_deep_study":"NO_GO",
        "model_provider_calls":0,"production":"BLOCKED"
    }

def check()->dict:
    return validate(load(PREG),load(DATA))

if __name__=="__main__":
    print(json.dumps(check(),indent=2,sort_keys=True))
