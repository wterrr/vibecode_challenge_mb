"""SQLite implementation of the JobRepository."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator
from app.domain.enums import JobStage, JobStatus
from app.domain.errors import JobError
from app.domain.jobs import Job
from app.domain.lesson import LessonPlan
from app.repositories.base import JobRepository


class DuplicateJobError(Exception):
    """Raised when attempting to insert a job with an existing ID."""


def _dt_to_str(value: datetime) -> str:
    """Format timezone-aware datetime to ISO 8601 UTC string."""
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(f"Datetime {value} must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat()


def _dt_from_str(value: str) -> datetime:
    """Parse ISO 8601 string into timezone-aware datetime."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError(f"Persisted datetime string '{value}' missing timezone info")
    return dt


def _json_dumps(value: dict | list | None) -> str | None:
    """Serialize JSON safely with UTF-8 support."""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: str | None) -> dict | None:
    """Deserialize JSON string or return None."""
    if value is None or not value.strip():
        return None
    return json.loads(value)


def _row_to_job(row: sqlite3.Row) -> Job:
    """Map a SQLite row to a typed Job domain instance."""
    error: JobError | None = None
    if row["error_code"]:
        stage_val = row["error_stage"]
        error = JobError(
            code=row["error_code"],
            stage=JobStage(stage_val) if stage_val else None,
            message=row["error_message"] or "",
            retryable=bool(row["error_retryable"]),
        )

    stage_col = row["stage"]
    stage = JobStage(stage_col) if stage_col else None

    return Job(
        id=row["id"],
        topic=row["topic"],
        audience=row["audience"],
        language=row["language"],
        target_duration_seconds=row["target_duration_seconds"],
        display_title=row["display_title"],
        note=row["note"],
        status=JobStatus(row["status"]),
        stage=stage,
        progress_percent=row["progress_percent"],
        created_at=_dt_from_str(row["created_at"]),
        updated_at=_dt_from_str(row["updated_at"]),
        lesson_plan_json=_json_loads(row["lesson_plan_json"]),
        artifact_path=row["artifact_path"],
        artifact_metadata=_json_loads(row["artifact_metadata_json"]),
        error=error,
        attempt_count=row["attempt_count"],
    )


class SqliteJobRepository(JobRepository):
    """Durable SQLite storage for video generation jobs."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        # Ensure parent directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Open a dedicated short-lived SQLite connection with safety pragmas."""
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA synchronous=NORMAL")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create tables and indexes with WAL mode enabled."""
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
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
                    progress_percent INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    lesson_plan_json TEXT,
                    artifact_path TEXT,
                    artifact_metadata_json TEXT,
                    error_code TEXT,
                    error_stage TEXT,
                    error_message TEXT,
                    error_retryable INTEGER,
                    attempt_count INTEGER NOT NULL DEFAULT 0
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
        error_retryable = 1 if job.error and job.error.retryable else (0 if job.error else None)

        sql = """
            INSERT INTO jobs (
                id, topic, audience, language, target_duration_seconds,
                display_title, note, status, stage, progress_percent,
                created_at, updated_at, lesson_plan_json,
                artifact_path, artifact_metadata_json,
                error_code, error_stage, error_message, error_retryable,
                attempt_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
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
            _dt_to_str(job.created_at),
            _dt_to_str(job.updated_at),
            _json_dumps(job.lesson_plan_json),
            job.artifact_path,
            _json_dumps(job.artifact_metadata),
            error_code,
            error_stage,
            error_message,
            error_retryable,
            job.attempt_count,
        )

        with self._connect() as conn:
            try:
                conn.execute(sql, params)
            except sqlite3.IntegrityError as err:
                raise DuplicateJobError(
                    f"Job with ID '{job.id}' already exists"
                ) from err

        return self.get(job.id) or job

    def get(self, job_id: str) -> Job | None:
        with self._connect() as conn:
            cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            return _row_to_job(row)

    def list(
        self,
        limit: int = 50,
        status: JobStatus | None = None,
    ) -> list[Job]:
        if limit < 1 or limit > 100:
            raise ValueError(f"Limit must be between 1 and 100 (got {limit})")

        with self._connect() as conn:
            if status is not None:
                sql = "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?"
                cursor = conn.execute(sql, (status.value, limit))
            else:
                sql = "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?"
                cursor = conn.execute(sql, (limit,))
            rows = cursor.fetchall()
            return [_row_to_job(r) for r in rows]

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

        now_str = _dt_to_str(datetime.now(timezone.utc))
        error_code = error.code if error else None
        error_stage = error.stage.value if error and error.stage else None
        error_message = error.message if error else None
        error_retryable = 1 if error and error.retryable else (0 if error else None)

        with self._connect() as conn:
            # Check existence
            cursor = conn.execute("SELECT attempt_count FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if row is None:
                return None

            attempt_count = row["attempt_count"]
            if increment_attempt:
                attempt_count += 1

            sql = """
                UPDATE jobs SET
                    status = ?,
                    stage = ?,
                    progress_percent = ?,
                    updated_at = ?,
                    error_code = ?,
                    error_stage = ?,
                    error_message = ?,
                    error_retryable = ?,
                    attempt_count = ?
                WHERE id = ?
            """
            conn.execute(
                sql,
                (
                    status.value,
                    stage.value if stage else None,
                    progress_percent,
                    now_str,
                    error_code,
                    error_stage,
                    error_message,
                    error_retryable,
                    attempt_count,
                    job_id,
                ),
            )

        return self.get(job_id)

    def set_plan(
        self,
        job_id: str,
        plan: LessonPlan,
    ) -> Job | None:
        plan_dict = plan.model_dump(mode="json")
        now_str = _dt_to_str(datetime.now(timezone.utc))

        with self._connect() as conn:
            cursor = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
            if cursor.fetchone() is None:
                return None

            sql = "UPDATE jobs SET lesson_plan_json = ?, updated_at = ? WHERE id = ?"
            conn.execute(sql, (_json_dumps(plan_dict), now_str, job_id))

        return self.get(job_id)

    def set_artifact(
        self,
        job_id: str,
        artifact_path: str,
        metadata: dict,
    ) -> Job | None:
        now_str = _dt_to_str(datetime.now(timezone.utc))

        with self._connect() as conn:
            cursor = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
            if cursor.fetchone() is None:
                return None

            sql = """
                UPDATE jobs SET
                    artifact_path = ?,
                    artifact_metadata_json = ?,
                    updated_at = ?
                WHERE id = ?
            """
            conn.execute(sql, (artifact_path, _json_dumps(metadata), now_str, job_id))

        return self.get(job_id)

    def update_user_fields(
        self,
        job_id: str,
        display_title: str | None,
        note: str | None,
    ) -> Job | None:
        now_str = _dt_to_str(datetime.now(timezone.utc))

        with self._connect() as conn:
            cursor = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
            if cursor.fetchone() is None:
                return None

            sql = "UPDATE jobs SET display_title = ?, note = ?, updated_at = ? WHERE id = ?"
            conn.execute(sql, (display_title, note, now_str, job_id))

        return self.get(job_id)

    def delete(self, job_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            return cursor.rowcount > 0
