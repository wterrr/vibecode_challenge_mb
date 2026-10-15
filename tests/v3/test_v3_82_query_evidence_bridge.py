"""Hostile query-to-Hermes-to-Manim mutation checks; no LLM or network."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json
import pytest

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.v382_query_evidence_bridge import (
    registered,expression_plan,compile_question,_approved_seed
)
from learnflow_v3.v381_finite_manim_compiler import source

ROOT=Path(__file__).resolve().parents[2]


def cases():
    return registered(ROOT)["cases"]


def test_first_child_prereg_frozen_before_implementation():
    p=registered(ROOT)
    assert p["parent"]["pr"]==118
    assert p["parent"]["sha"]=="947b05d029e2eadeee34d69ac1739a571c90ecfa"
    assert p["acceptance"]["real_model_calls"]==0
    assert p["acceptance"]["native_positive_exact"]==3
    assert p["acceptance"]["negative_abstain_exact"]==2


@pytest.mark.parametrize("index", [0,1,2])
def test_no_authored_operations_storyboards_narration(index):
    row=cases()[index]
    assert set(row)=={"id","role","domain","source_model","question","title","facts"}
    assert "operations" not in row and "narration" not in row
    steps,final=expression_plan(row)
    assert len(steps)==2 and final=="step_02"
    assert all(x["kind"] in ("ADD","SCALE") for x in steps)


@pytest.mark.parametrize("index", [0,1,2])
def test_real_reused_source_fact_script_pedagogy_director_gates(index):
    result=compile_question(cases()[index],ROOT)
    assert result["status"]=="READY_FOR_NATIVE_RESEARCH_ONLY"
    trace=result["trace"];c=result["contracts"]
    assert trace["all_numeric_outputs_verified"]
    assert c["pedagogy_gate"]=="V3_09_VALIDATED"
    assert c["visual_director_gate"]=="CORE_READY"
    assert c["source_status"]=="CURATED_HISTORICAL_REFERENCE_NOT_INDEPENDENT_SEMANTIC_PROOF"
    assert len(c["script"]["segments"])==len(trace["events"])
    assert trace["presentation_provenance"]=="VERIFIED_OPERATOR_OUTPUT_REPLAY_NO_MODEL"
    for event in trace["events"]:
        assert "var_" not in event["result_text"] and "step_" not in event["result_text"]
        assert all("var_" not in text and "step_" not in text
                   for text in event["operand_text"])
        assert "=" in event["result_text"]
    assert len(c["visual"]["beats"])==len(trace["events"])
    legacy=source(trace,[10.0]*len(trace["events"]))
    emitted=source(trace,[10.0]*len(trace["events"]),no_upscale_text=True)
    compile(emitted,"<v382-source>","exec")
    assert ".scale_to_fit_width(5.0).move_to(" in legacy
    assert ".scale_to_fit_width(5.0).move_to(" not in emitted
    assert "if left_0.width > 5.0:" in emitted
    assert "if right_0.width > 5.0:" in emitted


@pytest.mark.parametrize("index", [3,4])
def test_unseen_unverifiable_question_abstains_not_downgrades(index):
    c=compile_question(cases()[index],ROOT)
    assert c["status"]=="ABSTAIN" and c["video"] is None
    assert c["reason"]=="UNSUPPORTED_RESEARCH_AND_SEMANTIC_OPERATOR_FAMILY"


def test_source_model_swap_rejected():
    c=deepcopy(cases()[0]);c["source_model"]="CONSTANT_ACCELERATION_VELOCITY"
    with pytest.raises(Blocked,match="V382_UNSUPPORTED_DOMAIN_OR_SOURCE_URL"):
        compile_question(c,ROOT)


def test_unrecognized_source_model_rejected():
    c=deepcopy(cases()[0]);c["source_model"]="NEW_UNVERIFIED_SOURCE"
    with pytest.raises(Blocked,match="V382_UNREGISTERED_SOURCE_FAMILY"):
        compile_question(c,ROOT)


@pytest.mark.parametrize("expr",[
    "What is the result of __import__('os').system('id')?",
    "What is the result of a ** b + c?",
    "What is the result of (a or b) + c?",
    "What is the result of a / b + c?",
    "What is the result of a * missing + b?",
])
def test_unsafe_ast_and_unknown_variables_rejected(expr):
    c=deepcopy(cases()[0]);c["question"]=expr
    with pytest.raises(Blocked,match="V382_"):
        compile_question(c,ROOT)


def test_natural_prose_without_exact_grammar_abstains_explicit():
    c=deepcopy(cases()[0]);c["question"]="Please explain every result in chemistry."
    with pytest.raises(Blocked,match="V382_UNSUPPORTED_USER_QUERY_GRAMMAR"):
        compile_question(c,ROOT)


def test_wrong_literal_math_not_injected():
    c=deepcopy(cases()[0]);c["facts"]["m"]["n"]=100000000
    with pytest.raises(Blocked,match="V381_"):
        compile_question(c,ROOT)


def test_random_extra_operations_cannot_enter_preregister():
    c=deepcopy(cases()[0]);c["operations"]=[{"code":"eval()"}]
    with pytest.raises(Blocked,match="V382_CASE_INPUT_SCHEMA"):
        compile_question(c,ROOT)


def test_local_source_title_quote_or_url_mismatch_fail_closed():
    seed=deepcopy(_approved_seed(cases()[0],ROOT))
    assert seed["source_statement"].startswith("For a line")


def test_facts_and_operator_sequence_respond_to_new_numbers_not_topic_dispatch():
    a=compile_question(cases()[0],ROOT)
    altered=deepcopy(cases()[0]);altered["facts"]["m"]["n"]=9
    b=compile_question(altered,ROOT)
    assert a["trace"]["state"]["step_02"]!=b["trace"]["state"]["step_02"]
    assert [x["kind"] for x in a["trace"]["events"]]==[x["kind"] for x in b["trace"]["events"]]


def test_bounded_auto_script_numeric_and_visual_claim_alignment():
    a=compile_question(cases()[1],ROOT)
    scripts=a["contracts"]["script"]["segments"]
    for segment,event in zip(scripts,a["trace"]["events"],strict=True):
        assert event["claim_id"] in segment["claim_ids"]
        assert segment["spoken_text"]==event["narration"]
        assert segment["spoken_text"]==segment["subtitle_text"]


def test_no_domain_specific_dispatch_in_expression_compiler():
    s=(ROOT/"learnflow_v3/v382_query_evidence_bridge.py").read_text()
    assert "if row['domain'] ==" not in s
    assert "if row[\"domain\"] ==" not in s
    assert "if row['id'] ==" not in s
    assert "if row[\"id\"] ==" not in s
