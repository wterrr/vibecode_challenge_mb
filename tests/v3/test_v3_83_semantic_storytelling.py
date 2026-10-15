"""V3-83 frozen source-gated arithmetic to native geometry and adversarial tests."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.v382_query_evidence_bridge import compile_question, registered
from learnflow_v3.v381_finite_manim_compiler import source
from learnflow_v3.v383_semantic_unit_storytelling import (
    receipts, certify_event, emit_beat, SAFE_OPERATORS
)
from learnflow_v3.v383_native_unit_evidence import ROI

ROOT=Path(__file__).resolve().parents[2]


def cases():
    return registered(ROOT)["cases"]


def prereg():
    d=json.loads((ROOT/"benchmarks/learnflowbench/v3/v3_83_visual_storytelling_preregister.json").read_text())
    assert d["checkpoint"]=="V3-83"
    assert d["kind"]=="INDEPENDENT_VISUAL_FAILURE_PREREG_BEFORE_IMPLEMENTATION"
    assert d["baseline"]["parent"]["pr"]==119
    assert d["baseline"]["parent"]["head"]=="e9d7c502f25c6e9f9b8931a7a7c0df9a939c524b"
    assert d["locked_cases"]==[x["id"] for x in cases()]
    assert len(d["frozen_failures"])==3
    assert d["witness"]["late_elapsed_frames"]==88
    assert tuple(d["witness"]["pictorial_roi_xyxy"])==ROI
    return d


def test_preregistered_before_implementation():
    d=prereg()
    assert d["acceptance"]["native_three_required"]==3
    assert d["acceptance"]["negative_abstains_required"]==2
    assert d["acceptance"]["heldout_native_required"]==1
    assert d["acceptance"]["professional_visual_review"]=="NOT_PASS_UNTIL_INDEPENDENT_RUBRIC"


@pytest.mark.parametrize("index",range(3))
def test_real_contract_query_to_units(index):
    prereg()
    result=compile_question(cases()[index],ROOT)
    trace=result["trace"]
    certs=receipts(trace)
    assert [x["operator"] for x in certs]==["SCALE","ADD"]
    for x in certs:
        a,b=x["inputs"]
        assert x["result_units"]==(a*b if x["operator"]=="SCALE" else a+b)
        assert x["final_unit_count"]<=24
        if x["operator"]=="ADD":
            assert x["initial_unit_count"]==x["final_unit_count"]
    assert trace["all_numeric_outputs_verified"]
    assert result["contracts"]["pedagogy_gate"]=="V3_09_VALIDATED"
    assert result["contracts"]["visual_director_gate"]=="CORE_READY"
    original=source(trace,[12.0]*len(trace["events"]),no_upscale_text=True)
    native=source(trace,[12.0]*len(trace["events"]),
                  no_upscale_text=True,pedagogical_units=True)
    compile(native,"<v383-verified>",'exec')
    assert "V383_UNIT_WITNESS_STEP_0:SCALE" in native
    assert "V383_UNIT_WITNESS_STEP_1:ADD" in native
    assert "LaggedStart(*[TransformFromCopy" in native
    assert "merged_1 = list(units_left_1) + list(units_right_1)" in native
    assert "V383_UNIT_WITNESS_STEP" not in original
    assert "LaggedStart" not in original
    assert "V383" not in source(trace,[12.0]*len(trace["events"]))


def test_negative_domains_stay_abstain():
    for row in cases()[3:]:
        d=compile_question(row,ROOT)
        assert d["status"]=="ABSTAIN" and d["video"] is None


def test_geometry_tracks_data_not_topic():
    a=compile_question(cases()[0],ROOT)["trace"]
    b=compile_question(cases()[1],ROOT)["trace"]
    assert receipts(a)[0]["result_units"]==14
    assert receipts(b)[0]["result_units"]==8
    assert SAFE_OPERATORS=={"ADD","SCALE"}


@pytest.mark.parametrize("invalid",[-2,0,25,100,3.5])
def test_bad_unit_value_fails_closed(invalid):
    e=deepcopy(compile_question(cases()[0],ROOT)["trace"]["events"][0])
    e["operands"][0]={"kind":"scalar","n":invalid,"d":1}
    with pytest.raises((Blocked,TypeError,ValueError)):
        certify_event(e)


def test_tampered_claimed_unit_result_rejected():
    e=deepcopy(compile_question(cases()[0],ROOT)["trace"]["events"][0])
    e["actual"]["n"]+=1
    with pytest.raises(Blocked,match="V383_MATH_RESULT_OR_UNIT_COUNT_MISMATCH"):
        certify_event(e)


def test_fraction_not_disguised_as_unit():
    e=deepcopy(compile_question(cases()[1],ROOT)["trace"]["events"][0])
    e["operands"][0]={"kind":"scalar","n":3,"d":2}
    with pytest.raises(Blocked,match="V383_UNIT_PICTOGRAM_REQUIRES_POSITIVE_INTEGER"):
        certify_event(e)


def test_unsupported_operation_rejected():
    e=deepcopy(compile_question(cases()[1],ROOT)["trace"]["events"][0])
    e["kind"]="EQUIVALENT_PARTITION"
    with pytest.raises(Blocked,match="V383_UNSUPPORTED_VISUAL_OPERATOR"):
        certify_event(e)


def test_insufficient_narration_window_rejected():
    e=compile_question(cases()[0],ROOT)["trace"]["events"][0]
    with pytest.raises(Blocked,match="V383_INSUFFICIENT_SPEECH_BUDGET"):
        emit_beat(0,e,4.0)


def test_renderer_has_no_topic_identity_dispatch():
    s=(ROOT/"learnflow_v3/v383_semantic_unit_storytelling.py").read_text()
    for txt in ("if topic ==","if domain ==","if case_id ==",
                "linear_output_new","accelerating_new",
                "counterfactual_physics_heldout"):
        assert txt not in s


def test_full_media_and_pixel_gates_retained():
    s=(ROOT/"scripts/run_v3_83_semantic_storytelling.py").read_text()
    for txt in ("_codec_and_pixel_gates","deterministic_mux",
                "full_native_decode","witness(video,beats,trace)","pedagogical_units=True"):
        assert txt in s
