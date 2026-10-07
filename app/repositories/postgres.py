"""PostgreSQL implementation of the JobRepository for production deployments."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.domain.enums import JobStage, JobStatus
from app.domain.errors import JobError
from app.domain.jobs import Job
from app.domain.lesson import LessonPlan
from app.repositories.base import JobRepository
from app.repositories.errors import DuplicateJobError


def normalize_database_url(database_url: str) -> str:
    """Normalize common hosted-Postgres URI aliases without exposing credentials."""

    value = str(database_url or "").strip()
    if not value:
        raise ValueError("DATABASE_URL must not be empty")

    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    if scheme == "postgres":
        parsed = parsed._replace(scheme="postgresql")
        value = urlunsplit(parsed)
        scheme = "postgresql"
    if scheme not in {"postgresql", "postgresql+psycopg"}:
        raise ValueError(
            "DATABASE_URL must use a PostgreSQL URI (postgresql:// or postgres://)"
        )
    if scheme == "postgresql+psycopg":
        parsed = parsed._replace(scheme="postgresql")
        value = urlunsplit(parsed)
    return value


def _as_jsonb(value: dict | list | None):
    return None if value is None else Jsonb(value)


def _row_to_job(row: dict[str, Any]) -> Job:
    error: JobError | None = None
    if row.get("error_code"):
        stage_value = row.get("error_stage")
        error = JobError(
            code=str(row["error_code"]),
            stage=JobStage(stage_value) if stage_value else None,
            message=str(row.get("error_message") or ""),
            retryable=bool(row.get("error_retryable")),
        )

    stage_value = row.get("stage")
    created_at = row["created_at"]
    updated_at = row["updated_at"]
    if not isinstance(created_at, datetime) or not isinstance(updated_at, datetime):
        raise ValueError("PostgreSQL returned invalid timestamp values")
    if created_at.tzinfo is None or updated_at.tzinfo is None:
        raise ValueError("PostgreSQL timestamps must be timezone-aware")

    return Job(
        id=str(row["id"]),
        topic=str(row["topic"]),
        audience=str(row["audience"]),
        language=str(row["language"]),
        target_duration_seconds=int(row["target_duration_seconds"]),
        display_title=row.get("display_title"),
        note=row.get("note"),
        status=JobStatus(row["status"]),
        stage=JobStage(stage_value) if stage_value else None,
        progress_percent=int(row["progress_percent"]),
        created_at=created_at.astimezone(timezone.utc),
        updated_at=updated_at.astimezone(timezone.utc),
        lesson_plan_json=row.get("lesson_plan_json"),
        artifact_path=row.get("artifact_path"),
        artifact_metadata=row.get("artifact_metadata_json"),
        error=error,
        attempt_count=int(row["attempt_count"]),
    )


class PostgresJobRepository(JobRepository):
    """Durable PostgreSQL-backed repository for production video jobs."""

    def __init__(self, database_url: str, *, connect_timeout_seconds: int = 10):
        self.database_url = normalize_database_url(database_url)
        self.connect_timeout_seconds = int(connect_timeout_seconds)
        self._init_db()

    @contextmanager
    def _connect(self) -> Generator[psycopg.Connection, None, None]:
        with psycopg.connect(
            self.database_url,
            connect_timeout=self.connect_timeout_seconds,
            row_factory=dict_row,
        ) as conn:
            yield conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    audience TEXT NOT NULL,
                    language TEXT NOT NULL,
                    target_duration_seconds INTEGER NOT NULL,
                    display_title TEXT,
                    note TEXT,
                    status TEXT NOT NULL,
                    stage TEXT,
                    progress_percent INTEGER NOT NULL DEFAULT 0
                        CHECK (progress_percent BETWEEN 0 AND 100),
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    lesson_plan_json JSONB,
                    artifact_path TEXT,
                    artifact_metadata_json JSONB,
                    error_code TEXT,
                    error_stage TEXT,
                    error_message TEXT,
                    error_retryable BOOLEAN,
                    attempt_count INTEGER NOT NULL DEFAULT 0
                        CHECK (attempt_count >= 0)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_jobs_created_at
                ON jobs(created_at DESC)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_jobs_status
                ON jobs(status)
                """
            )

    def create(self, job: Job) -> Job:
        error_code = job.error.code if job.error else None
        error_stage = job.error.stage.value if job.error and job.error.stage else None
        error_message = job.error.message if job.error else None
        error_retryable = job.error.retryable if job.error else None

        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO jobs (
                        id, topic, audience, language, target_duration_seconds,
                        display_title, note, status, stage, progress_percent,
                        created_at, updated_at, lesson_plan_json,
                        artifact_path, artifact_metadata_json,
                        error_code, error_stage, error_message, error_retryable,
                        attempt_count
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s, %s, %s,
                        %s
                    )
                    RETURNING *
                    """,
                    (
                        job.id,
                        job.topic,
                        job.audience,
                        job.language,
                        job.target_duration_seconds,
                        job.display_title,
                        job.note,
                        job.status.value,
                        job.stage.value if job.stage else None,
                        job.progress_percent,
                        job.created_at,
                        job.updated_at,
                        _as_jsonb(job.lesson_plan_json),
                        job.artifact_path,
                        _as_jsonb(job.artifact_metadata),
                        error_code,
                        error_stage,
                        error_message,
                        error_retryable,
                        job.attempt_count,
                    ),
                ).fetchone()
        except UniqueViolation as exc:
            raise DuplicateJobError(
                f"Job with ID '{job.id}' already exists"
            ) from exc

        if row is None:
            raise RuntimeError("PostgreSQL INSERT did not return the created job")
        return _row_to_job(row)

    def get(self, job_id: str) -> Job | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE id = %s",
                (job_id,),
            ).fetchone()
        return None if row is None else _row_to_job(row)

    def list(
        self,
        limit: int = 50,
        status: JobStatus | None = None,
    ) -> list[Job]:
        if limit < 1 or limit > 100:
            raise ValueError(f"Limit must be between 1 and 100 (got {limit})")

        with self._connect() as conn:
            if status is None:
                rows = conn.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM jobs
                    WHERE status = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (status.value, limit),
                ).fetchall()
        return [_row_to_job(row) for row in rows]

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
        if progress_percent < 0 or progress_percent > 100:
            raise ValueError("progress_percent must be between 0 and 100")

        error_code = error.code if error else None
        error_stage = error.stage.value if error and error.stage else None
        error_message = error.message if error else None
        error_retryable = error.retryable if error else None

        with self._connect() as conn:
            row = conn.execute(
                """
                UPDATE jobs SET
                    status = %s,
                    stage = %s,
                    progress_percent = %s,
                    updated_at = %s,
                    error_code = %s,
                    error_stage = %s,
                    error_message = %s,
                    error_retryable = %s,
                    attempt_count = attempt_count + %s
                WHERE id = %s
                RETURNING *
                """,
                (
                    status.value,
                    stage.value if stage else None,
                    progress_percent,
                    datetime.now(timezone.utc),
                    error_code,
                    error_stage,
                    error_message,
                    error_retryable,
                    1 if increment_attempt else 0,
                    job_id,
                ),
            ).fetchone()
        return None if row is None else _row_to_job(row)

    def set_plan(
        self,
        job_id: str,
        plan: LessonPlan,
    ) -> Job | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                UPDATE jobs SET
                    lesson_plan_json = %s,
                    updated_at = %s
                WHERE id = %s
                RETURNING *
                """,
                (
                    _as_jsonb(plan.model_dump(mode="json")),
                    datetime.now(timezone.utc),
                    job_id,
                ),
            ).fetchone()
        return None if row is None else _row_to_job(row)

    def set_artifact(
        self,
        job_id: str,
        artifact_path: str,
        metadata: dict,
    ) -> Job | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                UPDATE jobs SET
                    artifact_path = %s,
                    artifact_metadata_json = %s,
                    updated_at = %s
                WHERE id = %s
                RETURNING *
                """,
                (
                    artifact_path,
                    _as_jsonb(metadata),
                    datetime.now(timezone.utc),
                    job_id,
                ),
            ).fetchone()
        return None if row is None else _row_to_job(row)

    def update_user_fields(
        self,
        job_id: str,
        display_title: str | None,
        note: str | None,
    ) -> Job | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                UPDATE jobs SET
                    display_title = %s,
                    note = %s,
                    updated_at = %s
                WHERE id = %s
                RETURNING *
                """,
                (
                    display_title,
                    note,
                    datetime.now(timezone.utc),
                    job_id,
                ),
            ).fetchone()
        return None if row is None else _row_to_job(row)

    def delete(self, job_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "DELETE FROM jobs WHERE id = %s RETURNING id",
                (job_id,),
            ).fetchone()
        return row is not None
