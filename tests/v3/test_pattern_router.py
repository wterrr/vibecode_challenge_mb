"""V3-04 bounded semantic routing: positive, abstention, anti-card, mutation tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts.lesson import ScriptSegment, Storyboard, StoryboardScene
from learnflow_v2.scenegraph import SceneGraph
from learnflow_v3 import SemanticContractError, StateLedger, VisualPatternSpec, VisualTeachingPlan
from learnflow_v3.pattern_router import (
    RouteReason, RouteStatus, VisualPatternRoute, route_visual_pattern,
)
from tests.v3.test_contracts import valid_objects


def _updated(model, update):
    data = model.model_dump(mode="json")
    data.update(update)
    return type(model).model_validate(data)


def _section(plan, *, budget=None, options=None):
    data = plan.model_dump(mode="json")
    if budget is not None:
        data["sections"][0]["visual_complexity_budget"] = budget
    if options is not None:
        data["sections"][0]["representation_options"] = options
    return VisualTeachingPlan.model_validate(data)


def _fixture_worked(*, budget=6, steps=2):
    b = valid_objects()
    data = b["plan"].model_dump(mode="json")
    data["sections"][0]["visual_complexity_budget"] = budget
    if steps == 2:
        second = dict(data["beats"][0])
        second.update(beat_id="beat-02", script_segment_ref="seg-02",
                      expected_visible_state_change="Update the pointer")
        data["beats"].append(second)
    b["plan"] = VisualTeachingPlan.model_validate(data)
    if steps == 2:
        script = b["script"]
        second = script.segments[0].model_copy(update={"segment_id": "seg-02"})
        b["script"] = script.model_copy(update={"segments": (script.segments[0], second)})
        scene = b["storyboard"].scenes[0].model_copy(
            update={"script_segment_ids": ("seg-01", "seg-02")}
        )
        b["storyboard"] = b["storyboard"].model_copy(update={"scenes": (scene,)})
        b["pattern"] = _updated(b["pattern"], {
            "source_refs": ["script:seg-01", "script:seg-02", "trace:trace-01"]
        })
        data = b["ledger"].model_dump(mode="json")
        second_state = dict(data["steps"][0])
        second_state["step_id"] = "step-02"
        second_state["beat_ref"] = "beat-02"
        second_state["object_states"] = [{
            "object_id": "array-01", "properties": {
                "visible": True, "index": 2, "items": [1, 3, 5]
            }
        }]
        data["steps"].append(second_state)
        b["ledger"] = StateLedger.model_validate(data)
    b["scenegraph"] = _updated(b["scenegraph"], {"layout_intent": {
        "type": "PROCESS", "reading_direction": "LEFT_TO_RIGHT"
    }})
    return b


def _fixture_static(family="PROCESS_FLOW", *, budget=6, branched=False):
    b = valid_objects()
    p = b["plan"].model_dump(mode="json")
    p["sections"][0]["representation_options"] = [family]
    p["sections"][0]["visual_complexity_budget"] = budget
    p["beats"][0]["expected_visible_state_change"] = None
    p["beats"][0]["allowed_static_justification"] = "Static relationships are sufficient"
    b["plan"] = VisualTeachingPlan.model_validate(p)
    pat = b["pattern"].model_dump(mode="json")
    pat["pattern_type"] = family
    pat["source_refs"] = ["script:seg-01"]
    pat["state_source"] = {"kind": "STATIC", "ref": "static:diagram-01"}
    pat["semantic_objects"] = [
        {"object_id": "obj-01", "kind": "PROCESS" if family == "PROCESS_FLOW" else (
            "EQUATION" if family == "EQUATION_GRAPH" else "LABEL"),
         "concept": {"concept_id": "c_alg", "canonical_key": "concept:algorithm"}}
    ]
    if family == "PROCESS_FLOW":
        pat["semantic_objects"].append({"object_id": "obj-02", "kind": "PROCESS"})
    pat["renderer_requirement"] = {
        "PROCESS_FLOW": "PROCESS", "EQUATION_GRAPH": "MATH", "CONCEPT_CARD": "STATIC"
    }[family]
    b["pattern"] = VisualPatternSpec.model_validate(pat)
    led = b["ledger"].model_dump(mode="json")
    led["source_ref"] = "static:diagram-01"
    led["steps"][0]["object_states"] = [
        {"object_id": item["object_id"], "properties": {"visible": True}}
        for item in pat["semantic_objects"]
    ]
    b["ledger"] = StateLedger.model_validate(led)
    graph = b["scenegraph"].model_dump(mode="json")
    if family == "PROCESS_FLOW":
        graph["layout_intent"]["type"] = "PROCESS"
        graph["nodes"].append({"id": "node-02", "kind": "TEXT", "label": "Step 2"})
        graph["relations"] = [{
            "id": "relation-01", "source": "node-01", "target": "node-02", "kind": "FLOW"
        }]
        if branched:
            graph["nodes"].append({"id": "node-03", "kind": "TEXT", "label": "Branch"})
            graph["relations"].append({
                "id": "relation-02", "source": "node-01", "target": "node-03", "kind": "FLOW"
            })
    if family == "EQUATION_GRAPH":
        graph["layout_intent"]["type"] = "ILLUSTRATION"
        graph["nodes"][0]["kind"] = "EQUATION"
    if family == "CONCEPT_CARD":
        graph["layout_intent"]["type"] = "CONCEPT_CARD"
        graph["purpose"] = "RECAP"
        script = b["script"]
        typed_seg = ScriptSegment.model_validate({
            **script.segments[0].model_dump(mode="json"), "teaching_function": "SUMMARIZE",
        })
        b["script"] = script.model_copy(update={"segments": (typed_seg,)})
        sb = b["storyboard"]
        typed_scene = StoryboardScene.model_validate({
            **sb.scenes[0].model_dump(mode="json"), "teaching_function": "SUMMARIZE",
        })
        b["storyboard"] = sb.model_copy(update={"scenes": (typed_scene,)})
    b["scenegraph"] = SceneGraph.model_validate(graph)
    b["verified_trace_refs"] = ()
    return b


def _route(bundle):
    return route_visual_pattern(**bundle)


def test_dynamic_worked_example_primary_is_bounded_and_unrenderable():
    routed = _route(_fixture_worked())
    assert routed.status == RouteStatus.SELECTED_UNRENDERABLE
    assert routed.selected_variant == "TRACE_SPOTLIGHT"
    assert routed.reason == RouteReason.ELIGIBLE
    assert routed.fallback_used is False
    assert routed.render_ready is False and routed.renderer_implementation == "NOT_IMPLEMENTED"
    assert routed.source_audit_hash and routed.decision_hash
    with pytest.raises(SemanticContractError, match="NO_RENDERER_PROOF"):
        routed.require_renderer()


def test_dynamic_worked_example_compact_is_same_family_not_card():
    routed = _route(_fixture_worked(budget=3))
    assert routed.selected_variant == "TRACE_COMPACT"
    assert routed.reason == RouteReason.FALLBACK_WITHIN_FAMILY
    assert routed.fallback_used is True
    assert [a.family.value for a in routed.attempts] == [
        "WORKED_EXAMPLE_BOARD", "WORKED_EXAMPLE_BOARD"
    ]
    assert routed.attempts[0].accepted is False
    assert routed.attempts[-1].accepted is True


def test_dynamic_without_enough_state_steps_abstains_not_static_fallback():
    result = _route(_fixture_worked(steps=1))
    assert result.status == RouteStatus.ABSTAIN
    assert result.reason == RouteReason.DYNAMIC_EVIDENCE_MISSING
    assert result.selected_variant is None


def test_process_flow_fallback_preserves_process_family():
    result = _route(_fixture_static("PROCESS_FLOW", budget=3))
    assert result.status == RouteStatus.SELECTED_UNRENDERABLE
    assert result.selected_variant == "PROCESS_LINEAR"
    assert result.fallback_used
    assert result.representation.value == "PROCESS_FLOW"


def test_branching_process_can_use_network_when_budget_is_sufficient():
    result = _route(_fixture_static("PROCESS_FLOW", branched=True, budget=6))
    assert result.selected_variant == "PROCESS_NETWORK"
    assert not result.fallback_used


def test_branching_process_budget_too_low_abstains_instead_of_flattening_graph():
    result = _route(_fixture_static("PROCESS_FLOW", branched=True, budget=3))
    assert result.status == RouteStatus.ABSTAIN
    assert result.selected_variant is None


def test_equation_graph_selection_no_card_collapse():
    result = _route(_fixture_static("EQUATION_GRAPH", budget=3))
    assert result.selected_variant == "EQUATION_COMPACT"
    assert result.representation.value == "EQUATION_GRAPH"


def test_intentional_recap_card_is_only_explicit_static_recap():
    result = _route(_fixture_static("CONCEPT_CARD", budget=1))
    assert result.selected_variant == "INTENTIONAL_RECAP_CARD"
    assert result.status == RouteStatus.SELECTED_UNRENDERABLE
    assert not result.render_ready


def test_non_recap_card_abstains_even_when_scene_layout_is_card():
    b = _fixture_static("CONCEPT_CARD")
    b["scenegraph"] = _updated(b["scenegraph"], {"purpose": "DEMONSTRATE"})
    with pytest.raises(SemanticContractError, match="V2_VISUAL_DIRECTOR_GATE_FAILED"):
        _route(b)


def test_fallback_to_concept_card_is_blocked_as_cross_family():
    b = _fixture_worked()
    b["pattern"] = _updated(b["pattern"], {"fallback_family": ["CONCEPT_CARD"]})
    result = _route(b)
    assert result.status == RouteStatus.ABSTAIN
    assert result.reason == RouteReason.CROSS_FAMILY_FALLBACK


def test_incompatible_default_concept_card_layout_for_dynamic_is_rejected():
    b = _fixture_worked()
    b["scenegraph"] = _updated(b["scenegraph"], {"layout_intent": {
        "type": "CONCEPT_CARD", "reading_direction": "LEFT_TO_RIGHT"
    }})
    result = _route(b)
    assert result.status == RouteStatus.ABSTAIN
    assert result.reason == RouteReason.MISMATCHED_LAYOUT_INTENT


def test_unknown_family_from_input_is_rejected_by_v3_schema():
    b = _fixture_worked()
    with pytest.raises(ValidationError):
        _updated(b["pattern"], {"pattern_type": "ARBITRARY_MANIM_PYTHON"})


def test_section_options_mutation_blocks_route():
    b = _fixture_worked()
    b["plan"] = _section(b["plan"], options=["PROCESS_FLOW"])
    result = _route(b)
    assert result.status == RouteStatus.ABSTAIN
    assert result.reason == RouteReason.NOT_IN_SECTION_OPTIONS


def test_visual_budget_mutation_changes_provenance_and_decision():
    b = _fixture_worked(budget=6)
    before = _route(b)
    b["plan"] = _section(b["plan"], budget=3)
    after = _route(b)
    assert before.decision_hash != after.decision_hash
    assert before.source_audit_hash != after.source_audit_hash
    assert before.selected_variant != after.selected_variant
    assert not after.render_ready


def test_mutated_trace_without_matching_ledger_fails_closed_before_route():
    b = _fixture_worked()
    pat = b["pattern"].model_dump(mode="json")
    pat["state_source"]["ref"] = "trace:other"
    pat["source_refs"] = ["script:seg-01", "script:seg-02", "trace:other"]
    pat["semantic_objects"][0]["state_ref"] = "trace:other"
    b["pattern"] = VisualPatternSpec.model_validate(pat)
    b["verified_trace_refs"] = ("trace:other",)
    with pytest.raises(SemanticContractError, match="state ledger/pattern source mismatch"):
        _route(b)


def test_invalid_canonical_concept_ref_fails_closed_before_route():
    b = _fixture_worked()
    pat = b["pattern"].model_dump(mode="json")
    pat["concept_refs"][0]["canonical_key"] = "concept:wrong"
    b["pattern"] = VisualPatternSpec.model_validate(pat)
    with pytest.raises(SemanticContractError, match="canonical key mismatch"):
        _route(b)


def test_mutated_object_kind_loses_eligibility_without_card_fallback():
    b = _fixture_worked()
    pat = b["pattern"].model_dump(mode="json")
    pat["semantic_objects"][0]["kind"] = "LABEL"
    b["pattern"] = VisualPatternSpec.model_validate(pat)
    res = _route(b)
    assert res.status == RouteStatus.ABSTAIN
    assert res.reason == RouteReason.INVALID_STATE_OR_OBJECT_KINDS


def test_result_rejects_forged_render_ready_and_forged_accepted_status():
    result = _route(_fixture_worked())
    data = result.model_dump(mode="json")
    data["render_ready"] = True
    with pytest.raises(ValidationError):
        VisualPatternRoute.model_validate(data)
    data["render_ready"] = False
    data["status"] = "ABSTAIN"
    with pytest.raises(ValidationError, match="abstention"):
        VisualPatternRoute.model_validate(data)


def test_repeatability_across_reconstruction_and_no_external_apis():
    a = _fixture_static("EQUATION_GRAPH", budget=3)
    first = _route(a)
    second = _route(a)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    source = (ROOT / "learnflow_v3/pattern_router.py").read_text()
    assert "OPENROUTER_API_KEY" not in source
    assert "subprocess" not in source
    assert "render_scene_video" not in source


def test_linear_process_even_with_high_budget_keeps_linear_semantics():
    result = _route(_fixture_static("PROCESS_FLOW", budget=6))
    assert result.status == RouteStatus.SELECTED_UNRENDERABLE
    assert result.selected_variant == "PROCESS_LINEAR"
    assert result.fallback_used


def test_v2_visual_director_purpose_mismatch_fails_before_router():
    b = _fixture_worked()
    # V3-02 alone checks reference agreement, not full Visual Director intent.
    b["scenegraph"] = _updated(b["scenegraph"], {"purpose": "RECAP"})
    with pytest.raises(SemanticContractError, match="V2_VISUAL_DIRECTOR_GATE_FAILED"):
        _route(b)
