"""V3-79 bounded, general-purpose pedagogical visual grouping.

This is an opt-in host layout composition pass, not generated model Python.
Tighten horizontal comparison columns while preserving exact scene identity,
node order, vertical extent-aware V3-77 placement, route topology and every
beat/claim. Geometry changes must be validated by the existing V3-75 gate
before the Manim compiler runs, never by painting over a screenshot.
"""
from __future__ import annotations

from copy import deepcopy
import math

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_scene_graph import _edge_route
from learnflow_v3.v375_creative_native_gate import box,_line_hit,SCALE,REQUIRED_MARGIN

COMPARISON_ABS_X=2.40
PREVIOUS_V377_ABS_X=3.05
MAX_SHRINK_RATIO=1.0

def need(ok,code):
    if not ok:raise Blocked("V379_"+code)

def compact(story,layout):
    new=deepcopy(layout);receipts=[]
    for scene in story.scenes:
        if scene.layout!="COMPARISON":continue
        need(scene.id in new,"MISSING_COMPARISON_SCENE")
        coords=new[scene.id]
        need(set(coords)=={n.id for n in scene.nodes},"SCENE_OBJECT_IDENTITY_DRIFT")
        revised={}
        for node in scene.nodes:
            x,y=coords[node.id]
            need(math.isfinite(x) and math.isfinite(y),"NONFINITE_SOURCE_COORD")
            # Compaction is not applied to x outside known V3-77 two-column
            # model; moving arbitrary coordinates would be a semantic change.
            need(abs(abs(x)-PREVIOUS_V377_ABS_X)<.001,
                 "UNRECOGNIZED_OLD_COMPARISON_COLUMN")
            revised[node.id]=(math.copysign(COMPARISON_ABS_X,x),y)
        rects={n.id:box(n,revised[n.id]) for n in scene.nodes}
        for a in scene.nodes:
            ab=rects[a.id]
            for b in scene.nodes:
                if a.id>=b.id:continue
                bb=rects[b.id]
                disjoint=(ab.right+REQUIRED_MARGIN<=bb.left or
                          bb.right+REQUIRED_MARGIN<=ab.left or
                          ab.bottom+REQUIRED_MARGIN<=bb.top or
                          bb.bottom+REQUIRED_MARGIN<=ab.top)
                need(disjoint,"COMPACT_OBJECT_OVERLAP")
        for relation in scene.relations:
            need(relation.source in rects and relation.target in rects,
                 "COMPACT_RELATION_IDENTITY_MISSING")
            route=_edge_route(scene,relation,revised)
            need(2<=len(route)<=4,"UNSUPPORTED_RELATION_ROUTE")
            pixels=[(640+x*SCALE,360-y*SCALE) for x,y in route]
            for a,b in zip(pixels,pixels[1:]):
                for node_id,bb in rects.items():
                    if node_id in (relation.source,relation.target):continue
                    need(not _line_hit(a,b,bb),
                         "COMPACT_RELATION_CROSSES_UNRELATED_VISUAL")
        before=coords.copy()
        new[scene.id]=revised
        receipts.append({
            "scene":scene.id,
            "node_ids":list(revised),
            "old_x_magnitude":PREVIOUS_V377_ABS_X,
            "new_x_magnitude":COMPARISON_ABS_X,
            "old_positions":before,
            "new_positions":revised,
            "relation_count":len(scene.relations),
            "source_conservative_margin_px":REQUIRED_MARGIN,
            "source_compaction":"BOUNDED_NON_COLLIDING_TWO_COLUMN_ONLY"})
    for scene in story.scenes:
        if scene.layout!="COMPARISON":
            need(new[scene.id]==layout[scene.id],"NON_COMPARISON_GEOMETRY_CHANGED")
    return new,{
        "checkpoint":"V3-79",
        "status":"COMPARISON_RECOMPOSED" if receipts else "NO_COMPARISON_IDENTITY_NOOP",
        "scenes":receipts,
        "typography_profile":"CMU_MAXWIDTH_BOUNDED_30_TEXT_27_CHART",
        "bar_width_world":1.2,
        "evidence_claims_modified":False,
        "beat_actions_modified":False,
        "dynamic_pixel_occupancy_certified":False}
