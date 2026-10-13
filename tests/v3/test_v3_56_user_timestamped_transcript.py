"""V3-56 user-provided transcript is timing evidence, not independently certified native words."""
import copy
import pytest
from scripts.verify_v3_56_user_timestamped_transcript import (
    check, validate_receipt, parse_timestamp_segments, RECEIPT, PREVIOUS
)
import json


def docs():
    return json.loads(RECEIPT.read_text(encoding="utf-8")),json.loads(PREVIOUS.read_text(encoding="utf-8"))


def test_exact_user_transcript_receipt_bounded_only():
    x=check()
    assert x["timestamped_segments"]==449
    assert x["anchors"]==12
    assert x["user_supplied_text_native_frame_correspondence"]=="BOUNDED_PASS"
    assert x["independent_native_speech_alignment"]=="NO_GO"
    assert x["production"]=="BLOCKED"


def test_parser_orders_events_and_preserves_segment_hashes():
    rows=parse_timestamp_segments("(0:01) Query before vector. (0:04) Vector appears.")
    assert len(rows)==2
    assert [x["t"] for x in rows]==[1,4]
    assert rows[0]["event_index"]==0
    with pytest.raises(AssertionError,match="NON_MONOTONIC_OR_DUPLICATE"):
        parse_timestamp_segments("(0:02) A (0:01) B")
    with pytest.raises(AssertionError,match="INVALID_SECONDS"):
        parse_timestamp_segments("(0:70) impossible")


@pytest.mark.parametrize("mutate",[
    lambda d:d["source"].update(file_sha256="0"*64),
    lambda d:d["source"].update(asr_engine_model_or_human_verification_provenance="NATIVE_ASR_VERIFIED"),
    lambda d:d["source"].update(parsed_timestamped_segments=12),
    lambda d:d["native_video"].update(source_evidence_level="INFERRED_FROM_READ"),
    lambda d:d["rows"][0].update(speech_words_verified_in_native_audio=True),
    lambda d:d["rows"][0].update(actual_speech_onset_s=119.9),
    lambda d:d["rows"][0].update(native_word_alignment_accuracy=0.99),
    lambda d:d["rows"][0].update(caption_to_video_relation_classification="NATIVE_WORD_ALIGNMENT_PASS"),
    lambda d:d["rows"][0].update(transcript_cue_to_visible_window_offset_s=[100,101]),
    lambda d:d["rows"][0].update(native_decoded_luma_sha256="fake"),
    lambda d:d["rows"][0].update(video_sampled_visible_change_interval_s=[1568,1570]),
    lambda d:d["rigor"].update(native_word_alignment_count=12),
    lambda d:d["conclusion"].update(independent_native_audio_word_accuracy="PASS"),
    lambda d:d["conclusion"].update(production="READY"),
])
def test_mutations_fail_closed(mutate):
    doc,old=docs()
    mutate(doc)
    with pytest.raises(AssertionError,match="V356_USER_TRANSCRIPT_"):
        validate_receipt(doc,old)


def test_user_source_to_native_witness_does_not_infer_word_for_word_sync():
    d,_=docs()
    a={r["anchor_id"]:r for r in d["rows"]}
    assert a["mole"]["user_transcript_cue_s"]==120
    assert a["softmax"]["user_transcript_cue_s"]==592
    assert a["multihead"]["user_transcript_cue_s"]==1237
    assert a["output"]["user_transcript_cue_s"]==1365
    assert all(row["actual_speech_onset_s"] is None for row in d["rows"])
    assert all(row["source_segment_utf8_sha256"] != row["native_decoded_luma_sha256"] for row in d["rows"])
