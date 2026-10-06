"""Deterministic Pillow + FFmpeg renderer for LearnFlow V2."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageStat

from learnflow_v2.layout.schema import LayoutGraph, Rect
from learnflow_v2.motion.compiler import CompiledMotionArtifact, PropertyTrack, PropertyTrackKind
from learnflow_v2.motion.enums import MotionTargetKind
from learnflow_v2.render.errors import RenderBackendError, RenderInvalidInputError
from learnflow_v2.render.schema import FrameRenderDigest, RenderedScene, RendererCapabilities, TextRenderEvidence
from learnflow_v2.scenegraph.enums import NodeKind
from learnflow_v2.scenegraph.schema import SceneGraph, SceneNode

BG=(10,16,28); CARD=(28,38,56); PRIMARY=(81,186,246); TEXT=(245,248,252); EDGE=(124,152,182); HIGHLIGHT=(251,191,36)
FONTS=("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf","/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf")
BOLD=("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf")


def _font(size:int,bold:bool=False):
    for path in (BOLD if bold else FONTS):
        if Path(path).is_file():
            return ImageFont.truetype(path,max(1,int(size)))
    raise RenderBackendError("No deterministic TrueType font available")


def _tracks(motion:CompiledMotionArtifact,target_kind:MotionTargetKind,target:str,kind:PropertyTrackKind):
    return tuple(sorted((t for t in motion.tracks if t.target_kind==target_kind and t.target==target and t.property_kind==kind),key=lambda t:(t.start_time,t.track_id)))


def _value(track:PropertyTrack,t:float)->float:
    frames=track.keyframes
    if t<=frames[0].time:return frames[0].value
    if t>=frames[-1].time:return frames[-1].value
    for a,b in zip(frames,frames[1:]):
        if a.time<=t<=b.time:
            ratio=(t-a.time)/(b.time-a.time) if b.time>a.time else 1.0
            return a.value+(b.value-a.value)*ratio
    return frames[-1].value


def _last_value(tracks,t,default,before_first=None):
    if not tracks:return default
    if t<tracks[0].start_time:return tracks[0].keyframes[0].value if before_first is None else before_first
    current=default
    for track in tracks:
        if t<track.start_time:break
        current=_value(track,t)
    return current


def _opacity(motion,node,t):
    tracks=_tracks(motion,MotionTargetKind.NODE,node,PropertyTrackKind.OPACITY)
    if not tracks:return 1.0
    before=tracks[0].keyframes[0].value
    return max(0,min(1,_last_value(tracks,t,1.0,before)))


def _translation(motion,node,t):
    tracks=_tracks(motion,MotionTargetKind.NODE,node,PropertyTrackKind.TRANSLATION_PROGRESS)
    if not tracks:return 1.0,None
    active=tracks[-1]
    for track in tracks:
        if t<=track.end_time+1e-9:
            active=track;break
    return max(0,min(1,_value(active,t) if t>=active.start_time else active.keyframes[0].value)),active


def _emphasis(motion,node,t):
    tracks=_tracks(motion,MotionTargetKind.NODE,node,PropertyTrackKind.EMPHASIS_INTENSITY)
    return max(0,min(1,_last_value(tracks,t,0.0))) if tracks else 0.0


def _edge_progress(motion,rel,t):
    tracks=_tracks(motion,MotionTargetKind.RELATION,rel,PropertyTrackKind.EDGE_DRAW_PROGRESS)
    if not tracks:return 1.0
    if t<tracks[0].start_time:return tracks[0].keyframes[0].value
    return max(0,min(1,_last_value(tracks,t,1.0)))


def _shift(rect:Rect,progress:float,track:PropertyTrack|None)->Rect:
    if track is None or progress>=0.999999:return rect
    remaining=1-progress
    direction=dict(track.metadata).get("direction","left")
    dx=dy=0.0
    if direction=="up":dy=rect.height*.18*remaining
    elif direction=="down":dy=-rect.height*.18*remaining
    elif direction=="right":dx=-rect.width*.18*remaining
    else:dx=-rect.width*.12*remaining
    return Rect(x=max(0,rect.x+dx),y=max(0,rect.y+dy),width=rect.width,height=rect.height)


def _text(node:SceneNode)->str:
    label=(node.label or "").strip(); content=(node.content or "").strip()
    return f"{label}\n{content}" if label and content and label!=content else (label or content or node.id)


def _wrap(draw,text,font,max_width,max_lines):
    source=" ".join(text.strip().split())
    if not source:return [],0
    words=source.split(); lines=[]; current=""
    for word in words:
        candidate=word if not current else current+" "+word
        if draw.textbbox((0,0),candidate,font=font)[2]<=max_width or not current:
            current=candidate
        else:
            lines.append(current)
            if len(lines)>=max_lines:break
            current=word
    if len(lines)<max_lines and current:lines.append(current)
    rendered=" ".join(lines)
    if len(rendered)<len(source) and lines:
        last=lines[-1]
        while last and draw.textbbox((0,0),last+"…",font=font)[2]>max_width:last=last[:-1]
        lines[-1]=(last.rstrip()+"…") if last else "…"
    return lines,min(len(source),len(rendered))


def _draw_node(base:Image.Image,node:SceneNode,rect:Rect,alpha:float,emphasis:float,frame_height:int)->TextRenderEvidence:
    layer=Image.new("RGBA",base.size,(0,0,0,0)); draw=ImageDraw.Draw(layer)
    x0,y0,x1,y1=map(lambda x:int(round(x)),(rect.x,rect.y,rect.right,rect.bottom))
    a=max(0,min(255,int(round(alpha*255))))
    border=tuple(int(PRIMARY[i]*(1-emphasis)+HIGHLIGHT[i]*emphasis) for i in range(3))
    draw.rounded_rectangle((x0,y0,x1,y1),radius=max(5,int(min(rect.width,rect.height)*.06)),fill=(*CARD,int(a*.96)),outline=(*border,a),width=max(1,int(2+emphasis*3)))
    fs=18 if frame_height<=400 else 24
    font=_font(fs,bold=node.kind in {NodeKind.CONCEPT,NodeKind.CALLOUT,NodeKind.CONTAINER})
    pad=max(8,int(min(rect.width,rect.height)*.08)); line_h=int(round(fs*1.28))
    lines,rendered=_wrap(draw,_text(node),font,max(8,int(rect.width)-2*pad),max(1,int((rect.height-2*pad)//line_h)))
    ty=int(rect.center_y-len(lines)*line_h/2)
    for line in lines:
        box=draw.textbbox((0,0),line,font=font); tx=int(rect.center_x-(box[2]-box[0])/2)
        draw.text((tx,ty),line,font=font,fill=(*TEXT,a)); ty+=line_h
    base.alpha_composite(layer)
    source=len(" ".join(_text(node).split()))
    return TextRenderEvidence(element_id=node.id,font_size_px=float(fs),alpha=round(alpha,6),source_chars=source,rendered_chars=rendered,truncated=rendered<source)


def _relation_points(scene:SceneGraph,layout:LayoutGraph,relation_id:str):
    routed=next((e for e in layout.routed_edges if e.edge_id==relation_id),None)
    if routed:return [(p.x,p.y) for p in routed.points]
    rel=next((r for r in scene.relations if r.id==relation_id),None)
    boxes={b.node_id:b.rect for b in layout.boxes}
    if rel is None or rel.source not in boxes or rel.target not in boxes:
        raise RenderInvalidInputError(f"relation '{relation_id}' cannot be rendered")
    return [(boxes[rel.source].center_x,boxes[rel.source].center_y),(boxes[rel.target].center_x,boxes[rel.target].center_y)]


def _partial(points,progress):
    if progress>=1:return points
    if progress<=0:return [points[0]]
    lengths=[math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(points,points[1:])]; total=sum(lengths)
    remain=total*progress; out=[points[0]]
    for i,length in enumerate(lengths):
        if remain>=length:out.append(points[i+1]);remain-=length;continue
        ratio=remain/length if length else 0
        a,b=points[i],points[i+1];out.append((a[0]+(b[0]-a[0])*ratio,a[1]+(b[1]-a[1])*ratio));break
    return out


def _frame(scene:SceneGraph,layout:LayoutGraph,motion:CompiledMotionArtifact,t:float):
    image=Image.new("RGBA",(int(round(layout.frame_width)),int(round(layout.frame_height))),(*BG,255)); draw=ImageDraw.Draw(image,"RGBA")
    for rel in sorted(scene.relations,key=lambda x:x.id):
        pts=_partial(_relation_points(scene,layout,rel.id),_edge_progress(motion,rel.id,t))
        if len(pts)>1:draw.line(pts,fill=(*EDGE,225),width=2)
    nodes={n.id:n for n in scene.nodes}; evidence=[]
    for box in layout.boxes:
        progress,track=_translation(motion,box.node_id,t)
        evidence.append(_draw_node(image,nodes[box.node_id],_shift(box.rect,progress,track),_opacity(motion,box.node_id,t),_emphasis(motion,box.node_id,t),image.height))
    return image.convert("RGB"),tuple(evidence)


def _digest(frame:Image.Image,index:int,t:float):
    rgb=frame.convert("RGB"); raw=rgb.tobytes(); sha=hashlib.sha256(raw).hexdigest(); gray=rgb.convert("L")
    mean=float(ImageStat.Stat(gray).mean[0]); hist=gray.histogram(); total=rgb.width*rgb.height; nonblack=total-sum(hist[:4])
    return FrameRenderDigest(frame_index=index,timestamp=round(t,6),sha256=sha,mean_luma=round(mean,6),non_black_fraction=round(nonblack/total,8))


def _probe(path:Path):
    p=subprocess.run(["ffprobe","-v","error","-show_entries","stream=codec_type,width,height:format=duration","-of","json",str(path)],capture_output=True,text=True,check=False,timeout=30)
    if p.returncode!=0:raise RenderBackendError("ffprobe failed")
    return json.loads(p.stdout)


class PillowFFmpegRenderer:
    def __init__(self,*,fps:int=12,backend_id:str="pillow_ffmpeg_v2"):
        if isinstance(fps,bool) or not isinstance(fps,int) or not 6<=fps<=60:raise RenderInvalidInputError("fps must be integer in [6,60]")
        if not isinstance(backend_id,str) or not backend_id.strip():raise RenderInvalidInputError("backend_id must be non-empty")
        self.fps=fps; self._cap=RendererCapabilities(backend_id=backend_id.strip())

    @property
    def capabilities(self):return self._cap

    def _validate(self,scene,layout,motion):
        scene=SceneGraph.model_validate(scene.model_dump(mode="json")); layout=LayoutGraph.model_validate(layout.model_dump(mode="json")); motion=CompiledMotionArtifact.model_validate(motion.model_dump(mode="json"))
        if not layout.feasible:raise RenderInvalidInputError("renderer refuses infeasible LayoutGraph")
        if len({scene.scene_id,layout.scene_id,motion.scene_id})!=1:raise RenderInvalidInputError("scene IDs must match across artifacts")
        node_ids={n.id for n in scene.nodes}; layout_ids={b.node_id for b in layout.boxes}; rel_ids={r.id for r in scene.relations}
        if node_ids!=layout_ids:raise RenderInvalidInputError(f"LayoutGraph must exactly cover SceneGraph nodes; missing={sorted(node_ids-layout_ids)}, extra={sorted(layout_ids-node_ids)}")
        for tr in motion.tracks:
            if tr.target_kind==MotionTargetKind.NODE and tr.target not in node_ids:raise RenderInvalidInputError("motion targets unknown node")
            if tr.target_kind==MotionTargetKind.RELATION and tr.target not in rel_ids:raise RenderInvalidInputError("motion targets unknown relation")
        return scene,layout,motion

    def render(self,*,scene_graph:SceneGraph,layout_graph:LayoutGraph,motion:CompiledMotionArtifact,output_path:Path,audio_path:Path|None=None)->RenderedScene:
        scene,layout,motion=self._validate(scene_graph,layout_graph,motion)
        out=Path(output_path).resolve(); out.parent.mkdir(parents=True,exist_ok=True)
        if out.suffix.lower()!=".mp4":raise RenderInvalidInputError("output_path must be .mp4")
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):raise RenderBackendError("ffmpeg/ffprobe required")
        audio=Path(audio_path).resolve() if audio_path is not None else None
        if audio is not None and (not audio.is_file() or audio.stat().st_size<=0):raise RenderInvalidInputError("audio_path must be a non-empty file")
        count=max(1,int(round(motion.scene_duration*self.fps))); duration=count/self.fps; samples={0,count//2,count-1}
        sampled=[]; hashes=[]; final_evidence=()
        with tempfile.TemporaryDirectory(prefix="lfv2_render_") as td:
            d=Path(td)
            for i in range(count):
                t=min(i/self.fps,max(0,motion.scene_duration-1/self.fps)); frame,evidence=_frame(scene,layout,motion,t)
                frame.save(d/f"frame_{i:06d}.png",format="PNG",optimize=False,compress_level=6)
                dig=_digest(frame,i,t);hashes.append(dig.sha256)
                if i in samples:sampled.append(dig)
                if i==count-1:final_evidence=evidence
            cmd=["ffmpeg","-y","-loglevel","error","-framerate",str(self.fps),"-i",str(d/"frame_%06d.png")]
            if audio is not None:cmd+=["-i",str(audio),"-map","0:v:0","-map","1:a:0"]
            else:cmd+=["-map","0:v:0"]
            cmd+=["-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-r",str(self.fps),"-threads","1","-map_metadata","-1","-fflags","+bitexact","-flags:v","+bitexact"]
            if audio is not None:cmd+=["-c:a","aac","-b:a","96k","-shortest"]
            cmd+=["-t",f"{duration:.6f}",str(out)]
            p=subprocess.run(cmd,capture_output=True,text=True,check=False,timeout=120)
            if p.returncode!=0 or not out.is_file() or out.stat().st_size<=0:raise RenderBackendError(f"ffmpeg encode failed: {p.stderr[-500:]}")
        data=_probe(out); video=next((s for s in data.get("streams",[]) if s.get("codec_type")=="video"),None)
        if video is None:raise RenderBackendError("encoded scene missing video")
        actual=float(data.get("format",{}).get("duration",duration))
        if int(video.get("width",0))!=int(round(layout.frame_width)) or int(video.get("height",0))!=int(round(layout.frame_height)):raise RenderBackendError("encoded dimensions mismatch")
        if abs(actual-duration)>max(.1,2/self.fps):raise RenderBackendError("encoded duration mismatch")
        audio_duration=None
        if audio is not None:audio_duration=float(_probe(audio).get("format",{}).get("duration",duration))
        return RenderedScene(
            scene_id=scene.scene_id,backend_id=self._cap.backend_id,width=int(video["width"]),height=int(video["height"]),fps=self.fps,
            expected_duration=motion.scene_duration,rendered_duration=round(actual,6),frame_count=count,output_path=str(out),file_size_bytes=out.stat().st_size,
            visual_digest=hashlib.sha256("\n".join(hashes).encode("ascii")).hexdigest(),sampled_frames=tuple(sampled),text_evidence=final_evidence,
            has_audio=audio is not None,audio_duration=round(audio_duration,6) if audio_duration is not None else None,diagnostics=(),
        )
