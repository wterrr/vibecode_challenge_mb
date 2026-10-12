"""V3-53 creative director autonomy is about finite plans, not provider calls."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from learnflow_v2.scenegraph.schema import SceneGraph
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.semantic_attention_motion import Case
from learnflow_v3.creative_motion_director import (
    VERSION,ORIGIN,DirectedBeat,DirectorPlan,plan_for,validated,
    compile_manim,narration,CLAIMS,FOCUS)
from scripts.run_v3_53_creative_director import manifest

ROOT=Path(__file__).resolve().parents[2]
PRE=manifest()

def case(row):
    q=tuple(row["query"])
    return Case(topic_id="query_matches_token_a" if q==(1,0) else "heldout_query_matches_token_b",
        query=q,keys=((1,0),(0,1)),values=((1,0),(0,1)),dim=2)

def plan(row):
    return plan_for(case(row),row["emphasis"],row["stages"])

def test_preregister_first_and_existing_parent_frozen():
    assert PRE["preregistration"]=="BEFORE_IMPLEMENTATION"
    assert PRE["parent_sha"]=="2be42bdfe4d0c242b67e8bfed3bae4f4e19ec9ff"
    assert PRE["acceptance"]["no_provider_requests"]
    assert len(PRE["preselected_fixtures"])==3
    assert len({tuple(i["stages"]) for i in PRE["preselected_fixtures"]})==3

@pytest.mark.parametrize("row",PRE["preselected_fixtures"])
def test_these_are_composed_plans_not_fixed_4_stage_v352(row):
    p=plan(row);v,f,g=validated(p)
    assert isinstance(g,SceneGraph)
    assert p.origin==ORIGIN and p.version==VERSION
    assert len(p.beats)==len(row["stages"])
    assert [b.op for b in p.beats]==row["stages"]
    assert all(b.claim_id==CLAIMS[b.op] for b in p.beats)
    assert {b.evidence_sha256 for b in p.beats}=={p.evidence_sha256}
    assert sum(f["weights"])==pytest.approx(1)
    code=compile_manim(p,[10.8]*len(p.beats))
    compile(code,"<v353_native_host>","exec")
    assert code.count("V353_BEAT_")==len(p.beats)
    assert "TransformFromCopy(bar_a,segment_a)" in code
    assert "TransformFromCopy(value_b,share_b)" in code
    assert "exec(" not in code and "subprocess" not in code
    assert "from manim import *" in code
    assert len(narration(p).beats)==len(p.beats)

def test_planner_can_change_focus_and_visual_action_without_new_compiler():
    p=plan(PRE["preselected_fixtures"][0])
    data=p.model_dump()
    data["beats"][2]["focus_ref"]="weight_b"
    data["beats"][2]["visual_mode"]="trace"
    changed=DirectorPlan.model_validate(data)
    validated(changed)
    assert compile_manim(p,[10]*len(p.beats))!=compile_manim(changed,[10]*len(changed.beats))
    assert "Flash(bar_b,color=YELLOW)" in compile_manim(changed,[10]*len(changed.beats))

@pytest.mark.parametrize("stages",[
    ["compare","normalize","compose"],
    ["normalize","compare","transport","compose"],
    ["compare","transport","normalize","compose"],
    ["compare","normalize","compose","transport"],
    ["intro","intro","compare","normalize","transport","compose"],
    ["compare","normalize","inspect","inspect","transport","compose"],
    ["inspect","compare","normalize","transport","compose"],
    ["compare","normalize","transport","compose","intro"]])
def test_bad_causal_compositions_rejected(stages):
    with pytest.raises((ValidationError,Blocked,ValueError,KeyError)):
        plan_for(case(PRE["preselected_fixtures"][0]),"network",stages)

@pytest.mark.parametrize("mutation",[
    "wrong_origin","wrong_sha","bad_claim","wrong_stage_sha",
    "wrong_focus","untrusted_code","bad_style","wrong_case",
    "model_copy_bypass","unknown_stage"])
def test_mutations_never_claim_grounded_motion(mutation):
    p=plan(PRE["preselected_fixtures"][0]);d=p.model_dump()
    if mutation=="wrong_origin":d["origin"]="GenuineModel"
    if mutation=="wrong_sha":d["evidence_sha256"]="0"*64
    if mutation=="bad_claim":d["beats"][1]["claim_id"]="A4"
    if mutation=="wrong_stage_sha":d["beats"][2]["evidence_sha256"]="f"*64
    if mutation=="wrong_focus":d["beats"][2]["focus_ref"]="query"
    if mutation=="untrusted_code":d["python"]="import os"
    if mutation=="bad_style":d["story_style"]="MANIM_AGENT_PYTHON"
    if mutation=="wrong_case":d["case"]["query"]=[1,1]
    if mutation=="unknown_stage":d["beats"][1]["op"]="unverified_operator"
    if mutation=="model_copy_bypass":
        with pytest.raises(Blocked):
            validated(p.model_copy(update={"evidence_sha256":"f"*64}))
        return
    with pytest.raises((ValidationError,Blocked,ValueError)):
        validated(DirectorPlan.model_validate(d))

def test_optional_post_compose_inspection_references_context():
    p=plan(PRE["preselected_fixtures"][2])
    assert p.beats[-1].op=="inspect" and p.beats[-1].focus_ref=="context"
    source=compile_manim(p,[10]*len(p.beats))
    assert "Indicate(segment_a" in source and "Circumscribe(context" in source

def test_v353_workflow_frozen_legacy_and_no_api_secrets():
    w=(ROOT/".github/workflows/v3-53-creative-director.yml").read_text()
    runner=(ROOT/"scripts/run_v3_53_creative_director.py").read_text()
    assert "test_v3_52_semantic_motion.py" in w
    assert "test_v3_51_creative_scene_graph.py" in w
    assert "verify_v2_core_freeze.py" in w
    assert "verify_learnflow_bench.py" in w
    assert "if-no-files-found: error" in w
    assert "runner.temp" in w
    assert "OPENROUTER_API_KEY" not in w
    assert "deterministic_mux" in runner
    assert "classify_colors" in runner
    assert "native_video_sha256" in runner
