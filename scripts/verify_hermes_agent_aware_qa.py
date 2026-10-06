#!/usr/bin/env python3
"""Verify Agent-Aware QA repair tasks against exact pinned Hermes schemas."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import AgentContractError
from agent_aware_qa import RepairOwner, build_agent_repair_task
from scripts.verify_agent_aware_qa import build_acceptance
from tools.delegation_output_schema import coerce_output_schema


def main() -> int:
    brief, pack, graph, fact_report, pedagogy, script, visual, plan = build_acceptance()
    checked = set()
    for intent in plan.intents:
        if intent.owner == RepairOwner.CORE_REPAIR or intent.owner in checked:
            continue
        task = build_agent_repair_task(
            intent,
            brief=brief,
            pack=pack,
            graph=graph,
            fact_report=fact_report,
            pedagogy=pedagogy,
            script=script,
            visual=visual,
        )
        schema, error = coerce_output_schema(task["output_schema"])
        if error or schema is None or schema.get("type") != "object":
            raise SystemExit(
                f"HERMES_AGENT_AWARE_QA=FAIL owner={intent.owner.value} schema={error!r}"
            )
        checked.add(intent.owner)

    core_intent = next(
        intent for intent in plan.intents if intent.owner == RepairOwner.CORE_REPAIR
    )
    try:
        build_agent_repair_task(
            core_intent,
            brief=brief,
            pack=pack,
            graph=graph,
            fact_report=fact_report,
            pedagogy=pedagogy,
            script=script,
            visual=visual,
        )
    except AgentContractError:
        pass
    else:
        raise SystemExit("HERMES_AGENT_AWARE_QA=FAIL Core repair was delegated")

    print("HERMES_AGENT_AWARE_QA=PASS")
    print("runtime=exact pinned Hermes")
    print("research_repair_schema=PASS")
    print("script_repair_schema=PASS")
    print("visual_repair_schema=PASS")
    print("core_delegation_blocked=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
