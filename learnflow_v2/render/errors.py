"""Structured errors for LearnFlow V2 deterministic renderer."""

from learnflow_v2.core.errors import LearnFlowV2Error


class RenderError(LearnFlowV2Error):
    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        super().__init__(code, message, details)


class RenderInvalidInputError(RenderError):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__("RENDER_INVALID_INPUT", message, details)


class RenderBackendError(RenderError):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__("RENDER_BACKEND_ERROR", message, details)
