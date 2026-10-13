"""V3-55 offline integrity; never exercises model/provider HTTP."""
from __future__ import annotations
from copy import deepcopy
import csv
import json
from pathlib import Path

import pytest
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.independent_pedagogical_quality import (
    CRITERIA, IDS, load_registration, verify_case_result,
    blank_review_csv, final_verdict)
from scripts.run_v3_55_independent_quality import build_new_cases, ROOT
from learnflow_v3.semantic_scene_wire import decode_model_facing_scene
from learnflow_v3.pedagogical_visual_grammar import offline_host_plan, validate_transformations
from learnflow_v3.grounded_fraction_claims import FractionTopic, ground, verify


def test_frozen_registration_parent_and_three_domains():
    reg = load_registration(ROOT)
    assert reg["frozen_baseline"]["artifact_id"] == 11738443652
    assert [x["family"] for x in reg["independent_cases"]] == [
        "fraction_equivalence", "ordered_process", "transformer_attention"]
    assert reg["acceptance"]["zero_provider_requests"] is True
    assert "not matched" in reg["frozen_baseline"]["matched_AB_warning"].lower() or (
        "not causal matched" in reg["frozen_baseline"]["matched_AB_warning"].lower())


def test_three_new_family_inputs_all_host_grounded():
    a, b, c = build_new_cases(load_registration(ROOT))
    assert a["id"] == "dev_" + IDS[0] and a["source"] == [2, 3]
    assert a["target"] == [4, 6]
    assert all(g["id"].startswith("z_") for g in b["graphics"])
    graph = decode_model_facing_scene(b)
    validate_transformations(graph, offline_host_plan(graph))
    assert c["query"] == [0, 1]
    assert c["stages"] == ["intro", "compare", "normalize", "transport", "compose"]


def test_fraction_forged_numeric_proof_fails_closed():
    t = FractionTopic(topic_id=IDS[0], numerator=2, denominator=3,
                      factor=2, target_numerator=4, target_denominator=6)
    original = ground(t)
    verify(original)
    tamper = original.model_copy(update={"proof": "2/3 = 5/6"})
    with pytest.raises(Blocked):
        verify(tamper)


def test_process_fabricated_positive_condition_rejected():
    _, raw, _ = build_new_cases(load_registration(ROOT))
    s = decode_model_facing_scene(raw)
    plan = offline_host_plan(s)
    probe = next(x for x in plan.actions if x.kind == "condition_probe")
    wrong = probe.model_copy(update={"outcome": "PASS"})
    bad = plan.model_copy(update={"actions": [wrong if x is probe else x for x in plan.actions]})
    with pytest.raises((Blocked, ValueError)):
        validate_transformations(s, bad)


def test_fraction_not_verified_by_hash_alone():
    x={"provider_posts":0,"evidence_verified":True,"factor":2,
       "fraction":[2,3],"target":[4,6],
       "semantic_cues":{"source_guides":[
           {"before_yellow_pixels":0,"after_yellow_pixels":22} for _ in range(3)]},
       "verified_numeric_proof_h264":{"pixel_count":33},
       "video":{"codec":"h264+aac","frames":320},
       "native_mp4_sha256":"a"*64}
    assert verify_case_result("fraction_equivalence", x)["human_quality"]=="UNRATED"
    bad=deepcopy(x)
    bad["semantic_cues"]["source_guides"][0]["before_yellow_pixels"]=20
    with pytest.raises(Blocked):
        verify_case_result("fraction_equivalence",bad)


def test_attention_pixel_counterfactual_must_agree_with_host_weights():
    x={"model_http_posts":0,"genuine_model_authored":False,
       "weights":[.33023845,.66976155],
       "causal_pixel_evidence":{"before":{"total_causal_pixels":0},
          "after":{"teal_pixels":5300,"amber_pixels":10800},
          "observed_teal_fraction":.33},
       "native_media":{"codec":"h264+aac","frames":800},
       "native_video_sha256":"b"*64}
    assert verify_case_result("transformer_attention",x)["human_quality"]=="UNRATED"
    bad=deepcopy(x);bad["causal_pixel_evidence"]["observed_teal_fraction"]=.72
    with pytest.raises(Blocked):
        verify_case_result("transformer_attention",bad)


def test_unknown_condition_must_remain_unknown():
    x={"model_api_posts":0,
       "frame_proof":{"outcome":"UNKNOWN_NOT_VERIFIED","yellow_check_cue_pixels":100},
       "process_node_overlap":{"status":"PASS"},
       "actual_video":{"codec":"h264+aac","frames":510},
       "output_mp4_sha256":"c"*64}
    assert verify_case_result("ordered_process",x)["human_quality"]=="UNRATED"
    bad=deepcopy(x);bad["frame_proof"]["outcome"]="PASS"
    with pytest.raises(Blocked):
        verify_case_result("ordered_process",bad)


def test_review_packet_contains_no_fabricated_people_or_scores(tmp_path):
    dest=tmp_path/"review.csv"
    blank_review_csv(dest)
    rows=list(csv.DictReader(dest.open()))
    assert len(rows)==3*len(CRITERIA)
    assert all(not r["score_1_to_5"] and not r["independent_reviewer_id"] for r in rows)
    assert all(r["review_status"]=="AWAITING_EXTERNAL_HUMAN_REVIEW" for r in rows)


def test_no_proxy_metric_can_produce_creative_pass():
    good=[{"family":s,"causal_pixel_proof":"PASS_BOUNDED_ORIGINAL_FAMILY_GATE"}
          for s in ("fraction_equivalence","ordered_process","transformer_attention")]
    assert "QUALITY_NO_GO" in final_verdict(good, human_ratings_supplied=False)
    assert "QUALITY_NO_GO" in final_verdict(good, human_ratings_supplied=True)
    with pytest.raises(Blocked):
        final_verdict(good[:2])
