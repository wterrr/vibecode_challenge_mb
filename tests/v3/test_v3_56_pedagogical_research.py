"""V3-56 offline research-only contract regression; no real model request."""
import copy
import pytest
from jsonschema import Draft202012Validator
from scripts.verify_v3_56_research import check, load, ARCH, PROTOCOL, MATRIX, ROOT, validate_frozen_ablation_arms


def valid_research_contract():
    schema=load(ARCH)["schema"]
    return {
      "contract_version":"research-v3-56-proposal-v1",
      "scope":{"topic_id":"heldout","approved_claim_ids":["H1"],"host_ledger_sha256":"a"*64},
      "learning_difficulty":{"description":"Predict the effect of an operation",
                             "misconception_hypothesis":"number table is an entire mechanism",
                             "probe_question":"What should visibly change next?",
                             "source_scope":"HYPOTHESIZED_FROM_TASK"},
      "target_mental_model":{"model_description":"a state transforms under a known operation",
                            "observable_change":"the same object changes with a verified invariant"},
      "visual_representation":{"representation_kind":"spatial_grid",
                               "why_this_representation":"a spatial relation explains motion",
                               "capability_ids":["host_verified_grid_deform"]},
      "persistent_semantic_objects":[{"object_id":"grid","semantic_role":"coordinate grid",
                      "identity_invariant":"same grid cell identities","claim_ids":["H1"]}],
      "verified_transformations":[{
        "operation":"grid_deform","input_object_ids":["grid"],"output_object_ids":["grid"],
        "claim_ids":["H1"],"host_evidence_sha256":"a"*64,
        "precondition":"host truth start","postcondition":"host truth end",
        "invariants":["point continuity"],"renderer_capability_id":"host_verified_grid_deform"}],
      "narration_anchors":[{"beat_id":"beat_1","claim_ids":["H1"],"referenced_object_ids":["grid"],
         "referenced_transform_indexes":[0],"relative_order":0,"time_source":"ORDER_ONLY"}],
      "expected_observable_explanation":[{"witness_id":"w1","transformation_index":0,
          "before_state":"grid original","after_state":"grid mapped",
          "witness_region":"center","witness_type":"NOT_YET_RENDERABLE"}],
      "explanatory_closure":{"return_to_probe":"Same identity under operation",
                             "known_limitations":["test fixture not a render"]},
      "unsupported_capability_outcome":{"state":"UNSUPPORTED_CAPABILITY",
          "reason_codes":["CAPABILITY_NOT_IMPLEMENTED"],"may_publish":False,
          "allowed_fallback":"DISCLOSE_LIMITATION_ONLY"}
    }


def test_v356_research_coverage_and_honesty():
    result=check()
    assert result["read_lessons"]==18
    assert result["matched_source_code_samples"]==3
    assert result["model_api_requests"]==0 and result["v2_core_edits"]==0
    assert result["full_lesson_videos_end_to_end"]=="NOT_VIEWED"


def test_contract_strictly_rejects_extra_execution_and_bad_hash():
    s=load(ARCH)["schema"]
    d=valid_research_contract()
    assert list(Draft202012Validator(s).iter_errors(d))==[]
    d["arbitrary_python"]="import os"
    assert list(Draft202012Validator(s).iter_errors(d))
    del d["arbitrary_python"]
    d["scope"]["host_ledger_sha256"]="not_a_hash"
    assert list(Draft202012Validator(s).iter_errors(d))


def test_missing_host_references_does_not_become_semantic_pass():
    arch=load(ARCH)
    assert any("Claim IDs are exact subset" in x for x in arch["host_owned_invariants"])
    assert "UNINTEGRATED" in arch["schema"]["status"]
    assert any("unsupported" in x.lower() for x in arch["host_owned_invariants"])
    assert not any("production" in x["role"] for x in arch["roles"])


def test_negative_controls_are_predeclared_and_outputs_unrated():
    evaluation=load(PROTOCOL)
    assert len(evaluation["measurement"]["negative_controls"])>=8
    assert evaluation["human_evaluation_results"] is None
    assert evaluation["inference"]["retry_budget"]==0
    assert validate_frozen_ablation_arms(evaluation["variants"]) == {
        "A_B_same_renderer": True, "B_C_same_prompt": True,
        "A_B_prompt_contrast": True, "B_C_renderer_contrast": True,
    }


def test_no_fabricated_timecodes_or_code_transfer():
    study=load(MATRIX)
    for r in study["rows"]:
      assert r["evidence_video"]["timestamp"]=="UNKNOWN"
      assert r["evidence_video"]["per_frame_alignment"]=="UNKNOWN"
      assert r["evidence_source"]["status"] in (
          "MATCHED_SOURCE_FILE_INSPECTED_NOT_RUN","LESSON_SPECIFIC_SOURCE_UNVERIFIED")
    assert "no screenshot/code reproduction" in study["licensing"]["read_source"]


# V3-69: frozen protocol must be byte-for-byte original, not rewritten to
# silence a failing verifier. This is a raw Git blob digest, not a timestamp.
def test_v369_original_v356_protocol_immutable_git_blob():
    from hashlib import sha1
    raw=(ROOT / PROTOCOL).read_bytes()
    git_blob=b"blob " + str(len(raw)).encode("ascii") + b"\\0" + raw
    assert sha1(git_blob).hexdigest() == "7206371d69ec5ca3670417314314a62e16b1b31c"


@pytest.mark.parametrize("arm,field,replacement", [
    (0, "id", "B"),
    (1, "id", "A"),
    (2, "id", "B"),
    (0, "renderer", "different V2 renderer"),
    (1, "renderer", "new V3 renderer"),
    (1, "renderer", "same renderer as A"),
    (2, "renderer", "SAME frozen V2 Core as A"),
    (0, "prompt", "new sidecar prompt"),
    (1, "prompt", "unmodified HEAD 42dd591 V2 pipeline"),
    (2, "prompt", "prompt close to B"),
    (2, "prompt", "unmodified HEAD 42dd591 V2 pipeline"),
])
def test_v369_mutated_arm_is_rejected(arm, field, replacement):
    variants=copy.deepcopy(load(PROTOCOL)["variants"])
    variants[arm][field]=replacement
    with pytest.raises(AssertionError, match=r"V356_FROZEN_ARM_"):
        validate_frozen_ablation_arms(variants)


def test_v369_swapped_arms_or_missing_arm_rejected():
    variants=copy.deepcopy(load(PROTOCOL)["variants"])
    with pytest.raises(AssertionError, match=r"V356_FROZEN_ARM_"):
        validate_frozen_ablation_arms([variants[1], variants[0], variants[2]])
    with pytest.raises(AssertionError, match=r"V356_AB_C_MISSING"):
        validate_frozen_ablation_arms(variants[:2])
