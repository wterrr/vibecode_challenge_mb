"""Tests for FakePipeline and JobRunner asynchronous lifecycle."""

import asyncio
from datetime import datetime, timezone
import pytest

from app.domain.enums import JobStage, JobStatus
from app.domain.errors import PipelineExecutionError
from app.domain.jobs import Job
from app.pipeline.fake import FAKE_STAGES, FakePipeline
from app.repositories.sqlite import SqliteJobRepository
from app.runner.job_runner import JobRunner
from tests.conftest import make_test_job


@pytest.mark.asyncio
async def test_fake_pipeline_successful_lifecycle(test_repo: SqliteJobRepository) -> None:
    """FakePipeline transitions through all stages, updates attempt_count to 1, and marks job succeeded."""
    job = make_test_job(
        job_id="lifecycle-test-1",
        topic="Asynchronous Processing in Python",
        status=JobStatus.QUEUED,
        progress_percent=0,
        attempt_count=0,
    )
    test_repo.create(job)
    assert test_repo.get("lifecycle-test-1").attempt_count == 0

    pipeline = FakePipeline(step_delay_seconds=0.001)
    runner = JobRunner(repository=test_repo, pipeline=pipeline)

    await runner.start()
    try:
        await runner.enqueue("lifecycle-test-1")
        await runner.queue.join()

        completed = test_repo.get("lifecycle-test-1")
        assert completed is not None
        assert completed.status == JobStatus.SUCCEEDED
        assert completed.stage is None
        assert completed.progress_percent == 100
        assert completed.attempt_count == 1
        assert completed.artifact_path is None
        assert completed.error is None
    finally:
        await runner.stop()


@pytest.mark.asyncio
async def test_fake_pipeline_injected_failure(test_repo: SqliteJobRepository) -> None:
    """FakePipeline raises deterministic error at injected stage, recording structured JobError."""
    job = make_test_job(
        job_id="fail-test-1",
        topic="Failure Handling",
        status=JobStatus.QUEUED,
        progress_percent=0,
        attempt_count=0,
    )
    test_repo.create(job)

    # Injected failure at RENDERING stage
    pipeline = FakePipeline(
        step_delay_seconds=0.001,
        fail_at_stage=JobStage.RENDERING,
    )
    runner = JobRunner(repository=test_repo, pipeline=pipeline)

    await runner.start()
    try:
        await runner.enqueue("fail-test-1")
        await runner.queue.join()

        failed_job = test_repo.get("fail-test-1")
        assert failed_job is not None
        assert failed_job.status == JobStatus.FAILED
        assert failed_job.stage == JobStage.RENDERING
        assert failed_job.attempt_count == 1
        assert failed_job.error is not None
        assert failed_job.error.code == "fake_pipeline_failure"
        assert failed_job.error.stage == JobStage.RENDERING
        assert failed_job.error.retryable is False
    finally:
        await runner.stop()


@pytest.mark.asyncio
async def test_runner_ignores_missing_and_non_queued_jobs(test_repo: SqliteJobRepository) -> None:
    """Runner safely handles missing job ID or non-queued status without crashing worker."""
    already_succeeded = make_test_job(
        job_id="already-succeeded",
        topic="Done",
        status=JobStatus.SUCCEEDED,
        progress_percent=100,
    )
    test_repo.create(already_succeeded)

    pipeline = FakePipeline(step_delay_seconds=0.001)
    runner = JobRunner(repository=test_repo, pipeline=pipeline)

    await runner.start()
    try:
        # Enqueue non-existent ID
        await runner.enqueue("non-existent-id")
        # Enqueue already succeeded job
        await runner.enqueue("already-succeeded")

        await runner.queue.join()

        # Worker should remain alive
        assert runner._worker_task is not None
        assert not runner._worker_task.done()

        # Job status unchanged
        unchanged = test_repo.get("already-succeeded")
        assert unchanged.status == JobStatus.SUCCEEDED
    finally:
        await runner.stop()


@pytest.mark.asyncio
async def test_fake_pipeline_unexpected_exception(test_repo: SqliteJobRepository) -> None:
    """Unexpected exception in pipeline is caught, sanitized, and stored as unexpected_pipeline_error."""
    job = make_test_job(
        job_id="unexpected-err-job",
        topic="Chaos Engineering",
        status=JobStatus.QUEUED,
        progress_percent=0,
    )
    test_repo.create(job)


    class CrashingPipeline(FakePipeline):
        async def process(self, job, on_stage):
            await on_stage(JobStage.AUDIO, 40)
            raise ZeroDivisionError("division by zero in speech synthesizer")

    pipeline = CrashingPipeline(step_delay_seconds=0.001)
    runner = JobRunner(repository=test_repo, pipeline=pipeline)

    await runner.start()
    try:
        await runner.enqueue("unexpected-err-job")
        await runner.queue.join()

        failed_job = test_repo.get("unexpected-err-job")
        assert failed_job is not None
        assert failed_job.status == JobStatus.FAILED
        assert failed_job.error is not None
        assert failed_job.error.code == "unexpected_pipeline_error"
        assert failed_job.error.retryable is False
        assert "ZeroDivisionError" in failed_job.error.message
    finally:
        await runner.stop()
