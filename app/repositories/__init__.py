"""Repository abstractions and implementations for LearnFlow AI."""

from app.repositories.base import JobRepository
from app.repositories.sqlite import DuplicateJobError, SqliteJobRepository

__all__ = [
    "JobRepository",
    "SqliteJobRepository",
    "DuplicateJobError",
]
