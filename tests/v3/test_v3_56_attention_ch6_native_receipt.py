"""The first supplied original 3B1B film does not magically satisfy 15 aligned films."""
from scripts.verify_v3_56_deep_video_audit import check, read, NATIVE


def test_real_attention_native_film_sha_codec_and_coverage():
    d=read(NATIVE)
    assert d["origin"]=="USER_SUPPLIED_UPLOADED_FULL_MP4"
    assert d["content_sha256"]=="439e154fffbb8696a37753d765c4f64bc06d25fbb17cb3d98bcc842045d85cb9"
    assert d["media"]["duration_s"]>1500
    assert d["media"]["total_decodable_frame_index_count"]==47076
    assert d["visual_inspection"]["number_global_frame_times_every_15s"]>=100
    assert len(d["timestamped_visual_beats"])==16
    assert all(0<=b["sampled_frame_s"]<d["media"]["duration_s"] for b in d["timestamped_visual_beats"])
    assert d["shared_media_redistributed_to_repo"] is False


def test_native_frames_dont_fabricate_voice_word_alignment():
    d=read(NATIVE)
    assert d["visual_inspection"]["original_clip_audio_stream_present"]
    assert d["visual_inspection"]["words_in_audio_manually_transcribed"] is False
    assert d["visual_inspection"]["word_alignment_measured"] is False
    assert d["gate"]["native_encoded_file_acquired"]==1
    assert d["gate"]["full_video_audio_word_aligned"]==0
    assert "NOT" in d["gate"]["quality_inference"]


def test_research_protocol_remains_15_full_media_audits_no_go():
    out=check()
    assert out["native_uploaded_video_visual_samples_verified"]==1
    assert out["native_uploaded_video_audio_stream_verified"]==1
    assert out["native_uploaded_video_word_alignment_count"]==0
    assert out["full_video_timeline_and_audio"]=="VIDEO_AUDIT_NO_GO"
    assert out["production"]=="BLOCKED"


def test_temporal_motion_and_static_cases_both_proven_via_real_frames():
    d=read(NATIVE)
    pairs=d["motion_cases"]
    assert len(pairs)>=8
    static=[p for p in pairs if p["changed_fraction_gt25"]<0.02]
    moving=[p for p in pairs if p["changed_fraction_gt25"]>0.5]
    assert len(static)>=2 and len(moving)>=2
    assert all(p["a_s"]<p["b_s"] for p in pairs)
