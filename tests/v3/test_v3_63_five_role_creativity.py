"""V3-63 adversarial checks. Every candidate here is TEST_ONLY, never model output."""
from __future__ import annotations
import copy,json
from hashlib import sha256
import pytest
from learnflow_v3.creative_pedagogical_director import (
    CASES,REFERENTS,LAYOUTS,receipt,witness
)
from learnflow_v3.five_role_creative_admission import (
    VERSION,CATALOG,MAX_BYTES,ROLE_NAMES,admit,test_only_packet
)
from learnflow_v3.five_role_creative_native import (
    render_decision_frame,bounded_progress,mean_diff
)
from scripts.run_v3_63_five_role_creativity import registration

def mutate(case,variant,section,key,value):
    raw=json.loads(test_only_packet(case,variant))
    if section=="root":raw[key]=value
    else:raw[section][key]=value
    return json.dumps(raw,separators=(",",":")).encode()

def test_v363_first_child_frozen_three_domain_and_zero_model_budget():
    r=registration()
    assert tuple(r["allowed_cases"])==CASES
    assert tuple(r["role_order"])==ROLE_NAMES
    assert r["parent_pr"]==98 and r["registration"]=="FIRST_CHILD_COMMIT"
    assert r["acceptance"]["no_llm_api"] is True
    assert r["acceptance"]["independent_human_quality"]=="UNRATED"
    assert r["acceptance"]["student_learning"]=="NOT_MEASURED"
    assert r["acceptance"]["production"]=="BLOCKED"

@pytest.mark.parametrize("case",CASES)
@pytest.mark.parametrize("variant",(0,1))
def test_admission_all_5_roles_and_frozen_host_facts(case,variant):
    raw=test_only_packet(case,variant)
    typed,plan=admit(raw)
    assert typed.protocol_version==VERSION
    assert plan["story"].case_id==case
    assert plan["story"].evidence_sha256==typed.evidence_sha256
    assert plan["story"].publication_allowed is False
    assert plan["release"]=="BLOCKED"
    assert plan["model_authoring"]=="NOT_VERIFIED"
    assert plan["human_quality"]=="UNRATED"
    assert plan["learner_effect"]=="NOT_MEASURED"
    assert plan["risk_id"]==CATALOG[case]["risk"]
    assert len(typed.model_fields)==8
    assert receipt(plan["story"])["precondition_before_result"] is True
    assert receipt(plan["story"])["result_after_transformation"] is True
    assert witness(plan["story"],2,.99).get(
        "final_12_label_visible", False) is False

@pytest.mark.parametrize("case",CASES)
def test_both_decision_policies_have_physical_pixel_effect_but_not_semantic_invention(case):
    a=admit(test_only_packet(case,0))[1]
    b=admit(test_only_packet(case,1))[1]
    im1=render_decision_frame(a,2,.49)
    im2=render_decision_frame(b,2,.49)
    assert im1.size==im2.size==(1280,720)
    assert mean_diff(im1,im2)>.2
    assert a["story"].evidence_sha256==b["story"].evidence_sha256
    assert a["story"].acts[2].claim_id==b["story"].acts[2].claim_id
    assert a["story"].acts[2].narration==b["story"].acts[2].narration
    for x in (a,b):
        assert witness(x["story"],2,.3).get(
            "balanced_equation_visible",False) is False

def test_quantized_motion_has_different_physical_temporal_profile():
    a=admit(test_only_packet(CASES[1],0))[1]
    b=admit(test_only_packet(CASES[1],1))[1]
    aa=[bounded_progress(a,p/20) for p in range(21)]
    bb=[bounded_progress(b,p/20) for p in range(21)]
    assert aa[0]==bb[0]==0 and aa[-1]==bb[-1]==1
    assert len(set(bb))<=5 and len(set(aa))>5
    assert aa!=bb

