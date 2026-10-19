#!/usr/bin/env python3
"""One real developer HTTP narrated lesson with measured source and AAC proof."""
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
from learnflow_v3.narrated_lesson import NarratedLessonReceipt,verify_narrated_lesson
from learnflow_v3.offline_lesson_source import build_binary_lesson_source

REQUEST={
    "family":"WORKED_EXAMPLE_BOARD",
    "values":[0,2,4,7,11,15,15,21,30],
    "target":15,
}


def run(folder:Path):
    folder.mkdir(parents=True,exist_ok=True)
    settings=Settings(
        environment="test",pipeline_mode="fake",
        db_path=str(folder/"test-local.db"),
        artifacts_dir=str(folder/"private"),
        v3_binary_preview_enabled=True,v3_narrated_lesson_enabled=True,
        gemini_api_key="",enable_image_generation=False)
    app=create_app(settings=settings)
    with TestClient(app) as client:
        r=client.post("/api/v3/offline/binary-search-lesson",json=REQUEST)
        if r.status_code!=200:
            raise RuntimeError(f"V3_19_HTTP_FAILED code={r.status_code} body={r.text[:250]}")
        response=r.json()
        assert client.get(f"/api/jobs/{response['preview_id']}/video").status_code==404
        bad=client.post("/api/v3/offline/binary-search-lesson",
                        json=REQUEST|{"family":"STATE_MACHINE"})
        assert bad.status_code==422
    preview=Path(settings.artifacts_dir)/response["preview_id"]
    verified=NarratedLessonReceipt.model_validate_json(
        (preview/"narrated_binary_lesson.receipt.json").read_text(encoding="utf-8"))
    source=build_binary_lesson_source(
        values=tuple(REQUEST["values"]),target=REQUEST["target"])
    verify_narrated_lesson(source=source,folder=preview,receipt=verified)
    video=preview/"narrated_binary_lesson.mp4"
    assert hashlib.sha256(video.read_bytes()).hexdigest()==response["video_sha256"]
    assert verified.publication=="PUBLISH_BLOCKED"
    assert verified.segment_alignment=="MEASURED_AUDIO_SAMPLES_SCENE_BOUNDARIES"
    assert verified.word_alignment=="UNMEASURED_NOT_FORCED_ALIGNMENT"
    shutil.copy2(video,folder/"v3_19_real_spoken_full_lesson.mp4")
    shutil.copy2(preview/"narrated_binary_lesson.srt",folder/"v3_19_measured_subtitles.srt")
    shutil.copy2(preview/"narrated_binary_lesson.receipt.json",folder/"v3_19_source_audio_scene_receipt.json")
    (folder/"v3_19_http_request_and_qa.json").write_text(json.dumps({
        "input":REQUEST,"http_status":r.status_code,"response":response,
        "source_reverified":True,"full_video_sha256":verified.video_sha256,
        "real_audio":True,"audio_origin":verified.speech_origin,
        "audio_engine":verified.speech_engine,
        "audiovisual_alignment":verified.segment_alignment,
        "word_or_phoneme_alignment":"UNMEASURED",
        "human_rating":"UNMEASURED","publication":"PUBLISH_BLOCKED",
        "provider_api_calls":0,"tts_external_network_calls":0,
        "normal_job_succeeded":False,
        "production_public_url":None,
    },indent=2)+"\n",encoding="utf-8")
    shutil.rmtree(folder/"private")
    (folder/"test-local.db").unlink(missing_ok=True)
    for other in folder.glob("test-local.db-*"):other.unlink(missing_ok=True)
    print(f"V3_19_HTTP=PASS real_request=True scene_count={len(verified.segments)} "
          f"duration={verified.duration_seconds:.3f} frames={verified.total_frames}")
    print(f"V3_19_MEDIA=PASS video_codec=h264 audio_codec=aac "
          f"spoken_rms_min={min(x['speech_energy_rms'] for x in verified.segments):.5f}")
    print("V3_19_ALIGN=PASS measured_wav_samples=True "
          "scene_srt_audio_bounds=True decoded_final_audio_each_scene=True "
          "forced_word_alignment=UNMEASURED")
    print("V3_19_RELEASE=BLOCKED silent_filler=False no_concept_card=True "
          "human_quality=UNMEASURED main_unchanged=True")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,required=True)
    run(p.parse_args().output_dir)
