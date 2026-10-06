# Runtime Governance — Hooks + Budget

This stage binds LearnFlow policy/accounting to the exact pinned Hermes hook surface while keeping enforcement deterministic.

Status: PASS. Accepted CI run `37448402550` proves deterministic hard USD/tool/retry enforcement, fail-closed publication policy, 16 governance regressions, 11 Agent Contracts regressions, exact pinned Hermes project-plugin discovery and native hook dispatch, token/cost and retry metrics, lifecycle tracing, privacy-minimized event persistence, and Core Freeze preservation.

## Native Hermes hooks

The project plugin `.hermes/plugins/learnflow-governance/` registers:

- `pre_tool_call` — blocking publication policy plus tool/subagent quota reservation;
- `post_tool_call` — privacy-minimized timing/status metrics;
- `post_api_request` — token/cost observation using the pinned Hermes pricing normalizer;
- `api_request_error` — retry/error metrics;
- `on_session_start` / `on_session_end` — session lifecycle;
- `subagent_start` / `subagent_stop` — delegated-agent lifecycle.

Raw prompts, raw tool arguments, raw tool results, and child summaries are not persisted by this plugin.

## Hard-budget semantics

The pinned Hermes `pre_api_request` hook is observer-only, so it would be incorrect to claim that a Python hook can cancel a provider request there. Hard USD enforcement therefore happens in the deterministic LearnFlow host **before** an agent stage starts through `HardBudgetController` / `BudgetedAgentRunner`.

A charge is a conservative reservation consumed before dispatch. If the reservation would exceed USD, tool, subagent, provider-attempt, retry, VLM-repair, or image-generation limits, the operation is refused before it starts.

Native `post_api_request` cost is observability evidence, not a retroactive enforcement mechanism.

## Publication policy

Publication-like tools are fail-closed unless operator-owned `GovernanceState.publication_authorized` is true. Authorization lives in the controlled governance state file and is not accepted from model tool arguments.

`learnflow_render` is intentionally not treated as publication.

## Out of scope

Skills and Kanban Durability are not implemented here.

## Verification

    python scripts/verify_runtime_governance.py
    pytest -q --confcutdir=tests/hermes tests/hermes/test_runtime_governance.py
    python scripts/verify_v2_core_freeze.py

Pinned Hermes verification discovers the real project plugin, invokes the native hook dispatcher, proves unauthorized publication is blocked, proves tool quotas block before dispatch, and checks lifecycle/metrics events.
