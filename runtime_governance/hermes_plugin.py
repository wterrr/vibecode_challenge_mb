"""Native pinned-Hermes hook callbacks for LearnFlow runtime governance."""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import RLock
from typing import Any

from agent_contracts import BudgetLedger

from .budget import HardBudgetController
from .events import append_event
from .models import GovernanceState
from .policy import evaluate_pre_tool_call

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_ROOT = _REPO_ROOT / ".hermes_runtime" / "runtime-governance"
_STATE_LOCK = RLock()


def _state_path() -> Path:
    raw = os.environ.get("LEARNFLOW_GOVERNANCE_STATE")
    return (
        Path(raw).expanduser().resolve()
        if raw
        else (_DEFAULT_ROOT / "state.json").resolve()
    )


def _events_path() -> Path:
    raw = os.environ.get("LEARNFLOW_GOVERNANCE_EVENTS")
    return (
        Path(raw).expanduser().resolve()
        if raw
        else (_state_path().parent / "events.jsonl").resolve()
    )


def load_state() -> GovernanceState:
    path = _state_path()
    if not path.is_file():
        return GovernanceState(
            state_id="runtime-governance.default",
            budget=None,
            publication_authorized=False,
        )
    return GovernanceState.model_validate_json(path.read_text(encoding="utf-8"))


def save_state(state: GovernanceState) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(state.to_canonical_json(), encoding="utf-8")
    os.replace(tmp, path)


def _event(event: str, **fields: Any) -> None:
    append_event(_events_path(), event, **fields)


def on_pre_tool_call(tool_name: str = "", args: Any = None, **kwargs: Any):
    # Research children execute tool calls concurrently. Keep the read-authorize-write
    # transaction atomic so sibling hooks cannot overwrite each other's counters.
    with _STATE_LOCK:
        state = load_state()
        controller = HardBudgetController(state.budget) if state.budget is not None else None
        decision = evaluate_pre_tool_call(
            tool_name,
            state=state,
            budget=controller,
            args=args,
        )
        if controller is not None and decision is None:
            save_state(
                GovernanceState(
                    state_id=state.state_id,
                    budget=controller.ledger,
                    publication_authorized=state.publication_authorized,
                    publication_tools=state.publication_tools,
                )
            )
    _event(
        "pre_tool_call",
        tool_name=str(tool_name or ""),
        blocked=bool(isinstance(decision, dict) and decision.get("action") == "block"),
        session_id=str(kwargs.get("session_id") or ""),
        task_id=str(kwargs.get("task_id") or ""),
        turn_id=str(kwargs.get("turn_id") or ""),
        tool_call_id=str(kwargs.get("tool_call_id") or ""),
    )
    return decision


def on_post_tool_call(
    tool_name: str = "",
    duration_ms: Any = None,
    status: Any = None,
    error_type: Any = None,
    **kwargs: Any,
) -> None:
    _event(
        "post_tool_call",
        tool_name=str(tool_name or ""),
        duration_ms=int(duration_ms or 0),
        status=str(status or ""),
        error_type=str(error_type or ""),
        session_id=str(kwargs.get("session_id") or ""),
        task_id=str(kwargs.get("task_id") or ""),
        turn_id=str(kwargs.get("turn_id") or ""),
        tool_call_id=str(kwargs.get("tool_call_id") or ""),
    )


def _estimated_cost_usd(
    *,
    model: str,
    provider: str,
    base_url: str,
    usage: Any,
) -> tuple[float | None, str]:
    if not isinstance(usage, dict):
        return None, "missing_usage"
    try:
        from agent.usage_pricing import CanonicalUsage, estimate_usage_cost

        canonical = CanonicalUsage(
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            cache_read_tokens=int(usage.get("cache_read_tokens") or 0),
            cache_write_tokens=int(usage.get("cache_write_tokens") or 0),
            reasoning_tokens=int(usage.get("reasoning_tokens") or 0),
            request_count=int(usage.get("request_count") or 1),
        )
        result = estimate_usage_cost(
            model,
            canonical,
            provider=provider,
            base_url=base_url,
        )
        amount = getattr(result, "amount_usd", None)
        return (
            None if amount is None else float(amount),
            str(getattr(result, "status", "unknown")),
        )
    except Exception as exc:
        return None, f"estimator_error:{type(exc).__name__}"


