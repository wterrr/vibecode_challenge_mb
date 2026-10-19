"""V3-78 native salience metric integrity, mutation and honest QA-scope tests.

No source-only mock can prove MP4 pixel presence; this suite ensures the
metric logic cannot silently count chrome or overlapping rectangles twice.
Physical Docker/FFmpeg receipts are separately required by Actions.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.v378_native_visual_salience import (
    content_rects,is_content,union_area,percentile,tally_runtime,
    pixel_witnesses,inspect,
)
from scripts.run_v3_78_native_salience_benchmark import REG,ROOT


def row(i):
    rgb=[.91,.93,.95]
    def ob(name,role,rect,parent=""):
        return {"id":name,"role":role,"bbox_px":list(rect),"rgb":rgb,
                "color_source":"CONSTRUCT_TIME_SVG_LEAF_FILL",
                "glyph_rgbs":[rgb],"opacity":1.,"parent":parent}
    return {"seq":i,"scene_time_s":i/15,"dt":1/15,
            "objects":[ob("chrome_brand","text",(80,30,360,62)),
                       ob("s:n0:text","text",(110,200,280,234)),
                       ob("s:n1:shape","shape",(500,260,700,390)),
                       ob("s:n2:label","text",(535,300,665,330),
                          "s:n1:shape"),
                       ob("s:n3:shape","shape",(760,260,865,330)),
                       ob("s:n4:text","text",(110,420,280,440))]}


def rows(n=120):
    return [row(i) for i in range(n)]


def test_prereg_locks_exact_native_fixtures_and_no_human_quality_claim():
    d=json.loads(REG.read_text())
    assert d["kind"]=="FIRST_CHILD_PREREG_BEFORE_IMPLEMENTATION"
    assert d["parent"]["draft_pr"]==114
    assert d["parent"]["sha"]=="cd821f1dbbd0abb343d5f99538713853bd964ddd"
    assert d["baseline"]["artifact"]==11942843574
    assert [x["native_frames"] for x in d["baseline"]["cases"]]==[632,623,788]
    assert d["restrictions"]["model_calls"]==0
    assert d["restrictions"]["production"]=="BLOCKED"
    assert d["acceptance"]["human"].startswith("Independent viewer")


def test_intersected_rectangles_counted_only_once():
    assert union_area([(0,0,10,10),(5,0,15,10)])==150
    assert union_area([(0,0,10,10),(0,0,10,10)])==100
    assert union_area([(0,0,10,10),(20,20,30,30)])==200
    assert union_area([])==0
    assert union_area([(0,0,5,5),(3,3,8,8)])==46


def test_chrome_never_counted_as_learning_content():
    o=row(0)["objects"][0]
    assert o["role"]=="text" and not is_content(o)
    assert len(content_rects(row(0)))==5
    measured=tally_runtime(rows(),120)
    assert measured["runtime_ticks"]==120
    assert measured["scene_owned_objects_per_tick_median"]==5
    assert measured["longest_chrome_only_streak_ticks"]==0
    assert measured["bbox_union_area_fraction_median"]>0
    assert measured["content_visible_fraction_of_ticks"]==1
    assert measured["bbox_semantics"].endswith("NOT_ACTUAL_FILLED_PIXELS")


def test_text_risk_is_only_a_report_not_auto_final_visual_failure():
    m=tally_runtime(rows(),120)
    assert m["text_groups_below_24px_native"]==1
    ids={x["id"] for x in m["effective_native_text_groups"]}
    assert ids=={"s:n0:text","s:n2:label","s:n4:text"}
    assert m["visual_density_is_learning_quality"]=="NO"


def test_zero_content_intervals_marked_instead_of_silently_passed():
    r=rows()
    for item in r[:12]:
        item["objects"]=[o for o in item["objects"] if o["id"]=="chrome_brand"]
    m=tally_runtime(r,120)
    assert m["longest_chrome_only_streak_ticks"]==12
    assert m["longest_chrome_only_streak_approx_seconds"]==.8


@pytest.mark.parametrize("bad",[
    "missing_seq","duplicate_seq","bbox_nan","bbox_outside",
    "missing_glyph_fill","all_chrome_only","not_enough_ticks"
])
def test_corrupt_or_laundered_telemetry_fails_closed(bad):
    arr=rows()
    if bad=="missing_seq":arr[10]["seq"]=99
    if bad=="duplicate_seq":arr[11]["seq"]=10
    if bad=="bbox_nan":arr[4]["objects"][1]["bbox_px"][1]=float("nan")
    if bad=="bbox_outside":arr[5]["objects"][1]["bbox_px"][2]=1282
    if bad=="missing_glyph_fill":del arr[7]["objects"][1]["color_source"]
    if bad=="all_chrome_only":
        for item in arr:
            item["objects"]=[item["objects"][0]]
    if bad=="not_enough_ticks":arr=arr[:12]
    with pytest.raises((Blocked,ValueError,TypeError)):
        tally_runtime(arr,120)


def test_invalid_area_cannot_be_reported_as_good_density():
    from learnflow_v3.v378_native_visual_salience import need
    with pytest.raises(Blocked,match="INVALID_CONTENT_RECT"):
        content_rects({"objects":[{"id":"s:x:text","role":"text",
                       "opacity":1.,"bbox_px":[0,1,2,float("nan")]}]})
    with pytest.raises(Blocked,match="CONTENT_OUT_OF_FRAME"):
        content_rects({"objects":[{"id":"s:x:text","role":"text",
                       "opacity":1.,"bbox_px":[-7,1,2,4]}]})


def test_no_laundered_visual_quality_label_or_arbitrary_score():
    s=(ROOT/"learnflow_v3/v378_native_visual_salience.py").read_text()
    for bad in ["mock_token_network","mock_score_comparison","mock_symbolic_equivalence",
                "learning_quality_score","visual_quality_PASS","3B1B_PARITY"]:
        assert bad not in s
    assert "NOT_ACTUAL_FILLED_PIXELS" in s
    assert "APPROXIMATE_NOT_1_TO_1" in s
    assert "per_object_pixel_segmentation" in s


def test_forged_mp4_or_missing_native_data_cannot_pass(tmp_path):
    with pytest.raises(Blocked,match="NO_VERSIONED_NATIVE_VIDEO"):
        inspect(tmp_path/"missing.mp4",tmp_path/"missing.jsonl",120)
    fake=tmp_path/"fake.mp4"
    fake.write_bytes(b"not-video"*6000)
    with pytest.raises(Blocked,match="MISSING_NATIVE_H264"):
        pixel_witnesses(tmp_path/"missing.mp4",rows(),120)


def test_native_foreground_pixel_witness_must_come_from_decoder(monkeypatch,tmp_path):
    from learnflow_v3 import v378_native_visual_salience as m
    vid=tmp_path/"fake.mp4";vid.write_bytes(b"fake"*15000)
    monkeypatch.setattr(m,"_frame",lambda movie,frame:np.zeros((720,1280,3),dtype=np.uint8))
    with pytest.raises(Blocked,match="MISSING_FOREGROUND_IN_ACTUAL_NATIVE_PIXELS"):
        pixel_witnesses(vid,rows(),120)


def test_new_qa_calls_three_actual_old_mp4s_with_strict_native_proofs():
    s=(ROOT/"scripts/run_v3_78_native_salience_benchmark.py").read_text()
    assert "old=old_run(output)" in s
    assert 'old["accepted_count"]!=3' in s
    assert 'record["candidate_native_sha256"]!=hashlib.sha256(movie.read_bytes()).hexdigest()' in s
    assert 'inspect(movie,telemetry,record["native_frames"])' in s
    assert '"human_visual_quality":"NOT_PASS_PENDING_REVIEW"' in s
    assert '"model_api_calls":0' in s


@pytest.mark.parametrize("pct,val",[(0,1),(.5,3),(1,5)])
def test_percentiles_are_deterministic(pct,val):
    assert percentile([5,2,1,4,3],pct)==val
