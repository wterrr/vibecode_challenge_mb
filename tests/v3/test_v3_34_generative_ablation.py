"""V3-34 ablation: exact frozen topic, real graph-data freedom and safe emit."""
from __future__ import annotations
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from learnflow_v3.creative_manim_ablation import (
  Blocked,CreativeScene,fixture_plan,manim_code,ablation_baselines,
  checked_manifest,FACTS,VERSION)
from learnflow_v3.creative_manim_runner import call_exact_model,prompt
ROOT=Path(__file__).resolve().parents[2]


def test_frozen_topic_matches_v333_not_hidden_curated_OLD_demo():
    r=checked_manifest(ROOT)
    assert r["preimplementation_locked"] is True
    assert r["topic_id"]=="lfb-018-math"
    assert r["topic_query_sha256"]=="376a06049a51990ddb7fe7a340ef42222b8d89ed601fa8a22dfe971524cf113d"
    assert r["provider_requests_cap"]==1 and r["provider_fallback"] is False
    assert "add_two" not in r["topic"] and "binary search" not in r["topic"]
    assert set(FACTS)=={"F1","F2","F3"}


def test_old_A_and_B_cannot_fake_success():
    p=fixture_plan()
    result=ablation_baselines(ROOT,p)
    assert result["A"]["rendered"] is False
    assert result["B"]["rendered"] is False
    assert result["C"]["rendered"] is False
    assert "ABSTAIN" in result["A"]["status"]
    assert "ABSTAIN" in result["B"]["status"]
    assert result["pilot_is_not_symmetric_three_finished_videos"] is True


def test_fixture_is_transparently_not_model_and_emits_real_manim():
    p=fixture_plan()
    assert p.model_author is None
    code=manim_code(p,[5.1,5.1,5.1,5.1])
    assert "class GeneratedLesson(Scene):" in code
    assert code.count("# BEAT")==4
    assert "FadeIn" in code and "Indicate" in code
    assert "from manim import *" in code
    assert "self.camera.background_color = '#000000'" in code
    assert "from os" not in code and "exec(" not in code


@pytest.mark.parametrize("mutation,expected",[
    ("foreign_number","V334_UNVERIFIED_SPOKEN_NUMERIC_FACT"),
    ("foreign_fraction","V334_UNVERIFIED_VISIBLE_NUMERIC_FACT"),
    ("unknown_id","V334_UNKNOWN_OBJECT"),
    ("unshown_move","V334_OBJECT_NOT_YET_VISIBLE"),
    ("duplicate_show","V334_DUPLICATED_SHOW"),
    ("extra_code","extra_forbidden"),
    ("missing_fact","V334_INCOMPLETE_TOPIC_FACT_COVERAGE"),
])
def test_model_creativity_fails_closed_on_factual_or_motion_mutations(mutation,expected):
    obj=fixture_plan().model_dump()
    if mutation=="foreign_number":
        obj["beats"][2]["narration"]+=" This somehow equals 9."
    if mutation=="foreign_fraction":
        obj["objects"][0]["text"]="New fact 3/8"
    if mutation=="unknown_id":
        obj["beats"][1]["actions"][0]["target"]="hacker"
    if mutation=="unshown_move":
        obj["beats"][0]["actions"][0]={"action":"move","target":"l1","x":1,"y":1}
    if mutation=="duplicate_show":
        obj["beats"][0]["actions"][1]["target"]="title"
    if mutation=="extra_code":
        obj["objects"][1]["python_source"]="__import__('os')"
    if mutation=="missing_fact":
        obj["beats"][2]["claim_ids"]=["F1"]
        obj["beats"][3]["claim_ids"]=["F1"]
    with pytest.raises(ValidationError,match=expected):
        CreativeScene.model_validate(obj)


def test_no_generated_code_or_secret_can_ride_graphic_text():
    obj=fixture_plan().model_dump()
    obj["objects"][0]["text"]="__import__('os').system('id')"
    p=CreativeScene.model_validate(obj)
    with pytest.raises(Blocked,match="V334_EMITTER_SAFETY_CONTRACT"):
        manim_code(p,[4,4,4,4])


def test_no_long_or_inexact_measured_audio_budget():
    p=fixture_plan()
    for times in ([1,5,5,5],[5]*3,[5,5,99,5]):
        with pytest.raises(Blocked):
            manim_code(p,times)


def test_one_request_provider_json_can_be_mocked_without_live_network():
    obj=fixture_plan().model_dump()
    obj["model_author"]="openai/gpt-6-luna"
    reply=json.dumps(obj)
    response={"id":"provider-response-123",
              "choices":[{"finish_reason":"stop","message":{"content":reply}}],
              "usage":{"prompt_tokens":80,"completion_tokens":190}}
    class Sender:
        def __call__(self,request,timeout):
            assert timeout<=125
            data=json.loads(request.data)
            assert data["model"]=="openai/gpt-6-luna"
            assert data["provider"]["allow_fallbacks"] is False
            self.request_count+=1
            class Context:
                def __enter__(self):return BytesIO(json.dumps(response).encode())
                def __exit__(self,*args):pass
            return Context()
        request_count=0
    mock=Sender()
    data,proof=call_exact_model("SOME_FAKE_SECRET_WITH_LENGTH",sender=mock)
    assert mock.request_count==1
    assert CreativeScene.model_validate(data).model_author=="openai/gpt-6-luna"
    assert proof["actual_provider_requests"]==1 and proof["no_retry"]


def test_schema_does_not_support_arbitrary_source_execution():
    x=fixture_plan().model_dump()
    x["objects"][0]["kind"]="python"
    with pytest.raises(ValidationError):CreativeScene.model_validate(x)
    x=fixture_plan().model_dump()
    x["beats"][1]["actions"][0]["action"]="shell"
    with pytest.raises(ValidationError):CreativeScene.model_validate(x)
