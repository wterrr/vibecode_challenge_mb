"""V3-11 bounded demonstration renderer for certified temporal geometry.

Reuses V3-06 actual Pillow/FFmpeg and decoded-frame validation. This is a
small geometry demo, NOT a replacement for V3-06 pedagogical renderers.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw
import math
from typing import Literal

from pydantic import Field

from learnflow_v2.repair import compute_content_hash
from .blackboard_style import BLACK, GREY, WHITE, CYAN, GREEN, YELLOW, cmu_font
from .models import SemanticContractError, V3Model
from .sequence_renderer import SequenceRenderProfile, _mean_absolute_error
from .temporal_geometry import (
    TemporalLayoutPlan,TemporalGeometryCertificate,
    certify_temporal_layout,verify_temporal_certificate,sample_layout,
)

class TemporalRenderEvidence(V3Model):
    version: Literal["v3-11-temporal-geometry-render-v1"] = "v3-11-temporal-geometry-render-v1"
    video_sha256: str
    video_bytes: int = Field(gt=0)
    plan_sha256: str
    certificate_sha256: str
    frame_count: int
    fps: int
    anchor_indices: tuple[int,...]
    decoded_anchor_mae: tuple[float,...]
    status: Literal["RENDERED_DECODED_TEMPORAL_GEOMETRY_DEMO"] = "RENDERED_DECODED_TEMPORAL_GEOMETRY_DEMO"
    source_semantics_oracle: Literal["RENDERER_OWNED_GEOMETRY_ONLY"] = "RENDERER_OWNED_GEOMETRY_ONLY"
    production_pipeline_integrated: Literal[False] = False


def draw_temporal_frame(plan:TemporalLayoutPlan,frame:int)->Image.Image:
    if not 0<=frame<plan.frame_count:
        raise SemanticContractError("V3_11_INVALID_DRAW_FRAME")
    im=Image.new("RGB",(plan.width,plan.height),BLACK)
    draw=ImageDraw.Draw(im)
    s=plan.subtitle_band
    draw.rectangle((round(s.x),round(s.y),round(s.right),round(s.bottom)),
                   outline=(58,58,58),width=1)
    palette={"TITLE":WHITE,"CONTENT":CYAN,"CAPTION":GREY}
    for track,box,texts,size in sample_layout(plan,frame):
        color=palette[track.role]
        bounds=tuple(round(x) for x in (box.x,box.y,box.right,box.bottom))
        if track.kind=="RECT":
            draw.rounded_rectangle(bounds,radius=5,outline=color,width=2)
        else:
            # Only the active label is rendered; certification conservatively
            # checked BOTH labels across keyframe transitions and minimum size.
            text=next((k.text for k in reversed(track.keyframes)
                       if k.frame<=frame),texts[0])
            draw.text((round(box.x+plan.text_padding),round(box.y+plan.text_padding)),
                      text,font=cmu_font(size),fill=color)
    return im


def _profile(plan):
    # Share fixed FPS/dimensions and precise CPU anchor decoding with V3-06.
    return SequenceRenderProfile(width=plan.width,height=plan.height,fps=plan.fps)


def _anchors(plan):
    return tuple(sorted(set((0,plan.frame_count//4,plan.frame_count//2,
                             (3*plan.frame_count)//4,plan.frame_count-1))))


def _decode_exact_frame(video:Path,frame:int,profile:SequenceRenderProfile)->Image.Image:
    # Seeking by timestamp is unstable at the final H264 frame. Decode the
    # exact ordinal frame and do not silently accept the preceding frame.
    cmd=["ffmpeg","-nostdin","-v","error","-i",str(video),
         "-vf",f"select=eq(n\\,{frame})","-vsync","0",
         "-frames:v","1","-pix_fmt","rgb24","-f","rawvideo","pipe:1"]
    try:
        done=subprocess.run(cmd,capture_output=True,timeout=30)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise SemanticContractError("V3_11_EXACT_FRAME_DECODE_ERROR") from exc
    if done.returncode!=0 or len(done.stdout)!=profile.width*profile.height*3:
        raise SemanticContractError("V3_11_EXACT_FRAME_DECODE_MISMATCH:"+done.stderr[-160:].decode(errors="replace"))
    return Image.frombytes("RGB",(profile.width,profile.height),done.stdout)


def _validate_video(*,plan:TemporalLayoutPlan,video:Path,anchors):
    profile=_profile(plan)
    from .beat_grounding import _probe
    _probe(video,profile,plan.frame_count)
    mae=[]
    for frame in anchors:
        decoded=_decode_exact_frame(video,frame,profile)
        expected=draw_temporal_frame(plan,frame)
        err=_mean_absolute_error(decoded,expected)
        if err>8.0:
            raise SemanticContractError(f"V3_11_DECODED_GEOMETRY_FRAME_MISMATCH frame={frame} mae={err:.3f}")
        # Also compare each exact object geometry ROI: a tiny moving object
        # must not disappear inside a reassuring whole-frame mean error.
        for track,box,_,_ in sample_layout(plan,frame):
            roi=(max(0,math.floor(box.x-6)),max(0,math.floor(box.y-6)),
                 min(plan.width,math.ceil(box.right+6)),
                 min(plan.height,math.ceil(box.bottom+6)))
            local=_mean_absolute_error(decoded,expected,rect=roi)
            if local>4.0:
                raise SemanticContractError(
                    f"V3_11_DECODED_OBJECT_GEOMETRY_MISMATCH object={track.object_id} "
                    f"frame={frame} mae={local:.3f}")
        mae.append(round(err,3))
    return tuple(mae)


def render_certified_temporal_demo(*,plan:TemporalLayoutPlan,
                                   certificate:TemporalGeometryCertificate,
                                   output_path:str|Path)->TemporalRenderEvidence:
    verify_temporal_certificate(plan=plan,candidate=certificate)
    output=Path(output_path).absolute()
    if output.suffix.lower()!=".mp4" or output.exists() or output.is_symlink():
        raise SemanticContractError("V3_11_UNSAFE_OUTPUT")
    if not output.parent.is_dir() or any(p.is_symlink() for p in (output.parent,*output.parent.parents)):
        raise SemanticContractError("V3_11_UNSAFE_OUTPUT_DIRECTORY")
    source=compute_content_hash(plan.model_dump(mode="json"))
    temporary=output.with_name(f".{output.stem}.{source[:12]}.part.mp4")
    if temporary.exists() or temporary.is_symlink():
        raise SemanticContractError("V3_11_UNSAFE_TEMP_OUTPUT")
    args=["ffmpeg","-hide_banner","-nostdin","-loglevel","error","-y",
          "-f","rawvideo","-pix_fmt","rgb24","-s:v",f"{plan.width}x{plan.height}",
          "-r",str(plan.fps),"-i","pipe:0","-an",
          "-c:v","libx264","-preset","ultrafast","-crf","20",
          "-pix_fmt","yuv420p","-movflags","+faststart",
          "-map_metadata","-1",str(temporary)]
    process=None
    try:
        process=subprocess.Popen(args,stdin=subprocess.PIPE,
                                 stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        assert process.stdin is not None
        for frame in range(plan.frame_count):
            process.stdin.write(draw_temporal_frame(plan,frame).tobytes())
        process.stdin.close()
        assert process.stderr is not None
        stderr=process.stderr.read()
        if process.wait(timeout=100)!=0 or not temporary.is_file() or temporary.stat().st_size==0:
            raise SemanticContractError("V3_11_FFMPEG_ENCODING_FAILED:"+stderr[-120:].decode(errors="replace"))
        anchors=_anchors(plan)
        errs=_validate_video(plan=plan,video=temporary,anchors=anchors)
        try:
            os.link(temporary,output)
        except FileExistsError as exc:
            raise SemanticContractError("V3_11_OUTPUT_RACE") from exc
        temporary.unlink()
    except Exception:
        if process and process.poll() is None:process.kill()
        if process:process.wait()
        temporary.unlink(missing_ok=True)
        raise
    return TemporalRenderEvidence(
        video_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        video_bytes=output.stat().st_size,plan_sha256=source,
        certificate_sha256=compute_content_hash(certificate.model_dump(mode="json")),
        frame_count=plan.frame_count,fps=plan.fps,
        anchor_indices=anchors,decoded_anchor_mae=errs,
    )


def verify_temporal_render(*,plan:TemporalLayoutPlan,
                           certificate:TemporalGeometryCertificate,
                           evidence:TemporalRenderEvidence,video_path:str|Path)->None:
    verify_temporal_certificate(plan=plan,candidate=certificate)
    path=Path(video_path)
    if not path.is_file() or path.is_symlink():
        raise SemanticContractError("V3_11_RENDER_FILE_MISSING")
    source=compute_content_hash(plan.model_dump(mode="json"))
    if (evidence.video_sha256!=hashlib.sha256(path.read_bytes()).hexdigest()
        or evidence.video_bytes!=path.stat().st_size or evidence.plan_sha256!=source
        or evidence.certificate_sha256!=compute_content_hash(certificate.model_dump(mode="json"))
        or evidence.frame_count!=plan.frame_count or evidence.fps!=plan.fps
        or evidence.anchor_indices!=_anchors(plan)):
        raise SemanticContractError("V3_11_STALE_OR_FORGED_RENDER_EVIDENCE")
    actual=_validate_video(plan=plan,video=path,anchors=evidence.anchor_indices)
    if any(abs(x-y)>0.01 for x,y in zip(actual,evidence.decoded_anchor_mae,strict=True)):
        raise SemanticContractError("V3_11_STALE_PIXEL_ANCHORS")
