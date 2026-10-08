"""V3-03 falsifiable signal-consumption declarations and mutation invalidation."""
from __future__ import annotations

from pathlib import Path
import sys
from copy import deepcopy
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learnflow_v3 import VisualTeachingPlan, VisualPatternSpec, StateLedger, SemanticContractError
from learnflow_v3 import signal_preservation as sp
from tests.v3.test_contracts import valid_objects


def _mutate(obj, field, value):
    data = obj.model_dump(mode="json")
    data[field] = value
    return type(obj).model_validate(data)


def _audit(**replacements):
    args = valid_objects()
    args.update(replacements)
    return sp.audit_signal_preservation(**args)


def test_every_leaf_has_explicit_stage_or_declared_unconsumed_owner():
    report = _audit()
    paths = {r.path for r in report.routes}
    assert len(paths) == len(report.routes)
    assert report.version == "3.0.3"
    assert report.assurance == "SEMANTIC_GATE_ONLY_NO_PIXEL_PROOF"
    assert report.render_ready is False
    assert paths
    assert {r.status for r in report.routes} == {
        sp.SignalStatus.SEMANTIC_GATED,
        sp.SignalStatus.DECLARED_UNCONSUMED,
    }
    assert "plan.sections.0.visual_teaching_goal" in report.declared_unconsumed_paths
    assert "pattern.pattern_type" in report.declared_unconsumed_paths
    assert "ledger.steps.0.object_states.0.properties" in report.declared_unconsumed_paths
    assert all(r.consumer.startswith(("v3.", "future:")) for r in report.routes)
    assert len(report.source_hashes) == 8


def test_strict_catalog_detects_dead_signals_when_policy_mapping_removed(monkeypatch):
    before = _audit()
    assert before.semantic_gate_hash
    monkeypatch.setattr(
        sp, "DEFERRED_PATHS",
        {key: value for key, value in sp.DEFERRED_PATHS.items()
         if key != "plan.sections.*.visual_teaching_goal"},
    )
    with pytest.raises(SemanticContractError, match="UNDECLARED_SEMANTIC_SIGNAL"):
        _audit()


def test_stage_proof_is_not_renderer_proof_and_no_unconsumed_signal_may_publish():
    evidence = _audit()
    with pytest.raises(SemanticContractError, match="DEAD_SIGNAL_BLOCKED"):
        evidence.require_render_consumption()
    with pytest.raises(SemanticContractError, match="NO_RENDERER_CONSUMPTION_PROOF"):
        evidence.model_copy(update={"routes": tuple(
            r for r in evidence.routes if r.status == sp.SignalStatus.SEMANTIC_GATED
        )}).require_render_consumption()


def test_deterministic_fingerprints_ignore_mapping_insertion_order():
    a, b = _audit(), _audit()
    assert a.semantic_gate_hash == b.semantic_gate_hash
    assert a.audit_hash == b.audit_hash
    assert a.routes == b.routes


@pytest.mark.parametrize("target,value", [
    ("visual_teaching_goal", "Teach the comparison with a table"),
    ("learner_state_before", "Learner has misconceptions"),
    ("hero_candidate", True),
    ("visual_complexity_budget", 6),
])
def test_deferred_pedagogy_signal_mutation_changes_audit_not_false_gate(target, value):
    base = valid_objects()
    before = sp.audit_signal_preservation(**base)
    newplan = base["plan"].model_dump(mode="json")
    newplan["sections"][0][target] = value
    after = _audit(plan=VisualTeachingPlan.model_validate(newplan))
    assert before.source_hashes["plan"] != after.source_hashes["plan"]
    assert before.audit_hash != after.audit_hash
    assert before.semantic_gate_hash == after.semantic_gate_hash
    assert sp.assert_mutation_invalidation(before, after)
    with pytest.raises(SemanticContractError, match="DEAD_SIGNAL_BLOCKED"):
        after.require_render_consumption()


