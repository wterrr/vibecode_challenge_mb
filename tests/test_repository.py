"""Tests for SQLite repository implementation."""

import sqlite3
from datetime import datetime, timezone, timedelta
import pytest

from app.domain.enums import JobStage, JobStatus, VisualIntent
from app.domain.errors import JobError
from app.domain.jobs import Job
from app.domain.lesson import (
    ConceptCardSpec,
    LessonPlan,
    ScenePlan,
)
from app.repositories.sqlite import DuplicateJobError, SqliteJobRepository


def _make_sample_job(
    job_id: str = "job_1",
    status: JobStatus = JobStatus.QUEUED,
    created_at: datetime | None = None,
) -> Job:
    now = created_at or datetime.now(timezone.utc)
    return Job(
        id=job_id,
        topic="How does photosynthesis work?",
        audience="High school biology",
        language="vi",
        target_duration_seconds=90,
        display_title="Photosynthesis Basics",
        note="User note",
        status=status,
        progress_percent=0,
        created_at=now,
        updated_at=now,
    )


def test_repository_init_creates_table_and_indexes(tmp_path):
    db_file = tmp_path / "test.db"
    SqliteJobRepository(db_file)

    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()

    # Verify table
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
    )
    assert cursor.fetchone() is not None

    # Verify indexes
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name IN ('idx_jobs_created_at', 'idx_jobs_status')"
    )
    indexes = {row[0] for row in cursor.fetchall()}
    assert "idx_jobs_created_at" in indexes
    assert "idx_jobs_status" in indexes
    conn.close()


def test_connection_pragmas_on_subsequent_connections(tmp_path):
    repo = SqliteJobRepository(tmp_path / "test.db")
    # Perform an operation first
    repo.create(_make_sample_job("job_p1"))

    # Test connection opened via repository's connection mechanism
    with repo._connect() as conn:
        # Check synchronous mode: 1 = NORMAL (not 2 = FULL)
        cur = conn.execute("PRAGMA synchronous")
        assert cur.fetchone()[0] == 1

        # Check foreign keys: 1 = ON
        cur = conn.execute("PRAGMA foreign_keys")
        assert cur.fetchone()[0] == 1

        # Check busy timeout: 5000 ms
        cur = conn.execute("PRAGMA busy_timeout")
        assert cur.fetchone()[0] == 5000

        # Check journal mode: wal
        cur = conn.execute("PRAGMA journal_mode")
        assert cur.fetchone()[0].lower() == "wal"

    # Verify a subsequent connection also retains synchronous=1
    with repo._connect() as conn2:
        assert conn2.execute("PRAGMA synchronous").fetchone()[0] == 1
        assert conn2.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn2.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        assert conn2.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


def test_create_and_get_round_trip(tmp_path):
    repo = SqliteJobRepository(tmp_path / "test.db")
    job = _make_sample_job("job_abc")

    created = repo.create(job)
    assert created.id == "job_abc"

    retrieved = repo.get("job_abc")
    assert retrieved is not None
    assert retrieved.id == "job_abc"
    assert retrieved.topic == job.topic
    assert retrieved.audience == job.audience
    assert retrieved.language == job.language
    assert retrieved.target_duration_seconds == job.target_duration_seconds
    assert retrieved.display_title == job.display_title
    assert retrieved.note == job.note
    assert retrieved.status == JobStatus.QUEUED
    assert retrieved.stage is None
    assert retrieved.progress_percent == 0
    assert retrieved.created_at == job.created_at
    assert retrieved.updated_at == job.updated_at
    assert retrieved.error is None
    assert retrieved.attempt_count == 0


def test_get_nonexistent_returns_none(tmp_path):
    repo = SqliteJobRepository(tmp_path / "test.db")
    assert repo.get("unknown_id") is None


def test_duplicate_id_raises_error(tmp_path):
    repo = SqliteJobRepository(tmp_path / "test.db")
    job = _make_sample_job("job_same")
    repo.create(job)

    with pytest.raises(DuplicateJobError, match="already exists"):
        repo.create(job)


def test_list_ordering_newest_first(tmp_path):
    repo = SqliteJobRepository(tmp_path / "test.db")
    base_time = datetime.now(timezone.utc)

    j1 = _make_sample_job("job_1", created_at=base_time - timedelta(minutes=10))
    j2 = _make_sample_job("job_2", created_at=base_time)
    j3 = _make_sample_job("job_3", created_at=base_time - timedelta(minutes=5))

    repo.create(j1)
    repo.create(j2)
    repo.create(j3)

    jobs = repo.list(limit=50)
    assert [j.id for j in jobs] == ["job_2", "job_3", "job_1"]


def test_list_status_filter(tmp_path):
    repo = SqliteJobRepository(tmp_path / "test.db")
    repo.create(_make_sample_job("job_q1", status=JobStatus.QUEUED))
    repo.create(_make_sample_job("job_r1", status=JobStatus.RUNNING))
    repo.create(_make_sample_job("job_q2", status=JobStatus.QUEUED))

    queued = repo.list(status=JobStatus.QUEUED)
    assert len(queued) == 2
    assert {j.id for j in queued} == {"job_q1", "job_q2"}

    running = repo.list(status=JobStatus.RUNNING)
    assert len(running) == 1
    assert running[0].id == "job_r1"


