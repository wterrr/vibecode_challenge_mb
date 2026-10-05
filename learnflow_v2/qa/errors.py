"""Structured QA and optional-critic errors for LearnFlow V2."""

from learnflow_v2.core.errors import LearnFlowV2Error


class DeterministicQAError(LearnFlowV2Error):
    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        super().__init__(code, message, details)


class QAInvalidInputError(DeterministicQAError):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__("QA_INVALID_INPUT", message, details)


class CriticProviderError(DeterministicQAError):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__("CRITIC_PROVIDER_ERROR", message, details)


class CriticProviderUnavailableError(CriticProviderError):
    pass


class CriticProviderQuotaError(CriticProviderError):
    pass