@pytest.mark.parametrize("field,value,error",[
    ("evidence_sha256","0"*64,"FROZEN_HOST_LEDGER_MISMATCH"),
    ("case_id","attention_reversed_query","ROLE_WIRE_SCHEMA_BLOCKED"),
    ("protocol_version","v3-64","ROLE_WIRE_SCHEMA_BLOCKED"),
    ("hidden_python","print(1)","ROLE_WIRE_SCHEMA_BLOCKED"),
    ("allow_publish",True,"ROLE_WIRE_SCHEMA_BLOCKED"),
])
def test_root_wire_cannot_invent_truth_or_python(field,value,error):
    with pytest.raises(ValueError,match="V363_"+error):
        admit(mutate(CASES[0],0,"root",field,value))

@pytest.mark.parametrize("section,key,value,error",[
    ("cognitive_designer","misconception_id","misinformation","UNSOURCED_MISCONCEPTION"),
    ("cognitive_designer","probe_id","Invent truth","UNKNOWN_PROBE"),
    ("cognitive_designer","source_scope","VALIDATED_LEARNER_EVIDENCE","ROLE_WIRE_SCHEMA_BLOCKED"),
    ("narrative_designer","text_provenance","MODEL_GENERATED_FACTS","ROLE_WIRE_SCHEMA_BLOCKED"),
    ("narrative_designer","opening_focus","reveal_result_first","ROLE_WIRE_SCHEMA_BLOCKED"),
    ("visual_thinker","persistent_ref","wrong_object","CROSS_ROLE_REFERENT_OR_LAYOUT_MISMATCH"),
    ("visual_thinker","representation","GRAPH_WITH_FAKE_EDGE","CROSS_ROLE_REFERENT_OR_LAYOUT_MISMATCH"),
    ("visual_thinker","focus_mode","unbounded_camera","ROLE_WIRE_SCHEMA_BLOCKED"),
    ("motion_director","transformation_profile","teleport","ROLE_WIRE_SCHEMA_BLOCKED"),
    ("motion_director","reveal_at","QUESTION","ROLE_WIRE_SCHEMA_BLOCKED"),
    ("motion_director","narration_relation","MEASURED_WORD_ALIGNMENT","ROLE_WIRE_SCHEMA_BLOCKED"),
    ("visual_critic","risk_id","pass_all","CRITIC_NOT_GROUNDED"),
    ("visual_critic","early_answer","ALLOW","ROLE_WIRE_SCHEMA_BLOCKED"),
    ("visual_critic","human_quality","PASS","ROLE_WIRE_SCHEMA_BLOCKED"),
])
def test_cross_role_collusion_drift_and_unsupported_capabilities(section,key,value,error):
    with pytest.raises(ValueError,match="V363_"+error):
        admit(mutate(CASES[0],0,section,key,value))

@pytest.mark.parametrize("wire,error",[
    (b"","BAD_OR_OVERSIZE_WIRE"),
    (b'{"x":1,"x":2}',"DUPLICATE_JSON_KEY"),
    (b'{"v":NaN}',"NONFINITE_JSON"),
    (b"not-json","MALFORMED_JSON"),
    (b"\xff","MALFORMED_JSON"),
    (b" "*17000,"BAD_OR_OVERSIZE_WIRE"),
    (b"[]","ROLE_WIRE_SCHEMA_BLOCKED"),
])
def test_malformed_oversize_and_duplicate_keys_fail_closed(wire,error):
    with pytest.raises(ValueError,match="V363_"+error):
        admit(wire)

def test_no_unauthorized_mutation_to_true_precondition_state():
    for case in CASES:
        for variant in (0,1):
            typed,d=admit(test_only_packet(case,variant))
            before=render_decision_frame(d,2,.08)
            after=render_decision_frame(d,3,.1)
            assert mean_diff(before,after)>.1
            assert d["story"].origin=="HOST_AUTHORED_DETERMINISTIC_NOT_LLM"
