from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

import pytest
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import BudgetLedger, BudgetLimits, BudgetUsage
from runtime_governance import (
    BudgetCharge,
    BudgetExceededError,
    BudgetedAgentRunner,
    GovernanceState,
    HardBudgetController,
    SpendCategory,
    apply_budget_charge,
    evaluate_pre_tool_call,
    is_publication_tool,
)
from runtime_governance.events import append_event
from runtime_governance.hermes_plugin import (
    on_post_tool_call,
    on_pre_tool_call,
    on_session_end,
    on_session_start,
    on_subagent_start,
)


def ledger(**limits):
    return BudgetLedger(
        ledger_id="budget.test",
        max_usd=1.0,
        limits=BudgetLimits(**limits),
    )


def test_charge_updates_usd_and_usage():
    updated = apply_budget_charge(
        ledger(tool_calls=2, provider_attempts=2),
        BudgetCharge(
            charge_id="c1",
            category=SpendCategory.LLM,
            amount_usd=0.25,
            usage=BudgetUsage(tool_calls=1, provider_attempts=1),
            reason="test",
        ),
    )
    assert updated.spent.llm == 0.25
    assert updated.usage.tool_calls == 1
    assert updated.usage.provider_attempts == 1


def test_usd_overspend_fails_before_commit():
    controller = HardBudgetController(
        BudgetLedger(
            ledger_id="budget.usd",
            max_usd=0.10,
            limits=BudgetLimits(provider_attempts=2),
        )
    )
    with pytest.raises(BudgetExceededError):
        controller.authorize(
            BudgetCharge(
                charge_id="too-much",
                category=SpendCategory.LLM,
                amount_usd=0.11,
                usage=BudgetUsage(provider_attempts=1),
                reason="too much",
            )
        )
    assert controller.ledger.spent.total_usd == 0.0



def test_uncapped_usd_still_enforces_provider_attempt_quota():
    controller = HardBudgetController(
        BudgetLedger(
            ledger_id="budget.no-usd-cap",
            max_usd=None,
            limits=BudgetLimits(provider_attempts=1),
        )
    )
    controller.authorize(
        BudgetCharge(
            charge_id="uncapped.1",
            category=SpendCategory.LLM,
            amount_usd=100.0,
            usage=BudgetUsage(provider_attempts=1),
            reason="record spend without a money ceiling",
        )
    )
    assert controller.ledger.spent.llm == 100.0
    assert controller.ledger.remaining_usd is None
    with pytest.raises(BudgetExceededError):
        controller.authorize(
            BudgetCharge(
                charge_id="uncapped.2",
                category=SpendCategory.LLM,
                amount_usd=100.0,
                usage=BudgetUsage(provider_attempts=1),
                reason="second provider attempt must still be blocked",
            )
        )


def test_tool_call_limit_fails_closed():
    controller = HardBudgetController(ledger(tool_calls=1))
    state = GovernanceState(
        state_id="state.tools",
        budget=controller.ledger,
        publication_authorized=False,
    )
    assert evaluate_pre_tool_call("read_file", state=state, budget=controller) is None
    decision = evaluate_pre_tool_call("read_file", state=state, budget=controller)
    assert decision["action"] == "block"


def test_subagent_limit_counts_children_in_delegate_batch():
    controller = HardBudgetController(ledger(tool_calls=2, subagent_calls=3))
    state = GovernanceState(
        state_id="state.subagents",
        budget=controller.ledger,
    )
    decision = evaluate_pre_tool_call(
        "delegate_task",
        state=state,
        budget=controller,
        args={"tasks": [{"goal": "a"}, {"goal": "b"}, {"goal": "c"}]},
    )
    assert decision is None
    assert controller.ledger.usage.subagent_calls == 3
    second = evaluate_pre_tool_call(
        "delegate_task",
        state=state,
        budget=controller,
        args={"goal": "extra"},
    )
    assert second["action"] == "block"


def test_publication_is_blocked_without_operator_authorization():
    state = GovernanceState(state_id="state.publish", publication_authorized=False)
    decision = evaluate_pre_tool_call("learnflow_publish", state=state)
    assert decision["action"] == "block"


def test_model_argument_cannot_authorize_publication():
    state = GovernanceState(state_id="state.publish", publication_authorized=False)
    decision = evaluate_pre_tool_call("learnflow_publish", state=state)
    assert decision["action"] == "block"


def test_publication_can_be_operator_authorized():
    state = GovernanceState(state_id="state.publish", publication_authorized=True)
    assert evaluate_pre_tool_call("learnflow_publish", state=state) is None


def test_render_is_not_publication():
    state = GovernanceState(state_id="state.render", publication_authorized=False)
    assert not is_publication_tool("learnflow_render", state)
    assert evaluate_pre_tool_call("learnflow_render", state=state) is None


def test_custom_publication_tool_is_blocked():
    state = GovernanceState(
        state_id="state.custom",
        publication_authorized=False,
        publication_tools=("ship_to_public_cdn",),
    )
    assert is_publication_tool("ship_to_public_cdn", state)


def test_retry_limit_is_hard():
    controller = HardBudgetController(
        ledger(provider_attempts=3, retries=1)
    )
    controller.authorize(
        BudgetCharge(
            charge_id="retry.1",
            usage=BudgetUsage(provider_attempts=1, retries=1),
            reason="first retry",
        )
    )
    with pytest.raises(BudgetExceededError):
        controller.authorize(
            BudgetCharge(
                charge_id="retry.2",
                usage=BudgetUsage(provider_attempts=1, retries=1),
                reason="second retry",
            )
        )


class Output(BaseModel):
    value: int


