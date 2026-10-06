"""Budget-enforcing adapter for the existing StructuredAgentRunner protocol."""

from __future__ import annotations

from typing import Callable, Protocol, TypeVar

from pydantic import BaseModel

from .budget import HardBudgetController
from .models import BudgetCharge

T = TypeVar("T", bound=BaseModel)


class StructuredRunner(Protocol):
    def run(self, *, stage: str, task: dict, output_model: type[T]) -> T | dict: ...


QuoteProvider = Callable[[str, dict, type[BaseModel]], BudgetCharge]


class BudgetedAgentRunner:
    """Reserve a conservative maximum charge before invoking an agent stage."""

    def __init__(
        self,
        runner: StructuredRunner,
        *,
        budget: HardBudgetController,
        quote_provider: QuoteProvider,
    ) -> None:
        self._runner = runner
        self._budget = budget
        self._quote_provider = quote_provider

    @property
    def ledger(self):
        return self._budget.ledger

    def run(self, *, stage: str, task: dict, output_model: type[T]) -> T | dict:
        charge = self._quote_provider(stage, task, output_model)
        if not isinstance(charge, BudgetCharge):
            charge = BudgetCharge.model_validate(charge)
        self._budget.authorize(charge)
        return self._runner.run(stage=stage, task=task, output_model=output_model)
