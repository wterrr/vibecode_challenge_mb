"""Unit tests for LessonPlanner implementations, Gemini provider, and PlanningService."""

import asyncio
import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from app.domain.enums import JobStage
from app.domain.errors import PipelineExecutionError
from app.domain.lesson import LearningRequest, LessonPlan
from app.planning.service import PlanningService
from app.planning.validator import PlanIssue
from app.providers.llm.base import LessonPlanner, PlannerProviderError
from app.providers.llm.gemini import GeminiLessonPlanner
from tests.test_plan_validator import make_valid_tcp_plan


class FakePlanner(LessonPlanner):
    """Test fake for LessonPlanner recording invocations and yielding configured responses."""

    def __init__(
        self,
        plan: LessonPlan | None = None,
        repair_plan: LessonPlan | None = None,
        error: Exception | None = None,
    ):
        self.plan = plan
        self.repair_plan_val = repair_plan
        self.error = error
        self.create_calls = 0
        self.repair_calls = 0
        self.last_repair_errors: list[Any] = []

    async def create_plan(self, request: LearningRequest) -> LessonPlan:
        self.create_calls += 1
        if self.error:
            raise self.error
        if self.plan:
            return self.plan
        raise RuntimeError("FakePlanner: No plan configured")

    async def repair_plan(
        self,
        request: LearningRequest,
        invalid_plan: LessonPlan,
        errors: list[Any],
    ) -> LessonPlan:
        self.repair_calls += 1
        self.last_repair_errors = errors
        if self.repair_plan_val:
            return self.repair_plan_val
        return invalid_plan


@pytest.mark.asyncio
async def test_planning_service_accepts_valid_plan_without_repair() -> None:
    """When the initial plan is valid, repair is never called."""
    valid_plan = make_valid_tcp_plan()
    fake = FakePlanner(plan=valid_plan)
    service = PlanningService(planner=fake)

    request = LearningRequest(
        topic="How does the TCP three-way handshake work?",
        language="vi",
        target_duration_seconds=60,
    )
    result = await service.build_valid_plan(request)

    assert result.title == valid_plan.title
    assert fake.create_calls == 1
    assert fake.repair_calls == 0


@pytest.mark.asyncio
async def test_planning_service_accepts_plan_with_warnings_only() -> None:
    """When a plan only has warnings (e.g. repeated titles), repair is not triggered."""
    plan = make_valid_tcp_plan()
    plan.scenes[2].title = plan.scenes[0].title  # Triggers warning: repeated_scene_titles

    fake = FakePlanner(plan=plan)
    service = PlanningService(planner=fake)

    request = LearningRequest(
        topic="How does the TCP three-way handshake work?",
        language="vi",
        target_duration_seconds=60,
    )
    result = await service.build_valid_plan(request)

    assert result.title == plan.title
    assert fake.create_calls == 1
    assert fake.repair_calls == 0


@pytest.mark.asyncio
async def test_planning_service_repairs_plan_with_errors_once() -> None:
    """When the initial plan has semantic errors, repair is called exactly once."""
    invalid_plan = make_valid_tcp_plan()
    invalid_plan.language = "en"  # Mismatch with vi request -> error

    valid_repaired = make_valid_tcp_plan()
    valid_repaired.language = "vi"

    fake = FakePlanner(plan=invalid_plan, repair_plan=valid_repaired)
    service = PlanningService(planner=fake)

    request = LearningRequest(
        topic="How does the TCP three-way handshake work?",
        language="vi",
        target_duration_seconds=60,
    )
    result = await service.build_valid_plan(request)

    assert result.language == "vi"
    assert fake.create_calls == 1
    assert fake.repair_calls == 1
    assert len(fake.last_repair_errors) > 0


@pytest.mark.asyncio
async def test_planning_service_raises_pipeline_error_if_repair_fails() -> None:
    """When repair still fails semantic validation, raises PipelineExecutionError."""
    invalid_plan = make_valid_tcp_plan()
    invalid_plan.language = "en"

    still_invalid = make_valid_tcp_plan()
    still_invalid.language = "en"  # Still invalid

    fake = FakePlanner(plan=invalid_plan, repair_plan=still_invalid)
    service = PlanningService(planner=fake)

    request = LearningRequest(
        topic="How does the TCP three-way handshake work?",
        language="vi",
        target_duration_seconds=60,
    )

    with pytest.raises(PipelineExecutionError) as exc_info:
        await service.build_valid_plan(request)

    assert exc_info.value.code == "plan_validation_failed"
    assert exc_info.value.stage == JobStage.VALIDATING_PLAN
    assert exc_info.value.retryable is False
    assert fake.create_calls == 1
    assert fake.repair_calls == 1  # Exactly 1 repair attempt, never 2+


