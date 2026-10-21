"""No-key production Visual Teaching Director + verified algorithm movie gates."""
from __future__ import annotations

import asyncio
import copy
import json
import shutil
import subprocess

import pytest
from pydantic import ValidationError

from app.domain.enums import VisualIntent
from app.domain.lesson import (
    LearningRequest, LessonPlan, ScenePlan, ArrayTraceSpec, FunctionGraphSpec,
)
from app.domain.timeline import ResolvedSceneTiming, SubtitleCue
from app.planning.prompts import build_lesson_plan_prompt
from app.planning.validator import validate_lesson_plan
from app.planning.visual_director import required_capability
from app.rendering.array_trace import ArrayTraceRenderer, verified_array_trace, beat_boundaries
from app.rendering.router import RendererRouter
from app.pipeline.motion_quality import decoded_motion_delta


def spec(values=None, target=8):
    return ArrayTraceSpec(
        algorithm="binary_search",
        values=values or [1,3,5,7,9,11,13,15,17], target=target,
    )


def scene_for(name="s01_trace", values=None, target=8):
    return ScenePlan(
        scene_id=name, title="Tìm vị trí trong dãy số đã sắp xếp",
        concept="Loại bỏ từng nửa dựa trên so sánh",
        narration="Đầu tiên ta xác định đoạn tìm kiếm. Sau đó so sánh với số ở giữa. Tiếp tục loại bỏ một nửa.",
        key_points=["So sánh tại giữa", "Thu hẹp phạm vi"],
        visual_intent=VisualIntent.ARRAY_TRACE,
        visual_spec=spec(values,target),
    )


def timing(duration=3.0):
    return ResolvedSceneTiming(
        scene_id="s01_trace", raw_audio_path="/no-paid-api.mp3",
        padded_audio_path="/no-paid-api.wav",
        audio_duration_seconds=duration-.25,render_duration_seconds=duration,
        start_seconds=0,end_seconds=duration,
        subtitle_cues=[
            SubtitleCue(start_seconds=0,end_seconds=(duration-.25)/2,text="Nửa đầu."),
            SubtitleCue(start_seconds=(duration-.25)/2,end_seconds=duration-.25,text="Nửa sau."),
        ],
    )


@pytest.mark.parametrize("values,target,expected",[
    ([1,2,3,4,5,6,7],5,4),
    ([1,3,5,7,9,11,13],8,None),
    ([1,2,2,2,2,3,4],2,1),
    ([-9,-5,-2,0,2,5,9],-5,1),
])
def test_independent_v3_oracle_trace_works_for_unseen_arrays(values,target,expected):
    t=verified_array_trace(spec(values,target))
    assert t.result_index==expected
    assert len(t.steps)>=2
    assert t.steps[-1].action==("FOUND" if expected is not None else "NOT_FOUND")


@pytest.mark.parametrize("values,target",[
    ([9,1,2,3,4],3),   # sorted-state error
    ([1,2,3,4],3),     # below visible minimum
    ([1,2,3,4,5]*4,3),# over visible cap
    ([1,2,3,4,False,6],3), # no bool or numeric coercion
    ([1,2,3,4,"5",6],3),
    ([1,2,3,4,1000,1001],3),
    ([1,2,3,4,5,6],True),
])
def test_trace_source_rejects_untrusted_inputs(values,target):
    with pytest.raises(ValidationError):
        spec(values,target)


def test_route_and_strict_paid_schema_have_verified_array():
    from app.providers.llm.openrouter_paid import build_strict_lesson_plan_schema
    from app.rendering.array_trace import ArrayTraceRenderer
    assert isinstance(RendererRouter().get_renderer(VisualIntent.ARRAY_TRACE),ArrayTraceRenderer)
    schema=build_strict_lesson_plan_schema()
    union=schema["$defs"]["ScenePlan"]["properties"]["visual_spec"]["anyOf"]
    assert any(u.get("$ref","").endswith("/ArrayTraceSpec") for u in union)
    assert len(union)==7
    req=LearningRequest(topic="Tìm kiếm nhị phân hoạt động thế nào?")
    prompt=build_lesson_plan_prompt(req)
    assert "array_trace" in prompt and "At least half" in prompt
    assert "NEVER give mid/low/high" in prompt


