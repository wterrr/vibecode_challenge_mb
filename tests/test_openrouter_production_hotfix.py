"""Offline regression tests for the paid OpenRouter planning hotfix.

Tests use fake HTTP responses only; they never send paid requests.
"""
import asyncio

import httpx
import pytest
from jsonschema import Draft202012Validator

from app.config import Settings
from app.domain.lesson import LessonPlan
from app.providers.llm.base import PlannerProviderError
from app.providers.llm.openrouter_paid import (
    OpenRouterPaidLessonPlanner, build_strict_lesson_plan_schema,
)


def test_openrouter_is_default_but_explicit_gemini_can_be_selected():
    assert Settings(_env_file=None).planner_provider == "openrouter"
    assert Settings(_env_file=None, planner_provider="gemini").planner_provider == "gemini"


def test_strict_schema_normalizes_all_object_fields_and_discriminator():
    raw = LessonPlan.model_json_schema()
    normalized = build_strict_lesson_plan_schema()
    Draft202012Validator.check_schema(normalized)
    assert "schema_version" not in raw["required"]
    assert "schema_version" in normalized["required"]

    def visit(node):
        if isinstance(node, list):
            for item in node:
                visit(item)
        elif isinstance(node, dict):
            assert not set(node).intersection({
                "default", "discriminator", "oneOf", "minLength", "maxLength",
                "pattern", "minItems", "maxItems", "minimum", "maximum",
            })
            if node.get("type") == "object" or "properties" in node:
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                visit(value)

    visit(normalized)
    scene = normalized["$defs"]["ScenePlan"]
    assert len(scene["properties"]["visual_spec"]["anyOf"]) == 4


def test_openrouter_sends_strict_schema_and_pinned_model(monkeypatch):
    seen = []
    returned = {
        "model": "openai/gpt-6-luna",
        "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
    }

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return returned

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, headers, json):
            seen.append((url, headers, json))
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    marker = object()
    monkeypatch.setattr(LessonPlan, "model_validate_json", staticmethod(lambda text: marker))
    planner = OpenRouterPaidLessonPlanner(
        api_key="ci-fake-provider-key-012345", model="openai/gpt-6-luna", tokens=12000,
    )
    assert asyncio.run(planner._complete("Educational prompt")) is marker
    assert len(seen) == 1
    url, headers, payload = seen[0]
    assert url == "https://openrouter.ai/api/v1/chat/completions"
    assert payload["provider"] == {"allow_fallbacks": False, "require_parameters": True}
    assert payload["model"] == "openai/gpt-6-luna"
    assert payload["response_format"]["json_schema"]["strict"] is True
    assert "schema_version" in payload["response_format"]["json_schema"]["schema"]["required"]
    assert payload["max_tokens"] == 12000


@pytest.mark.parametrize("status,expected", [
    (400, "paid_planner_bad_request"),
    (401, "paid_planner_auth_failed"),
    (402, "paid_planner_credits"),
    (429, "paid_planner_rate_limited"),
    (500, "paid_planner_upstream"),
])
def test_paid_http_errors_are_safe_and_never_retried(monkeypatch, status, expected):
    calls = []

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, headers, json):
            calls.append(url)
            return httpx.Response(
                status, text="provider internal secret / confidential response",
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    planner = OpenRouterPaidLessonPlanner(api_key="ci-fake-provider-key-012345")
    with pytest.raises(PlannerProviderError) as caught:
        asyncio.run(planner._complete("Educational prompt"))
    assert caught.value.code == expected
    assert caught.value.retryable is False
    assert "confidential" not in caught.value.message
    assert len(calls) == 1
