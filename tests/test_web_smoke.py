"""Web UI smoke tests for HTML pages."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.domain.enums import JobStatus
from app.domain.jobs import Job
from app.repositories.sqlite import SqliteJobRepository
from tests.conftest import make_test_job


def test_index_page(test_client: TestClient) -> None:
    """GET / renders landing page with product branding, chips, and CTA."""
    response = test_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "LearnFlow" in html
    assert "AI Learning Video Studio" in html
    assert "TCP three-way handshake" in html
    assert "Tạo video" in html


def test_create_page(test_client: TestClient) -> None:
    """GET /create renders create form with topic, audience, and duration inputs."""
    response = test_client.get("/create")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "Tạo video bài giảng mới" in html
    assert 'name="topic"' in html
    assert 'name="audience"' in html
    assert 'name="language"' in html
    assert 'name="target_duration_seconds"' in html


def test_create_page_with_prefill_topic(test_client: TestClient) -> None:
    """GET /create?topic=... pre-fills the topic textarea."""
    response = test_client.get("/create?topic=Photosynthesis+Deep+Dive")
    assert response.status_code == 200
    assert "Photosynthesis Deep Dive" in response.text


def test_library_page(test_client: TestClient, test_repo: SqliteJobRepository) -> None:
    """GET /library lists existing jobs or shows empty state."""
    # Initially empty
    res_empty = test_client.get("/library")
    assert res_empty.status_code == 200
    assert "Bạn chưa tạo video nào." in res_empty.text

    # With a job
    job = make_test_job(
        job_id="web-smoke-job-1",
        topic="Web Development Fundamentals",
        status=JobStatus.SUCCEEDED,
        progress_percent=100,
    )
    test_repo.create(job)

    res_with_job = test_client.get("/library")
    assert res_with_job.status_code == 200
    assert "Web Development Fundamentals" in res_with_job.text
    assert "succeeded" in res_with_job.text


def test_job_detail_page_known_and_unknown(test_client: TestClient, test_repo: SqliteJobRepository) -> None:
    """GET /jobs/{id} renders detail page for known job and 404 error page for unknown."""
    job = make_test_job(
        job_id="web-detail-known",
        topic="Machine Learning Basics",
        status=JobStatus.QUEUED,
        progress_percent=0,
    )
    test_repo.create(job)

    # Known job
    res_known = test_client.get("/jobs/web-detail-known")
    assert res_known.status_code == 200
    assert "Machine Learning Basics" in res_known.text
    assert "web-detail-known" in res_known.text
    assert "queued" in res_known.text

    # Unknown job -> returns 404 status with friendly error page
    res_unknown = test_client.get("/jobs/non-existent-web-id")
    assert res_unknown.status_code == 404
    assert "Không tìm thấy" in res_unknown.text

