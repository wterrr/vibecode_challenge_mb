"""V3-75 bounded creative SceneGraph -> native Manim visual QA exporter.

Reuse V3-73 per-frame IR ONLY for static conservative node reservations across
scene/beat intervals. This is NOT an exact runtime Manim glyph exporter or
per-pixel match: unsupported move/replace/hide must fail closed; Indicate gets
an enlarged envelope. Edges are checked against third-party node reservations.
Native H264/AAC decoding and V3-54 real pixel samples remain independent.
"""
from __future__ import annotations
import math
from pathlib import Path

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_scene_graph import _edge_route
from learnflow_v3.generalized_temporal_visual_qa import (
    Rect, Object, Frame, validate_timeline, VisualQAError, overlap,
)
from learnflow_v3.creative_visual_quality_gate import inspect_native
from learnflow_v3.creative_manim_runner import sha

SCALE=90.0
REQUIRED_MARGIN=6
ALLOWED_ACTIONS=frozenset({"reveal","connect","emphasize"})
SUPPORTED_KINDS=frozenset({"SHAPE","TEXT","MATH","EQUATION","CHART"})
# Reserve host compiler's bounded Manim widths. Text glyphs are not Manim
# runtime measured: these are conservative ENVELOPES, not literal glyphs.
SIZE={
    "SHAPE":(3.14,1.27,0.),
    "TEXT":(2.86,.72,0.),
    "MATH":(2.86,.72,0.),
    "EQUATION":(2.86,.72,0.),
    "CHART":(2.87,1.79,-.14),
}
# Include Indicate's 1.07 scale in precomputed reserved geometry.
HIGHLIGHT_SCALE=1.07

def need(ok,reason):
    if not ok:raise Blocked("V375_"+reason)

def box(node,coord):
    need(node.kind in SUPPORTED_KINDS, "UNKNOWN_RENDERED_OBJECT_KIND")
    w,h,offset=SIZE[node.kind]
    # Deliberate conservative geometry reservation, not exact glyph bbox.
    w*=HIGHLIGHT_SCALE;h*=HIGHLIGHT_SCALE
    x,y=coord[0]*SCALE+640,360-(coord[1]+offset)*SCALE
    return Rect(x-w*SCALE/2,y-h*SCALE/2,x+w*SCALE/2,y+h*SCALE/2)

def _line_hit(a,b,obstacle,margin=REQUIRED_MARGIN):
    """Exact line segment intersection with padded AABB (not sparse 21 probes)."""
    left,top,right,bottom=obstacle.left-margin,obstacle.top-margin,obstacle.right+margin,obstacle.bottom+margin
    dx=b[0]-a[0];dy=b[1]-a[1]
    lo,hi=0.0,1.0
    for p,q in [(-dx,a[0]-left),(dx,right-a[0]),(-dy,a[1]-top),(dy,bottom-a[1])]:
        if abs(p)<1e-9:
            if q<0:return False
        else:
            t=q/p
            if p<0:lo=max(lo,t)
            else:hi=min(hi,t)
            if lo>hi:return False
    return True

