"""V3-06 CPU-only, certified binary-search sequence renderer.

Draws bounded primitives with existing V2 Pillow theme/font; encodes raw RGB
through a fixed FFmpeg command. Absolutely no generated Python or arbitrary
renderer instructions. V3-05 replay + semantic binding is always re-run.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import time

from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, ConfigDict, Field, model_validator

# V2 uses the same open Pillow + FFmpeg stack; avoid importing
# app.rendering.__init__ which eagerly pulls provider SDKs and settings.
# Project-owned palette constants are mirrored for an isolated CPU renderer.
from .blackboard_style import BLACK, WHITE, GREY, YELLOW, CYAN, GREEN, cmu_font
COLOR_BG = BLACK
COLOR_PRIMARY = CYAN
COLOR_ACCENT = GREEN
COLOR_HIGHLIGHT = YELLOW
COLOR_TEXT_MAIN = WHITE
COLOR_TEXT_MUTED = GREY
from learnflow_v2.repair import compute_content_hash
from .binary_search_trace import (
    BinarySearchTrace, certify_and_route_binary_search,
)
from .models import SemanticContractError

RENDERER_VERSION = "v3-06-certified-sequence-blackboard-v2"
MAX_VISIBLE_ITEMS = 16
MAX_FRAMES = 960
MIN_FRAME_DELTA = 1.25


class SequenceRenderProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    width: int = Field(default=960, ge=640, le=1920, multiple_of=2)
    height: int = Field(default=540, ge=360, le=1080, multiple_of=2)
    fps: int = Field(default=18, ge=12, le=30)
    seconds_per_step: float = Field(default=1.0, ge=0.7, le=2.5)

    @model_validator(mode="after")
    def _aspect(self):
        if self.width * 9 != self.height * 16:
            raise ValueError("V3_06_16_9_ASPECT_RATIO_REQUIRED")
        return self

    def frames_per_step(self) -> int:
        return round(self.seconds_per_step * self.fps)


class SequenceRenderEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    renderer_version: str = RENDERER_VERSION
    video_path: str
    video_sha256: str
    video_bytes: int
    source_trace_sha256: str
    source_ledger_sha256: str
    source_route_hash: str
    source_manifest_hash: str
    width: int
    height: int
    fps: int
    frame_count: int
    duration_seconds: float
    step_frame_indices: tuple[int, ...]
    decoded_anchor_mae: tuple[float, ...]
    decoded_step_deltas: tuple[float, ...]
    identity_centers: tuple[int, ...]
    temporal_geometry_pass: bool
    decoded_semantic_frames_pass: bool
    render_wall_seconds: float
    status: str = "RENDERED_VERIFIED_OFFLINE_NO_NARRATION_AUDIO"


def _ease(t: float) -> float:
    v = max(0.0, min(1.0, t))
    return v * v * (3.0 - 2.0 * v)


def _lerp(x: float, y: float, a: float) -> float:
    return x + (y - x) * a


def _layout(profile: SequenceRenderProfile, length: int) -> tuple[int, ...]:
    if length > MAX_VISIBLE_ITEMS:
        raise SemanticContractError("V3_06_VISIBLE_ARRAY_CAP_EXCEEDED")
    margin, available = round(profile.width * 0.075), profile.width * 0.85
    if not length:
        return ()
    dx = min(88 * profile.width / 960, available / length)
    start = profile.width / 2 - dx * (length - 1) / 2
    centers = tuple(round(start + i * dx) for i in range(length))
    if not all(margin <= x <= profile.width-margin for x in centers):
        raise SemanticContractError("V3_06_ARRAY_OFFSCREEN")
    if len(centers) > 1 and min(y-x for x,y in zip(centers,centers[1:])) < 30 * profile.width/960:
        raise SemanticContractError("V3_06_ARRAY_LABEL_COLLISION")
    return centers


def _validate_visual_labels(profile: SequenceRenderProfile, values: tuple[int, ...], target: int) -> None:
    """Reject illegible digit strings rather than drawing overlapped labels."""
    centers = _layout(profile, len(values))
    scale = profile.width / 960
    half = min(round(34*scale),
               round((centers[1]-centers[0])*0.42) if len(centers)>1 else round(34*scale))
    half = max(10, half)
    draw = ImageDraw.Draw(Image.new("RGB", (4,4)))
    font = _font(25*profile.height/540)
    for number in values:
        box = draw.textbbox((0,0),str(number),font=font)
        if box[2]-box[0] > 2*half-10:
            raise SemanticContractError("V3_06_NUMERIC_LABEL_OVERLAP")
    target_font = _font(24*profile.height/540)
    box=draw.textbbox((0,0),f"TARGET  {target}",font=target_font)
    if box[2]-box[0] > 220*scale:
        raise SemanticContractError("V3_06_TARGET_LABEL_OVERLAP")


def _font(size: int) -> ImageFont.ImageFont:
    return cmu_font(max(11, round(size)))


def _center_text(draw: ImageDraw.ImageDraw, x: int, y: int, value: str,
                 font: ImageFont.ImageFont, color: tuple[int,int,int]) -> None:
    draw.text((x,y), value, font=font, fill=color, anchor="mm")


def _safe_subtitle(draw, text: str, font, profile) -> str:
    max_width = profile.width - round(profile.width * 0.12)
    out = text.strip().replace("\n", " ")
    # NEVER draw offscreen; visible truncation, no hidden overlay.
    while out and draw.textbbox((0,0),out,font=font)[2] > max_width:
        out = out[:-1]
    if out != text.strip().replace("\n", " "):
        out = out.rstrip()[:-1] + "…" if len(out) > 1 else ""
    return out


def draw_binary_search_frame(*, trace: BinarySearchTrace, step_index: int,
                             progress: float, subtitle: str,
                             profile: SequenceRenderProfile) -> Image.Image:
    """Pure deterministic draw: fixed object positions, tweened pointer locations.

    Pointer animation is only between adjacent oracle-certified step states;
    the array values and index slots NEVER reorder.
    """
    if not 0 <= step_index < len(trace.steps):
        raise SemanticContractError("V3_06_INVALID_STEP_FRAME")
    centers = _layout(profile, len(trace.query.values))
    w, h = profile.width, profile.height
    sx, sy = w/960, h/540
    image = Image.new("RGB", (w,h), COLOR_BG)
    d=ImageDraw.Draw(image)
    FAINT_COLOR = (61,61,61)
    text=_font(24*sy); title=_font(34*sy); small=_font(17*sy); valfont=_font(25*sy)
    pad=round(60*sx)
    d.line((pad,round(97*sy),w-pad,round(97*sy)),fill=FAINT_COLOR,width=max(1,round(2*sy)))
    d.text((pad,round(28*sy)),"BINARY SEARCH",font=title,fill=COLOR_TEXT_MAIN)
    d.text((pad,round(71*sy)),"Verified leftmost-index trace  /  immutable item IDs",font=small,fill=COLOR_TEXT_MUTED)
    _center_text(d,w-round(125*sx),round(56*sy),f"TARGET  {trace.query.target}",text,COLOR_HIGHLIGHT)

    step=trace.steps[step_index]
    previous=trace.steps[max(0,step_index-1)]
    a=_ease(progress/0.32) if step_index else 1.0
    low=_lerp(previous.low,step.low,a) if step_index else float(step.low)
    high=_lerp(previous.high,step.high,a) if step_index else float(step.high)
    prevmid=previous.mid if previous.mid is not None else (previous.candidate_index or 0)
    mid=step.mid if step.mid is not None else step.candidate_index
    pointer=_lerp(prevmid, mid if mid is not None else prevmid,a) if step_index else float(mid if mid is not None else 0)
    # Slot backgrounds show currently eligible and rejected *indices*.
    board_y=round(288*sy)
    boxhalf=min(round(34*sx),round((centers[1]-centers[0])*0.42) if len(centers)>1 else round(34*sx))
    boxhalf=max(10,boxhalf)
    if centers:
        if min(centers)-boxhalf < pad or max(centers)+boxhalf > w-pad:
            raise SemanticContractError("V3_06_SLOT_OFFSCREEN")
        for i,(x,v) in enumerate(zip(centers,trace.query.values)):
            # Smooth visual change during boundary motion, without changing
            # the stable item identity/center/value.
            eligible = low-0.01 <= i <= high+0.01
            ismid = step.phase=="COMPARE" and step.mid==i
            found = step.phase=="COMPLETE" and trace.result_index==i
            if found:
                fill,edge=(28,111,78),COLOR_ACCENT
            elif eligible:
                fill,edge=(20,20,20),(115,115,115)
            else:
                fill,edge=(7,7,7),(49,49,49)
            if ismid and progress>=0.32:
                fill,edge=(54,47,9),COLOR_HIGHLIGHT
            rect=(x-boxhalf,board_y-round(34*sy),x+boxhalf,board_y+round(34*sy))
            d.rounded_rectangle(rect,radius=round(10*sy),fill=fill,outline=edge,width=max(2,round(2*sy)))
            _center_text(d,x,board_y-1,str(v),valfont,COLOR_TEXT_MAIN if eligible or found or ismid else (96,115,134))
            _center_text(d,x,board_y+round(55*sy),str(i),small,COLOR_TEXT_MUTED)
    else:
        _center_text(d,w//2,board_y,"EMPTY ARRAY   [ ]",title,COLOR_TEXT_MUTED)

    # Three pointer rows always stay above sequence cells, not over captions.
    if centers:
        def marker(value, y, name, color):
            if value<0 or value>len(centers)-1: return
            if len(centers)==1: x=centers[0]
            else: x=centers[0]+(centers[-1]-centers[0])*value/(len(centers)-1)
            r=max(4,round(5*sy))
            d.ellipse((round(x-r),round(y-r),round(x+r),round(y+r)),fill=color)
            _center_text(d,round(x),round(y-20*sy),name,small,color)
        marker(low,round(176*sy),"LOW",COLOR_PRIMARY)
        marker(high,round(215*sy),"HIGH",(166,146,250))
        if step.phase=="COMPARE" or (step.phase=="COMPLETE" and step.candidate_index is not None):
            marker(pointer,round(254*sy),"MID" if step.phase=="COMPARE" else "FOUND",COLOR_HIGHLIGHT if step.phase=="COMPARE" else COLOR_ACCENT)
    d.line((pad,round(376*sy),w-pad,round(376*sy)), fill=FAINT_COLOR, width=max(1,round(2*sy)))
    if step.phase=="COMPARE":
        detail=f"LOW {step.low}    HIGH {step.high}    MID {step.mid}    VALUE {step.observed}"
        decision=step.action.replace("_"," ")
    else:
        detail=f"COMPLETE   •   {'FOUND AT INDEX '+str(trace.result_index) if trace.result_index is not None else 'NOT FOUND'}"
        decision="FIRST MATCH" if trace.result_index is not None else "SEARCH EXHAUSTED"
    _center_text(d,w//2,round(402*sy),detail,small,COLOR_TEXT_MAIN)
    _center_text(d,w//2,round(432*sy),decision,text,COLOR_ACCENT if step.phase=="COMPLETE" else COLOR_HIGHLIGHT)
    subtitle=_safe_subtitle(d,subtitle,_font(17*sy),profile)
    _center_text(d,w//2,round(489*sy),subtitle,_font(17*sy),COLOR_TEXT_MUTED)
    _center_text(d,w//2,round(523*sy),f"STEP {step_index+1:02d} / {len(trace.steps):02d}",small,COLOR_PRIMARY)
    return image


def _ffmpeg_anchor(path: Path, *, at: float, profile: SequenceRenderProfile) -> Image.Image:
    cmd=["ffmpeg","-nostdin","-v","error","-ss",f"{at:.5f}","-i",str(path),
         "-frames:v","1","-f","rawvideo","-pix_fmt","rgb24","pipe:1"]
    try:
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=25)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise SemanticContractError("V3_06_DECODE_COMMAND_FAILED") from exc
    expected=profile.width*profile.height*3
    if p.returncode!=0 or len(p.stdout)!=expected:
        raise SemanticContractError("V3_06_MP4_DECODE_FAILED")
    return Image.frombytes("RGB",(profile.width,profile.height),p.stdout)


def _mean_absolute_error(a: Image.Image, b: Image.Image, *, rect=None) -> float:
    from PIL import ImageChops, ImageStat
    if rect is not None: a,b=a.crop(rect),b.crop(rect)
    return sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3.0


def render_certified_binary_search_video(*, trace: BinarySearchTrace, plan,
                                          pattern, ledger, registry, script,
                                          storyboard, scenegraph,
                                          output_path: str | Path,
                                          profile: SequenceRenderProfile=SequenceRenderProfile(),
                                          verify_decoded: bool=True) -> SequenceRenderEvidence:
    """No fallback to CONCEPT_CARD. Re-certification is mandatory at the boundary."""
    start=time.monotonic()
    if not verify_decoded:
        raise SemanticContractError("V3_06_PIXEL_VERIFICATION_REQUIRED")
    if not isinstance(profile,SequenceRenderProfile):
        profile=SequenceRenderProfile.model_validate(profile)
    certified=certify_and_route_binary_search(
        trace=trace,plan=plan,pattern=pattern,ledger=ledger,registry=registry,
        script=script,storyboard=storyboard,scenegraph=scenegraph,
    )
    # Empty input has a valid oracle-certified terminal-only trace; V3-04
    # correctly abstains from claiming stateful motion. Permit a one-state
    # specialized EMPTY ARRAY clip, never a CONCEPT_CARD conversion.
    empty_terminal = (
        not trace.query.values and len(trace.steps) == 1
        and trace.steps[0].phase == "COMPLETE"
        and certified.route.status.value == "ABSTAIN"
    )
    if certified.route.selected_variant not in ("TRACE_SPOTLIGHT","TRACE_COMPACT") and not empty_terminal:
        raise SemanticContractError("V3_06_BINARY_SEQUENCE_PATTERN_ABSTAIN")
    if len(trace.query.values)>MAX_VISIBLE_ITEMS:
        raise SemanticContractError("V3_06_VISIBLE_ARRAY_CAP_EXCEEDED")
    _validate_visual_labels(profile, trace.query.values, trace.query.target)
    frame_per=profile.frames_per_step()
    count=frame_per*len(trace.steps)
    if count>MAX_FRAMES: raise SemanticContractError("V3_06_FRAME_BUDGET_EXCEEDED")
    subtitles=tuple(next(s.spoken_text for s in script.segments if s.segment_id==b.script_segment_ref)
                    for b in plan.beats)
    if len(subtitles)!=len(trace.steps):
        raise SemanticContractError("V3_06_BEAT_TIMING_MISMATCH")
    output=Path(output_path).absolute()
    if output.exists() or output.is_symlink() or output.suffix.lower()!=".mp4":
        raise SemanticContractError("V3_06_UNSAFE_OUTPUT_PATH")
    if not output.parent.is_dir():
        raise SemanticContractError("V3_06_PARENT_DIRECTORY_REQUIRED")
    # Prevent caller-provided symlink path from resolving outside workspace.
    if any(p.is_symlink() for p in (output.parent, *output.parent.parents)):
        raise SemanticContractError("V3_06_SYMLINK_OUTPUT_FORBIDDEN")
    tmp=output.with_name(f".{output.stem}.{trace.trace_sha256[:12]}.part.mp4")
    if tmp.exists(): raise SemanticContractError("V3_06_TEMP_OUTPUT_ALREADY_EXISTS")
    cmd=["ffmpeg","-hide_banner","-nostdin","-loglevel","error","-y",
         "-f","rawvideo","-pix_fmt","rgb24","-s:v",f"{profile.width}x{profile.height}",
         "-r",str(profile.fps),"-i","pipe:0","-an","-c:v","libx264",
         "-preset","ultrafast","-crf","20","-pix_fmt","yuv420p",
         "-movflags","+faststart","-map_metadata","-1",str(tmp)]
    proc=None
    try:
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        assert proc.stdin is not None
        for t in range(count):
            i,sub=divmod(t,frame_per)
            im=draw_binary_search_frame(
                trace=trace,step_index=i,progress=sub/max(1,frame_per-1),
                subtitle=subtitles[i],profile=profile,
            )
            proc.stdin.write(im.tobytes())
        proc.stdin.close()
        assert proc.stderr is not None
        stderr=proc.stderr.read()
        exit_code=proc.wait(timeout=120)
        if exit_code!=0 or not tmp.exists() or tmp.stat().st_size==0:
            raise SemanticContractError(f"V3_06_FFMPEG_ENCODING_FAILED: {stderr[-240:].decode(errors='replace')}")
        per_step_frames=tuple(i*frame_per+max(1,round(frame_per*0.72)) for i in range(len(trace.steps)))
        decoded_mae=[]
        sampled=[]
        for i,frame in enumerate(per_step_frames):
            at=(frame+0.4)/profile.fps
            if verify_decoded:
                decoded=_ffmpeg_anchor(tmp,at=at,profile=profile)
                ideal=draw_binary_search_frame(trace=trace,step_index=i,progress=0.75,
                                               subtitle=subtitles[i],profile=profile)
                mae=_mean_absolute_error(decoded,ideal)
                if mae>8.0: raise SemanticContractError(f"V3_06_DECODED_SEMANTIC_FRAME_MISMATCH step={i} mae={mae:.2f}")
                decoded_mae.append(round(mae,3))
                sampled.append(decoded)
        deltas=[]
        # Compare actual decoded frames in the semantic array+pointer viewport.
        roi=(round(profile.width*.055),round(profile.height*.26),
             round(profile.width*.945),round(profile.height*.69))
        for a,b in zip(sampled,sampled[1:]):
            delta=_mean_absolute_error(a,b,rect=roi)
            deltas.append(round(delta,3))
            if delta<MIN_FRAME_DELTA:
                raise SemanticContractError(f"V3_06_NO_SEMANTIC_PIXEL_CHANGE delta={delta:.3f}")
        # Atomic no-clobber publication: do not overwrite a concurrently
        # created target (including a late symlink).
        try:
            os.link(tmp,output)
        except FileExistsError as exc:
            raise SemanticContractError("V3_06_OUTPUT_RACE_DETECTED") from exc
        tmp.unlink()
    except Exception:
        if proc and proc.poll() is None: proc.kill()
        if proc: proc.wait()
        tmp.unlink(missing_ok=True)
        raise
    video_hash=hashlib.sha256(output.read_bytes()).hexdigest()
    return SequenceRenderEvidence(
        video_path=str(output),video_sha256=video_hash,video_bytes=output.stat().st_size,
        source_trace_sha256=trace.trace_sha256,source_ledger_sha256=certified.ledger_sha256,
        source_route_hash=certified.route.decision_hash,
        source_manifest_hash=compute_content_hash({
            "trace":trace.trace_sha256,"ledger":certified.ledger_sha256,
            "route":certified.route.decision_hash,
            "profile":profile.model_dump(mode="json"),"renderer":RENDERER_VERSION,
        }),width=profile.width,height=profile.height,fps=profile.fps,
        frame_count=count,duration_seconds=count/profile.fps,
        step_frame_indices=per_step_frames,decoded_anchor_mae=tuple(decoded_mae),
        decoded_step_deltas=tuple(deltas),
        identity_centers=_layout(profile,len(trace.query.values)),
        temporal_geometry_pass=True,decoded_semantic_frames_pass=verify_decoded,
        render_wall_seconds=round(time.monotonic()-start,3),
    )
