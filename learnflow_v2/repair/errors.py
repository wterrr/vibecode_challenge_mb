"""Structured errors for LearnFlow V2 CP2.13 repair and invalidation."""

from __future__ import annotations

from typing import Any

from learnflow_v2.core.errors import LearnFlowV2Error


class RepairError(LearnFlowV2Error):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, details)


class RepairInvalidInputError(RepairError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("REPAIR_INVALID_INPUT", message, details)


class RepairRetryLimitError(RepairError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("REPAIR_RETRY_LIMIT", message, details)


class RepairDependencyError(RepairError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("REPAIR_DEPENDENCY_ERROR", message, details)


class RepairNonDeterminismError(RepairError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("REPAIR_NON_DETERMINISM", message, details)
