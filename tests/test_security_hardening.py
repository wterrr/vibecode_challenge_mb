"""Regression tests ensuring unexpected exceptions and errors never leak secrets."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.domain.enums import JobStage, JobStatus
from app.main import create_app
from app.pipeline.base import LearningVideoPipeline
from app.pipeline.fake import FakePipeline
from app.repositories.sqlite import SqliteJobRepository
from app.runner.job_runner import JobRunner
from app.storage.local import LocalArtifactStore
from tests.conftest import make_test_job


class SecretLeakingPipeline(LearningVideoPipeline):
    """Pipeline double that raises an unhandled exception containing sensitive secrets."""

    async def process(self, job, on_stage):
        await on_stage(JobStage.PLANNING, 10)
        raise RuntimeError("request failed api_key=SUPERSECRET token=abc123")


@pytest.mark.asyncio
async def test_unexpected_pipeline_exception_sanitizes_secrets(
    test_repo: SqliteJobRepository,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unexpected pipeline exception must not leak secrets to job error or logs."""
    job = make_test_job(
        job_id="sec-job-1",
        topic="Secret Topic",
        status=JobStatus.QUEUED,
    )
    test_repo.create(job)

    pipeline = SecretLeakingPipeline()
    runner = JobRunner(repository=test_repo, pipeline=pipeline)

    caplog.clear()
    await runner.start()
    try:
        await runner.enqueue("sec-job-1")
        await runner.queue.join()

        failed_job = test_repo.get("sec-job-1")
        assert failed_job is not None
        assert failed_job.status == JobStatus.FAILED
        assert failed_job.error is not None
        assert failed_job.error.code == "unexpected_pipeline_error"
        assert "RuntimeError" in failed_job.error.message

        forbidden_strings = ["SUPERSECRET", "abc123", "api_key", "token=abc123"]
        for s in forbidden_strings:
            assert s not in failed_job.error.message, f"Secret '{s}' leaked into error message"
            assert s not in caplog.text, f"Secret '{s}' leaked into log output"
    finally:
        await runner.stop()


def test_api_does_not_expose_injected_secrets_for_failed_job(
    test_repo: SqliteJobRepository,
    temp_artifacts_dir: Path,
) -> None:
    """GET /api/jobs/{id} response must not expose raw secrets from failed pipeline runs."""
    pipeline = SecretLeakingPipeline()
    artifact_store = LocalArtifactStore(temp_artifacts_dir)
    app = create_app(
        repository=test_repo,
        artifact_store=artifact_store,
        pipeline=pipeline,
    )

    with TestClient(app) as client:
        # Create job through API to persist and enqueue
        create_res = client.post(
            "/api/jobs",
            json={
                "topic": "API Secret Leak Test",
                "audience": "Beginner",
                "language": "vi",
                "target_duration_seconds": 90,
            },
        )
        assert create_res.status_code == 202
        job_id = create_res.json()["job_id"]

        # Background worker runs and processes job with SecretLeakingPipeline
        import time
        for _ in range(50):
            time.sleep(0.05)
            check = test_repo.get(job_id)
            if check and check.status == JobStatus.FAILED:
                break

        res = client.get(f"/api/jobs/{job_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "failed"
        assert data["error"]["code"] == "unexpected_pipeline_error"

        # Explicitly verify sensitive tokens are absent from entire response payload
        raw_response_text = res.text
        forbidden_strings = ["SUPERSECRET", "abc123", "api_key", "token=abc123"]
        for s in forbidden_strings:
            assert s not in raw_response_text, f"Secret '{s}' leaked into API response JSON"


def test_artifact_deletion_failure_sanitizes_secrets_and_preserves_db_row(
    test_repo: SqliteJobRepository,
    fast_fake_pipeline: FakePipeline,
    temp_artifacts_dir: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Failed artifact deletion must return generic 500, preserve DB row, and not leak secrets."""
    job = make_test_job(
        job_id="sec-del-job",
        topic="Delete Secret Leak Test",
        status=JobStatus.SUCCEEDED,
    )
    test_repo.create(job)

    class SecretLeakingArtifactStore(LocalArtifactStore):
        def delete_job_artifacts(self, job_id: str) -> None:
            raise RuntimeError("filesystem failure secret=DELETESECRET")

    leaking_store = SecretLeakingArtifactStore(temp_artifacts_dir)
    app = create_app(
        repository=test_repo,
        artifact_store=leaking_store,
        pipeline=fast_fake_pipeline,
    )

    caplog.clear()
    with TestClient(app) as client:
        res = client.delete("/api/jobs/sec-del-job")
        assert res.status_code == 500
        assert res.json()["detail"] == "Failed to delete job artifacts."

        # DB row MUST remain intact
        assert test_repo.get("sec-del-job") is not None

        # Secrets must NOT appear in response body or captured logs
        assert "DELETESECRET" not in res.text
        assert "DELETESECRET" not in caplog.text
