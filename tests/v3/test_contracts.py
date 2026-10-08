"""V3-02 semantic contracts, V2 bridge, numeric drift and mutation regressions."""
from __future__ import annotations

from copy import deepcopy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from pydantic import ValidationError

from agent_contracts.lesson import LessonScript, ScriptSegment, Storyboard, StoryboardScene
from learnflow_v2.concepts import ConceptRegistry
from learnflow_v2.concepts.schema import ConceptEntry
from learnflow_v2.concepts.normalize import deterministic_concept_id, normalize_canonical_key
from learnflow_v2.scenegraph import SceneGraph
from learnflow_v2.scenegraph.schema import SceneNode
from learnflow_v3 import (
    CanonicalConceptRef, LedgerStep, ObjectState, SemanticContractError,
    StateLedger, VisualPatternSpec, VisualTeachingPlan,
    validate_semantic_bundle,
)


def valid_objects():
    entry = ConceptEntry(concept_id="c_alg", canonical_key="concept:algorithm", label="Algorithm")
    registry = ConceptRegistry()
    registry.register(entry)
    plan = VisualTeachingPlan(
        lesson_id="lesson-01", learning_objective_ids=("objective-01",),
        sections=({"section_id": "section-01", "objective_refs": ("objective-01",),
                   "learner_state_before": "Unknown", "learner_state_after": "Understands example",
                   "visual_teaching_goal": "Follow state transitions",
                   "representation_options": ("WORKED_EXAMPLE_BOARD",),
                   "visual_complexity_budget": 3},),
        beats=({"beat_id": "beat-01", "section_ref": "section-01",
                "script_segment_ref": "seg-01", "claim_refs": ("claim-01",),
                "concept_refs": ({"concept_id": "c_alg", "canonical_key": "concept:algorithm"},),
                "expected_visible_state_change": "Show next algorithm state",
                "importance": 0.9},),
        constraints={"language": "en", "learner_level": "beginner",
                     "target_duration_minutes": 3},
    )
    pattern = VisualPatternSpec(
        pattern_id="pattern-01", scene_id="scene-01",
        pattern_type="WORKED_EXAMPLE_BOARD", objective_refs=("objective-01",),
        source_refs=("script:seg-01", "trace:trace-01"),
        concept_refs=(CanonicalConceptRef(concept_id="c_alg", canonical_key="concept:algorithm"),),
        state_source={"kind": "VERIFIED_TRACE", "ref": "trace:trace-01"},
        semantic_objects=({"object_id": "array-01", "kind": "SEQUENCE",
                           "concept": {"concept_id": "c_alg", "canonical_key": "concept:algorithm"},
                           "state_ref": "trace:trace-01"},),
        visual_constraints={"reading_order": "LEFT_TO_RIGHT"},
        renderer_requirement="STATEFUL_SEQUENCE",
    )
    ledger = StateLedger(
        ledger_id="ledger-01", pattern_ref="pattern-01", source_ref="trace:trace-01",
        steps=({"step_id": "step-01", "beat_ref": "beat-01",
                "object_states": ({"object_id": "array-01",
                                   "properties": {"visible": True, "index": 1,
                                                  "items": [1, 3, 5]}},)},),
    )
    script = LessonScript(
        script_id="script-01", pedagogy_plan_id="pedagogy-01",
        segments=(ScriptSegment(
            segment_id="seg-01", spoken_text="Follow the algorithm.",
            subtitle_text="Follow the algorithm.", spoken_language="en",
            subtitle_language="en", teaching_function="DEMONSTRATE",
            claim_ids=("claim-01",), objective_ids=("objective-01",)),),
    )
    storyboard = Storyboard(
        storyboard_id="sb-01", script_id="script-01",
        scenes=(StoryboardScene(
            scene_id="scene-01", script_segment_ids=("seg-01",),
            teaching_function="DEMONSTRATE", visual_intent="Show state changes.",
            concept_refs=("c_alg",), continuity_keys=("concept:algorithm",)),),
    )
    graph = SceneGraph(
        scene_id="scene-01", purpose="DEMONSTRATE",
        nodes=[SceneNode(id="node-01", kind="TEXT", label="Algorithm",
                         concept_ref="c_alg", semantic_key="concept:algorithm")],
    )
    return dict(plan=plan, pattern=pattern, ledger=ledger, registry=registry,
                script=script, storyboard=storyboard, scenegraph=graph,
                verified_trace_refs=("trace:trace-01",))


