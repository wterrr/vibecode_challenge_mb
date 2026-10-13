"""V3-57 offline host-storytelling: semantic evidence not motion decoration."""
from dataclasses import replace
import copy,math
from PIL import ImageChops,ImageStat
import pytest

from learnflow_v3.pedagogical_storytelling_slice import (
    WIDTH,HEIGHT,FPS,STEPS,CLAIMS,REFERENT,Plan,Beat,facts,plan,validate,
    render_image,hash_obj)
from scripts.run_v3_57_pedagogical_slice import check_registration,parity_with_reused_ledgers

def test_preregister_fixed_exact_parent_and_three_domains():
    reg=check_registration()
    assert reg["parent_sha"]=="38a8ba0c69a58ac18ad3296f6e847cbdeb6dbe91"
    assert reg["registered_before_implementation"]
    assert len(reg["frozen_input_cases"])==3
    assert reg["acceptance"]["production"]=="BLOCKED"
    assert reg["acceptance"]["pedagogy_quality"]=="UNRATED_UNTIL_HUMAN_AND_FAIR_AB"

def test_v3_52_attention_and_v3_49_fraction_host_ledgers_parity():
    parity_with_reused_ledgers()
    a=facts("attention_reversed_query")
    assert a["weights"][1]>a["weights"][0]
    assert math.isclose(sum(a["weights"]),1,abs_tol=1e-12)
    assert a["context"]==a["weights"]
    assert facts("fraction_equivalence")["same_area"] is True
    assert facts("process_heldout_unknown")["condition"]=="UNKNOWN_NOT_VERIFIED"

@pytest.mark.parametrize("name",list(STEPS))
def test_evidence_bound_five_step_semantic_plan(name):
    p=plan(name)
    assert validate(p)==facts(name)
    assert len(p.beats)==5
    assert all(b.claim_id==CLAIMS[name][i] for i,b in enumerate(p.beats))
    assert all(b.referent_id==REFERENT[name] for b in p.beats)
    assert p.beats[0].witness_type=="STATIC_COMPARISON"
    assert all(b.witness_type=="NATIVE_SEMANTIC_TRANSFORMATION" for b in p.beats[1:])
    assert p.origin=="HOST_SYNTHETIC_NOT_MODEL_AUTHORED"

@pytest.mark.parametrize("field,newval",[
    ("evidence_sha256","0"*64),("origin","LIVE_MODEL_AUTHORED")])
def test_sham_evidence_or_authorship_fails(field,newval):
    p=plan("attention_reversed_query")
    with pytest.raises(ValueError):
        validate(replace(p,**{field:newval}))

@pytest.mark.parametrize("name",list(STEPS))
def test_reordered_forged_claim_id_or_narration_is_rejected(name):
    p=plan(name)
    with pytest.raises(ValueError):
        validate(replace(p,beats=tuple(reversed(p.beats))))
    bad=replace(p.beats[1],claim_id="A4" if name!="attention_reversed_query" else "P2")
    with pytest.raises(ValueError):
        validate(replace(p,beats=p.beats[:1]+(bad,)+p.beats[2:]))
    with pytest.raises(ValueError):
        validate(replace(p,beats=(replace(p.beats[0],narration="Claim already proved"),)+p.beats[1:]))

@pytest.mark.parametrize("name,index",[
    ("attention_reversed_query",1),
    ("fraction_equivalence",2),
    ("process_heldout_unknown",2)])
def test_semantic_visual_motion_changes_actual_pillow_pixels(name,index):
    p=plan(name)
    before=render_image(p,index,0.05)
    after=render_image(p,index,0.90)
    assert before.size==after.size==(WIDTH,HEIGHT)
    change=ImageStat.Stat(ImageChops.difference(before,after))
    assert sum(change.mean)/3>0.05, "Expected native semantic operation to change visible pixels"

def test_unknown_condition_not_laundered_to_pass():
    p=plan("process_heldout_unknown")
    evidence=facts(p.case_id)
    assert evidence["success_claim"] is False
    assert evidence["condition"]=="UNKNOWN_NOT_VERIFIED"
    im=render_image(p,4,1)
    assert im.size==(1280,720)
    wrong=replace(p.beats[3],narration="Condition passed")
    with pytest.raises(ValueError):
        validate(replace(p,beats=p.beats[:3]+(wrong,)+p.beats[4:]))

def test_unmatched_v355_and_human_outcome_are_not_measured():
    reg=check_registration()
    assert reg["acceptance"]["model_creativity"]=="NOT_TESTED"
    assert reg["acceptance"]["word_level_sync"]=="UNMEASURED"
    assert reg["acceptance"]["frame_pixel_witness_not_learning_quality"] is True
