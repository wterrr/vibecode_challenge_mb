"""Base interfaces and domain exceptions for LLM lesson planners."""

from abc import ABC, abstractmethod
from typing import Any
from app.domain.lesson import LearningRequest, LessonPlan


class PlannerProviderError(RuntimeError):
    """Raised when an LLM provider encounters a structured, safe failure."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class PlannerOutputValidationError(PlannerProviderError):
    """Verified provider JSON failed local validation; retain input only in memory.

    The invalid model output must never appear in messages, logs, job records
    or other user-visible diagnostics. A bounded, explicit repair may use it.
    """

    def __init__(self, *, invalid_json: str, issues: list[dict[str, str]]):
        self.invalid_json = invalid_json
        self.issues = issues
        summary = ", ".join(
            f"{issue['path']} ({issue['type']})" for issue in issues[:3]
        ) or "unknown validation failure"
        super().__init__(
            code="paid_planner_invalid_plan",
            message=f"OpenRouter lesson plan failed local validation: {summary}.",
            retryable=False,
        )


class LessonPlanner(ABC):
    """Abstract interface for planning and repairing educational lesson plans."""

    @abstractmethod
    async def create_plan(
        self,
        request: LearningRequest,
    ) -> LessonPlan:
        """Generate a complete structured LessonPlan from a user request."""
        ...

    @abstractmethod
    async def repair_plan(
        self,
        request: LearningRequest,
        invalid_plan: LessonPlan,
        errors: list[Any],
    ) -> LessonPlan:
        """Repair an invalid LessonPlan based on reported validation errors."""
        ...
