"""V3-76: fail-closed actual Manim telemetry + independently decoded native pixels.

Snapshots recorded INSIDE pinned Docker from actual Text/Shape Manim
mobjects, not predicted Pillow metrics. Time/frame drift and missing updates
are explicit NO-GO. Pixel checks sample native H264; never claim that sample
checks imply exhaustive pixel collision immunity across the entire video.
"""
from __future__ import annotations

from hashlib import sha256
import json,math
from pathlib import Path
import numpy as np
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.process_edge_visual_qa import _frame
from learnflow_v3.visual_quality_system import BG

BACKGROUND=np.array(list(bytes.fromhex(BG[1:])),dtype=np.float64)
W,H=1280,720
REQUIRED_CONTRAST=4.5
RUNTIME_FILENAME="v376_runtime_geometry.jsonl"

def require(ok,why):
    if not ok:raise Blocked("V376_"+why)

def srgb_lum(rgb):
    rgb=[float(x) for x in rgb]
    require(len(rgb)==3 and all(math.isfinite(x) and 0<=x<=1 for x in rgb),
            "INVALID_COLOR_CHANNELS")
    linear=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb]
    return sum(a*b for a,b in zip(linear,(.2126,.7152,.0722)))

def contrast_ratio(rgb,background=tuple(BACKGROUND/255.)):
    a,b=srgb_lum(rgb),srgb_lum(background)
    return (max(a,b)+.05)/(min(a,b)+.05)

def intersection(a,b,margin=0):
    return a[0]<b[2]+margin and a[2]+margin>b[0] and a[1]<b[3]+margin and a[3]+margin>b[1]

def validate_telemetry(rows,actual_video_frames,*,min_coverage=.94):
    require(isinstance(rows,list) and actual_video_frames>=100,
            "INVALID_TELEMETRY_INPUT")
    require(min_coverage<=len(rows)/actual_video_frames<=1.13,
            "RUNTIME_FRAMES_NOT_ALIGNED_TO_NATIVE_VIDEO")
    collisions=[];contrast=[];glyphs=0;visible_rows=0;unique_ids=set()
    previous_time=None
    for ix,row in enumerate(rows):
        require(isinstance(row,dict) and row.get("seq")==ix and
                isinstance(row.get("objects"),list),"RUNTIME_FRAME_GAP_OR_DUPLICATE")
        time=float(row.get("scene_time_s",-1))
        require(math.isfinite(time) and time>=0 and
                (previous_time is None or time>=previous_time-1e-5),
                "RUNTIME_CLOCK_INVALID")
        previous_time=time
        obs=row["objects"]
        require(len(obs)<=90,"UNBOUNDED_RUNTIME_OBJECTS")
        ids=set()
        visible=[]
        for o in obs:
            name=o.get("id");role=o.get("role")
            require(isinstance(name,str) and role in ("text","shape") and name not in ids,
                    "INVALID_MOBJECT_IDENTITY")
            ids.add(name);unique_ids.add(name)
            bbox=o.get("bbox_px")
            require(isinstance(bbox,list) and len(bbox)==4 and
                    all(type(x) in (int,float) and math.isfinite(x) for x in bbox)
                    and bbox[2]>bbox[0] and bbox[3]>bbox[1],
                    "MANIM_RUNTIME_BBOX_INVALID")
            require(bbox[0]>=-2 and bbox[1]>=-2 and
                    bbox[2]<=W+2 and bbox[3]<=H+2,
                    "RUNTIME_MOBJECT_OUT_OF_FRAME")
            opacity=float(o.get("opacity",-1))
            require(math.isfinite(opacity) and -.02<=opacity<=1.02,
                    "RUNTIME_OPACITY_INVALID")
            if opacity<.94:continue  # explicit fade states not readability targets
            visible.append(o)
            if role=="text":
                glyphs+=1
                # V3-76R1-A3: parent Text RGB can be black even when actual
                # Manim CE SVG leaf glyph paths have visible colored fills.
                # Fail CLOSED if instrumented footage omits glyph fill proof;
                # permit only legacy synthetic test fixtures with no source tag.
                measured=o.get("glyph_rgbs")
                provenance=o.get("color_source")
                if provenance=="CONSTRUCT_TIME_SVG_LEAF_FILL":
                    require(isinstance(measured,list) and 1<=len(measured)<=64,
                            "MISSING_REAL_SVG_GLYPH_COLORS")
                    candidates=measured
                else:
                    require(provenance is None and measured is None,
                            "UNTRUSTED_TEXT_COLOR_PROVENANCE")
                    candidates=[o["rgb"]]
                ratio=min(contrast_ratio(color) for color in candidates)
                contrast.append((ratio,ix,name))
        if visible:visible_rows+=1
        for i,a in enumerate(visible):
            for b in visible[i+1:]:
                if a["role"]!="text" and b["role"]!="text":continue
                # A text label is explicitly contained inside its own outlined node.
                if a.get("parent")==b["id"] or b.get("parent")==a["id"]:
                    continue
                if intersection(a["bbox_px"],b["bbox_px"],margin=2):
                    collisions.append((ix,a["id"],b["id"]))
                    if len(collisions)>=6:break
            if len(collisions)>=6:break
    require(visible_rows/max(1,len(rows))>=.70,"RUNTIME_NO_VISIBLE_OBJECT_EVIDENCE")
    require(glyphs>=30 and len(unique_ids)>=5,
            "INSUFFICIENT_ACTUAL_RUNTIME_GLYPH_TELEMETRY")
    return {"runtime_samples":len(rows),
            "native_frames":actual_video_frames,
            "runtime_to_frame_ratio":round(len(rows)/actual_video_frames,4),
            "actual_runtime_glyph_observations":glyphs,
            "actual_runtime_identity_count":len(unique_ids),
            "min_measured_object_color_contrast":round(min([r for r,_,_ in contrast],default=0),4),
            "contrast_defects":[{"frame":ix,"id":name,"ratio":round(r,3)}
                                for r,ix,name in sorted(contrast) if r<REQUIRED_CONTRAST][:8],
            "actual_glyph_shape_intersections":[{"frame":ix,"a":a,"b":b}
                                                for ix,a,b in collisions],
            "telemetry_coverage":"TRACKED_NATIVE_FRAME_SAMPLES_CONSERVATIVE",
            "bbox_provenance":"ACTUAL_MANIM_CMU_AT_CONSTRUCT_PLUS_1P07_INDICATE_ENVELOPE_NOT_DYNAMIC",
            "full_native_pixel_validation":"NOT_CLAIMED"}

