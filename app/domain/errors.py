"""Domain error models for LearnFlow AI."""

from pydantic import BaseModel, Field, field_validator
from app.domain.enums import JobStage


class JobError(BaseModel):
    """Structured job error representation."""

    code: str = Field(min_length=1)
    stage: JobStage | None = None
    message: str = Field(min_length=1)
    retryable: bool = False

    @field_validator("code", "message")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Field cannot be blank")
        return trimmed


class PipelineExecutionError(RuntimeError):
    """Raised when pipeline processing fails in a structured way."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        stage: JobStage | None = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.stage = stage
        self.retryable = retryable
