"""V3 production motion contracts: offline, topic-neutral, no paid calls."""
from __future__ import annotations

import asyncio
import json
import math
import shutil
import subprocess

import pytest
from pydantic import ValidationError

from app.domain.enums import VisualIntent
from app.domain.lesson import FunctionGraphSpec, ScenePlan, LessonPlan
from app.domain.timeline import ResolvedSceneTiming
from app.planning.prompts import build_lesson_plan_prompt
from app.domain.lesson import LearningRequest
from app.rendering.function_graph import FunctionGraphRenderer, value_and_slope
from app.rendering.router import RendererRouter


def graph_spec(*, function="polynomial", coefficients=None, focus_x=0.5,
               motion_kind="secant_to_tangent"):
    if coefficients is None:
        coefficients = [0, 0, 1]
    return FunctionGraphSpec(function=function, coefficients=coefficients,
                             focus_x=focus_x, motion_kind=motion_kind)


def scene_from(spec, *, sid="s01_generic_graph"):
    return ScenePlan(
        scene_id=sid, title="Độ dốc tức thời của đường cong",
        concept="Phép biến đổi trực quan", narration="Độ dốc dây cung tiến đến độ dốc tiếp tuyến.",
        key_points=["Dây cung", "Tiếp tuyến"], visual_intent=VisualIntent.FUNCTION_GRAPH,
        visual_spec=spec,
    )


def timing_for(scene_id, seconds=2.0):
    return ResolvedSceneTiming(scene_id=scene_id,
        raw_audio_path="/unused.raw.mp3", padded_audio_path="/unused.padded.wav",
        audio_duration_seconds=seconds-.25,
        render_duration_seconds=seconds, start_seconds=0.0, end_seconds=seconds)


@pytest.mark.parametrize("spec,x,expected", [
    (graph_spec(), 2.0, (4.0, 4.0)),
    (graph_spec(coefficients=[1,-2,3]), 1.0, (2.0, 4.0)),
    (graph_spec(function="sine", coefficients=[]), 0.0, (0.0,1.0)),
    (graph_spec(function="cosine", coefficients=[]), 0.0, (1.0,0.0)),
    (graph_spec(function="exponential", coefficients=[]), 0.0, (1.0,1.0)),
])
def test_analytic_host_computations(spec,x,expected):
    got=value_and_slope(spec,x)
    assert math.isclose(got[0],expected[0],abs_tol=1e-8)
    assert math.isclose(got[1],expected[1],abs_tol=1e-8)


@pytest.mark.parametrize("bad",[
    dict(function="polynomial",coefficients=[],focus_x=0,motion_kind="secant_to_tangent"),
    dict(function="polynomial",coefficients=[0, float("nan")],focus_x=0,motion_kind="slope_scan"),
    dict(function="polynomial",coefficients=[0, 6],focus_x=0,motion_kind="slope_scan"),
    dict(function="polynomial",coefficients=[0, 1],focus_x=12,motion_kind="slope_scan"),
    dict(function="evil_expression",coefficients=[0, 1],focus_x=0,motion_kind="slope_scan"),
])
def test_model_rejects_unsafe_or_unverifiable_visuals(bad):
    with pytest.raises(ValidationError):
        FunctionGraphSpec.model_validate(bad)


def test_model_route_and_openrouter_strict_schema():
    from app.providers.llm.openrouter_paid import build_strict_lesson_plan_schema
    spec = graph_spec()
    scene=scene_from(spec)
    assert isinstance(RendererRouter().get_renderer(VisualIntent.FUNCTION_GRAPH),FunctionGraphRenderer)
    with pytest.raises(ValidationError):
        ScenePlan.model_validate({**scene.model_dump(), "visual_intent":"comparison"})
    schema=build_strict_lesson_plan_schema()
    branch=schema["$defs"]["ScenePlan"]["properties"]["visual_spec"]["anyOf"]
    assert len(branch)==7
    assert any(x.get("$ref","").endswith("/FunctionGraphSpec") for x in branch)
    prompt=build_lesson_plan_prompt(LearningRequest(topic="Tốc độ thay đổi là gì?"))
    assert "function_graph" in prompt and "secant_to_tangent" in prompt
    assert "not narrated slides" in prompt


def test_motion_frames_are_semantically_different():
    scene=scene_from(graph_spec())
    renderer=FunctionGraphRenderer(width=640,height=360,fps=12)
    first=renderer._frame(scene,scene.visual_spec,0.05)
    secant=renderer._frame(scene,scene.visual_spec,0.45)
    tangent=renderer._frame(scene,scene.visual_spec,0.98)
    assert first.tobytes()!=secant.tobytes()
    assert secant.tobytes()!=tangent.tobytes()
    # Meaningful differences in the plot area, not only subtitle changes.
    from PIL import ImageChops
    delta=ImageChops.difference(secant.crop((40,70,470,278)),
                                tangent.crop((40,70,470,278)))
    assert delta.getbbox() is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("spec", [
    graph_spec(),
    graph_spec(function="sine",coefficients=[],motion_kind="slope_scan"),
])
async def test_production_720p_native_graph_motion(tmp_path,spec):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("Full-video preflight runs in production Docker image")
    scene=scene_from(spec)
    timing=timing_for(scene.scene_id)
    path=tmp_path/"semantic_motion.mp4"
    result=await FunctionGraphRenderer().render(scene,timing,path)
    assert path.is_file() and path.stat().st_size>1000
    assert result.width==1280 and result.height==720
    probe=subprocess.run([
        "ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path),
    ],capture_output=True,text=True,check=True,timeout=20)
    data=json.loads(probe.stdout)
    v=next(s for s in data["streams"] if s["codec_type"]=="video")
    assert v["codec_name"]=="h264"
    assert v["pix_fmt"]=="yuv420p"
    assert v["width"]==1280 and v["height"]==720
    assert abs(float(data["format"]["duration"])-2)<.09
    # Extract distinct decoded frames; V2 cards stay static between state cuts,
    # while the math renderer must demonstrably change during each interval.
    raw=subprocess.run([
        "ffmpeg","-v","error","-i",str(path),"-vf","fps=2,scale=320:180",
        "-f","rawvideo","-pix_fmt","gray","-",
    ],capture_output=True,check=True,timeout=30).stdout
    frames=[raw[i:i+320*180] for i in range(0,len(raw),320*180)]
    assert len(set(frames))>=3