def test_state_value_mutation_cannot_claim_it_changed_visual_pixels():
    base = valid_objects()
    before = sp.audit_signal_preservation(**base)
    ledger_data = base["ledger"].model_dump(mode="json")
    ledger_data["steps"][0]["object_states"][0]["properties"]["index"] = 2
    after = _audit(ledger=StateLedger.model_validate(ledger_data))
    assert before.semantic_gate_hash == after.semantic_gate_hash  # no actual stateful renderer
    assert before.audit_hash != after.audit_hash
    assert before.source_hashes["ledger"] != after.source_hashes["ledger"]
    assert sp.assert_mutation_invalidation(before, after) == (
        "ledger.steps.0.object_states.0.properties",
    )
    assert "PIXEL" in before.assurance


def test_declared_beat_visual_intent_changes_audit_but_not_renderer_gate():
    original = valid_objects()
    baseline = sp.audit_signal_preservation(**original)
    data = original["plan"].model_dump(mode="json")
    data["beats"][0]["expected_visible_state_change"] = "Update search window based on midpoint"
    mutated = _audit(plan=VisualTeachingPlan.model_validate(data))
    assert sp.assert_mutation_invalidation(baseline, mutated)
    assert mutated.semantic_gate_hash == baseline.semantic_gate_hash
    assert mutated.audit_hash != baseline.audit_hash
    assert any(
        r.normalized_path == "plan.beats.*.expected_visible_state_change"
        and r.status == sp.SignalStatus.DECLARED_UNCONSUMED
        for r in mutated.routes
    )
    with pytest.raises(SemanticContractError, match="DEAD_SIGNAL_BLOCKED"):
        mutated.require_render_consumption()


def test_objective_mutation_requires_all_cross_artifact_references_to_update():
    original = valid_objects()
    data = original["plan"].model_dump(mode="json")
    data["learning_objective_ids"] = ["obj-new"]
    with pytest.raises(Exception, match="unknown learning objective"):
        _audit(plan=VisualTeachingPlan.model_validate(data))

    # All validated dependencies change together, otherwise fail-closed.
    data["sections"][0]["objective_refs"] = ["obj-new"]
    plan = VisualTeachingPlan.model_validate(data)
    pattern_data = original["pattern"].model_dump(mode="json")
    pattern_data["objective_refs"] = ["obj-new"]
    pattern = VisualPatternSpec.model_validate(pattern_data)
    old_segment = original["script"].segments[0]
    new_segment = old_segment.model_copy(update={"objective_ids": ("obj-new",)})
    script = original["script"].model_copy(update={"segments": (new_segment,)})
    baseline = sp.audit_signal_preservation(**original)
    changed = _audit(plan=plan, pattern=pattern, script=script)
    assert changed.semantic_gate_hash != baseline.semantic_gate_hash
    assert changed.audit_hash != baseline.audit_hash
    assert sp.assert_mutation_invalidation(baseline, changed)


def test_canonical_concept_identity_mutation_rejects_before_provenance():
    baseline = valid_objects()
    data = baseline["plan"].model_dump(mode="json")
    data["beats"][0]["concept_refs"][0]["canonical_key"] = "concept:unknown"
    with pytest.raises(SemanticContractError, match="canonical key mismatch"):
        _audit(plan=VisualTeachingPlan.model_validate(data))


def test_beat_rename_requires_ledger_rebinding_or_fail():
    baseline = valid_objects()
    plan_data = baseline["plan"].model_dump(mode="json")
    plan_data["beats"][0]["beat_id"] = "beat-renamed"
    plan = VisualTeachingPlan.model_validate(plan_data)
    with pytest.raises(SemanticContractError, match="orphan ledger beat"):
        _audit(plan=plan)
    ledger_data = baseline["ledger"].model_dump(mode="json")
    ledger_data["steps"][0]["beat_ref"] = "beat-renamed"
    changed = _audit(plan=plan, ledger=StateLedger.model_validate(ledger_data))
    old = sp.audit_signal_preservation(**baseline)
    assert changed.semantic_gate_hash != old.semantic_gate_hash
    assert sp.assert_mutation_invalidation(old, changed)


