"""V3-87 frozen host geometry, end-user typography and real PCM compiler gates."""
from __future__ import annotations
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import pytest
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.v382_query_evidence_bridge import compile_question,registered
from learnflow_v3.v385_affine_visual_semantics import role_contract
from learnflow_v3.v386_pedagogical_speech_contract import semantic_phases
from learnflow_v3.v386_phased_affine_manim import finite_source as v386_source
from learnflow_v3.v387_readable_affine_continuity import (
    layout,finite_source,RECTS,FONT_SIZES,X1,Y1,RESULT_Y
)
from learnflow_v3.v387_native_readability_gate import GRAPH,RIGHT_CALLOUT,ANSWER

ROOT=Path(__file__).resolve().parents[2]


def rows():
    return registered(ROOT)["cases"]


def get(i=1):
    r=rows()[i];b=compile_question(r,ROOT)
    v=role_contract(r,b)
    return r,b,v,semantic_phases(r,b,v)


def test_preregistered_before_code_and_all_fixed_inputs():
    d=json.loads((ROOT/"benchmarks/learnflowbench/v3/v3_87_readability_continuity_preregister.json").read_text())
    assert d["checkpoint"]=="V3-87" and d["kind"]=="PREREG_FIRST_CHILD_BEFORE_IMPLEMENTATION"
    assert d["parent"]["head_sha"]=="9701b493c6dd561035c68e6b6e7451988072b57a"
    assert d["parent"]["pr"]==123
    assert d["baseline"]["fixed_question_set"]==[r["id"] for r in rows()]
    assert len(d["baseline"]["defects"])==3
    assert d["scope"]["three_positive"]==3 and d["scope"]["two_abstain"]==2
    assert d["release"]["production"]=="BLOCKED"


@pytest.mark.parametrize("index",[0,1,2])
def test_original_source_and_claims_produce_disjoint_layout(index):
    r,b,v,p=get(index)
    l=layout(v)
    assert l["claims"]==["C1","C2"]
    assert l["labels_in_distinct_gutter"] is True
    assert len(l["sha256"])==64
    assert set(l["safe_regions"])=={"heading","plot","callout","conclusion"}
    assert min(l["type_sizes"].values())>=28
    a=l["geometry"]["reference_final"]
    q=l["geometry"]["translated_final"]
    assert a[0]==q[0]==X1
    assert q[1]==Y1
    assert l["reference_slope_delta_y"]==pytest.approx(l["translated_slope_delta_y"],abs=.000025)
    assert l["vertical_intercept_shift"]>0
    assert l["host_verified_spatial_layout"] if "host_verified_spatial_layout" in l else True
    assert b["contracts"]["visual_director_gate"]=="CORE_READY"
    assert b["contracts"]["pedagogy_gate"]=="V3_09_VALIDATED"


@pytest.mark.parametrize("index",[0,1,2])
def test_natively_compilable_large_chart_and_same_curve_motion(index):
    r,b,v,p=get(index)
    code=finite_source(b["trace"],[10.0]*6,v,p)
    compile(code,"<v387-finite>",'exec')
    assert code.count("V387_SPEECH_SCENE_")==6
    assert "v387_1_reference=DashedLine" in code
    assert "v387_1_shifted=Line" in code
    assert "Transform(v387_1_curve,v387_1_shifted)" in code
    assert "v387_1_marker.animate.shift" in code
    assert "FadeIn(v387_1_callout_value)" in code
    assert "font_size=46" in code
    assert "font_size=34" in code and "font_size=33" in code
    assert code.count("self.wait(2/15)")==1
    assert code.count("run_time=26/15")==2
    assert "Square(" not in code
    old=v386_source(b["trace"],[10.0]*6,v,p)
    assert "V387_SPEECH_SCENE_" not in old


@pytest.mark.parametrize("index",[3,4])
def test_unknown_chemistry_history_do_not_render_static_cards(index):
    a=compile_question(rows()[index],ROOT)
    assert a["status"]=="ABSTAIN"
    assert a["video"] is None


