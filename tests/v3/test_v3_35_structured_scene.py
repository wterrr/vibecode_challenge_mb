"""V3-35 pre-registered schema, zero retry and one-shot fixture acceptance."""
from __future__ import annotations
from io import BytesIO
import json
from pathlib import Path
from copy import deepcopy
import pytest

from learnflow_v3.structured_scene_authoring import (
  strict_wire_schema,verify_schema,preflight,normalize_wire,
  one_shot_structured,Blocked
)
from learnflow_v3.creative_manim_ablation import CreativeScene,fixture_plan
ROOT=Path(__file__).resolve().parents[2]


def wire_from_fixture():
    d=fixture_plan().model_dump(mode="json",exclude={"model_author"})
    for beat in d["beats"]:
        for action in beat["actions"]:
            if action.get("target") is None:action["target"]=""
            if action.get("x") is None:action["x"]=0
            if action.get("y") is None:action["y"]=0
    return d


def test_preregistered_new_attempt_is_fixed_before_code():
    p=preflight(ROOT)
    assert p["topic_id"]=="lfb-018-math"
    assert p["preregistered_before_implementation"] is True
    assert p["max_model_http_requests"]==1
    assert p["provider_retries"]==0
    assert p["provider_fallback"] is False


def test_schema_all_required_and_no_unmapped_fields():
    schema=strict_wire_schema()
    assert schema["additionalProperties"] is False
    assert sorted(schema["required"])==sorted(schema["properties"])
    graphic=schema["properties"]["objects"]["items"]
    assert len(graphic["required"])==9
    beat=schema["properties"]["beats"]["items"]
    action=beat["properties"]["actions"]["items"]
    assert set(action["required"])=={"action","target","x","y"}
    verify_schema(schema)


def test_wire_normalization_preserves_composition_and_motion():
    raw=wire_from_fixture()
    normalized=normalize_wire(raw)
    p=CreativeScene.model_validate({**normalized,"model_author":"openai/gpt-6-luna"})
    assert len(p.objects)==len(raw["objects"]) and len(p.beats)==4
    assert p.beats[0].actions[0].action=="show"
    assert p.beats[0].actions[0].x is None
    assert p.model_author=="openai/gpt-6-luna"


@pytest.mark.parametrize("change,error",[
 ("wait_extra_target","V335_WAIT_TARGET_NOT_EMPTY"),
 ("wait_extra_coordinate","V335_WAIT_UNUSED_COORD_NOT_ZERO"),
 ("nonmove_coordinate","V335_NONMOVE_UNUSED_COORD_NOT_ZERO"),
 ("unknown_action","V335_UNKNOWN_ACTION"),
 ("unexpected_object_field","V335_RESPONSE_FIELD_SET_DRIFT")
])
def test_invalid_transport_values_reject_without_silent_knowledge_repairs(change,error):
    obj=wire_from_fixture()
    if change=="wait_extra_target":
        obj["beats"][0]["actions"].append({"action":"wait","target":"l1","x":0,"y":0})
    elif change=="wait_extra_coordinate":
        obj["beats"][0]["actions"].append({"action":"wait","target":"","x":1,"y":0})
    elif change=="nonmove_coordinate":
        obj["beats"][0]["actions"][0]["x"]=2
    elif change=="unknown_action":
        obj["beats"][0]["actions"][0]["action"]="shell"
    else:obj["evil_python"]="eval('1')"
    with pytest.raises(Blocked,match=error):normalize_wire(obj)


def test_strict_one_request_and_provider_require_parameters_plus_structured_plan(tmp_path):
    fixture=wire_from_fixture()
    response={"id":"one-off-provider-id","choices":[{"finish_reason":"stop",
         "message":{"content":json.dumps(fixture)}}],
         "usage":{"prompt_tokens":321,"completion_tokens":654}}
    class Sender:
        attempts=0
        def __call__(self,request,timeout):
            self.attempts+=1
            d=json.loads(request.data)
            assert d["provider"]=={"allow_fallbacks":False,"require_parameters":True}
            assert d["response_format"]["type"]=="json_schema"
            assert d["response_format"]["json_schema"]["strict"] is True
            assert d["model"]=="openai/gpt-6-luna"
            assert timeout<=125
            class C:
                def __enter__(self):return BytesIO(json.dumps(response).encode())
                def __exit__(self,*args):pass
            return C()
    sender=Sender()
    raw,usage=one_shot_structured("FAKE_KEY_FOR_TEST_ONLY",tmp_path,sender=sender)
    assert sender.attempts==1 and usage["actual_provider_requests"]==1
    assert raw["model_author"]=="openai/gpt-6-luna"
    assert (tmp_path/"v3_35_request_attempt.json").is_file()
    assert (tmp_path/"v3_35_structured_provider_receipt.json").is_file()


def test_injected_model_drifts_are_saved_by_paths_not_model_prose(tmp_path):
    fake=wire_from_fixture()
    fake["objects"][0]["text"]="One half equals 3/7"  # Uncertified arithmetic
    fake["beats"][1]["narration"]+=" therefore the number 9 is correct."
    response={"choices":[{"finish_reason":"stop","message":{"content":json.dumps(fake)}}],"usage":{}}
    class Sender:
        attempts=0
        def __call__(self,request,timeout):
            self.attempts+=1
            class C:
                def __enter__(self):return BytesIO(json.dumps(response).encode())
                def __exit__(self,*args):pass
            return C()
    client=Sender()
    with pytest.raises(Blocked,match="V335_SCENE_REJECTED"):
        one_shot_structured("FAKE_KEY_FOR_TEST_ONLY",tmp_path,sender=client)
    assert client.attempts==1
    proof=json.loads((tmp_path/"v3_35_structured_failure.json").read_text())
    assert proof["model_request_attempts"]==1
    assert proof["sanitized_error_code"]=="V335_PYDANTIC_SEMANTIC_REJECT"
    assert proof["raw_model_text_in_artifact"] is False
    assert len(proof["validation_error_shapes"])>=2
    assert "3/7" not in json.dumps(proof)
    assert "number 9" not in json.dumps(proof)


def test_finite_graphic_actions_still_reject_untrusted_generated_python():
    fake=wire_from_fixture()
    fake["objects"][0]["python"]="__import__('os')"
    # Wire normalization never alters graphic semantics; the existing
    # strict Pydantic model rejects extra object fields before code emission.
    from pydantic import ValidationError
    normalized=normalize_wire(fake)
    with pytest.raises(ValidationError):
        CreativeScene.model_validate({**normalized,"model_author":"openai/gpt-6-luna"})
