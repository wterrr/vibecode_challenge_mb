"""Bounded Newtonian host physics and real H264 animation acceptance, no paid calls."""
from __future__ import annotations

import asyncio
import json
import math
import shutil
import subprocess

import pytest
from pydantic import ValidationError

from app.domain.enums import VisualIntent
from app.domain.lesson import (
    CentralForceMotionSpec, ScenePlan, LearningRequest,
)
from app.domain.timeline import ResolvedSceneTiming
from app.planning.prompts import build_lesson_plan_prompt
from app.planning.visual_director import (
    required_capability, visual_teaching_errors,
)
from app.planning.visual_tools import execute_visual_tool, tool_catalog
from app.rendering.central_force_motion import (
    CentralForceMotionRenderer, orbital_states, energy, angular_momentum,
    motion_at,
)
from app.rendering.router import RendererRouter
from app.pipeline.motion_quality import SEMANTIC_MOTION_INTENTS, decoded_motion_delta


def spec(kind="bound_orbit", eccentricity=.2):
    return CentralForceMotionSpec(motion_kind=kind,eccentricity=eccentricity)


def scene(kind="bound_orbit", name="s01_orbit", eccentricity=.2):
    return ScenePlan(
        scene_id=name,
        title="Vận tốc tiếp tuyến và lực hút hướng tâm",
        concept="Một vật thể có vận tốc ngang sẽ bị trọng lực làm đổi hướng",
        narration="Nếu không có lực hút vật thể đi thẳng. Có lực hút, vận tốc đổi hướng dần.",
        key_points=["Vận tốc tiếp tuyến","Lực hấp dẫn hướng tâm"],
        visual_intent=VisualIntent.CENTRAL_FORCE_MOTION,
        visual_spec=spec(kind,eccentricity),
    )


def timing(seconds=2.0):
    return ResolvedSceneTiming(
        scene_id="s01_orbit",raw_audio_path="/unused.mp3",
        padded_audio_path="/unused.wav",
        audio_duration_seconds=seconds-.15,
        render_duration_seconds=seconds,
        start_seconds=0,end_seconds=seconds,
    )


@pytest.mark.parametrize("eccentricity", [0.,.1,.25,.45])
def test_gravity_host_oracle_conserves_energy_momentum_and_closes(eccentricity):
    states=orbital_states(spec(eccentricity=eccentricity))
    assert len(states)==1441
    assert states[0].x==1
    assert abs(energy(states[0])+.5*(1-eccentricity))<1e-8
    assert abs(angular_momentum(states[0])-math.sqrt(1+eccentricity))<1e-8
    assert abs(energy(states[700])-energy(states[0]))<1e-3
    assert abs(angular_momentum(states[700])-angular_momentum(states[0]))<1e-3
    assert math.dist((states[0].x,states[0].y),(states[-1].x,states[-1].y))<.025


def test_inertia_vs_gravity_difference_is_geometry_not_text():
    states=orbital_states(spec())
    a=motion_at(states,.8,"inertia_only")
    b=motion_at(states,.8,"gravity_deflection")
    assert abs(a.x-1)<1e-10
    assert abs(b.x-1)>.1
    assert math.dist((a.x,a.y),(b.x,b.y))>.15
    assert math.isclose(a.vx,0,abs_tol=1e-10)


@pytest.mark.parametrize("kind",["inertia_only","gravity_deflection","bound_orbit"])
def test_all_physics_modes_host_and_agent_probe(kind):
    receipt=execute_visual_tool(
        "probe_central_force_motion",
        json.dumps({"motion_kind":kind,"eccentricity":.3}),
    )
    assert receipt["verified"] is True
    assert receipt["motion_kind"]==kind
    assert receipt["host_orbit_closed"] is True
    assert receipt["host_energy"]<0
    assert receipt["host_angular_momentum"]>0


@pytest.mark.parametrize("params",[
    {"motion_kind":"teleport","eccentricity":.2},
    {"motion_kind":"bound_orbit","eccentricity":.99},
    {"motion_kind":"bound_orbit","eccentricity":-1},
    {"motion_kind":"bound_orbit","eccentricity":float("nan")},
    {"motion_kind":"bound_orbit","eccentricity":"unknown"},
])
def test_reject_unverified_or_unsafe_physical_inputs(params):
    with pytest.raises(ValidationError):
        CentralForceMotionSpec.model_validate(params)


