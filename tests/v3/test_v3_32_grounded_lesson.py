"""V3-32 anti-drift, cross-source contract, causal timing and real frame checks."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json
import pytest
from pydantic import ValidationError
from learnflow_v3.lesson_semantic_contract import (
    STAGES, WorkedExample,LessonBeat,LessonSemanticContract,
    compile_lesson,audited_model_research,load_contract,default_example,
    verify_numeric_replay,compiled_narration,compiled_research,
)
from learnflow_v3.grounded_lesson_video import (
    draw_frame,assert_temporal_events,causal_path,state_for,
)
from learnflow_v3.cs_code_state_lesson import load_pinned_receipt
from learnflow_v3.sequence_renderer import SequenceRenderProfile,_mean_absolute_error
from learnflow_v3.paid_cs_lesson import Blocked

ROOT=Path(__file__).resolve().parents[2]
RECEIPT=ROOT/"reports"/"v3_31_v330_real_receipt_subset.json"


def record():
    return load_pinned_receipt(RECEIPT)


def test_real_provider_research_rejected_not_silently_repaired():
    c,a=load_contract(ROOT)
    assert len(a["issues"])==3 and a["decision"]=="REJECT"
    assert c.research_provenance=="HOST_DETERMINISTIC_SOURCE_TRACE_COMPILER"
    assert c.deprecated_model_research_status=="REJECTED_EXAMPLE_DRIFT"
    assert tuple(b.stage for b in c.beats)==STAGES
    assert len(c.claims)==3
    assert "plus 2 equals 5" in c.beats[3].spoken_text
    assert c.beats[3].stage=="evaluate" and c.beats[4].stage=="return"
    assert "double" not in " ".join(c.research_explanations).lower()


@pytest.mark.parametrize("edit",[
  {"constant":3},{"argument":4},{"result":6},{"operator":"-"},
  {"source_code":"def add_two(n):\n    return n * 2\n\nanswer = add_two(3)"},
  {"source_code":"def add_two(n):\n    return n + 2\n\nanswer = add_two(4)"},
  {"source_code":"def add_two(n):\n    return n + 2\n\nanswer = add_two(__import__('os').system('id'))"},
  {"source_code":"def add_two(n):\n    return n + 2\n\nanswer = add_two(3)\nprint(answer)"},
])
def test_mutated_result_argument_operator_or_malicious_ast_fail_closed(edit):
    v=default_example().model_dump()
    v.update(edit)
    with pytest.raises(ValidationError,match="DRIFT|UNSAFE|EXAMPLE"):
        WorkedExample.model_validate(v)


def test_generic_contract_supports_second_function_and_negative_result():
    source="def subtract_four(x):\n    return x - 4\n\noutput = subtract_four(2)"
    e=WorkedExample(function_name="subtract_four",parameter="x",destination="output",
                    operator="-",constant=4,argument=2,result=-2,source_code=source)
    assert "2 minus 4 equals -2" in compiled_narration(e)[3]
    assert "- 4" in compiled_research(e)[0]
    assert verify_numeric_replay(e)["certified_final_value"]==-2
    c,a=compile_lesson(record(),e)
    assert c.example.function_name=="subtract_four" and a["decision"]=="REJECT"


def test_typed_contract_rejects_claim_beats_research_and_narration_drift():
    c,a=load_contract(ROOT)
    data=c.model_dump()
    for field in ("wrong_value","wrong_claim","missing_evaluate","wrong_state","wrong_source"):
        obj=deepcopy(data)
        if field=="wrong_value":obj["beats"][3]["spoken_text"]=obj["beats"][3]["spoken_text"].replace("equals 5","equals 6")
        if field=="wrong_claim":obj["beats"][2]["claim_ids"]=["C_RETURN"]
        if field=="missing_evaluate":obj["beats"].pop(3)
        if field=="wrong_state":obj["beats"][1]["visual_state_key"]="state-return"
        if field=="wrong_source":obj["claims"][0]["sha256_source"]="0"*64
        with pytest.raises(ValidationError):
            LessonSemanticContract.model_validate(obj)


def test_actual_publisher_origin_and_mutated_model_examples_are_never_accepted():
    c,a=load_contract(ROOT)
    r=record()
    assert a["issues"][0]["claim_id"]=="C_DEFINE"
    r["research_claims"][1]["explanation"]="The function doubles 4 into 8."
    assert audited_model_research(r,c.example)["decision"]=="REJECT"


def test_five_typed_states_show_distinct_argument_parameter_calculation_return():
    c,_=load_contract(ROOT)
    s=[state_for(c,i) for i in range(5)]
    assert s[0]["argument"] is None
    assert s[1]["argument"]==3 and s[1]["parameter"] is None
    assert s[2]["parameter"]==3 and s[2]["expression"] is None
    assert s[3]["expression"]=="3 + 2 = 5" and s[3]["return_value"] is None
    assert s[4]["destination_value"]==5
    assert causal_path("define",.4) is None
    assert causal_path("bind",.1)[2]!=causal_path("bind",.8)[2]


def test_frame_causal_motion_and_computer_modern_blackboard():
    c,_=load_contract(ROOT)
    profile=SequenceRenderProfile(width=1280,height=720,fps=18,seconds_per_step=1)
    for i in range(5):
        a=draw_frame(c,i,.15,profile,c.beats[i].spoken_text)
        b=draw_frame(c,i,.8,profile,c.beats[i].spoken_text)
        assert a.getpixel((1,1))==(0,0,0)
        assert _mean_absolute_error(a,b)>.045


def test_timeline_forgery_out_of_order_wrong_duration_or_event_identity_is_blocked():
    c,_=load_contract(ROOT)
    beats=[];events=[];start=0
    for i,b in enumerate(c.beats):
        beats.append({"stage":b.stage,"frame_start":start,"frames":120})
        k=start+round(b.event_fraction*120)
        events.append({"stage":b.stage,"event_id":b.semantic_event_id,
                       "visual_state_key":b.visual_state_key,"frame":k,
                       "seconds":k/18,"beat_start_frame":start})
        start+=120
    assert_temporal_events(c,beats,events)
    for bad in ("time","late","event","stage"):
        modified=deepcopy(events)
        if bad=="time":modified[3]["seconds"]+=.4
        if bad=="late":modified[1]["frame"]=999999
        if bad=="event":modified[2]["event_id"]="event-return"
        if bad=="stage":modified[4]["stage"]="evaluate"
        with pytest.raises(Blocked):
            assert_temporal_events(c,beats,modified)
