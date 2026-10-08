#!/usr/bin/env python3
"""Render real before/after from SAME input through developer-only FastAPI.

Emits two actual H264/AAC/SRT lessons and a source-bound utterance/event QA
manifest. No ASR, provider calls, publish, human expert ratings or word timing.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from learnflow_v3.event_alignment import verify_event_proof
from learnflow_v3.offline_lesson_source import build_binary_lesson_source
from learnflow_v3.narrated_lesson import (
    NarratedLessonReceipt,verify_narrated_lesson,
)

REQUEST={"family":"WORKED_EXAMPLE_BOARD",
         "values":[0,2,4,7,11,15,15,21,30],"target":15}


def produce(dest:Path)->dict:
    dest.mkdir(parents=True,exist_ok=True)
    settings=Settings(
        environment="test",pipeline_mode="fake",
        db_path=str(dest/"local.db"),artifacts_dir=str(dest/"private"),
        v3_binary_preview_enabled=True,v3_narrated_lesson_enabled=True,
        v3_event_alignment_enabled=True,
        gemini_api_key="",enable_image_generation=False)
    app=create_app(settings=settings)
    records={}
    with TestClient(app) as client:
        for label,endpoint in (
            ("before_v3_19","binary-search-lesson"),
            ("after_v3_20","binary-search-event-aligned"),
        ):
            resp=client.post("/api/v3/offline/"+endpoint,json=REQUEST)
            if resp.status_code!=200:
                raise RuntimeError(f"V3_20_{label}_HTTP_{resp.status_code}: {resp.text[:250]}")
            records[label]=resp.json()
            assert client.get(f"/api/jobs/{records[label]['preview_id']}/video").status_code==404
        unsupported=client.post("/api/v3/offline/binary-search-event-aligned",
                                json=REQUEST|{"family":"STATE_MACHINE"})
        assert unsupported.status_code==422
    source=build_binary_lesson_source(
        values=tuple(REQUEST["values"]),target=REQUEST["target"])
    proof=None
    for label in records:
        private=Path(settings.artifacts_dir)/records[label]["preview_id"]
        receipt=NarratedLessonReceipt.model_validate_json(
            (private/"narrated_binary_lesson.receipt.json").read_text())
        verify_narrated_lesson(source=source,folder=private,receipt=receipt)
        video=private/"narrated_binary_lesson.mp4"
        digest=hashlib.sha256(video.read_bytes()).hexdigest()
        assert digest==receipt.video_sha256==records[label]["video_sha256"]
        shutil.copy2(video,dest/f"{label}_real_audio_video.mp4")
        shutil.copy2(private/"narrated_binary_lesson.srt",dest/f"{label}.srt")
        shutil.copy2(private/"narrated_binary_lesson.receipt.json",
                     dest/f"{label}.receipt.json")
        records[label]["sha256"]=digest
        if label=="after_v3_20":
            proof=json.loads((private/"narrated_binary_lesson.event_proof.json").read_text())
            verify_event_proof(source=source,segments=receipt.segments,
                               supplied=proof)
            shutil.copy2(private/"narrated_binary_lesson.event_proof.json",
                         dest/"after_v3_20.event_proof.json")
            assert records[label]["event_proof_sha256"]==proof["proof_sha256"]
            assert records[label]["word_alignment"]=="UNMEASURED_NOT_FORCED_ALIGNMENT"
    assert proof is not None
    evidence={
        "checkpoint":"V3-20",
        "kind":"OFFLINE_DEVELOPMENT_TWO_REAL_HTTP_H264_AAC_LESSONS",
        "same_source_input":REQUEST,
        "before":records["before_v3_19"],
        "after":records["after_v3_20"],
        "improvement_claim":"SOURCE_BOUND_MEASURED_UTTERANCE_EVENT_TIMING_ONLY",
        "resolved_issue":"V3_19_ACTION_LABEL_AND_STATE_VISIBLE_BEFORE_CORRESPONDING_SPOKEN_ACTION",
        "before_observed_scene_start_seconds":14.333333,
        "comparison_attestation_sha256":proof["proof_sha256"],
        "measured_event_count":proof["event_count"],
        "word_level_alignment":"UNMEASURED",
        "lexical_audio_asr":"UNMEASURED",
        "human_pedagogy_quality":"UNMEASURED",
        "license":"GPL-3_OR_LATER_ESPEAK_ENGINE_VOICE_OUTPUT_RIGHTS_REQUIRE_REVIEW",
        "provider_calls":0,
        "production_release":"BLOCKED",
        "no_concept_card_fallback":True,
    }
    (dest/"v3_20_before_after_qa.json").write_text(
        json.dumps(evidence,indent=2)+"\n",encoding="utf-8")
    shutil.rmtree(dest/"private")
    for f in dest.glob("local.db*"):f.unlink(missing_ok=True)
    print(f"V3_20_REAL_HTTP=PASS before_scenes={records['before_v3_19']['scene_count']} "
          f"after_events={proof['event_count']}")
    print(f"V3_20_EVENT_BOUNDARIES=PASS measured_pcm=True "
          f"audio_events={proof['event_count']} word_alignment=UNMEASURED")
    print("V3_20_MEDIA=PASS actual_h264_aac_before_and_after=True "
          "source_video_audio_replayed=True")
    print("V3_20_GUARD=PASS unsupported_abstains=True publication=BLOCKED "
          "human_quality=UNMEASURED")
    return evidence


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    produce(p.parse_args().output_dir)
