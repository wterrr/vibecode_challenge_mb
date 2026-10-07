#!/usr/bin/env python3
"""Acceptance verifier for Hooks + Budget runtime governance."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pydantic import BaseModel

from agent_contracts import BudgetLedger, BudgetLimits, BudgetUsage
from runtime_governance import (
    BudgetCharge,
    BudgetExceededError,
    BudgetedAgentRunner,
    GovernanceState,
    HardBudgetController,
    SpendCategory,
    evaluate_pre_tool_call,
)


class DummyOutput(BaseModel):
    ok: bool


class DummyRunner:
    def __init__(self):
        self.calls = 0

    def run(self, *, stage, task, output_model):
        self.calls += 1
        return output_model(ok=True)


def main() -> int:
    ledger = BudgetLedger(
        ledger_id="budget.runtime-governance.acceptance",
        max_usd=0.05,
        limits=BudgetLimits(
            tool_calls=2,
            subagent_calls=1,
            provider_attempts=2,
            retries=1,
        ),
        usage=BudgetUsage(),
    )
    controller = HardBudgetController(ledger)
    runner = DummyRunner()
    governed = BudgetedAgentRunner(
        runner,
        budget=controller,
        quote_provider=lambda stage, task, output_model: BudgetCharge(
            charge_id=f"stage:{stage}",
            category=SpendCategory.LLM,
            amount_usd=0.03,
            usage=BudgetUsage(provider_attempts=1),
            reason=f"reserve stage {stage}",
        ),
    )
    governed.run(stage="research", task={}, output_model=DummyOutput)
    try:
        governed.run(stage="script", task={}, output_model=DummyOutput)
    except BudgetExceededError:
        pass
    else:
        raise SystemExit("RUNTIME_GOVERNANCE=FAIL USD budget exceeded")
    if runner.calls != 1:
        raise SystemExit("RUNTIME_GOVERNANCE=FAIL blocked stage reached runner")

    state = GovernanceState(
        state_id="governance.acceptance",
        budget=BudgetLedger(
            ledger_id="budget.tools",
            max_usd=1.0,
            limits=BudgetLimits(tool_calls=1, subagent_calls=1),
        ),
        publication_authorized=False,
    )
    publication = evaluate_pre_tool_call("learnflow_publish", state=state)
    if not publication or publication.get("action") != "block":
        raise SystemExit("RUNTIME_GOVERNANCE=FAIL illegal publication allowed")

    tool_controller = HardBudgetController(state.budget)
    if evaluate_pre_tool_call("read_file", state=state, budget=tool_controller) is not None:
        raise SystemExit("RUNTIME_GOVERNANCE=FAIL first tool call blocked")
    second = evaluate_pre_tool_call("read_file", state=state, budget=tool_controller)
    if not second or second.get("action") != "block":
        raise SystemExit("RUNTIME_GOVERNANCE=FAIL tool quota exceeded")

    batch_controller = HardBudgetController(
        BudgetLedger(
            ledger_id="budget.batch",
            max_usd=None,
            limits=BudgetLimits(tool_calls=1, subagent_calls=3),
        )
    )
    if evaluate_pre_tool_call(
        "delegate_task",
        state=GovernanceState(
            state_id="governance.batch",
            budget=batch_controller.ledger,
        ),
        budget=batch_controller,
        args={"tasks": [{"goal": "a"}, {"goal": "b"}, {"goal": "c"}]},
    ) is not None:
        raise SystemExit("RUNTIME_GOVERNANCE=FAIL three-child batch blocked")
    if batch_controller.ledger.usage.subagent_calls != 3:
        raise SystemExit("RUNTIME_GOVERNANCE=FAIL delegated children undercounted")

    bootstrap = (ROOT / "hermes" / "bootstrap" / "config.yaml").read_text(
        encoding="utf-8"
    )
    if "- learnflow-governance" not in bootstrap:
        raise SystemExit("RUNTIME_GOVERNANCE=FAIL governance plugin not enabled")

    retry_controller = HardBudgetController(
        BudgetLedger(
            ledger_id="budget.retry",
            max_usd=1.0,
            limits=BudgetLimits(provider_attempts=2, retries=1),
        )
    )
    retry_controller.authorize(
        BudgetCharge(
            charge_id="attempt.1",
            category=SpendCategory.LLM,
            usage=BudgetUsage(provider_attempts=1, retries=1),
            reason="first retry",
        )
    )
    try:
        retry_controller.authorize(
            BudgetCharge(
                charge_id="attempt.2",
                category=SpendCategory.LLM,
                usage=BudgetUsage(provider_attempts=1, retries=1),
                reason="second retry",
            )
        )
    except BudgetExceededError:
        pass
    else:
        raise SystemExit("RUNTIME_GOVERNANCE=FAIL retry budget exceeded")

    print("RUNTIME_GOVERNANCE=PASS")
    print("pre_tool_call_policy=PASS")
    print("hard_usd_reservation=PASS")
    print("tool_quota=PASS")
    print("retry_quota=PASS")
    print("delegated_child_accounting=PASS")
    print("governance_plugin_enabled=PASS")
    print("illegal_publication_blocked=PASS")
    print("blocked_operation_not_executed=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