def test_director_accepts_diverse_examples_and_rejects_slide_dominated():
    from app.demo.lesson_plans import DEMO_PHOTOSYNTHESIS_PLAN
    base=DEMO_PHOTOSYNTHESIS_PLAN
    trace1=scene_for()
    trace2=scene_for("s02_trace",[0,2,4,6,8,10,12,14,16],7)
    third=base.scenes[2]
    plan=base.model_copy(update={
        "topic":"Tìm kiếm nhị phân hoạt động thế nào?",
        "scenes":[trace1,trace2,third],
    })
    req=LearningRequest(topic=plan.topic)
    assert not [e for e in validate_lesson_plan(req,plan,enforce_visual_teaching=True)
                if e.severity=="error"], "Valid two distinct traces should be accepted"
    missing=plan.model_copy(update={"scenes":list(base.scenes)})
    errors=validate_lesson_plan(req,missing,enforce_visual_teaching=True)
    assert "insufficient_semantic_motion" in [e.code for e in errors]
    repeated=plan.model_copy(update={"scenes":[trace1,trace1.model_copy(update={"scene_id":"s02_trace"}),third]})
    errors=validate_lesson_plan(req,repeated,enforce_visual_teaching=True)
    assert "repeated_visual_example" in [e.code for e in errors]
    assert not [e for e in validate_lesson_plan(req,missing,enforce_visual_teaching=False)
                if e.code=="insufficient_semantic_motion"]


def test_derivative_needs_both_motion_kinds_without_topic_hardcoding():
    from app.demo.lesson_plans import DEMO_PHOTOSYNTHESIS_PLAN
    b=DEMO_PHOTOSYNTHESIS_PLAN
    scenes=[]
    for i,kind in enumerate(["secant_to_tangent","slope_scan"],1):
        v=FunctionGraphSpec(function="polynomial",coefficients=[1,0,1],
                            focus_x=0.2,motion_kind=kind)
        scenes.append(b.scenes[i-1].model_copy(update={
            "scene_id":f"s0{i}_math", "visual_intent":VisualIntent.FUNCTION_GRAPH,
            "visual_spec":v}))
    plan=b.model_copy(update={"topic":"Đạo hàm là gì?","scenes":[*scenes,b.scenes[2]]})
    assert required_capability(plan.topic).intent == VisualIntent.FUNCTION_GRAPH
    assert not [code for code,_ in __import__("app.planning.visual_director",
                       fromlist=["visual_teaching_errors"]).visual_teaching_errors(plan.topic,plan)]
    all_secant=plan.model_copy(update={"scenes":[scenes[0],scenes[1].model_copy(update={"visual_spec":scenes[0].visual_spec}),b.scenes[2]]})
    assert "missing_visual_transformation" in [code for code,_ in __import__(
        "app.planning.visual_director",fromlist=["visual_teaching_errors"]
    ).visual_teaching_errors(all_secant.topic,all_secant)]
    assert required_capability("Định luật Newton thứ hai") is None


def test_animation_progress_is_tied_to_measured_scene_audio():
    b=beat_boundaries(timing(),4)
    assert len(b)==5 and b[0]==0 and b[-1]==3
    assert all(x<y for x,y in zip(b,b[1:]))
    assert b[-2] < 2.75


@pytest.mark.asyncio
@pytest.mark.parametrize("array,target",[
    ([1,3,5,7,9,11,13,15,17], 11),
    ([2,4,6,8,10,12,14,16,18], 9),
])
async def test_production_movie_verified_720p_h264_decoded_motion(tmp_path,array,target):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("Native media only in Docker CI")
    s=scene_for(values=array,target=target)
    t=timing()
    path=tmp_path/"scene.mp4"
    result=await ArrayTraceRenderer().render(s,t,path)
    assert result.width==1280 and result.height==720
    assert path.is_file() and path.stat().st_size>1000
    cmd=["ffprobe","-v","error","-select_streams","v:0",
         "-show_entries","stream=codec_name,pix_fmt,width,height,duration",
         "-of","json",str(path)]
    output=json.loads(subprocess.run(cmd,capture_output=True,text=True,
                                     check=True,timeout=25).stdout)
    assert output["streams"][0]["codec_name"]=="h264"
    assert output["streams"][0]["pix_fmt"]=="yuv420p"
    assert float(output["streams"][0]["duration"])>=2.9
    assert decoded_motion_delta(path,t.render_duration_seconds)>=.7


def test_motion_qa_blocks_static_h264(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("Native ffmpeg required")
    static=tmp_path/"static.mp4"
    subprocess.run([
        "ffmpeg","-nostdin","-v","error","-y",
        "-f","lavfi","-i","color=c=black:s=640x360:r=12:d=3",
        "-c:v","libx264","-pix_fmt","yuv420p",str(static),
    ],check=True,timeout=30)
    with pytest.raises(ValueError,match="semantic_motion_frames_static"):
        decoded_motion_delta(static,3.0)
