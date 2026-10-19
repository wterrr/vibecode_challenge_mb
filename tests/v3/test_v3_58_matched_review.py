"""V3-58 audit: finite authoring choices and matched review never imply learning."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from PIL import ImageChops,ImageStat

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.pedagogical_storytelling_slice import STEPS,plan,render_image,facts
from learnflow_v3.pedagogical_authoring_readiness import (
    ProposedStory,synthetic_candidate,certify_candidate,ORIGIN
)
from learnflow_v3.matched_pedagogy_ablation import (
    IDS,QUALITY,CRITERIA,make_review_packet,evaluate_submissions,
    source_case,require
)
from scripts.run_v3_58_matched_review import check_registration,validate_agent_readiness,PARENT

def test_first_commit_preregister_and_release_guard():
    p=check_registration()
    assert p["parent_sha"]==PARENT
    assert p["cases"]==list(IDS)
    assert p["acceptance"]["no_new_external_video_or_text_data"]
    assert p["acceptance"]["blind_review_quality"]=="UNRATED_UNTIL_INDEPENDENT_REVIEWERS"
    assert p["acceptance"]["model_authorship"]=="NOT_TESTED"
    assert p["acceptance"]["production"]=="BLOCKED"

@pytest.mark.parametrize("case",list(IDS))
def test_synthetic_only_author_choice_is_bounded(case):
    c=synthetic_candidate(case)
    o=ProposedStory.model_validate(c)
    proof=certify_candidate(c)
    assert len(o.observable_beats)==5
    assert proof["origin"]==ORIGIN
    assert proof["pedagogical_quality"]=="UNRATED"
    assert proof["real_model_authoring"]=="NOT_TESTED"
    assert not c["allow_publish"]
    assert c["ledger_sha256"]==plan(case).evidence_sha256

@pytest.mark.parametrize("case",list(IDS))
def test_strict_python_fixture_and_json_wire_roundtrip_share_host_validation(case):
    # Python's strict Tuple != list; JSON arrays are allowed through JSON mode.
    candidate=synthetic_candidate(case)
    assert isinstance(candidate["observable_beats"],tuple)
    parsed=json.loads(json.dumps(candidate))
    assert isinstance(parsed["observable_beats"],list)
    with pytest.raises(ValidationError,match="observable_beats"):
        ProposedStory.model_validate(parsed)
    host=certify_candidate(parsed)
    assert host["origin"]==ORIGIN
    assert host["approval"]=="DATA_SCHEMA_AND_HOST_PROVENANCE_ONLY"
    assert host["pedagogical_quality"]=="UNRATED"
    assert host["production"]=="BLOCKED"

    # The JSON wire adapter must NOT bypass proof-bearing adversarial validators.
    parsed["observable_beats"][0]["witness_mode"]="SEMANTIC_MOTION"
    with pytest.raises(ValidationError,match="V358_FAKE_MOTION_WITNESS"):
        certify_candidate(parsed)
    parsed=json.loads(json.dumps(candidate))
    parsed["observable_beats"].append(parsed["observable_beats"][0])
    with pytest.raises(ValidationError,match="observable_beats"):
        certify_candidate(parsed)
    parsed=json.loads(json.dumps(candidate))
    parsed["allow_publish"]=True
    with pytest.raises(ValidationError,match="allow_publish"):
        certify_candidate(parsed)


@pytest.mark.parametrize("case",list(IDS))
def test_authoring_must_not_invent_motion_for_static_hold(case):
    c=synthetic_candidate(case)
    c["observable_beats"][0]["witness_mode"]="SEMANTIC_MOTION"
    with pytest.raises(ValidationError,match="V358_FAKE_MOTION_WITNESS"):
        ProposedStory.model_validate(c)

@pytest.mark.parametrize("mutation",[
 lambda c:c.update(ledger_sha256="0"*64),
 lambda c:c.update(origin="REAL_MODEL_AUTHORED"),
 lambda c:c.update(allow_publish=True),
 lambda c:c["observable_beats"][1].update(claim_id="UNVERIFIED_CLAIM"),
 lambda c:c["observable_beats"][1].update(referent_id="different_token"),
 lambda c:c["observable_beats"][1].update(beat_index=4),
 lambda c:c["observable_beats"][1].update(display_lag_intent="LEAD"),
 lambda c:c["observable_beats"][2].update(witness_mode="OBSERVE_HOLD"),
 lambda c:c.update(extra_python="import os"),
])
def test_host_truth_fails_closed(mutation):
    c=synthetic_candidate("attention_reversed_query")
    mutation(c)
    with pytest.raises(ValidationError):
        ProposedStory.model_validate(c)

@pytest.mark.parametrize("case",list(IDS))
def test_motion_pixels_distinct_from_end_state_hold(case):
    p=plan(case)
    moves=[]
    for idx,beat in enumerate(p.beats):
        a=render_image(p,idx,.15)
        b=render_image(p,idx,.95)
        delta=sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3
        if beat.operation in ("SCORE_SELECTION","SOFTMAX_NORMALIZATION",
            "CONTENT_TRANSPORT","SUBDIVIDE","EQUIVALENCE_LINK",
            "STATE_TRANSITION","CONDITION_PROBE"):
            moves.append(delta)
    assert moves and max(moves)>.02
    assert p.origin=="HOST_SYNTHETIC_NOT_MODEL_AUTHORED"

def test_synthetic_offline_authoring_not_a_model_result():
    result=validate_agent_readiness()
    assert result["model_api_posts"]==0
    assert result["model_authorship"]=="NOT_TESTED"
    assert result["production"]=="BLOCKED"
    assert len(result["synthetic_schema_validations"])==3

def test_review_packet_is_blind_and_all_marks_blank(tmp_path):
    samples=[]
    for i,case in enumerate(IDS):
        motion=tmp_path/(case+"_motion.mp4")
        static=tmp_path/(case+"_static.mp4")
        motion.write_bytes(b"synthetic_video_motion_"+bytes([i]))
        static.write_bytes(b"synthetic_video_static_"+bytes([i]))
        samples.append({"case_id":case,
          "source_video":str(motion),"control_video":str(static)})
    dest=tmp_path/"reviewer_blinded"
    key=make_review_packet(samples,dest,PARENT)
    assert len(list(dest.glob("*.mp4")))==6
    assert len(key["case_treatments"])==3
    raw=(dest/"blank_review.csv").read_text()
    assert "motion" not in raw.lower() and "static" not in raw.lower()
    assert all(not line.split(",")[0] for line in raw.strip().splitlines()[1:])
    assert "UNRATED" in evaluate_submissions([],key)["review_quality"]

def test_rater_submission_requires_complete_independent_panel():
    names=[(case,case+"_"+grade+".mp4") for case in IDS for grade in ("A","B")]
    key={"case_treatments":{case:{name:{"treatment":"unrevealed"} for c,name in names if c==case}
        for case in IDS}}
    assert evaluate_submissions([],key)["quality_gate"]=="NO_GO_NO_REVIEWERS"
    one=[{"rater_id":"person_1","case_id":case,"clip_id":clip,
           **{k:"3" for k in CRITERIA}}
         for case,clip in names]
    assert evaluate_submissions(one,key)["quality_gate"]=="NO_GO_NO_COMPLETE_PANEL"
    with pytest.raises(Blocked,match="V358_INVALID_RATING"):
        evaluate_submissions([dict(one[0],clarity="6")]+one[1:],key)
    with pytest.raises(Blocked,match="V358_INCOMPLETE_REVIEW_PACKET"):
        evaluate_submissions(one[:-1],key)
    three=[dict(r,rater_id=f"person_{i}") for i in range(3) for r in one]
    report=evaluate_submissions(three,key)
    assert report["quality_gate"]=="REVIEW_DATA_AVAILABLE_NOT_CAUSAL_LEARNING_PROOF"
    assert report["human_learning_effect"]=="NOT_MEASURED"
