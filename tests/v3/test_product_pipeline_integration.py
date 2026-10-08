"""V3-18 app HTTP product-entrypoint real MP4 gate tests (offline, no providers).

Build FastAPI with its actual factory, actual app.state.pipeline and router,
actual SQLite repository and LocalArtifactStore. Never call a golden script.
The exposed endpoint returns only a QA receipt; MP4 stays local and unserved.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.pipeline.fake import FakePipeline
from app.pipeline.v3_preview import V3OfflinePreviewPipeline

PAYLOAD={
    "family":"WORKED_EXAMPLE_BOARD",
    "values":[1,3,5,7,9,12,12,14,18],
    "target":12,
}


def _app(tmp_path:Path,*,enabled:bool=True,environment:str="test"):
    settings=Settings(
        environment=environment,pipeline_mode="fake",render_profile="test",
        db_path=str(tmp_path/"offline_test.db"),
        artifacts_dir=str(tmp_path/"artifacts"),
        v3_binary_preview_enabled=enabled,
        gemini_api_key="",
        enable_image_generation=False,
    )
    return create_app(settings=settings),settings


def _probe(video:Path):
    p=subprocess.run([
        "ffprobe","-v","error","-show_entries",
        "stream=codec_name,width,height,nb_frames,codec_type",
        "-of","json",str(video),
    ],text=True,capture_output=True,check=True,timeout=25)
    streams=json.loads(p.stdout)["streams"]
    assert len(streams)==1
    return streams[0]


def test_default_flag_off_preserves_factory_and_blocks_http(tmp_path):
    app,settings=_app(tmp_path,enabled=False)
    assert settings.v3_binary_preview_enabled is False
    assert type(app.state.pipeline) is FakePipeline
    with TestClient(app) as client:
        assert client.get("/healthz").status_code==200
        blocked=client.post("/api/v3/offline/binary-search",json=PAYLOAD)
        assert blocked.status_code==404
        assert blocked.json()["detail"]=="V3 offline preview is disabled"
        legacy=client.post("/api/jobs",json={
            "topic":"How a TCP handshake works","audience":"Beginner",
            "language":"en","target_duration_seconds":60,
        })
        assert legacy.status_code==202
        assert legacy.json()["job_id"]
    assert not (Path(settings.artifacts_dir)/"v3offline").exists()
    assert not any(Path(settings.artifacts_dir).glob("v3offline*"))


def test_feature_on_uses_same_factory_pipeline_and_does_not_change_legacy_job(tmp_path):
    app,settings=_app(tmp_path)
    assert isinstance(app.state.pipeline,V3OfflinePreviewPipeline)
    assert isinstance(app.state.pipeline.legacy,FakePipeline)
    assert app.state.runner.pipeline is app.state.pipeline
    assert app.state.pipeline.requires_published_artifact is False
    with TestClient(app) as client:
        res=client.post("/api/jobs",json={
            "topic":"Existing unchanged V2 job","audience":"Beginner",
            "language":"en","target_duration_seconds":60,
        })
        assert res.status_code==202
        assert not list(Path(settings.artifacts_dir).glob("v3offline*"))


@pytest.fixture(scope="module")
def real_http(tmp_path_factory):
    temp=tmp_path_factory.mktemp("v3_18_real_fastapi")
    app,settings=_app(temp)
    with TestClient(app) as client:
        response=client.post("/api/v3/offline/binary-search",json=PAYLOAD)
    return response,Path(settings.artifacts_dir)


def test_real_http_request_to_original_renderer_and_assembled_h264(real_http):
    response,root=real_http
    assert response.status_code==200,response.text[:350]
    data=response.json()
    assert data["status"]=="OFFLINE_PREVIEW_QA_PASS_NOT_PUBLISHED"
    assert data["representation"]=="WORKED_EXAMPLE_BOARD"
    assert data["renderer_family"]=="STATEFUL_SEQUENCE_BINARY_SEARCH"
    assert data["qa"]=="BOUNDED_SOURCE_AND_DECODED_PIXEL_PASS"
    assert data["publication"]=="PUBLISH_BLOCKED"
    assert data["public_video_url"] is None
    assert data["production_renderer_registered"] is False
    assert data["human_quality"]=="UNMEASURED"
    assert data["audio"]=="NOT_GENERATED"
    assert data["frame_count"]==36
    assert data["width"]==640 and data["height"]==360 and data["fps"]==12
    assert data["beat_ids"]==["beat-01","beat-02","beat-03","beat-04"]
    assert data["claim_ids"]==["claim-01"]
    assert data["object_ids"]==["array-01"]
    assert data["deferred_signal_count"]>0
    parent=root/data["preview_id"]
    video=parent/"integrated_binary_lesson.mp4"
    receipt_path=parent/"integrated_binary_lesson.receipt.json"
    assert parent.is_dir()
    assert video.is_file() and video.stat().st_size>1000
    assert receipt_path.is_file()
    assert set(p.name for p in parent.iterdir())=={
        "integrated_binary_lesson.mp4",
        "integrated_binary_lesson.receipt.json",
    }
    assert not (parent/"final.mp4").exists()
    assert not (parent/"final.pending.mp4").exists()
    assert _probe(video)=={
        "codec_name":"h264","codec_type":"video",
        "width":640,"height":360,"nb_frames":"36",
    }
    receipt=json.loads(receipt_path.read_text())
    assert receipt["assembled_video_sha256"]==data["assembled_video_sha256"]
    assert receipt["trace_sha256"]==data["source_trace_sha256"]
    assert receipt["route_sha256"]==data["source_route_sha256"]
    assert receipt["report_sha256"]==data["manifest_sha256"]
    assert receipt["decoded_assembly_rgb_sha256"]==data["decoded_rgb_sha256"]
    assert receipt["publication"]=="PUBLISH_BLOCKED"
    assert receipt["web_pipeline_connected"] is False
    assert hashlib.sha256(video.read_bytes()).hexdigest()==data["assembled_video_sha256"]


def test_http_feature_does_not_expose_preview_through_legacy_job_video(real_http,tmp_path):
    response,root=real_http
    preview_id=response.json()["preview_id"]
    app,_=_app(tmp_path)
    with TestClient(app) as client:
        response=client.get(f"/api/jobs/{preview_id}/video")
        assert response.status_code==404
        response=client.get(f"/api/jobs/{preview_id}")
        assert response.status_code==404
    assert (root/preview_id/"integrated_binary_lesson.mp4").is_file()


@pytest.mark.parametrize("family",[
    "PROCESS_FLOW","EQUATION_GRAPH","CODE_WALKTHROUGH",
    "STATE_MACHINE","CONCEPT_CARD",
])
def test_unsupported_family_abstains_without_creating_video(tmp_path,family):
    app,settings=_app(tmp_path)
    with TestClient(app) as client:
        response=client.post(
            "/api/v3/offline/binary-search",json=PAYLOAD|{"family":family})
    assert response.status_code==422
    assert "ABSTAIN_UNCONNECTED_FAMILY" in response.text
    assert "no CONCEPT_CARD fallback" in response.text
    assert not list(Path(settings.artifacts_dir).glob("v3offline*"))


@pytest.mark.parametrize("values,target",[
    ([3,1,2],2),([1,2],1),([1]*13,1),
    ([1,2,3],1000001),([1,2,1000001],3),
])
def test_invalid_sorted_range_fails_closed_no_temp_outputs(tmp_path,values,target):
    app,settings=_app(tmp_path)
    with TestClient(app) as client:
        r=client.post("/api/v3/offline/binary-search",
                      json=PAYLOAD|{"values":values,"target":target})
    assert r.status_code==422
    assert not list(Path(settings.artifacts_dir).glob("v3offline*"))


def test_boolean_forged_integer_rejected_at_http_schema(tmp_path):
    app,settings=_app(tmp_path)
    with TestClient(app) as client:
        r=client.post("/api/v3/offline/binary-search",
                      json=PAYLOAD|{"values":[1,True,3]})
    assert r.status_code==422
    assert not list(Path(settings.artifacts_dir).glob("v3offline*"))


def test_production_cannot_enable_v3_even_in_fake_mode(tmp_path):
    settings=Settings(
        environment="production",pipeline_mode="fake",
        v3_binary_preview_enabled=True,
        db_path=str(tmp_path/"bad.db"),artifacts_dir=str(tmp_path/"artifacts"),
    )
    from app.pipeline.factory import create_pipeline
    from app.repositories.sqlite import SqliteJobRepository
    from app.storage.local import LocalArtifactStore
    with pytest.raises(RuntimeError,match="V3 developer preview must not run in production"):
        create_pipeline(settings,SqliteJobRepository(str(tmp_path/"data.db")),
                        LocalArtifactStore(tmp_path/"artifacts"))


def test_renderer_writes_partial_file_then_crashes_cleanup_entire_preview(tmp_path,monkeypatch):
    app,settings=_app(tmp_path)
    import app.pipeline.v3_preview as preview_mod
    def partial(*,source,out_dir,profile):
        (out_dir/"integrated_binary_lesson.mp4").write_bytes(b"broken partial MP4")
        raise RuntimeError("intentional crash after writing")
    monkeypatch.setattr(preview_mod,"run_integrated_binary_clip",partial)
    with TestClient(app) as client:
        r=client.post("/api/v3/offline/binary-search",json=PAYLOAD)
    assert r.status_code==500
    assert "nothing published" in r.json()["detail"]
    assert not list(Path(settings.artifacts_dir).glob("v3offline*"))


def test_tampered_source_before_video_does_not_publish(tmp_path,monkeypatch):
    app,settings=_app(tmp_path)
    import app.pipeline.v3_preview as preview_mod
    from dataclasses import replace
    from learnflow_v3.models import VisualTeachingPlan
    good=preview_mod.build_binary_lesson_source
    def tampered(*,values,target):
        source=good(values=values,target=target)
        plan=source.plan.model_dump(mode="json")
        plan["beats"][0]["claim_refs"]=["fabricated-claim"]
        return replace(source,plan=VisualTeachingPlan.model_validate(plan))
    monkeypatch.setattr(preview_mod,"build_binary_lesson_source",tampered)
    with TestClient(app) as client:
        r=client.post("/api/v3/offline/binary-search",json=PAYLOAD)
    assert r.status_code==500
    assert not list(Path(settings.artifacts_dir).glob("v3offline*"))


def test_wrong_host_blocked_even_with_flag_on(tmp_path):
    app,settings=_app(tmp_path)
    # Starlette TestClient lets us simulate a remote peer host.
    with TestClient(app,client=("203.0.113.17",2345)) as client:
        r=client.post("/api/v3/offline/binary-search",json=PAYLOAD)
    assert r.status_code==403
    assert not list(Path(settings.artifacts_dir).glob("v3offline*"))
