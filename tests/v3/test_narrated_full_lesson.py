"""V3-19: real locally spoken English, source-grounded multi-scene HTTP lesson.

Proof is per-scene measured-sample boundaries, never invented phoneme timing.
No real provider, external APIs, production publication or human-quality pass.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from dataclasses import replace
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import create_app
from app.config import Settings
from app.pipeline.v3_preview import V3OfflinePreviewPipeline
from learnflow_v3.narrated_lesson import (
    NarratedLessonReceipt,build_narrated_lesson,verify_narrated_lesson,
)
from learnflow_v3.models import SemanticContractError,VisualTeachingPlan
from learnflow_v3.offline_lesson_source import build_binary_lesson_source

SOURCE={"family":"WORKED_EXAMPLE_BOARD","values":[1,3,5,7,9,11,13],
        "target":9}


def _app(tmp_path:Path,*,binary:bool=True,narrated:bool=True,env:str="test"):
    settings=Settings(
        environment=env,pipeline_mode="fake",render_profile="test",
        db_path=str(tmp_path/"local.db"),
        artifacts_dir=str(tmp_path/"artifacts"),
        v3_binary_preview_enabled=binary,
        v3_narrated_lesson_enabled=narrated,
        gemini_api_key="",enable_image_generation=False)
    return create_app(settings=settings),settings


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    root=tmp_path_factory.mktemp("v3_19_real_spoken_lesson")
    app,settings=_app(root)
    with TestClient(app) as client:
        result=client.post("/api/v3/offline/binary-search-lesson",json=SOURCE)
        assert result.status_code==200,result.text[:300]
        identity=result.json()
        assert client.get(f"/api/jobs/{identity['preview_id']}/video").status_code==404
    return root,identity,Path(settings.artifacts_dir)/identity["preview_id"]


def test_actual_http_narrated_multiscene_video_and_sources(live):
    _,data,folder=live
    receipt=NarratedLessonReceipt.model_validate_json(
        (folder/"narrated_binary_lesson.receipt.json").read_text())
    source=build_binary_lesson_source(values=tuple(SOURCE["values"]),
                                     target=SOURCE["target"])
    verify_narrated_lesson(source=source,folder=folder,receipt=receipt)
    assert receipt.publication=="PUBLISH_BLOCKED"
    assert receipt.kind=="OFFLINE_MULTISCENE_REAL_SPEECH_NOT_PUBLISHED"
    assert receipt.speech_origin=="LOCAL_ESPEAK_SYNTHESIZED_WAV"
    assert receipt.segment_alignment=="MEASURED_AUDIO_SAMPLES_SCENE_BOUNDARIES"
    assert receipt.word_alignment=="UNMEASURED_NOT_FORCED_ALIGNMENT"
    assert receipt.real_human_lexical_review=="UNMEASURED"
    assert receipt.real_lesson_quality=="UNMEASURED"
    assert receipt.duration_seconds>20
    assert receipt.total_frames>200
    assert len(receipt.segments)>=6
    assert set(x["role"] for x in receipt.segments)=={
        "INTRODUCTION","EXPLANATION","WORKED_EXAMPLE","RECAP"
    }
    assert all(x["speech_energy_rms"]>.006 for x in receipt.segments)
    assert receipt.video_sha256==hashlib.sha256(
        (folder/"narrated_binary_lesson.mp4").read_bytes()).hexdigest()
    assert receipt.report_sha256==data["manifest_sha256"]
    assert data["video_sha256"]==receipt.video_sha256
    assert data["audio_codec"]=="aac" and data["video_codec"]=="h264"
    assert data["public_video_url"] is None
    assert data["human_quality"]=="UNMEASURED"
    assert set(p.name for p in folder.iterdir())=={
        "narrated_binary_lesson.mp4",
        "narrated_binary_lesson.srt",
        "narrated_binary_lesson.receipt.json",
    }
    assert not (folder/"final.mp4").exists()


def test_measured_audio_cues_and_beat_scene_identity(live):
    _,data,folder=live
    receipt=NarratedLessonReceipt.model_validate_json(
        (folder/"narrated_binary_lesson.receipt.json").read_text())
    cursor=0
    for e in receipt.segments:
        assert e["frame_start"]==cursor
        assert e["frame_end_exclusive"]>cursor
        assert e["subtitle_start"]==e["seconds_start"]
        assert abs(e["subtitle_end"]-e["subtitle_start"]-
                   e["raw_spoken_duration_seconds"])<1e-5
        assert e["claim_refs"]==["claim-01"]
        assert e["object_ids"]==["array-01"]
        assert e["source_trace_sha256"]==receipt.source_trace_sha256
        assert e["spoken_wav_sha256"]!=receipt.video_sha256
        cursor=e["frame_end_exclusive"]
    assert abs(cursor-receipt.total_frames)<=1
    assert data["scene_count"]==len(receipt.segments)
    assert data["beat_ids"]==[s["beat_id"] for s in receipt.segments]
    subs=(folder/"narrated_binary_lesson.srt").read_text()
    assert subs.count("-->")==len(receipt.segments)
    assert "Binary search" in subs or "binary search" in subs


def test_missing_or_mutated_audio_video_detected(live,tmp_path):
    _,_,folder=live
    source=build_binary_lesson_source(values=tuple(SOURCE["values"]),
                                     target=SOURCE["target"])
    receipt=NarratedLessonReceipt.model_validate_json(
        (folder/"narrated_binary_lesson.receipt.json").read_text())
    new=tmp_path/"corrupt";new.mkdir()
    for p in folder.iterdir():shutil.copy2(p,new/p.name)
    (new/"narrated_binary_lesson.mp4").write_bytes(b"invalid or missing AAC track")
    with pytest.raises(SemanticContractError,match="STALE_AUDIO_VIDEO"):
        verify_narrated_lesson(source=source,folder=new,receipt=receipt)


def test_subtitle_time_and_trace_drift_detected(live,tmp_path):
    _,_,folder=live
    source=build_binary_lesson_source(values=tuple(SOURCE["values"]),
                                     target=SOURCE["target"])
    receipt=NarratedLessonReceipt.model_validate_json(
        (folder/"narrated_binary_lesson.receipt.json").read_text())
    new=tmp_path/"subtitle_corrupt";new.mkdir()
    for p in folder.iterdir():shutil.copy2(p,new/p.name)
    subtitles=new/"narrated_binary_lesson.srt"
    subtitles.write_text(subtitles.read_text().replace("-->","--> 23:00:00,000"))
    with pytest.raises(SemanticContractError,match="STALE_AUDIO_VIDEO"):
        verify_narrated_lesson(source=source,folder=new,receipt=receipt)
    wrong=build_binary_lesson_source(values=(1,3,5,7,9,11,13),target=7)
    with pytest.raises(SemanticContractError,match="SOURCE_TRACE"):
        verify_narrated_lesson(source=wrong,folder=folder,receipt=receipt)


def test_forged_claim_beat_scene_or_alignment_fails_receipt_validation(live):
    _,_,folder=live
    data=json.loads((folder/"narrated_binary_lesson.receipt.json").read_text())
    from learnflow_v2.repair import compute_content_hash
    for key,value in (("word_alignment","FORCED_PASS"),
                      ("publication","PUBLISH_ALLOWED"),
                      ("real_human_lexical_review","PASS")):
        bad=json.loads(json.dumps(data))
        bad[key]=value
        bad["report_sha256"]=compute_content_hash({
            k:v for k,v in bad.items() if k!="report_sha256"})
        with pytest.raises(ValidationError):
            NarratedLessonReceipt.model_validate(bad)
    for key,value in (("frame_start",500),("subtitle_end",999),
                      ("claim_refs",["claim-fabricated"]),
                      ("source_trace_sha256","f"*64)):
        bad=json.loads(json.dumps(data))
        bad["segments"][1][key]=value
        bad["report_sha256"]=compute_content_hash({
            k:v for k,v in bad.items() if k!="report_sha256"})
        with pytest.raises(ValidationError):
            NarratedLessonReceipt.model_validate(bad)


def test_flags_default_off_and_independent_gate(tmp_path):
    app,_=_app(tmp_path,binary=False,narrated=False)
    with TestClient(app) as client:
        assert client.post("/api/v3/offline/binary-search-lesson",
                           json=SOURCE).status_code==404
        assert client.get("/healthz").status_code==200
    from app.pipeline.factory import create_pipeline
    from app.repositories.sqlite import SqliteJobRepository
    from app.storage.local import LocalArtifactStore
    settings=Settings(environment="test",pipeline_mode="fake",
                      v3_narrated_lesson_enabled=True,
                      v3_binary_preview_enabled=False)
    with pytest.raises(RuntimeError,match="requires explicit V3 binary"):
        create_pipeline(settings,SqliteJobRepository(str(tmp_path/"other.db")),
                        LocalArtifactStore(tmp_path/"sandbox"))


def test_remote_peer_and_unsupported_family_no_video(tmp_path):
    app,settings=_app(tmp_path)
    with TestClient(app,client=("203.0.113.12",43000)) as c:
        assert c.post("/api/v3/offline/binary-search-lesson",json=SOURCE).status_code==403
    with TestClient(app) as c:
        r=c.post("/api/v3/offline/binary-search-lesson",
                 json=SOURCE|{"family":"PROCESS_FLOW"})
        assert r.status_code==422 and "ABSTAIN" in r.text
    assert not list(Path(settings.artifacts_dir).glob("v3narrated*"))


def test_missing_offline_tts_abstains_without_leaking_private_artifact(tmp_path,monkeypatch):
    app,settings=_app(tmp_path)
    import learnflow_v3.narrated_lesson as module
    monkeypatch.setattr(module,"_tts_executable",
                        lambda:module._block("OFFLINE_LICENSED_SPEECH_PROVIDER_MISSING"))
    with TestClient(app) as client:
        response=client.post("/api/v3/offline/binary-search-lesson",json=SOURCE)
    assert response.status_code==500
    assert "not published" in response.text
    assert not list(Path(settings.artifacts_dir).glob("v3narrated*"))


def test_partial_write_crash_cleaned_and_unpublished(tmp_path,monkeypatch):
    app,settings=_app(tmp_path)
    import learnflow_v3.narrated_lesson as module
    def fail_after_side_effect(*,source,out):
        (out/"narrated_binary_lesson.mp4").write_bytes(b"PARTIAL_WROTE_MP4")
        raise RuntimeError("after renderer partial write")
    monkeypatch.setattr(module,"build_narrated_lesson",fail_after_side_effect)
    with TestClient(app) as client:
        response=client.post("/api/v3/offline/binary-search-lesson",json=SOURCE)
    assert response.status_code==500
    assert not list(Path(settings.artifacts_dir).glob("v3narrated*"))
