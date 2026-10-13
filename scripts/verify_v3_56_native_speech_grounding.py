#!/usr/bin/env python3
"""V3-56 strict offline native speech/visual evidence provenance verifier.

PASS here certifies the truthfulness and integrity of evidence, NOT actual speech alignment.
No model API, remote network, original MP4, or copyrighted frames are needed in CI.
"""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PREG=ROOT/"research/v3_56_native_speech_grounding_preregister.json"
DATA=ROOT/"research/v3_56_native_speech_visual_grounding.json"
OLD=ROOT/"research/v3_56_attention_native_caption_alignment.json"
EXPECTED_SHA="439e154fffbb8696a37753d765c4f64bc06d25fbb17cb3d98bcc842045d85cb9"
EXPECTED_COMMIT="fc3a403c5a4d79ea0ac5c5409bfdf6a5f2aa7575"


def require(condition, code):
    if not condition:
        raise AssertionError("V356_NATIVE_SPEECH_"+code)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(p, d, old):
    require(p["checkpoint"]=="V3-56" and d["checkpoint"]=="V3-56","SCOPE_CHANGED")
    require(p["package"]=="NATIVE_SPEECH_VISUAL_GROUNDING","WRONG_PACKAGE")
    require(d["frozen_preregister_commit"]==EXPECTED_COMMIT,"PREREG_ORDER")
    require(p["video"]["sha256"]==EXPECTED_SHA and d["original_mp4"]["sha256"]==EXPECTED_SHA,"NATIVE_MEDIA_SHA")
    require(p["zero_provider_requests"] and p["no_main_merge"] and
            p["no_v2_core_change"] and p["no_production_prompt_change"],"SCOPE_SAFETY")
    require(d["offline_asr_due_diligence"]["provider_model_api_used"] is False and
            d["offline_asr_due_diligence"]["cached_model_weights_found"] is False and
            d["offline_asr_due_diligence"]["container_network"].startswith("NO_DNS"),"FAKE_ASR")
    require(not any(d["offline_asr_due_diligence"]["checked_local_modules"].values()),"MISSING_ASR_PROVENANCE")
    require(d["audio"]["manual_audio_listening_verified"] is False and
            d["audio"]["native_spoken_word_transcript"] is None and
            d["audio"]["word_alignment_native"] is False,"FABRICATED_SPEECH")
    require(d["audio"]["pcm_sample_rate_hz"]==8000 and
            d["audio"]["pcm_samples"]==12553265 and
            abs(d["audio"]["decoded_duration_s"]-1569.158125)<0.01,"PCM_MISMATCH")
    require(d["original_mp4"]["total_native_frames"]==47076 and
            d["original_mp4"]["h264_fps"]==30,"VIDEO_BOUNDS")
    o={x["anchor_id"]:x for x in old["alignment_rows"]}
    rows=d["rows"]
    require(len(rows)==12 and
            {x["anchor_id"] for x in rows}==set(p["locked_anchor_order"]) and
            [x["anchor_id"] for x in rows]==p["locked_anchor_order"],"ANCHOR_LOSS_OR_REORDER")
    require(set(p["locked_anchor_order"])==set(o),"CAPTION_RECEIPTS_DISAGREE")
    for r in rows:
        require(r["external_caption_proxy_start_s"]==o[r["anchor_id"]]["transcript_proxy_start_s"],
                "CAPTION_TIME_CONFLATION")
        require(r["cue_to_visual_is_not_native_speech_latency"] is True and
                r["native_speech_onset_s"] is None and
                r["native_utterance_to_visual_lead_lag_s"] is None and
                r["native_spoken_phrase_transcribed"] is None and
                r["word_error_rate"] is None and
                r["audio_visual_alignment_verdict"]=="UNVERIFIED_NATIVE_SPEECH",
                "FALSE_NATIVE_ALIGNMENT")
        require(re.fullmatch("[0-9a-f]{64}",r["native_first_frame_grayscale_sha256"]) is not None,
                "FRAME_HASH")
        v=r["native_largest_visual_change_window_s"]
        still=r["native_near_still_window_s"]
        lo,hi=r["native_sampled_pts_range_s"]
        require(0<=lo<hi<d["original_mp4"]["duration_s"] and
                lo<=v[0]<v[1]<=hi and lo<=still[0]<still[1]<=hi and
                v[1]-v[0]==2 and still[1]-still[0]==2 and
                r["native_frame_samples_count"]>=15 and
                r["native_sample_period_s"]==2,
                "FRAME_PTS_OUT_OF_BOUNDS")
        require(0<=r["native_largest_mean_abs_gray_diff"]<=255 and
                0<=r["native_near_still_mean_abs_gray_diff"]<=255 and
                r["native_largest_mean_abs_gray_diff"]>=r["native_near_still_mean_abs_gray_diff"] and
                0<=r["native_largest_fraction_luminance_change_gt25"]<=1 and
                0<=r["native_acoustic_pcm_rms_median_in_proxy_window"]<=1,
                "SIGNAL_FEATURE_INVALID")
        require(r["external_proxy_to_largest_visual_change_start_s"] ==
                r["native_largest_visual_change_window_s"][0]-r["external_caption_proxy_start_s"],
                "PROXY_OFFSET_INVALID")
    g=d["research_gates"]
    require(g["audio_pcm_decoded"]=="PASS" and
            g["frames_measured_for_12_anchors"]=="PASS" and
            g["independent_native_phrase_accuracy"]=="NO_GO_ZERO_OF_TWELVE" and
            g["prereg_native_speech_gate_minimum"]==8 and
            all(g[k]=="NOT_VERIFIED" for k in (
                "reliable_sentence_level_alignment","reliable_phrase_level_alignment","reliable_word_level_alignment")) and
            g["actual_learner_improvement"]=="NOT_TESTED" and
            g["production"]=="BLOCKED" and
            g["model_provider_requests"]==0 and
            g["no_main_merge"] is True,
            "FALSE_GO")
    require(d["v355_comparison"]["matched_efficacy_design"] is False and
            d["v355_comparison"]["measured_v355_duration_s"]==63.8,
            "UNFAIR_VIDEO_COMPARISON")
    return {
        "checkpoint":"V3-56","media_provenance":"PASS",
        "pcm_waveform_integrity":"PASS","frame_timing_research":"PASS",
        "anchors":12,"native_phrase_verified":0,
        "native_speech_alignment":"NO_GO",
        "pedagogical_visual_mechanism":"BOUNDED_RESEARCH_GO",
        "architecture":"RESEARCH_ONLY_GO_NOT_INTEGRATED",
        "production":"BLOCKED","model_api_requests":0
    }


def check():
    return validate(load(PREG),load(DATA),load(OLD))


if __name__=="__main__":
    print(json.dumps(check(),ensure_ascii=False,indent=2,sort_keys=True))
