"""Pydantic request and response schemas for API endpoints."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator

from app.domain.enums import JobStage, JobStatus
from app.domain.errors import JobError
from app.domain.jobs import Job


class CreateJobResponse(BaseModel):
    """Response returned upon accepting a new job creation request."""

    job_id: str
    status: JobStatus
    status_url: str
    page_url: str


class UpdateJobRequest(BaseModel):
    """User-modifiable fields for an existing job."""

    display_title: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("display_title", "note", mode="before")
    @classmethod
    def normalize_optional_str(cls, value: object) -> object:
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed if trimmed else None
        return value


class JobResponse(BaseModel):
    """Detailed job status and metadata response."""

    id: str
    job_id: str
    topic: str
    audience: str
    language: str
    target_duration_seconds: int
    display_title: str | None = None
    note: str | None = None
    status: JobStatus
    stage: JobStage | None = None
    progress_percent: int
    created_at: datetime
    updated_at: datetime
    attempt_count: int
    error: JobError | None = None
    video_url: str | None = None
    page_url: str
    status_url: str
    lesson_plan_summary: str | None = None

    @classmethod
    def from_job(cls, job: Job, video_url: str | None = None) -> "JobResponse":
        """Construct JobResponse from domain Job model."""
        summary = None
        if job.lesson_plan_json and isinstance(job.lesson_plan_json, dict):
            summary = job.lesson_plan_json.get("summary")

        return cls(
            id=job.id,
            job_id=job.id,
            topic=job.topic,
            audience=job.audience,
            language=job.language,
            target_duration_seconds=job.target_duration_seconds,
            display_title=job.display_title,
            note=job.note,
            status=job.status,
            stage=job.stage,
            progress_percent=job.progress_percent,
            created_at=job.created_at,
            updated_at=job.updated_at,
            attempt_count=job.attempt_count,
            error=job.error,
            video_url=video_url,
            page_url=f"/jobs/{job.id}",
            status_url=f"/api/jobs/{job.id}",
            lesson_plan_summary=summary,
        )
