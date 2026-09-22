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