def on_post_api_request(
    model: str = "",
    provider: str = "",
    base_url: str = "",
    usage: Any = None,
    api_duration: Any = None,
    **kwargs: Any,
) -> None:
    amount, cost_status = _estimated_cost_usd(
        model=str(model or ""),
        provider=str(provider or ""),
        base_url=str(base_url or ""),
        usage=usage,
    )
    safe_usage = usage if isinstance(usage, dict) else {}
    _event(
        "post_api_request",
        model=str(model or ""),
        provider=str(provider or ""),
        input_tokens=int(safe_usage.get("input_tokens") or 0),
        output_tokens=int(safe_usage.get("output_tokens") or 0),
        total_tokens=int(safe_usage.get("total_tokens") or 0),
        estimated_cost_usd=amount,
        cost_status=cost_status,
        api_duration=float(api_duration or 0.0),
        session_id=str(kwargs.get("session_id") or ""),
        task_id=str(kwargs.get("task_id") or ""),
        turn_id=str(kwargs.get("turn_id") or ""),
        api_request_id=str(kwargs.get("api_request_id") or ""),
    )


def on_api_request_error(
    model: str = "",
    provider: str = "",
    retry_count: Any = None,
    max_retries: Any = None,
    retryable: Any = None,
    status_code: Any = None,
    **kwargs: Any,
) -> None:
    _event(
        "api_request_error",
        model=str(model or ""),
        provider=str(provider or ""),
        retry_count=int(retry_count or 0),
        max_retries=int(max_retries or 0),
        retryable=bool(retryable),
        status_code=None if status_code is None else int(status_code),
        session_id=str(kwargs.get("session_id") or ""),
        task_id=str(kwargs.get("task_id") or ""),
        turn_id=str(kwargs.get("turn_id") or ""),
        api_request_id=str(kwargs.get("api_request_id") or ""),
    )


def on_session_start(session_id: str = "", model: str = "", platform: str = "", **_: Any) -> None:
    _event(
        "session_start",
        session_id=str(session_id or ""),
        model=str(model or ""),
        platform=str(platform or ""),
    )


def on_session_end(session_id: str = "", **kwargs: Any) -> None:
    _event(
        "session_end",
        session_id=str(session_id or ""),
        task_id=str(kwargs.get("task_id") or ""),
        turn_id=str(kwargs.get("turn_id") or ""),
        completed=bool(kwargs.get("completed")),
        failed=bool(kwargs.get("failed")),
        interrupted=bool(kwargs.get("interrupted")),
        turn_exit_reason=str(kwargs.get("turn_exit_reason") or kwargs.get("reason") or ""),
        model=str(kwargs.get("model") or ""),
        platform=str(kwargs.get("platform") or ""),
    )


def on_subagent_start(
    parent_session_id: str = "",
    parent_turn_id: str = "",
    child_session_id: str = "",
    child_subagent_id: str = "",
    child_role: str = "",
    **_: Any,
) -> None:
    _event(
        "subagent_start",
        parent_session_id=str(parent_session_id or ""),
        parent_turn_id=str(parent_turn_id or ""),
        child_session_id=str(child_session_id or ""),
        child_subagent_id=str(child_subagent_id or ""),
        child_role=str(child_role or ""),
    )


def on_subagent_stop(
    parent_session_id: str = "",
    parent_turn_id: str = "",
    child_session_id: str = "",
    child_role: str = "",
    child_status: Any = None,
    duration_ms: Any = None,
    **_: Any,
) -> None:
    _event(
        "subagent_stop",
        parent_session_id=str(parent_session_id or ""),
        parent_turn_id=str(parent_turn_id or ""),
        child_session_id=str(child_session_id or ""),
        child_role=str(child_role or ""),
        child_status=str(child_status or ""),
        duration_ms=int(duration_ms or 0),
    )
