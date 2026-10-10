"""V3-40 contract tests: strictly local, no provider requests or credentials."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from learnflow_v3.creative_manim_ablation import Blocked, CreativeScene, fixture_plan
from learnflow_v3.strict_schema_parity_audit import (
    HOST_ONLY, assert_parity, audit, candidate_schema,
)
from learnflow_v3.structured_scene_authoring import normalize_wire, strict_wire_schema

ROOT = Path(__file__).resolve().parents[2]


def wire_fixture() -> dict:
    raw = fixture_plan().model_dump(mode="json", exclude={"model_author"})
    for beat in raw["beats"]:
        for motion in beat["actions"]:
            if motion.get("target") is None:
                motion["target"] = ""
            if motion.get("x") is None:
                motion["x"] = 0
            if motion.get("y") is None:
                motion["y"] = 0
    return raw


def host_validate(raw: dict) -> None:
    clean = normalize_wire(raw)
    CreativeScene.model_validate({**clean, "model_author": "openai/gpt-6-luna"})


def test_preregister_was_separate_and_explicitly_prohibits_model_http_post():
    p = json.loads((ROOT / "benchmarks/learnflowbench/v3/v3_40_strict_schema_parity_preregister.json").read_text())
    assert p["frozen_parent_pr"] == 73
    assert p["frozen_parent_head"] == "f5dd06a0dcb8b1cfd0398ea17c196c50aabaa0b5"
    assert p["preregistered_before_implementation"] is True
    assert p["model_http_posts_allowed"] == 0
    assert "model inference POST" in p["forbidden"]
    assert p["production"] == "BLOCKED"


def test_dynamic_contract_manifest_covers_bounds_and_failure_paths():
    schema = candidate_schema()
    Draft202012Validator.check_schema(schema)
    fields = {(c["field"], c["keyword"]): c["value"] for c in assert_parity(schema)}
    assert len(fields) >= 25
    assert fields[("root.objects[].height", "maximum")] == 2.4
    assert fields[("root.beats[].claim_ids", "minItems")] == 1
    assert fields[("root.beats", "minItems")] == 4
    assert fields[("root.beats", "maxItems")] == 4
    assert fields[("root.objects[].x", "minimum")] == -5.7
    assert fields[("root.beats[].actions[].y", "maximum")] == 2.55
    assert fields[("root.objects[].id", "pattern")] == "^[a-z][a-z0-9_]{0,22}$"
    assert Draft202012Validator(schema).is_valid(wire_fixture())
    host_validate(wire_fixture())


@pytest.mark.parametrize("path, value", [
    (("objects", 0, "height"), 2.41),
    (("objects", 1, "height"), 9),
    (("beats", 0, "claim_ids"), []),
    (("objects", 0, "x"), -5.71),
    (("objects", 0, "y"), 2.56),
    (("objects", 1, "width"), .24),
    (("objects", 0, "id"), "INVALID"),
    (("beats", 0, "narration"), "too short"),
    (("beats", 0, "visual_goal"), "bad"),
    (("beats", 0, "actions"), []),
    (("beats",), []),
    (("title",), "tiny"),
    (("learning_objective",), "short"),
])
def test_bounded_schema_and_host_both_reject_invalid_individual_limits(path, value):
    raw = wire_fixture()
    dest = raw
    for key in path[:-1]:
        dest = dest[key]
    dest[path[-1]] = value
    assert not Draft202012Validator(candidate_schema()).is_valid(raw), path
    with pytest.raises((ValidationError, Blocked)):
        host_validate(raw)


@pytest.mark.parametrize("mutation", [
    "duplicate_ids",
    "unsafe_numeric_fact",
    "unknown_animation_target",
    "unverified_claim_coverage",
])
def test_host_only_cross_field_rules_remain_fail_closed(mutation):
    raw = wire_fixture()
    if mutation == "duplicate_ids":
        raw["objects"][1]["id"] = raw["objects"][0]["id"]
    elif mutation == "unsafe_numeric_fact":
        raw["objects"][0]["text"] = "One half equals 3/7"
    elif mutation == "unknown_animation_target":
        raw["beats"][0]["actions"][0]["target"] = "absent_but_valid_id"
    elif mutation == "unverified_claim_coverage":
        for beat in raw["beats"]:
            beat["claim_ids"] = ["F1"]
    assert Draft202012Validator(candidate_schema()).is_valid(raw)
    with pytest.raises((ValidationError, Blocked)):
        host_validate(raw)


def test_placeholder_semantics_are_enforced_without_repair():
    raw = wire_fixture()
    raw["beats"][0]["actions"][0]["x"] = .5
    before = deepcopy(raw)
    assert Draft202012Validator(candidate_schema()).is_valid(raw)
    with pytest.raises(Blocked, match="V335_NONMOVE_UNUSED_COORD_NOT_ZERO"):
        normalize_wire(raw)
    assert raw == before


def test_candidate_drift_mutations_reject_even_if_mutation_loosens_bound():
    wire = candidate_schema()
    wire["properties"]["objects"]["items"]["properties"]["height"]["maximum"] = 3.0
    with pytest.raises(Blocked, match="V340_BOUND_DRIFT"):
        assert_parity(wire)
    other = candidate_schema()
    other["properties"]["beats"]["items"]["properties"]["claim_ids"]["minItems"] = 0
    with pytest.raises(Blocked, match="V340_BOUND_DRIFT"):
        assert_parity(other)


def test_existing_v339_wire_request_is_not_retroactively_modified():
    old = strict_wire_schema()
    new = candidate_schema()
    height = old["properties"]["objects"]["items"]["properties"]["height"]
    claim_ids = old["properties"]["beats"]["items"]["properties"]["claim_ids"]
    assert "maximum" not in height
    assert "minItems" not in claim_ids
    assert new["properties"]["objects"]["items"]["properties"]["height"]["maximum"] == 2.4
    assert new["properties"]["beats"]["items"]["properties"]["claim_ids"]["minItems"] == 1
    assert old == strict_wire_schema()
    assert len(HOST_ONLY) >= 8


def test_report_is_evidence_bounded_and_no_legacy_status_is_overridden():
    schema, report = audit(ROOT)
    assert schema == candidate_schema()
    assert report["checkpoint"] == "V3-40"
    assert report["model_inference_http_posts"] == 0
    assert report["provider_native_strict_bounds_enforcement"] == "NOT_VERIFIED"
    assert report["historical_v339_one_shot"] == "CONSUMED_NO_RETRY"
    assert report["real_model_mp4"] == "NOT_OBTAINED"
    assert report["production"] == "BLOCKED"


def test_v340_workflow_is_offline_and_contains_no_secret_or_trial_activation():
    workflow = (ROOT / ".github/workflows/v3-40-strict-schema-parity-audit.yml").read_text()
    assert "secrets." not in workflow
    assert "OPENROUTER_API_KEY" not in workflow
    assert "compatible_creative_trial" not in workflow
    assert "unique-preregistered-no-temperature-model-post" not in workflow
    assert "python -m learnflow_v3.strict_schema_parity_audit" in workflow
    assert "test_v3_40_strict_schema_parity.py" in workflow
