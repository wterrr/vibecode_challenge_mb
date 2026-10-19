"""V3-80 preregistered adverse semantic transformation protocol tests.

No network/model; fake source math cannot add animations to host compiler.
The dedicated Actions render is the only certified H264 physical evidence.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_scene_fixtures import fixtures
from learnflow_v3.creative_candidate_acceptance import accept,mock_candidate_bytes
from learnflow_v3.creative_scene_graph import manim
from learnflow_v3.v377_extent_aware_comparison import refine
from learnflow_v3.v379_visual_hierarchy import compact
from learnflow_v3.v380_semantic_transformations import plan
from learnflow_v3.v380_native_semantic_witness import (
    check_growth,visible_height,clipped_bar_rect,WIDTH,HEIGHT
)
from scripts.run_v3_54_model_candidate_quality import ROOT,NAMES

REG=ROOT/"benchmarks/learnflowbench/v3/v3_80_semantic_transformations_preregister.json"

def make(case):
    accepted,diag=accept(mock_candidate_bytes(fixtures()[case]))
    assert accepted is not None,diag
    st=accepted["storyboard"]
    coords,_=refine(st,accepted["layout"])
    coords,_=compact(st,coords)
    seconds=[10.0]*len(st.beats)
    return st,deepcopy(accepted["facts"]),accepted["graphs"],coords,seconds

def test_prereg_parent_exact_sha_before_code_and_human_boundary():
    p=json.loads(REG.read_text())
    assert p["checkpoint"]=="V3-80"
    assert p["kind"]=="FIRST_CHILD_PREREG_BEFORE_CODE"
    assert p["parent"]["pr"]==116
    assert p["parent"]["sha"]=="2f98efaeabb21440aafdafa9d5bfb31e98d4e9f2"
    assert p["baseline"]["artifact"]==11945282706
    assert p["restrictions"]["model_api_calls"]==0
    assert p["restrictions"]["production"]=="BLOCKED"
    assert p["baseline"]["native_fixtures"][0]["h264_frames"]==632

@pytest.mark.parametrize("case",list(NAMES.values()))
def test_ledger_checked_bar_growth_and_causal_routing_in_original_three(case):
    st,facts,graphs,coords,seconds=make(case)
    receipt=plan(st,facts,coords,seconds)
    assert receipt["status"]=="HOST_GROUNDED_FINITE_TRANSFORM_CONTRACT"
    assert receipt["verified_bar_growth_count"]>=1
    assert receipt["verified_causal_route_count"]>=1
    assert receipt["all_animation_slots_contained_in_original_beats"]
    assert receipt["narration_beat_total_seconds"]==sum(seconds)
    for event in receipt["events"]:
        assert event["source"]=="HOST_VERIFIED_LEDGER"
        assert event["slot_duration_s"]>0
        assert abs(sum(event["phases"])-event["slot_duration_s"])<.00011
        if event["kind"]=="HOST_SCALAR_BAR_GROWTH":
            assert 0<event["host_bar_value"]<=1
            assert event["bar_width_world"]==1.2
            assert event["fact_ref"] in facts["facts"]
            assert event["physical_bar_height_world"]==round(
                max(.24,1.75*event["host_bar_value"]),4)
        else:
            assert event["relation_kind"] in ("FLOW","TRANSFORMS_INTO")
            assert [event["source_fact"],event["target_fact"],event["relation_kind"]] in facts["allowed_edges"]
            assert "Indicate(source)" in event["animation"]

@pytest.mark.parametrize("case",list(NAMES.values()))
def test_original_compiler_default_bit_identical_and_true_new_native_phases(case):
    st,facts,graphs,coords,sec=make(case)
    baseline=manim(st,facts,graphs,coords,sec,hierarchy_v379=True)
    explicit_off=manim(st,facts,graphs,coords,sec,hierarchy_v379=True,semantic_v380=False)
    transformed=manim(st,facts,graphs,coords,sec,hierarchy_v379=True,semantic_v380=True)
    assert baseline==explicit_off
    assert "GrowFromEdge(" not in baseline
    assert "GrowFromEdge(" in transformed
    assert "FadeIn(" in transformed and "_caption" in transformed
    assert "rate_func=linear" in transformed
    assert "scale_factor=1.07" in transformed
    assert "self.play(Indicate(" in transformed
    assert "Dot(" not in transformed and "MoveAlongPath(" not in transformed
    assert transformed.count("# BEAT_")==len(st.beats)
    compile(transformed,"<host-source-v380>","exec")

def test_reversed_relation_cannot_be_animated_as_a_true_host_flow():
    st,facts,graph,layout,sec=make("tokens_as_network")
    rel=next(r for s in st.scenes for r in s.relations if r.kind=="FLOW")
    rel.source,rel.target=rel.target,rel.source
    with pytest.raises(Blocked,match="V380_CAUSAL_RELATION_NOT_LEDGER_APPROVED"):
        plan(st,facts,layout,sec)

def test_moving_semantic_arrow_before_revealing_endpoint_rejected():
    st,facts,graph,layout,sec=make("tokens_as_network")
    st.beats[0].actions.insert(0,st.beats[0].actions.pop(3))
    with pytest.raises(Blocked,match="V380_CAUSAL_ENDPOINT_NOT_YET_REVEALED"):
        plan(st,facts,layout,sec)

@pytest.mark.parametrize("value",[0,-.1,float("nan"),1.2])
def test_chart_bar_height_bad_host_value_fail_closed(value):
    st,facts,graph,layout,sec=make("tokens_as_network")
    facts["facts"]["weight_a"]["bar_value"]=value
    with pytest.raises(Blocked,match="V380_CHART_NOT_POSITIVE_NORMALIZED_HOST_VALUE"):
        plan(st,facts,layout,sec)

def test_chart_claim_not_in_narration_beat_cannot_start_growth():
    st,facts,graph,layout,sec=make("tokens_as_network")
    beat=next(b for b in st.beats if b.scene_id=="mixture")
    beat.claims=["A2"]
    with pytest.raises(Blocked,match="V380_CHART_BEAT_CLAIM_UNGROUNDED"):
        plan(st,facts,layout,sec)

def test_wrong_relation_target_claim_cannot_get_fake_causal_animation():
    st,facts,graph,layout,sec=make("tokens_as_network")
    st.beats[-1].claims=["A3"]
    with pytest.raises(Blocked,match="V380_CAUSAL_TARGET_CLAIM_NOT_IN_BEAT"):
        plan(st,facts,layout,sec)

def test_semantic_animation_slots_are_strictly_inside_original_beat_duration():
    st,facts,graph,layout,sec=make("tokens_as_network")
    events=plan(st,facts,layout,sec)
    for e in events["events"]:
        b=e["beat_index"]
        assert sum(sec[:b])<=e["slot_start_s"]
        assert e["slot_start_s"]+e["slot_duration_s"]<=sum(sec[:b+1])+.0001
    assert all(b["duration_s"]==sec[b["beat_index"]] for b in events["beats"])

def test_user_supplied_move_and_replace_without_full_geometry_fails_closed():
    st,facts,graph,layout,sec=make("tokens_as_network")
    st.beats[0].actions[0].kind="move"
    with pytest.raises(Blocked,match="V380_UNSUPPORTED_DYNAMIC_ACTION"):
        plan(st,facts,layout,sec)

def test_native_bar_pixel_height_detects_real_progress_not_flat_fade():
    e={"bar_center_world":[0.,0.],"physical_bar_height_world":1.,
       "bar_width_world":1.2}
    rect=clipped_bar_rect(e)
    bg=np.zeros((HEIGHT,WIDTH,3),dtype=np.uint8)
    bg[:]=[8,11,17]
    start=bg.copy();end=bg.copy()
    x0,y0,x1,y1=rect
    start[y1-8:y1-2,x0+3:x1-3]=[255,170,30]
    end[y0+2:y1-2,x0+3:x1-3]=[255,170,30]
    assert visible_height(start,rect)>=4
    assert visible_height(end,rect)>visible_height(start,rect)+10
    with pytest.raises(Blocked,match="V380_PHYSICAL_BAR_RECT_UNGROUNDED"):
        clipped_bar_rect({"bar_center_world":[0.,float("nan")],
                          "physical_bar_height_world":1.,"bar_width_world":1.2})

def test_no_media_witness_from_nonexistent_or_forged_mp4(tmp_path):
    with pytest.raises(Blocked,match="V380_VIDEO_MISSING"):
        check_growth(tmp_path/"nothing.mp4",[],620)

def test_host_default_runner_stays_original_and_v380_requires_all_QA():
    s=(ROOT/"scripts/run_v3_54_model_candidate_quality.py").read_text()
    assert "semantic_v380:bool=False" in s
    assert "V380_REQUIRES_FULL_V377_79_AND_NATIVE_A3_QA" in s
    assert s.index("semantic_receipt=plan")<s.index("host_code=manim")
    assert "v380_semantic_transformations" in s

def test_physical_runner_uses_frozen_three_and_actual_h264_witness():
    s=(ROOT/"scripts/run_v3_80_native_semantic_transformations.py").read_text()
    assert "registered();directory.mkdir" in s
    assert "semantic_v380=True" in s
    assert "check_growth(movie,event" in s
    assert "inspect(movie,telemetry" in s
    assert '"frozen_prior_mp4s_overwritten":False' in s
    assert '"production":"BLOCKED"' in s
