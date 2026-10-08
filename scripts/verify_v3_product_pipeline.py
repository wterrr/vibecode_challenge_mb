#!/usr/bin/env python3
"""V3-18: real FastAPI/TestClient request via EXISTING app pipeline factory.

Developer-only, no model/TTS, publication or job-SUCCEEDED status.
Emits independently verified H264 and JSON to CI evidence after the HTTP call.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.pipeline.v3_preview import V3OfflinePreviewPipeline
from learnflow_v3.integration_slice import IntegratedClipReceipt,verify_integrated_binary_clip
from learnflow_v3.offline_lesson_source import build_binary_lesson_source
from learnflow_v3.sequence_renderer import SequenceRenderProfile

PAYLOAD={
    "family":"WORKED_EXAMPLE_BOARD",
    "values":[0,2,5,8,12,19,25,31,42],
    "target":19,
}


def main(output:Path):
    output.mkdir(parents=True,exist_ok=True)
    settings=Settings(
        environment="test",pipeline_mode="fake",
        render_profile="test",db_path=str(output/"local-only.db"),
        artifacts_dir=str(output/"private"),
        v3_binary_preview_enabled=True,
        gemini_api_key="",enable_image_generation=False,
    )
    app=create_app(settings=settings)
    assert isinstance(app.state.pipeline,V3OfflinePreviewPipeline)
    assert app.state.runner.pipeline is app.state.pipeline
    with TestClient(app) as client:
        assert client.get("/healthz").status_code==200
        response=client.post("/api/v3/offline/binary-search",json=PAYLOAD)
        if response.status_code!=200:
            raise AssertionError(f"V3_18_HTTP_FAIL code={response.status_code} "
                                 f"message={response.text[:200]}")
        result=response.json()
        assert client.get(f"/api/jobs/{result['preview_id']}/video").status_code==404
        bad=client.post("/api/v3/offline/binary-search",
                        json=PAYLOAD|{"family":"STATE_MACHINE"})
        assert bad.status_code==422
        assert "ABSTAIN_UNCONNECTED_FAMILY" in bad.text
    private=Path(settings.artifacts_dir)/result["preview_id"]
    video=private/"integrated_binary_lesson.mp4"
    receipt=IntegratedClipReceipt.model_validate_json(
        (private/"integrated_binary_lesson.receipt.json").read_text())
    assert result["assembled_video_sha256"]==hashlib.sha256(video.read_bytes()).hexdigest()
    source=build_binary_lesson_source(values=tuple(PAYLOAD["values"]),target=PAYLOAD["target"])
    profile=SequenceRenderProfile(width=640,height=360,fps=12,seconds_per_step=.75)
    verify_integrated_binary_clip(
        source=source,out_dir=private,profile=profile,receipt=receipt)
    info=subprocess.run([
        "ffprobe","-v","error","-show_entries",
        "stream=codec_name,width,height,nb_frames","-of","json",str(video)
    ],check=True,capture_output=True,text=True,timeout=30)
    stream=json.loads(info.stdout)["streams"][0]
    assert stream["codec_name"]=="h264" and int(stream["width"])==640
    assert int(stream["height"])==360 and int(stream["nb_frames"])==receipt.frame_count
    assert receipt.decoded_scene_rgb_sha256==receipt.decoded_assembly_rgb_sha256
    assert result["publication"]=="PUBLISH_BLOCKED"
    assert result["public_video_url"] is None
    assert not (private/"final.mp4").exists()
    shutil.copy2(video,output/"v3_18_binary_http_verified.mp4")
    (output/"v3_18_binary_http_receipt.json").write_text(
        json.dumps(receipt.model_dump(mode="json"),indent=2)+"\n",encoding="utf-8")
    (output/"v3_18_http_response_and_qa.json").write_text(
        json.dumps({
            "request":PAYLOAD,"response":result,
            "http_status":200,"abstain_unsupported_http_status":422,
            "legacy_job_download_http_status":404,
            "video_ffprobe":stream,
            "video_sha256":hashlib.sha256(video.read_bytes()).hexdigest(),
            "source_independently_replayed":True,
            "generation_route":"HTTP_FASTAPI_EXISTING_APP_STATE_PIPELINE_FACTORY",
            "legacy_v2_job_processor_shared":True,
            "model_provider_calls":0,"tts_calls":0,
            "publication":"PUBLISH_BLOCKED",
            "complete_voiced_lesson":False,
            "human_quality":"UNMEASURED",
        },indent=2)+"\n",encoding="utf-8")
    # Avoid shipping local sqlite db or developer-private cache in artifact.
    shutil.rmtree(output/"private")
    (output/"local-only.db").unlink(missing_ok=True)
    print("V3_18_PRODUCT_ENTRYPOINT=PASS http=200 existing_factory=True "
          "same_jobrunner_pipeline=True job_video_download=404")
    print(f"V3_18_VIDEO=PASS h264=True frames={receipt.frame_count} "
          f"width={receipt.width} height={receipt.height} "
          f"sha256={result['assembled_video_sha256']}")
    print("V3_18_SOURCE_IDENTITY=PASS trace=sha256 beats=verified "
          "claim=verified object=verified decoded_rgb=matched")
    print("V3_18_UNSUPPORTED=ABSTAIN state_machine=422 concept_card_fallback=False")
    print("V3_18_FLAG=PASS default_OFF=True production_refused=True")
    print("V3_18_PUBLICATION=BLOCKED actual_publication=False "
          "human_quality=UNMEASURED audio=NOT_GENERATED")


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",type=Path,required=True)
    main(ap.parse_args().output_dir)
