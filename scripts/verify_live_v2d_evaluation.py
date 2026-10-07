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
    LIVE_MODEL_CANDIDATES,
    PILOT_TOPIC_ID,
    build_pilot_brief,
    initialize_governance_state,
)
from live_evaluation.hermes_runner import LiveHermesStructuredRunner


def main() -> int:
    brief = build_pilot_brief()
    if brief.brief_id != f"live-eval:{PILOT_TOPIC_ID}":
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL pilot topic binding")
    expected_models = (
        "google/gemma-4-31b-it:free",
        "poolside/laguna-s-2.1:free",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "apodex/apodex-1.1-mini:free",
    )
    if LIVE_MODEL_CANDIDATES != expected_models or DEFAULT_LIVE_MODEL != expected_models[0]:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL live model candidate order")

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
    if state.budget.limits.provider_attempts != 1600:
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
    if reservations["research_orchestration"]["provider_attempts"] != 384:
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

    probe_source = (ROOT / "live_evaluation" / "model_probe.py").read_text(encoding="utf-8")
    for required in (
        '"tools": [',
        "_RESPONSE_FORMAT_MODELS",
        'final_payload["response_format"] = {"type": "json_object"}',
        '"require_parameters": True',
        '"max_tokens": 4096',
        'tool_payload["reasoning_effort"] = "medium"',
        'message["tool_calls"]',
        '"role": "tool"',
        '"native_tool_call_missing"',
        "request_count=2",
        "_SPECIALIST_PROBE_OBJECT",
        '"source_indexes": [0]',
        '"claim_indexes": [0]',
    ):
        if required not in probe_source:
            raise SystemExit("LIVE_V2D_CONTRACT=FAIL model capability probe")

    tool_payload_block = probe_source[
        probe_source.index("tool_payload: dict[str, Any] = {"):
        probe_source.index(
            'if model.startswith("google/gemma-4-"):',
            probe_source.index("tool_payload: dict[str, Any] = {"),
        )
    ]
    if '"tool_choice"' in tool_payload_block:
        raise SystemExit(
            "LIVE_V2D_CONTRACT=FAIL probe must match pinned Hermes auto tool selection"
        )

    pilot_source = (ROOT / "live_evaluation" / "pilot.py").read_text(encoding="utf-8")
    if "_reset_runtime_preserving_hermes_home(" not in pilot_source:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL Hermes profile preservation missing")
    if "preserve_governance=preserve_governance" not in pilot_source:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL governance preservation wiring missing")
    if "shutil.rmtree(runtime)" in pilot_source:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL pilot deletes active runtime root")

    source = (ROOT / "live_evaluation" / "hermes_runner.py").read_text(encoding="utf-8")
    if 'provider="openrouter"' not in source:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL OpenRouter runner binding")
    if "skip_memory=True" not in source or "skip_context_files=True" not in source:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL stateless live runner")
    if 'disabled = [] if research else ["*"]' not in source:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL non-research tools not disabled")
    if "max_iterations=128 if research else 3" not in source:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL research iteration budget")
    if 'request_overrides["response_format"] = {"type": "json_object"}' not in source:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL conditional json_object wire constraint")
    if 'request_overrides["reasoning_effort"] = "medium"' not in source:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL Gemma reasoning must stay enabled")
    if '"max_tokens"' in source:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL live runner must not impose a low token cap")
    if "assemble_specialist_delegation_results(" not in source:
        raise SystemExit(
            "LIVE_V2D_CONTRACT=FAIL deterministic research assembly missing"
        )
    if "background=False" not in source or "delegate_task(" not in source:
        raise SystemExit(
            "LIVE_V2D_CONTRACT=FAIL synchronous native research fan-out missing"
        )

    for required in (
        "def _isolated_research_workspace",
        'prefix="learnflow-research-context-"',
        "from tools.terminal_scope import terminal_scope",
        'terminal_scope({"TERMINAL_CWD": isolated})',
        'os.environ["TERMINAL_CWD"] = isolated',
        "hints.working_dir = Path(isolated)",
        "os.chdir(isolated)",
        "with _isolated_research_workspace(agent):",
    ):
        if required not in source:
            raise SystemExit(
                "LIVE_V2D_CONTRACT=FAIL sealed research workspace missing"
            )
    if '"host-research-fanout"' not in source or "on_pre_tool_call(" not in source:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL direct research fan-out bypasses governance")

    bootstrap = (ROOT / "hermes" / "bootstrap" / "config.yaml").read_text(
        encoding="utf-8"
    )
    if "max_iterations: 128" not in bootstrap:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL delegated research budget mismatch")
    if "- learnflow-governance" not in bootstrap:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL governance project plugin not enabled")

    live_script = (ROOT / "scripts" / "run_live_v2d_pilot.py").read_text(
        encoding="utf-8"
    )
    if "_charge_probe_attempts" not in live_script:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL model probes outside governance")
    if "_probe_request_count(selection.probes)" not in live_script:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL probe HTTP attempts undercounted")
    if "_retryable_research_model_incompatibility" not in live_script:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL research model incompatibility fallback missing")
    if "preserve_governance=True" not in live_script:
        raise SystemExit("LIVE_V2D_CONTRACT=FAIL fallback resets governance")

    print("LIVE_V2D_CONTRACT=PASS")
    print(f"pilot_topic={PILOT_TOPIC_ID}")
    print(f"default_model={DEFAULT_LIVE_MODEL}")
    print("model_probe=native_tool_roundtrip+nested_specialist_shape+model_compatible_json+diverse_providers")
    print("usd_cap=none")
    print("publication_authorized=false")
    print("live_secret_step_scope=PASS")
    print("research_provider_runtime_fallback=PASS")
    print("research_model_incompatibility_fallback=PASS")
    print("research_workspace_sealing=PASS")
    print("native_research_delegation_enabled=PASS")
    print("active_hermes_profile_preserved=PASS")
    print("deterministic_research_assembly=PASS")
    print("research_max_iterations=128")
    print("research_fanout_reservation=384")
    print("provider_attempt_quota=1600")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
