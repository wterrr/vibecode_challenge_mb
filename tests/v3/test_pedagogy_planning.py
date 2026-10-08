"""V3-09 evidence-backed pedagogy, hero allocation, ablation and mutation tests."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from agent_contracts.lesson import LessonScript
from learnflow_v3.models import SemanticContractError, VisualTeachingPlan
from learnflow_v3.pedagogy_planner import (
    GroundedPedagogyPlan, HeroAblationPair, PedagogyPlannerRequest,
    compile_pedagogy_and_hero,verify_grounded_pedagogy_plan,
)
from scripts.verify_v3_pedagogy_planning import offline_demo


def inputs():
    return offline_demo()


def modified(model, **changes):
    raw=model.model_dump(mode="json")
    raw.update(changes)
    return type(model).model_validate(raw)


def request_change(data, **changes):
    return modified(data["request"],**changes)


def visual_change(data, mutate):
    raw=data["visual"].model_dump(mode="json")
    mutate(raw)
    return VisualTeachingPlan.model_validate(raw)


def test_source_reuse_full_c1_and_c2_fixture_and_objective_coverage():
    data=inputs()
    output=compile_pedagogy_and_hero(**data)
    verify_grounded_pedagogy_plan(candidate=output,**data)
    assert tuple(x.objective_id for x in output.objectives)==("O1","O2")
    assert tuple(x.segment_ids for x in output.objectives)==(("intro",),("summary",))
    assert tuple(x.assessment_probe_ids for x in output.objectives)==(("P1",),("P2",))
    assert output.misconceptions[0].misconception_id=="M1"
    assert output.misconceptions[0].correction_beat_id=="correct-idea"
    assert output.prerequisite_graph.inferred_edges==0
    assert [(x.prerequisite_concept,x.dependent_concept) for x in output.prerequisite_graph.declared_edges]==[
        ("first","second")]
    assert output.section_mental_models[0][1:] == ("Mistaken idea","Correct explanation")
    assert output.status=="VALIDATED_OFFLINE_PLAN_NO_RENDERER_PROOF"
    assert output.render_ready is False


def test_matched_budget_ablation_changes_allocation_not_sources():
    data=inputs()
    output=compile_pedagogy_and_hero(**data)
    assert output.ablation.total_visual_units==10
    assert [x.allocated_units for x in output.ablation.uniform]==[5,5]
    assert [x.allocated_units for x in output.ablation.prioritized]==[8,2]
    assert output.ablation.priority_shift_units==3
    assert output.ablation.status=="REBALANCED_OFFLINE"
    assert len(output.hero_moments)==1
    moment=output.hero_moments[0]
    assert moment.beat_id=="correct-idea"
    assert moment.misconception_ids==("M1",)
    assert moment.approved_claim_ids==("C1",)
    assert moment.objective_ids==("O1",)
    assert moment.essential_state_change=="Replace the misconception"
    assert moment.representation.value=="WORKED_EXAMPLE_BOARD"
    assert output.ablation.learning_gain=="UNMEASURED"
    assert output.ablation.human_clarity_delta=="UNMEASURED"
    assert output.independent_human_review=="UNMEASURED"


def test_repeated_serialized_runs_have_identical_decision_and_control_hash():
    p=compile_pedagogy_and_hero(**inputs())
    q=compile_pedagogy_and_hero(**inputs())
    assert p.model_dump(mode="json")==q.model_dump(mode="json")
    assert p.decision_sha256==q.decision_sha256
    assert p.source_decision_sha256==p.ablation.control_input_sha256


def test_wrong_correction_segment_claims_do_not_pass():
    data=inputs()
    data["visual"]=visual_change(data,lambda v:v["beats"][0].update(claim_refs=["C2"]))
    with pytest.raises(SemanticContractError,match="BEAT_CLAIM_NOT_APPROVED"):
        compile_pedagogy_and_hero(**data)


def test_rehashed_fact_report_cannot_turn_blocked_claim_into_approved_source():
    data=inputs()
    raw=data["fact_report"].model_dump(mode="json")
    for claim in raw["claims"]:
        if claim["claim_id"]=="C2":
            claim["issues"]=[]
    data["fact_report"]=type(data["fact_report"]).model_validate(raw)
    with pytest.raises(SemanticContractError,match="UPSTREAM_PEDAGOGY_SCRIPT_GATE_FAILED"):
        compile_pedagogy_and_hero(**data)


def test_script_content_must_actually_contain_correction_text():
    data=inputs()
    raw=data["script"].model_dump(mode="json")
    raw["segments"][0]["spoken_text"]="A vague replacement."
    raw["segments"][0]["subtitle_text"]="No correction is shown."
    data["script"]=LessonScript.model_validate(raw)
    with pytest.raises(SemanticContractError,match="MISCONCEPTION_CORRECTION_MISSING_FROM_SCRIPT"):
        compile_pedagogy_and_hero(**data)


def test_misconception_cannot_be_bound_to_unrelated_or_unknown_beat():
    data=inputs()
    data["request"]=request_change(data,misconception_bindings=[{
        "misconception_id":"M1","correction_beat_id":"consolidate"}])
    data["visual"]=visual_change(data,lambda v:v["beats"][1].update(claim_refs=[]))
    with pytest.raises(SemanticContractError,match="MISCONCEPTION_UNGROUNDED_BEAT"):
        compile_pedagogy_and_hero(**data)
    data=inputs()
    data["request"]=request_change(data,misconception_bindings=[{
        "misconception_id":"M1","correction_beat_id":"invented"}])
    with pytest.raises(SemanticContractError,match="MISCONCEPTION_UNGROUNDED_BEAT"):
        compile_pedagogy_and_hero(**data)


def test_all_misconceptions_need_explicit_typed_binding():
    data=inputs()
    data["request"]=request_change(data,misconception_bindings=[])
    with pytest.raises(SemanticContractError,match="MISCONCEPTION_BINDINGS_INCOMPLETE"):
        compile_pedagogy_and_hero(**data)


def test_proposed_prerequisite_graph_never_infers_dependencies():
    data=inputs()
    data["request"]=request_change(data,prerequisite_edges=[])
    output=compile_pedagogy_and_hero(**data)
    assert output.prerequisite_graph.declared_edges==()
    assert output.prerequisite_graph.inferred_edges==0


@pytest.mark.parametrize("prerequisite,dependent,reason",[
    ("second","first","CYCLIC_OR_OUT_OF_ORDER"),
    ("first","first","CYCLIC_OR_OUT_OF_ORDER"),
    ("invented","second","UNDECLARED_PREREQUISITE"),
])
def test_invalid_prerequisite_dag_fails_closed(prerequisite,dependent,reason):
    data=inputs()
    data["request"]=request_change(data,prerequisite_edges=[{
        "prerequisite_concept":prerequisite,"dependent_concept":dependent}])
    with pytest.raises(SemanticContractError,match=reason):
        compile_pedagogy_and_hero(**data)


def test_section_budget_fixed_and_capacity_bounded():
    data=inputs()
    data["request"]=request_change(data,total_visual_units=17)
    with pytest.raises(SemanticContractError,match="INFEASIBLE_FIXED_TOTAL_BUDGET"):
        compile_pedagogy_and_hero(**data)
    data=inputs()
    data["request"]=request_change(data,total_visual_units=2)
    p=compile_pedagogy_and_hero(**data)
    assert p.ablation.status=="UNIFORM_FALLBACK_NO_CAPACITY"
    assert p.ablation.priority_shift_units==0
    assert [x.allocated_units for x in p.ablation.uniform]==[1,1]
    assert p.ablation.uniform==p.ablation.prioritized


def test_no_dynamic_hero_never_invents_interpolation_or_relabels_card_as_hero():
    data=inputs()
    def mutate(v):
        v["beats"][0]["expected_visible_state_change"]=None
        v["beats"][0]["allowed_static_justification"]="No dynamic evidence"
    data["visual"]=visual_change(data,mutate)
    output=compile_pedagogy_and_hero(**data)
    assert output.hero_moments==()
    assert output.ablation.uniform==output.ablation.prioritized
    assert output.ablation.status=="UNIFORM_FALLBACK_NO_CAPACITY"


def test_learner_profile_and_script_beat_coverage_do_not_drift():
    data=inputs()
    data["visual"]=visual_change(data,lambda v:v["constraints"].update(language="fr"))
    with pytest.raises(SemanticContractError,match="LEARNER_PROFILE_OR_DURATION_DRIFT"):
        compile_pedagogy_and_hero(**data)
    data=inputs()
    data["visual"]=visual_change(data,lambda v:v["beats"][0].update(script_segment_ref="summary"))
    with pytest.raises(SemanticContractError,match="SCRIPT_BEAT_ORDER_OR_COVERAGE_DRIFT"):
        compile_pedagogy_and_hero(**data)


def test_mismatched_v3_section_objective_does_not_forge_sequence():
    data=inputs()
    data["visual"]=visual_change(data,lambda v:v["sections"][1].update(objective_refs=["O1"]))
    with pytest.raises(SemanticContractError,match="BEAT_OBJECTIVE_SECTION_DRIFT|UNEXPLAINED_SECTION_OBJECTIVE"):
        compile_pedagogy_and_hero(**data)


def test_section_no_hero_candidate_falls_back_without_pretend_quality():
    data=inputs()
    data["visual"]=visual_change(data,lambda v:v["sections"][0].update(hero_candidate=False))
    r=compile_pedagogy_and_hero(**data)
    assert not r.hero_moments
    assert r.ablation.priority_shift_units==0
    assert r.ablation.status=="UNIFORM_FALLBACK_NO_CAPACITY"


def test_modified_source_invalidates_prior_plan_even_if_hashes_regenerated():
    data=inputs()
    p=compile_pedagogy_and_hero(**data)
    bad=p.model_dump(mode="json")
    bad["hero_moments"][0]["priority_score"]+=100
    from learnflow_v2.repair import compute_content_hash
    # Recomputing any self-declared string hash cannot overwrite source replay.
    bad["decision_sha256"]=compute_content_hash(bad)
    with pytest.raises(SemanticContractError,match="FORGED_STALE"):
        verify_grounded_pedagogy_plan(candidate=GroundedPedagogyPlan.model_validate(bad),**data)
    revised=inputs()
    revised["visual"]=visual_change(revised,lambda v:v["beats"][0].update(importance=.89))
    with pytest.raises(SemanticContractError,match="FORGED_STALE"):
        verify_grounded_pedagogy_plan(candidate=p,**revised)


def test_output_budget_and_claim_contract_cannot_be_relabelled_as_learning_gain():
    p=compile_pedagogy_and_hero(**inputs())
    a=p.ablation.model_dump(mode="json")
    a["learning_gain"]="0.3"
    with pytest.raises(ValidationError):
        HeroAblationPair.model_validate(a)
    a=p.ablation.model_dump(mode="json")
    a["prioritized"][0]["allocated_units"]=10
    with pytest.raises(ValidationError,match="BUDGET_LEAK|SECTION_BUDGET_EXCEEDED"):
        HeroAblationPair.model_validate(a)


def test_provider_free_pure_planning_and_distinct_unmeasured_human_gate():
    source=(ROOT/"learnflow_v3/pedagogy_planner.py").read_text()
    assert "openrouter" not in source.lower()
    assert "requests.post" not in source
    assert "subprocess" not in source
    assert "human_clarity_delta" in source and '"UNMEASURED"' in source


def test_offline_evidence_reproducer(tmp_path):
    from scripts.verify_v3_pedagogy_planning import main
    path=tmp_path/"evidence.json"
    import subprocess
    run=subprocess.run([sys.executable,"scripts/verify_v3_pedagogy_planning.py",
                        "--output-file",str(path)],cwd=ROOT,capture_output=True,text=True)
    assert run.returncode==0,run.stdout+run.stderr
    assert "V3_09_PEDAGOGY_HERO=PASS" in run.stdout
    p=json.loads(path.read_text())
    assert p["ablation"]["total_visual_units"]==10
    assert p["ablation"]["human_clarity_delta"]=="UNMEASURED"
