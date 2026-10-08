"""V3-05: independent binary search oracle, malicious trace and ledger mutations."""
from __future__ import annotations

from bisect import bisect_left
from itertools import combinations_with_replacement
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learnflow_v2.repair import compute_content_hash
from learnflow_v3 import SemanticContractError, VisualPatternSpec
from learnflow_v3.binary_search_trace import (
    BINARY_SEARCH_ORACLE_VERSION, BinarySearchInput, BinarySearchTrace,
    certify_and_route_binary_search, make_binary_search_trace,
    to_binary_search_state_ledger, verify_binary_search_ledger,
    verify_binary_search_trace,
)
from learnflow_v3.pattern_router import RouteStatus
from tests.v3.test_pattern_router import _fixture_worked


def _trace(values=(2, 3, 3, 3, 5), target=3):
    return make_binary_search_trace(values=values, target=target, source_ref="trace:trace-01")


def _modify_trace(trace, *, steps=None, result_index=None, source_ref=None, recompute_hash=False):
    data = trace.model_dump(mode="json")
    if steps is not None:
        data["steps"] = steps
    if result_index is not None:
        data["result_index"] = result_index
    if source_ref is not None:
        data["source_ref"] = source_ref
    if recompute_hash:
        data["trace_sha256"] = compute_content_hash({
            key: value for key, value in data.items() if key != "trace_sha256"
        })
    return BinarySearchTrace.model_validate(data)


def _binding():
    bundle = _fixture_worked(steps=2, budget=6)
    trace = _trace((3,), 3)
    beats = tuple(b.beat_id for b in bundle["plan"].beats)
    ledger = to_binary_search_state_ledger(
        trace=trace, pattern=bundle["pattern"], beat_refs=beats,
    )
    bundle["ledger"] = ledger
    example = "Binary search for 3 in [3]"
    script_dict = bundle["script"].model_dump(mode="json")
    script_dict["segments"][0]["spoken_text"] = example
    script_dict["segments"][0]["subtitle_text"] = example
    bundle["script"] = type(bundle["script"]).model_validate(script_dict)
    sb_dict = bundle["storyboard"].model_dump(mode="json")
    sb_dict["scenes"][0]["visual_intent"] = example
    bundle["storyboard"] = type(bundle["storyboard"]).model_validate(sb_dict)
    return bundle, trace


def test_leftmost_duplicate_policy_and_terminal_certification():
    trace = _trace()
    proof = verify_binary_search_trace(trace)
    assert trace.result_index == 1
    assert proof.oracle_index == 1
    assert proof.step_count == len(trace.steps)
    assert proof.assurance == "REPLAYED_EVERY_STEP_AND_BISECT_LEFT"
    assert trace.oracle_version == BINARY_SEARCH_ORACLE_VERSION
    assert trace.steps[-1].action == "FOUND"
    assert all(x.phase == "COMPARE" for x in trace.steps[:-1])


@pytest.mark.parametrize("values,target,expected", [
    ((), 5, None), ((2,), 2, 0), ((2,), 1, None), ((2,), 3, None),
    ((-8, -8, -1, 0, 2), -8, 0), ((2, 2, 2), 2, 0),
    ((1, 2, 2, 3), 2, 1), ((1, 2, 3), 4, None),
    ((1, 2, 3), 0, None), ((-6, -2, 0, 4), 0, 2),
])
def test_oracle_edge_cases(values, target, expected):
    trace = _trace(values, target)
    proof = verify_binary_search_trace(trace)
    assert proof.oracle_index == expected
    assert trace.result_index == expected
    assert trace.steps[-1].phase == "COMPLETE"
    assert trace.steps[-1].candidate_index == expected


def test_empty_array_explicit_terminal_step_not_a_fabricated_comparison():
    trace = _trace((), 5)
    assert len(trace.steps) == 1
    assert trace.steps[0].phase == "COMPLETE"
    assert trace.steps[0].low == 0
    assert trace.steps[0].high == -1
    assert trace.steps[0].action == "NOT_FOUND"
    assert verify_binary_search_trace(trace).oracle_index is None


