"""V3-56 mutation tests for auditable native PCM/visual timing and NO-GO word-level gate."""
import copy
import pytest
from scripts.verify_v3_56_native_speech_grounding import check, validate, load, PREG, DATA, OLD


def fixture():
    return load(PREG),load(DATA),load(OLD)


def test_one_uploaded_native_film_has_actual_pcm_visual_evidence():
    r=check()
    assert r["anchors"]==12 and r["native_phrase_verified"]==0
    assert r["media_provenance"]=="PASS"
    assert r["frame_timing_research"]=="PASS"
    assert r["pcm_waveform_integrity"]=="PASS"
    assert r["native_speech_alignment"]=="NO_GO"
    assert r["production"]=="BLOCKED"


@pytest.mark.parametrize("change",[
    lambda p,d,o:d["audio"].update(manual_audio_listening_verified=True),
    lambda p,d,o:d["audio"].update(native_spoken_word_transcript="fake"),
    lambda p,d,o:d["research_gates"].update(independent_native_phrase_accuracy="PASS"),
    lambda p,d,o:d["research_gates"].update(reliable_word_level_alignment="PASS"),
    lambda p,d,o:d["offline_asr_due_diligence"].update(cached_model_weights_found=True),
    lambda p,d,o:d["offline_asr_due_diligence"].update(provider_model_api_used=True),
    lambda p,d,o:d["rows"][0].update(native_speech_onset_s=109.1),
    lambda p,d,o:d["rows"][0].update(native_spoken_phrase_transcribed="mole"),
    lambda p,d,o:d["rows"][0].update(cue_to_visual_is_not_native_speech_latency=False),
    lambda p,d,o:d["rows"][0].update(word_error_rate=0.01),
    lambda p,d,o:d["rows"][0].update(native_first_frame_grayscale_sha256="missing"),
    lambda p,d,o:d["rows"][0].update(native_largest_visual_change_window_s=[2000,2002]),
    lambda p,d,o:d["rows"][1].update(external_caption_proxy_start_s=1),
    lambda p,d,o:d["v355_comparison"].update(matched_efficacy_design=True),
    lambda p,d,o:d["research_gates"].update(model_provider_requests=1),
    lambda p,d,o:d["research_gates"].update(production="READY"),
    lambda p,d,o:p.update(no_main_merge=False),
])
def test_adversarial_mismatch_fails_closed(change):
    p,d,o=fixture()
    change(p,d,o)
    with pytest.raises(AssertionError,match="V356_NATIVE_SPEECH_"):
        validate(p,d,o)


def test_every_caption_proxy_is_distinct_from_speech_and_visual_peak():
    p,d,o=fixture()
    for row in d["rows"]:
        assert row["native_speech_onset_s"] is None
        assert row["native_utterance_to_visual_lead_lag_s"] is None
        assert row["external_proxy_to_largest_visual_change_start_s"] == (
            row["native_largest_visual_change_window_s"][0]-
            row["external_caption_proxy_start_s"]
        )
    assert p["success_gate"]["native_audio_phrases"].startswith("At least 8")


def test_static_motion_not_a_cognitive_quality_score():
    _,d,_=fixture()
    assert any(row["native_near_still_mean_abs_gray_diff"]<0.01 for row in d["rows"])
    assert any(row["native_largest_mean_abs_gray_diff"]>30 for row in d["rows"])
    assert d["v355_comparison"]["matched_efficacy_design"] is False
    assert d["research_gates"]["actual_learner_improvement"]=="NOT_TESTED"
