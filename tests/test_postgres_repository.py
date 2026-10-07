"""PostgreSQL repository integration tests.

These tests are skipped in the ordinary local suite unless TEST_POSTGRES_DATABASE_URL
is configured. The dedicated GitHub Actions workflow supplies a real postgres:16 service.
"""

from __future__ import annotations

import os

import psycopg
import pytest

from app.config import Settings
from app.domain.enums import JobStage, JobStatus
from app.repositories.errors import DuplicateJobError
from app.repositories.factory import create_job_repository
from app.repositories.postgres import PostgresJobRepository, normalize_database_url
from tests.conftest import make_test_job


TEST_DATABASE_URL = os.environ.get("TEST_POSTGRES_DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_POSTGRES_DATABASE_URL is not configured",
)


@pytest.fixture
def postgres_repo():
    repo = PostgresJobRepository(TEST_DATABASE_URL)
    with psycopg.connect(repo.database_url) as conn:
        conn.execute("TRUNCATE TABLE jobs")
    yield repo
    with psycopg.connect(repo.database_url) as conn:
        conn.execute("TRUNCATE TABLE jobs")


def test_normalizes_hosted_postgres_uri_alias():
    assert normalize_database_url("postgres://u:p@db.example/test") == (
        "postgresql://u:p@db.example/test"
    )


def test_postgres_crud_lifecycle_and_jsonb_round_trip(postgres_repo):
    job = make_test_job(
        job_id="postgres-job-1",
        topic="PostgreSQL persistence",
        status=JobStatus.QUEUED,
    )
    created = postgres_repo.create(job)
    assert created.id == job.id
    assert created.created_at.tzinfo is not None

    loaded = postgres_repo.get(job.id)
    assert loaded is not None
    assert loaded.topic == "PostgreSQL persistence"

    running = postgres_repo.update_state(
        job.id,
        status=JobStatus.RUNNING,
        stage=JobStage.PLANNING,
        progress_percent=25,
        increment_attempt=True,
    )
    assert running is not None
    assert running.status == JobStatus.RUNNING
    assert running.stage == JobStage.PLANNING
    assert running.attempt_count == 1

    artifact = postgres_repo.set_artifact(
        job.id,
        "artifacts/postgres-job-1/final.mp4",
        {
            "duration_seconds": 61.5,
            "streams": {"video": "h264", "audio": "aac"},
            "tags": ["production", "postgres"],
        },
    )
    assert artifact is not None
    assert artifact.artifact_metadata == {
        "duration_seconds": 61.5,
        "streams": {"video": "h264", "audio": "aac"},
        "tags": ["production", "postgres"],
    }

    patched = postgres_repo.update_user_fields(
        job.id,
        display_title="Persisted title",
        note="Stored in PostgreSQL",
    )
    assert patched is not None
    assert patched.display_title == "Persisted title"
    assert patched.note == "Stored in PostgreSQL"

    rows = postgres_repo.list(limit=10, status=JobStatus.RUNNING)
    assert [row.id for row in rows] == [job.id]

    assert postgres_repo.delete(job.id) is True
    assert postgres_repo.get(job.id) is None
    assert postgres_repo.delete(job.id) is False


def test_postgres_duplicate_id_uses_shared_repository_error(postgres_repo):
    job = make_test_job(job_id="duplicate-postgres", topic="Duplicate")
    postgres_repo.create(job)
    with pytest.raises(DuplicateJobError):
        postgres_repo.create(job)


def test_production_factory_uses_postgres(postgres_repo):
    settings = Settings(
        environment="production",
        database_url=TEST_DATABASE_URL,
    )
    selected = create_job_repository(settings)
    assert isinstance(selected, PostgresJobRepository)


def test_production_factory_refuses_sqlite_fallback():
    with pytest.raises(RuntimeError, match="DATABASE_URL is required in production"):
        create_job_repository(
            Settings(
                environment="production",
                database_url="",
                db_path="must-not-be-used.db",
            )
        )
