#!/usr/bin/env python3
"""V3-95 CI wiring smoke: new user text→mock HTTP→strict host→real MP4.

EXPLICITLY not evidence of a new real GPT API call or free-form topic support.
Replaces only network transport in tests; native video/audio are real ffmpeg/eSpeak.
"""
from __future__ import annotations
import argparse,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from learnflow_v3.v392_compact_authoring import pilot_case
from learnflow_v3.v395_prompt_to_video import run_dev_preview
from learnflow_v3.v364_native_array_compiler import probe,file_sha,decode_movie

class Response(io.BytesIO):
    status=200
def fake_sender(payload):
    def send(req,timeout=None):
        return Response(json.dumps(payload).encode("utf-8"))
    return send

def supported_fixture():
    p=pilot_case()
    p["motion_method"]="smooth_morph"
    return p

def run(out):
    query="Can a grid of squares measuring 3x4 be rotated to 4x3 and preserve all 12 pieces?"
    model="openai/gpt-6-luna"
    catalog={"data":[{"id":model,
      "pricing":{"prompt":"0.0000001","completion":"0.0000005"},
      "supported_parameters":["response_format","max_completion_tokens"]}]}
    account={"data":{"limit_remaining":1,"is_management_key":False}}
    fake={"id":"v395_offline_mocked_inference_this_is_not_gpt",
          "model":model,"usage":{"cost":"0.0004","prompt_tokens":600,"completion_tokens":450},
          "choices":[{"finish_reason":"stop",
                      "message":{"content":json.dumps(supported_fixture())}}]}
    r=run_dev_preview(query=query,output=out,key="testkey"+"x"*24,
        catalog_sender=fake_sender(catalog),
        key_sender=fake_sender(account),
        post_sender=fake_sender(fake),
        do_native=True)
    assert r["result"]=="MOCK_TO_NATIVE_TECHNICAL_PASS_NOT_REAL_AI",r
    assert r["storyboard_origin"]=="MOCK_SENDER_UNATTRIBUTED"
    assert r["provider_posts"]==1 and r["retry_count"]==0
    assert r["final_video"]=="VERIFIED_PRIVATE_DEVELOPER_PREVIEW"
    assert r["timeline_geometry"]["geometry_pass"] is True
    assert r["timeline_geometry"]["timeline_frames_audited"]==r["native_video_frames"]
    native_receipt=json.loads((out/"native_pair/v364_native_receipt.json").read_text())
    assert native_receipt["matched_video_frame_counts"] is True
    for movie in native_receipt["native_mp4s"]:
        src=out/"native_pair"/movie["name"]
        assert src.is_file() and file_sha(src)==movie["sha256"]
        assert probe(src)==movie["native_frames"]
        decode_movie(src)
    print("V395_DYNAMIC_PROMPT_TO_MOCK_JSON_TO_REAL_FFMPEG_NATIVE_PASS_NOT_NEW_GPT",flush=True)
    return r

if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--output",type=Path,required=True)
    x=cli.parse_args()
    run(x.output)
