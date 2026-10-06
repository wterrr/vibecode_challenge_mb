#!/usr/bin/env python3
"""Verify Runtime Governance through the exact pinned Hermes plugin dispatcher."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_HOME = ROOT / ".hermes_runtime" / "runtime-governance" / "verify-home"
STATE = ROOT / ".hermes_runtime" / "runtime-governance" / "verify-state.json"
EVENTS = ROOT / ".hermes_runtime" / "runtime-governance" / "verify-events.jsonl"


def _prepare_home(home: Path) -> None:
    if (home / "config.yaml").exists():
        return
    home.mkdir(parents=True, exist_ok=True)
    base = (ROOT / "hermes" / "bootstrap" / "config.yaml").read_text(encoding="utf-8")
    (home / "config.yaml").write_text(base, encoding="utf-8")


def _enable_plugin(home: Path) -> None:
    from hermes_cli.config import load_config, save_config
    from hermes_cli.plugin_python_deps import install_for_plugin_dir

    config = load_config()
    plugins = config.setdefault("plugins", {})
    enabled = plugins.setdefault("enabled", [])
    if "learnflow-governance" not in enabled:
        enabled.append("learnflow-governance")
    disabled = plugins.get("disabled")
    if isinstance(disabled, list):
        plugins["disabled"] = [
            name for name in disabled if name != "learnflow-governance"
        ]
    save_config(config)

    outcome = install_for_plugin_dir(
        ROOT / ".hermes" / "plugins" / "learnflow-governance"
    )
    if outcome.status not in {"installed", "none"}:
        raise RuntimeError(
            f"governance plugin dependency install failed: {outcome.status} {outcome.message}"
        )


def _write_state(*, authorized: bool, tool_calls: int = 2) -> None:
    from agent_contracts import BudgetLedger, BudgetLimits
    from runtime_governance import GovernanceState

    state = GovernanceState(
        state_id="runtime-governance.pinned",
        budget=BudgetLedger(
            ledger_id="budget.pinned",
            max_usd=1.0,
            limits=BudgetLimits(tool_calls=tool_calls, subagent_calls=1),
        ),
        publication_authorized=authorized,
    )
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(state.to_canonical_json(), encoding="utf-8")


def _blocked(results) -> bool:
    return any(
        isinstance(item, dict)
        and item.get("action") == "block"
        and item.get("message")
        for item in (results or [])
    )


def main() -> int:
    os.chdir(ROOT)
    home = Path(os.environ.get("HERMES_HOME") or DEFAULT_HOME).resolve()
    shutil.rmtree(STATE.parent, ignore_errors=True)
    _prepare_home(home)
    os.environ["HERMES_HOME"] = str(home)
    os.environ["HERMES_ENABLE_PROJECT_PLUGINS"] = "true"
    os.environ["LEARNFLOW_GOVERNANCE_STATE"] = str(STATE)
    os.environ["LEARNFLOW_GOVERNANCE_EVENTS"] = str(EVENTS)

    _enable_plugin(home)
    _write_state(authorized=False, tool_calls=2)

    from hermes_cli.plugins import discover_plugins, get_plugin_manager

    discover_plugins(force=True)
    manager = get_plugin_manager()
    rows = manager.list_plugins()
    matches = [row for row in rows if row.get("name") == "learnflow-governance"]
    if len(matches) != 1:
        raise SystemExit(
            f"HERMES_RUNTIME_GOVERNANCE=FAIL discovery matches={matches!r}"
        )
    row = matches[0]
    if row.get("source") != "project" or row.get("enabled") is not True:
        raise SystemExit(
            f"HERMES_RUNTIME_GOVERNANCE=FAIL plugin row={row!r}"
        )

    blocked = manager.invoke_hook(
        "pre_tool_call",
        tool_name="learnflow_publish",
        args={"authorization": "model-cannot-grant-this"},
        session_id="session.pinned",
        task_id="task.pinned",
        turn_id="turn.pinned",
        tool_call_id="tool.publish",
    )
    if not _blocked(blocked):
        raise SystemExit("HERMES_RUNTIME_GOVERNANCE=FAIL publication was not blocked")

    first = manager.invoke_hook(
        "pre_tool_call",
        tool_name="read_file",
        args={"path": "README.md"},
        session_id="session.pinned",
        task_id="task.pinned",
        turn_id="turn.pinned",
        tool_call_id="tool.read.1",
    )
    if _blocked(first):
        raise SystemExit("HERMES_RUNTIME_GOVERNANCE=FAIL first tool quota blocked")

    second = manager.invoke_hook(
        "pre_tool_call",
        tool_name="read_file",
        args={"path": "AGENTS.md"},
        session_id="session.pinned",
        task_id="task.pinned",
        turn_id="turn.pinned",
        tool_call_id="tool.read.2",
    )
    if _blocked(second):
        raise SystemExit("HERMES_RUNTIME_GOVERNANCE=FAIL second tool quota blocked")

    third = manager.invoke_hook(
        "pre_tool_call",
        tool_name="read_file",
        args={"path": "PLAN_V2.md"},
        session_id="session.pinned",
        task_id="task.pinned",
        turn_id="turn.pinned",
        tool_call_id="tool.read.3",
    )
    if not _blocked(third):
        raise SystemExit("HERMES_RUNTIME_GOVERNANCE=FAIL tool budget was exceeded")

    _write_state(authorized=True, tool_calls=4)
    allowed_publication = manager.invoke_hook(
        "pre_tool_call",
        tool_name="learnflow_publish",
        args={},
        session_id="session.pinned",
        task_id="task.pinned",
        turn_id="turn.pinned",
        tool_call_id="tool.publish.allowed",
    )
    if _blocked(allowed_publication):
        raise SystemExit("HERMES_RUNTIME_GOVERNANCE=FAIL authorized publication blocked")

    manager.invoke_hook(
        "post_tool_call",
        tool_name="read_file",
        args={"path": "secret-path-not-persisted"},
        result="secret-result-not-persisted",
        duration_ms=7,
        status="success",
        session_id="session.pinned",
        task_id="task.pinned",
        turn_id="turn.pinned",
        tool_call_id="tool.metric",
    )
    manager.invoke_hook(
        "post_api_request",
        model="gpt-4o",
        provider="openai",
        base_url="https://api.openai.com/v1",
        usage={
            "input_tokens": 1000,
            "output_tokens": 100,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
            "reasoning_tokens": 0,
            "request_count": 1,
            "total_tokens": 1100,
        },
        api_duration=0.25,
        session_id="session.pinned",
        task_id="task.pinned",
        turn_id="turn.pinned",
        api_request_id="api.pinned",
    )
    manager.invoke_hook(
        "api_request_error",
        model="gpt-4o",
        provider="openai",
        retry_count=1,
        max_retries=2,
        retryable=True,
        status_code=429,
        session_id="session.pinned",
        task_id="task.pinned",
        turn_id="turn.pinned",
        api_request_id="api.retry",
    )

    manager.invoke_hook(
        "on_session_start",
        session_id="session.pinned",
        model="nvidia/nemotron-3.5-lightning:free",
        platform="cli",
    )
    manager.invoke_hook(
        "subagent_start",
        parent_session_id="session.pinned",
        parent_turn_id="turn.pinned",
        child_session_id="child.pinned",
        child_subagent_id="researcher.1",
        child_role="evidence-researcher",
        child_goal="sensitive-goal-not-persisted",
    )
    manager.invoke_hook(
        "subagent_stop",
        parent_session_id="session.pinned",
        parent_turn_id="turn.pinned",
        child_session_id="child.pinned",
        child_role="evidence-researcher",
        child_summary="sensitive-summary-not-persisted",
        child_status="completed",
        duration_ms=12,
    )
    manager.invoke_hook(
        "on_session_end",
        session_id="session.pinned",
        task_id="task.pinned",
        turn_id="turn.pinned",
        completed=True,
        failed=False,
        interrupted=False,
        model="nvidia/nemotron-3.5-lightning:free",
        platform="cli",
    )

    lines = [
        json.loads(line)
        for line in EVENTS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    kinds = {item["event"] for item in lines}
    required = {
        "pre_tool_call",
        "post_tool_call",
        "post_api_request",
        "api_request_error",
        "session_start",
        "session_end",
        "subagent_start",
        "subagent_stop",
    }
    if not required.issubset(kinds):
        raise SystemExit(
            f"HERMES_RUNTIME_GOVERNANCE=FAIL missing events={sorted(required-kinds)!r}"
        )
    api_rows = [item for item in lines if item["event"] == "post_api_request"]
    if len(api_rows) != 1:
        raise SystemExit("HERMES_RUNTIME_GOVERNANCE=FAIL post_api_request event missing")
    api_row = api_rows[0]
    if api_row.get("total_tokens") != 1100:
        raise SystemExit("HERMES_RUNTIME_GOVERNANCE=FAIL normalized token metrics missing")
    if api_row.get("estimated_cost_usd") is None:
        raise SystemExit("HERMES_RUNTIME_GOVERNANCE=FAIL pinned cost estimate missing")
    retry_rows = [item for item in lines if item["event"] == "api_request_error"]
    if len(retry_rows) != 1 or retry_rows[0].get("retry_count") != 1:
        raise SystemExit("HERMES_RUNTIME_GOVERNANCE=FAIL retry metrics missing")
    raw = EVENTS.read_text(encoding="utf-8")
    for secret in (
        "secret-path-not-persisted",
        "secret-result-not-persisted",
        "sensitive-goal-not-persisted",
        "sensitive-summary-not-persisted",
    ):
        if secret in raw:
            raise SystemExit("HERMES_RUNTIME_GOVERNANCE=FAIL sensitive payload persisted")

    print("HERMES_RUNTIME_GOVERNANCE=PASS")
    print("runtime=exact pinned Hermes")
    print("plugin_discovery=PASS")
    print("native_pre_tool_call_block=PASS")
    print("tool_budget_block=PASS")
    print("authorized_publication=PASS")
    print("post_tool_metrics=PASS")
    print("post_api_cost_metrics=PASS")
    print("api_retry_metrics=PASS")
    print("session_lifecycle=PASS")
    print("subagent_lifecycle=PASS")
    print("sensitive_payload_not_persisted=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
