"""V3-88 preregistered two-family semantic transfer with heldout and attack cases.

A passing source test is not a native-video PASS. GitHub Actions must render,
mux, decode and independently sample real H264 for all 4 frozen positives.
"""
from __future__ import annotations
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import json
import pytest

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.v388_cross_family_planner import registered,compile_case
from learnflow_v3.v388_cross_family_manim import finite_source
from learnflow_v3.binary_search_trace import (
    make_binary_search_trace,verify_binary_search_trace
)

ROOT=Path(__file__).resolve().parents[2]


def rows():
    return registered(ROOT)["cases"]


def test_preregister_first_child_scope_and_locked_denominator():
    p=registered(ROOT)
    assert p["protocol"]=="FIRST_COMMIT_PREREG_BEFORE_STORYBOARD_RENDERER"
    assert p["parent"]=={"pr":124,"sha":"94836da45b53499052bd3ccad7cf2a349cb1f2ff"}
    assert len(rows())==8
    assert [r["role"] for r in rows()]==[
        "development","heldout","development","heldout",
        "negative","negative","negative","negative"]
    assert [r["id"] for r in rows()]==p["fixed_case_ids"]
    assert p["acceptance"]["native_exact"]==4
    assert p["acceptance"]["abstain_exact"]==4
    assert p["acceptance"]["heldout_exact"]==2
    assert p["acceptance"]["model_api"]==0
    assert p["acceptance"]["production"]=="BLOCKED"


@pytest.mark.parametrize("index",(0,1))
def test_real_v349_claims_v347_grammar_and_v381_partition_exact(index):
    p=compile_case(rows()[index])
    assert p["status"]=="SUPPORTED_HOST_ONLY"
    plan=p["plan"]
    assert plan["origin"]=="V349_HOST_VERIFIED_NOT_MODEL"
    assert plan["visual_operator"]=="PARTITION_REFINEMENT"
    assert plan["typed_claims"]==["F1","F2","F3"]
    assert plan["shaded_area_equal"] is True
    n,d,nt,dt=plan["ratio"]
    assert nt==n*plan["subdivision_factor"]
    assert dt==d*plan["subdivision_factor"]
    assert Fraction(n,d)==Fraction(nt,dt)
    assert plan["shade_exact"]==[n,d]
    assert plan["refined_exact"]==[nt,dt]
    assert [x["phase"] for x in plan["scripted_semantic_events"]]==[
        "ORIENT","TRANSFORM","INTERPRET"]
    assert all(x["claim_ids"] for x in plan["scripted_semantic_events"])


@pytest.mark.parametrize("index",(2,3))
def test_real_v305_binary_search_leftmost_verified_every_step(index):
    result=compile_case(rows()[index])
    assert result["status"]=="SUPPORTED_HOST_ONLY"
    plan=result["plan"]
    assert plan["origin"]=="V305_REPLAYED_TRACE_NOT_MODEL"
    assert plan["visual_operator"]=="ORDERED_ELIMINATION_WITH_CANDIDATE"
    assert plan["trace_replayed_every_step"] is True
    assert plan["result_index"]==3
    assert plan["values"][plan["result_index"]]==plan["target"]
    assert plan["scripted_semantic_events"][-1]["phase"]=="COMPLETE"
    comparisons=plan["scripted_semantic_events"][:-1]
    assert len(comparisons)>=3
    assert all(x["phase"]=="COMPARE" for x in comparisons)
    assert all(x["claim_ids"] and x["mid"]>=x["low"] and x["mid"]<=x["high"]
               for x in comparisons)
    assert len(plan["source_sha256"])==64