def test_exhaustive_small_domain_property_against_independent_stdlib_oracle():
    count = 0
    for n in range(0, 7):
        for values in combinations_with_replacement((-2, -1, 0, 1, 2), n):
            for target in (-3, -2, -1, 0, 1, 2, 3):
                trace = _trace(values, target)
                proof = verify_binary_search_trace(trace)
                expected = bisect_left(values, target)
                expected = expected if expected < n and values[expected] == target else None
                assert proof.oracle_index == expected
                assert len(trace.steps) <= n.bit_length() + 2
                count += 1
    assert count >= 3000


@pytest.mark.parametrize("values,target", [
    ((3, 2), 2), ((1, 5, 4, 6), 5),
])
def test_unsorted_input_rejected_before_trace(values, target):
    with pytest.raises(ValidationError, match="UNSORTED_BINARY_SEARCH_INPUT"):
        _trace(values, target)


@pytest.mark.parametrize("values,target", [
    ((True, 2), 2), ((1, 2.0), 2), ((1, 2), False),
    (("1", 2), 2),
])
def test_non_integral_or_boolean_input_rejected(values, target):
    with pytest.raises(ValidationError):
        _trace(values, target)


def test_wrong_duplicate_policy_and_oversized_array_fail_closed():
    with pytest.raises(ValidationError):
        BinarySearchInput(values=(1, 1), target=1, duplicate_policy="ANY_MATCH")
    with pytest.raises(ValidationError, match="too_long"):
        BinarySearchInput(values=(0,) * 4097, target=0)


def test_deterministic_bytes_and_hash_over_separate_runs():
    a, b = _trace(), _trace()
    assert a == b
    assert a.model_dump_json() == b.model_dump_json()
    assert a.trace_sha256 == b.trace_sha256
    assert a.trace_sha256 != _trace(target=2).trace_sha256


def test_corrupted_trace_checksum_rejected():
    trace = _trace()
    steps = [x.model_dump(mode="json") for x in trace.steps]
    steps[0]["mid"] = 0
    tampered = _modify_trace(trace, steps=steps)
    with pytest.raises(SemanticContractError, match="TRACE_HASH_MISMATCH"):
        verify_binary_search_trace(tampered)


@pytest.mark.parametrize("mutate", [
    lambda s: s[0].update(mid=0),
    lambda s: s[0].update(low=1),
    lambda s: s[0].update(high=2),
    lambda s: s[0].update(observed=99),
    lambda s: s[0].update(action="DISCARD_LEFT"),
    lambda s: s[0].update(next_low=2),
    lambda s: s[0].update(next_high=3),
    lambda s: s[0].update(candidate_index=4),
])
def test_forged_rehashed_comparison_is_still_rejected_by_oracle(mutate):
    trace = _trace()
    steps = [x.model_dump(mode="json") for x in trace.steps]
    mutate(steps)
    forged = _modify_trace(trace, steps=steps, recompute_hash=True)
    with pytest.raises(SemanticContractError, match="STEP_MISMATCH"):
        verify_binary_search_trace(forged)


def test_early_termination_detected_even_with_valid_hash():
    trace = _trace((1, 3, 5, 7, 9), 9)
    steps = [x.model_dump(mode="json") for x in trace.steps]
    steps.pop(-2)
    forged = _modify_trace(trace, steps=steps, recompute_hash=True)
    with pytest.raises(SemanticContractError, match="EARLY_TERMINATION|TERMINAL_MISMATCH"):
        verify_binary_search_trace(forged)


def test_wrong_final_result_detected_after_rehash():
    trace = _trace((2, 2, 2), 2)
    forged = _modify_trace(trace, result_index=1, recompute_hash=True)
    with pytest.raises(SemanticContractError, match="TERMINAL_MISMATCH"):
        verify_binary_search_trace(forged)


def test_forged_terminal_action_detected_even_when_checksum_recomputed():
    trace = _trace()
    steps = [x.model_dump(mode="json") for x in trace.steps]
    steps[-1]["action"] = "NOT_FOUND"
    forged = _modify_trace(trace, steps=steps, recompute_hash=True)
    with pytest.raises(SemanticContractError, match="TERMINAL_MISMATCH"):
        verify_binary_search_trace(forged)


def test_missing_or_extra_comparison_is_rejected():
    trace = _trace()
    steps = [x.model_dump(mode="json") for x in trace.steps]
    skipped = _modify_trace(trace, steps=steps[1:], recompute_hash=True)
    with pytest.raises(SemanticContractError, match="STEP_MISMATCH"):
        verify_binary_search_trace(skipped)
    extended = _modify_trace(trace, steps=steps[:-1] + [steps[0], steps[-1]], recompute_hash=True)
    with pytest.raises(SemanticContractError, match="EXTRA_COMPARISON"):
        verify_binary_search_trace(extended)


