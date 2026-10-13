"""V3-56 adversarial tests: narrated-caption proxy must never become native speech proof."""
from __future__ import annotations
import copy
import pytest
from scripts.verify_v3_56_attention_alignment import check,validate,load,PREG,DATA


def data():
    return load(PREG),load(DATA)


def test_twelve_real_frame_witnesses_and_pcm_but_no_speech_claim():
    result=check()
    assert result["anchors"]==12
    assert result["decoded_native_frame_samples"]==60
    assert result["decoded_original_audio_seconds"]>1569
    assert result["word_level_alignment"]=="NOT_MEASURED"
    assert result["fifteen_video_deep_study"]=="NO_GO"
    assert result["production"]=="BLOCKED"


@pytest.mark.parametrize("mutation", [
    lambda p,d:d["evidence_levels"].update(caption="NATIVE_SPEECH_VERIFIED"),
    lambda p,d:d["outcome"].update(native_word_level_alignment="WORD_SYNC_PASS"),
    lambda p,d:d["outcome"].update(full_15_films="PASS"),
    lambda p,d:d["alignment_rows"][0].update(native_frame_seconds=[-1,115,121,127,146]),
    lambda p,d:d["alignment_rows"][0].update(native_frame_first_sha256="not_real_sha"),
    lambda p,d:d["alignment_rows"][0].update(unverified_scope=[]),
    lambda p,d:d["alignment_rows"][0].update(transcript_proxy_start_s=300),
    lambda p,d:d["native_media"].update(actual_visual_sample_count=12),
    lambda p,d:d["native_media"].update(mono_audio_decoded_seconds=20),
    lambda p,d:p["acceptance"].update(model_provider_calls=1),
])
def test_negative_cases_cannot_launder_unsupported_evidence(mutation):
    p,d=data()
    mutation(p,d)
    with pytest.raises(AssertionError,match="V356_ALIGN_"):
        validate(p,d)


def test_video_caption_bounded_lead_lag_not_exact_speech_matching():
    _,d=data()
    rows={r["anchor_id"]:r for r in d["alignment_rows"]}
    assert rows["mole"]["transcript_proxy_start_s"]==109
    assert 121 in rows["mole"]["native_frame_seconds"]
    assert "BEFORE_EXAMPLE" in rows["mole"]["cross_modal_relation"]
    assert rows["softmax"]["transcript_proxy_start_s"]==589
    assert rows["weighting"]["transcript_proxy_start_s"]==862
    assert 882 in rows["weighting"]["native_frame_seconds"]
    assert rows["multihead"]["transcript_proxy_start_s"]==1231
    assert all(r["caption_source"]=="2outube original-caption mirror" for r in rows.values())


def test_audio_rms_is_not_a_word_timing_estimator():
    _,d=data()
    assert "CANNOT_RELIABLY_IDENTIFY_WORDS" in d["evidence_levels"]["audio"]
    assert all(any("spoken words" in x for x in r["unverified_scope"]) for r in d["alignment_rows"])
    assert any(any(x<0.01 for x in r["audio_rms_sample_points"]) for r in d["alignment_rows"])
    assert d["outcome"]["native_word_level_alignment"]=="NOT_MEASURED"


def test_v3_research_pec_separates_external_caption_from_native_verified_speech():
    from jsonschema import Draft202012Validator
    from scripts.verify_v3_56_research import load as read_repo, ARCH
    schema=read_repo(ARCH)["schema"]["properties"]["narration_visual_evidence"]["items"]
    Draft202012Validator.check_schema(schema)
    record={
      "beat_id":"attention_query_1",
      "text_cue_source":"EXTERNAL_CAPTION_PROXY",
      "caption_time_s":382,
      "native_visible_sample_times_s":[382,388,394],
      "relation":"LEAD",
      "audio_content_certification":"CAPTION_PROXY_ONLY",
      "native_media_sha256":"439e154fffbb8696a37753d765c4f64bc06d25fbb17cb3d98bcc842045d85cb9",
      "claim_scope":"GROUNDED_SCRIPT_TOPIC"
    }
    validator=Draft202012Validator(schema)
    assert not list(validator.iter_errors(record))
    record["audio_content_certification"]="NATIVE_FORCED_ALIGNMENT_VERIFIED"
    assert list(validator.iter_errors(record)), "external caption cannot claim native forced alignment"
    record["audio_content_certification"]="CAPTION_PROXY_ONLY"
    record["claim_scope"]="NATIVE_AUDIO_VISUAL_ALIGNED"
    assert list(validator.iter_errors(record)), "external caption cannot claim verified native speech"
