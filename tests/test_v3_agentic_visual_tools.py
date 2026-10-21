"""Host-owned visual agent tool calling: mocked paid HTTP, no actual API charge.

Proves the paid model is actually supplied tool definitions; it requests
registered functions, host executes Pydantic/oracle probes, and only verified
receipts enter the final strict JSON planning request. No recursive tool loop.
"""
from __future__ import annotations

import asyncio
import json
from copy import deepcopy

import httpx
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.domain.lesson import LearningRequest, LessonPlan
from app.demo.lesson_plans import DEMO_PHOTOSYNTHESIS_PLAN
from app.planning.visual_tools import (
    MAX_TOOL_CALLS, execute_visual_tool, render_tool_receipts,
    visual_tool_definitions, tool_catalog,
)
from app.providers.llm.base import PlannerProviderError
from app.providers.llm.openrouter_paid import OpenRouterPaidLessonPlanner


def test_host_catalog_lists_actual_six_renderer_families_without_fake_tools():
    from app.rendering.router import RendererRouter
    catalog=tool_catalog()
    names={t["intent"] for t in catalog["scene_tools"]}
    assert names=={x.value for x in RendererRouter()._registry}
    assert len(visual_tool_definitions())==3
    registered={x["function"]["name"] for x in visual_tool_definitions()}
    assert registered=={"describe_visual_tools","probe_array_trace","probe_function_graph"}
    assert MAX_TOOL_CALLS==3
    assert execute_visual_tool("describe_visual_tools","{}")==catalog


@pytest.mark.parametrize("values,target,index",[
    ([1,3,5,7,9,11,13], 7, 3),
    ([1,2,2,2,2,3,4], 2, 1),
    ([1,3,5,7,9,11,13], 8, None),
])
def test_array_probe_executes_host_oracle(values,target,index):
    witness=execute_visual_tool("probe_array_trace",json.dumps({
        "values":values, "target":target,
    }))
    assert witness["verified"] is True
    assert witness["intent"]=="array_trace"
    assert witness["result_index"]==index
    assert witness["steps"][0]["mid"]==len(values)//2
    assert len(witness["trace_sha256"])==64


def test_function_probe_host_math_derivative_and_bounds():
    good={"function":"polynomial","coefficients":[0,0,1],
          "focus_x":1,"motion_kind":"secant_to_tangent"}
    witness=execute_visual_tool("probe_function_graph",json.dumps(good))
    assert witness["verified"] is True
    assert witness["host_value_at_focus"]==1.0
    assert witness["host_slope_at_focus"]==2.0
    for field,value in [("function","__import__"),("focus_x",100),
                        ("coefficients",[0,float("nan")])]:
        bad=dict(good,**{field:value})
        with pytest.raises(ValueError):
            execute_visual_tool("probe_function_graph",json.dumps(bad))


@pytest.mark.parametrize("name,arguments", [
    ("unregistered_exec","{}"),
    ("probe_array_trace",'{"values": [1,2,3,4,5],"target":3,"cmd":"rm -rf /"}'),
    ("probe_array_trace",'{"values": [5,4,3,2,1],"target":3}'),
    ("probe_array_trace",'{"values": [1,2,3,4,5],"target":true}'),
    ("probe_array_trace",'{"values": [1,2,3,4,5],"target": 3'),
    ("describe_visual_tools",'{"python":"print(3)"}'),
    ("probe_function_graph",'{"function":"sine","focus_x":0,"motion_kind":"slope_scan"}'),
])
def test_unknown_untrusted_or_malformed_function_calls_fail_closed(name,arguments):
    with pytest.raises(ValueError):
        execute_visual_tool(name,arguments)


def test_tool_result_serialization_is_bounded_and_no_nan():
    result=[{"tool":"describe_visual_tools",
             "result":execute_visual_tool("describe_visual_tools","{}")}]
    assert "production-visual-tools-v1" in render_tool_receipts(result)
    with pytest.raises(ValueError):
        render_tool_receipts(result*4)
    with pytest.raises(ValueError):
        execute_visual_tool("describe_visual_tools"," " * 4100)


class MockResponse:
    def __init__(self,obj): self.obj=obj
    def raise_for_status(self): pass
    def json(self): return self.obj


