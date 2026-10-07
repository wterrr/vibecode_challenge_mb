"""Repository backend selection for local/test and production deployments."""

from __future__ import annotations

from app.config import Settings
from app.repositories.base import JobRepository
from app.repositories.postgres import PostgresJobRepository
from app.repositories.sqlite import SqliteJobRepository


def create_job_repository(settings: Settings) -> JobRepository:
    """Create the configured repository backend.

    Production is PostgreSQL-only. SQLite remains an explicit local/test fallback
    so the existing fast unit-test suite does not require a database service.
    """

    database_url = settings.database_url.strip()
    if database_url:
        return PostgresJobRepository(database_url)

    environment = settings.environment.strip().lower()
    if environment in {"production", "prod"}:
        raise RuntimeError(
            "DATABASE_URL is required in production; SQLite is not a supported "
            "production persistence backend."
        )

    return SqliteJobRepository(settings.db_path)
