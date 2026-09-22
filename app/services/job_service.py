"""JobService coordinating repository, artifact store, and async runner."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import logging
import uuid

from app.domain.enums import JobStatus
from app.domain.jobs import Job
from app.domain.lesson import LearningRequest
from app.repositories.base import JobRepository
from app.runner.job_runner import JobRunner
from app.storage.base import ArtifactStore

logger = logging.getLogger(__name__)


class DeleteStatus(str, Enum):
    """Result status of a delete operation."""

    SUCCESS = "success"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    ERROR = "error"


@dataclass
class DeleteResult:
    """Outcome of attempting to delete a job and its artifacts."""

    status: DeleteStatus
    message: str | None = None


class JobService:
    """Coordinates business operations across repository, artifact store, and runner."""

    def __init__(
        self,
        repository: JobRepository,
        artifact_store: ArtifactStore,
        runner: JobRunner,
    ):
        self.repository = repository
        self.artifact_store = artifact_store
        self.runner = runner

    async def create_job(self, request: LearningRequest) -> Job:
        """Create a new job, persisting to repository BEFORE enqueuing."""
        now = datetime.now(timezone.utc)
        job = Job(
            id=str(uuid.uuid4()),
            topic=request.topic,
            audience=request.audience,
            language=request.language,
            target_duration_seconds=request.target_duration_seconds,
            status=JobStatus.QUEUED,
            stage=None,
            progress_percent=0,
            created_at=now,
            updated_at=now,
        )

        # Invariant: persist BEFORE enqueue
        persisted = self.repository.create(job)
        logger.info("Persisted new job %s to database", persisted.id)

        await self.runner.enqueue(persisted.id)
        return persisted

    def get_job(self, job_id: str) -> Job | None:
        """Retrieve job by ID."""
        return self.repository.get(job_id)

    def list_jobs(self, limit: int = 50, status: JobStatus | None = None) -> list[Job]:
        """List jobs ordered newest-first with optional status filter."""
        return self.repository.list(limit=limit, status=status)

    def update_user_fields(
        self,
        job_id: str,
        display_title: str | None,
        note: str | None,
    ) -> Job | None:
        """Update user-modifiable fields (display_title and note)."""
        return self.repository.update_user_fields(
            job_id,
            display_title=display_title,
            note=note,
        )

    def delete_job(self, job_id: str) -> DeleteResult:
        """Delete job and artifacts only if completed or failed; reject queued/running."""
        job = self.repository.get(job_id)
        if job is None:
            return DeleteResult(status=DeleteStatus.NOT_FOUND, message="Job not found")

        if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
            return DeleteResult(
                status=DeleteStatus.CONFLICT,
                message=f"Cannot delete job in {job.status.value} state",
            )

        # First delete artifact directory
        try:
            self.artifact_store.delete_job_artifacts(job_id)
        except Exception as exc:
            logger.error(
                "Failed to delete artifacts for job_id=%s exception_type=%s",
                job_id,
                type(exc).__name__,
            )
            return DeleteResult(
                status=DeleteStatus.ERROR,
                message="Failed to delete job artifacts.",
            )

        # Then delete database row
        deleted = self.repository.delete(job_id)
        if not deleted:
            return DeleteResult(status=DeleteStatus.NOT_FOUND, message="Job not found")

        return DeleteResult(status=DeleteStatus.SUCCESS)
