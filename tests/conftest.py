"""Test fixtures for LearnFlow AI test suite."""

from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.enums import JobStatus
from app.domain.jobs import Job
from app.main import create_app
from app.pipeline.fake import FakePipeline
from app.repositories.sqlite import SqliteJobRepository
from app.storage.local import LocalArtifactStore


def make_test_job(
    job_id: str = "test-job-1",
    topic: str = "Test Topic",
    status: JobStatus = JobStatus.QUEUED,
    audience: str = "Beginner",
    language: str = "vi",
    target_duration_seconds: int = 90,
    progress_percent: int = 0,
    attempt_count: int = 0,
    display_title: str | None = None,
    note: str | None = None,
) -> Job:
    """Helper to instantiate valid domain Job for testing."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    return Job(
        id=job_id,
        topic=topic,
        audience=audience,
        language=language,  # type: ignore[arg-type]
        target_duration_seconds=target_duration_seconds,  # type: ignore[arg-type]
        status=status,
        progress_percent=progress_percent,
        attempt_count=attempt_count,
        display_title=display_title,
        note=note,
        created_at=now,
        updated_at=now,
    )



@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Provide a path to a temporary SQLite database file."""
    return tmp_path / "test_learnflow.db"


@pytest.fixture
def temp_artifacts_dir(tmp_path: Path) -> Path:
    """Provide a path to a temporary artifacts directory."""
    d = tmp_path / "test_artifacts"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def test_settings(temp_db_path: Path, temp_artifacts_dir: Path) -> Settings:
    """Create isolated test settings."""
    return Settings(
        db_path=str(temp_db_path),
        artifacts_dir=str(temp_artifacts_dir),
        environment="test",
    )


@pytest.fixture
def test_repo(temp_db_path: Path) -> SqliteJobRepository:
    """Create isolated SQLite repository."""
    return SqliteJobRepository(str(temp_db_path))


@pytest.fixture
def test_artifact_store(temp_artifacts_dir: Path) -> LocalArtifactStore:
    """Create isolated local artifact store."""
    return LocalArtifactStore(temp_artifacts_dir)


@pytest.fixture
def fast_fake_pipeline() -> FakePipeline:
    """Create a FakePipeline with very fast delays for rapid test execution."""
    return FakePipeline(step_delay_seconds=0.001)


@pytest.fixture
def test_client(
    test_settings: Settings,
    test_repo: SqliteJobRepository,
    test_artifact_store: LocalArtifactStore,
    fast_fake_pipeline: FakePipeline,
) -> Generator[TestClient, None, None]:
    """Provide a TestClient with lifespan context and isolated dependencies."""
    app = create_app(
        settings=test_settings,
        repository=test_repo,
        artifact_store=test_artifact_store,
        pipeline=fast_fake_pipeline,
    )
    with TestClient(app) as client:
        yield client