class ProviderReplay:
    def __init__(self, responses):
        self.responses=list(responses)
        self.requests=[]
    def install(self,monkeypatch):
        parent=self
        class FakeClient:
            def __init__(self,**kwargs): pass
            async def __aenter__(self): return self
            async def __aexit__(self,*args): pass
            async def post(self,url,headers,json):
                assert url=="https://openrouter.ai/api/v1/chat/completions"
                assert headers["Authorization"].startswith("Bearer ")
                parent.requests.append(json)
                if not parent.responses: raise AssertionError("Unexpected extra paid POST")
                return MockResponse(parent.responses.pop(0))
        monkeypatch.setattr(httpx,"AsyncClient",FakeClient)


def response(tool_calls=None,finish_reason="tool_calls",model="openai/gpt-6-luna",plan=None):
    if plan is not None:
        return {
            "model": model,
            "choices": [{"finish_reason":"stop",
                         "message":{"content":plan.model_dump_json()}}],
        }
    return {
        "model":model,
        "choices":[{"finish_reason":finish_reason,
                    "message":{"tool_calls":tool_calls}}],
    }


def function_call(name, arguments, id="call-1"):
    return {"id":id,"type":"function","function":{
        "name":name,"arguments":json.dumps(arguments),
    }}


def test_agentic_openrouter_executes_tools_then_strict_json(monkeypatch):
    first=response([
        function_call("describe_visual_tools",{}),
        function_call("probe_array_trace",{
            "values":[1,3,5,7,9,11,13],"target":7,
        },id="call-2"),
    ])
    server=ProviderReplay([first,response(plan=DEMO_PHOTOSYNTHESIS_PLAN)])
    server.install(monkeypatch)
    planner=OpenRouterPaidLessonPlanner(
        api_key="test-token-not-paid-please-dont-call",agentic_visual_tools=True,
    )
    plan=asyncio.run(planner.create_plan(LearningRequest(topic="Các khái niệm cơ bản")))
    assert isinstance(plan,LessonPlan)
    assert len(server.requests)==2
    discovery,final=server.requests
    assert discovery["tool_choice"]=="required"
    assert len(discovery["tools"])==3
    assert "response_format" not in discovery
    assert discovery["model"]==final["model"]=="openai/gpt-6-luna"
    assert "tools" not in final
    assert final["response_format"]["type"]=="json_schema"
    assert final["provider"]["allow_fallbacks"] is False
    text=final["messages"][0]["content"]
    assert "HOST-VERIFIED VISUAL TOOL RESULTS" in text
    assert '"result_index":3' in text
    assert "trace_sha256" in text


def test_when_disabled_exactly_one_paid_json_post(monkeypatch):
    server=ProviderReplay([response(plan=DEMO_PHOTOSYNTHESIS_PLAN)])
    server.install(monkeypatch)
    planner=OpenRouterPaidLessonPlanner(
        api_key="test-token-not-paid-please-dont-call",agentic_visual_tools=False)
    plan=asyncio.run(planner.create_plan(LearningRequest(topic="Các khái niệm cơ bản")))
    assert isinstance(plan,LessonPlan)
    assert len(server.requests)==1
    assert "tools" not in server.requests[0]
    assert Settings(_env_file=None).agentic_visual_tools is False
    assert Settings(_env_file=None,agentic_visual_tools=True).agentic_visual_tools is True


@pytest.mark.parametrize("call_data,finish,model", [
    ([function_call("exec_python",{"code":"print('hello')"})],"tool_calls","openai/gpt-6-luna"),
    ([function_call("probe_array_trace",{"values":[7,1,3,5,9],"target":7})],"tool_calls","openai/gpt-6-luna"),
    ([function_call("describe_visual_tools",{})]*4,"tool_calls","openai/gpt-6-luna"),
    ([],"stop","openai/gpt-6-luna"),
    ([function_call("describe_visual_tools",{})],"tool_calls","provider/untrusted-model"),
    ([function_call("describe_visual_tools",{})],"tool_calls","openai/gpt-6-luna"),
])
def test_agent_fail_closed_without_extra_paid_request(monkeypatch,call_data,finish,model):
    server=ProviderReplay([response(call_data,finish,model)])
    server.install(monkeypatch)
    planner=OpenRouterPaidLessonPlanner(
        api_key="test-token-not-paid-please-dont-call",agentic_visual_tools=True)
    with pytest.raises(PlannerProviderError):
        asyncio.run(planner.create_plan(LearningRequest(topic="Tìm kiếm nhị phân")))
    assert len(server.requests)==1


