"""Repository abstractions and implementations for LearnFlow AI."""

from app.repositories.base import JobRepository
from app.repositories.errors import DuplicateJobError
from app.repositories.factory import create_job_repository
from app.repositories.postgres import PostgresJobRepository
from app.repositories.sqlite import SqliteJobRepository

__all__ = [
    "JobRepository",
    "SqliteJobRepository",
    "PostgresJobRepository",
    "DuplicateJobError",
    "create_job_repository",
]
