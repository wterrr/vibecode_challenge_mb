"""V3-59: falsify visible early results, invariant drift and fabricated quality."""
from dataclasses import replace
from PIL import ImageChops, ImageStat
import pytest

import learnflow_v3.causal_reveal as cr
from learnflow_v3.pedagogical_storytelling_slice import (
    STEPS,plan,facts,render_image,validate,WIDTH,HEIGHT
)
from scripts.run_v3_59_causal_reveal import registration,PARENT,PREREG
from learnflow_v3.creative_manim_ablation import Blocked


def test_registered_first_child_before_any_code_and_not_main():
    r=registration()
    assert PARENT=="d9d8830c0486a0c25b0ca924a091084b267425fe"
    assert PREREG=="148f1b73cdedce9ed1b1e4af6a9d5251d33903c4"
    assert r["parent_pr"]==92
    assert r["frozen_methods"]["baseline"].startswith("Use EXACT V3-57")
    assert r["acceptance"]["pedagogical_quality"].startswith("UNRATED")
    assert r["acceptance"]["learning_gain"]=="NOT_MEASURED"
    assert r["acceptance"]["real_model_creativity"]=="NOT_TESTED"
    assert r["acceptance"]["production"]=="BLOCKED"

@pytest.mark.parametrize("case",list(STEPS))
def test_host_reveal_check_and_full_decodable_pillow_geometry(case):
    p=plan(case)
    result=cr.verify_reveal_progression(p)
    assert result["semantic_gate"]=="PASS_HOST_ONLY"
    assert result["native_pillow_region_MAE"]>.1
    for t in (0,.15,.5,.8,1):
        im=cr.render_image_causal(p,2,t)
        assert im.size==(WIDTH,HEIGHT)
    assert p.origin=="HOST_SYNTHETIC_NOT_MODEL_AUTHORED"

def test_fraction_old_partition_and_area_witness_before_result():
    c="fraction_equivalence"
    start=cr.witness(c,2,0)
    middle=cr.witness(c,2,.6)
    end=cr.witness(c,2,1)
    assert (start["partitions"],start["shaded_parts"],start["fraction"])==(3,2,"2/3")
    assert middle["partitions"]==3 and middle["fraction"]=="2/3"
    assert end["partitions"]==6 and end["shaded_parts"]==4
    assert end["preserved_area"]=="2/3"
    assert end["shaded_parts"]/end["partitions"]==2/3
    assert facts(c)["same_area"] is True
    # Verify a real native drawn boundary appears at 1/6, not just state metadata.
    first=cr.render_image_causal(plan(c),2,0)
    last=cr.render_image_causal(plan(c),2,1)
    x=round(160+(1115-160)/6)-2
    assert first.getpixel((x,338))!=last.getpixel((x,338))
    assert first.getpixel((180,330))==last.getpixel((180,330))

def test_process_marker_arrival_before_action_activation_never_false_pass():
    c="process_heldout_unknown"
    assert cr.witness(c,2,0)["action_active"] is False
    assert cr.witness(c,2,.9)["action_active"] is False
    end=cr.witness(c,2,1)
    assert end["action_active"] is True
    assert end["marker_center_x"]==end["action_center_x"]==640
    assert end["marker_center_y"]==337
    assert end["action_arrival_verified"] is True
    assert cr.witness(c,2,.9)["marker_center_x"]<640
    assert cr.witness(c,2,.9)["action_arrival_verified"] is False
    assert cr.witness(c,2,1)["condition"]=="UNKNOWN_NOT_VERIFIED"
    assert cr.witness(c,2,1)["success_claim"] is False
    assert facts(c)["condition"]=="UNKNOWN_NOT_VERIFIED"
    a=cr.render_image_causal(plan(c),2,.9)
    b=cr.render_image_causal(plan(c),2,1)
    assert a.getpixel((640,290))!=b.getpixel((640,290))
    # Marker physically reaches the destination center, not y=426 off-graph.
    assert b.getpixel((640,337))!=a.getpixel((640,337))
    assert b.getpixel((640,337))==(236,239,244)  # WHITE arrival witness

