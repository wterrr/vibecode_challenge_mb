"""Deterministic pre-tool-call policy for publication and tool budgets."""

from __future__ import annotations

from agent_contracts import BudgetUsage

from .budget import BudgetExceededError, HardBudgetController
from .models import BudgetCharge, GovernanceState, SpendCategory


DEFAULT_PUBLICATION_TOOLS = frozenset(
    {
        "learnflow_publish",
        "publish",
        "publish_video",
        "release",
        "deploy",
        "upload_public",
        "send_public",
    }
)


def is_publication_tool(tool_name: str, state: GovernanceState) -> bool:
    name = str(tool_name or "").strip().lower()
    configured = set(DEFAULT_PUBLICATION_TOOLS) | {
        item.lower() for item in state.publication_tools
    }
    return name in configured


def evaluate_pre_tool_call(
    tool_name: str,
    *,
    state: GovernanceState,
    budget: HardBudgetController | None = None,
):
    """Return a Hermes pre_tool_call block directive or None.

    Publication authorization is operator state, never a model-facing argument.
    Tool/subagent usage is charged before dispatch when a budget is configured.
    """

    name = str(tool_name or "").strip()
    if is_publication_tool(name, state) and not state.publication_authorized:
        return {
            "action": "block",
            "message": (
                "LearnFlow runtime governance blocked publication: "
                "operator authorization is absent."
            ),
        }

    if budget is None:
        return None

    usage = BudgetUsage(
        tool_calls=1,
        subagent_calls=1 if name == "delegate_task" else 0,
    )
    try:
        budget.authorize(
            BudgetCharge(
                charge_id=f"tool:{name or 'unknown'}",
                category=SpendCategory.OTHER,
                amount_usd=0.0,
                usage=usage,
                reason=f"pre-authorize Hermes tool call {name or '<unknown>'}",
            )
        )
    except BudgetExceededError as exc:
        return {
            "action": "block",
            "message": f"LearnFlow runtime governance blocked tool call: {exc}",
        }
    return None
