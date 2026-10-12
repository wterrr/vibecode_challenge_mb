"""V3-50 model/attention: only injected mock envelopes, never real POST."""
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest
from jsonschema import Draft202012Validator
from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.creative_manim_runner import MODEL

from learnflow_v3.model_authored_attention import (
  ROOT,REG,prereg,portable_schema,request_body,verify_storyboard,
  synthetic_fixture,exact_example,compile_manim,sha)
from scripts.run_v3_50_attention_one_query import model_once


def fake_envelope(story):
    return json.dumps({"model":MODEL,"id":"mock-provider-not-genuine",
      "choices":[{"finish_reason":"stop","message":{"content":json.dumps(story)}}],
      "usage":{"prompt_tokens":200,"completion_tokens":400}}).encode()

class SpySender:
    def __init__(self,body=None,code=0):
        self.body=body;self.code=code;self.calls=[]
    def __call__(self,request,timeout):
        self.calls.append((request,timeout))
        if self.code:
            raise HTTPError(request.full_url,self.code,"MOCK_ERROR",{},None)
        class Reply:
            def __enter__(self_inner):return BytesIO(self.body)
            def __exit__(self_inner,*args):return False
        return Reply()


def test_one_frozen_attention_query_and_one_post_contract():
    r=prereg()
    assert r["parent_pr"]==83 and r["parent_sha"]=="bdc4d6a21fb1e58a50f96b4722f81585e511aee2"
    assert r["one_shot_budget"]["max_new_http_posts"]==1
    assert "Transformer" in r["user_query"] or "Transformer" in r["source"]["title"]
    schema=portable_schema()
    Draft202012Validator.check_schema(schema)
    body=request_body()
    assert body["model"]==MODEL and body["max_tokens"]==2800
    assert "temperature" not in body and body["provider"]=={
      "allow_fallbacks":False,"require_parameters":True}
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"]==schema
    assert sha(body)==sha(request_body())


def test_host_exact_attention_truth_and_rounded_probability():
    v=exact_example()
    assert v["dk"]==2 and v["q"]==[1,0]
    assert abs(v["scores"][0]-.7071067811865475)<1e-12
    assert v["scores"][1]==0
    assert [round(x,3) for x in v["weights"]]==[.670,.330]
    assert [round(x,3) for x in v["context"]]==[.670,.330]
    assert sum(v["weights"])==pytest.approx(1.)


def test_fixture_compiles_only_finite_host_owned_code():
    story=verify_storyboard(synthetic_fixture())
    code=compile_manim(story,[9.3,10.2,9.1,9.2])
    compile(code,"<V350_HOST_ONLY>","exec")
    assert code.count("V350_BEAT_")==4
    assert "Q K^T / sqrt(d_k)" in code
    assert "GrowFromEdge" in code and "ReplacementTransform(VGroup(weight1,weight2),output)" in code
    assert "FadeOut(dot1),FadeOut(dot2)" in code
    assert "Arrow([-3.12,.78,0],[2.17,.78,0]" in code
    assert "self.play" in code
    assert "__import__" not in code and "subprocess" not in code
    assert "from manim import *" in code


@pytest.mark.parametrize("case",[
 "wrong_claim","missing_beat","wrong_field","bad_focus","bad_numbers",
 "bad_scientific_stage","too_short","untrusted_python","invented_formula"
])
def test_invalid_model_scene_fails_closed(case):
    x=deepcopy(synthetic_fixture())
    b=x["beats"]["beat_3"]
    if case=="wrong_claim":b["claim_id"]="A2"
    if case=="missing_beat":del x["beats"]["beat_4"]
    if case=="wrong_field":b["python"]="import os"
    if case=="bad_focus":b["focus"]="unverified_transformer_key"
    if case=="bad_numbers":b["narration"]+=" Every weight is 99."
    if case=="bad_scientific_stage":b["narration"]="We can use a fixed score for every token instead of normalizing anything at all. This would make the whole graph easier and more interesting to understand."
    if case=="too_short":b["narration"]="softmax weights"
    if case=="untrusted_python":x["injected_code"]="os.system('whoami')"
    if case=="invented_formula":b["narration"]+=" The key dimension is 1024."
    with pytest.raises((Blocked,ValueError)):
        verify_storyboard(x)


def test_mock_one_post_response_is_not_real_inference(tmp_path):
    sender=SpySender(fake_envelope(synthetic_fixture()))
    story,receipt=model_once(tmp_path,"FAKE_STABLE_TEST_KEY_ONLY",sender=sender)
    assert len(sender.calls)==1 and sender.calls[0][1]==125
    req=sender.calls[0][0]
    assert req.get_method()=="POST"
    assert json.loads(req.data)==request_body()
    assert story==synthetic_fixture()
    assert receipt["http_post_attempts"]==1
    assert receipt["model_authored_python"] is False
    assert not (tmp_path/"attention_one_query_with_audio.mp4").exists()
    assert receipt["validated_storyboard_sha256"]==sha(synthetic_fixture())


def test_missing_secret_preflight_zero_http_calls(tmp_path):
    send=SpySender(b"")
    with pytest.raises(Blocked,match="V350_API_KEY_MISSING"):
        model_once(tmp_path,"",sender=send)
    assert len(send.calls)==0
    assert json.loads((tmp_path/"v350_failure.json").read_text())["attempted_model_http_posts"]==0


def test_provider_http_error_consumes_one_no_retry(tmp_path):
    send=SpySender(code=404)
    with pytest.raises(Blocked,match="V350_PROVIDER_HTTP_404"):
        model_once(tmp_path,"FAKE_STABLE_TEST_KEY_ONLY",sender=send)
    assert len(send.calls)==1
    failure=json.loads((tmp_path/"v350_failure.json").read_text())
    assert failure["attempted_model_http_posts"]==1
    assert failure["no_retry"] and failure["no_fallback"]


def test_provider_json_valid_envelope_wrong_attention_semantics_rejected(tmp_path):
    story=deepcopy(synthetic_fixture())
    story["beats"]["beat_1"]["narration"]+=" The network has 64 attention heads."
    sender=SpySender(fake_envelope(story))
    with pytest.raises(Blocked,match="V350_SCHEMA_OR_CLAIM_REJECTED"):
        model_once(tmp_path,"FAKE_STABLE_TEST_KEY_ONLY",sender=sender)
    assert len(sender.calls)==1
    assert json.loads((tmp_path/"v350_failure.json").read_text())["attempted_model_http_posts"]==1


def test_separate_one_time_activation_only_after_offline_job():
    workflow=(ROOT/".github/workflows/v3-50-one-query-attention.yml").read_text()
    assert "github.run_attempt == 1" in workflow
    assert "github.event_name == 'push'" in workflow
    assert "[v3-50-single-attention-model-post]" in workflow
    assert "needs: offline-schema-native-attention" in workflow
    assert "secrets.OPENROUTER_API_KEY" in workflow
    assert "chatgpt/v3-50-one-shot-attention-model-trial" in workflow
    assert "pull_request:" in workflow


def test_original_fraction_claims_unchanged():
    from learnflow_v3.semantic_scene_wire import decode_model_facing_scene
    from learnflow_v3.semantic_scene_offline_fixtures import fixture_cases
    for fixture in fixture_cases().values():
        decode_model_facing_scene(fixture)
