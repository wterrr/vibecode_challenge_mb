"""V3-86 independent H264 semantic *segment* audiovisual timing witness.

All sampled windows are from actual PCM-derived utterance frame ranges.
No fake ASR timestamps or inference about exact spoken word alignment.
"""
from __future__ import annotations
from hashlib import sha256

import numpy as np
from learnflow_v3.process_edge_visual_qa import _frame
from learnflow_v3.v385_native_affine_visual_gate import ROI,spectrum
from learnflow_v3.v385_affine_visual_semantics import need
from learnflow_v3.v386_pedagogical_speech_contract import align_real_wav

RESULT_ROI=(200,558,1080,695)


def _result_ink(frame):
    x0,y0,x1,y1=RESULT_ROI
    crop=frame[y0:y1,x0:x1].astype("int16")
    r,g,b=crop[:,:,0],crop[:,:,1],crop[:,:,2]
    return int(((r>155)&(g>155)&(b>155)).sum())


def verify_native_phases(mp4,beat_rows,phases,trace,role):
    receipts=align_real_wav(phases,beat_rows)
    out=[]
    for i,(beat,phase,receipt) in enumerate(zip(beat_rows,phases,receipts,strict=True)):
        start=receipt["frame_start"]
        size=receipt["frames"]
        need(size>=75,"V386_AUDIO_SEGMENT_NOT_LONG_ENOUGH_FOR_RENDERED_WITNESS")
        shots=[]
        for offset in (1,size//2,size-10):
            frame=_frame(mp4,start+offset)
            shots.append((frame,spectrum(frame),_result_ink(frame),offset))
        first=shots[0]
        last=shots[-1]
        early=first[1];late=last[1]
        if phase["phase_kind"]=="ORIENT":
            need(late["axes_neutral"]>=600,
                 "V386_ORIENTATION_HAS_NO_SEMANTIC_CHART_AXES")
            need(late["axes_neutral"]>early["axes_neutral"]+120,
                 "V386_ORIENTATION_NOT_REVEALED_WITH_AUDIO")
        elif phase["phase_kind"]=="TRANSFORM":
            need(late["curve_cyan"]>=420 and
                 late["curve_cyan"]>early["curve_cyan"]+300,
                 "V386_TRANSFORMATION_MISSING_FROM_VOICED_PHASE")
            need(late["rise_gold"]>=80,
                 "V386_VERIFIED_SLOPE_VISUAL_NOT_PRESENT")
        else:
            need(late["curve_cyan"]>=420,
                 "V386_INTERPRETATION_LOST_GRAPH_EVIDENCE")
            need(last[2]>first[2]+120,
                 "V386_INTERPRETATION_FORMULA_NOT_VISIBLE_WHEN_SPOKEN")
        cropped_first=first[0][ROI[1]:ROI[3],ROI[0]:ROI[2]].astype("int16")
        cropped_last=last[0][ROI[1]:ROI[3],ROI[0]:ROI[2]].astype("int16")
        diff=int((np.max(np.abs(cropped_last-cropped_first),axis=2)>35).sum())
        need(diff>=100,"V386_STATIC_PHASE_NO_PHYSICAL_VISUAL_DECISION")
        need(phase["claim_id"]==trace["events"][i//3]["claim_id"] and
             role["claim_ids"][i//3]==phase["claim_id"],
             "V386_NATIVE_VISUAL_AND_VOICED_CLAIM_MISMATCH")
        out.append({
            "phase_id":phase["phase_id"],
            "semantic_beat_index":phase["semantic_beat_index"],
            "phase_kind":phase["phase_kind"],"claim_id":phase["claim_id"],
            "wav_derived_range":[start,start+size],
            "physical_frame_change_pixels":diff,
            "native_result_text_pixels_early":first[2],
            "native_result_text_pixels_late":last[2],
            "frames":[{
                "frame":start+offset,
                "offset_in_voiced_segment":offset,
                "sha256":sha256(frame.tobytes()).hexdigest(),
                "graph_color_spectrum":spectral,
                "result_ink":result
            } for frame,spectral,result,offset in shots],
            "timing_claim":"TRUE_PCM_SEGMENT_RANGE_NOT_WORD_LEVEL_ALIGNMENT",
            "evidence_kind":"INDEPENDENT_NATIVE_H264_DECODE",
        })
    need(len(out)==6,"V386_UNVERIFIED_VOICED_SEGMENT_COUNT")
    return out
