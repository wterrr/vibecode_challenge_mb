"""Optional Code2Video scene adapter, always off unless worker is configured.

The paid agent selects a *semantic scene*; the API never accepts generated
Python or calls Manim. A distinct worker generates Code2Video code, then a
secretless Manim sandbox executes it. The resulting MP4 enters the ordinary
LearnFlow FFmpeg assembly, timing and decoded-motion QA.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import subprocess
import time
from urllib.parse import urlparse

import httpx

from app.domain.lesson import Code2VideoSceneSpec, ScenePlan
from app.domain.timeline import ResolvedSceneTiming
from app.rendering.base import RenderResult, SceneRenderer

MAX_VIDEO_BYTES=55_000_000
MAX_SCENE_SECONDS=40.0
MIN_INPUT_SECONDS=1.0


def validate_worker_endpoint(url: str, token: str) -> str:
    """Refuse remote plaintext token transmission and all URL tricks."""
    if not url or not token or len(token)<24:
        raise ValueError("Code2Video requires a private worker endpoint and scoped token")
    parsed=urlparse(url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Code2Video worker URL must not contain credentials or query")
    if parsed.path not in ("", "/") or parsed.scheme not in ("http","https"):
        raise ValueError("Code2Video worker URL must be an origin only")
    host=(parsed.hostname or "").lower()
    if parsed.scheme=="http" and host not in (
        "localhost","127.0.0.1","::1","code2video-planner",
    ):
        raise ValueError("External Code2Video endpoints must use HTTPS")
    if not host: raise ValueError("Code2Video worker host missing")
    return url.rstrip("/")


def _probe_duration(path: Path) -> float:
    try:
        cp=subprocess.run([
            "ffprobe","-v","error","-select_streams","v:0",
            "-show_entries","stream=duration","-of","default=nokey=1:noprint_wrappers=1",
            str(path)
        ],capture_output=True,text=True,timeout=20,check=True)
        duration=float(cp.stdout.strip())
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        raise ValueError("Code2Video worker did not return decodable H264") from exc
    if not MIN_INPUT_SECONDS<=duration<=MAX_SCENE_SECONDS:
        raise ValueError("Code2Video returned unsupported scene duration")
    return duration


class Code2VideoSceneRenderer(SceneRenderer):
    def __init__(self,*,worker_url:str="",token:str="",width:int=1280,
                 height:int=720,fps:int=24):
        self.width,self.height,self.fps=width,height,fps
        self.worker_url=worker_url
        self.token=token

    async def render(self,scene:ScenePlan,timing:ResolvedSceneTiming,
                     output_path:Path)->RenderResult:
        if not isinstance(scene.visual_spec,Code2VideoSceneSpec):
            raise ValueError("Expected Code2VideoSceneSpec")
        origin=validate_worker_endpoint(self.worker_url,self.token)
        if not 1.0<=timing.render_duration_seconds<=MAX_SCENE_SECONDS:
            raise ValueError("Code2Video scene duration outside bounded budget")
        body={
            "title":scene.visual_spec.title,
            "narration":scene.narration[:1200],
            "visual_goal":scene.visual_spec.visual_goal,
            "duration_seconds":timing.render_duration_seconds,
            "language":"auto",
        }
        output_path=Path(output_path)
        output_path.parent.mkdir(parents=True,exist_ok=True)
        candidate=output_path.with_suffix(".code2video-raw.mp4")
        bytes_seen=0
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(245,connect=10,read=240),
                follow_redirects=False,
                trust_env=False,
            ) as client:
                async with client.stream(
                    "POST", origin+"/render",
                    headers={"Authorization":"Bearer "+self.token,
                             "Accept":"video/mp4"},
                    json=body,
                ) as response:
                    if response.status_code!=200 or response.headers.get("content-type","").split(";")[0]!="video/mp4":
                        raise ValueError("Code2Video worker rejected render request")
                    with candidate.open("wb") as out:
                        async for chunk in response.aiter_bytes():
                            bytes_seen+=len(chunk)
                            if bytes_seen>MAX_VIDEO_BYTES:
                                raise ValueError("Code2Video worker exceeded video size budget")
                            out.write(chunk)
            if bytes_seen<1024: raise ValueError("Code2Video worker returned empty video")
            duration=await asyncio.to_thread(_probe_duration,candidate)
            # Normalize the external clip to LearnFlow's exact measured TTS
            # duration and codec; never copy arbitrary streams into final MP4.
            factor=timing.render_duration_seconds/duration
            filters=(f"setpts={factor:.7f}*(PTS-STARTPTS),"
                     f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                     f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,"
                     f"fps={self.fps},format=yuv420p")
            cmd=["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
                 "-i",str(candidate),"-vf",filters,"-an",
                 "-c:v","libx264","-preset","veryfast","-threads","2",
                 "-crf","23","-pix_fmt","yuv420p",
                 "-t",str(timing.render_duration_seconds),
                 "-movflags","+faststart",str(output_path)]
            await asyncio.to_thread(subprocess.run,cmd,check=True,timeout=180,
                                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            if not output_path.is_file() or output_path.stat().st_size<1024:
                raise RuntimeError("Code2Video normalized MP4 unavailable")
            return RenderResult(path=str(output_path),width=self.width,
                                height=self.height,
                                duration_seconds=timing.render_duration_seconds,warnings=[])
        except (OSError,RuntimeError,ValueError,subprocess.SubprocessError,httpx.HTTPError):
            output_path.unlink(missing_ok=True)
            raise
        finally:
            candidate.unlink(missing_ok=True)
