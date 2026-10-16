"""V3-87 real H264 legibility and causal continuity observability.

This observes pixel evidence and host-proven layout. It is not OCR, expert
aesthetic judgement, true ASR timing, or a test of learner understanding.
"""
from __future__ import annotations
from hashlib import sha256
import numpy as np
from learnflow_v3.process_edge_visual_qa import _frame
from learnflow_v3.v385_affine_visual_semantics import need
from learnflow_v3.v386_native_speech_visual_gate import verify_native_phases
from learnflow_v3.v387_readable_affine_continuity import layout, X1, Y1

# Nonoverlapping chart / label regions expressed in decoded 1280x720 pixels.
GRAPH=(210,285,920,520)
RIGHT_CALLOUT=(940,265,1200,425)
ANSWER=(220,566,1070,690)


def _cut(frame,roi):
    x0,y0,x1,y1=roi
    return frame[y0:y1,x0:x1].astype("int16")


def _mask_cyan(crop):
    r,g,b=crop[:,:,0],crop[:,:,1],crop[:,:,2]
    return (r<165)&(g>155)&(b>150)&((g-r)>55)


def _mask_yellow(crop):
    r,g,b=crop[:,:,0],crop[:,:,1],crop[:,:,2]
    return (r>180)&(g>165)&(b<175)&(r-b>65)


def _curve_mean_y(frame):
    local=_mask_cyan(_cut(frame,GRAPH))
    yy,xx=np.nonzero(local)
    need(len(yy)>250,"V387_MISSING_PHYSICAL_CURVE_FOR_TEMPORAL_COMPARISON")
    return float(np.mean(yy))+GRAPH[1],len(yy)


def verify(movie,beat_rows,phases,trace,role):
    base=verify_native_phases(movie,beat_rows,phases,trace,role)
    l=layout(role)
    need(len(base)==6 and len(beat_rows)==6,"V387_VOICE_SEGMENT_COUNT_DRIFT")
    witnesses=[]
    for index,kind in enumerate(("TRANSFORM","INTERPRET","TRANSFORM","INTERPRET")):
        phase_index=(1,2,4,5)[index]
        beat=beat_rows[phase_index]
        begin=int(beat["frame_start"])
        frames=int(beat["frames"])
        before=_frame(movie,begin+1)
        late=_frame(movie,begin+frames-10)
        need(before.shape==late.shape==(720,1280,3),
             "V387_WRONG_REAL_NATIVE_DIMENSIONS")
        if kind=="TRANSFORM":
            callout=_cut(late,RIGHT_CALLOUT)
            readable=int(_mask_yellow(callout).sum())
            need(readable>=160,"V387_NO_LEGIBLE_NUMERIC_CALLOUT_IN_GUTTER")
            late_y,n_late=_curve_mean_y(late)
            shift=None
            if phase_index==4:
                early_y,n_early=_curve_mean_y(before)
                shift=early_y-late_y
                # Real line must visibly translate upward to encode C2's
                # positive initial-value intercept, not just redraw at new y.
                need(shift>=18.0,"V387_C2_INTERCEPT_NOT_VISUALLY_TRANSLATED")
                need(l["vertical_intercept_shift"]>0,
                     "V387_C2_HAS_NO_VERIFIED_INTERCEPT")
            witnesses.append({
                "phase_id":phases[phase_index]["phase_id"],
                "kind":"RIGHT_GUTTER_AND_SLOPE_CONTINUITY",
                "real_gutter_yellow_pixels":readable,
                "decoded_cyan_curve_pixels":n_late,
                "real_curve_centroid_rise_px":shift,
                "physical_late_frame_sha":sha256(late.tobytes()).hexdigest(),
            })
        else:
            frac=_cut(late,ANSWER)
            r,g,b=frac[:,:,0],frac[:,:,1],frac[:,:,2]
            visible=int(((r>155)&(g>155)&(b>155)).sum())
            need(visible>=500,"V387_NOT_READABLE_RESULT_AREA")
            witnesses.append({
                "phase_id":phases[phase_index]["phase_id"],
                "kind":"READABLE_VERIFIED_EQUATION",
                "bright_result_pixels":visible,
                "physical_late_frame_sha":sha256(late.tobytes()).hexdigest(),
            })
    need(len(witnesses)==4,"V387_MISSING_READABILITY_WITNESS")
    return {"original_pcm_phases":base,
            "real_h264_readability_witnesses":witnesses,
            "host_verified_spatial_layout":l,
            "qa_limitations":"PIXEL_AND_GEOMETRY_NOT_OCR_HUMAN_VISUAL_PASS"}