def test_malformed_trace_phase_or_ref_rejected_by_schema():
    trace = _trace()
    raw = trace.model_dump(mode="json")
    raw["source_ref"] = "not:trace"
    with pytest.raises(ValidationError, match="INVALID_TRACE_REF"):
        BinarySearchTrace.model_validate(raw)
    raw = trace.model_dump(mode="json")
    raw["steps"][0]["phase"] = "COMPLETE"
    with pytest.raises(ValidationError, match="COMPLETE_STEP_HAS_COMPARISON_STATE"):
        BinarySearchTrace.model_validate(raw)


def test_trace_to_v3_ledger_has_stable_provenance_and_correct_state():
    bundle, trace = _binding()
    ledger = bundle["ledger"]
    proof = verify_binary_search_ledger(
        trace=trace, pattern=bundle["pattern"], ledger=ledger,
        beat_refs=tuple(b.beat_id for b in bundle["plan"].beats),
    )
    assert proof.trace_sha256 == trace.trace_sha256
    assert len(ledger.steps) == len(trace.steps) == 2
    assert ledger.source_ref == trace.source_ref
    assert ledger.pattern_ref == bundle["pattern"].pattern_id
    assert ledger.steps[0].object_states[0].properties["mid"] == 0
    assert ledger.steps[-1].object_states[0].properties["result_index"] == 0


def test_mutated_ledger_state_is_rejected_even_if_trace_ref_is_unchanged():
    bundle, trace = _binding()
    obj = bundle["ledger"].model_dump(mode="json")
    obj["steps"][0]["object_states"][0]["properties"]["low"] = 999
    forged = type(bundle["ledger"]).model_validate(obj)
    with pytest.raises(SemanticContractError, match="STATE_LEDGER_MISMATCH"):
        verify_binary_search_ledger(
            trace=trace, pattern=bundle["pattern"], ledger=forged,
            beat_refs=tuple(b.beat_id for b in bundle["plan"].beats),
        )


def test_wrong_or_duplicate_beat_alignment_rejected_before_ledger():
    bundle, trace = _binding()
    with pytest.raises(SemanticContractError, match="BEAT_ALIGNMENT_MISMATCH"):
        to_binary_search_state_ledger(trace=trace, pattern=bundle["pattern"], beat_refs=("beat-01",))
    with pytest.raises(SemanticContractError, match="BEAT_ALIGNMENT_MISMATCH"):
        to_binary_search_state_ledger(trace=trace, pattern=bundle["pattern"], beat_refs=("beat-01", "beat-01"))


def test_pattern_source_mismatch_blocks_reusing_verified_trace():
    bundle, trace = _binding()
    pat = bundle["pattern"].model_dump(mode="json")
    pat["state_source"]["ref"] = "trace:unrelated"
    pat["source_refs"] = ["script:seg-01", "script:seg-02", "trace:unrelated"]
    pat["semantic_objects"][0]["state_ref"] = "trace:unrelated"
    changed = VisualPatternSpec.model_validate(pat)
    with pytest.raises(SemanticContractError, match="PATTERN_SOURCE_MISMATCH"):
        to_binary_search_state_ledger(
            trace=trace, pattern=changed, beat_refs=("beat-01", "beat-02"),
        )


def test_verified_route_passes_oracle_first_then_existing_v3_gates():
    bundle, trace = _binding()
    result = certify_and_route_binary_search(trace=trace, **{
        key: value for key, value in bundle.items()
        if key not in ("verified_trace_refs",)
    })
    assert result.proof.oracle_index == 0
    assert result.proof.trace_ref == "trace:trace-01"
    assert result.route.status == RouteStatus.SELECTED_UNRENDERABLE
    assert result.route.selected_variant == "TRACE_SPOTLIGHT"
    assert result.render_ready is False
    assert result.route.render_ready is False