def test_unknown_physics_arguments_fail_closed():
    with pytest.raises(ValueError,match="visual_tool_unexpected_arguments"):
        execute_visual_tool("probe_central_force_motion",json.dumps({
            "motion_kind":"bound_orbit","eccentricity":.2,
            "python":"exec('unsafe')",
        }))


def test_strict_schema_dispatch_and_topic_capability():
    from app.providers.llm.openrouter_paid import build_strict_lesson_plan_schema
    schema=build_strict_lesson_plan_schema()
    branches=schema["$defs"]["ScenePlan"]["properties"]["visual_spec"]["anyOf"]
    assert len(branches)==7
    assert any(x.get("$ref","").endswith("/CentralForceMotionSpec") for x in branches)
    assert isinstance(RendererRouter().get_renderer(VisualIntent.CENTRAL_FORCE_MOTION),
                      CentralForceMotionRenderer)
    assert VisualIntent.CENTRAL_FORCE_MOTION in SEMANTIC_MOTION_INTENTS
    for topic in ("Vì sao các hành tinh có quỹ đạo?",
                  "Why do artificial satellites orbit Earth?",
                  "Chuyển động quanh Mặt Trời"):
        assert required_capability(topic).intent==VisualIntent.CENTRAL_FORCE_MOTION
    assert required_capability("Quang hợp diễn ra thế nào?") is None
    prompt=build_lesson_plan_prompt(LearningRequest(topic="Vì sao các hành tinh có quỹ đạo?"))
    assert "central_force_motion" in prompt
    assert "inertia_only / gravity_deflection / bound_orbit" in prompt
    assert "At least half" in prompt
    assert any(x["intent"]=="central_force_motion" for x in tool_catalog()["scene_tools"])


def test_reject_exact_user_slide_only_plan_and_require_causal_demonstration():
    from app.demo.lesson_plans import DEMO_PHOTOSYNTHESIS_PLAN
    demo=DEMO_PHOTOSYNTHESIS_PLAN
    topic="Vì sao các hành tinh có quỹ đạo?"
    slide_plan=demo.model_copy(update={"topic":topic})
    issues=visual_teaching_errors(topic,slide_plan)
    assert "insufficient_semantic_motion" in {code for code,_ in issues}
    assert "missing_physical_causal_sequence" in {code for code,_ in issues}
    scenes=[
        scene("inertia_only","s01_inertia"),
        scene("gravity_deflection","s02_deflect"),
        scene("bound_orbit","s03_orbit"),
        demo.scenes[0].model_copy(update={"scene_id":"s04_recap"}),
        demo.scenes[1].model_copy(update={"scene_id":"s05_summary"}),
    ]
    plan=demo.model_copy(update={"topic":topic,"scenes":scenes})
    assert not visual_teaching_errors(topic,plan)
    plan_missing=plan.model_copy(deep=True)
    plan_missing.scenes[2].visual_spec.motion_kind="inertia_only"
    assert "missing_physical_causal_sequence" in {
        code for code,_ in visual_teaching_errors(topic,plan_missing)
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("kind",["inertia_only","gravity_deflection","bound_orbit"])
async def test_native_physics_mp4_h264_and_decoded_motion(tmp_path,kind):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg required in deployment CI")
    renderer=CentralForceMotionRenderer(width=640,height=360,fps=12)
    output=tmp_path/(kind+".mp4")
    plan=scene(kind)
    await renderer.render(plan,timing(2),output)
    assert output.is_file() and output.stat().st_size>1000
    cmd=["ffprobe","-v","error","-select_streams","v:0",
         "-show_entries","stream=codec_name,pix_fmt,width,height,duration",
         "-of","json",str(output)]
    info=json.loads(subprocess.run(cmd,check=True,capture_output=True,text=True,
                                   timeout=25).stdout)
    stream=info["streams"][0]
    assert stream["codec_name"]=="h264"
    assert stream["pix_fmt"]=="yuv420p"
    assert stream["width"]==640 and stream["height"]==360
    assert decoded_motion_delta(output,2.0)>=.7
