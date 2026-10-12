"""V3-47 preregistered adversarial grammar and held-out topology tests."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.semantic_scene_offline_fixtures import fixture_cases
from learnflow_v3.semantic_scene_wire import decode_model_facing_scene,compile_scene
from learnflow_v3.pedagogical_visual_grammar import (
    Transformation,TransformationPlan,GRAMMAR_VERSION,SYNTHETIC_GRAMMAR_ORIGIN,
    offline_host_plan,validate_transformations)
from scripts.run_v3_47_pedagogical_storytelling import heldout_process

ROOT=Path(__file__).resolve().parents[2]


def test_preregistered_truth_policy_baselines_and_no_model_requests():
    d=json.loads((ROOT/"benchmarks/learnflowbench/v3/v3_47_pedagogical_grammar_preregister.json").read_text())
    assert d["registered_before_implementation"]
    assert d["parent_sha"]=="6a3a980258c52bd9b83b58b6eaf042cb3f908694"
    assert d["baseline"]["v346_pr_run"] if "v346_pr_run" in d["baseline"] else d["baseline"]["run_id"]==38200776147
    assert d["acceptance"]["model_http_posts"]==0
    assert "No actual LLM-generated" in str(d["research_nonclaims"])
    assert "subdivide" in d["action_vocabulary"]
    assert "condition_probe" in d["action_vocabulary"]


@pytest.mark.parametrize("family_id",["v345-synthetic-fractions","v345-synthetic-process"])
def test_strict_claim_grounding_and_generated_host_code_family(family_id):
    s=decode_model_facing_scene(fixture_cases()[family_id])
    plan=offline_host_plan(s)
    event_bindings=validate_transformations(s,plan)
    assert len(event_bindings)>=2
    assert all(x["relative_span"]>0 for x in event_bindings)
    code=compile_scene(s,[8.66,8.53,8.8,9.2],visual_quality=True,
                       pedagogical_plan=plan)
    assert "V347" in code or "v347_" in code
    assert "subprocess" not in code and "__import__" not in code
    assert "from manim import *" in code
    assert "self.wait(.8)" in code or "self.wait(0.80000)" in code
    compile(code,"<trusted host source>","exec")
    if s.family=="fraction_equivalence":
        assert "DashedLine" in code and "Create(v347_cut_" in code
        assert "v347_equal_" in code and "TransformFromCopy" in code
        assert {x.kind for x in plan.actions}=={"subdivide","equivalence_link"}
    else:
        assert "CHECK ?" in code
        assert "MoveAlongPath" in code and "get_start()" in code
        assert "PASS" not in code and "FAIL" not in code
        assert {x.kind for x in plan.actions}=={"state_transition","condition_probe","causal_emphasis"}


def test_heldout_graph_rekeys_every_object_and_compiles_without_id_hardcode():
    raw=fixture_cases()["v345-synthetic-process"]
    alt=heldout_process(raw)
    assert {x["id"] for x in alt["graphics"]}.isdisjoint(
           {x["id"] for x in raw["graphics"]})
    assert any(x["x"]!=y["x"] or x["y"]!=y["y"]
               for x,y in zip(alt["graphics"],raw["graphics"]))
    assert [b["narration"] for b in alt["beats"]]==[b["narration"] for b in raw["beats"]]
    s=decode_model_facing_scene(alt)
    plan=offline_host_plan(s)
    source=compile_scene(s,[8.66,8.53,8.8,9.2],
                         visual_quality=True,pedagogical_plan=plan)
    assert "h_edge_start_verify" in source and "h_verify" in source
    assert "CHECK ?" in source and "PASS" not in source
    compile(source,"<heldout trusted Manim>","exec")


@pytest.mark.parametrize("mutation",[
 "fake_pass","unsupported_predicate","unknown_action","unknown_ref",
 "wrong_claim","wrong_factor","out_of_beat","illegal_code_payload",
 "wrong_source_node","wrong_event_id","missing_subdivision",
 "wrong_family_probe","fake_verified_state","duplicate_action"
])
def test_invalid_grammar_fails_closed(mutation):
    family="v345-synthetic-process" if mutation in (
        "fake_pass","unsupported_predicate","unknown_action","unknown_ref",
        "wrong_source_node","wrong_family_probe","fake_verified_state",
        "illegal_code_payload","duplicate_action") else "v345-synthetic-fractions"
    scene=decode_model_facing_scene(fixture_cases()[family])
    d=offline_host_plan(scene).model_dump()
    first=d["actions"][0]
    if mutation=="fake_pass":
        next(x for x in d["actions"] if x["kind"]=="condition_probe")["outcome"]="pass"
    elif mutation=="unsupported_predicate":
        first["predicate"]="secret condition satisfied"
    elif mutation=="unknown_action": first["kind"]="execute_python"
    elif mutation=="unknown_ref": first["subject_id"]="undefined_object"
    elif mutation=="wrong_claim": first["claim_id"]="P3"
    elif mutation=="wrong_factor": first["factor"]=3
    elif mutation=="out_of_beat": first["beat_index"]=3
    elif mutation=="illegal_code_payload":first["python"]="__import__('os')"
    elif mutation=="wrong_source_node":first["source_id"]="nonexistent_node"
    elif mutation=="wrong_event_id": first["event_target"]="random_object"
    elif mutation=="missing_subdivision":
        d["actions"]=[x for x in d["actions"] if x["kind"]!="subdivide"]
    elif mutation=="wrong_family_probe":first["kind"]="condition_probe"
    elif mutation=="fake_verified_state":
        next(x for x in d["actions"] if x["kind"]=="condition_probe")["outcome"]="verified"
    elif mutation=="duplicate_action":
        d["actions"].append(deepcopy(first))
    with pytest.raises((Blocked,ValidationError,ValueError)):
        plan=TransformationPlan.model_validate(d)
        validate_transformations(scene,plan)


def test_no_silent_fallback_to_baseline_when_pedagogy_plan_invalid():
    scene=decode_model_facing_scene(fixture_cases()["v345-synthetic-fractions"])
    d=offline_host_plan(scene).model_dump()
    d["actions"][0]["source_id"]="missing"
    with pytest.raises(Blocked):
        compile_scene(scene,[8.5]*4,visual_quality=True,
                      pedagogical_plan=TransformationPlan.model_validate(d))


def test_pipeline_is_offline_and_keeps_claim_grounding_and_native_media_evidence():
    runner=(ROOT/"scripts/run_v3_47_pedagogical_storytelling.py").read_text()
    workflow=(ROOT/".github/workflows/v3-47-pedagogical-storytelling.yml").read_text()
    assert "run_v3_47_pedagogical_storytelling.py" in workflow
    assert "38200776147" in workflow
    assert "deterministic_mux" in runner
    assert "inspect_first_edge" in runner and "_semantic_frame_proofs" in runner
    assert "inspect_candidate" in runner and "NO" not in runner[:20]
    assert "OPENROUTER_API_KEY" not in workflow
    assert "model_authenticated_gets" in runner
    assert "INDEPENDENT_PEDAGOGICAL_REVIEW_UNRATED.csv" in runner



def test_subdivision_axis_follows_geometry_and_rejects_invalid_colors():
    from learnflow_v3.pedagogical_visual_grammar import subdivision_axis
    base=fixture_cases()["v345-synthetic-fractions"]
    scene=decode_model_facing_scene(base)
    assert subdivision_axis(scene,"halves","quarters",2)=="vertical"
    bad=deepcopy(base)
    next(x for x in bad["graphics"] if x["id"]=="qshade1")["color"]="GREY"
    with pytest.raises((Blocked,ValidationError,ValueError)):
        scene_bad=decode_model_facing_scene(bad)
        validate_transformations(scene_bad,offline_host_plan(scene_bad))


def test_horizontal_subdivision_is_supported_without_fraction_fixture_ids():
    from learnflow_v3.pedagogical_visual_grammar import subdivision_axis
    base=deepcopy(fixture_cases()["v345-synthetic-fractions"])
    # Rotate the two whole diagrams independently by 90 degrees:
    # horizontal split lines must be derived from TARGET tile geometry.
    left=["hshade","hplain"]
    right=["qshade1","qshade2","qplain1","qplain2"]
    by_id={g["id"]:g for g in base["graphics"]}
    for ids,cx in ((left,-3.6),(right,2.1)):
        for ident in ids:
            t=by_id[ident]
            dx=t["x"]-cx
            t["x"]=cx
            t["y"]=round(.5+dx,3)
            t["width"],t["height"]=t["height"],t["width"]
    s=decode_model_facing_scene(base)
    assert subdivision_axis(s,"halves","quarters",2)=="horizontal"
    plan=offline_host_plan(s)
    code=compile_scene(s,[8.6,8.8,8.9,9.2],
                       visual_quality=True,pedagogical_plan=plan)
    assert "DashedLine" in code
    compile(code,"<safe horizontal source>","exec")
