"""Comprehensive tests for Job CRUD API endpoints."""

from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.enums import JobStage, JobStatus
from app.domain.jobs import Job
from app.domain.lesson import LearningRequest
from app.main import create_app
from app.pipeline.fake import FakePipeline
from app.repositories.sqlite import SqliteJobRepository
from app.runner.job_runner import JobRunner
from app.services.job_service import JobService
from app.storage.local import LocalArtifactStore
from tests.conftest import make_test_job



def test_post_job_creates_and_returns_202(test_client: TestClient, test_repo: SqliteJobRepository) -> None:
    """POST /api/jobs returns 202 Accepted and creates job in queued status."""
    payload = {
        "topic": "How does the TCP three-way handshake work?",
        "audience": "Developer",
        "language": "vi",
        "target_duration_seconds": 90,
    }

    response = test_client.post("/api/jobs", json=payload)
    assert response.status_code == 202

    data = response.json()
    job_id = data["job_id"]
    assert job_id is not None
    assert data["status"] in ("queued", "running", "succeeded")
    assert data["status_url"] == f"/api/jobs/{job_id}"
    assert data["page_url"] == f"/jobs/{job_id}"

    # Verify persisted in database
    persisted = test_repo.get(job_id)
    assert persisted is not None
    assert persisted.topic == payload["topic"]
    assert persisted.audience == payload["audience"]


def test_persist_before_enqueue_invariant(
    test_repo: SqliteJobRepository,
    test_artifact_store: LocalArtifactStore,
    fast_fake_pipeline: FakePipeline,
) -> None:
    """Verify that job is already stored in repository when enqueue is called."""
    enqueue_called = False
    verified_in_repo = False

    class SpyRunner(JobRunner):
        async def enqueue(self, job_id: str) -> None:
            nonlocal enqueue_called, verified_in_repo
            enqueue_called = True
            found = test_repo.get(job_id)
            if found is not None:
                verified_in_repo = True
            await super().enqueue(job_id)

    spy_runner = SpyRunner(repository=test_repo, pipeline=fast_fake_pipeline)
    service = JobService(repository=test_repo, artifact_store=test_artifact_store, runner=spy_runner)

    req = LearningRequest(
        topic="Testing Invariant Persistence Order",
        audience="Student",
        language="en",
        target_duration_seconds=60,
    )

    import asyncio
    created_job = asyncio.run(service.create_job(req))

    assert enqueue_called is True
    assert verified_in_repo is True
    assert created_job.id is not None


def test_post_job_validation_errors(test_client: TestClient) -> None:
    """POST /api/jobs validates topic length, language, and duration."""
    # Empty topic
    res1 = test_client.post("/api/jobs", json={"topic": "   "})
    assert res1.status_code == 422

    # Topic too short (< 3 chars)
    res2 = test_client.post("/api/jobs", json={"topic": "ab"})
    assert res2.status_code == 422

    # Invalid language
    res3 = test_client.post(
        "/api/jobs",
        json={"topic": "Valid Topic Here", "language": "fr"},
    )
    assert res3.status_code == 422

    # Invalid duration
    res4 = test_client.post(
        "/api/jobs",
        json={"topic": "Valid Topic Here", "target_duration_seconds": 45},
    )
    assert res4.status_code == 422


def test_get_jobs_list_and_filtering(test_client: TestClient, test_repo: SqliteJobRepository) -> None:
    """GET /api/jobs returns ordered list with optional filtering and limit validation."""
    j1 = make_test_job(
        job_id="job-list-1",
        topic="First Topic",
        status=JobStatus.SUCCEEDED,
        progress_percent=100,
    )
    j2 = make_test_job(
        job_id="job-list-2",
        topic="Second Topic",
        status=JobStatus.FAILED,
        progress_percent=60,
    )
    test_repo.create(j1)
    test_repo.create(j2)

    # All jobs
    res = test_client.get("/api/jobs")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 2
    ids = [item["id"] for item in items]
    assert "job-list-2" in ids
    assert "job-list-1" in ids

    # Filter succeeded
    res_succeeded = test_client.get("/api/jobs?status=succeeded")
    assert res_succeeded.status_code == 200
    succeeded_items = res_succeeded.json()
    assert all(item["status"] == "succeeded" for item in succeeded_items)

    # Filter failed
    res_failed = test_client.get("/api/jobs?status=failed")
    assert res_failed.status_code == 200
    failed_items = res_failed.json()
    assert all(item["status"] == "failed" for item in failed_items)

    # Limit validation
    res_invalid_limit = test_client.get("/api/jobs?limit=0")
    assert res_invalid_limit.status_code == 422

    res_limit_too_large = test_client.get("/api/jobs?limit=150")
    assert res_limit_too_large.status_code == 422


def test_get_job_detail(test_client: TestClient, test_repo: SqliteJobRepository) -> None:
    """GET /api/jobs/{id} returns job if known or 404 if unknown."""
    job = make_test_job(
        job_id="detail-test-1",
        topic="Quantum Computing",
        audience="Professional",
        language="en",
        target_duration_seconds=120,
        status=JobStatus.QUEUED,
        progress_percent=0,
    )
    test_repo.create(job)

    # Known job
    res = test_client.get("/api/jobs/detail-test-1")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "detail-test-1"
    assert data["topic"] == "Quantum Computing"
    assert data["target_duration_seconds"] == 120
    assert data["video_url"] is None

    # Unknown job
    res_unknown = test_client.get("/api/jobs/non-existent-id")
    assert res_unknown.status_code == 404