def preflight(story, evidence, layouts, beats) -> dict:
    need(len(beats)==len(story.beats) and all(type(x)==int and x>=25 for x in beats),
         "MISSING_PHYSICAL_BEAT_FRAMES")
    need(2<=len(story.scenes)<=5 and 3<=len(story.beats)<=7,
         "STORYBOARD_UNSUPPORTED")
    seen=set();records=[]
    for scene in story.scenes:
        need(scene.id not in seen and scene.id in layouts,"SCENE_IDENTITY_DRIFT")
        seen.add(scene.id)
        coords=layouts[scene.id]
        byid={n.id:n for n in scene.nodes}
        need(set(coords)==set(byid) and len(byid)==len(scene.nodes),
             "UNEXPORTED_SCENE_OBJECT")
        nodes=[Object(n.id,"box",box(n,coords[n.id]))
               for n in scene.nodes]
        checked={n.object_id:n.rect for n in nodes}
        if len(nodes)<3:
            raise Blocked("V375_TOO_FEW_OBJECTS_TO_CERTIFY")
        for relation in scene.relations:
            need(relation.source in checked and relation.target in checked,
                 "EDGE_WITHOUT_CERTIFIED_OBJECT")
            path=_edge_route(scene,relation,coords)
            need(2<=len(path)<=4,"UNCERTIFIED_EDGE_ROUTE")
            pts=[(640+px*SCALE,360-py*SCALE) for px,py in path]
            for i in range(len(pts)-1):
                for obj_id,rect in checked.items():
                    if obj_id in (relation.source,relation.target):continue
                    need(not _line_hit(pts[i],pts[i+1],rect),
                         "EDGE_INTERSECTS_UNRELATED_VISUAL")
        # Existing V3-73 renderer-agnostic geometry, with conservative node
        # occupancy (not unsupported full-font pixel claims).
        sequence=[b for b in zip(story.beats,beats) if b[0].scene_id==scene.id]
        nframes=sum(n for _,n in sequence)
        need(nframes>=1,"EMPTY_SCENE_NATIVE_TIMELINE")
        for beat,_ in sequence:
            for action in beat.actions:
                need(action.kind in ALLOWED_ACTIONS,
                     "DYNAMIC_ACTION_NO_COMPLETE_EXPORTER")
                need(action.target in byid or any(r.id==action.target
                         for r in scene.relations),
                     "UNEXPORTED_ACTION_TARGET")
        # All possible visual objects reserved at every instant, even if
        # invisible during a reveal. Conservative over-approximation.
        frames=[Frame(i,tuple(nodes)) for i in range(nframes)]
        try:
            report=validate_timeline(frames,expected_frames=nframes)
        except (VisualQAError,ValueError,TypeError) as exc:
            raise Blocked("V375_GENERIC_V373_REJECTED:"+str(exc)[:160]) from None
        records.append({"scene":scene.id,"native_frames_reserved":nframes,
                        "objects":list(checked),"relations":len(scene.relations),
                        "generic_contract":report["geometry"],
                        "reservation":"STATIC_WORST_CASE_INCLUDING_INDICATE_1P07"})
    total=sum(item["native_frames_reserved"] for item in records)
    need(total==sum(beats),"INCOMPLETE_BEAT_FRAME_COVERAGE")
    return {"checkpoint":"V3-75","status":"PASS_DECLARED_CREATIVE_SCENE_RESERVATIONS",
            "scene_count":len(records),"scene_receipts":records,
            "all_physical_frame_times_reserved":total,
            "scope":"CONSERVATIVE_OBJECT_RESERVATION_NOT_RUNTIME_GLYPH_PIXELS",
            "unexported_dynamic_actions":"FAIL_CLOSED",
            "source":"V3-54_ACTUAL_HOST_COMPILER_SCENEGRAPH"}


def native_gate(movie:Path,expected_frames:int,upstream:dict):
    need(upstream.get("checkpoint")=="V3-75" and
         upstream.get("status")=="PASS_DECLARED_CREATIVE_SCENE_RESERVATIONS",
         "MISSING_PRE_RENDER_CERTIFICATION")
    need(movie.is_file() and movie.stat().st_size>40000 and expected_frames>100,
         "MISSING_NATIVE_MOVIE")
    # Existing V3-54 native H264 decoder extracts real pixels from the
    # *actual* Manim/FFmpeg movie. Not a source-only geometric assertion.
    data,_=inspect_native(movie,expected_frames)
    need(len(data["sample_frame_sha256"])==5 and
         data["max_temporal_difference"]>=1.5,
         "NO_REAL_DECODED_VISUAL_EVIDENCE")
    return {"checkpoint":"V3-75","status":"PASS_BOUNDED_NATIVE_CREATIVE_QUALITY_GATE",
            "native_sha256":sha(movie),
            "native_decoded_proxy":data,
            "reserved_source":upstream,
            "actual_manims_text_glyphs":"NOT_CERTIFIED",
            "framewise_rendered_collision_pixels":"NOT_CERTIFIED",
            "video_audio_learning":"UNRATED",
            "production":"BLOCKED"}
