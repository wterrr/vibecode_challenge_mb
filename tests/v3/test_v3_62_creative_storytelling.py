"""V3-62 strict negative gates: static structural creativity != genuine model authorship."""
from __future__ import annotations
from dataclasses import replace
import json
from fractions import Fraction

import pytest
from PIL import ImageChops, ImageStat
from learnflow_v3.creative_pedagogical_director import (
    ACTS,CASES,STYLE,CLAIMS,ORIGIN,Blocked,candidate,digest,
    exact_facts,proposed_visual_choice,receipt,validate,witness
)
from learnflow_v3.creative_pedagogical_native import (
    render_frame,scene_objects,visible_state,W,H,FPS,diff
)
from scripts.run_v3_62_creative_storytelling import registration, STYLE as CASE_STYLE


def test_preregistered_three_novel_domains_and_truth_proofs():
    reg=registration()
    assert reg["registration"]=="FIRST_CHILD_COMMIT"
    assert len(reg["frozen_heldout_topics"])==3
    assert reg["design_contract"]["semantics"][0]=="maintain_referent_identity"
    assert (CASES[0],CASES[1],CASES[2])==tuple(
        r["id"] for r in reg["frozen_heldout_topics"])
    assert Fraction(3,8)+Fraction(5,8)==1
    f=exact_facts(CASES[1])
    assert f["positions_m"]==[0,3,6,9,12]
    assert f["final_distance_m"]==12
    assert exact_facts(CASES[2])["reactant_atoms"]=={"H":4,"O":2}
    assert exact_facts(CASES[2])["product_atoms"]=={"H":4,"O":2}


@pytest.mark.parametrize("case",CASES)
def test_approved_claim_narration_referent_and_variable_style(case):
    p=candidate(case,CASE_STYLE[case])
    q=candidate(case,"witness_first" if p.visual_style=="focus_first" else "focus_first")
    for story in (p,q):
        assert validate(story)==exact_facts(case)
        assert story.origin==ORIGIN and story.publication_allowed is False
        assert tuple(b.act for b in story.acts)==ACTS
        assert tuple(b.claim_id for b in story.acts)==CLAIMS[case]
        assert len(set(b.referent_id for b in story.acts))==1
        assert len(set(b.narration for b in story.acts))==5
        r=receipt(story)
        assert r["precondition_before_result"] is True
        assert r["result_after_transformation"] is True
        assert r["human_quality"]=="UNRATED" and r["model_creativity"]=="NOT_TESTED"
    a=render_frame(p,2,.5)
    b=render_frame(q,2,.5)
    assert diff(a,b)>.01, "alternative permitted visual choice must affect image pixels"


@pytest.mark.parametrize("case",CASES)
def test_no_result_before_end_of_transformation(case):
    p=candidate(case)
    for act in (0,1,2):
        for progress in (0,.01,.4,.99,1.):
            state=witness(p,act,progress)
            field={
                CASES[0]:"complement_label_visible",
                CASES[1]:"final_12_label_visible",
                CASES[2]:"balanced_equation_visible"
            }[case]
            assert state[field] is False
            assert scene_objects(p,act,progress)["result_visible"] is False
    assert scene_objects(p,3,0)["result_visible"] is True
    assert visible_state(p,0,.1,control=True)["result_visible"] is True


@pytest.mark.parametrize("case",CASES)
def test_native_image_is_real_1280_and_semantically_changes(case):
    p=candidate(case)
    before=render_frame(p,2,.12)
    after=render_frame(p,3,1)
    hold=render_frame(p,2,.12,control=True)
    assert before.size==after.size==hold.size==(W,H)
    assert diff(before,after)>.30
    assert diff(before,hold)>.30
    control_late=render_frame(p,2,.95,control=True)
    assert diff(control_late,hold)<.001
    assert FPS==15


def test_probability_eight_persistent_ids_complement_never_loses_total():
    p=candidate(CASES[0])
    for act,phase in ((0,0),(1,0),(2,.18),(2,.85),(3,1),(4,0)):
        e=scene_objects(p,act,phase)
        assert len(e["eight_objects"])==8
        assert len({z["id"] for z in e["eight_objects"]})==8
        assert sum(z["event"] for z in e["eight_objects"])==3
        assert e["total"]==8 and e["selected"]+e["complement"]==8