def assert_valid(override=None):
    obj = valid_objects()
    if override:
        obj.update(override)
    validate_semantic_bundle(**obj)
    return obj


def modify_model(model, field, value):
    data = model.model_dump(mode="json")
    data[field] = value
    return type(model).model_validate(data)


def test_valid_versioned_triplet_and_real_v2_registry_graph_script():
    b = assert_valid()
    for name in ("plan", "pattern", "ledger"):
        model = b[name]
        loaded = type(model).model_validate_json(model.canonical_json())
        assert loaded.content_sha256() == model.content_sha256()
        assert model.schema_version == "3.0"
    assert b["plan"].learning_objective_ids == ("objective-01",)


@pytest.mark.parametrize("key", ["plan", "pattern", "ledger"])
def test_unknown_version_must_fail(key):
    b = valid_objects()
    with pytest.raises(ValidationError, match="schema_version"):
        modify_model(b[key], "schema_version", "4.0")


@pytest.mark.parametrize("key", ["plan", "pattern", "ledger"])
def test_unknown_fields_must_fail(key):
    b = valid_objects()
    with pytest.raises(ValidationError, match="extra_forbidden"):
        modify_model(b[key], "unsafe_renderer_instruction", "ffmpeg")


def test_unknown_pattern_enum_must_fail():
    b = valid_objects()
    with pytest.raises(ValidationError):
        modify_model(b["pattern"], "pattern_type", "LLM_EXEC_PYTHON")


def test_dangling_section_and_invalid_order_rejected():
    b = valid_objects()
    plan = b["plan"].model_dump(mode="json")
    plan["beats"][0]["section_ref"] = "nonexistent"
    with pytest.raises(ValidationError, match="unknown section"):
        VisualTeachingPlan.model_validate(plan)


def test_duplicate_ids_and_missing_dynamic_change_rejected():
    b = valid_objects()
    ledger = b["ledger"].model_dump(mode="json")
    ledger["steps"].append(deepcopy(ledger["steps"][0]))
    with pytest.raises(ValidationError, match="ledger step IDs"):
        StateLedger.model_validate(ledger)
    plan = b["plan"].model_dump(mode="json")
    plan["beats"][0]["expected_visible_state_change"] = None
    with pytest.raises(ValidationError, match="exactly one"):
        VisualTeachingPlan.model_validate(plan)


def test_non_json_state_and_pixel_coordinates_rejected():
    b = valid_objects()
    bad = b["ledger"].model_dump(mode="json")
    bad["steps"][0]["object_states"][0]["properties"]["value"] = float("nan")
    with pytest.raises(ValidationError, match="finite"):
        StateLedger.model_validate(bad)
    bad = b["ledger"].model_dump(mode="json")
    bad["steps"][0]["object_states"][0]["properties"]["x_px"] = 100
    with pytest.raises(ValidationError, match="pixel"):
        StateLedger.model_validate(bad)


def test_visual_spec_rejects_executable_coordinates_or_malformed_trace():
    b = valid_objects()
    with pytest.raises(ValidationError, match="geometry"):
        modify_model(b["pattern"], "visual_constraints", {"x": "42"})
    with pytest.raises(ValidationError, match="kind/ref mismatch"):
        modify_model(b["pattern"], "state_source", {"kind": "VERIFIED_TRACE", "ref": "static:trace-01"})


def test_unverified_trace_fails_closed():
    with pytest.raises(SemanticContractError, match="provenance unverified"):
        assert_valid({"verified_trace_refs": ()})


def test_orphan_pattern_sources_and_ledger_mismatch_rejected():
    b = valid_objects()
    p = modify_model(b["pattern"], "source_refs", ["script:unknown", "trace:trace-01"])
    with pytest.raises(SemanticContractError, match="missing script sources"):
        assert_valid({"pattern": p})
    led = modify_model(b["ledger"], "pattern_ref", "other-pattern")
    with pytest.raises(SemanticContractError, match="source mismatch"):
        assert_valid({"ledger": led})