def test_trace_ref_mutation_propagates_or_fails_provenance():
    original = valid_objects()
    pattern_data = original["pattern"].model_dump(mode="json")
    pattern_data["state_source"]["ref"] = "trace:new-02"
    pattern_data["source_refs"] = ["script:seg-01", "trace:new-02"]
    pattern_data["semantic_objects"][0]["state_ref"] = "trace:new-02"
    changed_pattern = VisualPatternSpec.model_validate(pattern_data)
    with pytest.raises(SemanticContractError, match="state ledger/pattern source mismatch"):
        _audit(pattern=changed_pattern, verified_trace_refs=("trace:new-02",))
    ledger_data = original["ledger"].model_dump(mode="json")
    ledger_data["source_ref"] = "trace:new-02"
    changed_ledger = StateLedger.model_validate(ledger_data)
    with pytest.raises(SemanticContractError, match="trace provenance unverified"):
        _audit(pattern=changed_pattern, ledger=changed_ledger)
    new = _audit(pattern=changed_pattern, ledger=changed_ledger,
                 verified_trace_refs=("trace:new-02",))
    old = sp.audit_signal_preservation(**original)
    assert new.semantic_gate_hash != old.semantic_gate_hash
    assert sp.assert_mutation_invalidation(old, new)
    assert new.render_ready is False


def test_forged_unmodified_downstream_fingerprint_is_detected():
    before = _audit()
    baseline = valid_objects()
    plan_data = baseline["plan"].model_dump(mode="json")
    plan_data["beats"][0]["beat_id"] = "beat-renamed"
    ledger_data = baseline["ledger"].model_dump(mode="json")
    ledger_data["steps"][0]["beat_ref"] = "beat-renamed"
    after = _audit(
        plan=VisualTeachingPlan.model_validate(plan_data),
        ledger=StateLedger.model_validate(ledger_data),
    )
    forged = after.model_copy(update={"semantic_gate_hash": before.semantic_gate_hash})
    with pytest.raises(SemanticContractError, match="STALE_SEMANTIC_GATE_FINGERPRINT"):
        sp.assert_mutation_invalidation(before, forged)


def test_forged_audit_hash_is_detected():
    before = _audit()
    baseline = valid_objects()
    plan_data = baseline["plan"].model_dump(mode="json")
    plan_data["sections"][0]["visual_teaching_goal"] = "Focus on the invariant"
    after = _audit(plan=VisualTeachingPlan.model_validate(plan_data))
    forged = after.model_copy(update={"audit_hash": before.audit_hash})
    with pytest.raises(SemanticContractError, match="STALE_AUDIT_HASH"):
        sp.assert_mutation_invalidation(before, forged)


def test_mutating_nested_dict_on_frozen_model_is_not_silently_accepted():
    objects = valid_objects()
    first = sp.audit_signal_preservation(**objects)
    # Pydantic frozen=True does not freeze nested JSON dictionaries.
    objects["ledger"].steps[0].object_states[0].properties["index"] = 3
    second = sp.audit_signal_preservation(**objects)
    assert first.audit_hash != second.audit_hash
    assert first.semantic_gate_hash == second.semantic_gate_hash
    assert sp.assert_mutation_invalidation(first, second)


def test_no_semantic_delta_is_not_a_proof_of_invalidation():
    a = _audit()
    with pytest.raises(SemanticContractError, match="NO_SEMANTIC_MUTATION_DETECTED"):
        sp.assert_mutation_invalidation(a, a)


def test_verified_trace_declaration_is_versioned_provenance_not_oracle_proof():
    original = valid_objects()
    baseline = sp.audit_signal_preservation(**original)
    amended = _audit(verified_trace_refs=("trace:trace-01", "trace:other-02"))
    assert baseline.source_hashes["verified_trace_refs"] != amended.source_hashes["verified_trace_refs"]
    assert baseline.semantic_gate_hash != amended.semantic_gate_hash
    assert baseline.audit_hash != amended.audit_hash
    assert baseline.render_ready is False
