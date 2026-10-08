"""V3-20 actual HTTP audible event boundaries vs V3-19 implicit progress.

No word/phoneme forced alignment, no independent ASR lexical judgment.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app
from learnflow_v2.repair import compute_content_hash
from learnflow_v3.event_alignment import (
    authored_event_specs,certify_event_boundaries,verify_event_proof,
)
from learnflow_v3.models import SemanticContractError,VisualTeachingPlan
from learnflow_v3.narrated_lesson import NarratedLessonReceipt,verify_narrated_lesson
from learnflow_v3.offline_lesson_source import build_binary_lesson_source

INPUT={"family":"WORKED_EXAMPLE_BOARD",
       "values":[0,2,4,7,11,15,15,21,30],"target":15}


def _app(tmp_path,*,enabled=True):
    settings=Settings(
        environment="test",pipeline_mode="fake",
        db_path=str(tmp_path/"test.db"),artifacts_dir=str(tmp_path/"private"),
        v3_binary_preview_enabled=True,v3_narrated_lesson_enabled=True,
        v3_event_alignment_enabled=enabled,
        gemini_api_key="",enable_image_generation=False,
    )
    return create_app(settings=settings),settings


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    folder=tmp_path_factory.mktemp("v3_20_true_event_phrases")
    app,settings=_app(folder)
    with TestClient(app) as client:
        r=client.post("/api/v3/offline/binary-search-event-aligned",json=INPUT)
        assert r.status_code==200,r.text[:350]
        response=r.json()
        assert client.get(f"/api/jobs/{response['preview_id']}/video").status_code==404
    path=Path(settings.artifacts_dir)/response["preview_id"]
    source=build_binary_lesson_source(
        values=tuple(INPUT["values"]),target=INPUT["target"])
    receipt=NarratedLessonReceipt.model_validate_json(
        (path/"narrated_binary_lesson.receipt.json").read_text())
    proof=json.loads((path/"narrated_binary_lesson.event_proof.json").read_text())
    return path,source,response,receipt,proof


def test_real_http_speaking_each_oracle_event_matches_source_video_and_audio(live):
    folder,source,r,receipt,proof=live
    assert r["status"]=="OFFLINE_EVENT_ALIGNED_QA_PASS_NOT_PUBLISHED"
    assert r["public_video_url"] is None
    assert r["publication"]=="PUBLISH_BLOCKED"
    assert r["event_boundary_alignment"]=="MEASURED_UTTERANCE_BOUNDARIES_NOT_WORD_LEVEL"
    assert r["event_proof_sha256"]==receipt.event_proof_sha256
    assert receipt.word_alignment=="UNMEASURED_NOT_FORCED_ALIGNMENT"
    assert r["lexical_transcript_as_heard"]=="UNMEASURED"
    assert proof["spoken_text_lexical_asr"]=="UNMEASURED"
    assert proof["human_pedagogy_or_visual_preference"]=="UNMEASURED"
    assert proof["published"] is False
    assert receipt.publication=="PUBLISH_BLOCKED"
    assert len(receipt.segments)>len(source.trace.steps)+3
    assert all(s["source_trace_sha256"]==source.trace.trace_sha256
               for s in receipt.segments)
    assert not (folder/"final.mp4").exists()
    assert (folder/"narrated_binary_lesson.mp4").stat().st_size>40000
    assert (folder/"narrated_binary_lesson.srt").is_file()
    assert hashlib.sha256((folder/"narrated_binary_lesson.mp4").read_bytes()).hexdigest()==r["video_sha256"]
    verify_event_proof(source=source,segments=receipt.segments,supplied=proof)
    verify_narrated_lesson(source=source,folder=folder,receipt=receipt)


def test_physically_measured_apply_only_after_matching_observe_utterance(live):
    _,source,_,receipt,proof=live
    scenes=receipt.segments
    expected=authored_event_specs(source)
    assert [s["event_kind"] for s in scenes]==[s["event_kind"] for s in expected]
    for i,part in enumerate(scenes):
        assert part["event_id"]==expected[i]["event_id"]
        assert part["visual_step"]==expected[i]["visual_step"]
        assert part["expected_low"]==source.trace.steps[part["visual_step"]].low
        assert part["expected_high"]==source.trace.steps[part["visual_step"]].high
        assert part["frame_start"]==round(part["seconds_start"]*12)
        assert abs(part["raw_spoken_duration_seconds"]-
                   part["raw_spoken_samples"]/part["spoken_sample_rate"])<1e-7
        if part["event_kind"]=="APPLY":
            observe=scenes[i-1]
            assert observe["event_kind"]=="OBSERVE"
            assert observe["step"]==part["step"]
            assert observe["visual_step"]==part["step"]
            assert part["visual_step"]==part["step"]+1
            assert part["frame_start"]==observe["frame_end_exclusive"]
            assert part["seconds_start"]==observe["seconds_end"]
            assert part["spoken_wav_sha256"]!=observe["spoken_wav_sha256"]
            assert observe["beat_id"]==part["beat_id"]
    assert proof["event_count"]==len(scenes)
    assert proof["trace_comparisons"]==len([s for s in source.trace.steps if s.phase=="COMPARE"])


def test_shifted_rehashed_event_boundary_must_fail(live):
    _,source,_,receipt,proof=live
    data=receipt.model_dump(mode="json")
    steps=data["segments"]
    first_update=next(i for i,s in enumerate(steps) if s["event_kind"]=="APPLY")
    steps[first_update]["frame_start"]+=1
    with pytest.raises(SemanticContractError,match="NONCONTIGUOUS_EVENT_FRAMES"):
        certify_event_boundaries(source=source,segments=tuple(steps))


def test_changed_oracle_event_identity_cannot_be_self_rehashed(live):
    _,source,_,receipt,proof=live
    data=json.loads(json.dumps(proof))
    data["events"][3]["expected_oracle_step"]+=1
    data["proof_sha256"]=compute_content_hash({
        k:v for k,v in data.items() if k!="proof_sha256"})
    with pytest.raises(SemanticContractError,match="STALE_OR_SELF_REHASHED_EVENT_PROOF"):
        verify_event_proof(source=source,segments=receipt.segments,supplied=data)


def test_wrong_audio_sample_count_after_rehash_must_fail(live):
    _,source,_,receipt,_=live
    rows=json.loads(json.dumps(receipt.model_dump(mode="json")["segments"]))
    rows[2]["raw_spoken_samples"]+=12000
    with pytest.raises(SemanticContractError,match="FABRICATED_AUDIO_DURATION"):
        certify_event_boundaries(source=source,segments=tuple(rows))


def test_replayed_shifted_subtitle_must_fail(live):
    _,source,_,receipt,_=live
    rows=json.loads(json.dumps(receipt.model_dump(mode="json")["segments"]))
    rows[2]["subtitle_start"]+=1.
    with pytest.raises(SemanticContractError,match="EVENT_AUDIO_FRAME_SHIFT"):
        certify_event_boundaries(source=source,segments=tuple(rows))


def test_forged_word_alignment_cannot_pass_even_with_matching_receipt_hash(live):
    _,_,_,receipt,_=live
    d=receipt.model_dump(mode="json")
    d["word_alignment"]="FORCED_ALIGNMENT_PASS"
    d["report_sha256"]=compute_content_hash({
        k:v for k,v in d.items() if k!="report_sha256"})
    with pytest.raises(ValidationError,match="FORGED_PUBLICATION_OR_ALIGNMENT"):
        NarratedLessonReceipt.model_validate(d)


def test_wrong_semantic_source_fails_even_when_artifact_exists(live):
    folder,source,_,receipt,_=live
    source_plan=source.plan.model_dump(mode="json")
    source_plan["sections"][0]["visual_teaching_goal"]="Fake changed objective"
    bad=replace(source,plan=VisualTeachingPlan.model_validate(source_plan))
    with pytest.raises(SemanticContractError):
        verify_narrated_lesson(source=bad,folder=folder,receipt=receipt)


def test_missing_audio_video_and_event_proof_fail_closed(live,tmp_path):
    folder,source,_,receipt,_=live
    target=tmp_path/"mutated";target.mkdir()
    for f in folder.iterdir():shutil.copy2(f,target/f.name)
    (target/"narrated_binary_lesson.event_proof.json").unlink()
    with pytest.raises(SemanticContractError,match="MISSING_PHYSICAL_EVENT_PROOF"):
        verify_narrated_lesson(source=source,folder=target,receipt=receipt)


def test_disabled_event_flag_returns_404_without_files(tmp_path):
    app,settings=_app(tmp_path,enabled=False)
    with TestClient(app) as client:
        res=client.post("/api/v3/offline/binary-search-event-aligned",json=INPUT)
        assert res.status_code==404
    assert not list(Path(settings.artifacts_dir).glob("v3narrated*"))


def test_other_family_abstains_no_cards_no_video(tmp_path):
    app,settings=_app(tmp_path)
    with TestClient(app) as client:
        res=client.post("/api/v3/offline/binary-search-event-aligned",
                        json=INPUT|{"family":"STATE_MACHINE"})
        assert res.status_code==422
        assert "ABSTAIN_UNCONNECTED_FAMILY" in res.text
    assert not list(Path(settings.artifacts_dir).glob("v3narrated*"))


def test_remote_not_authorized(tmp_path):
    app,settings=_app(tmp_path)
    with TestClient(app,client=("203.0.113.55",444)) as client:
        res=client.post("/api/v3/offline/binary-search-event-aligned",json=INPUT)
        assert res.status_code==403
    assert not list(Path(settings.artifacts_dir).glob("v3narrated*"))


def test_audio_renderer_partial_write_and_crash_keeps_no_artifact(tmp_path,monkeypatch):
    app,settings=_app(tmp_path)
    import app.pipeline.v3_preview as adapter
    def crashes(*,source,out,event_aware=False):
        (out/"narrated_binary_lesson.mp4").write_bytes(b"partial corrupted mp4")
        raise RuntimeError("broken renderer")
    monkeypatch.setattr("learnflow_v3.narrated_lesson.build_narrated_lesson",crashes)
    with TestClient(app) as client:
        res=client.post("/api/v3/offline/binary-search-event-aligned",json=INPUT)
        assert res.status_code==500
    assert not list(Path(settings.artifacts_dir).glob("v3narrated*"))


def test_production_flag_refused_before_any_provider(tmp_path):
    from app.pipeline.factory import create_pipeline
    from app.repositories.sqlite import SqliteJobRepository
    from app.storage.local import LocalArtifactStore
    settings=Settings(
        environment="production",pipeline_mode="fake",
        v3_binary_preview_enabled=True,
        v3_narrated_lesson_enabled=True,
        v3_event_alignment_enabled=True)
    with pytest.raises(RuntimeError,match="developer preview must not run in production"):
        create_pipeline(settings,SqliteJobRepository(str(tmp_path/"local.db")),
                        LocalArtifactStore(tmp_path))



def test_regressed_renderer_rewinds_pointer_at_scene_boundary_is_rejected(tmp_path,monkeypatch):
    """Mutation: a decoder oracle sampled only mid-scene would miss this."""
    import learnflow_v3.narrated_lesson as narrator
    source=build_binary_lesson_source(
        values=(0,2,4,7,11,15,15,21,30),target=15)
    original=narrator._narrated_frame

    def rewind_at_first_observe(*,source,spec,profile,progress):
        if spec.get("event_kind")=="OBSERVE" and spec.get("visual_step",0)>0:
            # Reproduce old V3-19 mistake: re-run the 0→1 tween at the
            # beginning of the NEXT observation, temporarily moving LOW back.
            faulty={**spec,"event_kind":"LEGACY_SCENE_REWIND"}
            return original(source=source,spec=faulty,profile=profile,progress=progress)
        return original(source=source,spec=spec,profile=profile,progress=progress)

    monkeypatch.setattr(narrator,"_narrated_frame",rewind_at_first_observe)
    receipt=narrator.build_narrated_lesson(
        source=source,out=tmp_path,event_aware=True)
    assert (tmp_path/"narrated_binary_lesson.mp4").is_file()
    with pytest.raises(SemanticContractError,
                       match="EVENT_SCENE_BOUNDARY_REWINDS_STATE"):
        narrator.verify_narrated_lesson(
            source=source,folder=tmp_path,receipt=receipt)
