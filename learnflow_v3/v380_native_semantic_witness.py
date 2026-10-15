"""V3-80 physical H264 semantic growth witnesses, independent of compiler.

The source receipts authorize expected host-ledger bar geometry/timestamps.
Full encoded H264 frames are decoded independently. This is bounded pixel
evidence of growing scalar area, NOT learner understanding or word alignment.
"""
from __future__ import annotations
from hashlib import sha256
import math
from pathlib import Path
import numpy as np
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.process_edge_visual_qa import _frame

WIDTH=1280;HEIGHT=720;FPS=15;SCALE=90
BACKGROUND=np.array([8,11,17],dtype=np.int16)

def need(ok,why):
    if not ok:raise Blocked("V380_"+why)

def clipped_bar_rect(event):
    center=event.get("bar_center_world")
    height=event.get("physical_bar_height_world")
    width=event.get("bar_width_world")
    need(isinstance(center,list) and len(center)==2 and
         all(type(x) in (float,int) and math.isfinite(x) for x in center)
         and type(height) in (float,int) and math.isfinite(height)
         and type(width) in (float,int) and math.isfinite(width),
         "PHYSICAL_BAR_RECT_UNGROUNDED")
    cx,cy=center
    x0=math.floor(640+(cx-width/2)*SCALE+4)
    x1=math.ceil(640+(cx+width/2)*SCALE-4)
    y0=math.floor(360-(cy+height/2)*SCALE+4)
    y1=math.ceil(360-(cy-height/2)*SCALE-4)
    need(0<=x0<x1<=WIDTH and 0<=y0<y1<=HEIGHT,"BAR_RECT_OFF_CANVAS")
    return x0,y0,x1,y1

def visible_height(pixels,rect):
    need(isinstance(pixels,np.ndarray) and pixels.shape==(HEIGHT,WIDTH,3),
         "H264_DECODE_SHAPE_WRONG")
    x0,y0,x1,y1=rect
    roi=pixels[y0:y1,x0:x1].astype(np.int16)
    dist=np.max(np.abs(roi-BACKGROUND),axis=2)
    rows=np.where(np.count_nonzero(dist>28,axis=1)>=5)[0]
    if not len(rows):return 0
    return int(rows[-1]-rows[0]+1)

def check_growth(movie:Path,events:list,video_frames:int):
    need(movie.is_file() and movie.stat().st_size>40000,"VIDEO_MISSING")
    need(video_frames>100,"NOT_FULL_NATIVE_LESSON")
    witnesses=[]
    for event in events:
        if event["kind"]!="HOST_SCALAR_BAR_GROWTH":continue
        start=event["slot_start_s"];duration=event["slot_duration_s"]
        need(0<=start and .20<=duration<=.81,"UNTRUSTED_ACTION_SLOT")
        early=min(video_frames-1,round(FPS*(start+.13*duration)))
        late=min(video_frames-1,round(FPS*(start+.92*duration)))
        need(late>early,"NO_TEMPORAL_SAMPLING_GAP")
        rect=clipped_bar_rect(event)
        a=_frame(movie,early);b=_frame(movie,late)
        ha,hb=visible_height(a,rect),visible_height(b,rect)
        # 4px is an explicitly physical minimum, not a confidence score;
        # genuine chart growth must occupy additional rows in late frame.
        need(hb>=ha+4,"SCALAR_HEIGHT_NOT_GROWN_IN_H264")
        witnesses.append({
          "scene":event["scene"],"node":event["target"],
          "verified_fact_ref":event["fact_ref"],
          "host_bar_value":event["host_bar_value"],
          "early_video_frame":early,"late_video_frame":late,
          "early_visible_bar_height_px":ha,
          "late_visible_bar_height_px":hb,
          "height_gain_px":hb-ha,
          "physical_roi_rect_px":list(rect),
          "early_frame_sha256":sha256(a.tobytes()).hexdigest(),
          "late_frame_sha256":sha256(b.tobytes()).hexdigest(),
          "attestation":"PHYSICAL_H264_PROGRESSIVE_SCALAR_BAR"}
        )
    need(bool(witnesses),"NO_RECORDED_PHYSICAL_BAR_WITNESS")
    return {"checkpoint":"V3-80",
            "status":"DECODABLE_GROWTH_ATTESTED",
            "physical_bar_witnesses":witnesses,
            "witness_count":len(witnesses),
            "synthetic_source":"FROZEN_HOST_STORYBOARDS",
            "claim":"VISIBLE_GROWTH_ONLY_NOT_MEASURED_STUDENT_LEARNING",
            "causal_relation_trajectory":"HOST_ROUTE_AND_ANIMATION_SOURCE_PROOF_ONLY"}
