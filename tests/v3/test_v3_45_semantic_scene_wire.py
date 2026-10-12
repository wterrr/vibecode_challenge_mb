"""V3-45 strict semantic wire: two genuine structural families, mock JSON only.

Negative controls reject unsupported schema and arbitrary generated Python;
the tests never send provider requests, and real-model attribution is forbidden.
"""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.compatible_scene_protocol import _forbid_unsupported
from learnflow_v3.semantic_scene_wire import (
    SceneWire,SYNTHETIC_ORIGIN,VERSION,
    decode_model_facing_scene,portable_semantic_schema,
    compile_scene,fraction_lesson,
)
from learnflow_v3.semantic_scene_offline_fixtures import fixture_cases
from scripts.run_v3_45_semantic_offline import PREREG

ROOT=Path(__file__).resolve().parents[2]


def test_early_preregister_scope_and_no_paid_requests():
    p=json.loads((ROOT/PREREG).read_text())
    assert p["checkpoint"]=="V3-45" and p["preregistered_before_implementation"] is True
    assert p["parent_sha"]=="734f212af4326e589674b1df9d1af152587ba9bd"
    assert p["model_http_requests"]==0 and p["provider_authenticated_gets"]==0
    assert len(p["frozen_topics"])==2
    assert {c["kind"] for c in p["frozen_topics"]}=={"ordered_process","fraction_equivalence"}


def test_portable_schema_strict_required_budget_and_two_distinct_families():
    s=portable_semantic_schema()
    Draft202012Validator.check_schema(s)
    assert _forbid_unsupported(s)<1000
    assert s["properties"]["family"]["enum"]==["fraction_equivalence","ordered_process"]
    assert set(s["required"])==set(s["properties"])
    assert s["additionalProperties"] is False
    assert "anyOf" not in json.dumps(s)
    assert "$ref" not in json.dumps(s)
    assert "minimum" not in json.dumps(s)
    for item in fixture_cases().values():
        Draft202012Validator(s).validate(item)


@pytest.mark.parametrize("fixture_id",["v345-synthetic-fractions","v345-synthetic-process"])
def test_offline_wire_decodes_then_host_compiles_safe_not_model_python(fixture_id):
    p=decode_model_facing_scene(fixture_cases()[fixture_id])
    assert p.family==("fraction_equivalence" if "fractions" in fixture_id else "ordered_process")
    code=compile_scene(p,[9.2,9.933,10.4,9.8])
    assert "class GeneratedLesson(Scene):" in code
    assert "from manim import *" in code
    assert "OPENROUTER" not in code and "subprocess" not in code
    assert "__import__" not in code
    if p.family=="fraction_equivalence":
        assert "TransformFromCopy" in code and "(1×2)/(2×2) = 2/4" in code
        assert len(fraction_lesson(p).partitions)==2
    else:
        assert "MoveAlongPath" in code
        assert "Arrow(" in code
        assert "RoundedRectangle" in code
        assert "TransformFromCopy" not in code


