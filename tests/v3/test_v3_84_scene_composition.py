"""V3-84 preregistered spatial layout / exact continuity / hostile mutation gates."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import pytest

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.v382_query_evidence_bridge import compile_question,registered
from learnflow_v3.v381_finite_manim_compiler import source
from learnflow_v3.v384_pedagogical_scene_composer import (
    PALETTE, UNIT_SIDE, layout_event, plan, emit_step, require)
from learnflow_v3.v384_native_composition_gate import ROI, BEAT_SAMPLES

ROOT=Path(__file__).resolve().parents[2]


def examples():
    return registered(ROOT)["cases"]


def freeze():
    d=json.loads((ROOT/"benchmarks/learnflowbench/v3/v3_84_scene_composition_preregister.json").read_text())
    assert d["checkpoint"]=="V3-84"
    assert d["protocol"]=="PREREGISTER_BEFORE_IMPLEMENTATION"
    assert d["parent"]=={"draft_pr":120,"sha":"5ffa3b18e2c433696f7de3d3716b953ed38486fc"}
    assert d["fixed_cases"]==[x["id"] for x in examples()]
    assert d["denominators"]=={"new_native_positive":3,"unsupported_abstain":2,"heldout_new_native":1}
    assert d["temporal_witness"]["sample_frames_relative"]==list(BEAT_SAMPLES)
    assert d["temporal_witness"]["roi_xyxy"]==list(ROI)
    assert d["acceptance"]["production"]=="BLOCKED"
    return d


def test_preregistered_failure_inventory_and_scoped_acceptance():
    d=freeze()
    assert len(d["failure_inventory"])==4
    assert d["acceptance"]["autonomous_storyboarding"]=="NOT_TESTED"
    assert d["acceptance"]["visual_human_final"]=="NOT_PASS_UNTIL_INDEPENDENT_REVIEW"


@pytest.mark.parametrize("i",range(3))
def test_all_actual_frozen_queries_have_source_and_topic_independent_layout(i):
    freeze()
    bundle=compile_question(examples()[i],ROOT)
    assert bundle["contracts"]["pedagogy_gate"]=="V3_09_VALIDATED"
    assert bundle["contracts"]["visual_director_gate"]=="CORE_READY"
    trace=bundle["trace"]
    geometries=plan(trace)
    assert [p["operator"] for p in geometries]==["SCALE","ADD"]
    for g in geometries:
        assert g["count"]==g["host_verification"]["result_units"]
        assert len(g["unit_targets"])==g["count"]
        assert g["host_verification"]["host_verified"] is True
        assert all(-5.3<=x<=5.3 and -1.91<=y<=.75 for x,y in g["unit_targets"])
        assert g["layout"]=="STAGED_GROUPS_WITH_CAUSAL_CONTINUITY"
    multiplication,addition=geometries
    a,b=multiplication["source_counts"]
    assert len(multiplication["group_centers"])==a
    assert len(multiplication["unit_offsets"])==b
    assert len(set(multiplication["unit_targets"]))==a*b
    assert addition["count"]==len(addition["source_left"])+len(addition["source_right"])
    assert len(set(addition["unit_targets"]))==addition["count"]
    assert len(set(addition["source_left"]))==len(addition["source_left"])
    assert len(set(addition["source_right"]))==len(addition["source_right"])
    assert set(addition["source_left"]).isdisjoint(addition["source_right"])


@pytest.mark.parametrize("i",range(3))
def test_real_finite_manim_compiles_and_old_defaults_do_not_change(i):
    trace=compile_question(examples()[i],ROOT)["trace"]
    d=[12.0]*len(trace["events"])
    original=source(trace,d,no_upscale_text=True,pedagogical_units=True)
    old_plain=source(trace,d,no_upscale_text=True)
    new=source(trace,d,no_upscale_text=True,pedagogical_composition=True)
    compile(new,"<trusted-v384-composition>",'exec')
    assert "V384_COMPOSITION_STAGE_0:SCALE" in new
    assert "V384_COMPOSITION_STAGE_1:ADD" in new
    assert "COMBINE WITHOUT LOSING PIECES" in new
    assert "BUILD EQUAL GROUPS" in new
    assert "merged_target_1" in new and "strict=True" in new
    assert "RoundedRectangle" in new
    assert "V384_COMPOSITION_STAGE" not in original
    assert "V384_COMPOSITION_STAGE" not in old_plain
    assert "V383_UNIT_WITNESS_STEP" in original
    assert "V383_UNIT_WITNESS_STEP" not in new


@pytest.mark.parametrize("idx",(3,4))
def test_unsupported_history_chemistry_still_abstain(idx):
    r=compile_question(examples()[idx],ROOT)
    assert r["status"]=="ABSTAIN" and r["video"] is None


@pytest.mark.parametrize("bad",(0,-1,25,3.5))
def test_non_positive_overlarge_or_fractional_units_rejected(bad):
    case=deepcopy(compile_question(examples()[0],ROOT)["trace"]["events"][0])
    case["operands"][0]={"kind":"scalar","n":bad,"d":1}
    with pytest.raises((Blocked,ValueError,TypeError)):
        layout_event(case)


def test_wrong_result_never_renders():
    e=deepcopy(compile_question(examples()[1],ROOT)["trace"]["events"][1])
    e["actual"]["n"]+=1
    with pytest.raises(Blocked):
        layout_event(e)


def test_unverified_operation_never_renders():
    e=deepcopy(compile_question(examples()[1],ROOT)["trace"]["events"][1])
    e["kind"]="EQUIVALENT_PARTITION"
    with pytest.raises(Blocked):
        layout_event(e)


def test_missing_math_claim_never_renders():
    e=deepcopy(compile_question(examples()[1],ROOT)["trace"]["events"][0])
    e["operands"][1]["d"]=0
    with pytest.raises((Blocked,ZeroDivisionError)):
        layout_event(e)


def test_short_speech_beats_not_deceptively_retimed():
    e=compile_question(examples()[0],ROOT)["trace"]["events"][0]
    with pytest.raises(Blocked,match="V384_INSUFFICIENT_SPEECH_WINDOW"):
        emit_step(0,e,5.0,2)


def test_host_generated_storyboard_no_subject_id_branches():
    s=(ROOT/"learnflow_v3/v384_pedagogical_scene_composer.py").read_text()
    for forbidden in ("if topic ==","if domain ==","if case_id ==",
        "linear_output_new","accelerating_new","counterfactual_physics_heldout"):
        assert forbidden not in s


def test_native_three_phase_observability_and_audio_mux_preserved():
    src=(ROOT/"scripts/run_v3_84_scene_composition.py").read_text()
    for tok in ("native_three_phase(video,beats,trace)",
        "pedagogical_composition=True","_codec_and_pixel_gates",
        "deterministic_mux","full_native_decode","ffmpeg"):
        assert tok in src
