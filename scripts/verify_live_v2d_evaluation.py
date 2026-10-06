#!/usr/bin/env python3
"""Static acceptance verifier for the governed live V2D pilot."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live_evaluation import (
    DEFAULT_LIVE_MODEL,
    PILOT_TOPIC_ID,
    build_pilot_brief,
    initialize_governance_state,
)
from live_evaluation.hermes_runner import LiveHermesStructuredRunner


def main() -> int:
    brief = build_pilot_brief()
    if brief.brief_id != f"live-eval:{PILOT_TOPIC_ID}":
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL pilot topic binding")
    if DEFAULT_LIVE_MODEL != "nvidia/nemotron-3.5-lightning:free":
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL pilot must default to accepted free model")

    runtime = ROOT / ".hermes_runtime" / "live-v2d-contract"
    state = initialize_governance_state(runtime / "state.json")
    if state.publication_authorized:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL publication must be disabled")
    if state.budget is None or state.budget.max_usd is not None:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL live evaluation must not impose a USD cap")
    if state.budget.limits.subagent_calls != 3:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL subagent cap")
    if state.budget.limits.tool_calls != 32:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL tool cap")
    if state.budget.limits.provider_attempts != 160:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL provider-attempt quota")
    if state.budget.limits.retries != 4:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL retry cap")

    reservations = LiveHermesStructuredRunner._STAGE_RESERVATIONS
    if tuple(reservations) != (
        "research_orchestration",
        "pedagogy_agent",
        "script_agent",
        "visual_director",
    ):
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL stage reservation order")
    if any(float(item["usd"]) != 0.0 for item in reservations.values()):
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL live stages must not reserve USD")
    if reservations["research_orchestration"]["provider_attempts"] != 128:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL research provider-attempt quota")
    if any(
        reservations[name]["provider_attempts"] != 3
        for name in ("pedagogy_agent", "script_agent", "visual_director")
    ):
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL non-research provider-attempt quota")

    workflow = (ROOT / ".github" / "workflows" / "live-v2d-evaluation.yml").read_text(
        encoding="utf-8"
    )
    if "secrets.OPENROUTER_API_KEY" not in workflow:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL Actions secret wiring missing")
    if "OPENROUTER_API_KEY:" not in workflow:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL secret env binding missing")
    if "branches:" not in workflow or "chatgpt/live-v2d-evaluation" not in workflow:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL pilot branch trigger missing")
    if "push" not in workflow or "workflow_dispatch" not in workflow:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL controlled triggers missing")

    source = (ROOT / "live_evaluation" / "hermes_runner.py").read_text(encoding="utf-8")
    if 'provider="openrouter"' not in source:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL OpenRouter runner binding")
    if "skip_memory=True" not in source or "skip_context_files=True" not in source:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL stateless live runner")
    if 'disabled = [] if research else ["*"]' not in source:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL non-research tools not disabled")
    if "max_iterations=128 if research else 3" not in source:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL research iteration budget")

    print("LIVE_V2D_CONTRACT=PASS")
    print(f"pilot_topic={PILOT_TOPIC_ID}")
    print(f"default_model={DEFAULT_LIVE_MODEL}")
    print("usd_cap=none")
    print("publication_authorized=false")
    print("live_secret_step_scope=PASS")
    print("native_research_delegation_enabled=PASS")
    print("research_max_iterations=128")
    print("provider_attempt_quota=160")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
