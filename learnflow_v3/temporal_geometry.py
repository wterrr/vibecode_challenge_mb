"""V3-11 deterministic temporal geometry: continuous affine sweep and conservative easing.

This stage REUSES frozen V2 Rect collision semantics, V3 CMU font metrics,
the V3-06 Pillow/FFmpeg stack. It consumes renderer-owned keyframe geometry,
not LLM-generated coordinates. Any unprovable nonlinear sweep fails closed.
"""
from __future__ import annotations

import math
from typing import Literal

from PIL import Image, ImageDraw
from pydantic import Field, field_validator, model_validator

from learnflow_v2.layout.schema import Rect
from learnflow_v2.repair import compute_content_hash
from .blackboard_style import cmu_font
from .models import SemanticContractError, V3Model

VERSION = "v3-11-interpolation-aware-layout-v1"
EPS = 1e-7
MAX_DEPTH = 11


def _fail(reason: str) -> None:
    raise SemanticContractError("V3_11_" + reason)


class TemporalBox(V3Model):
    """Unlike V2 Rect, negatives are initially permitted so clipping gets typed QA."""
    x: float
    y: float
    width: float = Field(gt=0.0)
    height: float = Field(gt=0.0)

    @field_validator("x", "y", "width", "height", mode="before")
    @classmethod
    def _number(cls, v):
        if type(v) not in (int, float) or not math.isfinite(v):
            raise ValueError("V3_11_FINITE_NUMERIC_RECT_REQUIRED")
        return float(v)

    @property
    def right(self): return self.x+self.width

    @property
    def bottom(self): return self.y+self.height

    def v2_rect(self) -> Rect:
        if self.x < 0 or self.y < 0:
            _fail("OFFSCREEN_BOX")
        return Rect(x=self.x,y=self.y,width=self.width,height=self.height)


class TemporalKeyframe(V3Model):
    frame: int = Field(strict=True,ge=0)
    box: TemporalBox
    font_px: int | None = Field(default=None,ge=9,le=96)
    text: str | None = Field(default=None,max_length=160)

    @model_validator(mode="after")
    def _text(self):
        if (self.text is None) != (self.font_px is None):
            raise ValueError("V3_11_TEXT_FONT_PAIR_REQUIRED")
        if self.text is not None and not self.text.strip():
            raise ValueError("V3_11_EMPTY_VISIBLE_TEXT")
        return self


class TemporalTrack(V3Model):
    object_id: str = Field(min_length=1,max_length=80)
    role: Literal["CONTENT","TITLE","CAPTION"]
    kind: Literal["RECT","TEXT"]
    interpolation: Literal["LINEAR","SMOOTHSTEP"] = "LINEAR"
    keyframes: tuple[TemporalKeyframe,...] = Field(min_length=2,max_length=60)

    @model_validator(mode="after")
    def _shape(self):
        frames=[k.frame for k in self.keyframes]
        if any(b<=a for a,b in zip(frames,frames[1:])):
            raise ValueError("V3_11_KEYFRAMES_NOT_STRICTLY_ORDERED")
        if any((k.text is None) == (self.kind=="TEXT") for k in self.keyframes):
            raise ValueError("V3_11_KIND_TEXT_CONTRACT")
        return self


class TemporalLayoutPlan(V3Model):
    layout_id: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    width: int = Field(strict=True,ge=320,le=1920)
    height: int = Field(strict=True,ge=180,le=1080)
    fps: int = Field(strict=True,ge=12,le=30)
    frame_count: int = Field(strict=True,ge=12,le=300)
    edge_inset: float = Field(default=8.0,ge=0.0,le=80.0)
    subtitle_band: TemporalBox
    text_padding: float = Field(default=5.0,ge=0.0,le=30.0)
    max_simultaneously_moving: int = Field(default=4,strict=True,ge=1,le=12)
    max_pixels_per_frame: float = Field(default=55.0,gt=0.0,le=120.0)
    tracks: tuple[TemporalTrack,...] = Field(min_length=1,max_length=12)

    @model_validator(mode="after")
    def _shape(self):
        ids=[x.object_id for x in self.tracks]
        if len(ids)!=len(set(ids)):
            raise ValueError("V3_11_DUPLICATE_OBJECT_ID")
        if self.width<=2*self.edge_inset or self.height<=2*self.edge_inset:
            raise ValueError("V3_11_INFEASIBLE_SAFE_EDGE")
        s=self.subtitle_band
        if not (self.edge_inset<=s.x and self.edge_inset<=s.y and
                s.right<=self.width-self.edge_inset and
                s.bottom<=self.height-self.edge_inset):
            raise ValueError("V3_11_INVALID_SUBTITLE_SAFE_BAND")
        for track in self.tracks:
            if track.keyframes[0].frame!=0 or track.keyframes[-1].frame!=self.frame_count-1:
                raise ValueError("V3_11_INCOMPLETE_OBJECT_TIMELINE")
        return self


