#!/usr/bin/env python3
"""Run deterministic V2 Core rendering on the three frozen V1 lesson fixtures."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import wave
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.domain.lesson import LessonPlan
from app.domain.timeline import ResolvedSceneTiming
from app.rendering.comparison import ComparisonRenderer
from app.rendering.concept_card import ConceptCardRenderer
from app.rendering.process_diagram import ProcessDiagramRenderer
from learnflow_v2.integration import compile_v1_scene_to_v2
from learnflow_v2.qa import AudioProbe, FrameProbe, QAIssueCode, RenderedSceneProbe, TextElementProbe, analyze_deterministic_qa
from learnflow_v2.render import PillowFFmpegRenderer, assemble_rendered_scenes
from learnflow_v2.transitions import InterSceneTransitionPlan

WIDTH=640; HEIGHT=360; FPS=12; SCENE_DURATION=4.0; TRANSITION_DURATION=0.4
BENCHMARK_ID="v2-core-v1-frozen-fixtures-1.0"
_FATAL_CLIPPING={QAIssueCode.CONTENT_CLIPPING,QAIssueCode.FRAME_OVERFLOW}


def _git_sha() -> str:
    p=subprocess.run(["git","rev-parse","HEAD"],cwd=REPO_ROOT,capture_output=True,text=True,check=False)
    s=p.stdout.strip().lower()
    return s if p.returncode==0 and len(s)==40 else "unknown"


def _tone(path:Path,duration:float,rate:int=48000)->Path:
    frames=int(round(duration*rate))
    with wave.open(str(path),"wb") as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate)
        for i in range(frames):
            sample=int(2600*math.sin(2*math.pi*220*i/rate))
            wav.writeframesraw(sample.to_bytes(2,"little",signed=True))
    return path


def _probe_media(path:Path)->dict[str,Any]:
    p=subprocess.run(
        ["ffprobe","-v","error","-show_entries","stream=codec_type,codec_name,width,height:format=duration","-of","json",str(path)],
        capture_output=True,text=True,check=False,timeout=30,
    )
    if p.returncode!=0:raise RuntimeError(f"ffprobe failed: {p.stderr[-300:]}")
    return json.loads(p.stdout)


def _v2_probe(rendered)->RenderedSceneProbe:
    if not rendered.has_audio or rendered.audio_duration is None:
        raise RuntimeError("Core benchmark scene must contain deterministic audio")
    return RenderedSceneProbe(
        scene_id=rendered.scene_id,
        expected_duration=rendered.expected_duration,
        rendered_duration=rendered.rendered_duration,
        text_elements=tuple(TextElementProbe(element_id=x.element_id,font_size_px=x.font_size_px,alpha=x.alpha) for x in rendered.text_evidence),
        visual_elements=(),assets=(),
        frames=tuple(FrameProbe(timestamp=x.timestamp,mean_luma=x.mean_luma,non_black_fraction=x.non_black_fraction,expected_blank=False) for x in rendered.sampled_frames),
        audio=AudioProbe(duration=rendered.audio_duration,rms_windows=(0.05,)*10,expected_audio=True),
        subtitles=(),
    )


def _transition(left,right,index:int)->InterSceneTransitionPlan:
    return InterSceneTransitionPlan(
        transition_id=f"t{index:02d}_{left.scene_id}__{right.scene_id}",
        from_scene=left.scene_id,to_scene=right.scene_id,duration=TRANSITION_DURATION,
        persistent_objects=(),
        departing_node_ids=tuple(sorted(n.id for n in left.nodes)),
        entering_node_ids=tuple(sorted(n.id for n in right.nodes)),
        unmatched_keys=(),diagnostics=("CORE_BENCHMARK_FADE",),
        metadata={"benchmark_id":BENCHMARK_ID},
    )


def _v1_renderer(scene):
    intent=scene.visual_intent.value
    if intent=="concept_card":return ConceptCardRenderer(width=WIDTH,height=HEIGHT,fps=FPS)
    if intent=="process_diagram":return ProcessDiagramRenderer(width=WIDTH,height=HEIGHT,fps=FPS)
    if intent=="comparison":return ComparisonRenderer(width=WIDTH,height=HEIGHT,fps=FPS)
    raise ValueError(f"unsupported V1 intent {intent}")


async def _v1_static_clean(scene,output:Path):
    timing=ResolvedSceneTiming(
        scene_id=scene.scene_id,raw_audio_path="benchmark.wav",padded_audio_path="benchmark.wav",
        audio_duration_seconds=SCENE_DURATION,render_duration_seconds=SCENE_DURATION,
        start_seconds=0,end_seconds=SCENE_DURATION,subtitle_cues=[],
    )
    result=await _v1_renderer(scene).render(scene,timing,output)
    warnings=tuple(sorted(set(result.warnings)))
    lost=any(w.startswith("Text truncated:") or "omitted due to canvas overflow" in w for w in warnings)
    return not lost,warnings


def _critical_regressions(final_path:Path,scene_count:int,spec:dict[str,Any])->tuple[str,...]:
    issues=[]
    if scene_count!=int(spec["scene_count"]):issues.append("SCENE_COUNT")
    data=_probe_media(final_path);streams=data.get("streams",[])
    video=next((x for x in streams if x.get("codec_type")=="video"),None)
    audio=next((x for x in streams if x.get("codec_type")=="audio"),None)
    if video is None:issues.append("VIDEO_STREAM")
    else:
        if video.get("codec_name")!=spec.get("expected_video_codec","h264"):issues.append("VIDEO_CODEC")
        if int(video.get("width",0))!=int(spec.get("expected_width",WIDTH)):issues.append("WIDTH")
        if int(video.get("height",0))!=int(spec.get("expected_height",HEIGHT)):issues.append("HEIGHT")
    if audio is None:issues.append("AUDIO_STREAM")
    elif audio.get("codec_name")!=spec.get("expected_audio_codec","aac"):issues.append("AUDIO_CODEC")
    duration=float(data.get("format",{}).get("duration",0))
    if not math.isfinite(duration) or duration<=1:issues.append("DURATION")
    if not final_path.is_file() or final_path.stat().st_size<=10000:issues.append("FINAL_ARTIFACT")
    return tuple(sorted(set(issues)))


async def run(output_json:Path|None=None)->dict[str,Any]:
    fixtures=REPO_ROOT/"benchmarks"/"fixtures"/"v1"
    baseline=json.loads((REPO_ROOT/"benchmarks"/"baselines"/"v1"/"baseline.json").read_text(encoding="utf-8"))
    metric=json.loads((REPO_ROOT/"benchmarks"/"core_gate"/"static_quality_metric.json").read_text(encoding="utf-8"))
    if metric.get("metric_id")!="static_text_integrity_scene_rate_v1" or not metric.get("frozen_before_v2_core_benchmark"):
        raise RuntimeError("static-quality metric is not frozen")
    renderer=PillowFFmpegRenderer(fps=FPS)
    total=rendered_ok=reproducible=invalid_motion=clipping=overlap=v1_clean=v2_clean=regressions=0
    lessons=[];started=time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="learnflow_v2_core_bench_") as tmp:
        root=Path(tmp)
        for lesson_key,spec in baseline["lessons"].items():
            plan=LessonPlan.model_validate_json((fixtures/spec["fixture_file"]).read_text(encoding="utf-8"))
            lesson_dir=root/lesson_key;lesson_dir.mkdir(parents=True,exist_ok=True)
            rendered=[];built=[];scene_records=[]
            for scene in plan.scenes:
                total+=1
                try:v1_ok,v1_warnings=await _v1_static_clean(scene,lesson_dir/f"v1_{scene.scene_id}.mp4")
                except Exception as exc:v1_ok=False;v1_warnings=(f"V1_RENDER_ERROR:{type(exc).__name__}",)
                if v1_ok:v1_clean+=1
                try:
                    compiled=compile_v1_scene_to_v2(scene,scene_duration=SCENE_DURATION)
                except Exception as exc:
                    if exc.__class__.__module__.startswith("learnflow_v2.motion"):invalid_motion+=1
                    scene_records.append({"scene_id":scene.scene_id,"status":"COMPILE_FAIL","error":f"{type(exc).__name__}:{exc}","v1_static_clean":v1_ok,"v1_warnings":list(v1_warnings)})
                    continue
                try:
                    audio=_tone(lesson_dir/f"{scene.scene_id}.wav",SCENE_DURATION)
                    first=renderer.render(scene_graph=compiled.scene_graph,layout_graph=compiled.layout_graph,motion=compiled.motion,output_path=lesson_dir/f"v2_{scene.scene_id}.mp4",audio_path=audio)
                    replay=renderer.render(scene_graph=compiled.scene_graph,layout_graph=compiled.layout_graph,motion=compiled.motion,output_path=lesson_dir/f"v2_{scene.scene_id}_replay.mp4")
                    rendered_ok+=1
                    same=first.visual_digest==replay.visual_digest
                    if same:reproducible+=1
                    qa=analyze_deterministic_qa(compiled.layout_graph,_v2_probe(first),expected_node_ids={n.id for n in compiled.scene_graph.nodes})
                    c=sum(1 for issue in qa.issues if issue.code in _FATAL_CLIPPING)
                    o=sum(1 for issue in qa.issues if issue.code==QAIssueCode.BBOX_OVERLAP)
                    clipping+=c;overlap+=o
                    clean=qa.passed and not any(x.truncated for x in first.text_evidence)
                    if clean:v2_clean+=1
                    rendered.append(first);built.append(compiled)
                    scene_records.append({
                        "scene_id":scene.scene_id,"status":"PASS" if qa.passed else "QA_FAIL",
                        "visual_digest":first.visual_digest,"reproducible":same,"qa_pass":qa.passed,
                        "qa_issue_codes":[x.code.value for x in qa.issues],"fatal_clipping":c,"fatal_overlap":o,
                        "text_truncated":[x.element_id for x in first.text_evidence if x.truncated],
                        "v1_static_clean":v1_ok,"v1_warnings":list(v1_warnings),"v2_static_clean":clean,
                    })
                except Exception as exc:
                    scene_records.append({"scene_id":scene.scene_id,"status":"RENDER_FAIL","error":f"{type(exc).__name__}:{exc}","v1_static_clean":v1_ok,"v1_warnings":list(v1_warnings)})

            record={"lesson_key":lesson_key,"scene_results":scene_records,"final_video":None,"critical_regressions":[]}
            if len(rendered)==len(plan.scenes):
                transitions=tuple(_transition(built[i].scene_graph,built[i+1].scene_graph,i+1) for i in range(len(built)-1))
                final_path=lesson_dir/"final.mp4"
                try:
                    final=assemble_rendered_scenes(video_id=f"core-benchmark:{lesson_key}",scenes=tuple(rendered),transition_plans=transitions,output_path=final_path)
                    violations=_critical_regressions(final_path,len(rendered),spec)
                    if violations:regressions+=1
                    record["critical_regressions"]=list(violations)
                    record["final_video"]={"status":"PASS" if not violations else "REGRESSION","duration":final.duration,"size_bytes":final.file_size_bytes,"diagnostics":list(final.diagnostics)}
                except Exception as exc:
                    regressions+=1;record["critical_regressions"]=[f"ASSEMBLY:{type(exc).__name__}"];record["final_video"]={"status":"FAIL","error":f"{type(exc).__name__}:{exc}"}
            else:
                regressions+=1;record["critical_regressions"]=["MISSING_RENDERED_SCENE"]
            lessons.append(record)

    v1_rate=v1_clean/total if total else 0;v2_rate=v2_clean/total if total else 0
    result={
        "benchmark_id":BENCHMARK_ID,"engine_commit":_git_sha(),
        "profile":{"width":WIDTH,"height":HEIGHT,"fps":FPS,"scene_duration":SCENE_DURATION},
        "sample_count":total,
        "metrics":{
            "render_success_rate":rendered_ok/total if total else 0,
            "fatal_clipping_count":clipping,
            "fatal_overlap_count":overlap,
            "invalid_motion_plan_count":invalid_motion,
            "reproducibility_rate":reproducible/total if total else 0,
            "v1_v2_critical_regression_count":regressions,
            "v1_static_quality_rate":v1_rate,
            "v2_static_quality_rate":v2_rate,
            "v2_static_quality_delta":v2_rate-v1_rate,
        },
        "static_quality_metric":metric,"lessons":lessons,
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }
    text=json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)
    print(text);print("CORE_BENCHMARK_SUMMARY="+json.dumps(result["metrics"],sort_keys=True))
    if output_json is not None:
        output_json.parent.mkdir(parents=True,exist_ok=True);output_json.write_text(text+"\n",encoding="utf-8")
    return result


def main()->int:
    parser=argparse.ArgumentParser();parser.add_argument("--output-json",type=Path,default=None);args=parser.parse_args()
    result=asyncio.run(run(args.output_json))
    return 0 if result["metrics"]["render_success_rate"]==1.0 else 2


if __name__=="__main__":
    raise SystemExit(main())