@pytest.mark.parametrize("index",(0,1,2,3))
def test_all_four_frozen_native_host_source_compiles_without_fixture_branches(index):
    r=rows()[index]
    plan=compile_case(r)["plan"]
    narration_count=len(plan["scripted_semantic_events"])
    source=finite_source(r,plan,[13.0]*narration_count)
    compile(source,"<trusted-v388>",'exec')
    assert "from manim import *" in source
    assert "self.wait(2/15)" in source
    assert "CMU Serif" in source
    if plan["family"]=="FRACTION_EQUIVALENCE":
        assert "refined_guides.add(Line" in source
        assert "source_guides.add(Line" in source
        assert "subdivide" not in source.lower() or "refined_guides" in source
        assert "shade=Rectangle" in source
    else:
        assert "LOW " in source and " MID " in source and " HIGH " in source
        assert "square_0" in source
        assert "LEFTMOST INDEX = 3" in source
        assert ".animate.set_fill" in source
    assert "from openai" not in source and "eval(" not in source


@pytest.mark.parametrize("index",(4,5,6,7))
def test_four_rejections_fail_closed_without_video(index):
    r=compile_case(rows()[index])
    assert r["status"]=="ABSTAIN"
    assert r["video"] is None
    assert r["reason"] in ("NO_TYPED_PROVEN_SOURCE_FAMILY",
                            "FAILED_HOST_SEMANTIC_ORACLE")


@pytest.mark.parametrize("index",(0,1,2,3))
def test_host_verified_visual_plan_tampering_blocks_native(index):
    r=rows()[index]
    plan=deepcopy(compile_case(r)["plan"])
    if index<=1:
        plan["ratio"][2]+=1
    else:
        plan["scripted_semantic_events"][0]["mid"]+=1
    with pytest.raises(Blocked,match="V388_TAMPERED_VISUAL_SOURCE_OR_REPLAYED_STORYBOARD"):
        finite_source(r,plan,[13.0]*len(plan["scripted_semantic_events"]))


def test_binary_trace_mutation_fails_independent_sha_and_oracle():
    trace=make_binary_search_trace(values=(1,3,5,8,8,8,11,16),
                                   target=8,source_ref="trace:v388:negative")
    assert verify_binary_search_trace(trace).oracle_index==3
    attack=trace.model_copy(update={"result_index":4})
    with pytest.raises(Exception,match="TRACE_HASH_MISMATCH"):
        verify_binary_search_trace(attack)


@pytest.mark.parametrize("wrong",[
  "Can 2/3 and 4/7 show the same shaded amount?",
  "Can 2/3 and 1/2 show the same shaded amount?",
  "Can 6/5 and 12/10 show the same shaded amount?",
  "Can 2/3 and 0/0 show the same shaded amount?",
])
def test_invalid_equal_parts_cannot_enter_rendering(wrong):
    row=deepcopy(rows()[0]);row["question"]=wrong
    assert compile_case(row)["status"]=="ABSTAIN"


@pytest.mark.parametrize("wrong",[
  "Find the leftmost index of 8 in [3, 8, 1, 5].",
  "Find the leftmost index of 8 in [5, 4, 3].",
  "Find the leftmost index of 8 in [1, 2].",
])
def test_unsorted_or_too_short_binary_search_cannot_render(wrong):
    row=deepcopy(rows()[2]);row["question"]=wrong
    assert compile_case(row)["status"]=="ABSTAIN"


def test_literal_topic_ids_never_control_renderer_branch():
    source=(ROOT/"learnflow_v3/v388_cross_family_manim.py").read_text()
    for literal in ("fraction_refinement_development","fraction_refinement_heldout",
                    "binary_search_development","binary_search_heldout",
                    "if row['id'] ==","if topic =="):
        assert literal not in source


def test_runner_reuses_old_secure_native_audio_and_full_decoder():
    source=(ROOT/"scripts/run_v3_88_cross_family_native.py").read_text()
    for token in ("_audio(","_docker_manim(","_codec_and_pixel_gates(",
                  "deterministic_mux(","verify_native(","full_native_decode",
                  "H264/AAC","model_api_requests"):
        assert token in source


def test_no_human_ratings_fabricated():
    r=registered(ROOT)["independent_human_review"]
    assert r["real_reviewer_count"]==0
    assert r["scores"]=="UNMEASURED"
    assert r["rubric_axes"]==[
        "semantic correctness","continuity and causal meaning",
        "readable spatial composition","narration visual timing",
        "pedagogical usefulness"]
