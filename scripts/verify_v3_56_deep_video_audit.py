#!/usr/bin/env python3
"""V3-56 deep media-evidence audit: PASS integrity, NO-GO full-video review when unavailable.

Never equate Read prose, thumbnail, class names, or self.play counts with watched native video.
"""
import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
REG=Path("research/v3_56_deep_video_audit_preregister.json")
BEATS=Path("research/v3_56_deep_pedagogical_beats.json")
SOURCES=Path("research/v3_56_source_scene_corpus.json")
ARCH=Path("research/v3_56_agent_prompt_architecture.json")
READ=Path("research/v3_56_3b1b_lesson_evidence.json")
NATIVE=Path("research/v3_56_attention_ch6_native_video_receipt.json")


def read(p):
    return json.loads((ROOT/p).read_text(encoding="utf-8"))


def require(x,code):
    if not x:
        raise AssertionError("V356_DEEP_"+code)


def check():
    preg, beats, source, contract, original=(read(p) for p in (REG,BEATS,SOURCES,ARCH,READ))
    byid={r["lesson_id"]:r for r in beats["rows"]}
    src={r["lesson_id"]:r for r in source["rows"]}
    orig={r["lesson_id"]:r for r in original["rows"]}
    require(preg["all_video_required_count"]>=15,"FROZEN_MEDIA_THRESHOLD")
    require(len(byid)==18 and set(byid)==set(orig)==set(src),"SOURCE_COVERAGE")
    require(beats["totals"]["first_party_read_pages"]==18,"READ_COUNT")
    require(beats["totals"]["read_pedagogical_beats"]==sum(len(x["pedagogical_beats"]) for x in byid.values()),"BEAT_COUNT")
    require(beats["totals"]["native_video_frame_attestations"]==0 and
            beats["totals"]["voice_aligned_attestations"]==0,"FALSE_NATIVE_VIDEO")
    for lesson_id, beat in byid.items():
        require(beat["first_party_read_url"]==orig[lesson_id]["read_url"],"READ_ID_SWAP")
        require(len(beat["pedagogical_beats"])>=5,"INSUFFICIENT_BEATS")
        require([x["read_order"] for x in beat["pedagogical_beats"]]==list(range(1,len(beat["pedagogical_beats"])+1)),"BEAT_READ_ORDER")
        require(beat["complete_native_video_inspected"] is False and beat["real_video_timeline_certified"] is False
                and beat["word_level_narration_alignment_certified"] is False,"MEDIA_ATTESTATION_FABRICATION")
        require(beat["static_vs_motion_negative_case"] and beat["negative_case_strategy"],"NO_NEGATIVE_CASE")
        for x in beat["pedagogical_beats"]:
            require(x["actual_video_time_start_sec"] is None and x["actual_video_time_end_sec"] is None,"FAKE_SECONDS")
            require(x["encoded_frame_observed"] is False and x["speech_synced"] is False,"FAKE_FRAMES_OR_AUDIO")
        s=src[lesson_id]
        require(s["source_sha"] if "source_sha" in s else s.get("blob_sha"),"MISSING_CODE_SHA")
        require(len(s["blob_sha"])==40 and s["class_count"]>=1 and
                len(s["scene_class_evidence"])>=2 and s["path"].endswith(".py"),"NO_REAL_CODE")
        require(s["semantics"]=="SOURCE_CODE_ONLY","CODE_WAS_FALSELY_MARKED_NATIVE_VIDEO")

    neg={r["lesson_id"]:r["negative_case_strategy"] for r in beats["rows"]}
    require(neg["calc_exp"]=="STATIC_SYMBOLIC_ALLOWED" and
            neg["compo_fourier"]=="FORMULA_TEASER_ALLOWED" and
            neg["prob_bayes"]=="STATIC_COMPARE_ALLOWED","COUNTEREXAMPLE_REGRESS")
    schema=contract["schema"]
    Draft202012Validator.check_schema(schema)
    item=schema["properties"]["expected_observable_explanation"]["items"]
    require("STATIC_COMPARISON" in item["properties"]["witness_type"]["enum"]
            and "SYMBOLIC_DEDUCTION" in item["properties"]["witness_type"]["enum"]
            and item.get("allOf"),"STATIC_WITNESS_UNSUPPORTED")
    native=read(NATIVE)
    require(native["checkpoint"]=="V3-56" and native["origin"]=="USER_SUPPLIED_UPLOADED_FULL_MP4",
            "NATIVE_PROVENANCE")
    require(len(native["content_sha256"])==64 and native["shared_media_redistributed_to_repo"] is False,
            "NATIVE_HASH_OR_COPYRIGHT")
    media=native["media"]
    require(media["width"]==1280 and media["height"]==720 and media["fps_num"]==30
            and media["video_codec"]=="h264" and media["audio_codec"]=="aac"
            and media["total_decodable_frame_index_count"]==47076,"NATIVE_MEDIA_CONTRACT")
    inspection=native["visual_inspection"]
    require(inspection["frame_images_verified_directly"] is True and
            inspection["number_global_frame_times_every_15s"]>=100 and
            len(native["timestamped_visual_beats"])>=15,
            "INSUFFICIENT_NATIVE_FILM_COVERAGE")
    require(inspection["words_in_audio_manually_transcribed"] is False and
            inspection["word_alignment_measured"] is False,
            "AUDIO_ALIGNMENT_FALSE_CLAIM")
    require(inspection["original_clip_audio_stream_present"] is True,
            "AUDIO_STREAM_NOT_CHECKED")
    require(native["gate"]["native_encoded_file_acquired"]==1 and
            native["gate"]["full_video_audio_word_aligned"]==0,
            "NATIVE_EVIDENCE_WRONG_SCOPE")
    for beat in native["timestamped_visual_beats"]:
        require(0<=beat["sampled_frame_s"]<media["duration_s"] and
                beat["approx_interval_start_s"]<=beat["sampled_frame_s"]<=beat["approx_interval_end_s"] and
                beat["timecode_precision"]=="APPROXIMATE_SECTION_BOUNDARIES_NOT_FRAME_EXACT_CUTS",
                "FAKE_OR_OUT_OF_BOUNDS_NATIVE_PTS")
    real_native_video_count=sum(x["complete_native_video_inspected"] for x in byid.values())
    video_verdict="VIDEO_AUDIT_PASS" if real_native_video_count>=preg["all_video_required_count"] else "VIDEO_AUDIT_NO_GO"
    require(video_verdict=="VIDEO_AUDIT_NO_GO","IMPOSSIBLE_NATIVE_ATTESTATION")
    return {"checkpoint":"V3-56","source_file_research":"PASS", "read_beat_reconstruction":"PASS",
            "lesson_reads":len(byid),"verified_scene_source_files":len(src),
            "read_pedagogical_beats":beats["totals"]["read_pedagogical_beats"],
            "full_video_timeline_and_audio":video_verdict,
            "actual_native_video_review_count":real_native_video_count,
            "native_uploaded_video_visual_samples_verified":native["gate"]["source_video_frame_covered"],
            "native_uploaded_video_audio_stream_verified":int(inspection["original_clip_audio_stream_present"]),
            "native_uploaded_video_word_alignment_count":native["gate"]["full_video_audio_word_aligned"],
            "required_native_video_review_count":preg["all_video_required_count"],
            "human_learning_gains":"NOT_TESTED",
            "next_checkpoint_blocked_on_media":True,"model_api_calls":0,"production":"BLOCKED"}

if __name__=="__main__":
    print(json.dumps(check(),indent=2,sort_keys=True))
