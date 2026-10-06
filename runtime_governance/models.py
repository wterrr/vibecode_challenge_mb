"""Typed runtime-governance contracts."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from agent_contracts import (
    AgentContractError,
    BudgetLedger,
    BudgetUsage,
    ContractModel,
)
from agent_contracts.base import finite_nonnegative, normalize_id, normalize_text


def _tupleize(value: Any):
    return tuple(value) if isinstance(value, list) else value


class SpendCategory(str, Enum):
    LLM = "llm"
    VLM = "vlm"
    IMAGE = "image"
    TTS = "tts"
    OTHER = "other"


class BudgetCharge(ContractModel):
    """Conservative charge consumed before a governed operation starts."""

    charge_id: str
    category: SpendCategory = SpendCategory.OTHER
    amount_usd: float = Field(default=0.0, ge=0.0)
    usage: BudgetUsage = Field(default_factory=BudgetUsage)
    reason: str = Field(..., min_length=1)

    @field_validator("charge_id")
    @classmethod
    def _charge_id(cls, value: str) -> str:
        return normalize_id(value, field_name="charge_id")

    @field_validator("amount_usd", mode="before")
    @classmethod
    def _amount(cls, value: Any) -> float:
        return finite_nonnegative(value, field_name="amount_usd")

    @field_validator("reason")
    @classmethod
    def _reason(cls, value: str) -> str:
        return normalize_text(value, field_name="reason")


class GovernanceState(ContractModel):
    """Operator-owned governance state. Model tool arguments cannot mutate it."""

    state_id: str
    budget: BudgetLedger | None = None
    publication_authorized: bool = False
    publication_tools: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("state_id")
    @classmethod
    def _state_id(cls, value: str) -> str:
        return normalize_id(value, field_name="state_id")

    @field_validator("publication_authorized", mode="before")
    @classmethod
    def _strict_bool(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise AgentContractError("publication_authorized must be boolean")
        return value

    @field_validator("publication_tools", mode="before")
    @classmethod
    def _tools_tuple(cls, value: Any):
        return _tupleize(value)

    @field_validator("publication_tools")
    @classmethod
    def _tools(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(
            normalize_id(item, field_name="publication_tools") for item in value
        )
        if len(normalized) != len(set(normalized)):
            raise AgentContractError("publication_tools must be unique")
        return tuple(sorted(normalized))
