"""V3-49 bounded new-topic semantic grounding negative and compiler tests."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.grounded_fraction_claims import (
 FractionTopic,EvidenceBundle,ground,verify,build,ORIGIN,VERSION)
from learnflow_v3.semantic_scene_offline_fixtures import fixture_cases
from learnflow_v3.semantic_scene_wire import decode_model_facing_scene
from learnflow_v3.semantic_visual_events import compile_manim
from learnflow_v3.pedagogical_visual_grammar import validate_transformations,subdivision_axis

ROOT=Path(__file__).resolve().parents[2]
PRE="benchmarks/learnflowbench/v3/v3_49_grounded_claims_preregister.json"


def cases():
    return json.loads((ROOT/PRE).read_text())["cases"]


def topic(row):
    return FractionTopic(topic_id=row["id"],numerator=row["source"][0],
       denominator=row["source"][1],factor=row["factor"],
       target_numerator=row["target"][0],target_denominator=row["target"][1])


def test_preregister_and_three_strictly_distinct_ratios_before_implementation():
    p=json.loads((ROOT/PRE).read_text())
    assert p["registration_kind"]=="PREREGISTRATION_BEFORE_IMPLEMENTATION"
    assert p["parent_sha"]=="ed201a4cd31c429a6a979e3b857716c8afe0fa0d"
    assert p["acceptance"]["zero_provider_requests"]
    assert len(p["cases"])==3
    assert sum(x["role"]=="heldout_new_topic" for x in p["cases"])==2
    assert len({tuple(x["source"])+(x["factor"],) for x in p["cases"]})==3
    assert all(x["source"]!=[1,2] for x in p["cases"])


@pytest.mark.parametrize("row",cases(),ids=lambda x:x["id"])
def test_source_specific_claims_morph_and_native_compiler_not_fixture_specific(row):
    t=topic(row)
    evidence=ground(t)
    verify(evidence)
    lesson,adapter,plan=build(evidence)
    bound=validate_transformations(adapter,plan)
    assert {x["kind"] for x in bound}=={"subdivide","equivalence_link"}
    assert subdivision_axis(adapter,"source_parts","target_parts",t.factor)=="vertical"
    assert len(lesson.partitions[0].part_ids)==t.denominator
    assert len(lesson.partitions[1].part_ids)==t.target_denominator
    assert evidence.proof in [x.text for x in lesson.labels]
    assert len({x.source_topic_sha256 for x in evidence.claims})==1
    assert evidence.origin==ORIGIN and evidence.version==VERSION
    code=compile_manim(lesson,[8.8,9.2,8.3,8.4],
                       visual_quality=True,pedagogical_plan=plan)
    compile(code,"<v349 compiled trusted host>","exec")
    assert "TransformFromCopy" in code and "DashedLine" in code
    assert "v347_equal_" in code and "Create(v347_cut_" in code
    assert "__import__" not in code and "subprocess" not in code
    assert "from manim import *" in code
    # Every source cell gets factor-1 cutting guides. No single-tile shortcut.
    assert code.count(" = DashedLine(")==t.denominator*(t.factor-1)


@pytest.mark.parametrize("mutation",[
  {"denominator":0},{"numerator":3,"denominator":3},
  {"factor":0},{"factor":4},{"target_numerator":7},
  {"target_denominator":9},{"target_denominator":13},
  {"python":"import os"},{"narration":"new fake proof"},
])
def test_bad_topic_or_extra_untrusted_code_rejected(mutation):
    orig=ground(topic(cases()[0])).topic.model_dump()
    orig.update(mutation)
    with pytest.raises((ValueError,ValidationError,Blocked)):
        FractionTopic.model_validate(orig)


@pytest.mark.parametrize("mutation",[
 "fake_origin","altered_proof","altered_source_sha",
 "altered_claim_sha","swap_F1_and_F2","reuse_wrong_topics_claim",
])
def test_grounded_topic_binding_prevents_claim_recycling(mutation):
    e=ground(topic(cases()[0]))
    d=e.model_dump()
    d["claims"]=list(d["claims"])
    if mutation=="fake_origin":d["origin"]="OPENROUTER_REAL"
    if mutation=="altered_proof":d["proof"]="1/2 = 3/5"
    if mutation=="altered_source_sha":d["source_sha256"]="0"*64
    if mutation=="altered_claim_sha":d["claims"][0]["facts_sha256"]="a"*64
    if mutation=="swap_F1_and_F2":d["claims"][0],d["claims"][1]=d["claims"][1],d["claims"][0]
    if mutation=="reuse_wrong_topics_claim":
        wrong=ground(topic(cases()[1]))
        d["claims"]=list(wrong.model_dump()["claims"])
    with pytest.raises((ValidationError,ValueError,Blocked)):
        verify(EvidenceBundle.model_validate(d))


def test_tampered_bundle_rejected_even_when_already_instantiated():
    original=ground(topic(cases()[0]))
    mutated=original.model_copy(update={"proof":"1 = 0"})
    with pytest.raises(Blocked,match="V349_UNBOUND_OR_TAMPERED_TOPIC_CLAIM"):
        build(mutated)


def test_legacy_global_claim_ids_still_fail_closed_for_new_math():
    # The historical frozen fixture still works; no V3-48 scope bypass.
    decode_model_facing_scene(fixture_cases()["v345-synthetic-fractions"])
    decode_model_facing_scene(fixture_cases()["v345-synthetic-process"])
    raw=deepcopy(fixture_cases()["v345-synthetic-fractions"])
    next(p for p in raw["partitions"] if p["id"]=="halves")["numerator"]=2
    with pytest.raises((Blocked,ValueError,ValidationError)):
        decode_model_facing_scene(raw)


def test_source_generated_narration_is_factual_not_unbounded_user_prose():
    for row in cases():
        e=ground(topic(row))
        lesson,_,_=build(e)
        assert all(65<=len(b.narration)<=270 for b in lesson.beats)
        assert all(set(b.claim_ids).issubset({"F1","F2","F3"}) for b in lesson.beats)
        assert e.proof in [x.text for x in lesson.labels]


def test_native_workflow_reuses_sandbox_frozen_regressions_no_model_key():
    workflow=(ROOT/".github/workflows/v3-49-grounded-fraction-claims.yml").read_text()
    runner=(ROOT/"scripts/run_v3_49_grounded_claims.py").read_text()
    assert "run_v3_49_grounded_claims.py" in workflow
    assert "verify_v2_core_freeze.py" in workflow
    assert "test_v3_48_pedagogical_quality.py" in workflow
    assert "OPENROUTER_API_KEY" not in workflow
    assert "gemini_api_key" not in workflow.lower()
    assert "deterministic_mux" in runner
    assert "inspect_candidate" in runner
    assert "_semantic_frame_proofs" in runner
