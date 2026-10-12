"""V3-45-FIX: reproduce screenshot defect from immutable OLD native MP4.

Independent AABB/oblique/nonintersection tests + physical before/after decoded
H264 pixel failure gate. No live-model response or generated Python accepted.
"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.semantic_scene_offline_fixtures import synthetic_process_wire
from learnflow_v3.semantic_scene_wire import (
    decode_model_facing_scene,compile_scene,process_edge_layout,
    PROCESS_EDGE_CLEARANCE
)
from learnflow_v3.process_edge_visual_qa import inspect_frozen_failure

ROOT=Path(__file__).resolve().parents[2]
FIX_REG="benchmarks/learnflowbench/v3/v3_45_fix_edge_visual_preregister.json"


def test_preregister_before_fixes_and_exact_historical_bug():
    p=json.loads((ROOT/FIX_REG).read_text())
    assert p["preregistered_before_fix"] is True
    assert p["parent_pr"]==79
    assert p["parent_sha"]=="65499a93b733395f2b465df1894ad7a1b47556a1"
    assert p["acceptance"]["edge_to_node_min_clearance_world_units"]==.16
    assert p["frozen_failed"]["synthetic_process_mp4_sha256"]=="f9f6c54647fad3797da445b1a8714c9fa967f1f0bf35a9bfa1fd629cc1172a48"


def test_centres_to_node_boundary_clearance_is_geometric_not_buff_magic():
    scene=decode_model_facing_scene(synthetic_process_wire())
    layout=process_edge_layout(scene)
    a,b=layout["edge_start_verify"]["src"],layout["edge_start_verify"]["dst"]
    c,d=layout["edge_verify_finish"]["src"],layout["edge_verify_finish"]["dst"]
    assert (a[0],b[0])==pytest.approx((-1.94,-1.06),abs=1e-5)
    assert (c[0],d[0])==pytest.approx((1.06,1.94),abs=1e-5)
    assert a[1]==b[1]==c[1]==d[1]==0
    assert b[0]-a[0]>.8
    assert layout["edge_start_verify"]["clearance"]==PROCESS_EDGE_CLEARANCE

    code=compile_scene(scene,[8.66,8.46,8.53,8.53])
    assert "buff=0" in code
    assert "buff=.75" not in code
    assert "Arrow(start.get_center()" not in code
    assert "Line(start.get_center(),verify.get_center())" not in code
    assert "Line(edge_start_verify.get_start(),edge_start_verify.get_end())" in code
    assert ".set_z_index(0)" in code and ".set_z_index(2)" in code
    compile(code,"<v345_fix_geometry>","exec")


@pytest.mark.parametrize("centres,sizes",[
  ([(-3,-1.3),(0,0),(3,1.3)],[(1.4,.7),(2.1,1.4),(1.4,.9)]),
  ([(0,-2),(0,0),(0,2)],[(1.2,.8),(1.3,.8),(1.2,.8)]),
  ([(-3,0),(0,0),(3,0)],[(1.8,1.2),(1.8,1.2),(1.8,1.2)]),
])
def test_off_axis_rectangle_ray_intersections_keep_margins(centres,sizes):
    raw=synthetic_process_wire()
    for name,pos,sz in zip(("start","verify","finish"),centres,sizes):
        obj=next(x for x in raw["graphics"] if x["id"]==name)
        obj["x"],obj["y"]=map(float,pos)
        obj["width"],obj["height"]=map(float,sz)
    scene=decode_model_facing_scene(raw)
    graph={v.id:v for v in scene.graphics}
    for edge in (v for v in scene.graphics if v.kind=="edge"):
        a,b=graph[edge.src],graph[edge.dst]
        path=process_edge_layout(scene)[edge.id]
        import math
        vx,vy=b.x-a.x,b.y-a.y
        norm=math.hypot(vx,vy)
        ux,uy=vx/norm,vy/norm
        def boundary(t):
            return min((t.width/2)/abs(ux) if abs(ux)>1e-12 else math.inf,
                       (t.height/2)/abs(uy) if abs(uy)>1e-12 else math.inf)
        start_distance=((path["src"][0]-a.x)*ux+
                        (path["src"][1]-a.y)*uy)
        end_distance=((b.x-path["dst"][0])*ux+
                      (b.y-path["dst"][1])*uy)
        assert start_distance-boundary(a)>=.1599
        assert end_distance-boundary(b)>=.1599


@pytest.mark.parametrize("geometry_mutation",[
 "blocked_by_third_node","no_gap","source_partially_out_of_canvas"
])
def test_invalid_process_route_fails_before_Manim(geometry_mutation):
    raw=deepcopy(synthetic_process_wire())
    a,b,c=(next(x for x in raw["graphics"] if x["id"]==nid)
           for nid in ("start","verify","finish"))
    if geometry_mutation=="blocked_by_third_node":
        a["x"],b["x"],c["x"]=-3,3,0
    elif geometry_mutation=="no_gap":
        a["x"],b["x"],c["x"]=-.9,.9,3.5
    else:
        c["x"]=5.6
        c["width"]=3
    with pytest.raises(Blocked):
        decode_model_facing_scene(raw)


def test_old_real_h264_temporal_pixel_overlap_is_reproduced():
    base=os.environ.get("V345_FIX_BASELINE_DIR")
    assert base, "V345_FIX_BASELINE_DIR must be downloaded immutable GH artifact"
    scene=decode_model_facing_scene(synthetic_process_wire())
    proof=inspect_frozen_failure(Path(base),scene)
    assert proof["new_edge_pixels_inside_source_node"]>=20
    assert proof["new_edge_pixels_inside_target_node"]>=20
    assert proof["cursor_pixels_changed_on_source_caption"]>=12
    assert proof["new_edge_pixels_in_open_gap"]>=100


def test_new_ci_requires_rendered_pixel_gate_not_just_validator():
    workflow=(ROOT/".github/workflows/v3-45-semantic-offline.yml").read_text()
    runner=(ROOT/"scripts/run_v3_45_semantic_offline.py").read_text()
    assert "V345_FIX_BASELINE_DIR" in workflow
    assert "38196528217" in workflow
    assert "test_v3_45_fix_process_edge_geometry.py" in workflow
    assert "inspect_first_edge" in runner
    assert "decoded_process_edge_overlap_gate" in runner
    assert "OPENROUTER_API_KEY" not in workflow
