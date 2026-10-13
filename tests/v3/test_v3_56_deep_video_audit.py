"""Deep source/Read audit: prohibit passing media validation on screenshots/code."""
import copy
from jsonschema import Draft202012Validator
from scripts.verify_v3_56_deep_video_audit import check,read,ARCH,BEATS,REG


def static_contract_witness():
    return {"witness_id":"static-probe","transformation_index":None,
            "before_state":"2x=4","after_state":"2x=4",
            "witness_region":"question hold overlay",
            "witness_type":"QUESTION_HOLD"}


def test_deep_read_and_source_are_real_but_media_gate_is_no_go():
    x=check()
    assert x["verified_scene_source_files"]==18
    assert x["lesson_reads"]==18
    assert x["read_pedagogical_beats"]>=90
    assert x["actual_native_video_review_count"]==0
    assert x["required_native_video_review_count"]>=15
    assert x["full_video_timeline_and_audio"]=="VIDEO_AUDIT_NO_GO"
    assert x["production"]=="BLOCKED"


def test_static_question_hold_does_not_fake_motion():
    schema=read(ARCH)["schema"]["properties"]["expected_observable_explanation"]["items"]
    v=Draft202012Validator(schema)
    assert not list(v.iter_errors(static_contract_witness()))
    bad=static_contract_witness()
    bad["transformation_index"]=0
    assert list(v.iter_errors(bad)), "static witness must not cite a fake transformation"
    motion=static_contract_witness()
    motion["witness_type"]="DECODABLE_PIXEL_TRANSITION"
    assert list(v.iter_errors(motion)), "motion witness must cite actual transformation index"
    motion["transformation_index"]=0
    assert not list(v.iter_errors(motion))


def test_frozen_media_threshold_cannot_be_replaced_by_read_proxies():
    preg, b=(read(x) for x in (REG,BEATS))
    assert preg["video_attestation_requirements"]["has_actual_encoded_media"]
    assert preg["video_attestation_requirements"]["has_audio_or_sync_evidence"]
    assert b["totals"]["voice_aligned_attestations"]==0
    for record in b["rows"]:
        assert all(z["actual_video_time_start_sec"] is None for z in record["pedagogical_beats"])
        assert all(z["encoded_frame_observed"] is False for z in record["pedagogical_beats"])


def test_counterexamples_disprove_simple_more_motion_is_better_prompt_rule():
    b={x["lesson_id"]:x for x in read(BEATS)["rows"]}
    assert b["calc_exp"]["negative_case_strategy"]=="STATIC_SYMBOLIC_ALLOWED"
    assert b["compo_fourier"]["negative_case_strategy"]=="FORMULA_TEASER_ALLOWED"
    assert b["prob_bayes"]["negative_case_strategy"]=="STATIC_COMPARE_ALLOWED"
    assert b["calc_essence"]["negative_case_strategy"]=="APPROXIMATION_DISCLOSURE"
