"""In-process background job runner using single-worker asyncio.Queue."""

import asyncio
import logging
from app.domain.enums import JobStage, JobStatus
from app.domain.errors import JobError, PipelineExecutionError
from app.pipeline.base import LearningVideoPipeline
from app.repositories.base import JobRepository
from app.storage.base import ArtifactStore

logger = logging.getLogger(__name__)


class JobRunner:
    """Processes video generation jobs asynchronously with a single worker."""

    def __init__(
        self,
        repository: JobRepository,
        pipeline: LearningVideoPipeline,
        artifact_store: ArtifactStore | None = None,
    ):
        self.repository = repository
        self.pipeline = pipeline
        self.artifact_store = artifact_store
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the background worker if not already running."""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker())
            logger.info("JobRunner background worker started")

    async def stop(self) -> None:
        """Stop the background worker task cleanly."""
        if self._worker_task is not None and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        self._worker_task = None
        logger.info("JobRunner background worker stopped")

    async def enqueue(self, job_id: str) -> None:
        """Enqueue a job ID for background processing."""
        await self.queue.put(job_id)
        logger.info("Enqueued job %s (queue size: %d)", job_id, self.queue.qsize())

    async def _worker(self) -> None:
        """Worker loop processing one job at a time from the queue."""
        while True:
            try:
                job_id = await self.queue.get()
            except asyncio.CancelledError:
                break

            try:
                await self._process_job(job_id)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(
                    "Unexpected worker exception job_id=%s exception_type=%s",
                    job_id,
                    type(exc).__name__,
                )
            finally:
                self.queue.task_done()

    async def _process_job(self, job_id: str) -> None:
        """Process a single job through pipeline with state tracking."""
        job = self.repository.get(job_id)
        if job is None:
            logger.warning("Job %s not found in repository, skipping", job_id)
            return

        if job.status != JobStatus.QUEUED:
            logger.warning("Job %s has status %s, expected queued; skipping", job_id, job.status.value)
            return

        # Start execution: set running, initial stage, and increment attempt_count
        current_stage: JobStage | None = JobStage.PLANNING
        current_progress = 10
        self.repository.update_state(
            job_id,
            status=JobStatus.RUNNING,
            stage=current_stage,
            progress_percent=current_progress,
            increment_attempt=True,
        )
        logger.info("Job %s started processing (attempt %d)", job_id, (job.attempt_count + 1))

        async def on_stage(stage: JobStage, progress: int) -> None:
            nonlocal current_stage, current_progress
            current_stage = stage
            current_progress = progress
            self.repository.update_state(
                job_id,
                status=JobStatus.RUNNING,
                stage=stage,
                progress_percent=progress,
            )
            logger.debug("Job %s transitioned to stage %s (%d%%)", job_id, stage.value, progress)

        try:
            await self.pipeline.process(job, on_stage)

            # CP8 Invariant: Real video pipelines require a published, non-empty final artifact
            if getattr(self.pipeline, "requires_published_artifact", False):
                has_valid_final = False
                if self.artifact_store is not None:
                    final_path = self.artifact_store.get_final_path(job_id)
                    if (
                        final_path is not None
                        and final_path.exists()
                        and final_path.is_file()
                        and final_path.stat().st_size > 0
                    ):
                        has_valid_final = True

                if not has_valid_final:
                    logger.error(
                        "Job %s pipeline finished but final artifact is missing or unpublished",
                        job_id,
                    )
                    job_error = JobError(
                        code="missing_published_artifact",
                        stage=JobStage.VALIDATING_OUTPUT,
                        message="The final video artifact was not published.",
                        retryable=False,
                    )
                    self.repository.update_state(
                        job_id,
                        status=JobStatus.FAILED,
                        stage=JobStage.VALIDATING_OUTPUT,
                        progress_percent=current_progress,
                        error=job_error,
                    )
                    return

            # Pipeline completed successfully
            self.repository.update_state(
                job_id,
                status=JobStatus.SUCCEEDED,
                stage=None,
                progress_percent=100,
            )
            logger.info("Job %s completed successfully", job_id)
        except PipelineExecutionError as err:
            logger.error("Job %s failed at stage %s: %s (code: %s)", job_id, err.stage, err.message, err.code)
            job_error = JobError(
                code=err.code,
                stage=err.stage,
                message=err.message,
                retryable=err.retryable,
            )
            self.repository.update_state(
                job_id,
                status=JobStatus.FAILED,
                stage=err.stage,
                progress_percent=current_progress,
                error=job_error,
            )
        except Exception as exc:
            fallback_stage = current_stage or JobStage.PLANNING
            logger.error(
                "Unexpected pipeline failure job_id=%s stage=%s exception_type=%s",
                job_id,
                fallback_stage.value,
                type(exc).__name__,
            )
            job_error = JobError(
                code="unexpected_pipeline_error",
                stage=fallback_stage,
                message=f"Unexpected pipeline error ({type(exc).__name__}).",
                retryable=False,
            )
            self.repository.update_state(
                job_id,
                status=JobStatus.FAILED,
                stage=fallback_stage,
                progress_percent=current_progress,
                error=job_error,
            )
