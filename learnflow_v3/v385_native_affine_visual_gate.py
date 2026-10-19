"""V3-85 independently decoded graph semantics: axes + line + moving point.

Checks H264 visual pixels in prerecorded graph ROI at exactly 1,35,90
frames per beat, coupled to host-certified graph coordinates. Does NOT claim
line-pixel OCR, learner comprehension, or object physical displacement.
"""
from __future__ import annotations
from hashlib import sha256

import numpy as np
from learnflow_v3.process_edge_visual_qa import _frame
from learnflow_v3.v385_affine_visual_semantics import need,role_contract

ROI=(160,270,1120,565)
SAMPLES=(1,35,90)


def spectrum(f):
    need(f.shape==(720,1280,3),"WRONG_NATIVE_H264_DIMENSION")
    x0,y0,x1,y1=ROI
    arr=f[y0:y1,x0:x1].astype("int16")
    r,g,b=arr[:,:,0],arr[:,:,1],arr[:,:,2]
    turquoise=(r<165)&(g>155)&(b>150)&(g-r>55)
    gold=(r>170)&(g>130)&(b<165)&((r-b)>50)
    salmon=(r>190)&(g>90)&(b<175)&((r-b)>80)
    grey=(r>110)&(g>125)&(b>140)&(np.abs(r-g)<40)&(np.abs(g-b)<45)
    return {"curve_cyan":int(turquoise.sum()),
            "rise_gold":int(gold.sum()),
            "point_orange":int(salmon.sum()),
            "axes_neutral":int(grey.sum())}


def native_affine_witness(movie,beat_rows,trace,role):
    need(len(beat_rows)==len(trace["events"])==2,"BEAT_COUNT_MISMATCH")
    proof=[]
    for i,(beat,event) in enumerate(zip(beat_rows,trace["events"],strict=True)):
        start=int(beat["frame_start"])
        need(int(beat["frames"])>SAMPLES[-1]+10,
             "NOT_ENOUGH_FRAMES_TO_SEE_GRAPH")
        captures=[]
        for shift in SAMPLES:
            frame=_frame(movie,start+shift)
            captures.append((frame,spectrum(frame)))
        early,mid,late=[x[1] for x in captures]
        need(late["curve_cyan"]>=420,"GRAPH_LINE_NOT_RENDERED")
        need(late["axes_neutral"]>=600,"GRAPH_AXES_NOT_VISIBLE")
        need(late["rise_gold"]>=80,"AFFINE_RATE_TRIANGLE_NOT_SHOWN")
        e=captures[0][0][ROI[1]:ROI[3],ROI[0]:ROI[2]].astype("int16")
        l=captures[-1][0][ROI[1]:ROI[3],ROI[0]:ROI[2]].astype("int16")
        changed=int((np.max(np.abs(l-e),axis=2)>35).sum())
        need(changed>=850,"STATIC_CHART_WITHOUT_SEMANTIC_EVENT")
        need(late["curve_cyan"]>early["curve_cyan"]+300,
             "NO_TEMPORAL_CURVE_REVEAL")
        need(event["claim_id"]==role["claim_ids"][i],
             "NARRATION_TO_SOURCE_GRAPH_CLAIM_DRIFT")
        proof.append({
            "index":i,"claim_id":event["claim_id"],
            "semantic_graph_role":role["role"],
            "graph_point_final":role["points"]["rate_end"] if i==0 else role["points"]["final"],
            "graph_motion_represents":"PLOTTED_VALUE_NOT_PHYSICAL_DISPLACEMENT",
            "native_graph_change_pixels":changed,
            "sampled_frames":[{
                "offset":offset,"frame":start+offset,
                "physical_pixel_spectrum":stats,
                "decoded_sha256":sha256(frame.tobytes()).hexdigest()
            } for offset,(frame,stats) in zip(SAMPLES,captures,strict=True)],
            "provenance":"HOST_VERIFIED_AFFINE_COORDINATES_PLUS_DECODED_PIXELS_NOT_OCR",
        })
    return proof