def test_attention_do_not_announce_normalized_values_before_cue():
    c="attention_reversed_query"
    assert cr.witness(c,2,.1)["weights_visible"] is False
    assert cr.witness(c,2,.75)["weights_visible"] is False
    assert cr.witness(c,2,1)["weights_visible"] is True
    assert abs(cr.witness(c,2,1)["weights_sum"]-1)<1e-10
    a=cr.render_image_causal(plan(c),2,.1)
    b=cr.render_image_causal(plan(c),2,1)
    im_a=a.crop((100,359,315,490))
    im_b=b.crop((100,359,315,490))
    assert sum(ImageStat.Stat(ImageChops.difference(im_a,im_b)).mean)/3>.1

@pytest.mark.parametrize("field,val",[
    ("evidence_sha256","0"*64),
    ("origin","REAL_MODEL_AUTHORED")])
def test_no_forged_evidence_or_authorship(field,val):
    p=replace(plan("attention_reversed_query"),**{field:val})
    with pytest.raises(ValueError):
        cr.render_image_causal(p,2,.8)

@pytest.mark.parametrize("bad",[-.1,1.1,float("nan"),float("inf")])
def test_progress_out_of_bounds_fail_closed(bad):
    with pytest.raises(Blocked,match="V358_INVALID_PROGRESS"):
        cr.witness("fraction_equivalence",2,bad)

def test_unregistered_topic_and_beat_rejected():
    with pytest.raises(Blocked,match="V358_UNKNOWN_PLAN"):
        cr.witness("invented_topic",2,.5)
    with pytest.raises(Blocked,match="V358_UNKNOWN_PLAN"):
        cr.witness("fraction_equivalence",8,.5)

@pytest.mark.parametrize("setting,bad",[
    ("FRACTION_REVEAL",0),
    ("PROCESS_ACTION_ARRIVAL",0),
    ("ATTENTION_WEIGHT_REVEAL",0)])
def test_pre_reveal_mutations_trigger_semantic_guard(monkeypatch,setting,bad):
    monkeypatch.setattr(cr,setting,bad)
    topic={"FRACTION_REVEAL":"fraction_equivalence",
           "PROCESS_ACTION_ARRIVAL":"process_heldout_unknown",
           "ATTENTION_WEIGHT_REVEAL":"attention_reversed_query"}[setting]
    with pytest.raises(Blocked,match="V358_"):
        cr.verify_reveal_progression(plan(topic))

def test_non_motion_beats_remain_untouched_parent_pixel_for_pixel():
    for case in STEPS:
        p=plan(case)
        for idx in (0,1,3,4):
            # V3-59 changes only beat 2, so all other images are byte-identical.
            assert cr.render_image_causal(p,idx,.4).tobytes()==render_image(p,idx,.4).tobytes()


def test_three_arm_independent_panel_honesty_and_duplicate_rejection():
    from scripts.run_v3_59_causal_reveal import validate_three_arm_reviews
    from learnflow_v3.matched_pedagogy_ablation import CRITERIA
    cases=list(STEPS)
    key={"cases":{c:{c+"_"+x+".mp4":{"treatment":"hidden"}
                      for x in "ABC"} for c in cases}}
    assert validate_three_arm_reviews([],key)["gate"]=="NO_GO"
    one=[{"rater_id":"r01","case_id":c,"clip_id":c+"_"+x+".mp4",
          **{k:"3" for k in CRITERIA}}
         for c in cases for x in "ABC"]
    assert len(one)==9
    assert validate_three_arm_reviews(one,key)["gate"]=="NO_GO"
    with pytest.raises(Blocked,match="DUPLICATE_REVIEW"):
        validate_three_arm_reviews(one+[one[0]],key)
    with pytest.raises(Blocked,match="INCOMPLETE_NINE_VIDEO_PANEL"):
        validate_three_arm_reviews(one[:-1],key)
    with pytest.raises(Blocked,match="INVALID_SUBJECTIVE_RATING"):
        validate_three_arm_reviews([dict(one[0],clarity="9")]+one[1:],key)
    fake_complete=[dict(r,rater_id="r"+str(i)) for i in range(3) for r in one]
    report=validate_three_arm_reviews(fake_complete,key)
    # Synthetic rows exercise a validator, NOT proof of actual independent raters.
    assert report["quality"]=="RATINGS_RECEIVED_PENDING_PROVENANCE_AUDIT"
    assert report["student_learning_gain"]=="NOT_MEASURED"
    assert report["gate"]=="PANEL_PRESENT_NOT_LEARNING_PROOF"
