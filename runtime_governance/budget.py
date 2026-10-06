"""Hard pre-authorization for governed LearnFlow runtime operations."""

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


def _add_usage(current: BudgetUsage, delta: BudgetUsage) -> dict[str, int]:
    return {
        name: int(getattr(current, name)) + int(getattr(delta, name))
        for name in BudgetUsage.model_fields
    }


def apply_budget_charge(ledger: BudgetLedger, charge: BudgetCharge) -> BudgetLedger:
    """Return a newly validated ledger or raise before the operation begins.

    Charges are conservative reservations: the maximum authorized amount is
    consumed up front. This deliberately prefers under-utilization over a
    provider/tool operation crossing the configured hard limit.
    """

    ledger = BudgetLedger.model_validate(ledger.model_dump(mode="json"))
    charge = BudgetCharge.model_validate(charge.model_dump(mode="json"))

    spent = ledger.spent.model_dump(mode="json")
    key = charge.category.value
    spent[key] = float(spent[key]) + charge.amount_usd
    payload = {
        "ledger_id": ledger.ledger_id,
        "max_usd": ledger.max_usd,
        "spent": BudgetSpend.model_validate(spent).model_dump(mode="json"),
        "limits": ledger.limits.model_dump(mode="json"),
        "usage": _add_usage(ledger.usage, charge.usage),
    }
    try:
        return BudgetLedger.model_validate(payload)
    except (ValidationError, AgentContractError) as exc:
        raise BudgetExceededError(
            f"budget authorization refused charge {charge.charge_id!r}: {exc}"
        ) from exc


class HardBudgetController:
    """Thread-safe, fail-closed budget state for synchronous orchestration."""

    def __init__(self, ledger: BudgetLedger) -> None:
        self._lock = RLock()
        self._ledger = BudgetLedger.model_validate(ledger.model_dump(mode="json"))

    @property
    def ledger(self) -> BudgetLedger:
        with self._lock:
            return BudgetLedger.model_validate(self._ledger.model_dump(mode="json"))

    def authorize(self, charge: BudgetCharge) -> BudgetLedger:
        with self._lock:
            candidate = apply_budget_charge(self._ledger, charge)
            self._ledger = candidate
            return self.ledger
