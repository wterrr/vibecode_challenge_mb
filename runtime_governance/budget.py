"""Fail-closed pre-authorization for governed LearnFlow runtime operations."""

from __future__ import annotations

from threading import RLock

from pydantic import ValidationError

from agent_contracts import (
    AgentContractError,
    BudgetLedger,
    BudgetSpend,
    BudgetUsage,
)

from .models import BudgetCharge


class BudgetExceededError(AgentContractError):
    """Raised before an operation when its conservative charge cannot fit."""


_COUNTER_FIELDS = (
    "subagent_calls",
    "vlm_repairs",
    "image_generations",
    "tool_calls",
    "provider_attempts",
    "retries",
)


def _add_usage(current: BudgetUsage, delta: BudgetUsage) -> dict[str, int]:
    return {
        name: int(getattr(current, name)) + int(getattr(delta, name))
        for name in _COUNTER_FIELDS
    }


def apply_budget_charge(ledger: BudgetLedger, charge: BudgetCharge) -> BudgetLedger:
    """Return a newly validated ledger or raise before the operation begins.

    Charges are conservative reservations consumed up front. Numeric USD
    ceilings are enforced when configured; a ledger with max_usd=None records
    spend telemetry without imposing a money ceiling. Usage counters remain
    fail-closed hard limits in either mode.
    """

    ledger = BudgetLedger.model_validate(ledger.model_dump(mode="json", exclude_computed_fields=True))
    charge = BudgetCharge.model_validate(charge.model_dump(mode="json", exclude_computed_fields=True))

    spent = ledger.spent.model_dump(mode="json", exclude_computed_fields=True)
    key = charge.category.value
    spent[key] = float(spent[key]) + charge.amount_usd
    payload = {
        "ledger_id": ledger.ledger_id,
        "max_usd": ledger.max_usd,
        "spent": BudgetSpend.model_validate(spent).model_dump(mode="json", exclude_computed_fields=True),
        "limits": ledger.limits.model_dump(mode="json", exclude_computed_fields=True),
        "usage": _add_usage(ledger.usage, charge.usage),
    }
    try:
        return BudgetLedger.model_validate(payload)
    except (ValidationError, AgentContractError) as exc:
        raise BudgetExceededError(
            f"budget authorization refused charge {charge.charge_id!r}: {exc}"
        ) from exc


class HardBudgetController:
    """Thread-safe, fail-closed budget/quota state for synchronous orchestration."""

    def __init__(self, ledger: BudgetLedger) -> None:
        self._lock = RLock()
        self._ledger = BudgetLedger.model_validate(ledger.model_dump(mode="json", exclude_computed_fields=True))

    @property
    def ledger(self) -> BudgetLedger:
        with self._lock:
            return BudgetLedger.model_validate(self._ledger.model_dump(mode="json", exclude_computed_fields=True))

    def authorize(self, charge: BudgetCharge) -> BudgetLedger:
        with self._lock:
            candidate = apply_budget_charge(self._ledger, charge)
            self._ledger = candidate
            return self.ledger