class TemporalGeometryCertificate(V3Model):
    version: Literal["v3-11-interpolation-aware-layout-v1"] = VERSION
    layout_id: str
    source_hash: str
    frame_count: int
    tested_frames: int
    checked_intervals: int
    analytic_pair_segments: int
    conservative_pair_subdivisions: int
    checked_text_bounds: int
    max_simultaneous_motion_observed: int
    critical_collisions: Literal[0] = 0
    clipping_errors: Literal[0] = 0
    text_fit_errors: Literal[0] = 0
    subtitle_intrusions: Literal[0] = 0
    status: Literal["BOUNDED_TEMPORAL_GEOMETRY_CERTIFIED"] = "BOUNDED_TEMPORAL_GEOMETRY_CERTIFIED"
    pixel_rendered: Literal[False] = False
    audio_timing_verified: Literal[False] = False
    video_publication_ready: Literal[False] = False


def _interp(a: TemporalBox,b: TemporalBox,u:float)->TemporalBox:
    return TemporalBox(x=a.x+(b.x-a.x)*u,y=a.y+(b.y-a.y)*u,
                       width=a.width+(b.width-a.width)*u,
                       height=a.height+(b.height-a.height)*u)


def _state(track:TemporalTrack,frame:float):
    frames=track.keyframes
    k=next(i for i in range(len(frames)-1)
           if frames[i].frame <= frame <= frames[i+1].frame)
    a,b=frames[k],frames[k+1]
    u=(frame-a.frame)/(b.frame-a.frame)
    if track.interpolation=="SMOOTHSTEP":
        u=u*u*(3-2*u)
    box=_interp(a.box,b.box,u)
    # Conservative crossfade contract: both labels may be visible for all in-between frames.
    texts=tuple(dict.fromkeys((a.text,b.text))) if track.kind=="TEXT" else ()
    largest_font=max(a.font_px or 0,b.font_px or 0)
    return box,tuple(s for s in texts if s is not None),largest_font


def _intersect(a:TemporalBox,b:TemporalBox)->bool:
    # Reuse V2 immutable Rect.intersects; disallow offscreen before calling it.
    return a.v2_rect().intersects(b.v2_rect(),tol=EPS)


def _bounds(plan:TemporalLayoutPlan,track:TemporalTrack,box:TemporalBox):
    inset=plan.edge_inset
    if (box.x<inset-EPS or box.y<inset-EPS or
        box.right>plan.width-inset+EPS or box.bottom>plan.height-inset+EPS):
        _fail("FRAME_CLIPPING:"+track.object_id)
    subtitle=plan.subtitle_band
    if track.role=="CAPTION":
        if (box.x<subtitle.x-EPS or box.y<subtitle.y-EPS or
            box.right>subtitle.right+EPS or box.bottom>subtitle.bottom+EPS):
            _fail("CAPTION_OUTSIDE_RESERVED_BAND:"+track.object_id)
    elif _intersect(box,subtitle):
        _fail("SUBTITLE_INTRUSION:"+track.object_id)


def _measure_text(draw,track:TemporalTrack,box:TemporalBox,texts:tuple[str,...],
                  font_px:int,plan:TemporalLayoutPlan):
    for text in texts:
        font=cmu_font(font_px)
        bbox=draw.textbbox((0,0),text,font=font)
        width=bbox[2]-bbox[0]
        height=bbox[3]-bbox[1]
        if (width>box.width-2*plan.text_padding+EPS or
            height>box.height-2*plan.text_padding+EPS):
            _fail("INTERMEDIATE_TEXT_OVERFLOW:"+track.object_id)


def _interval_for_lt(v0:float,v1:float):
    """Parameter interval u∈[0,1] satisfying v(u)<-EPS; open boundary guarded."""
    dv=v1-v0
    if abs(dv)<1e-12:
        return (0.0,1.0) if v0 < -EPS else None
    root=(-EPS-v0)/dv
    return (0.0,min(1.0,root)) if dv>0 else (max(0.0,root),1.0)


def _continuous_linear_collision(a0,a1,b0,b1)->bool:
    # Rectangles overlap iff four affine differences are STRICTLY negative
    # at the SAME continuous time. Merely testing endpoints is unsound.
    inequalities=(
        (a0.x-b0.right,a1.x-b1.right),
        (b0.x-a0.right,b1.x-a1.right),
        (a0.y-b0.bottom,a1.y-b1.bottom),
        (b0.y-a0.bottom,b1.y-a1.bottom),
    )
    low,high=0.0,1.0
    for v0,v1 in inequalities:
        band=_interval_for_lt(v0,v1)
        if band is None:
            return False
        low=max(low,band[0])
        high=min(high,band[1])
        if high<=low+1e-10:
            return False
    return True


def _envelope(a:TemporalBox,b:TemporalBox)->TemporalBox:
    x=min(a.x,b.x)
    y=min(a.y,b.y)
    return TemporalBox(x=x,y=y,
                       width=max(a.right,b.right)-x,
                       height=max(a.bottom,b.bottom)-y)


