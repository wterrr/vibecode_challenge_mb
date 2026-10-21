"""No-key Code2Video worker boundaries and actual normalized external MP4.

The optional source-worker image is a separate build. Standard LearnFlow Docker
CI never runs GPT or AI-authored Python, but executes an actual H264 roundtrip
via mocked worker transport and enforces host policy before rendering.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import httpx
import pytest

from app.config import Settings
from app.domain.enums import VisualIntent
from app.domain.lesson import Code2VideoSceneSpec, ScenePlan
from app.domain.timeline import ResolvedSceneTiming
from app.demo.lesson_plans import DEMO_PHOTOSYNTHESIS_PLAN
from app.planning.prompts import build_lesson_plan_prompt
from app.planning.validator import validate_lesson_plan
from app.domain.lesson import LearningRequest
from app.planning.visual_tools import execute_visual_tool,visual_tool_definitions,tool_catalog
from app.rendering.code2video_scene import (
    Code2VideoSceneRenderer,validate_worker_endpoint,
)
from app.rendering.router import RendererRouter
from app.pipeline.motion_quality import SEMANTIC_MOTION_INTENTS,decoded_motion_delta


def spec():
    return Code2VideoSceneSpec(
        title="Chuyển động của các hành tinh",
        visual_goal="Minh họa quỹ đạo bằng chuyển động hình học liên tục trên không gian tối.",
    )


def scene(name="s01_creative"):
    return ScenePlan(
        scene_id=name,title="Chuyển động của các hành tinh",
        concept="Lực hút bẻ hướng vận tốc",
        narration="Quan sát hướng của vận tốc và đường đi cong của hành tinh.",
        key_points=["Quỹ đạo liên tục","Vận tốc tiếp tuyến"],
        visual_intent=VisualIntent.CODE2VIDEO_SCENE,
        visual_spec=spec(),
    )


def timing():
    return ResolvedSceneTiming(
        scene_id="s01_creative",raw_audio_path="/unused.mp3",
        padded_audio_path="/unused.wav",
        audio_duration_seconds=1.9,render_duration_seconds=2.0,
        start_seconds=0,end_seconds=2,
    )


def test_agent_discovery_cannot_advertise_worker_without_opt_in():
    assert len(visual_tool_definitions())==4
    assert len(visual_tool_definitions(code2video_enabled=True))==5
    names={x["function"]["name"] for x in visual_tool_definitions()}
    assert "probe_code2video_scene" not in names
    catalog=tool_catalog()
    c=[x for x in catalog["scene_tools"] if x["intent"]=="code2video_scene"]
    assert len(c)==1 and c[0]["available"] is False
    assert {x["intent"] for x in catalog["scene_tools"]}=={
        intent.value for intent in RendererRouter()._registry
    }
    with pytest.raises(ValueError,match="visual_tool_not_registered"):
        execute_visual_tool("probe_code2video_scene",json.dumps({
            "title":spec().title,"visual_goal":spec().visual_goal,
        }))
    receipt=execute_visual_tool("probe_code2video_scene",json.dumps({
        "title":spec().title,"visual_goal":spec().visual_goal,
    }),code2video_enabled=True)
    assert receipt["accepted"] is True
    assert receipt["execution"]=="deferred_to_secretless_manim_worker"
    for args in (
        {"title":"abc","visual_goal":"x"},
        {"title":"abc","visual_goal":"a valid explanation of motion","code":"import os"},
    ):
        with pytest.raises(ValueError):
            execute_visual_tool("probe_code2video_scene",json.dumps(args),
                                code2video_enabled=True)


def test_disabled_fails_before_paid_audio_or_manim_render():
    base=DEMO_PHOTOSYNTHESIS_PLAN
    subject=LearningRequest(topic="Vì sao các hành tinh có quỹ đạo?")
    plan=base.model_copy(update={"scenes":[scene(),base.scenes[1],base.scenes[2]]})
    issues=validate_lesson_plan(subject,plan,code2video_enabled=False)
    assert "code2video_worker_disabled" in [i.code for i in issues]
    issues=validate_lesson_plan(subject,plan,code2video_enabled=True)
    assert "code2video_worker_disabled" not in [i.code for i in issues]
    twice=base.model_copy(update={"scenes":[scene(),scene("s02_creative"),base.scenes[2]]})
    assert "code2video_budget_exceeded" in [
        i.code for i in validate_lesson_plan(subject,twice,code2video_enabled=True)
    ]
    text=build_lesson_plan_prompt(subject,code2video_enabled=False)
    assert "UNAVAILABLE" in text
    assert "AVAILABLE only through a dedicated isolated worker" in build_lesson_plan_prompt(
        subject,code2video_enabled=True,
    )


@pytest.mark.parametrize("url",[
    "http://evil.example","http://192.168.1.1","http://169.254.169.254",
    "https://user:pass@example.com","https://example.com/other",
    "https://example.com?token=foo","file:///tmp/secret",
])
def test_worker_url_refuses_ssrf_and_plaintext_secrets(url):
    with pytest.raises(ValueError):
        validate_worker_endpoint(url,"a"*32)


def test_host_token_redacted_and_external_production_disabled():
    settings=Settings(_env_file=None,code2video_enabled=False,
                      code2video_worker_token="secret-scope-token-123456789")
    assert "secret-scope-token-123456789" not in repr(settings)
    assert VisualIntent.CODE2VIDEO_SCENE in SEMANTIC_MOTION_INTENTS


def test_secretless_worker_preflight_forbids_sensitive_python():
    file=Path(__file__).resolve().parents[1]/"integrations/code2video/render_worker.py"
    module_spec=importlib.util.spec_from_file_location("c2v_test_renderer",file)
    module=importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    valid="from manim import *\nclass LearnflowScene(Scene):\n    def construct(self):\n        self.play(Create(Circle()))\n"
    module.preflight(valid)
    for bad in (
        "from manim import *\nimport os\nclass LearnflowScene(Scene):\n    pass",
        "from manim import *\nclass LearnflowScene(Scene):\n    def construct(self):\n        exec('print(2)')",
    ):
        with pytest.raises(ValueError):
            module.preflight(bad)


@pytest.mark.asyncio
async def test_end_to_end_worker_mp4_to_native_learnflow_h264_no_paid_api(tmp_path,monkeypatch):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("native H264 test in Docker CI")
    upstream=tmp_path/"sample.mp4"
    subprocess.run([
        "ffmpeg","-nostdin","-v","error","-y",
        "-f","lavfi","-i","testsrc2=size=640x360:rate=12:duration=2",
        "-c:v","libx264","-pix_fmt","yuv420p",str(upstream),
    ],check=True,timeout=25)
    original=upstream.read_bytes()
    outbound=[]
    class FakeResponse:
        status_code=200
        headers={"content-type":"video/mp4"}
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def aiter_bytes(self):
            for i in range(0,len(original),7000):
                yield original[i:i+7000]
    class FakeClient:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        def stream(self,method,url,headers,json):
            outbound.append((method,url,headers,json))
            return FakeResponse()
    monkeypatch.setattr(httpx,"AsyncClient",FakeClient)
    dest=tmp_path/"scene.mp4"
    renderer=Code2VideoSceneRenderer(
        worker_url="http://code2video-planner:8765",
        token="a"*32,width=640,height=360,fps=12,
    )
    result=await renderer.render(scene(),timing(),dest)
    assert result.width==640 and result.height==360
    assert dest.exists() and dest.stat().st_size>1024
    assert len(outbound)==1
    assert outbound[0][1]=="http://code2video-planner:8765/render"
    assert outbound[0][2]["Authorization"]=="Bearer "+"a"*32
    assert set(outbound[0][3])=={
        "title","narration","visual_goal","duration_seconds","language"
    }
    assert "code" not in outbound[0][3]
    assert decoded_motion_delta(dest,2)>=.7
    probe=subprocess.run([
        "ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=codec_name,width,height,duration",
        "-of","json",str(dest),
    ],check=True,capture_output=True,text=True,timeout=25)
    stream=json.loads(probe.stdout)["streams"][0]
    assert stream["codec_name"]=="h264"
    assert stream["width"]==640 and stream["height"]==360
    assert abs(float(stream["duration"])-2)<.1