def test_semantic_role_specific_labels_do_not_use_topic_dispatch():
    math=get(0)[2];phys=get(1)[2]
    assert math["role"]=="input_output_line"
    assert phys["role"]=="velocity_vs_elapsed_time"
    assert math["horizontal_label"]=="x (input)"
    assert phys["horizontal_label"]=="t (elapsed time)"
    code=(ROOT/"learnflow_v3/v387_readable_affine_continuity.py").read_text()
    for forbid in ("if topic ==","if case_id ==","linear_output_new",
                   "accelerating_new","counterfactual_physics_heldout"):
        assert forbid not in code


def test_forged_intercept_or_delta_does_not_preserve_slope():
    role=deepcopy(get(1)[2])
    role["verified_values"]["initial"]="14"
    with pytest.raises(Blocked,match="V385_SOURCE_AFFINE_NUMBERS_NOT_CONSERVED"):
        layout(role)
    role=deepcopy(get(1)[2])
    role["verified_values"]["change"]="20"
    with pytest.raises(Blocked):
        layout(role)


def test_reversed_false_geometry_rejected():
    role=deepcopy(get(1)[2])
    role["verified_values"]["final"]="0"
    with pytest.raises(Blocked):
        layout(role)


def test_overlapping_boxes_are_rejected_before_native_render(monkeypatch):
    from learnflow_v3 import v387_readable_affine_continuity as m
    r=deepcopy(RECTS);r["callout"]=r["plot"]
    monkeypatch.setattr(m,"RECTS",r)
    with pytest.raises(Blocked,match="V385_VISUAL_LABEL_OR_PLOT_ZONES_OVERLAP"):
        layout(get(0)[2])


def test_wrong_voice_claim_not_renderable():
    r,b,v,p=get(1)
    swapped=deepcopy(p)
    swapped[4]["claim_id"]="C1"
    with pytest.raises(Blocked):
        finite_source(b["trace"],[10.0]*6,v,swapped)


def test_no_short_voiced_phase_padded_into_a_fake_scene():
    r,b,v,p=get(1)
    with pytest.raises(Blocked):
        finite_source(b["trace"],[2.0]*6,v,p)


def test_native_gate_attests_real_readability_zones_and_translation():
    assert GRAPH[2]<RIGHT_CALLOUT[0]
    assert GRAPH[3]<ANSWER[1]
    code=(ROOT/"learnflow_v3/v387_native_readability_gate.py").read_text()
    for token in ("verify_native_phases(","_frame(","_mask_cyan","real_curve_centroid_rise_px",
                  "V387_C2_INTERCEPT_NOT_VISUALLY_TRANSLATED",
                  "V387_NO_LEGIBLE_NUMERIC_CALLOUT_IN_GUTTER"):
        assert token in code


def test_runner_keeps_original_pcm_and_strict_decoder():
    code=(ROOT/"scripts/run_v3_87_readability_native.py").read_text()
    for token in ("semantic_phases(","align_real_wav(","_audio(","_docker_manim(",
                  "deterministic_mux(","_codec_and_pixel_gates(",
                  "full_native_decode","review=verify("):
        assert token in code
    assert "model_api_calls" in code


def test_source_layout_cannot_claim_word_level_alignment():
    _,_,_,phases=get(0)
    assert all(p["word_timestamps"]=="NOT_AVAILABLE_NOT_FABRICATED" for p in phases)
    assert not any("per-word-alignment-pass" in p["narration"] for p in phases)


def test_v386_default_draw_gate_remains_frozen_with_explicit_opt_in_only():
    old=(ROOT/"learnflow_v3/v386_native_speech_visual_gate.py").read_text()
    new=(ROOT/"learnflow_v3/v387_native_readability_gate.py").read_text()
    assert 'line_motion_contract="DRAW_REVEAL"' in old
    assert 'late["curve_cyan"]>early["curve_cyan"]+300' in old
    assert 'line_motion_contract="C2_SOURCE_PRESERVING_TRANSLATION"' in new
    assert "real_curve_centroid_rise_px" in new
