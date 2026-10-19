"""V3-90 deadline demo: new numeric queries, native compiler, fail-closed release."""
from __future__ import annotations
from html import escape
from pathlib import Path
import pytest

from scripts.run_v3_90_deadline_demo import registered, prepare, run
from learnflow_v3.v388_cross_family_manim import finite_source

ROOT=Path(__file__).resolve().parents[2]

def test_frozen_scope_and_honest_quality():
    d=registered()
    assert (d["locked_denominator"],d["expected_native"],d["expected_abstain"])==(4,2,2)
    assert d["acceptance"]["model_api_requests"]==0
    assert d["acceptance"]["production"]=="BLOCKED"
    assert d["acceptance"]["external_human_scores"]==0
    assert d["acceptance"]["autonomous_model_storyboard"]=="NOT_TESTED"

@pytest.mark.parametrize("i,family",[(0,"FRACTION_EQUIVALENCE"),(1,"ORDERED_SEARCH")])
def test_new_parameters_compile_to_trusted_finite_manim(i,family):
    q=registered()["positive_queries"][i]
    row,result=prepare(q)
    assert row["family"]==family
    assert result["status"]=="SUPPORTED_HOST_ONLY"
    plan=result["plan"]
    assert plan["model_authorship"] is False
    assert len(plan["source_semantic_proof_sha256"])==64
    assert len(plan["scripted_semantic_events"])>=3
    source=finite_source(row,plan,[13.0]*len(plan["scripted_semantic_events"]))
    compile(source,"<finite-manim>","exec")
    assert "from manim import *" in source

@pytest.mark.parametrize("i",[0,1])
def test_false_fraction_or_unsorted_array_abstains(i):
    row,result=prepare(registered()["negative_queries"][i])
    assert result["status"]=="ABSTAIN"
    assert result["reason"]=="FAILED_HOST_SEMANTIC_ORACLE"
    assert result["video"] is None

@pytest.mark.parametrize("question",[
    "Explain photosynthesis.","Why did the Industrial Revolution begin?",
    "<img src=x onerror=alert(1)>",
])
def test_unsupported_input_does_not_generate_video(question):
    row,r=prepare(question)
    assert row["family"]=="UNSUPPORTED"
    assert r["status"]=="ABSTAIN" and r["video"] is None

@pytest.mark.parametrize("question",[
    "Can 1/3 and 1/3 show the same shaded amount?",
    "Find the leftmost index of 9 in [9, 2, 9].",
])
def test_invalid_operator_or_input_never_reaches_renderer(question):
    assert prepare(question)[1]["status"]=="ABSTAIN"

@pytest.mark.parametrize("question",[
    "  Can 1/3 and 3/9 show the same shaded amount?",
    "x"*301, "illegal\nnewline",
])
def test_query_malformed_is_error_not_silent_normalization(question):
    with pytest.raises(ValueError,match="V390_QUERY_MALFORMED"):
        prepare(question)

def test_new_user_parameters_not_fixture_ids():
    row,r=prepare("Can 2/5 and 4/10 show the same shaded amount?")
    assert row["family"]=="FRACTION_EQUIVALENCE"
    assert r["status"]=="SUPPORTED_HOST_ONLY"
    assert r["plan"]["ratio"]==[2,5,4,10]

def test_preflight_is_not_native_or_human_pass(tmp_path):
    out=tmp_path/"preflight"
    d=registered()
    report=run(out,d["positive_queries"]+d["negative_queries"],
               locked=True,preflight_only=True)
    assert report["machine_native_evidence"]=="NOT_RUN_OR_ALL_ABSTAIN"
    assert report["native_verified"]==0 and report["abstained"]==2
    assert report["final_visual_quality"]=="NOT_PASS"
    assert report["production"]=="BLOCKED"
    assert report["independent_human_quality"]=="PENDING_HUMAN_REVIEW_ZERO_REAL_SCORES"
    assert not list(out.glob("**/*.mp4"))
    assert "PREFLIGHT ONLY" in (out/"index.html").read_text()

def test_preregistered_demo_cannot_swap_input(tmp_path):
    d=registered()
    q=d["positive_queries"]+d["negative_queries"]
    q[0]="Can 2/5 and 4/10 show the same shaded amount?"
    with pytest.raises(ValueError,match="V390_LOCKED_QUESTIONS_SUBSTITUTED"):
        run(tmp_path/"swapped",q,locked=True,preflight_only=True)
    assert not (tmp_path/"swapped").exists()

def test_gallery_escape_never_injects_untrusted_markup(tmp_path):
    q="<img src=x onerror=alert(1)>"
    out=tmp_path/"unsafe_html"
    report=run(out,[q],preflight_only=True)
    page=(out/"index.html").read_text()
    assert escape(q) in page and q not in page
    assert "<video" not in page
    assert report["cases"][0]["status"]=="ABSTAIN"

def test_native_pipeline_reuses_actual_decoder_not_mock():
    code=(ROOT/"scripts/run_v3_90_deadline_demo.py").read_text()
    for token in ("_audio(","_docker_manim(","deterministic_mux(",
                  "_codec_and_pixel_gates(","verify_native(","FULL_H264_DECODING_FAILED"):
        assert token in code
    assert "OPENROUTER_API_KEY" not in code
    assert "urlopen(" not in code
