"""Abstract base class for Job repository."""

from abc import ABC, abstractmethod
from app.domain.enums import JobStage, JobStatus
from app.domain.errors import JobError
from app.domain.jobs import Job
from app.domain.lesson import LessonPlan


class JobRepository(ABC):
    """Abstract interface for job persistence."""

    @abstractmethod
    def create(self, job: Job) -> Job:
        """Persist a new job. Raise error if ID already exists."""
        ...

    @abstractmethod
    def get(self, job_id: str) -> Job | None:
        """Retrieve a job by ID, or None if not found."""
        ...

    @abstractmethod
    def list(
        self,
        limit: int = 50,
        status: JobStatus | None = None,
    ) -> list[Job]:
        """List jobs newest first, optionally filtered by status. Limit: 1..100."""
        ...

    @abstractmethod
    def update_state(
        self,
        job_id: str,
        *,
        status: JobStatus,
        stage: JobStage | None,
        progress_percent: int,
        error: JobError | None = None,
        increment_attempt: bool = False,
    ) -> Job | None:
        """Update lifecycle state and error. If error is None, clear error columns."""
        ...

    @abstractmethod
    def set_plan(
        self,
        job_id: str,
        plan: LessonPlan,
    ) -> Job | None:
        """Store validated lesson plan JSON without changing job status."""
        ...

    @abstractmethod
    def set_artifact(
        self,
        job_id: str,
        artifact_path: str,
        metadata: dict,
    ) -> Job | None:
        """Store final published artifact path and metadata without changing status."""
        ...

    @abstractmethod
    def update_user_fields(
        self,
        job_id: str,
        display_title: str | None,
        note: str | None,
    ) -> Job | None:
        """Update only user-editable fields (display_title, note)."""
        ...

    @abstractmethod
    def delete(self, job_id: str) -> bool:
        """Delete job by ID. Return True if deleted, False if not found."""
        ...
