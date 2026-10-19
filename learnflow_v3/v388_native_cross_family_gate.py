"""V3-88 independent decoded H264 witnesses for two new semantic families.

Frame-color evidence is distinct from host mathematically certified identities.
It cannot measure understanding; true human quality ratings are NEVER invented.
"""
from __future__ import annotations
from hashlib import sha256
import numpy as np

from learnflow_v3.process_edge_visual_qa import _frame
from learnflow_v3.v388_cross_family_planner import check

FRACTION_ROI=(150,280,1130,485)
SEARCH_ROI=(150,255,1130,490)
RESULT_ROI=(230,520,1040,665)


def _rgb(frame,roi):
    check(frame.shape==(720,1280,3),"NATIVE_FRAME_NOT_720P_H264_RGB")
    a,b,c,d=roi
    return frame[b:d,a:c].astype("int16")


def _color_count(frame,roi,name):
    f=_rgb(frame,roi)
    r,g,b=f[:,:,0],f[:,:,1],f[:,:,2]
    if name=="teal":
        mask=(r<165)&(g>155)&(b>150)&((g-r)>55)
    elif name=="yellow":
        mask=(r>175)&(g>150)&(b<175)&(r-b>50)
    else:
        mask=(r>165)&(g>165)&(b>165)
    return int(mask.sum())


def _changed(a,b,roi):
    x=_rgb(a,roi);y=_rgb(b,roi)
    return int((np.max(np.abs(x-y),axis=2)>38).sum())


def verify_native(movie,beat_rows,plan):
    events=plan["scripted_semantic_events"]
    check(len(events)==len(beat_rows) and len(events)>=3,
          "NATIVE_BEAT_COUNT_NOT_VERIFIED")
    witnesses=[]
    for i,(row,ev) in enumerate(zip(beat_rows,events,strict=True)):
        start=int(row["frame_start"]);total=int(row["frames"])
        check(total>=100 and row["index"]==i and
              row["narration"]==ev["narration"] and
              row["claim_ids"]==ev["claim_ids"],
              "PCM_NARRATION_AND_SEMANTIC_EVENT_NOT_SAME")
        before=_frame(movie,start+1)
        late=_frame(movie,start+min(70,total-12))
        roi=(FRACTION_ROI if plan["family"]=="FRACTION_EQUIVALENCE"
             else SEARCH_ROI)
        diff=_changed(before,late,roi)
        data={
            "index":i,"phase":ev["phase"],"source_claim_ids":ev["claim_ids"],
            "audio_frame_range":[start,start+total],
            "semantic_visual_roi":list(roi),
            "before_frame_sha256":sha256(before.tobytes()).hexdigest(),
            "late_frame_sha256":sha256(late.tobytes()).hexdigest(),
            "native_changed_pixels":diff,
            "evidence":"H264_PIXELS_PLUS_HOST_SEMANTICS_NOT_OCR_OR_LEARNER_GAIN",
        }
        if plan["family"]=="FRACTION_EQUIVALENCE":
            n,d,nt,dt=plan["ratio"]
            check(n*dt==nt*d and
                  plan["shade_exact"]==[n,d] and
                  plan["refined_exact"]==[nt,dt],
                  "FRACTION_SHADING_NOT_MATHEMATICALLY_CONSERVED")
            if ev["phase"]=="TRANSFORM":
                teal_before=_color_count(before,FRACTION_ROI,"teal")
                teal_after=_color_count(late,FRACTION_ROI,"teal")
                check(teal_before>1500 and teal_after>1500,
                      "NO_VISIBLE_SAME_WHOLE_SHADE")
                retained=abs(teal_after-teal_before)/teal_before
                check(retained<=.18,"SUBDIVISION_DECEPTIVELY_CHANGED_WHOLE")
                check(diff>=180,"NO_ACTUAL_SUBDIVISION_GUIDES_IN_MP4")
                data.update({"physical_teal_area_before":teal_before,
                             "physical_teal_area_after":teal_after,
                             "relative_teal_change":round(retained,5),
                             "host_exact_fraction_ratio":f"{n}/{d}={nt}/{dt}"})
            elif ev["phase"]=="ORIENT":
                check(_color_count(late,FRACTION_ROI,"teal")>1500,
                      "NO_NATIVE_FRACTION_PICTOGRAM")
            else:
                check(_color_count(late,RESULT_ROI,"white")>350,
                      "NO_EQUIVALENCE_EQUATION_WHEN_SPOKEN")
        else:
            check(plan["trace_replayed_every_step"] is True,
                  "UNVERIFIED_BINARY_SEARCH_LEFTMOST_ORACLE")
            if ev["phase"]=="COMPARE":
                check(diff>=140,"NO_PHYSICAL_SEARCH_STATE_TRANSITION")
                check(0<=ev["low"]<=ev["mid"]<=ev["high"]<len(plan["values"]),
                      "IMPOSSIBLE_NATIVE_MIDPOINT")
                data["host_exact_eliminated_indices"]=ev["discard"]
                data["host_candidate_index"]=ev["candidate"]
            else:
                check(_color_count(late,RESULT_ROI,"yellow")>220,
                      "NO_NATIVE_LEFTMOST_SEARCH_CONCLUSION")
                check(ev["candidate"]==plan["result_index"],
                      "WRONG_SEARCH_TERMINAL_CANDIDATE")
        witnesses.append(data)
    check(len(witnesses)==len(events),"MISSING_INDEPENDENT_RENDERED_STATES")
    return witnesses
