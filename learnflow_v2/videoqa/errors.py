"""Structured errors for LearnFlow V2 CP2.14 video-level critique."""

from __future__ import annotations

from typing import Any

from learnflow_v2.core.errors import LearnFlowV2Error


class VideoCriticError(LearnFlowV2Error):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, details)


class VideoCriticInvalidInputError(VideoCriticError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("VIDEO_CRITIC_INVALID_INPUT", message, details)


class VideoCriticProviderError(VideoCriticError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("VIDEO_CRITIC_PROVIDER_ERROR", message, details)


class VideoCriticProviderUnavailableError(VideoCriticProviderError):
    pass


class VideoCriticProviderQuotaError(VideoCriticProviderError):
    pass
