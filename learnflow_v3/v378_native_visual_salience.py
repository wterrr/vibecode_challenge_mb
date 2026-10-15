"""V3-78 independent real-Manim telemetry / decoded-H264 visual salience audit.

This audit does NOT label pedagogical success or video beauty based on an
invented numerical score. Bounding boxes are ACTUAL construct-time Manim CMU
glyph/shape extents conservatively enlarged by 1.07 for Indicate, NOT real
per-pixel foreground mask or exact per-frame mutated geometry.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
from statistics import median

import numpy as np

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.process_edge_visual_qa import _frame
from learnflow_v3.v376_native_runtime_readability import (
    read_runtime,validate_telemetry,contrast_ratio,
)
from learnflow_v3.visual_quality_system import BG

WIDTH=1280
HEIGHT=720
UNDERREADABLE_GROUP_HEIGHT_PX=24.0
FRACS=(.10,.20,.30,.40,.50,.60,.70,.80,.90)
DARK_BG=np.array(list(bytes.fromhex(BG[1:])),dtype=np.int16)


def need(condition,code):
    if not condition:
        raise Blocked("V378_"+code)


def is_content(o):
    return (isinstance(o.get("id"),str) and
            ":" in o["id"] and o.get("role") in ("shape","text") and
            isinstance(o.get("opacity"),(int,float)) and
            o["opacity"]>=.94)


def content_rects(row):
    rects=[]
    for item in row["objects"]:
        if not is_content(item):continue
        r=item["bbox_px"]
        need(isinstance(r,list) and len(r)==4 and
             all(type(v) in (int,float) and math.isfinite(v) for v in r),
             "INVALID_CONTENT_RECT")
        x0,y0,x1,y1=r
        need(0<=x0<x1<=WIDTH and 0<=y0<y1<=HEIGHT,
             "CONTENT_OUT_OF_FRAME")
        rects.append((x0,y0,x1,y1))
    return rects


def union_area(rects):
    """Exact AABB union area, no simple sum/double-count of overlapping text."""
    if not rects:return 0.
    xs=sorted(set([x for a,b,c,d in rects for x in (a,c)]))
    area=0.
    for x0,x1 in zip(xs,xs[1:]):
        if x1<=x0:continue
        ys=sorted((b,d) for a,b,c,d in rects if a<x1 and c>x0)
        if not ys:continue
        lo,hi=ys[0];filled=0.
        for ya,yb in ys[1:]:
            if ya<=hi:hi=max(hi,yb)
            else:filled+=hi-lo;lo,hi=ya,yb
        filled+=hi-lo
        area+=(x1-x0)*filled
    need(0<=area<=WIDTH*HEIGHT+1e-5,"UNION_AREA_OVERFLOW")
    return area


def percentile(values,fraction):
    need(bool(values) and 0<=fraction<=1,"INVALID_PERCENTILE_DATA")
    v=sorted(values)
    return v[min(len(v)-1,int(round((len(v)-1)*fraction)))]


def tally_runtime(rows,frames):
    # Reuse V3-76's exact declared identity, bounding-box, WCAG provenance
    # validation before introducing any new visual-statistics layer.
    native=validate_telemetry(rows,frames)
    need(not native["actual_glyph_shape_intersections"],"UPSTREAM_ACTUAL_MOBJECT_COLLISION")
    need(not native["contrast_defects"],"UPSTREAM_SVG_GLYPH_CONTRAST")
    need(len(rows)>=100,"INSUFFICIENT_RUNTIME_OBSERVATIONS")
    areas=[];active=[];heights={};empty_len=longest=0
    for row in rows:
        rects=content_rects(row)
        active.append(len(rects))
        areas.append(union_area(rects)/(WIDTH*HEIGHT))
        empty_len=0 if rects else empty_len+1
        longest=max(longest,empty_len)
        for o in row["objects"]:
            if is_content(o) and o["role"]=="text":
                need(o.get("color_source")=="CONSTRUCT_TIME_SVG_LEAF_FILL" and
                     bool(o.get("glyph_rgbs")),"TEXT_NATIVE_GLYPH_COLOR_MISSING")
                height=o["bbox_px"][3]-o["bbox_px"][1]
                # retain worst observed text group size per identity
                heights[o["id"]]=min(height,heights.get(o["id"],height))
    need(heights,"NO_PEDAGOGICAL_GLYPH_GROUPS")
    need(sum(bool(x) for x in active)>=len(active)*.8,
         "TOO_FEW_CONTENT_FRAMES_FOR_RELIABLE_AUDIT")
    text_rows=[{"id":k,"native_bbox_height_px":round(h,2),
                "at_risk_in_half_resolution":h<UNDERREADABLE_GROUP_HEIGHT_PX}
               for k,h in sorted(heights.items())]
    return {
        "runtime_ticks":len(rows),"native_frames":frames,
        "runtime_to_encoded_frame_identity":"APPROXIMATE_NOT_1_TO_1",
        "native_glyph_qa":native,
        "content_visible_fraction_of_ticks":
            round(sum(bool(v) for v in active)/len(active),5),
        "longest_chrome_only_streak_ticks":longest,
        "longest_chrome_only_streak_approx_seconds":
            round(longest/15,3),
        "scene_owned_objects_per_tick_median":median(active),
        "bbox_union_area_fraction_median":round(median(areas),6),
        "bbox_union_area_fraction_p10":round(percentile(areas,.10),6),
        "bbox_union_area_fraction_p90":round(percentile(areas,.90),6),
        "effective_native_text_groups":text_rows,
        "text_groups_below_24px_native":
            sum(x["at_risk_in_half_resolution"] for x in text_rows),
        "bbox_semantics":"CONSTRUCT_TIME_CMU_GROUP_RESERVATION_1P07_NOT_ACTUAL_FILLED_PIXELS",
        "visual_density_is_learning_quality":"NO"}


def pixel_witnesses(movie,rows,frames):
    need(movie.is_file() and movie.stat().st_size>40000,"MISSING_NATIVE_H264")
    witnesses=[]
    for frac in FRACS:
        pos=min(frames-1,max(1,int(frac*(frames-1))))
        sample=rows[min(len(rows)-1,int(frac*(len(rows)-1)))]
        rects=content_rects(sample)
        pixels=_frame(movie,pos)
        need(isinstance(pixels,np.ndarray) and pixels.shape==(HEIGHT,WIDTH,3),
             "NATIVE_DECODED_PIXELS_BAD_DIMENSIONS")
        foreground=0;total=0
        for x0,y0,x1,y1 in rects:
            a,b=max(0,int(x0)),max(0,int(y0))
            c,d=min(WIDTH,int(math.ceil(x1))),min(HEIGHT,int(math.ceil(y1)))
            if c<=a or d<=b:continue
            roi=pixels[b:d,a:c].astype(np.int16)
            pixel_diff=np.max(np.abs(roi-DARK_BG),axis=2)
            foreground+=int(np.count_nonzero(pixel_diff>26))
            total+=pixel_diff.size
        witnesses.append({
            "sample_fraction":frac,
            "decoded_native_frame_idx":pos,
            "pixel_sha256":hashlib.sha256(pixels.tobytes()).hexdigest(),
            "runtime_tick_idx_used_approximately":sample["seq"],
            "geometry_roi_count":len(rects),
            "foreground_coverage_in_bbox_rois":
                round(foreground/max(1,total),6),
        })
    need(len(witnesses)==9 and
         sum(x["foreground_coverage_in_bbox_rois"]>0 for x in witnesses)>=6,
         "MISSING_FOREGROUND_IN_ACTUAL_NATIVE_PIXELS")
    return {"decoded_samples":witnesses,
            "alignment":"APPROXIMATE_TIMELINE_FRACTION_MATCH_ONLY",
            "foreground_test":"RGB_MAX_DIFF_GT_26_VS_DARK_BG_IN_CMU_BBOX_ROI",
            "full_frame_semantic_readability":"NOT_CERTIFIED",
            "per_object_pixel_segmentation":"NOT_CERTIFIED"}


def inspect(movie:Path,telemetry:Path,frames:int):
    need(frames>100 and movie.is_file(),"NO_VERSIONED_NATIVE_VIDEO")
    raw=telemetry.read_bytes() if telemetry.is_file() else b""
    need(raw,"NO_RUNTIME_TELEMETRY")
    rows=read_runtime(telemetry)
    measured=tally_runtime(rows,frames)
    native=pixel_witnesses(movie,rows,frames)
    return {
        "checkpoint":"V3-78",
        "status":"PHYSICAL_MEASUREMENTS_REVIEW_READY_NOT_VISUAL_PASS",
        "native_movie_sha256":hashlib.sha256(movie.read_bytes()).hexdigest(),
        "runtime_telemetry_sha256":hashlib.sha256(raw).hexdigest(),
        "native":native,
        "visual_salience_measurements":measured,
        "viewer_visual_rating":"NOT_MEASURED",
        "learning_gain":"NOT_MEASURED",
        "3blue1brown_equivalence":"NOT_CLAIMED",
        "production":"BLOCKED"}
