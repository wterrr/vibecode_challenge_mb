"""V3-54 offline mocked model JSON wire acceptance and decoded visual QA."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator

from learnflow_v3.creative_scene_fixtures import fixtures
from learnflow_v3.creative_candidate_acceptance import (
    MOCK_ORIGIN,VERSION,MAX_BYTES,
    candidate_schema,packet_for_fixture,mock_candidate_bytes,accept)
from learnflow_v3.creative_visual_quality_gate import (
    measure_frames,distinguish,OCCUPANCY_MIN)
from learnflow_v3.creative_manim_ablation import Blocked
from scripts.run_v3_54_model_candidate_quality import registered,NAMES

ROOT=Path(__file__).resolve().parents[2]


def payload(source_id="tokens_as_network"):
    return packet_for_fixture(fixtures()[source_id])

def encoded(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True).encode("utf-8")

def check_bad(obj,stage=None):
    result,diag=accept(encoded(obj))
    assert result is None
    assert diag["status"]=="BLOCKED" and diag["real_provider_calls"]==0
    assert diag["raw_candidate_stored"] is False
    if stage:assert diag["stage"]==stage
    return diag


def test_frozen_preregister_first_and_no_inference():
    spec=registered()
    assert spec["parent_pr"]==87
    assert spec["parent_sha"]=="f5556e89199dc95fc00c4f7b82d17b8f19850e65"
    assert spec["case_ids"]==list(NAMES)
    assert spec["physical_quality"]["native_video_count"]==3
    assert spec["safety"]["max_model_provider_posts"]==0


def test_portable_jsonschema_has_strict_typed_nested_scene_contract():
    schema=candidate_schema()
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    assert "scenes" in schema["properties"]
    assert "beats" in schema["properties"]
    assert "model_author" not in schema["properties"]


@pytest.mark.parametrize("source_id",list(fixtures()))
def test_frozen_host_mock_wires_are_semantically_accepted(source_id):
    content=mock_candidate_bytes(fixtures()[source_id])
    result,diag=accept(content)
    assert diag["status"]=="ACCEPTED_OFFLINE_CONTRACT_ONLY"
    assert diag["stage"]=="accepted"
    assert result["source_class"]==MOCK_ORIGIN
    assert result["storyboard"].origin=="OFFLINE_HOST_STORYBOARD_NOT_MODEL"
    assert len(result["graphs"])==len(result["storyboard"].scenes)
    assert set(result["facts"]["claims"])=={"A1","A2","A3","A4"}
    assert not diag["raw_candidate_stored"]
    assert diag["real_provider_calls"]==0


@pytest.mark.parametrize("change,stage",[
    ("extra_root","json_schema"),("spoof_model","json_schema"),
    ("change_protocol","json_schema"),("unapproved_topic","json_schema"),
    ("wrong_wire_type","json_schema"),("bad_digest_syntax","json_schema"),
    ("tamper_fact_sha","evidence"),("unsupported_number","typed_schema"),
    ("python_code_field","json_schema"),("unknown_node_fact","semantic_graph"),
    ("invalid_relation_endpoint","semantic_graph"),
    ("wrong_claim","semantic_graph"),("unknown_action_target","semantic_graph"),
    ("no_scenes","json_schema"),("different_id","semantic_graph"),
])
def test_adversarial_model_shaped_packets_are_denied(change,stage):
    d=deepcopy(payload())
    if change=="extra_root":d["unexpected"]="model_message"
    if change=="spoof_model":d["real_provider_origin"]="gpt-6-luna"
    if change=="change_protocol":d["protocol_version"]="v3-unknown"
    if change=="unapproved_topic":d["topic_id"]="arbitrary_false_topic"
    if change=="wrong_wire_type":d["scenes"]="not_an_array"
    if change=="bad_digest_syntax":d["evidence_sha256"]="123"
    if change=="tamper_fact_sha":d["evidence_sha256"]="f"*64
    if change=="unsupported_number":d["scenes"][0]["nodes"][0]["label"]="Attention 777"
    if change=="python_code_field":d["scenes"][0]["nodes"][0]["code"]="__import__('os')"
    if change=="unknown_node_fact":d["scenes"][0]["nodes"][0]["fact_ref"]="imagined_key"
    if change=="invalid_relation_endpoint":d["scenes"][0]["relations"][0]["target"]="phantom"
    if change=="wrong_claim":d["beats"][0]["claims"]=["A4"]
    if change=="unknown_action_target":d["beats"][0]["actions"][0]["target"]="imaginary"
    if change=="no_scenes":d["scenes"]=[]
    if change=="different_id":d["scenes"][0]["nodes"][1]["id"]=d["scenes"][0]["nodes"][0]["id"]
    check_bad(d,stage)


def test_wire_rejects_nonjson_bad_utf8_nonfinite_and_oversize_without_copies():
    cases=[b"not json",b"\xff",b'{"x":NaN}',b"x"*(MAX_BYTES+1)]
    for bad in cases:
        result,diag=accept(bad)
        assert result is None and diag["status"]=="BLOCKED"
        assert diag["stage"]=="wire"
        assert not diag["raw_candidate_stored"]


def test_rejects_genuine_provider_attribution_and_no_untrusted_code_execution():
    d=payload()
    d["model_author"]="openai/gpt-6-luna"
    diag=check_bad(d,"json_schema")
    assert not any("gpt" in str(x) for x in diag.values())
    assert diag["origin"]==MOCK_ORIGIN


def _image(x:int,y:int):
    bg=np.zeros((720,1280,3),dtype=np.uint8)
    bg[:]=[8,11,17]
    bg[y:y+210,x:x+220]=[233,183,102]
    return bg


def test_decoded_pixel_proxy_distinguishes_real_geometry_without_model_calls():
    frames=[_image(100+i*175,220) for i in range(5)]
    d=measure_frames(frames)
    assert len(d["sample_frame_sha256"])==5
    assert min(d["non_background_pixel_fractions"])>OCCUPANCY_MIN
    assert d["max_temporal_difference"]>1.5
    other=[_image(70+i*80,420) for i in range(5)]
    third=[_image(250+i*130,90) for i in range(5)]
    links=distinguish([("a",frames,"sig_a"),("b",other,"sig_b"),("c",third,"sig_c")])
    assert len(links)==3
    assert all(x["peak_visible_difference"]>=2.5 for x in links)


def test_still_or_blank_or_identical_cases_fail_visual_quality():
    still=[_image(100,240)]*5
    with pytest.raises(Blocked,match="V354_VISUALLY_STATIC_STORY"):
        measure_frames(still)
    blank=[np.zeros((720,1280,3),dtype=np.uint8)]*5
    with pytest.raises(Blocked,match="V354_EMPTY_OR_EXCESSIVELY_FILLED"):
        measure_frames(blank)
    first=[_image(100+i*175,220) for i in range(5)]
    with pytest.raises(Blocked,match="V354_STORYBOARDS_ONLY_METADATA_DIFFER"):
        distinguish([("a",first,"sig_a"),("b",first,"sig_b"),("c",first,"sig_c")])
    with pytest.raises(Blocked,match="V354_STRUCTURAL_SCENEGRAPHS_IDENTICAL"):
        distinguish([("a",first,"s"),("b",first,"s"),("c",first,"u")])


def test_pipeline_does_not_use_model_key_and_preserves_legacy_freeze():
    w=(ROOT/".github/workflows/v3-54-model-candidate-quality.yml").read_text()
    runner=(ROOT/"scripts/run_v3_54_model_candidate_quality.py").read_text()
    for historic in ("test_v3_53_creative_director.py",
                     "test_v3_52_semantic_motion.py",
                     "test_v3_51_creative_scene_graph.py",
                     "test_v3_50_one_query_attention.py"):
        assert historic in w
    assert "verify_v2_core_freeze.py" in w
    assert "verify_learnflow_bench.py" in w
    assert "if-no-files-found: error" in w
    assert "OPENROUTER_API_KEY" not in w
    assert "_docker_manim" in runner
    assert "deterministic_mux" in runner
    assert "distinguish" in runner
