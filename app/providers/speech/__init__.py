"""Speech synthesis provider interfaces and implementations."""

from app.providers.speech.base import (
    SpeechProvider,
    SpeechProviderError,
    SpeechResult,
)
from app.providers.speech.edge import EdgeSpeechProvider

__all__ = [
    "SpeechProvider",
    "SpeechProviderError",
    "SpeechResult",
    "EdgeSpeechProvider",
]
