"""Abstract base class for learning video pipelines."""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from app.domain.enums import JobStage
from app.domain.jobs import Job

StageCallback = Callable[[JobStage, int], Awaitable[None]]


class LearningVideoPipeline(ABC):
    """Abstract interface for video generation pipelines."""

    requires_published_artifact: bool = False

    @abstractmethod
    async def process(
        self,
        job: Job,
        on_stage: StageCallback,
    ) -> None:
        """Process a job through pipeline stages reporting progress via callback."""
        ...