# ============================================================
# Gemini Provider Unit Tests (Mocking SDK boundary)
# ============================================================

def test_gemini_init_rejects_empty_credentials() -> None:
    """GeminiLessonPlanner rejects empty API keys or models."""
    with pytest.raises(ValueError):
        GeminiLessonPlanner(api_key="", model="gemini-3.8-flash")
    with pytest.raises(ValueError):
        GeminiLessonPlanner(api_key="key", model="")


@pytest.mark.asyncio
async def test_gemini_provider_uses_configured_model_and_schema() -> None:
    """GeminiLessonPlanner sends correct model and structured output schema."""
    valid_plan = make_valid_tcp_plan()
    raw_json = valid_plan.model_dump_json()

    planner = GeminiLessonPlanner(api_key="fake-test-key", model="gemini-3.8-flash")

    mock_interaction = MagicMock()
    mock_interaction.output_text = raw_json

    with patch.object(planner._client.interactions, "create", return_value=mock_interaction) as mock_create:
        request = LearningRequest(
            topic="How does the TCP three-way handshake work?",
            language="vi",
            target_duration_seconds=60,
        )
        result = await planner.create_plan(request)

        assert result.title == valid_plan.title
        mock_create.assert_called_once()
        _, kwargs = mock_create.call_args
        assert kwargs["model"] == "gemini-3.8-flash"
        assert kwargs["response_format"]["type"] == "text"
        assert kwargs["response_format"]["mime_type"] == "application/json"
        assert "schema" in kwargs["response_format"]


@pytest.mark.asyncio
async def test_gemini_provider_maps_invalid_json_to_safe_error() -> None:
    """Invalid JSON response maps to planner_invalid_output."""
    planner = GeminiLessonPlanner(api_key="fake-test-key", model="gemini-3.8-flash")
    mock_interaction = MagicMock()
    mock_interaction.output_text = "NOT_A_VALID_JSON"

    with patch.object(planner._client.interactions, "create", return_value=mock_interaction):
        request = LearningRequest(topic="TCP Handshake", language="vi")
        with pytest.raises(PlannerProviderError) as exc_info:
            await planner.create_plan(request)

        assert exc_info.value.code == "planner_invalid_output"
        assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_gemini_provider_maps_pydantic_invalid_json_to_safe_error() -> None:
    """JSON that fails LessonPlan schema validation maps to planner_invalid_output."""
    planner = GeminiLessonPlanner(api_key="fake-test-key", model="gemini-3.8-flash")
    mock_interaction = MagicMock()
    # Missing required fields such as scenes
    mock_interaction.output_text = '{"title": "Test", "topic": "TCP"}'

    with patch.object(planner._client.interactions, "create", return_value=mock_interaction):
        request = LearningRequest(topic="TCP Handshake", language="vi")
        with pytest.raises(PlannerProviderError) as exc_info:
            await planner.create_plan(request)

        assert exc_info.value.code == "planner_invalid_output"
        assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_gemini_provider_maps_timeout_to_safe_error() -> None:
    """Timeout exception maps to planner_timeout with retryable=True."""
    planner = GeminiLessonPlanner(api_key="fake-test-key", model="gemini-3.8-flash")

    with patch.object(planner._client.interactions, "create", side_effect=TimeoutError("Request timed out")):
        request = LearningRequest(topic="TCP Handshake", language="vi")
        with pytest.raises(PlannerProviderError) as exc_info:
            await planner.create_plan(request)

        assert exc_info.value.code == "planner_timeout"
        assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_gemini_provider_maps_rate_limit_to_safe_error() -> None:
    """429 / resource exhausted maps to planner_rate_limited."""
    planner = GeminiLessonPlanner(api_key="fake-test-key", model="gemini-3.8-flash")

    class FakeRateLimitError(Exception):
        code = 429
        def __str__(self) -> str:
            return "Resource exhausted quota limit reached"

    with patch.object(planner._client.interactions, "create", side_effect=FakeRateLimitError()):
        request = LearningRequest(topic="TCP Handshake", language="vi")
        with pytest.raises(PlannerProviderError) as exc_info:
            await planner.create_plan(request)

        assert exc_info.value.code == "planner_rate_limited"
        assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_gemini_provider_maps_auth_error_to_safe_error() -> None:
    """401/403 or auth errors map to planner_auth_error with retryable=False."""
    planner = GeminiLessonPlanner(api_key="fake-test-key", model="gemini-3.8-flash")

    class FakeAuthError(Exception):
        code = 401
        def __str__(self) -> str:
            return "API_KEY_INVALID"

    with patch.object(planner._client.interactions, "create", side_effect=FakeAuthError()):
        request = LearningRequest(topic="TCP Handshake", language="vi")
        with pytest.raises(PlannerProviderError) as exc_info:
            await planner.create_plan(request)

        assert exc_info.value.code == "planner_auth_error"
        assert exc_info.value.retryable is False


