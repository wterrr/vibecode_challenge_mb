"""V3-81 hostile and metamorphic cross-domain arithmetic evidence tests."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import pytest

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.v381_generic_semantic_operators import (
    OPS, calculate, parse_value, validate_case
)
from learnflow_v3.v381_finite_manim_compiler import source
from scripts.run_v3_81_cross_topic_semantic_native import registered

ROOT = Path(__file__).resolve().parents[2]


def rows():
    return json.loads((ROOT / "benchmarks/learnflowbench/v3/v3_81_domain_agnostic_preregister.json").read_text())["cases"]


@pytest.mark.parametrize("index", range(4))
def test_each_locked_case_has_recomputed_exact_proofs(index):
    c = rows()[index]
    trace = validate_case(c)
    assert trace["all_numeric_outputs_verified"] is True
    assert len(trace["events"]) == len(c["operations"]) >= 2
    assert trace["domain"] == c["domain"] and trace["input_sha256"]
    assert all(e["host_arithmetic_attested"] and e["claim_id"] in c["claims"] for e in trace["events"])
    assert trace["natural_language_claim_truth_verified"] is False


def test_preregister_happened_before_code_and_roles_locked():
    p, digest = registered()
    assert p["parent"]["pr"] == 117
    assert p["parent"]["sha"] == "63135f9e9986b606dfea7b8915b2ea99658066a6"
    assert p["restrictions"]["model_api_requests"] == 0
    assert p["restrictions"]["main_merge"] is False
    assert p["restrictions"]["production"] == "BLOCKED"
    assert p["locked_roles"] == {"development": 3, "heldout": 1}
    assert len(digest) == 64


def test_operator_set_is_typed_not_topic_dispatched():
    assert OPS == {"SCALE", "ADD", "EQUIVALENT_PARTITION"}
    c = deepcopy(rows()[2])
    base = validate_case(c)
    c["domain"] = "unseen_biology_example"
    c["id"] = "novel_topic_same_algebra"
    new = validate_case(c)
    assert [x["actual"] for x in new["events"]] == [x["actual"] for x in base["events"]]


def test_attention_exact_weighted_vector_aggregation():
    s = validate_case(rows()[0])["state"]
    assert s["left_contribution"] == {"kind": "vector",
        "items": [{"kind": "scalar", "n": 3, "d": 2},
                  {"kind": "scalar", "n": 3, "d": 1}]}
    assert s["context"] == {"kind": "vector",
        "items": [{"kind": "scalar", "n": 2, "d": 1},
                  {"kind": "scalar", "n": 3, "d": 1}]}


def test_fraction_geometry_preserves_rational_area():
    events = validate_case(rows()[1])["events"]
    assert len(events) == 2
    for e in events:
        before, after = e["operands"][0], e["actual"]
        assert Fraction(before["n"], before["d"]) == Fraction(after["n"], after["d"])
        assert after["d"] <= 24


def test_heldout_running_state_uses_same_add_operator():
    s = validate_case(rows()[3])["state"]
    assert s["sum_after_first"]["n"] == 3
    assert s["sum_after_second"]["n"] == 7


@pytest.mark.parametrize("case_index", range(4))
def test_compiler_emits_safe_source_for_four_domains(case_index):
    trace = validate_case(rows()[case_index])
    output = source(trace, [10.0] * len(trace["events"]))
    compile(output, "<v381-test>", "exec")
    assert output.count("GROUND_TRUTH_STEP_") == len(trace["events"])
    assert "from manim import *" in output
    assert "eval(" not in output and "subprocess" not in output
    if "EQUIVALENT_PARTITION" in trace["native_operator_kinds"]:
        assert "Transform(before_" in output
    else:
        assert "TransformFromCopy(" in output


def test_wrong_output_fails_before_renderer():
    c = deepcopy(rows()[2])
    c["operations"][-1]["expected"]["n"] = 15
    with pytest.raises(Blocked, match="V381_CLAIMED_ARITHMETIC_NOT_HOST_VERIFIED"):
        validate_case(c)


def test_wrong_fraction_proportion_fails():
    c = deepcopy(rows()[1])
    c["operations"][0]["expected"]["n"] = 5
    with pytest.raises(Blocked, match="V381_CLAIMED_ARITHMETIC_NOT_HOST_VERIFIED"):
        validate_case(c)


def test_forward_reference_or_missing_fact_rejected():
    c = deepcopy(rows()[0])
    c["operations"][0]["inputs"][0] = "context"
    with pytest.raises(Blocked, match="V381_FORWARD_OR_UNGROUNDED_REFERENCE"):
        validate_case(c)


def test_duplicate_output_rejected():
    c = deepcopy(rows()[3])
    c["operations"][1]["id"] = c["operations"][0]["id"]
    with pytest.raises(Blocked, match="V381_DUPLICATE_OUTPUT_OR_INVALID_ID"):
        validate_case(c)


def test_unbound_claim_rejected():
    c = deepcopy(rows()[0])
    c["operations"][0]["claim_id"] = "UNRELATED"
    with pytest.raises(Blocked, match="V381_UNBOUND_CLAIM"):
        validate_case(c)


@pytest.mark.parametrize("kind", ["PYTHON", "MOVE", "UNVERIFIED_EQUIVALENCE"])
def test_unknown_operator_rejected(kind):
    c = deepcopy(rows()[2])
    c["operations"][0]["kind"] = kind
    with pytest.raises(Blocked, match="V381_UNSUPPORTED_OPERATION"):
        validate_case(c)


@pytest.mark.parametrize("bad", [0, -1, True, 2.7])
def test_invalid_denominator_rejected(bad):
    c = deepcopy(rows()[0])
    c["facts"]["weight_a"]["d"] = bad
    with pytest.raises(Blocked, match="V381_"):
        validate_case(c)


@pytest.mark.parametrize("factor", [0, 1, -2, 100])
def test_bad_partition_factor_rejected(factor):
    c = deepcopy(rows()[1])
    c["facts"]["two"]["n"] = factor
    with pytest.raises(Blocked, match="V381_"):
        validate_case(c)


def test_mismatched_vector_dimensions_rejected():
    a = parse_value({"kind": "vector", "items": [{"kind": "scalar", "n": 1, "d": 1}]})
    b = parse_value({"kind": "vector", "items": [{"kind": "scalar", "n": 1, "d": 1},
                                               {"kind": "scalar", "n": 2, "d": 1}]})
    with pytest.raises(Blocked, match="V381_VECTOR_DIMENSION_MISMATCH"):
        calculate("ADD", [a, b])


def test_wrong_kind_cannot_be_silently_coerced():
    with pytest.raises(Blocked, match="V381_UNSUPPORTED_ADD_TYPES"):
        calculate("ADD", [
            parse_value({"kind": "scalar", "n": 2, "d": 1}),
            parse_value({"kind": "fraction", "n": 1, "d": 2})])


def test_compiler_rejects_untrusted_content():
    c = deepcopy(rows()[3])
    c["title"] = "__import__('os').system('id')"
    with pytest.raises(Blocked, match="V381_UNSAFE_EMITTED_SOURCE"):
        source(validate_case(c), [10.0] * len(c["operations"]))


def test_cannot_spoof_real_model_origin():
    c = deepcopy(rows()[3])
    c["origin"] = "REAL_MODEL_CREATED"
    with pytest.raises(Blocked, match="V381_CASE_SCHEMA"):
        validate_case(c)


def test_no_false_claim_of_human_learning():
    trace = validate_case(rows()[2])
    assert trace["natural_language_claim_truth_verified"] is False
    assert trace["model_authoring"] == "NOT_TESTED"


def test_no_topic_id_switch_in_interpreter_source():
    text = (ROOT / "learnflow_v3/v381_generic_semantic_operators.py").read_text()
    for token in ("if domain ==", "if topic ==", "if case_id ==", "attention_context",
                  "physics_velocity", "fraction_partition", "cs_running_sum"):
        assert token not in text


def test_audio_length_and_event_count_drift_blocked():
    trace = validate_case(rows()[0])
    with pytest.raises(Blocked, match="V381_AUDIO_BUDGET_OUT_OF_BOUNDS"):
        source(trace, [4.0] * len(trace["events"]))
    with pytest.raises(Blocked, match="V381_NARRATION_TIMELINE_DRIFT"):
        source(trace, [10.0])