def read_runtime(path:Path,max_lines=4000):
    require(path.is_file() and path.stat().st_size>2000,
            "RUNTIME_TELEMETRY_MISSING")
    rows=[]
    with path.open(encoding="utf-8") as f:
        for i,line in enumerate(f):
            require(i<max_lines,"RUNTIME_TELEMETRY_TOO_MANY_SAMPLES")
            try: rows.append(json.loads(line))
            except (ValueError,TypeError):
                raise Blocked("V376_RUNTIME_TELEMETRY_CORRUPT") from None
    return rows

def check_actual_native_samples(movie:Path,rows:list,frames:int):
    """Independent decoder, 9 time-slice probes, only for stable glyphs.

    A glyph's exact Manim bounding box and RGB are taken from the runtime
    snapshot. At the approximate corresponding encoded frame, witness checks
    that a visible non-background region is present in the bbox. Alignment
    tolerance is constrained; no arbitrary OCR/semantic text claim.
    """
    require(movie.is_file() and movie.stat().st_size>40000,
            "MISSING_PHYSICAL_NATIVE_MP4")
    require(abs(len(rows)-frames)/frames<=.13,"RUNTIME_NATIVE_ALIGNMENT_DRIFT")
    witnesses=[]
    for frac in (.12,.21,.31,.40,.49,.59,.69,.79,.88):
        frame_idx=min(frames-2,max(1,int(round(frames*frac))))
        # Approximate scene frame using actual sequential update ticks;
        # explicit "approx" scope remains in receipt.
        row=rows[min(len(rows)-1,round(frac*(len(rows)-1)))]
        text=[o for o in row["objects"] if o["role"]=="text" and
              o["opacity"]>.98 and o["bbox_px"][2]-o["bbox_px"][0]>10]
        if not text:continue
        px=_frame(movie,frame_idx)
        observed=0
        for obj in text:
            a=obj["bbox_px"]
            x0=max(0,int(a[0])-3);y0=max(0,int(a[1])-3)
            x1=min(W,int(a[2])+4);y1=min(H,int(a[3])+4)
            if x1-x0<4 or y1-y0<4:continue
            roi=px[y0:y1,x0:x1].astype(np.int16)
            background=np.array(BACKGROUND,dtype=np.int16)
            hit=np.max(np.abs(roi-background),axis=2)>26
            if np.count_nonzero(hit)>=max(3,hit.size*.0003):observed+=1
        witnesses.append({"approximate_frame":frame_idx,"tracked_runtime_seq":row["seq"],
                          "runtime_text_count":len(text),"pixel_text_regions_visible":observed,
                          "native_frame_sha256":sha256(px.tobytes()).hexdigest()})
    require(len(witnesses)>=4 and
            sum(w["pixel_text_regions_visible"]>0 for w in witnesses)>=4,
            "ACTUAL_PIXEL_TEXT_WITNESS_MISSING")
    return {"sampled_real_decoded_frames":len(witnesses),"witnesses":witnesses,
            "runtime_to_encoded_frame_correspondence":"APPROXIMATE_NOT_EXACT",
            "actual_native_full_video_ocr":"NOT_DONE"}

def evaluate(movie:Path,telemetry:Path,frames:int):
    rows=read_runtime(telemetry)
    # The REAL renderer may not launder missing effective CMU glyph colors
    # into a PASS using historical synthetic test-only parent RGB fixtures.
    for row in rows:
        for obj in row.get("objects",[]):
            if obj.get("role")=="text":
                require(obj.get("color_source")=="CONSTRUCT_TIME_SVG_LEAF_FILL"
                        and isinstance(obj.get("glyph_rgbs"),list)
                        and bool(obj["glyph_rgbs"]),
                        "NATIVE_TEXT_GLYPH_FILL_PROVENANCE_MISSING")
    measured=validate_telemetry(rows,frames)
    samples=check_actual_native_samples(movie,rows,frames)
    require(not measured["actual_glyph_shape_intersections"],
            "ACTUAL_MANIM_RUNTIME_GLYPH_SHAPE_COLLISION")
    require(not measured["contrast_defects"],
            "ACTUAL_MANIM_TEXT_COLOR_CONTRAST_LT_4P5")
    return {"checkpoint":"V3-76","status":"PASS_BOUNDED_RUNTIME_READABILITY",
            "actual_runtime":measured,"decoded_native_pixels":samples,
            "telemetry_sha256":sha256(telemetry.read_bytes()).hexdigest(),
            "movie_sha256":sha256(movie.read_bytes()).hexdigest(),
            "no_unsupported_actions_certified":True,
            "production":"BLOCKED","learning_gain":"NOT_MEASURED"}
