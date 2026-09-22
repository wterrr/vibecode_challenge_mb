"""Domain job model representing a video generation request and state."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator
from app.domain.enums import JobStage, JobStatus
from app.domain.errors import JobError


class Job(BaseModel):
    """Represents the complete durable state of a learning video job."""

    id: str = Field(min_length=1)

    topic: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    language: Literal["vi", "en"]
    target_duration_seconds: Literal[60, 90, 120]

    display_title: str | None = None
    note: str | None = None

    status: JobStatus = JobStatus.QUEUED
    stage: JobStage | None = None

    progress_percent: int = Field(default=0, ge=0, le=100)

    created_at: datetime
    updated_at: datetime

    lesson_plan_json: dict | None = None

    artifact_path: str | None = None
    artifact_metadata: dict | None = None

    error: JobError | None = None

    attempt_count: int = Field(default=0, ge=0)

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_timezone_aware(cls, dt: datetime) -> datetime:
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            raise ValueError("Datetime must be timezone-aware (UTC)")
        return dt

    @field_validator("topic", "audience", mode="before")
    @classmethod
    def validate_non_blank(cls, value: object) -> object:
        if isinstance(value, str):
            trimmed = value.strip()
            if not trimmed:
                raise ValueError("Field cannot be empty or blank")
            return trimmed
        return value
