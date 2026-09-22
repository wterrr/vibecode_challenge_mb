"""Abstract base and contract definitions for ImageProvider."""

from abc import ABC, abstractmethod
from pathlib import Path
from pydantic import BaseModel, Field


class ImageGenerationResult(BaseModel):
    """Normalized metadata for a successfully generated local image."""

    path: str = Field(description="Absolute or relative filesystem path to the validated image")
    provider: str = Field(description="Name of the image provider (e.g., 'gemini', 'fake')")
    model: str = Field(description="Model identifier used for generation")
    width: int = Field(ge=1, description="Width in pixels")
    height: int = Field(ge=1, description="Height in pixels")


class ImageProviderError(RuntimeError):
    """Sanitized structured error emitted across the image provider boundary."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        retryable: bool,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable

    def __str__(self) -> str:
        return f"[{self.code}] {self.message} (retryable={self.retryable})"


class ImageProvider(ABC):
    """Abstract interface for image generation providers."""

    @abstractmethod
    async def generate(
        self,
        *,
        prompt: str,
        output_path: Path,
    ) -> ImageGenerationResult:
        """Generate an image from prompt and atomically save validated RGB PNG to output_path.

        Args:
            prompt: Visual description and composition directives.
            output_path: Target filesystem path where the final image must be written.

        Returns:
            ImageGenerationResult with validated dimensions and metadata.

        Raises:
            ImageProviderError: If generation fails, times out, or yields invalid bytes.
        """
        ...