def test_list_limit_validation(tmp_path):
    repo = SqliteJobRepository(tmp_path / "test.db")
    with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
        repo.list(limit=0)

    with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
        repo.list(limit=101)


def test_update_state_and_attempt_increment(tmp_path):
    repo = SqliteJobRepository(tmp_path / "test.db")
    job = repo.create(_make_sample_job("job_trans"))

    # Initial state
    assert job.attempt_count == 0
    assert job.status == JobStatus.QUEUED

    # Update to running, stage planning, increment attempt = True
    updated = repo.update_state(
        "job_trans",
        status=JobStatus.RUNNING,
        stage=JobStage.PLANNING,
        progress_percent=15,
        increment_attempt=True,
    )
    assert updated is not None
    assert updated.status == JobStatus.RUNNING
    assert updated.stage == JobStage.PLANNING
    assert updated.progress_percent == 15
    assert updated.attempt_count == 1
    assert updated.updated_at >= job.updated_at

    # Update again without incrementing attempt
    updated2 = repo.update_state(
        "job_trans",
        status=JobStatus.RUNNING,
        stage=JobStage.AUDIO,
        progress_percent=40,
        increment_attempt=False,
    )
    assert updated2 is not None
    assert updated2.stage == JobStage.AUDIO
    assert updated2.progress_percent == 40
    assert updated2.attempt_count == 1  # unchanged


def test_error_round_trip_and_clear(tmp_path):
    repo = SqliteJobRepository(tmp_path / "test.db")
    repo.create(_make_sample_job("job_err"))

    # Set error
    err = JobError(
        code="AUDIO_TTS_FAILED",
        stage=JobStage.AUDIO,
        message="Edge-TTS connection timeout",
        retryable=True,
    )
    failed = repo.update_state(
        "job_err",
        status=JobStatus.FAILED,
        stage=JobStage.AUDIO,
        progress_percent=30,
        error=err,
    )
    assert failed is not None
    assert failed.error is not None
    assert failed.error.code == "AUDIO_TTS_FAILED"
    assert failed.error.stage == JobStage.AUDIO
    assert failed.error.message == "Edge-TTS connection timeout"
    assert failed.error.retryable is True

    # Clear error by passing error=None
    recovered = repo.update_state(
        "job_err",
        status=JobStatus.RUNNING,
        stage=JobStage.AUDIO,
        progress_percent=35,
        error=None,
    )
    assert recovered is not None
    assert recovered.error is None


def test_set_plan_round_trip(tmp_path):
    repo = SqliteJobRepository(tmp_path / "test.db")
    repo.create(_make_sample_job("job_plan"))

    plan = LessonPlan(
        title="Photosynthesis",
        topic="Biology",
        audience="High School",
        language="vi",
        learning_objective="Understand light reactions",
        summary="Summary of process",
        scenes=[
            ScenePlan(
                scene_id=f"s0{i}_step",
                title=f"Step {i}",
                concept="Chloroplast",
                narration="Light hits chlorophyll.",
                key_points=["Photon absorption"],
                visual_intent=VisualIntent.CONCEPT_CARD,
                visual_spec=ConceptCardSpec(heading="Chloroplast", points=["Thylakoid"]),
            )
            for i in range(1, 4)
        ],
    )

    updated = repo.set_plan("job_plan", plan)
    assert updated is not None
    assert updated.lesson_plan_json is not None
    assert updated.lesson_plan_json["title"] == "Photosynthesis"
    assert len(updated.lesson_plan_json["scenes"]) == 3
    # Status must not change
    assert updated.status == JobStatus.QUEUED


def test_set_artifact_metadata(tmp_path):
    repo = SqliteJobRepository(tmp_path / "test.db")
    repo.create(_make_sample_job("job_art"))

    metadata = {
        "duration_seconds": 90.2,
        "width": 1280,
        "height": 720,
    }
    updated = repo.set_artifact("job_art", "/artifacts/job_art/final.mp4", metadata)
    assert updated is not None
    assert updated.artifact_path == "/artifacts/job_art/final.mp4"
    assert updated.artifact_metadata == metadata
    assert updated.status == JobStatus.QUEUED


def test_update_user_fields(tmp_path):
    repo = SqliteJobRepository(tmp_path / "test.db")
    repo.create(_make_sample_job("job_user"))

    # Update title and note
    updated = repo.update_user_fields("job_user", "Custom Title", "My custom notes")
    assert updated is not None
    assert updated.display_title == "Custom Title"
    assert updated.note == "My custom notes"

    # Clear title and note
    cleared = repo.update_user_fields("job_user", None, None)
    assert cleared is not None
    assert cleared.display_title is None
    assert cleared.note is None


def test_delete_job(tmp_path):
    repo = SqliteJobRepository(tmp_path / "test.db")
    repo.create(_make_sample_job("job_del"))

    assert repo.delete("job_del") is True
    assert repo.get("job_del") is None
    # Second delete returns False
    assert repo.delete("job_del") is False