def test_patch_job_fields(test_client: TestClient, test_repo: SqliteJobRepository) -> None:
    """PATCH /api/jobs/{id} updates title/note, preserves omitted, and clears on null."""
    job = make_test_job(
        job_id="patch-test-1",
        topic="Initial Topic",
        display_title="Original Title",
        note="Original Note",
        status=JobStatus.SUCCEEDED,
        progress_percent=100,
    )
    test_repo.create(job)

    # 1. Update only display_title, note should remain "Original Note"
    res1 = test_client.patch(
        "/api/jobs/patch-test-1",
        json={"display_title": "New Title"},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["display_title"] == "New Title"
    assert data1["note"] == "Original Note"

    # 2. Update note, display_title should remain "New Title"
    res2 = test_client.patch(
        "/api/jobs/patch-test-1",
        json={"note": "Updated Note"},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["display_title"] == "New Title"
    assert data2["note"] == "Updated Note"

    # 3. Explicitly null note, should become None
    res3 = test_client.patch(
        "/api/jobs/patch-test-1",
        json={"note": None},
    )
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["note"] is None
    assert data3["display_title"] == "New Title"

    # 4. Unknown job
    res4 = test_client.patch("/api/jobs/unknown-id", json={"display_title": "X"})
    assert res4.status_code == 404


def test_delete_job_rules(
    test_client: TestClient,
    test_repo: SqliteJobRepository,
    test_artifact_store: LocalArtifactStore,
) -> None:
    """DELETE /api/jobs/{id} rejects queued/running with 409, deletes succeeded/failed with 204."""
    # 1. Unknown job -> 404
    res_unknown = test_client.delete("/api/jobs/nonexistent-id")
    assert res_unknown.status_code == 404

    # 2. Queued job -> 409 Conflict
    q_job = make_test_job(job_id="del-queued", topic="Queued", status=JobStatus.QUEUED)
    test_repo.create(q_job)
    res_queued = test_client.delete("/api/jobs/del-queued")
    assert res_queued.status_code == 409

    # 3. Running job -> 409 Conflict
    r_job = make_test_job(job_id="del-running", topic="Running", status=JobStatus.RUNNING)
    test_repo.create(r_job)
    res_running = test_client.delete("/api/jobs/del-running")
    assert res_running.status_code == 409

    # 4. Succeeded job -> 204 No Content
    s_job = make_test_job(job_id="del-succeeded", topic="Succeeded", status=JobStatus.SUCCEEDED)
    test_repo.create(s_job)
    # Create test artifact file
    art_path = test_artifact_store.get_job_dir("del-succeeded", create=True) / "test.txt"
    art_path.write_text("artifact content")


    res_succeeded = test_client.delete("/api/jobs/del-succeeded")
    assert res_succeeded.status_code == 204
    assert test_repo.get("del-succeeded") is None
    assert not art_path.parent.exists()

    # 5. Failed job -> 204 No Content
    f_job = make_test_job(job_id="del-failed", topic="Failed", status=JobStatus.FAILED)
    test_repo.create(f_job)
    res_failed = test_client.delete("/api/jobs/del-failed")
    assert res_failed.status_code == 204
    assert test_repo.get("del-failed") is None


def test_delete_artifact_failure_leaves_db_row(
    test_repo: SqliteJobRepository,
    fast_fake_pipeline: FakePipeline,
    temp_artifacts_dir: Path,
) -> None:
    """If artifact deletion fails, returns 500 and preserves database row."""
    job = make_test_job(job_id="err-del-job", topic="Err Del", status=JobStatus.SUCCEEDED)
    test_repo.create(job)

    class FailingArtifactStore(LocalArtifactStore):
        def delete_job_artifacts(self, job_id: str) -> None:
            raise RuntimeError("Disk I/O error during artifact purge")

    failing_store = FailingArtifactStore(temp_artifacts_dir)
    app = create_app(
        repository=test_repo,
        artifact_store=failing_store,
        pipeline=fast_fake_pipeline,
    )

    with TestClient(app) as client:
        res = client.delete("/api/jobs/err-del-job")
        assert res.status_code == 500
        # Invariant: DB row remains!
        assert test_repo.get("err-del-job") is not None


def test_get_job_video_contract(test_client: TestClient, test_repo: SqliteJobRepository) -> None:
    """GET /api/jobs/{id}/video enforces status constraints and returns 500 if no real file."""
    # Unknown -> 404
    assert test_client.get("/api/jobs/unknown-id/video").status_code == 404

    # Queued -> 409
    q_job = make_test_job(job_id="vid-queued", topic="Q", status=JobStatus.QUEUED)
    test_repo.create(q_job)
    assert test_client.get("/api/jobs/vid-queued/video").status_code == 409

    # Running -> 409
    r_job = make_test_job(job_id="vid-running", topic="R", status=JobStatus.RUNNING)
    test_repo.create(r_job)
    assert test_client.get("/api/jobs/vid-running/video").status_code == 409

    # Failed -> 409
    f_job = make_test_job(job_id="vid-failed", topic="F", status=JobStatus.FAILED)
    test_repo.create(f_job)
    assert test_client.get("/api/jobs/vid-failed/video").status_code == 409

    # Fake succeeded with no final artifact -> 500
    s_job = make_test_job(job_id="vid-succeeded", topic="S", status=JobStatus.SUCCEEDED)
    test_repo.create(s_job)
    assert test_client.get("/api/jobs/vid-succeeded/video").status_code == 500

