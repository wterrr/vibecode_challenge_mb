"""V3-85 frozen evidence-grounded affine graph transfer and attack tests."""
from __future__ import annotations
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import pytest

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.v382_query_evidence_bridge import compile_question, registered
from learnflow_v3.v385_affine_visual_semantics import (
    AFFINE_ROLE_REGISTRY, role_contract, finite_manim_source, emit_step, _fmt
)
from learnflow_v3.v385_native_affine_visual_gate import ROI,SAMPLES

ROOT=Path(__file__).resolve().parents[2]


def rows():
    return registered(ROOT)["cases"]


def pre():
    d=json.loads((ROOT/"benchmarks/learnflowbench/v3/v3_85_domain_visual_preregister.json").read_text())
    assert d["checkpoint"]=="V3-85"
    assert d["kind"]=="FIRST_COMMIT_PREREG_BEFORE_CODE"
    assert d["parent"]=={
        "draft_pr":121,
        "head_sha":"727200532b763b8badb7a0ad55af7c6db47f5296"}
    assert d["locked_original_case_ids"]==[x["id"] for x in rows()]
    assert d["selection"]["positive"]==3
    assert d["selection"]["negative_abstain"]==2
    assert d["native_evidence"]["per_beat_offsets"]==list(SAMPLES)
    assert d["native_evidence"]["graph_roi"]==list(ROI)
    assert d["constraints"]["production"]=="BLOCKED"
    return d


def test_preregistration_is_immutable_inputs_and_limits():
    d=pre()
    assert d["selection"]["source_families"]==2
    assert d["selection"]["heldout_parameters"]==1
    assert d["selection"]["real_autonomous_model_storyboarding"]==0
    assert len(d["representation_contracts"])==2
    assert d["constraints"]["final_visual_quality"]=="NOT_PASS_UNTIL_INDEPENDENT_REVIEW"


@pytest.mark.parametrize("i",range(3))
def test_query_to_source_to_evidence_to_correct_graph(i):
    pre()
    row=rows()[i]
    bundle=compile_question(row,ROOT)
    v=role_contract(row,bundle)
    assert v["source_kind"]==row["source_model"]
    assert v["role"] in ("input_output_line","velocity_vs_elapsed_time")
    assert len(v["receipt_sha256"])==64
    assert v["source_truth_independently_reviewed"] is False
    assert v["actual_object_motion"]=="NONE_GRAPH_POINT_ONLY"
    fact=v["verified_values"]
    assert Fraction(fact["rate"])*Fraction(fact["independent"])==Fraction(fact["change"])
    assert Fraction(fact["initial"])+Fraction(fact["change"])==Fraction(fact["final"])
    pts=v["points"]
    assert pts["final"][0]==pts["rate_end"][0]
    assert pts["initial"][0]==pts["origin"][0]
    assert pts["final"][1]>.0
    assert pts["final"][1]>pts["rate_end"][1]
    assert pts["final"][1]>=pts["initial"][1]
    assert bundle["contracts"]["pedagogy_gate"]=="V3_09_VALIDATED"
    assert bundle["contracts"]["visual_director_gate"]=="CORE_READY"
    src=finite_manim_source(bundle["trace"],[12.0,12.0],v)
    compile(src,"<v385-native>",'exec')
    assert "V385_VERIFIED_SEMANTIC_GRAPH_BEAT_0" in src
    assert "V385_VERIFIED_SEMANTIC_GRAPH_BEAT_1" in src
    assert "MoveAlongPath" in src and "DashedLine" in src
    assert "run_time=26/15" in src
    assert "self.wait(2/15)" in src
    assert "v385_curve_1" in src
    assert "Square(" not in src and "V384_COMPOSITION_STAGE" not in src


def test_math_means_y_over_x_and_physics_means_v_over_time():
    r=[role_contract(rows()[i],compile_question(rows()[i],ROOT)) for i in range(3)]
    assert r[0]["horizontal_label"]=="x (input)"
    assert r[0]["vertical_label"]=="y (output)"
    for x in r[1:]:
        assert x["horizontal_label"]=="t (elapsed time)"
        assert x["vertical_label"]=="v (velocity)"
        assert x["interpretation"]=="SLOPE_IS_ACCELERATION_NOT_OBJECT_DISPLACEMENT"
    assert r[1]["points"]["rate_end"]!=r[2]["points"]["rate_end"]
    assert "LINEAR_SLOPE" in AFFINE_ROLE_REGISTRY
    assert "CONSTANT_ACCELERATION_VELOCITY" in AFFINE_ROLE_REGISTRY


