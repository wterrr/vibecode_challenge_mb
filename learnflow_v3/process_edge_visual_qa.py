"""V3-45-FIX: decoded-pixel temporal QA for typed process edges.

Uses a real H264 frame immediately before/after first Create(edge) at the
physical beat boundary. This checks pixels added *inside* process nodes and
pixels added *between* nodes, unlike semantic-only Graph tests.
No OCR, synthetic images, model calls, or on-video text recognition.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import math
import subprocess
import wave

import numpy as np

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.semantic_scene_wire import SceneWire,process_edge_layout

FPS=15
W,H=1280,720
SCALE=90.0  # Manim 720p: camera 8 world-units high, 1280/14.222 wide.
BASELINE_FAILED_SHA="f9f6c54647fad3797da445b1a8714c9fa967f1f0bf35a9bfa1fd629cc1172a48"


def _pixel(point):
    return (int(round(W/2+point[0]*SCALE)),int(round(H/2-point[1]*SCALE)))


def _mask_sample(points,thickness_px=2):
    mask=np.zeros((H,W),dtype=np.bool_)
    for point in points:
        x,y=_pixel(point)
        if not (3<=x<W-3 and 3<=y<H-3):
            raise Blocked("V345_FIX_ROI_OFFSCREEN")
        mask[max(0,y-thickness_px):min(H,y+thickness_px+1),
             max(0,x-thickness_px):min(W,x+thickness_px+1)]=True
    if not mask.any():
        raise Blocked("V345_FIX_EMPTY_PIXEL_ROI")
    return mask


def _node_inner_edge_mask(node,other):
    dx,dy=other.x-node.x,other.y-node.y
    distance=float(np.hypot(dx,dy))
    if distance<.01:
        raise Blocked("V345_FIX_INVALID_NODE_CENTRES")
    u=np.array((dx/distance,dy/distance))
    half=min((node.width/2)/abs(u[0]) if abs(u[0])>1e-12 else np.inf,
             (node.height/2)/abs(u[1]) if abs(u[1])>1e-12 else np.inf)
    p=np.array((-u[1],u[0]))
    centre=np.array((node.x,node.y))
    boundary=centre+u*half
    # Sample just INSIDE each endpoint node; old centre+buff geometry
    # extended 0.15 world units into the block and fails this test.
    points=[boundary-u*depth+p*offset
            for depth in np.arange(.045,.175,.012)
            for offset in np.arange(-.075,.076,.025)]
    return _mask_sample(points,2)


def _centre_text_mask(node):
    return _mask_sample([
        (node.x+dx,node.y+dy) for dx in np.arange(-.30,.301,.035)
        for dy in np.arange(-.16,.161,.04)
    ],2)


def _gap_mask(path):
    a,b=np.array(path["src"]),np.array(path["dst"])
    vector=b-a
    length=float(np.linalg.norm(vector))
    if length<.3:
        raise Blocked("V345_FIX_NO_VISIBLE_ARROW_GAP")
    normal=np.array((-vector[1],vector[0]))/length
    return _mask_sample([
        a+vector*part+normal*offset
        for part in np.arange(.08,.921,.025)
        for offset in (-.040,0,.040)
    ],2)


def _frame(mp4:Path,index:int):
    # FFmpeg fully decodes source H264 to the requested frame, allowing
    # an independently checkable pixel-level assertion, not scene metadata.
    if index<0:
        raise Blocked("V345_FIX_INVALID_FRAME_INDEX")
    cmd=["ffmpeg","-nostdin","-hide_banner","-v","error","-i",str(mp4),
         "-vf",f"select=eq(n\\,{index})",
         "-vsync","0","-frames:v","1","-f","rawvideo",
         "-pix_fmt","rgb24","-"]
    try:
        p=subprocess.run(cmd,capture_output=True,timeout=45)
    except (OSError,subprocess.TimeoutExpired):
        raise Blocked("V345_FIX_FFMPEG_DECODE_FAILURE") from None
    if p.returncode or len(p.stdout)!=W*H*3:
        raise Blocked("V345_FIX_INVALID_DECODED_FRAME") from None
    return np.frombuffer(p.stdout,dtype=np.uint8).reshape(H,W,3)


def _changed(a,b,mask):
    if a.shape!=b.shape or a.shape!=(H,W,3):
        raise Blocked("V345_FIX_VIDEO_SHAPE_DRIFT")
    return int(np.count_nonzero((np.max(np.abs(a.astype(np.int16)-b.astype(np.int16)),axis=2)>70)&mask))


def inspect_first_edge(mp4:Path,scene:SceneWire,beat_frames:list[int],
                       require_fixed:bool)->dict:
    if scene.family!="ordered_process" or len(beat_frames)!=4 or any(n<20 for n in beat_frames):
        raise Blocked("V345_FIX_PROCESS_FRAME_BUDGET_INVALID")
    first=None
    for beat_index,beat in enumerate(scene.beats):
        for event in beat.events:
            if event.kind=="reveal_edge":
                first=(beat_index,event,beat.events)
                break
        if first:
            break
    if first is None:
        raise Blocked("V345_FIX_MISSING_FIRST_REVEAL_EDGE")
    i,reveal,events=first
    following=next((e for e in events if e.kind=="traverse_edge"
                    and e.target==reveal.target and e.at>reveal.at+reveal.span),None)
    if following is None:
        # Guard expected test window: no other animation before cursor.
        following=next((e for e in events if e.kind=="traverse_edge"
                        and e.target==reveal.target and e.at>=reveal.at+reveal.span),None)
    if following is None:
        raise Blocked("V345_FIX_NO_MATCHED_TRAVERSAL")
    # Choose one frame after arrow Create completes and before the cursor
    # begins, and one frame just after cursor traversal begins.
    n=beat_frames[i]
    beat_start=sum(beat_frames[:i])
    before=beat_start+int(n*reveal.at)-2
    after=beat_start+int(n*(reveal.at+reveal.span+
                              (following.at-reveal.at-reveal.span)/2))
    cursor_at=beat_start+int(n*(following.at+.035))
    if not (0<=before<after<cursor_at<sum(beat_frames)):
        raise Blocked("V345_FIX_UNISOLATED_ANIMATION_TIMES")
    objs={o.id:o for o in scene.graphics}
    edge=objs[reveal.target]
    source,target=objs[edge.src],objs[edge.dst]
    # NOTE the destination mask faces the source.
    masks={"source_inner":_node_inner_edge_mask(source,target),
           "target_inner":_node_inner_edge_mask(target,source),
           "visible_gap":_gap_mask(process_edge_layout(scene)[edge.id]),
           "source_caption":_centre_text_mask(source)}
    prior,complete,moving=(_frame(mp4,k) for k in (before,after,cursor_at))
    src_count=_changed(prior,complete,masks["source_inner"])
    dst_count=_changed(prior,complete,masks["target_inner"])
    gap_count=_changed(prior,complete,masks["visible_gap"])
    cursor_inside=_changed(complete,moving,masks["source_caption"])
    result={
        "first_edge":edge.id,
        "time_isolation_frames":{"before":before,"after":after,"cursor":cursor_at},
        "new_edge_pixels_inside_source_node":src_count,
        "new_edge_pixels_inside_target_node":dst_count,
        "new_edge_pixels_in_open_gap":gap_count,
        "cursor_pixels_changed_on_source_caption":cursor_inside,
        "provenance":"REAL_DECODED_H264_FRAME_DIFF_NOT_SCENE_METADATA",
    }
    if require_fixed:
        if src_count>8 or dst_count>8 or cursor_inside>8:
            raise Blocked("V345_FIX_RENDERED_NODE_EDGE_OR_CURSOR_OVERLAP")
        if gap_count<100:
            raise Blocked("V345_FIX_MISSING_VISIBLE_CONNECTOR")
    else:
        if src_count<20 or dst_count<20 or cursor_inside<12:
            raise Blocked("V345_FIX_FROZEN_NEGATIVE_CONTROL_NOT_REPRODUCED")
    return result


def read_beat_frames(folder:Path)->list[int]:
    result=[]
    for i in range(4):
        file=folder/f"beat_{i}.wav"
        if not file.is_file():
            raise Blocked("V345_FIX_MISSING_PHYSICAL_AUDIO_BEAT")
        try:
            with wave.open(str(file),"rb") as audio:
                result.append(math.ceil(FPS*audio.getnframes()/audio.getframerate())+3)
        except (OSError,wave.Error):
            raise Blocked("V345_FIX_INVALID_PHYSICAL_AUDIO_BEAT") from None
    return result


def inspect_frozen_failure(root:Path,scene:SceneWire)->dict:
    movie=root/"v345-synthetic-process/offline_host_semantic_with_audio.mp4"
    if not movie.is_file() or sha256(movie.read_bytes()).hexdigest()!=BASELINE_FAILED_SHA:
        raise Blocked("V345_FIX_BASELINE_MP4_SHA_DRIFT")
    return inspect_first_edge(movie,scene,read_beat_frames(movie.parent),require_fixed=False)
