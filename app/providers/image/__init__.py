"""Image provider abstractions and implementations."""

from app.providers.image.base import ImageGenerationResult, ImageProvider, ImageProviderError
from app.providers.image.gemini import GeminiImageProvider
from app.providers.image.prompts import build_illustration_prompt

__all__ = [
    "ImageGenerationResult",
    "ImageProvider",
    "ImageProviderError",
    "GeminiImageProvider",
    "build_illustration_prompt",
]