def test_heldout_values_not_storyboard_replay():
    a=role_contract(rows()[1],compile_question(rows()[1],ROOT))
    b=role_contract(rows()[2],compile_question(rows()[2],ROOT))
    assert a["verified_values"]!=b["verified_values"]
    assert a["source_kind"]==b["source_kind"]
    assert a["role"]==b["role"]
    assert a["points"]["initial"]!=b["points"]["initial"]


@pytest.mark.parametrize("idx",(3,4))
def test_chm_history_still_real_abstain_not_text_card(idx):
    x=compile_question(rows()[idx],ROOT)
    assert x["status"]=="ABSTAIN" and x["video"] is None
    with pytest.raises(Blocked):
        role_contract(rows()[idx],x)


def test_wrong_family_cannot_spoof_visual_meaning():
    row=deepcopy(rows()[0])
    row["source_model"]="CONSTANT_ACCELERATION_VELOCITY"
    with pytest.raises(Blocked):
        role_contract(row,compile_question(rows()[0],ROOT))


def test_missing_required_symbol_rejected():
    row=deepcopy(rows()[0]);row["facts"].pop("b")
    with pytest.raises(Blocked):
        role_contract(row,compile_question(rows()[0],ROOT))


@pytest.mark.parametrize("change",["source_kind","source_url","source_provenance","fact"])
def test_mutated_evidence_or_fact_fail_closed(change):
    row=deepcopy(rows()[1])
    bundle=deepcopy(compile_question(row,ROOT))
    if change=="source_kind":
        row["source_model"]="UNKNOWN"
    elif change=="source_url":
        bundle["source_url"]="https://fake.example.com"
    elif change=="source_provenance":
        bundle["source_reference_kind"]="MODEL_AUTHOR_VERIFIED"
    else:
        row["facts"]["acceleration"]["n"]=9
    with pytest.raises(Blocked):
        role_contract(row,bundle)


def test_mutated_final_number_cannot_create_fake_graph():
    b=deepcopy(compile_question(rows()[1],ROOT))
    b["trace"]["events"][-1]["actual"]["n"]+=3
    with pytest.raises(Blocked):
        role_contract(rows()[1],b)


def test_mutated_claim_reference_rejected():
    b=deepcopy(compile_question(rows()[1],ROOT))
    b["trace"]["events"][0]["claim_id"]="C99"
    with pytest.raises(Blocked):
        role_contract(rows()[1],b)


@pytest.mark.parametrize("bad",[-1,0,16,41,2.4])
def test_bad_elapsed_input_bounded_fail_closed(bad):
    row=deepcopy(rows()[1]);row["facts"]["elapsed"]={"kind":"scalar","n":bad,"d":1}
    try:
        bundle=compile_question(row,ROOT)
        with pytest.raises((Blocked,ValueError,TypeError)):
            role_contract(row,bundle)
    except (Blocked,TypeError,ValueError):
        pass


def test_renderer_cannot_invent_physical_displacement():
    src=(ROOT/"learnflow_v3/v385_affine_visual_semantics.py").read_text()
    for term in ("if topic ==","if case_id ==","if row['domain'] ==",
                 "linear_output_new","accelerating_new","counterfactual_physics_heldout"):
        assert term not in src
    assert "actual_object_motion" in src
    assert "NONE_GRAPH_POINT_ONLY" in src


def test_too_short_audio_must_abstain_without_looser_mux():
    row=rows()[1];b=compile_question(row,ROOT);contract=role_contract(row,b)
    with pytest.raises(Blocked,match="V385_AUDIO_BEAT_TOO_SHORT"):
        emit_step(0,b["trace"]["events"][0],5.0,contract)


def test_source_runner_reuses_original_av_and_native_pixel_gates():
    src=(ROOT/"scripts/run_v3_85_typed_affine_visual.py").read_text()
    for thing in ("finite_manim_source","role_contract","native_affine_witness",
                  "_codec_and_pixel_gates","deterministic_mux","ffmpeg",
                  "source_grounded_contracts","original_question"):
        assert thing in src
