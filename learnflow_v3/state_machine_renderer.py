"""V3-15: finite STATE_MACHINE candidate renderer, sourced to locked pilot demand.

A state-machine is NOT V3-07's acyclic PROCESS_FLOW: it permits guarded cycles,
retry and branches, with a strict trace replay. Renderer-owned node positions;
no LLM code or coordinates. Standalone, NOT registered for auto-production routing.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time
from typing import Literal

from PIL import Image,ImageDraw
from pydantic import Field,StrictInt,model_validator

from learnflow_v2.repair import compute_content_hash
from .blackboard_style import BLACK, WHITE, GREY, FAINT, CYAN, GREEN, YELLOW, cmu_font, assert_fits
from .models import SemanticContractError,V3Model
from .sequence_renderer import SequenceRenderProfile,_ffmpeg_anchor,_mean_absolute_error

VERSION="v3-15-state-machine-blackboard-v1"
ELIGIBLE_PREREG_TOPICS=("lfb-006-cs","lfb-016-cs")
MAX_NODES=6
MAX_EDGES=12
MAX_FRAMES=180


def _fail(reason):
    raise SemanticContractError("V3_15_"+reason)


class MachineState(V3Model):
    state_id:str=Field(min_length=2,max_length=26,pattern=r"^[a-z][a-z0-9_-]+$")
    label:str=Field(min_length=2,max_length=20)
    terminal:bool=False


class MachineTransition(V3Model):
    transition_id:str=Field(min_length=2,max_length=30,pattern=r"^[a-z][a-z0-9_-]+$")
    source_id:str
    target_id:str
    trigger:str=Field(min_length=2,max_length=20)


class MachineBeat(V3Model):
    beat_id:str=Field(min_length=2,max_length=32,pattern=r"^[a-z][a-z0-9_-]+$")
    state_id:str
    via_transition_id:str|None=None
    trigger:str|None=None

    @model_validator(mode="after")
    def _joint(self):
        if (self.via_transition_id is None)!=(self.trigger is None):
            raise ValueError("V3_15_BEAT_EDGE_TRIGGER_PAIR_REQUIRED")
        return self


class StateMachineLesson(V3Model):
    renderer_family:Literal["STATE_MACHINE"]="STATE_MACHINE"
    source_origin:Literal["AUTHOR_CURATED_LOCKED_PILOT"]="AUTHOR_CURATED_LOCKED_PILOT"
    topic_id:Literal["lfb-006-cs","lfb-016-cs"]
    topic_query_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    concept_title:str=Field(min_length=6,max_length=34)
    states:tuple[MachineState,...]=Field(min_length=3,max_length=MAX_NODES)
    transitions:tuple[MachineTransition,...]=Field(min_length=3,max_length=MAX_EDGES)
    beats:tuple[MachineBeat,...]=Field(min_length=3,max_length=12)
    initial_state_id:str
    no_concept_card_fallback:Literal[True]=True
    registered_in_v3_04_router:Literal[False]=False
    independent_factual_verification:Literal[False]=False
    real_audio_sync_verified:Literal[False]=False

    @model_validator(mode="after")
    def _local_replay(self):
        states={x.state_id:x for x in self.states}
        edges={x.transition_id:x for x in self.transitions}
        if len(states)!=len(self.states) or len(edges)!=len(self.transitions):
            raise ValueError("V3_15_DUPLICATE_GRAPH_ID")
        if len({x.beat_id for x in self.beats})!=len(self.beats):
            raise ValueError("V3_15_DUPLICATE_BEAT")
        if self.initial_state_id not in states:
            raise ValueError("V3_15_START_STATE_UNKNOWN")
        if self.beats[0].state_id!=self.initial_state_id or self.beats[0].via_transition_id is not None:
            raise ValueError("V3_15_BEAT_START_INVALID")
        if any(x.source_id not in states or x.target_id not in states for x in self.transitions):
            raise ValueError("V3_15_EDGE_REFERENCES_MISSING_NODE")
        if len({(x.source_id,x.target_id,x.trigger) for x in self.transitions})!=len(self.transitions):
            raise ValueError("V3_15_DUPLICATE_EDGE_SEMANTICS")
        if any(x.terminal for x in self.states if x.state_id!=self.beats[-1].state_id
               and x.state_id in {b.state_id for b in self.beats[:-1]}):
            raise ValueError("V3_15_TRACE_PASSES_THROUGH_TERMINAL")
        if not states[self.beats[-1].state_id].terminal:
            raise ValueError("V3_15_TERMINAL_BEAT_REQUIRED")
        for prev,now in zip(self.beats,self.beats[1:]):
            edge=edges.get(now.via_transition_id)
            if edge is None or edge.source_id!=prev.state_id or edge.target_id!=now.state_id or edge.trigger!=now.trigger:
                raise ValueError("V3_15_TRACE_TOPOLOGY_OR_TRIGGER_MISMATCH")
            if states[prev.state_id].terminal:
                raise ValueError("V3_15_TERMINAL_HAS_FOLLOWUP")
        if any(e.source_id==e.target_id for e in self.transitions):
            raise ValueError("V3_15_SELF_LOOP_NOT_RENDERED_IN_THIS_BOUND")
        outgoing={s:[] for s in states}
        for e in self.transitions:outgoing[e.source_id].append(e.target_id)
        reached={self.initial_state_id}
        q=[self.initial_state_id]
        while q:
            for child in outgoing[q.pop(0)]:
                if child not in reached:reached.add(child);q.append(child)
        if reached!=set(states):
            raise ValueError("V3_15_UNREACHABLE_STATE")
        if any(e.source_id in {s.state_id for s in self.states if s.terminal} for e in self.transitions):
            raise ValueError("V3_15_TERMINAL_HAS_OUTGOING_TRANSITION")
        def has_cycle():
            colors={}
            def visit(node):
                colors[node]=1
                for target in outgoing[node]:
                    if colors.get(target)==1 or colors.get(target,0)==0 and visit(target):
                        return True
                colors[node]=2
                return False
            return visit(self.initial_state_id)
        branch=any(len(e)>1 for e in outgoing.values())
        if not branch and not has_cycle():
            raise ValueError("V3_15_NOT_A_DISTINCT_STATE_MACHINE_USE_PROCESS_FLOW")
        return self


class StateMachineRenderEvidence(V3Model):
    renderer_version:Literal["v3-15-state-machine-blackboard-v1"]=VERSION
    family:Literal["STATE_MACHINE"]="STATE_MACHINE"
    video_path:str
    video_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    source_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    topic_query_sha256:str=Field(pattern=r"^[0-9a-f]{64}$")
    frame_count:StrictInt=Field(gt=0)
    fps:StrictInt=Field(ge=12)
    decoded_beat_indices:tuple[int,...]
    decoded_anchor_mae:tuple[float,...]
    decoded_state_roi_delta:tuple[float,...]
    decoded_within_beat_motion:tuple[float,...]
    stable_node_centers:dict[str,tuple[int,int]]
    status:Literal["BOUNDED_ACTUAL_H264_STATE_MACHINE_PASS"]="BOUNDED_ACTUAL_H264_STATE_MACHINE_PASS"
    publication_blocked:Literal[True]=True
    audio_sync:Literal["UNMEASURED"]="UNMEASURED"
    human_lesson_quality:Literal["UNMEASURED"]="UNMEASURED"


def certify_source(spec:StateMachineLesson,*,topic)->None:
    """Verify demand provenance from immutable LearnFlowBench topic, no name heuristics."""
    if topic.topic_id!=spec.topic_id or topic.domain.value!="cs":
        _fail("FROZEN_DEMAND_TOPIC_MISMATCH")
    if compute_content_hash({"topic_id":topic.topic_id,"query":topic.query})!=spec.topic_query_sha256:
        _fail("FROZEN_QUERY_DRIFT")
    if spec.topic_id not in ELIGIBLE_PREREG_TOPICS:
        _fail("NO_PREREG_EVIDENCE_FOR_EXPANSION")
    if spec.topic_id=="lfb-006-cs" and "http request lifecycle" not in topic.query.casefold():
        _fail("HTTP_TOPIC_SCOPE_MISMATCH")
    if spec.topic_id=="lfb-016-cs" and "distributed transactions" not in topic.query.casefold():
        _fail("TRANSACTION_TOPIC_SCOPE_MISMATCH")


def stable_layout(spec:StateMachineLesson,profile:SequenceRenderProfile)->dict[str,tuple[int,int]]:
    # Renderer owns circular topology. Sorting preserves ID mapping if input reordered.
    ordered=sorted(x.state_id for x in spec.states)
    n=len(ordered)
    cx=profile.width*.5;cy=profile.height*.54
    # Keep every node entirely below header divider and above the event/footer strip.
    rx=profile.width*.32;ry=profile.height*.24
    return {name:(round(cx+rx*math.cos(2*math.pi*i/n-math.pi/2)),
                  round(cy+ry*math.sin(2*math.pi*i/n-math.pi/2)))
            for i,name in enumerate(ordered)}


def _draw_arrow(draw,a,b,*,color,width:int,profile:SequenceRenderProfile):
    import math
    dx=b[0]-a[0];dy=b[1]-a[1];dist=math.hypot(dx,dy)
    if dist<1:_fail("DEGENERATE_EDGE_LAYOUT")
    ux=dx/dist;uy=dy/dist
    start=(a[0]+ux*48*profile.width/960,a[1]+uy*28*profile.height/540)
    end=(b[0]-ux*48*profile.width/960,b[1]-uy*28*profile.height/540)
    draw.line((start,end),fill=color,width=width)
    head=11*profile.width/960
    orth=(-uy,ux)
    draw.polygon([end,(end[0]-ux*head+orth[0]*head*.5,end[1]-uy*head+orth[1]*head*.5),
                       (end[0]-ux*head-orth[0]*head*.5,end[1]-uy*head-orth[1]*head*.5)],fill=color)


def draw_state_frame(spec:StateMachineLesson,beat_index:int,progress:float,
                     profile:SequenceRenderProfile)->Image.Image:
    if not 0<=beat_index<len(spec.beats) or not 0<=progress<=1:
        _fail("FRAME_OUT_OF_TIMELINE")
    w,h=profile.width,profile.height
    sx=w/960;sy=h/540
    im=Image.new("RGB",(w,h),BLACK);d=ImageDraw.Draw(im)
    title=cmu_font(round(29*sy));label=cmu_font(round(21*sy))
    small=cmu_font(round(16*sy))
    d.text((round(47*sx),round(24*sy)),"STATE MACHINE",font=title,fill=WHITE)
    d.text((round(49*sx),round(71*sy)),spec.concept_title,font=small,fill=GREY)
    d.line((round(46*sx),round(103*sy),round(913*sx),round(103*sy)),fill=FAINT,width=2)
    centers=stable_layout(spec,profile)
    current=spec.beats[beat_index]
    prev=spec.beats[max(0,beat_index-1)]
    active_edge=current.via_transition_id
    for edge in spec.transitions:
        picked=edge.transition_id==active_edge
        a=centers[edge.source_id];b=centers[edge.target_id]
        _draw_arrow(d,a,b,color=CYAN if picked else FAINT,width=4 if picked else 2,profile=profile)
    # A moving semantic token on the ACTIVE transition (not merely flashing a title).
    if active_edge is not None:
        a=centers[prev.state_id];b=centers[current.state_id]
        # Advance through a full visible trajectory within each beat.
        px=a[0]+(b[0]-a[0])*progress;py=a[1]+(b[1]-a[1])*progress
        r=round(8*sx)
        d.ellipse((round(px-r),round(py-r),round(px+r),round(py+r)),fill=YELLOW)
    for state in spec.states:
        x,y=centers[state.state_id]
        halfw=round(77*sx);halfh=round(26*sy)
        fill=(20,42,36) if state.state_id==current.state_id else (16,19,23)
        outline=GREEN if state.state_id==current.state_id else GREY
        d.rounded_rectangle((x-halfw,y-halfh,x+halfw,y+halfh),
                            radius=round(12*sx),fill=fill,outline=outline,
                            width=3 if state.state_id==current.state_id else 2)
        txt=state.label
        assert_fits(d,txt,label,halfw*2-15,role="STATE_MACHINE_STATE_LABEL")
        bbox=d.textbbox((0,0),txt,font=label)
        d.text((round(x-(bbox[2]-bbox[0])/2),round(y-(bbox[3]-bbox[1])/2-3*sy)),
               txt,font=label,fill=WHITE)
        if state.terminal:
            d.ellipse((x+halfw-9,y-halfh-9,x+halfw+4,y-halfh+4),fill=GREEN)
    active_text=("Begin: "+current.state_id if active_edge is None
                 else "Transition: "+current.trigger)
    assert_fits(d,active_text,small,round(700*sx),role="STATE_MACHINE_TRIGGER")
    d.text((round(51*sx),round(476*sy)),active_text,font=small,fill=CYAN)
    d.text((round(757*sx),round(476*sy)),
           f"{beat_index+1} / {len(spec.beats)}",font=small,fill=GREY)
    return im


def _real_frame(video:Path,frame:int,profile:SequenceRenderProfile)->Image.Image:
    # Exact ordinal frame selection avoids timestamp seek drift at the last frame.
    from .temporal_demo_renderer import _decode_exact_frame
    return _decode_exact_frame(video,frame,profile)


def verify_state_machine_video(*,spec:StateMachineLesson,topic,video_path:str|Path,
                               evidence:StateMachineRenderEvidence,
                               profile:SequenceRenderProfile)->None:
    certify_source(spec,topic=topic)
    path=Path(video_path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size<1000:
        _fail("VIDEO_MISSING_OR_UNSAFE")
    if (hashlib.sha256(path.read_bytes()).hexdigest()!=evidence.video_sha256 or
        compute_content_hash(spec.model_dump(mode="json"))!=evidence.source_sha256 or
        spec.topic_query_sha256!=evidence.topic_query_sha256):
        _fail("VIDEO_OR_SOURCE_FINGERPRINT_MISMATCH")
    count=profile.frames_per_step()*len(spec.beats)
    if evidence.frame_count!=count or evidence.fps!=profile.fps:
        _fail("VIDEO_FRAME_PROFILE_MISMATCH")
    probe=subprocess.run(["ffprobe","-v","error","-show_streams",
                          "-of","json",str(path)],capture_output=True,text=True,timeout=25,check=True)
    streams=json.loads(probe.stdout)["streams"]
    videos=[x for x in streams if x.get("codec_type")=="video"]
    if len(videos)!=1 or any(x.get("codec_type")=="audio" for x in streams):
        _fail("UNAUTHORIZED_AUDIO_OR_VIDEO_STREAM")
    v=videos[0]
    if v.get("codec_name")!="h264" or int(v.get("width",0))!=profile.width or int(v.get("height",0))!=profile.height:
        _fail("UNEXPECTED_H264_PROFILE")
    if int(v.get("nb_frames",0))!=count:
        _fail("VIDEO_LENGTH_NOT_VERIFIED")
    if evidence.stable_node_centers!=stable_layout(spec,profile):
        _fail("NODE_IDENTITY_LAYOUT_MISMATCH")
    if len(evidence.decoded_beat_indices)!=len(spec.beats):
        _fail("MISSING_BEAT_ANCHORS")
    roi=(round(profile.width*.09),round(profile.height*.15),
         round(profile.width*.91),round(profile.height*.78))
    decoded=[]
    for i,idx in enumerate(evidence.decoded_beat_indices):
        expected_idx=i*profile.frames_per_step()+round(profile.frames_per_step()*.7)
        if idx!=expected_idx:_fail("ANCHOR_TIME_MUTATED")
        actual=_real_frame(path,idx,profile)
        ideal=draw_state_frame(spec,i,(idx%profile.frames_per_step()+.5)/profile.frames_per_step(),profile)
        err=_mean_absolute_error(actual,ideal,rect=roi)
        if err>8.0:_fail("SEMANTIC_ANCHOR_PIXELS_WRONG")
        decoded.append(actual)
    diffs=[_mean_absolute_error(a,b,rect=roi) for a,b in zip(decoded,decoded[1:])]
    if any(d<0.5 for d in diffs):
        _fail("SEMANTIC_ACTIVE_STATE_NOT_VISIBLE")
    inner=[]
    for i in range(1,len(spec.beats)):
        n=profile.frames_per_step()
        a=_real_frame(path,i*n+max(1,round(n*.15)),profile)
        b=_real_frame(path,i*n+min(n-1,round(n*.8)),profile)
        d=_mean_absolute_error(a,b,rect=roi)
        if d<0.06:_fail("NO_TRANSITION_MOTION_IN_MP4")
        inner.append(d)
    if (len(evidence.decoded_anchor_mae)!=len(decoded) or
        len(evidence.decoded_state_roi_delta)!=len(diffs) or
        len(evidence.decoded_within_beat_motion)!=len(inner)):
        _fail("EVIDENCE_CARDINALITY_MISMATCH")
    for calculated,recorded in zip(diffs,evidence.decoded_state_roi_delta):
        if abs(round(calculated,3)-recorded)>0.002:_fail("FORGED_VISIBLE_STATE_DELTA")
    for calculated,recorded in zip(inner,evidence.decoded_within_beat_motion):
        if abs(round(calculated,3)-recorded)>0.002:_fail("FORGED_IN_BEAT_MOTION")
    for i,actual in enumerate(decoded):
        expected=draw_state_frame(spec,i,(evidence.decoded_beat_indices[i]%profile.frames_per_step()+.5)/profile.frames_per_step(),profile)
        err=_mean_absolute_error(actual,expected,rect=roi)
        if abs(round(err,3)-evidence.decoded_anchor_mae[i])>.002:_fail("FORGED_ANCHOR_MAE")


def render_state_machine(*,spec:StateMachineLesson,topic,
                         output_path:str|Path,
                         profile:SequenceRenderProfile=SequenceRenderProfile(
                             width=640,height=360,fps=12,seconds_per_step=.8
                         ))->StateMachineRenderEvidence:
    certify_source(spec,topic=topic)
    count=profile.frames_per_step()*len(spec.beats)
    if count>MAX_FRAMES:_fail("FRAME_BUDGET_EXCEEDED")
    path=Path(output_path).absolute()
    if path.suffix!=".mp4" or path.exists() or path.is_symlink() or not path.parent.is_dir():
        _fail("UNSAFE_VIDEO_DESTINATION")
    if any(p.is_symlink() for p in (path.parent,*path.parent.parents)):
        _fail("SYMLINK_OUTPUT_FORBIDDEN")
    source=compute_content_hash(spec.model_dump(mode="json"))
    tmp=path.with_name("."+path.stem+"."+source[:12]+".part.mp4")
    if tmp.exists():_fail("TEMP_FILE_CONFLICT")
    cmd=["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
         "-f","rawvideo","-pix_fmt","rgb24","-s:v",f"{profile.width}x{profile.height}",
         "-r",str(profile.fps),"-i","pipe:0","-an","-c:v","libx264","-preset","ultrafast",
         "-crf","20","-pix_fmt","yuv420p","-movflags","+faststart","-map_metadata","-1",str(tmp)]
    proc=None
    try:
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        assert proc.stdin is not None
        n=profile.frames_per_step()
        for idx in range(count):
            beat,step=divmod(idx,n)
            im=draw_state_frame(spec,beat,(step+.5)/n,profile)
            proc.stdin.write(im.tobytes())
        proc.stdin.close()
        assert proc.stderr is not None
        err=proc.stderr.read()
        if proc.wait(timeout=90)!=0 or not tmp.is_file() or tmp.stat().st_size<1000:
            _fail("H264_ENCODE_FAILED:"+err[-120:].decode(errors="replace"))
        # Do NOT link to target until decoded pixels and graph state pass QA.
    except Exception:
        if proc and proc.poll() is None:proc.kill()
        if proc:proc.wait()
        tmp.unlink(missing_ok=True)
        raise
    try:
        anchors=tuple(i*n+round(n*.7) for i in range(len(spec.beats)))
        roi=(round(profile.width*.09),round(profile.height*.15),
             round(profile.width*.91),round(profile.height*.78))
        frames=[_real_frame(tmp,k,profile) for k in anchors]
        errors=tuple(round(_mean_absolute_error(frame,
            draw_state_frame(spec,i,(anchors[i]%n+.5)/n,profile),rect=roi),3)
            for i,frame in enumerate(frames))
        deltas=tuple(round(_mean_absolute_error(a,b,rect=roi),3)
                     for a,b in zip(frames,frames[1:]))
        within=[]
        for i in range(1,len(spec.beats)):
            a=_real_frame(tmp,i*n+max(1,round(n*.15)),profile)
            b=_real_frame(tmp,i*n+min(n-1,round(n*.8)),profile)
            within.append(round(_mean_absolute_error(a,b,rect=roi),3))
        result=StateMachineRenderEvidence(
            video_path=str(path),
            video_sha256=hashlib.sha256(tmp.read_bytes()).hexdigest(),
            source_sha256=source,topic_query_sha256=spec.topic_query_sha256,
            frame_count=count,fps=profile.fps,
            decoded_beat_indices=anchors,decoded_anchor_mae=errors,
            decoded_state_roi_delta=deltas,decoded_within_beat_motion=tuple(within),
            stable_node_centers=stable_layout(spec,profile),
        )
        verify_state_machine_video(spec=spec,topic=topic,video_path=tmp,evidence=result,profile=profile)
        try:os.link(tmp,path)
        except FileExistsError as exc:raise SemanticContractError("V3_15_OUTPUT_RACE") from exc
        return result
    finally:
        tmp.unlink(missing_ok=True)
