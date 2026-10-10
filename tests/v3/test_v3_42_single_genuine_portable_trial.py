"""V3-42 real-provider transport is tested ONLY with injected fake senders.

This test module is offline and makes ZERO HTTP POST or authenticated GET.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from urllib.error import HTTPError
import pytest

from learnflow_v3.compatible_scene_protocol import (
    candidate_request_body, offline_synthetic_wire_fixture)
from learnflow_v3.creative_manim_ablation import Blocked,CreativeScene
from learnflow_v3.genuine_portable_response import one_shot_portable
from learnflow_v3.single_genuine_portable_trial import frozen_protocol,one_trial
from learnflow_v3.structured_scene_authoring import strict_wire_schema

ROOT=Path(__file__).resolve().parents[2]
FAKE_KEY="FAKE_FOR_UNIT_TEST_ABC_123_NOT_REAL"


def reply(data:dict,*,finish="stop")->bytes:
    return json.dumps({"model":"openai/gpt-6-luna","id":"mock-only-id",
          "choices":[{"finish_reason":finish,
                      "message":{"content":json.dumps(data)}}],
          "usage":{"prompt_tokens":44,"completion_tokens":212}}).encode("utf-8")


class OneSender:
    def __init__(self, raw: bytes|None=None, status_code: int|None=None):
        self.raw=raw
        self.status_code=status_code
        self.calls=[]
    def __call__(self, request, timeout):
        self.calls.append((request,timeout))
        if self.status_code:
            raise HTTPError(request.full_url,self.status_code,"MOCK",{},None)
        class C:
            def __init__(self, payload):
                self.payload=payload
            def __enter__(self):
                return BytesIO(self.payload)
            def __exit__(self,*exc):
                return False
        return C(self.raw)


def test_separately_preregistered_trial_is_frozen():
    manifest=frozen_protocol(ROOT)
    assert manifest["checkpoint"]=="V3-42"
    assert manifest["parent_pr"]==75
    assert manifest["parent_ci_run"]==38025538022
    assert manifest["one_shot_budget"]["maximum_new_model_http_posts"]==1
    assert manifest["one_shot_budget"]["retries"]==0
    assert manifest["no_inference_until_tagged_activation"] is True


def test_exact_frozen_wire_and_one_fake_post_returns_host_valid_scene(tmp_path):
    fixture=offline_synthetic_wire_fixture()
    raw=reply(fixture)
    sender=OneSender(raw)
    result,receipt=one_shot_portable(FAKE_KEY,tmp_path,sender=sender)
    assert len(sender.calls)==1
    req,timeout=sender.calls[0]
    wire=json.loads(req.data)
    assert timeout==125 and req.get_method()=="POST"
    assert wire==candidate_request_body()
    assert "temperature" not in wire and wire["max_tokens"]==6500
    assert wire["provider"]=={"allow_fallbacks":False,"require_parameters":True}
    assert result["model_author"]=="openai/gpt-6-luna"
    CreativeScene.model_validate(result)
    assert receipt["model_response_sha256"]==sha256(json.dumps(fixture).encode()).hexdigest()
    assert receipt["protocol"]=="V3-42_PREREGISTERED_V3-41_PORTABLE"
    assert receipt["actual_provider_requests"]==1
    assert receipt["no_retry"] is True and receipt["no_fallback"] is True
    assert not (tmp_path/"scene_plan.json").exists()
    assert not (tmp_path/"creative_manim_with_audio.mp4").exists()
    assert "FAKE_FOR_UNIT_TEST" not in json.dumps([
        json.loads(p.read_text()) for p in tmp_path.iterdir() if p.suffix==".json"])
    # Synthetic fake responder CANNOT establish actual model provenance.
    assert not (tmp_path/"v3_42_single_genuine_outcome.json").exists()


@pytest.mark.parametrize("badcase",[
    "height_one","height_two","empty_primary","missing_first_beat",
    "invalid_fact","duplicate_id","missing_all_facts"])
def test_invalid_fake_model_responses_fail_closed_without_repair(tmp_path,badcase):
    raw=offline_synthetic_wire_fixture()
    if badcase=="height_one":raw["objects"][0]["height"]=3.0
    if badcase=="height_two":raw["objects"][1]["height"]=99.0
    if badcase=="empty_primary":raw["beats"]["beat_1"]["claim_primary"]=""
    if badcase=="missing_first_beat":raw["beats"].pop("beat_1")
    if badcase=="invalid_fact":raw["objects"][0]["text"]="One half equals 3/7"
    if badcase=="duplicate_id":raw["objects"][1]["id"]=raw["objects"][0]["id"]
    if badcase=="missing_all_facts":
        for beat in raw["beats"].values():
            beat["claim_primary"]="F1"
            beat["claim_secondary"]=""
            beat["claim_tertiary"]=""
    sender=OneSender(reply(raw))
    with pytest.raises(Blocked,match="V342_PROVIDER_"):
        one_shot_portable(FAKE_KEY,tmp_path,sender=sender)
    assert len(sender.calls)==1
    fail=json.loads((tmp_path/"v3_42_portable_model_failure.json").read_text())
    assert fail["model_request_attempts"]==1
    assert fail["model_response_sha256"] is not None
    assert fail["raw_model_text_saved"] is False
    assert fail["retry_count"]==0 and fail["provider_fallback"] is False


def test_mock_http_404_does_not_retry_and_does_not_claim_model_content(tmp_path):
    sender=OneSender(status_code=404)
    with pytest.raises(Blocked,match="V342_HTTP_404"):
        one_shot_portable(FAKE_KEY,tmp_path,sender=sender)
    assert len(sender.calls)==1
    fail=json.loads((tmp_path/"v3_42_portable_model_failure.json").read_text())
    assert fail["model_response_sha256"] is None
    assert fail["model_request_attempts"]==1


def test_fake_truncated_response_does_not_retry(tmp_path):
    sender=OneSender(reply(offline_synthetic_wire_fixture(),finish="length"))
    with pytest.raises(Blocked,match="V342_PROVIDER_TRUNCATED"):
        one_shot_portable(FAKE_KEY,tmp_path,sender=sender)
    assert len(sender.calls)==1


def test_preflight_missing_key_has_no_post(tmp_path):
    attempts=[]
    def sender(*args,**kw):
        attempts.append(1)
    with pytest.raises(Blocked,match="V342_API_KEY_NOT_CONFIGURED"):
        one_shot_portable("",tmp_path,sender=sender)
    assert attempts==[]
    proof=json.loads((tmp_path/"v3_42_portable_model_failure.json").read_text())
    assert proof["model_request_attempts"]==0


def public_ok():
    return {
        "model":"openai/gpt-6-luna",
        "http_status":"HTTP_200",
        "model_id_matched":True,
        "schema_advertised_count":7,
        "schema_and_max_tokens_count":4,
        "v337_all_advertised_generation_params_count":0,
        "metadata_cannot_certify_json_schema_strict":True,
        "inference_requests":0,
        "account_eligibility_certified":False,
    }


def test_public_preflight_fail_blocks_runner_before_any_inference(tmp_path):
    calls=[]
    bad={**public_ok(),"schema_and_max_tokens_count":0}
    with pytest.raises(Blocked,match="V339_PUBLIC_CAPABILITY_UNVERIFIED_NO_PAID_POST"):
        one_trial(ROOT,tmp_path,key=FAKE_KEY,public_probe=lambda:bad,
                  runner=lambda *args,**kwargs:calls.append("SENT"))
    assert calls==[]


def test_candidate_synthetic_false_pass_rejected(tmp_path):
    calls=[]
    def fake_runner(root,out,*,mode,key):
        calls.append(mode)
        return {"model_plan_origin":"SYNTHETIC_V341_COMPAT_WIRE_FIXTURE_NOT_REAL_MODEL",
                "provider_requests":0,"provider_receipt":None}
    with pytest.raises(Blocked,match="V342_WRONG_PROVIDER_OR_SYNTHETIC_PROVENANCE"):
        one_trial(ROOT,tmp_path,key=FAKE_KEY,public_probe=public_ok,
                  runner=fake_runner,evidence_gate=lambda _:{"status":"MODEL_ORIGIN_TECHNICAL_EVIDENCE_PASS_NOT_EDUCATIONAL_PASS"})
    assert calls==["live-v342-portable"]


def test_mock_receipt_passing_guard_still_is_not_real_provider_proof(tmp_path):
    observed=[]
    def fake_runner(root,out,*,mode,key):
        observed.append(mode)
        return {
            "topic_id":"lfb-018-math",
            "model_plan_origin":"REAL_GPT6_LUNA_STRICT_JSON_SCHEMA_ONE_REQUEST",
            "manim_source_origin":"HOST_COMPILED_FROM_MODEL_PRIMITIVE_DATA",
            "provider_requests":1,"provider_receipt":{
                "protocol":"V3-42_PREREGISTERED_V3-41_PORTABLE",
                "stage":"REAL_MODEL_SCHEMA_CONSTRAINED_SCENE",
                "actual_provider_requests":1,
                "temperature_parameter_sent":False,
                "provider_require_parameters":True,
                "no_retry":True,"no_fallback":True,
                "model_response_sha256":"a"*64}}
    out=one_trial(ROOT,tmp_path,key=FAKE_KEY,public_probe=public_ok,
             runner=fake_runner,
             evidence_gate=lambda _:{"status":"MODEL_ORIGIN_TECHNICAL_EVIDENCE_PASS_NOT_EDUCATIONAL_PASS",
                                      "video_sha256":"b"*64})
    assert observed==["live-v342-portable"]
    assert out["human" if "human" in out else "blinded_educational_quality"]=="NOT_ASSESSED"
    assert out["production"]=="BLOCKED"
    # TEST fixtures are not evidence; this tests only structural guard wiring.


def test_v339_historical_schema_is_untouched():
    schema=strict_wire_schema()
    assert "maximum" not in schema["properties"]["objects"]["items"]["properties"]["height"]
    assert "claim_ids" in schema["properties"]["beats"]["items"]["properties"]


def test_ci_paid_stage_requires_exact_marker_first_attempt_and_main_never_merge():
    workflow=(ROOT/".github/workflows/v3-42-single-genuine-portable.yml").read_text()
    assert "github.run_attempt == 1" in workflow
    assert "github.event_name == 'push'" in workflow
    assert "refs/heads/chatgpt/v3-42-single-genuine-portable-lesson" in workflow
    assert "[v3-42-single-genuine-portable-post]" in workflow
    assert "needs: exact-head-offline-schema-and-host-media" in workflow
    assert "secrets.OPENROUTER_API_KEY" in workflow
    assert "one_shot_portable" not in workflow  # Only CLI via locked registered main()
    assert "pull_request" in workflow
