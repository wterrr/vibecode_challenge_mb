"""V3-84 three-phase, decoded-H264 spatial composition observations.

Pixel-color evidence and host-derived geometry are complementary: colors alone
do not count objects, and host geometry alone cannot prove rendered pixels.
"""
from __future__ import annotations
from hashlib import sha256
import numpy as np

from learnflow_v3.process_edge_visual_qa import _frame
from learnflow_v3.v384_pedagogical_scene_composer import layout_event, require

ROI=(120,295,1160,555)
BEAT_SAMPLES=(1,35,90)


def color_area(frame):
    require(frame.shape==(720,1280,3),"WRONG_NATIVE_FRAME_SIZE")
    x0,y0,x1,y1=ROI
    v=frame[y0:y1,x0:x1].astype("int16")
    r,g,b=v[:,:,0],v[:,:,1],v[:,:,2]
    cyan=(r<165)&(g>155)&(b>150)&(g-r>55)
    orange=(r>185)&(g>95)&(b<168)&(r-b>75)
    return {"cyan":int(cyan.sum()),"orange":int(orange.sum()),
            "physical_total":int(cyan.sum()+orange.sum())}


def native_three_phase(movie, beats, trace):
    require(len(beats)==len(trace["events"]),"SOURCE_BEAT_IDENTITY_CHANGED")
    rows=[]
    for idx,(beat,event) in enumerate(zip(beats,trace["events"],strict=True)):
        p=layout_event(event)
        start=int(beat["frame_start"])
        count=int(beat["frames"])
        require(count>BEAT_SAMPLES[-1]+3,"INSUFFICIENT_BEAT_WINDOW")
        frames=[]
        for shift in BEAT_SAMPLES:
            f=_frame(movie,start+shift)
            frames.append((f,color_area(f)))
        early,mid,late=[r[1] for r in frames]
        require(late["physical_total"]>=3000,"NO_READABLE_PHYSICAL_DIAGRAM")
        require(late["physical_total"]-early["physical_total"]>=1200,
                "STAGE_DOES_NOT_REVEAL_SEMANTIC_UNITS")
        require(late["cyan"]>=650,"MISSING_VERIFIED_CYAN_SOURCE")
        if p["operator"]=="ADD":
            require(late["orange"]>=550,"RIGHT_SOURCE_NOT_VISIBLE_AFTER_MERGE")
        a=frames[0][0][295:555,120:1160].astype("int16")
        z=frames[2][0][295:555,120:1160].astype("int16")
        changed=int((np.max(np.abs(z-a),axis=2)>30).sum())
        require(changed>=1200,"NO_NATIVE_CAUSAL_FRAME_CHANGE")
        # Guard that semantic-color diagrams remain in the verified board,
        # while actual title/captions and result areas are separate.
        # These checks are frame observations, not exact glyph detection.
        snapshots=[]
        for shift,(fr,cc) in zip(BEAT_SAMPLES,frames,strict=True):
            snapshots.append({
                "offset_frames":shift,"frame_index":start+shift,
                "pixel_counts":cc,"decoded_frame_sha256":sha256(fr.tobytes()).hexdigest()
            })
        rows.append({
            "index":idx,"claim_id":event["claim_id"],"operator":p["operator"],
            "host_verified_units":p["count"],
            "native_three_phase_frames":snapshots,
            "pixel_change_early_vs_late":changed,
            "geometry_board_bounds_verified":True,
            "topic_independent_geometry":True,
            "observability":"H264_DECODED_COLOR_CHANGES_NOT_EXACT_OBJECT_OCR",
        })
    return rows