def test_canonical_concept_key_and_object_ref_must_match_v2_registry():
    b = valid_objects()
    plan = b["plan"].model_dump(mode="json")
    plan["beats"][0]["concept_refs"][0]["canonical_key"] = "concept:unrelated"
    with pytest.raises(SemanticContractError, match="canonical key mismatch"):
        assert_valid({"plan": VisualTeachingPlan.model_validate(plan)})
    pat = b["pattern"].model_dump(mode="json")
    pat["semantic_objects"][0]["concept"]["concept_id"] = "missing"
    with pytest.raises(SemanticContractError, match="unknown concept_ref"):
        assert_valid({"pattern": VisualPatternSpec.model_validate(pat)})


def test_claim_and_objective_references_are_source_grounded():
    b = valid_objects()
    plan = b["plan"].model_dump(mode="json")
    plan["beats"][0]["claim_refs"] = ["invented-claim"]
    with pytest.raises(SemanticContractError, match="not grounded"):
        assert_valid({"plan": VisualTeachingPlan.model_validate(plan)})
    pat = modify_model(b["pattern"], "objective_refs", ["unknown-objective"])
    with pytest.raises(SemanticContractError, match="unknown objective"):
        assert_valid({"pattern": pat})


def test_ledger_object_coverage_and_beat_origin_cannot_drift():
    b = valid_objects()
    ledger = b["ledger"].model_dump(mode="json")
    ledger["steps"][0]["object_states"][0]["object_id"] = "new-object"
    with pytest.raises(SemanticContractError, match="object identity coverage"):
        assert_valid({"ledger": StateLedger.model_validate(ledger)})
    ledger = b["ledger"].model_dump(mode="json")
    ledger["steps"][0]["beat_ref"] = "unknown-beat"
    with pytest.raises(SemanticContractError, match="orphan ledger beat"):
        assert_valid({"ledger": StateLedger.model_validate(ledger)})


def test_scenegraph_storyboard_and_script_cross_refs_fail_closed():
    b = valid_objects()
    graph = SceneGraph(scene_id="wrong-scene", nodes=b["scenegraph"].nodes)
    with pytest.raises(SemanticContractError, match="scene identity mismatch"):
        assert_valid({"scenegraph": graph})
    graph = SceneGraph(scene_id="scene-01", nodes=[
        SceneNode(id="node-01", kind="TEXT", concept_ref="c_alg", semantic_key="concept:unrelated")
    ])
    with pytest.raises(SemanticContractError, match="frozen V2 graph"):
        assert_valid({"scenegraph": graph})


def test_original_numeric_example_16_vs_24_is_rejected_through_reused_gate():
    b = valid_objects()
    label = "Worked example: In [2, 5, 8, 12, 16, 23, 38], search for 16."
    key = normalize_canonical_key(label)
    concept_id = deterministic_concept_id(key)
    registry = ConceptRegistry()
    registry.register(ConceptEntry(concept_id=concept_id, canonical_key=key, label=label))
    cref = {"concept_id": concept_id, "canonical_key": key}
    plan = b["plan"].model_dump(mode="json")
    plan["beats"][0]["concept_refs"] = [cref]
    pattern = b["pattern"].model_dump(mode="json")
    pattern["concept_refs"] = [cref]
    pattern["semantic_objects"][0]["concept"] = cref
    sb = Storyboard(storyboard_id="sb-01", script_id="script-01", scenes=(
        StoryboardScene(scene_id="scene-01", script_segment_ids=("seg-01",),
            teaching_function="DEMONSTRATE",
            visual_intent="Search for 24 in [3, 7, 12, 18, 24, 31, 40]",
            concept_refs=(concept_id,), continuity_keys=(key,)),))
    graph = SceneGraph(scene_id="scene-01", nodes=[
        SceneNode(id="node-01", kind="TEXT", concept_ref=concept_id, semantic_key=key)])
    with pytest.raises(SemanticContractError, match="SEMANTIC_WORKED_EXAMPLE_MISMATCH"):
        assert_valid({
            "plan": VisualTeachingPlan.model_validate(plan),
            "pattern": VisualPatternSpec.model_validate(pattern),
            "registry": registry, "storyboard": sb, "scenegraph": graph
        })


def test_mutated_valid_content_changes_stable_hash_but_does_not_approve_runtime():
    b = valid_objects()
    p = b["plan"].model_dump(mode="json")
    p["sections"][0]["visual_teaching_goal"] = "A changed but valid pedagogical goal"
    new = VisualTeachingPlan.model_validate(p)
    assert new.content_sha256() != b["plan"].content_sha256()
    assert new.content_sha256() == new.content_sha256()