def _pair_safe_adaptive(t1,t2,start:float,end:float,depth:int):
    """Conservative intervals: no false PASS for nonlinear easing.

    Each box coordinate is endpoint-monotone within one keyframe segment.
    Union AABBs enclose all intermediate values; recursively disprove contact.
    At maximum depth an unresolved overlap raises instead of being approved.
    """
    a0,a1=_state(t1,start)[0],_state(t1,end)[0]
    b0,b1=_state(t2,start)[0],_state(t2,end)[0]
    if not _intersect(_envelope(a0,a1),_envelope(b0,b1)):
        return 1
    mid=(start+end)/2
    if _intersect(_state(t1,mid)[0],_state(t2,mid)[0]):
        _fail("INTERMEDIATE_COLLISION:"+t1.object_id+":"+t2.object_id)
    if depth>=MAX_DEPTH:
        _fail("UNPROVEN_NONLINEAR_SWEEP:"+t1.object_id+":"+t2.object_id)
    return (1+_pair_safe_adaptive(t1,t2,start,mid,depth+1)
             +_pair_safe_adaptive(t1,t2,mid,end,depth+1))


def certify_temporal_layout(plan:TemporalLayoutPlan)->TemporalGeometryCertificate:
    """Global time-grid geometric preflight: no video rendered, no auto-unsafe fallback."""
    tracks=plan.tracks
    points=sorted({k.frame for t in tracks for k in t.keyframes})
    draw=ImageDraw.Draw(Image.new("RGB",(1,1)))
    text_checks=0
    frames_checked=0
    observed_motion=0
    for f in range(plan.frame_count):
        frames_checked+=1
        poses=[]
        for t in tracks:
            box,texts,font=_state(t,float(f))
            _bounds(plan,t,box)
            if texts:
                _measure_text(draw,t,box,texts,font,plan)
                text_checks+=len(texts)
            poses.append(box)
        for i in range(len(tracks)):
            for j in range(i+1,len(tracks)):
                if _intersect(poses[i],poses[j]):
                    _fail("FRAME_COLLISION:"+tracks[i].object_id+":"+tracks[j].object_id+":"+str(f))
        if f+1<plan.frame_count:
            count=0
            for t in tracks:
                a=_state(t,float(f))[0]
                b=_state(t,float(f+1))[0]
                distance=math.hypot(b.x-a.x,b.y-a.y)
                if distance>EPS or abs(b.width-a.width)>EPS or abs(b.height-a.height)>EPS:
                    count+=1
                if max(distance,abs(b.width-a.width),abs(b.height-a.height))>plan.max_pixels_per_frame+EPS:
                    _fail("EXCESSIVE_MOTION_PER_FRAME:"+t.object_id)
            observed_motion=max(observed_motion,count)
            if count>plan.max_simultaneously_moving:
                _fail("EXCESSIVE_SIMULTANEOUS_MOTION")
    analytic=0
    adaptive=0
    for first in range(len(tracks)):
        for second in range(first+1,len(tracks)):
            a,b=tracks[first],tracks[second]
            for start,end in zip(points,points[1:]):
                a0=_state(a,float(start))[0];a1=_state(a,float(end))[0]
                b0=_state(b,float(start))[0];b1=_state(b,float(end))[0]
                if a.interpolation==b.interpolation:
                    # Both use SAME parametric easing on this segment; even
                    # smoothstep is affine in their common eased parameter.
                    if _continuous_linear_collision(a0,a1,b0,b1):
                        _fail("SWEPT_COLLISION:"+a.object_id+":"+b.object_id)
                    analytic+=1
                else:
                    adaptive+=_pair_safe_adaptive(a,b,float(start),float(end),0)
    # Text-fit on every keyframe interval: bound by minimum box dimensions and
    # maximum font; both old/new text are conservatively present during morph.
    for track in tracks:
        if track.kind!="TEXT": continue
        for a,b in zip(track.keyframes,track.keyframes[1:]):
            maxfont=max(a.font_px,b.font_px)
            texts=tuple(dict.fromkeys((a.text,b.text)))
            smaller=TemporalBox(x=0,y=0,width=min(a.box.width,b.box.width),
                                height=min(a.box.height,b.box.height))
            _measure_text(draw,track,smaller,texts,maxfont,plan)
            text_checks+=len(texts)
    return TemporalGeometryCertificate(
        layout_id=plan.layout_id,
        source_hash=compute_content_hash(plan.model_dump(mode="json")),
        frame_count=plan.frame_count,tested_frames=frames_checked,
        checked_intervals=len(points)-1,analytic_pair_segments=analytic,
        conservative_pair_subdivisions=adaptive,
        checked_text_bounds=text_checks,
        max_simultaneous_motion_observed=observed_motion,
    )


def verify_temporal_certificate(*,plan:TemporalLayoutPlan,
                                candidate:TemporalGeometryCertificate)->None:
    """A rehashed/forged certificate never overrides source recomputation."""
    if certify_temporal_layout(plan).model_dump(mode="json")!=candidate.model_dump(mode="json"):
        _fail("FORGED_OR_STALE_CERTIFICATE")


def sample_layout(plan:TemporalLayoutPlan,frame:float):
    """Renderer-owned geometry positions, not semantic LLM output."""
    if not 0<=frame<=plan.frame_count-1:
        _fail("SAMPLE_FRAME_OUTSIDE_TIMELINE")
    return tuple((track, *_state(track,frame)) for track in plan.tracks)
