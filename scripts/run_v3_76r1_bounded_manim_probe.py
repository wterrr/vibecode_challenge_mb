#!/usr/bin/env python3
"""V3-76R1: 45-second exact pinned Manim/first-tick bisection, before 340s render.

Host-only trusted two-object smoke (Text + RoundedRectangle). Run with the
SAME no-network read-only-root sandbox settings and the V3-76 observer.
No inference, no model Python, no changes to frozen prior video evidence.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_manim_runner import IMAGE,FPS
from learnflow_v3.v376_native_manim_probe import instrument


SOURCE = """# V3-51 GENERIC HOST COMPILED SOURCE NEVER MODEL PYTHON
from manim import *
class GeneratedLesson(Scene):
    def construct(self):
        self.camera.background_color='#080B11'
        brand=Text('LEARNFLOW',font='CMU Serif',font_size=20,color='#E8ECF0')
        top=Text('Runtime probe',font='CMU Serif',font_size=30,color='#E8ECF0').to_edge(UP)
        self.add(brand,top)
        v351_section_0=Text('Probe scene',font='CMU Serif',font_size=24,color='#E8ECF0')
        v351_n0_0_shape=RoundedRectangle(width=3.,height=1.12,
            fill_color='#13212D',fill_opacity=.6,stroke_color='#73CAD2')
        v351_n0_0_label=Text('ACTION',font='CMU Serif',font_size=26,
            color='#E8ECF0')
        v351_n0_0_label.move_to(v351_n0_0_shape)
        v351_n0_0=VGroup(v351_n0_0_shape,v351_n0_0_label)
        self.play(FadeIn(v351_n0_0),run_time=.5)
        self.wait(.75)
"""
PARENT_SHA="33293e63ded8318537197d133f51b0cf36e1aa60"
PREREG=Path(__file__).resolve().parents[1]/"benchmarks/learnflowbench/v3/v3_76r1_runtime_probe_recovery_preregister.json"


def check(condition, code):
    if not condition:
        raise Blocked("V376R1_"+code)


def fixture():
    return SimpleNamespace(scenes=[
        SimpleNamespace(id="probe",nodes=[
            SimpleNamespace(id="demo",kind="SHAPE")])])


def compile_smoke() -> str:
    source=instrument(SOURCE,fixture())
    check(source.count("V3-76 HOST INJECTED ACTUAL MANIM")==1,
          "HOST_PROBE_INJECTION_MISSING")
    check("v376_stage_before_bbox" in source, "NO_BBOX_STAGE")
    return source


def main(output: Path) -> dict:
    prereg=json.loads(PREREG.read_text())
    check(prereg["parent"]["sha"]==PARENT_SHA
          and prereg["kind"]=="FIRST_CHILD_PREREG_BEFORE_CODE",
          "PREREG_DRIFT")
    check(not output.exists(),"OUTPUT_NOT_VERSIONED")
    output.mkdir(parents=True)
    movie_source=output/"v376r1_minimal_host_probe.py"
    movie_source.write_text(compile_smoke(),encoding="utf-8")
    media=output/"manim_output"
    media.mkdir()
    image=subprocess.run(["docker","image","inspect",IMAGE,"--format","{{.Id}}"],
        capture_output=True,text=True,timeout=12)
    check(image.returncode==0,"MISSING_PINNED_MANIM_IMAGE")
    command=[
        "docker","run","--rm","--network","none","--read-only",
        "--cpus","2","--memory","3g","--pids-limit","128",
        "--cap-drop","ALL","--security-opt","no-new-privileges",
        "--user",f"{os.getuid()}:{os.getgid()}",
        "--tmpfs","/tmp:rw,exec,nosuid,size=768m",
        "-e","HOME=/tmp","-e","XDG_CACHE_HOME=/tmp",
        "-v",str(output.resolve())+":/project:ro",
        "-v",str(media.resolve())+":/output:rw",
        "-w","/project",
    ]
    cmu=Path("/usr/share/fonts/truetype/cmu")
    if cmu.is_dir():
        command+=["-v",str(cmu)+":/usr/share/fonts/truetype/cmu:ro"]
    command+=[
        IMAGE,"manim","-ql","-r","1280,720","--fps",str(FPS),
        "--disable_caching","--media_dir","/output",
        "/project/"+movie_source.name,"GeneratedLesson"]
    result={"checkpoint":"V3-76R1","stage":"MINIMAL_BOUND_45_SECONDS",
            "parent":PARENT_SHA,
            "image":IMAGE,"image_id":image.stdout.strip(),
            "max_wallclock_seconds":45,"source_sha256":
                sha256(movie_source.read_bytes()).hexdigest(),
            "network":"none","secret_mounts":False,
            "runtime_gate":"NO_GO_PENDING_PHYSICAL_RECEIPTS"}
    try:
        p=subprocess.run(command,capture_output=True,text=True,timeout=45)
        result["render_returncode"]=p.returncode
        result["render_timed_out"]=False
        # Truncate and sanitize: only bounded Manim source, no user/provider.
        result["stderr_tail"]=p.stderr[-1500:]
    except subprocess.TimeoutExpired:
        result["render_returncode"]=None
        result["render_timed_out"]=True
    result["stage_markers"]=sorted(
        p.name for p in media.glob("v376_*.marker"))
    observations=media/"v376_runtime_geometry.jsonl"
    result["telemetry_bytes"]=observations.stat().st_size if observations.exists() else 0
    files=[p for p in media.rglob("*.mp4")
           if "partial_movie_files" not in p.parts]
    result["native_mp4_count"]=len(files)
    if result["render_returncode"]==0 and files:
        stream=json.loads(subprocess.check_output(["ffprobe","-v","error",
            "-show_streams","-of","json",str(files[0])],timeout=12))["streams"]
        video=next(x for x in stream if x["codec_type"]=="video")
        result["codec"]=video["codec_name"]
        result["video_frames"]=int(video["nb_frames"])
        result["movie_sha256"]=sha256(files[0].read_bytes()).hexdigest()
    else:
        result["codec"]=None;result["video_frames"]=0
    rows=[]
    if observations.is_file() and observations.stat().st_size:
        try:
            rows=[json.loads(line) for line in
                observations.read_text(encoding="utf-8").splitlines()]
        except (ValueError,UnicodeError):
            result["telemetry_parse_error"]=True
    result["runtime_rows"]=len(rows)
    result["runtime_first_row_nonempty"]=bool(rows and rows[0]["objects"])
    pass_gate=(
        result["render_returncode"]==0 and
        not result["render_timed_out"] and
        result["native_mp4_count"]==1 and
        result["codec"]=="h264" and
        result["video_frames"]>=15 and
        result["runtime_rows"]>=15 and
        result["runtime_first_row_nonempty"] and
        "v376_stage_after_flush.marker" in result["stage_markers"]
    )
    result["runtime_gate"]=(
        "MINIMAL_PHYSICAL_PROBE_PASS" if pass_gate else
        "FAIL_CLOSED_FIRST_TICK_NOT_CERTIFIED"
    )
    (output/"v376r1_bounded_probe_receipt.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True))
    check(pass_gate,"MINIMAL_REAL_MANIM_PROBE_NOT_CERTIFIED")
    return result


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",type=Path,required=True)
    main(ap.parse_args().output_dir)
