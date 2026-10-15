"""V3-77 generic host-owned extent-aware COMPARISON scene reflow.

Optimizes real layout source before trusted Manim compilation; never patches
decoded video/screenshot or changes semantic graph identity. Uses V3-75's
existing conservative Manim kind budgets incl. CHART offset and 1.07 Indicate
envelope, not topic-specific or screenshot-derived coordinates.
Opt-in only: historical V3-54/75/76 source defaults and frozen MP4s unchanged.
"""
from __future__ import annotations

from copy import deepcopy
import math

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_scene_graph import _edge_route
from learnflow_v3.v375_creative_native_gate import (
    SIZE, HIGHLIGHT_SCALE, REQUIRED_MARGIN, SCALE, box, _line_hit,
)

LEFT_COL=-3.05
RIGHT_COL=3.05
CONTENT_TOP=2.25
CONTENT_BOTTOM=-2.55
ROW_CLEARANCE_WORLD=0.20
MIN_SAME_COL_SEPARATION=1.55


def need(check:bool, code:str):
    if not check:
        raise Blocked("V377_"+code)


def row_extents(nodes):
    above=below=0.0
    for node in nodes:
        need(node.kind in SIZE,"UNEXPORTED_RENDERER_KIND")
        _,h,offset=SIZE[node.kind]
        radius=h*HIGHLIGHT_SCALE/2
        above=max(above,offset+radius)
        below=max(below,-offset+radius)
    need(above>0 and below>0,"INVALID_KIND_GEOMETRY")
    return above,below


def reflow_comparison(scene):
    """Compute and certify safe new host x/y placements for one scene."""
    need(scene.layout=="COMPARISON","UNSUPPORTED_LAYOUT")
    need(len(scene.nodes)==len({n.id for n in scene.nodes}),
         "DUPLICATE_NODE_IDS")
    need(3<=len(scene.nodes)<=6,"UNSUPPORTED_NODE_COUNT")
    rows=[scene.nodes[i:i+2] for i in range(0,len(scene.nodes),2)]
    ext=[row_extents(x) for x in rows]
    gaps=[
        max(MIN_SAME_COL_SEPARATION,
            ext[i][1]+ext[i+1][0]+
            max(ROW_CLEARANCE_WORLD,REQUIRED_MARGIN/SCALE))
        for i in range(len(rows)-1)
    ]
    total=ext[0][0]+sum(gaps)+ext[-1][1]
    available=CONTENT_TOP-CONTENT_BOTTOM
    need(total<=available+1e-9,"CONTENT_BUDGET_EXCEEDED")
    slack=(available-total)/2
    centers=[CONTENT_TOP-ext[0][0]-slack]
    for gap in gaps:
        centers.append(centers[-1]-gap)
    result={}
    for ri,row in enumerate(rows):
        for column,node in enumerate(row):
            result[node.id]=(LEFT_COL if column==0 else RIGHT_COL,centers[ri])
    boxes={node.id:box(node,result[node.id]) for node in scene.nodes}
    # Finite, in-frame, disjoint inflated boxes; never change the QA margin.
    for key,bb in boxes.items():
        need(all(math.isfinite(v) for v in
                 (bb.left,bb.right,bb.top,bb.bottom)),
             "NONFINITE_NODE_RECT")
        need(bb.top>=0 and bb.bottom<=720,
             "NODE_OUTSIDE_PHYSICAL_FRAME")
        for other,ob in boxes.items():
            if key>=other:continue
            overlap_x=bb.left<ob.right+REQUIRED_MARGIN and bb.right+REQUIRED_MARGIN>ob.left
            overlap_y=bb.top<ob.bottom+REQUIRED_MARGIN and bb.bottom+REQUIRED_MARGIN>ob.top
            need(not (overlap_x and overlap_y),"STILL_COLLIDING_OBJECTS")
    # Reuse the actual compiler edge-route algorithm, not a new solver that
    # emits edges only the preflight (but not Manim) understands.
    for rel in scene.relations:
        need(rel.source in boxes and rel.target in boxes,
             "RELATION_LOST_ENDPOINT")
        path=_edge_route(scene,rel,result)
        need(2<=len(path)<=4,"RELATION_ROUTE_NOT_EXPORTED")
        pixels=[(640+x*SCALE,360-y*SCALE) for x,y in path]
        for a,b in zip(pixels,pixels[1:]):
            for name,ob in boxes.items():
                if name in (rel.source,rel.target):continue
                need(not _line_hit(a,b,ob),"RELATION_TOUCHES_UNRELATED_NODE")
    return result,{"scene_id":scene.id,"node_ids":list(result),
                   "row_count":len(rows),"row_centers_world":centers,
                   "row_clearances_world":gaps,
                   "reserved_height_world":round(total,5),
                   "content_top":CONTENT_TOP,"content_bottom":CONTENT_BOTTOM,
                   "qa_kind_budget":"V375_SIZE_INDICATE_1P07",
                   "geometry":"CLEAR_CERTIFIED_SOURCE_BOUNDS"}


def refine(story,legacy_layout):
    """Keep all non-COMPARISON scenes bit-for-bit identical to old layout."""
    new=deepcopy(legacy_layout)
    evidence=[]
    for scene in story.scenes:
        if scene.layout!="COMPARISON":continue
        need(scene.id in new,"UNKNOWN_SCENE")
        mapped,receipt=reflow_comparison(scene)
        need(set(mapped)==set(new[scene.id]),
             "SCENE_NODE_IDENTITIES_CHANGED")
        old=dict(new[scene.id])
        new[scene.id]=mapped
        receipt["old_layout"]=old
        receipt["new_layout"]=mapped
        evidence.append(receipt)
    # Heldout lessons without COMPARISON are a declared identity-preserving
    # NO-OP, not a rejected visual or a falsely repaired COMPARISON scene.
    if not evidence:
        need(new==legacy_layout,"NOOP_CHANGED_LEGACY_LAYOUT")
    return new,{"checkpoint":"V3-77",
                "family":"COMPARISON",
                "status":("GENERATED_GEOMETRY_CERTIFIED" if evidence
                          else "NOT_APPLICABLE_NO_COMPARISON_UNMODIFIED"),
                "scenes":evidence,
                "source":"TRUSTED_HOST_PLACER",
                "rendered_pixel_quality":"NOT_PROVEN_BY_LAYOUT_ALONE"}
