#!/usr/bin/env python3
"""Verify Research Orchestration against the exact pinned Hermes delegation runtime."""

from __future__ import annotations

import inspect
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import LearningBrief
from live_evaluation.hermes_runner import _isolated_research_workspace
from research_orchestration import (
    build_research_orchestration_plan,
    expected_hermes_limits,
)

from tools import delegate_tool
from tools.delegate_tool_config import (
    _get_max_concurrent_children,
    _get_max_spawn_depth,
    _get_oneshot_max_children,
    _get_orchestrator_enabled,
)
from tools.delegate_tool_tasks import _coerce_task_schemas, _normalize_task_list
from tools.delegate_tool_progress import (
    _build_child_system_prompt,
    _resolve_workspace_hint,
)
from tools.delegate_tool_toolsets import _blocked_toolsets_for_role
from toolsets import resolve_toolset


def _resolved_disabled_tools(role: str) -> set[str]:
    tools: set[str] = set()
    for toolset_name in _blocked_toolsets_for_role(role):
        resolved = resolve_toolset(toolset_name)
        if resolved:
            tools.update(resolved)
    return tools


def main() -> int:
    expected = expected_hermes_limits()
    actual = {
        "max_spawn_depth": _get_max_spawn_depth(),
        "max_concurrent_children": _get_max_concurrent_children(),
        "oneshot_max_children": _get_oneshot_max_children(),
        "orchestrator_enabled": _get_orchestrator_enabled(),
    }
    if actual != expected:
        raise SystemExit(
            f"HERMES_RESEARCH_DELEGATION=FAIL limits expected={expected!r} actual={actual!r}"
        )

    schema = delegate_tool.DELEGATE_TASK_SCHEMA["parameters"]["properties"]["tasks"]
    context_description = schema["items"]["properties"]["context"]["description"]
    if "Each child sees only its own context" not in context_description:
        raise SystemExit("HERMES_RESEARCH_DELEGATION=FAIL context isolation schema missing")
    if "output_schema" not in schema["items"]["properties"]:
        raise SystemExit("HERMES_RESEARCH_DELEGATION=FAIL output_schema unavailable")

    child_source = inspect.getsource(delegate_tool._build_child_agent)
    for required in ("skip_context_files=True", "skip_memory=True", "child_depth"):
        if required not in child_source:
            raise SystemExit(
                f"HERMES_RESEARCH_DELEGATION=FAIL child isolation/depth marker {required!r} missing"
            )

    class _Hints:
        working_dir = ROOT

    class _Parent:
        _subdirectory_hints = _Hints()
        terminal_cwd = str(ROOT)
        cwd = str(ROOT)

    parent = _Parent()
    original_process_cwd = Path.cwd().resolve()
    original_hint = Path(parent._subdirectory_hints.working_dir).resolve()
    with _isolated_research_workspace(parent) as isolated_cwd:
        resolved = _resolve_workspace_hint(parent)
        if resolved is None or Path(resolved).resolve() != Path(isolated_cwd).resolve():
            raise SystemExit(
                "HERMES_RESEARCH_DELEGATION=FAIL isolated workspace hint not authoritative"
            )
        prompt = _build_child_system_prompt(
            "test goal",
            "test context",
            workspace_path=resolved,
        )
        if "# Project Context" in prompt or "AGENTS.md" in prompt:
            raise SystemExit(
                "HERMES_RESEARCH_DELEGATION=FAIL repository context leaked into child"
            )
        if Path.cwd().resolve() != Path(isolated_cwd).resolve():
            raise SystemExit(
                "HERMES_RESEARCH_DELEGATION=FAIL process cwd not isolated"
            )
    if Path.cwd().resolve() != original_process_cwd:
        raise SystemExit(
            "HERMES_RESEARCH_DELEGATION=FAIL process cwd not restored"
        )
    if Path(parent._subdirectory_hints.working_dir).resolve() != original_hint:
        raise SystemExit(
            "HERMES_RESEARCH_DELEGATION=FAIL parent workspace hint not restored"
        )

    leaf_disabled = _resolved_disabled_tools("leaf")
    orchestrator_disabled = _resolved_disabled_tools("orchestrator")
    if "delegate_task" not in leaf_disabled:
        raise SystemExit("HERMES_RESEARCH_DELEGATION=FAIL leaf may recursively delegate")
    if "delegate_task" in orchestrator_disabled:
        raise SystemExit("HERMES_RESEARCH_DELEGATION=FAIL orchestrator cannot delegate")

    brief = LearningBrief(
        brief_id="brief.hermes-runtime",
        user_query="Explain a test concept.",
        learner_level="beginner",
        target_duration_minutes=2,
        language="en",
    )
    plan = build_research_orchestration_plan(brief)
    tasks = [
        {
            "goal": item.goal,
            "context": item.context,
            "output_schema": item.output_schema,
        }
        for item in plan.specialist_tasks
    ]

    normalized, error = _normalize_task_list(
        None,
        None,
        tasks,
        None,
        "leaf",
        _get_max_concurrent_children(),
    )
    if error or normalized is None or len(normalized) != 3:
        raise SystemExit(f"HERMES_RESEARCH_DELEGATION=FAIL 3-task batch: {error!r}")

    schemas, error = _coerce_task_schemas(normalized, None)
    if error or len(schemas) != 3 or any(item is None for item in schemas):
        raise SystemExit(f"HERMES_RESEARCH_DELEGATION=FAIL output schemas: {error!r}")

    overflow = tasks + [dict(tasks[0])]
    rejected, error = _normalize_task_list(
        None,
        None,
        overflow,
        None,
        "leaf",
        _get_max_concurrent_children(),
    )
    if rejected is not None or not error or "Too many tasks" not in error:
        raise SystemExit("HERMES_RESEARCH_DELEGATION=FAIL >3 specialist batch not rejected")

    print("HERMES_RESEARCH_DELEGATION=PASS")
    print("runtime=exact pinned Hermes")
    print("isolated_child_context=PASS")
    print("sealed_workspace_context=PASS")
    print("orchestrator_nested_delegation=PASS")
    print("leaf_recursive_delegation_blocked=PASS")
    print("specialist_batch_limit=3")
    print("max_spawn_depth=2")
    print("per_child_output_schema=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
