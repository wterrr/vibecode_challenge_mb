"""V3-39 compatibility-contract tests: all provider senders are mock, 0 live POST."""
from __future__ import annotations
import json
from pathlib import Path
from urllib.error import HTTPError
import pytest

from learnflow_v3.compatible_creative_trial import (
    frozen_protocol, exact_public_capability, one_trial, Blocked
)
from learnflow_v3.structured_scene_authoring import one_shot_structured

ROOT = Path(__file__).resolve().parents[2]


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
      "account_eligibility_certified":False
    }


def test_prereg_is_separate_and_one_wire_change_only():
    p=frozen_protocol(ROOT)
    assert p["checkpoint"] == "V3-39"
    assert p["frozen_intervention"]["remove_only"] == ["temperature"]
    assert p["requests"]["maximum_new_model_http_posts"] == 1
    assert p["requests"]["retry"] == 0
    assert p["production"] == "BLOCKED"


@pytest.mark.parametrize("field,value", [
 ("schema_and_max_tokens_count",0),
 ("v337_all_advertised_generation_params_count",4),
 ("metadata_cannot_certify_json_schema_strict",False),
 ("model_id_matched",False),
 ("inference_requests",1),
 ("account_eligibility_certified",True),
 ("http_status","HTTP_404"),
])
def test_catalog_requires_no_temp_and_advertised_compatible_candidates(field,value):
    p={**public_ok(),field:value}
    with pytest.raises(Blocked,match="V339_PUBLIC_CAPABILITY_UNVERIFIED_NO_PAID_POST"):
        exact_public_capability(probe=lambda:p)


def test_no_post_when_metadata_unverified(tmp_path):
    calls=[]
    with pytest.raises(Blocked,match="V339_PUBLIC_CAPABILITY_UNVERIFIED_NO_PAID_POST"):
        one_trial(ROOT,tmp_path,key="fake-used-only-as-fixture",
                  public_probe=lambda:{**public_ok(),"schema_and_max_tokens_count":0},
                  runner=lambda *a,**kw:calls.append("POST"))
    assert calls==[]


def test_default_legacy_wire_unchanged_but_v339_omits_only_temperature(tmp_path):
    wires=[]
    def sender(request,timeout):
        assert request.get_method()=="POST"  # fake sender: never reaches network
        body=json.loads(request.data)
        wires.append(body)
        raise HTTPError(request.full_url,404,"MOCK_HTTP_404",{},None)
    for omit in (False,True):
        out=tmp_path / str(omit)
        out.mkdir()
        with pytest.raises(Blocked,match="V335_HTTP_404"):
            one_shot_structured("fake-only-unit-test-key",out,sender=sender,
                               omit_temperature=omit)
        attempt=json.loads((out/"v3_35_request_attempt.json").read_text())
        assert attempt["temperature_parameter_sent"] is (not omit)
        fail=json.loads((out/"v3_35_structured_failure.json").read_text())
        assert fail["retry_count"]==0 and fail["provider_fallback"] is False
    assert len(wires)==2
    old,new=wires
    assert old["temperature"]==.65
    assert "temperature" not in new
    assert {**old, "temperature":None} == {**new, "temperature":None}
    assert new["max_tokens"]==6500
    assert new["provider"]=={"allow_fallbacks":False,"require_parameters":True}
    assert new["response_format"]["json_schema"]["strict"] is True
    assert len(new["messages"])==2


def test_mock_contract_returns_technical_not_pedagogy_pass(tmp_path):
    calls=[]
    def runner(root,out,*,mode,key):
        calls.append((mode,key))
        return {"model_plan_origin":"REAL_GPT6_LUNA_STRICT_JSON_SCHEMA_ONE_REQUEST",
                "provider_requests":1,"topic_id":"lfb-018-math",
                "provider_receipt":{
                    "model":"openai/gpt-6-luna",
                    "temperature_parameter_sent":False,
                    "actual_provider_requests":1,
                    "provider_require_parameters":True,"no_retry":True,
                    "no_fallback":True,"model_response_sha256":"a"*64}}
    result=one_trial(ROOT,tmp_path,key="fake-key",
                     public_probe=public_ok,runner=runner,
                     evidence_gate=lambda _:{"status":"MODEL_ORIGIN_TECHNICAL_EVIDENCE_PASS_NOT_EDUCATIONAL_PASS",
                                             "video_sha256":"b"*64})
    assert calls==[("live-structured-no-temperature","fake-key")]
    assert result["temperature_parameter_sent"] is False
    assert result["public_candidate_count_without_temperature"]==4
    assert result["human_educational_quality"]=="NOT_ASSESSED"
    assert result["production"]=="BLOCKED"
    assert json.loads((tmp_path/"v3_39_compatible_luna_receipt.json").read_text())==result


def test_reject_model_origin_fixture(tmp_path):
    def runner(root,out,*,mode,key):
        return {"model_plan_origin":"SYNTHETIC_HOST_FIXTURE_NOT_REAL_MODEL",
                "provider_requests":0,"provider_receipt":None}
    with pytest.raises(Blocked,match="V339_NOT_VERIFIED_ONE_MODEL_POST_OR_CHANGED_WIRE"):
        one_trial(ROOT,tmp_path,key="fake",
                  public_probe=public_ok,runner=runner,
                  evidence_gate=lambda _:{"status":"MODEL_ORIGIN_TECHNICAL_EVIDENCE_PASS_NOT_EDUCATIONAL_PASS"})


def test_reject_sender_even_if_it_sends_temperature(tmp_path):
    def runner(root,out,*,mode,key):
        return {"model_plan_origin":"REAL_GPT6_LUNA_STRICT_JSON_SCHEMA_ONE_REQUEST",
                "provider_requests":1,"provider_receipt":{
                   "temperature_parameter_sent":True, "actual_provider_requests":1,
                   "provider_require_parameters":True,"no_retry":True,"no_fallback":True}}
    with pytest.raises(Blocked,match="V339_NOT_VERIFIED_ONE_MODEL_POST_OR_CHANGED_WIRE"):
        one_trial(ROOT,tmp_path,key="fake",public_probe=public_ok,runner=runner)


def test_outdir_never_overwritten(tmp_path):
    (tmp_path/"existing_response.json").write_text("{}")
    with pytest.raises(Blocked,match="V339_OUTPUT_NOT_EMPTY"):
        one_trial(ROOT,tmp_path,key="fake",public_probe=public_ok)
