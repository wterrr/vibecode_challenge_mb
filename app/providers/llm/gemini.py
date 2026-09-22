"""Gemini structured lesson planner provider using Google GenAI SDK."""

import asyncio
import json
import logging
from typing import Any
from google import genai
from pydantic import ValidationError

from app.domain.lesson import LearningRequest, LessonPlan
from app.planning.prompts import build_lesson_plan_prompt, build_repair_prompt
from app.providers.llm.base import LessonPlanner, PlannerProviderError

logger = logging.getLogger(__name__)


def _map_gemini_exception(exc: Exception) -> PlannerProviderError:
    """Map raw provider exception to safe structured PlannerProviderError without leaking secrets."""
    if isinstance(exc, PlannerProviderError):
        return exc

    exc_type = type(exc).__name__
    status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)

    # Convert status code or error indicators to string safely
    err_str = str(exc).lower()

    if (
        isinstance(exc, (TimeoutError, asyncio.TimeoutError))
        or "timeout" in err_str
        or "deadline" in err_str
    ):
        return PlannerProviderError(
            code="planner_timeout",
            message="LLM provider request timed out.",
            retryable=True,
        )

    if (
        status_code in (401, 403)
        or "unauthenticated" in err_str
        or "permission_denied" in err_str
        or "api_key" in err_str
        or "auth" in err_str
    ):
        return PlannerProviderError(
            code="planner_auth_error",
            message="Authentication failed with the LLM provider.",
            retryable=False,
        )

    if (
        status_code in (429, 402)
        or "resource_exhausted" in err_str
        or "quota" in err_str
        or "rate_limit" in err_str
        or "rate limit" in err_str
    ):
        return PlannerProviderError(
            code="planner_rate_limited",
            message="LLM provider rate limit or quota exceeded.",
            retryable=True,
        )

    if isinstance(exc, (json.JSONDecodeError, ValidationError)):
        return PlannerProviderError(
            code="planner_invalid_output",
            message="LLM provider output did not conform to the expected schema.",
            retryable=True,
        )

    return PlannerProviderError(
        code="planner_provider_error",
        message=f"LLM provider encountered an error ({exc_type}).",
        retryable=False,
    )


class GeminiLessonPlanner(LessonPlanner):
    """Generates structured lesson plans using the official Google GenAI SDK."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float = 30.0,
    ):
        if not api_key or not api_key.strip():
            raise ValueError("api_key must be non-empty")
        if not model or not model.strip():
            raise ValueError("model must be non-empty")

        self._api_key = api_key
        self.model = model
        self.timeout = timeout
        self._client = genai.Client(api_key=api_key)

    async def _execute_with_retry(self, prompt: str) -> str:
        """Call Gemini Interactions API with structured schema and bounded transient retry."""
        schema = LessonPlan.model_json_schema()
        max_attempts = 2

        for attempt in range(1, max_attempts + 1):
            try:
                def _call() -> str:
                    interaction = self._client.interactions.create(
                        model=self.model,
                        input=prompt,
                        response_format={
                            "type": "text",
                            "mime_type": "application/json",
                            "schema": schema,
                        },
                        timeout=self.timeout,
                    )
                    out = getattr(interaction, "output_text", None)
                    if not out and hasattr(interaction, "text"):
                        out = interaction.text
                    if not out:
                        raise ValueError("Empty output_text from interaction")
                    return str(out)

                raw_text = await asyncio.to_thread(_call)
                return raw_text

            except Exception as exc:
                mapped = _map_gemini_exception(exc)
                logger.error(
                    "Gemini provider error provider=gemini model=%s exception_type=%s error_code=%s attempt=%d",
                    self.model,
                    type(exc).__name__,
                    mapped.code,
                    attempt,
                )

                if mapped.retryable and attempt < max_attempts:
                    await asyncio.sleep(0.5)
                    continue
                raise mapped from None

        raise PlannerProviderError(
            code="planner_provider_error",
            message="LLM provider failed after retries.",
            retryable=False,
        )

    async def create_plan(self, request: LearningRequest) -> LessonPlan:
        """Generate a complete structured LessonPlan from a user request."""
        prompt = build_lesson_plan_prompt(request)
        raw_json = await self._execute_with_retry(prompt)
        try:
            return LessonPlan.model_validate_json(raw_json)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error(
                "Gemini provider produced unparseable plan provider=gemini model=%s exception_type=%s",
                self.model,
                type(exc).__name__,
            )
            raise PlannerProviderError(
                code="planner_invalid_output",
                message="LLM provider output did not conform to the expected schema.",
                retryable=True,
            ) from None

    async def repair_plan(
        self,
        request: LearningRequest,
        invalid_plan: LessonPlan,
        errors: list[Any],
    ) -> LessonPlan:
        """Repair an invalid LessonPlan based on reported validation errors."""
        prompt = build_repair_prompt(request, invalid_plan, errors)
        raw_json = await self._execute_with_retry(prompt)
        try:
            return LessonPlan.model_validate_json(raw_json)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error(
                "Gemini repair produced unparseable plan provider=gemini model=%s exception_type=%s",
                self.model,
                type(exc).__name__,
            )
            raise PlannerProviderError(
                code="planner_invalid_output",
                message="LLM provider output did not conform to the expected schema.",
                retryable=True,
            ) from None
