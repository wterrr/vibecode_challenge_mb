"""Base interfaces, data structures, and errors for speech synthesis providers."""

from abc import ABC, abstractmethod
from pathlib import Path
from pydantic import BaseModel, Field
from app.domain.timeline import SubtitleCue


class SpeechResult(BaseModel):
    """Result of synthesizing narration audio for a single scene."""

    path: str
    provider: str
    duration_seconds: float | None = None
    subtitle_cues: list[SubtitleCue] = Field(default_factory=list)


class SpeechProviderError(RuntimeError):
    """Raised when speech synthesis encounters a structured, safe failure."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class SpeechProvider(ABC):
    """Abstract interface for synthesizing scene narration speech."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        output_path: Path,
        language: str,
    ) -> SpeechResult:
        """Synthesize spoken audio for the given text and save to output_path."""
        ...