class Runner:
    def __init__(self):
        self.calls = 0
    def run(self, *, stage, task, output_model):
        self.calls += 1
        return output_model(value=self.calls)


def test_budgeted_runner_never_calls_underlying_runner_after_exhaustion():
    base = Runner()
    controller = HardBudgetController(
        BudgetLedger(
            ledger_id="budget.runner",
            max_usd=0.05,
            limits=BudgetLimits(provider_attempts=2),
        )
    )
    wrapped = BudgetedAgentRunner(
        base,
        budget=controller,
        quote_provider=lambda stage, task, output_model: BudgetCharge(
            charge_id=f"stage:{stage}",
            category=SpendCategory.LLM,
            amount_usd=0.03,
            usage=BudgetUsage(provider_attempts=1),
            reason=stage,
        ),
    )
    assert wrapped.run(stage="research", task={}, output_model=Output).value == 1
    with pytest.raises(BudgetExceededError):
        wrapped.run(stage="script", task={}, output_model=Output)
    assert base.calls == 1


def test_charge_is_conservative_and_not_rolled_back_on_failure():
    controller = HardBudgetController(
        BudgetLedger(
            ledger_id="budget.reserve",
            max_usd=1.0,
            limits=BudgetLimits(provider_attempts=2),
        )
    )
    controller.authorize(
        BudgetCharge(
            charge_id="stage.failed",
            category=SpendCategory.LLM,
            amount_usd=0.4,
            usage=BudgetUsage(provider_attempts=1),
            reason="reserve before call",
        )
    )
    assert controller.ledger.spent.llm == 0.4


def test_metrics_writer_is_jsonl(tmp_path):
    path = tmp_path / "events.jsonl"
    append_event(path, "post_tool_call", tool_name="read_file", duration_ms=5)
    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["event"] == "post_tool_call"
    assert row["tool_name"] == "read_file"


def test_post_tool_hook_does_not_persist_args_or_results(tmp_path, monkeypatch):
    state = tmp_path / "state.json"
    events = tmp_path / "events.jsonl"
    monkeypatch.setenv("LEARNFLOW_GOVERNANCE_STATE", str(state))
    monkeypatch.setenv("LEARNFLOW_GOVERNANCE_EVENTS", str(events))
    on_post_tool_call(
        tool_name="read_file",
        args={"path": "secret-path"},
        result="secret-result",
        duration_ms=8,
        status="success",
    )
    raw = events.read_text(encoding="utf-8")
    assert "secret-path" not in raw
    assert "secret-result" not in raw


def test_subagent_hook_does_not_persist_goal(tmp_path, monkeypatch):
    events = tmp_path / "events.jsonl"
    monkeypatch.setenv("LEARNFLOW_GOVERNANCE_EVENTS", str(events))
    on_subagent_start(
        parent_session_id="p",
        child_session_id="c",
        child_subagent_id="id",
        child_role="researcher",
        child_goal="private project goal",
    )
    assert "private project goal" not in events.read_text(encoding="utf-8")


def test_no_skills_or_kanban_implementation_leaks_into_checkpoint():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "runtime_governance").glob("*.py")
    ).lower()
    assert "kanban_task_" not in source
    assert "skill_manage" not in source



def test_concurrent_pre_tool_hooks_do_not_lose_budget_updates(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    events_path = tmp_path / "events.jsonl"
    state = GovernanceState(
        state_id="state.concurrent",
        budget=BudgetLedger(
            ledger_id="budget.concurrent",
            max_usd=None,
            limits=BudgetLimits(tool_calls=8),
        ),
    )
    state_path.write_text(state.to_canonical_json(), encoding="utf-8")
    monkeypatch.setenv("LEARNFLOW_GOVERNANCE_STATE", str(state_path))
    monkeypatch.setenv("LEARNFLOW_GOVERNANCE_EVENTS", str(events_path))

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(
                lambda _: on_pre_tool_call("web_search", args={"q": "x"}),
                range(8),
            )
        )

    assert results == [None] * 8
    persisted = GovernanceState.model_validate_json(
        state_path.read_text(encoding="utf-8")
    )
    assert persisted.budget is not None
    assert persisted.budget.usage.tool_calls == 8


def test_live_governance_plugin_is_explicitly_enabled():
    config = (ROOT / "hermes" / "bootstrap" / "config.yaml").read_text(
        encoding="utf-8"
    )
    assert "plugins:" in config
    assert "enabled:" in config
    assert "- learnflow-governance" in config



def test_subagent_session_hooks_are_not_duplicated(tmp_path, monkeypatch):
    events = tmp_path / "events.jsonl"
    monkeypatch.setenv("LEARNFLOW_GOVERNANCE_EVENTS", str(events))

    on_session_start(
        session_id="child-session",
        model="free-model:free",
        platform="subagent",
    )
    on_session_end(
        session_id="child-session",
        platform="subagent",
        completed=True,
    )
    assert not events.exists()

    on_subagent_start(
        parent_session_id="parent",
        child_session_id="child-session",
        child_subagent_id="child-id",
        child_role="leaf",
    )
    rows = [
        json.loads(line)
        for line in events.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [row["event"] for row in rows] == ["subagent_start"]


def test_parent_session_hooks_remain_recorded(tmp_path, monkeypatch):
    events = tmp_path / "events.jsonl"
    monkeypatch.setenv("LEARNFLOW_GOVERNANCE_EVENTS", str(events))
    on_session_start(
        session_id="parent-session",
        model="free-model:free",
        platform="cli",
    )
    on_session_end(
        session_id="parent-session",
        platform="cli",
        completed=True,
    )
    rows = [
        json.loads(line)
        for line in events.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [row["event"] for row in rows] == ["session_start", "session_end"]