@pytest.mark.asyncio
async def test_gemini_provider_maps_unexpected_error_to_safe_error() -> None:
    """Unexpected exception maps to planner_provider_error."""
    planner = GeminiLessonPlanner(api_key="fake-test-key", model="gemini-3.8-flash")

    with patch.object(planner._client.interactions, "create", side_effect=RuntimeError("Some strange internal error")):
        request = LearningRequest(topic="TCP Handshake", language="vi")
        with pytest.raises(PlannerProviderError) as exc_info:
            await planner.create_plan(request)

        assert exc_info.value.code == "planner_provider_error"
        assert exc_info.value.retryable is False


@pytest.mark.asyncio
async def test_gemini_provider_does_not_leak_secrets_in_logs_or_messages(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure sensitive secrets embedded in provider exceptions are never logged or returned."""
    injected_secret = "SUPERSECRET-GEMINI-KEY-XYZ"
    planner = GeminiLessonPlanner(api_key=injected_secret, model="gemini-3.8-flash")

    class LeakyException(Exception):
        code = 400
        def __str__(self) -> str:
            return f"Error communicating with auth token {injected_secret}"

    with caplog.at_level(logging.DEBUG):
        with patch.object(planner._client.interactions, "create", side_effect=LeakyException()):
            request = LearningRequest(topic="TCP Handshake", language="vi")
            with pytest.raises(PlannerProviderError) as exc_info:
                await planner.create_plan(request)

    # Injected secret must NOT appear in the exception message
    assert injected_secret not in str(exc_info.value)
    assert injected_secret not in exc_info.value.message

    # Injected secret must NOT appear anywhere in the captured logs
    for record in caplog.records:
        assert injected_secret not in record.message


@pytest.mark.asyncio
async def test_gemini_provider_passes_timeout_parameter() -> None:
    """GeminiLessonPlanner explicitly passes self.timeout to interactions.create."""
    planner = GeminiLessonPlanner(api_key="fake-test-key", model="gemini-3.8-flash", timeout=12.5)
    captured_kwargs: dict[str, Any] = {}

    def fake_create(**kwargs: Any) -> MagicMock:
        nonlocal captured_kwargs
        captured_kwargs = kwargs
        mock = MagicMock()
        mock.output_text = make_valid_tcp_plan().model_dump_json()
        return mock

    with patch.object(planner._client.interactions, "create", side_effect=fake_create):
        request = LearningRequest(topic="TCP Handshake", language="vi")
        await planner.create_plan(request)

    assert captured_kwargs.get("timeout") == 12.5


@pytest.mark.asyncio
async def test_gemini_provider_maps_timeout_and_retries() -> None:
    """Gemini timeout error retries once and maps to planner_timeout with retryable=True."""
    planner = GeminiLessonPlanner(api_key="fake-test-key", model="gemini-3.8-flash", timeout=5.0)
    attempts = 0

    def fake_create(**kwargs: Any) -> None:
        nonlocal attempts
        attempts += 1
        raise TimeoutError("Deadline exceeded waiting for Gemini response")

    with patch.object(planner._client.interactions, "create", side_effect=fake_create):
        request = LearningRequest(topic="TCP Handshake", language="vi")
        with pytest.raises(PlannerProviderError) as exc_info:
            await planner.create_plan(request)

    assert exc_info.value.code == "planner_timeout"
    assert exc_info.value.retryable is True
    assert attempts == 2

