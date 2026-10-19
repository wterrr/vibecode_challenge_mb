"""Paid OpenRouter planner for the validated LearnFlow lesson pipeline.

Only the pinned paid OpenAI model. No provider/model fallback or automatic
retry of a paid POST. Strict output remains validated by the LessonPlan model.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from pydantic import ValidationError

from app.domain.lesson import LearningRequest, LessonPlan
from app.planning.prompts import build_lesson_plan_prompt, build_repair_prompt
from app.providers.llm.base import LessonPlanner, PlannerProviderError

log = logging.getLogger(__name__)

# OpenAI Structured Outputs strict mode accepts only a subset of JSON Schema.
# Keep stricter local Pydantic validators to check model content after parsing.
_UNSUPPORTED_STRICT_KEYS = frozenset({
    "default", "discriminator", "format", "minLength", "maxLength", "pattern",
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "multipleOf", "minItems", "maxItems", "uniqueItems",
    "minProperties", "maxProperties",
})


def build_strict_lesson_plan_schema() -> dict[str, Any]:
    """Make Pydantic's lesson schema compatible with strict structured output.

    Strict providers require every object key, required=all properties, and
    additionalProperties=false. Pydantic's discriminated union uses oneOf,
    while OpenAI's strict schema supports anyOf; the literal 'type' fields
    still distinguish each branch. Any stripped constraints remain enforced
    when LessonPlan.model_validate_json is called.
    """
    def convert(node: Any) -> Any:
        if isinstance(node, list):
            return [convert(item) for item in node]
        if not isinstance(node, dict):
            return node
        result = {key: convert(value) for key, value in node.items()
                  if key not in _UNSUPPORTED_STRICT_KEYS}
        if "oneOf" in result:
            result["anyOf"] = result.pop("oneOf")
        if result.get("type") == "object" or "properties" in result:
            properties = result.get("properties", {})
            result["required"] = list(properties)
            result["additionalProperties"] = False
        return result

    return convert(LessonPlan.model_json_schema())


def _http_error(status: int) -> tuple[str, str]:
    """Report useful but non-sensitive provider failures."""
    if status in (401, 403):
        return "paid_planner_auth_failed", "OpenRouter rejected the API key or access (HTTP 401/403)."
    if status == 402:
        return "paid_planner_credits", "OpenRouter reports insufficient credits (HTTP 402)."
    if status == 429:
        return "paid_planner_rate_limited", "OpenRouter rate limit or quota was reached (HTTP 429)."
    if status in (400, 422):
        return "paid_planner_bad_request", "OpenRouter rejected the planner request or JSON schema (HTTP 400/422)."
    if status >= 500:
        return "paid_planner_upstream", "OpenRouter/provider failed during planning (HTTP 5xx)."
    return "paid_planner_http_error", "OpenRouter rejected the planner request."


class OpenRouterPaidLessonPlanner(LessonPlanner):
    def __init__(self, *, api_key: str, model: str = "openai/gpt-6-luna", tokens: int = 12000):
        if not api_key or len(api_key) < 16:
            raise ValueError("OPENROUTER_API_KEY is required")
        if not model.startswith("openai/") or model.endswith(":free"):
            raise ValueError("Paid OpenAI model required; no free models")
        self.api_key = api_key
        self.model = model
        self.tokens = tokens

    async def _complete(self, prompt: str) -> LessonPlan:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.tokens,
            "provider": {"allow_fallbacks": False, "require_parameters": True},
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "learnflow_lesson_plan",
                    "strict": True,
                    "schema": build_strict_lesson_plan_schema(),
                },
            },
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(75.0, connect=10.0)) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": "Bearer " + self.api_key,
                        "Content-Type": "application/json",
                        "X-OpenRouter-Title": "LearnFlow Private Studio",
                    },
                    json=payload,
                )
                response.raise_for_status()
                obj = response.json()
            if not isinstance(obj, dict) or obj.get("model") != self.model:
                raise PlannerProviderError(
                    "paid_planner_model_mismatch",
                    "OpenRouter returned an unverified model response; no fallback accepted.",
                    retryable=False,
                )
            choice = (obj.get("choices") or [])[0]
            if choice.get("finish_reason") != "stop":
                raise PlannerProviderError(
                    "paid_planner_incomplete",
                    "OpenRouter did not finish the lesson plan; check output token budget.",
                    retryable=False,
                )
            body = choice["message"]["content"]
            if not isinstance(body, str) or not body.strip():
                raise PlannerProviderError(
                    "paid_planner_empty_output",
                    "OpenRouter returned no usable lesson plan.",
                    retryable=False,
                )
            return LessonPlan.model_validate_json(body)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            code, message = _http_error(status)
            log.warning("Paid planner HTTP rejection model=%s status=%d code=%s", self.model, status, code)
            raise PlannerProviderError(code, message, retryable=False) from None
        except httpx.TimeoutException:
            log.warning("Paid planner timed out model=%s", self.model)
            raise PlannerProviderError(
                "paid_planner_timeout", "OpenRouter request timed out; no automatic paid retry.",
                retryable=False,
            ) from None
        except httpx.RequestError as exc:
            log.warning("Paid planner transport failure model=%s type=%s", self.model, type(exc).__name__)
            raise PlannerProviderError(
                "paid_planner_network_error", "OpenRouter network request failed; no automatic paid retry.",
                retryable=False,
            ) from None
        except ValidationError:
            log.warning("Paid planner schema validation failed model=%s", self.model)
            raise PlannerProviderError(
                "paid_planner_invalid_plan", "OpenRouter returned JSON that failed lesson-plan validation.",
                retryable=False,
            ) from None
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            log.warning("Paid planner response unverified model=%s type=%s", self.model, type(exc).__name__)
            raise PlannerProviderError(
                "paid_planner_unverified_response", "OpenRouter returned a malformed or unverified response.",
                retryable=False,
            ) from None

    async def create_plan(self, request: LearningRequest) -> LessonPlan:
        return await self._complete(build_lesson_plan_prompt(request))

    async def repair_plan(
        self, request: LearningRequest, invalid_plan: LessonPlan, errors: list[Any],
    ) -> LessonPlan:
        # PlanRepairer explicitly permits one semantic repair POST per job.
        return await self._complete(build_repair_prompt(request, invalid_plan, errors))