def test_agentic_repair_is_one_json_request_no_recursive_discovery(monkeypatch):
    server=ProviderReplay([response(plan=DEMO_PHOTOSYNTHESIS_PLAN)])
    server.install(monkeypatch)
    planner=OpenRouterPaidLessonPlanner(
        api_key="test-token-not-paid-please-dont-call",agentic_visual_tools=True)
    from app.planning.validator import PlanIssue
    plan=asyncio.run(planner.repair_plan(
        LearningRequest(topic="Quang hợp"),
        DEMO_PHOTOSYNTHESIS_PLAN,
        [PlanIssue(code="test",message="Test validation issue",severity="error")],
    ))
    assert isinstance(plan,LessonPlan)
    assert len(server.requests)==1
    assert "tools" not in server.requests[0]


@pytest.mark.parametrize("status,expected_code",[
    (404,"paid_planner_no_compatible_endpoint"),
    (408,"paid_planner_upstream_timeout"),
    (409,"paid_planner_conflict"),
    (413,"paid_planner_payload_too_large"),
    (429,"paid_planner_rate_limited"),
    (451,"paid_planner_http_451"),
    (503,"paid_planner_upstream"),
])
@pytest.mark.parametrize("phase",["structured_plan","visual_discovery"])
def test_openrouter_http_status_diagnosed_exactly_without_leaking_body(
    monkeypatch, caplog, status, expected_code, phase
):
    import httpx
    calls=[]
    class HTTPFailureClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,url,headers,json):
            calls.append(json)
            return httpx.Response(
                status,
                request=httpx.Request("POST",url),
                json={"error":{"code":status,"message":"secret-upstream-user-prompt",
                               "metadata":{"error_type":"not_found" if status==404 else "invalid_request"}}},
            )
    monkeypatch.setattr(httpx,"AsyncClient",HTTPFailureClient)
    planner=OpenRouterPaidLessonPlanner(
        api_key="ci-fake-valid-provider-key-1234",
        agentic_visual_tools=(phase=="visual_discovery"),
    )
    with pytest.raises(PlannerProviderError) as exc:
        asyncio.run(planner.create_plan(LearningRequest(topic="Vì sao các hành tinh có quỹ đạo?")))
    assert exc.value.code==expected_code
    assert f"HTTP {status}" in exc.value.message
    assert len(calls)==1
    assert "secret-upstream-user-prompt" not in caplog.text
    assert "secret-upstream-user-prompt" not in exc.value.message
    assert f"phase={phase}" in caplog.text
    assert f"status={status}" in caplog.text


@pytest.mark.parametrize("status,expected_code",[
    (404,"paid_planner_no_compatible_endpoint"),
    (429,"paid_planner_rate_limited"),
    (503,"paid_planner_upstream"),
])
def test_nonstreaming_http_200_error_body_is_classified_not_model_mismatch(
    monkeypatch,caplog,status,expected_code
):
    import httpx
    called=[]
    class ResponseWithErrorClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,url,headers,json):
            called.append(json)
            return httpx.Response(
                200,request=httpx.Request("POST",url),
                json={"error":{"code":status,"message":"private-provider-prompt",
                               "metadata":{"error_type":"provider_unavailable"}}},
            )
    monkeypatch.setattr(httpx,"AsyncClient",ResponseWithErrorClient)
    planner=OpenRouterPaidLessonPlanner(api_key="ci-fake-valid-provider-key-1234")
    with pytest.raises(PlannerProviderError) as exc:
        asyncio.run(planner.create_plan(LearningRequest(topic="Vì sao các hành tinh có quỹ đạo?")))
    assert exc.value.code==expected_code
    assert f"HTTP {status}" in exc.value.message
    assert len(called)==1
    assert "private-provider-prompt" not in caplog.text
    assert "private-provider-prompt" not in exc.value.message