def test_incorrect_algorithm_with_correct_schema_cannot_reach_router():
    bundle, trace = _binding()
    steps = [x.model_dump(mode="json") for x in trace.steps]
    steps[0]["mid"] = 1
    forged = _modify_trace(trace, steps=steps, recompute_hash=True)
    with pytest.raises(SemanticContractError, match="STEP_MISMATCH"):
        certify_and_route_binary_search(trace=forged, **{
            key: value for key, value in bundle.items() if key != "verified_trace_refs"
        })


def test_bundle_cannot_use_unverified_ledger_even_if_source_ref_valid():
    bundle, trace = _binding()
    raw = bundle["ledger"].model_dump(mode="json")
    raw["steps"][-1]["object_states"][0]["properties"]["result_index"] = 777
    bundle["ledger"] = type(bundle["ledger"]).model_validate(raw)
    with pytest.raises(SemanticContractError, match="STATE_LEDGER_MISMATCH"):
        certify_and_route_binary_search(trace=trace, **{
            key: value for key, value in bundle.items() if key != "verified_trace_refs"
        })


def test_empty_input_remains_provable_but_router_abstains_no_fake_animation():
    bundle = _fixture_worked(steps=2, budget=6)
    trace = _trace((), 5)
    # Empty binary search has only a terminal step; V3-04 must not claim 2-step animation.
    with pytest.raises(SemanticContractError, match="BEAT_ALIGNMENT_MISMATCH"):
        to_binary_search_state_ledger(
            trace=trace, pattern=bundle["pattern"], beat_refs=("beat-01", "beat-02")
        )


def test_no_api_no_renderer_implementation_added():
    src = (ROOT / "learnflow_v3/binary_search_trace.py").read_text(encoding="utf-8")
    assert "OPENROUTER_API_KEY" not in src
    assert "render_scene_video" not in src
    assert "subprocess" not in src



def test_trace_algorithm_correct_but_wrong_taught_target_must_fail_closed():
    bundle, trace = _binding()
    sb = bundle["storyboard"].model_dump(mode="json")
    sb["scenes"][0]["visual_intent"] = "Binary search for 4 in [3]"
    bundle["storyboard"] = type(bundle["storyboard"]).model_validate(sb)
    with pytest.raises(SemanticContractError, match="BINARY_SEARCH_SEMANTIC_INPUT_MISMATCH"):
        certify_and_route_binary_search(trace=trace, **{
            key: value for key, value in bundle.items() if key != "verified_trace_refs"
        })


def test_unmentioned_binary_search_example_cannot_be_inferred_from_valid_trace():
    bundle, trace = _binding()
    d = bundle["script"].model_dump(mode="json")
    d["segments"][0]["spoken_text"] = "Today we learn binary search."
    d["segments"][0]["subtitle_text"] = "Today we learn binary search."
    bundle["script"] = type(bundle["script"]).model_validate(d)
    with pytest.raises(SemanticContractError, match="BINARY_SEARCH_CANONICAL_INPUT_UNGROUNDED"):
        certify_and_route_binary_search(trace=trace, **{
            key: value for key, value in bundle.items() if key != "verified_trace_refs"
        })


def test_malformed_explicit_example_rejected_not_silently_discarded():
    from learnflow_v3.binary_search_trace import _explicit_binary_search_example
    with pytest.raises(SemanticContractError, match="EXAMPLE_INVALID_INTEGER"):
        _explicit_binary_search_example("Binary search for 3 in [3, oops]")
    with pytest.raises(SemanticContractError, match="EXAMPLE_AMBIGUOUS_OR_MALFORMED"):
        _explicit_binary_search_example("Binary search for 3 in [1] and binary search for 5 in [5]")
    assert _explicit_binary_search_example("Binary search for 5 in []").values == ()


def test_explicit_registry_example_if_present_must_match_trace():
    from learnflow_v2.concepts.schema import ConceptEntry
    from learnflow_v2.concepts import ConceptRegistry
    from learnflow_v3.binary_search_trace import verify_binary_search_teaching_binding
    bundle, trace = _binding()
    registry = ConceptRegistry()
    registry.register(ConceptEntry(
        concept_id="c_alg", canonical_key="concept:algorithm",
        label="Worked example: Binary search for 4 in [3]",
    ))
    with pytest.raises(SemanticContractError, match="SEMANTIC_INPUT_MISMATCH"):
        verify_binary_search_teaching_binding(
            trace=trace, pattern=bundle["pattern"], registry=registry,
            script=bundle["script"], storyboard=bundle["storyboard"],
        )