def test_physics_marker_identity_speed_and_earned_distance():
    p=candidate(CASES[1])
    history=[scene_objects(p,2,v/10)["marker_m"] for v in range(11)]
    assert history==sorted(history)
    assert history[0]==0 and history[-1]==12
    assert all(scene_objects(p,2,v/10)["marker_id"]=="moving_marker" for v in range(11))
    assert scene_objects(p,2,.2)["result_visible"] is False
    assert scene_objects(p,3,0)["result_visible"] is True


def test_chemistry_never_creates_or_destroys_atoms_and_does_not_claim_kinetics():
    p=candidate(CASES[2])
    canonical=None
    for act,phase in ((0,0),(1,0),(2,0),(2,.31),(2,1),(3,0),(4,1)):
        s=scene_objects(p,act,phase)
        elements={a["id"]:a["element"] for a in s["atoms"]}
        if canonical is None: canonical=elements
        assert elements==canonical
        assert sorted(a["id"] for a in s["atoms"])==sorted(
            ("H0","H1","H2","H3","O0","O1"))
        assert s["atom_counts"]=={"H":4,"O":2}
        assert s["chemical_kinetics"]=="NOT_CLAIMED"


@pytest.mark.parametrize("type_of_forgery,pattern",[
    ("evidence_sha256","FROZEN_LEDGER_DRIFT"),
    ("origin","UNTRUSTED_AUTHORSHIP"),
    ("version","UNTRUSTED_AUTHORSHIP"),
    ("publication_allowed","UNSUPPORTED_RELEASE_OR_WORD_ALIGNMENT"),
    ("word_level_alignment","UNSUPPORTED_RELEASE_OR_WORD_ALIGNMENT"),
    ("layout","UNSUPPORTED_LAYOUT_OR_STYLE"),
    ("visual_style","UNSUPPORTED_LAYOUT_OR_STYLE"),
])
def test_mutations_block_grounding_and_release(type_of_forgery,pattern):
    p=candidate(CASES[0])
    bad={"evidence_sha256":"f"*64,"origin":"MODEL_DID_IT",
        "version":"v999","publication_allowed":True,
        "word_level_alignment":"VERIFIED_NATIVE",
        "layout":"UNSUPPORTED_LAYOUT","visual_style":"dramatize"}
    with pytest.raises(Blocked,match=pattern):
        validate(replace(p,**{type_of_forgery:bad[type_of_forgery]}))


@pytest.mark.parametrize("field,value",[
    ("act","CLOSE"),("claim_id","FAKE"),("referent_id","different"),
    ("narration","I can assert a false fact."),("highlight","fabricated"),
)
def test_mutated_beat_rejected(field,value):
    p=candidate(CASES[1])
    bad=replace(p.acts[2],**{field:value})
    with pytest.raises(Blocked,match="CLAIM_REFERENT_OPERATION_NARRATION_OR_DEPENDENCY_DRIFT"):
        validate(replace(p,acts=p.acts[:2]+(bad,)+p.acts[3:]))


def test_candidate_wire_allowlisted_only_and_host_math_uneditable():
    p=candidate(CASES[0])
    raw={"case_id":p.case_id,"visual_style":p.visual_style,
         "evidence_sha256":p.evidence_sha256}
    assert proposed_visual_choice(raw)==p
    with pytest.raises(Blocked,match="UNTRUSTED_PROPOSAL_FIELDS"):
        proposed_visual_choice({**raw,"python":"print(1)"})
    with pytest.raises(Blocked,match="PROPOSAL_EVIDENCE_FORGED"):
        proposed_visual_choice({**raw,"evidence_sha256":"0"*64})
    with pytest.raises(Blocked,match="UNTRUSTED_PROPOSAL_VALUES"):
        proposed_visual_choice({**raw,"visual_style":123})
    with pytest.raises(Blocked,match="UNSUPPORTED_HELDOUT_FAMILY"):
        proposed_visual_choice({**raw,"case_id":"attention_reversed_query"})


def test_bad_timing_queries_fail_closed():
    p=candidate(CASES[0])
    for act,progress in ((-1,.2),(5,.2),(2,-.1),(2,1.1),(2,float("nan"))):
        with pytest.raises(Blocked,match="INVALID_TEMPORAL_QUERY"):
            witness(p,act,progress)
