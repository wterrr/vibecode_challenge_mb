"""V3-41 offline protocol security, semantic, schema and provenance tests.

No live calls, credentials, provider POST or provider-enforced-schema claim.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from learnflow_v3.compatible_scene_protocol import (
    ALLOWED_KEYWORDS, CLAIM_SLOTS, MAX_TOTAL_ENUM_VALUES, REQUIRED_BEATS,
    _forbid_unsupported, audit_protocol, candidate_request_body,
    decode_portable_wire, offline_synthetic_wire_fixture, portable_wire_schema)
from learnflow_v3.creative_manim_ablation import Blocked, CreativeScene, fixture_plan
from learnflow_v3.structured_scene_authoring import strict_wire_schema

ROOT = Path(__file__).resolve().parents[2]


def test_prereg_is_offline_and_parent_is_frozen():
    p = json.loads((ROOT / "benchmarks/learnflowbench/v3/v3_41_provider_compatible_protocol_preregister.json").read_text())
    assert p["checkpoint"] == "V3-41"
    assert p["preregistered_before_implementation"] is True
    assert p["frozen_parent_sha"] == "491e6378d6323ae3a030d308406e9b846a06e80c"
    assert p["current_authorization"]["model_inference_http_posts"] == 0
    assert p["current_authorization"]["authenticated_provider_gets"] == 0
    assert p["future_live_trial"]["requires_separate_explicit_authorization"] is True
    assert p["future_live_trial"]["implemented_in_this_phase"] is False


def test_only_portable_keywords_and_strict_fields():
    s = portable_wire_schema()
    Draft202012Validator.check_schema(s)
    assert _forbid_unsupported(s) <= MAX_TOTAL_ENUM_VALUES
    assert "minimum" not in json.dumps(s)
    assert "maximum" not in json.dumps(s)
    assert "minItems" not in json.dumps(s)
    assert "maxItems" not in json.dumps(s)
    assert "pattern" not in json.dumps(s)
    assert "$ref" not in json.dumps(s)
    assert set(s["properties"]["beats"]["required"]) == set(REQUIRED_BEATS)
    first = s["properties"]["beats"]["properties"]["beat_1"]
    assert set(first["properties"]) == {"claim_primary", "claim_secondary", "claim_tertiary",
                                         "narration", "visual_goal", "actions"}
    assert first["properties"]["claim_primary"]["enum"] == ["F1", "F2", "F3"]
    assert first["properties"]["claim_secondary"]["enum"] == ["", "F1", "F2", "F3"]
    assert set(ALLOWED_KEYWORDS) == {
        "type", "properties", "required", "additionalProperties",
        "enum", "items", "description"}


def test_numeric_enum_generated_from_host_limits_and_has_useful_granularity():
    s = portable_wire_schema()
    graphic = s["properties"]["objects"]["items"]["properties"]
    action = s["properties"]["beats"]["properties"]["beat_1"]["properties"]["actions"]["items"]["properties"]
    heights = graphic["height"]["enum"]
    assert .6 in heights and .9 in heights and 2.4 in heights
    assert all(.18 <= x <= 2.4 for x in heights)
    assert 2.41 not in heights
    assert 0 in action["x"]["enum"]
    assert len(action["x"]["enum"]) >= 50
    assert len(graphic["x"]["enum"]) >= 110
    assert graphic["width"]["enum"] != [1]
    assert graphic["radius"]["enum"] != [.45]


def test_synthetic_fixture_round_trip_preserves_all_semantic_choices():
    raw = offline_synthetic_wire_fixture()
    assert Draft202012Validator(portable_wire_schema()).is_valid(raw)
    plan = CreativeScene.model_validate(decode_portable_wire(raw))
    original = fixture_plan().model_dump(mode="json")
    assert plan.model_dump(mode="json") == original
    assert set(raw["beats"]) == set(REQUIRED_BEATS)
    assert raw["beats"]["beat_1"]["claim_primary"] == "F1"
    assert raw["beats"]["beat_1"]["claim_secondary"] == ""


@pytest.mark.parametrize("mutation", [
    "bad_height_first", "bad_height_second", "empty_primary", "missing_primary",
    "missing_beat", "extra_beat", "claim_ids_old_wire", "unsafe_action",
    "bad_object_position", "bad_move_position", "foreign_model_author",
])
def test_v339_reproductions_and_extra_wire_mutations_fail_before_host(mutation):
    raw = offline_synthetic_wire_fixture()
    if mutation == "bad_height_first":
        raw["objects"][0]["height"] = 2.41
    elif mutation == "bad_height_second":
        raw["objects"][1]["height"] = 200
    elif mutation == "empty_primary":
        raw["beats"]["beat_1"]["claim_primary"] = ""
    elif mutation == "missing_primary":
        del raw["beats"]["beat_1"]["claim_primary"]
    elif mutation == "missing_beat":
        del raw["beats"]["beat_1"]
    elif mutation == "extra_beat":
        raw["beats"]["beat_5"] = deepcopy(raw["beats"]["beat_4"])
    elif mutation == "claim_ids_old_wire":
        raw["beats"]["beat_1"]["claim_ids"] = []
    elif mutation == "unsafe_action":
        raw["beats"]["beat_1"]["actions"][0]["action"] = "exec"
    elif mutation == "bad_object_position":
        raw["objects"][0]["x"] = -99
    elif mutation == "bad_move_position":
        raw["beats"]["beat_1"]["actions"][0]["x"] = 50
    else:
        raw["model_author"] = "trusted-real-model"
    before = deepcopy(raw)
    assert not Draft202012Validator(portable_wire_schema()).is_valid(raw)
    with pytest.raises(Blocked, match="V341_WIRE_SCHEMA_REJECTED"):
        decode_portable_wire(raw)
    assert raw == before


@pytest.mark.parametrize("mutation", [
    "invalid_equation", "duplicate_id", "empty_coverage", "action_before_show",
    "illegal_placeholder", "too_short_narration",
])
def test_host_only_semantic_rules_remain_fail_closed(mutation):
    raw = offline_synthetic_wire_fixture()
    if mutation == "invalid_equation":
        raw["objects"][0]["text"] = "one half equals 3/7"
    elif mutation == "duplicate_id":
        raw["objects"][1]["id"] = raw["objects"][0]["id"]
    elif mutation == "empty_coverage":
        for beat in raw["beats"].values():
            beat["claim_primary"] = "F1"
            beat["claim_secondary"] = ""
            beat["claim_tertiary"] = ""
    elif mutation == "action_before_show":
        raw["beats"]["beat_1"]["actions"][0]["action"] = "emphasize"
    elif mutation == "illegal_placeholder":
        raw["beats"]["beat_1"]["actions"][0]["x"] = 0.2
    else:
        raw["beats"]["beat_1"]["narration"] = "short"
    assert Draft202012Validator(portable_wire_schema()).is_valid(raw)
    with pytest.raises(Blocked):
        decode_portable_wire(raw)


def test_request_preview_is_one_strict_no_temp_no_fallback_data_only():
    body = candidate_request_body()
    assert body["model"] == "openai/gpt-6-luna"
    assert "temperature" not in body
    assert body["max_tokens"] == 6500
    assert body["provider"] == {"allow_fallbacks": False, "require_parameters": True}
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"] == portable_wire_schema()
    assert len(body["messages"]) == 2
    msg = json.loads(body["messages"][1]["content"])
    assert msg["wire_rules"][0].startswith("Return exactly four")
    assert msg["output_protocol"].startswith("v3-41-")
    assert "schema" not in msg  # old V3-34 hint is incompatible with v341
    assert not any("key" in k.lower() for k in body)


def test_old_schema_is_still_original_and_new_wire_never_mutates_it():
    historical = deepcopy(strict_wire_schema())
    wire = portable_wire_schema()
    assert wire != historical
    assert strict_wire_schema() == historical
    assert "claim_ids" in historical["properties"]["beats"]["items"]["properties"]
    assert "claim_ids" not in wire["properties"]["beats"]["properties"]["beat_1"]["properties"]


def test_reject_disguised_synthetic_media_without_trusting_self_report(tmp_path):
    from learnflow_v3.creative_evidence_gate import EvidenceRejected, inspect_candidate
    receipt = {
        "checkpoint": "V3-34",
        "model_plan_origin": "SYNTHETIC_V341_COMPAT_WIRE_FIXTURE_NOT_REAL_MODEL",
        "production": "BLOCKED",
    }
    (tmp_path / "v3_34_ablation_receipt.json").write_text(json.dumps(receipt))
    with pytest.raises(EvidenceRejected, match="NOT_REAL_MODEL_SCENE"):
        inspect_candidate(tmp_path)


def test_never_route_offline_fixture_through_live_runner(monkeypatch, tmp_path):
    from learnflow_v3 import creative_manim_runner as runner
    monkeypatch.setattr(runner, "checked_manifest", lambda _: {"topic_id": "lfb-018-math"})
    with pytest.raises(Blocked, match="V341_OFFLINE_WIRE_OR_NO_NETWORK_CONTRACT"):
        runner.run(ROOT, tmp_path, mode="offline-v341-compatible",
                   compatible_wire=offline_synthetic_wire_fixture(), key="FAKE")
    with pytest.raises(Blocked, match="V341_OFFLINE_WIRE_NOT_ALLOWED_IN_LEGACY_MODE"):
        runner.run(ROOT, tmp_path, mode="offline-smoke",
                   compatible_wire=offline_synthetic_wire_fixture())


def test_audit_does_not_claim_model_provenance():
    a = audit_protocol()
    assert a["model_inference_http_posts"] == 0
    assert a["synthetic_fixture_host_valid"] is True
    assert a["model_authored_mp4"] == "NOT_OBTAINED"
    assert a["strict_endpoint_native_enforcement"] == "NOT_VERIFIED"
    assert a["production"] == "BLOCKED"