@pytest.mark.parametrize("mutation",[
 "extra_root_field","provider_exec_field","bad_family","out_of_range_geometry",
 "extra_graphic_python","dangling_process_edge","process_cycle","reversed_traversal",
 "missing_process_step","reveal_order_swap","edge_before_nodes",
 "flow_contains_partition","fraction_contains_flow_node","wrong_fraction_proof",
 "invalid_math_rewrite","fraction_unequal_whole","missing_proof_event",
 "overlapping_events","out_of_beat_events","forged_claim","missing_claim_coverage",
 "duplicate_ids","narration_numeric_drift","unknown_event","unsafe_object_id"
])
def test_fail_closed_mutated_mock_provider_json(mutation):
    cases=fixture_cases()
    raw=deepcopy(cases["v345-synthetic-process" if mutation in (
        "dangling_process_edge","process_cycle","reversed_traversal",
        "missing_process_step","reveal_order_swap","edge_before_nodes",
        "flow_contains_partition") else "v345-synthetic-fractions"])
    if mutation=="extra_root_field":raw["surprise"]="model code"
    elif mutation=="provider_exec_field":raw["python"]="print('hello')"
    elif mutation=="bad_family":raw["family"]="visual_anything"
    elif mutation=="out_of_range_geometry":raw["graphics"][0]["x"]=100
    elif mutation=="extra_graphic_python":raw["graphics"][0]["python"]="unsafe()"
    elif mutation=="dangling_process_edge":raw["graphics"][3]["dst"]="unseen"
    elif mutation=="process_cycle":raw["graphics"][4]["dst"]="start"
    elif mutation=="reversed_traversal":
        raw["beats"][1]["events"][1]["target"]="edge_verify_finish"
    elif mutation=="missing_process_step":raw["graphics"][2]["id"]="deleted"
    elif mutation=="reveal_order_swap":
        raw["beats"][0]["events"][1]["target"]="verify"
        raw["beats"][0]["events"][2]["target"]="start"
    elif mutation=="edge_before_nodes":
        raw["beats"][0]["events"][0]["kind"]="reveal_edge"
        raw["beats"][0]["events"][0]["target"]="edge_start_verify"
    elif mutation=="flow_contains_partition":raw["partitions"]=[{"id":"x","part_ids":["a","b"],"shaded_ids":["a"],"numerator":1,"denominator":2}]
    elif mutation=="fraction_contains_flow_node":raw["graphics"][0]["kind"]="node";raw["graphics"][0]["text"]="Start"
    elif mutation=="wrong_fraction_proof":
        next(g for g in raw["graphics"] if g["id"]=="proof")["text"]="(1×3)/(2×3) = 2/4"
    elif mutation=="invalid_math_rewrite":raw["relations"][0]["multiply_by"]=3
    elif mutation=="fraction_unequal_whole":
        for x in raw["graphics"]:
            if x["id"].startswith("q"):x["height"]=1.6
    elif mutation=="missing_proof_event":
        raw["beats"][2]["events"][0]["target"]="summary"
    elif mutation=="overlapping_events":raw["beats"][0]["events"][1]["at"]=0
    elif mutation=="out_of_beat_events":raw["beats"][0]["events"][0]["at"]=.95;raw["beats"][0]["events"][0]["span"]=.2
    elif mutation=="forged_claim":raw["beats"][0]["claim_ids"]=["P3"]
    elif mutation=="missing_claim_coverage":raw["beats"][2]["claim_ids"]=["F1"]
    elif mutation=="duplicate_ids":raw["graphics"][1]["id"]=raw["graphics"][0]["id"]
    elif mutation=="narration_numeric_drift":raw["beats"][0]["narration"]+=" 999."
    elif mutation=="unknown_event":raw["beats"][0]["events"][0]["kind"]="execute_code"
    elif mutation=="unsafe_object_id":raw["graphics"][0]["id"]="__import__"
    with pytest.raises((Blocked,ValueError,ValidationError)):
        decode_model_facing_scene(raw)


def test_cross_family_fixtures_do_not_share_topology_or_claim_bank():
    f,p=fixture_cases().values()
    assert f["family"]!=p["family"]
    assert f["partitions"] and f["relations"]
    assert not p["partitions"] and not p["relations"]
    assert any(o["kind"]=="edge" for o in p["graphics"])
    assert not any(o["kind"]=="edge" for o in f["graphics"])
    assert {claim for b in f["beats"] for claim in b["claim_ids"]}=={"F1","F2","F3"}
    assert {claim for b in p["beats"] for claim in b["claim_ids"]}=={"P1","P2","P3"}


def test_workflow_offline_no_model_and_two_native_renders():
    wf=(ROOT/".github/workflows/v3-45-semantic-offline.yml").read_text()
    script=(ROOT/"scripts/run_v3_45_semantic_offline.py").read_text()
    assert "manimcommunity/manim:v0.19.0" in wf
    assert "run_v3_45_semantic_offline.py" in wf
    assert "OPENROUTER_API_KEY" not in wf
    assert "secrets.OPENROUTER" not in wf
    assert "deterministic_mux" in script
    assert "inspect_candidate" in script
    assert "OFFLINE_TWO_FAMILY_NATIVE_VIDEO_PASS_NOT_MODEL_PROOF" in script
