from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
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


def test_pilot_topic_is_frozen_corpus_member():
    brief = build_pilot_brief(PILOT_TOPIC_ID)
    assert brief.brief_id == f"live-eval:{PILOT_TOPIC_ID}"
    assert brief.target_duration_minutes == 3
    assert brief.language == "en"


def test_unknown_pilot_topic_fails_closed():
    with pytest.raises(KeyError):
        build_pilot_brief("not-in-frozen-corpus")


def test_live_model_candidates_are_ordered_and_qwen_free_is_removed():
    assert LIVE_MODEL_CANDIDATES == (
        "apodex/apodex-1.1-mini:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "nex-agi/nex-n2.5-mini:free",
    )
    assert DEFAULT_LIVE_MODEL == LIVE_MODEL_CANDIDATES[0]
    assert all("qwen/qwen3.8-27b:free" != item for item in LIVE_MODEL_CANDIDATES)


def test_model_probe_requires_tools_and_native_json_schema():
    source = (ROOT / "live_evaluation" / "model_probe.py").read_text(encoding="utf-8")
    assert '"tools": [' in source
    assert '"tool_choice": "none"' in source
    assert '"type": "json_schema"' in source
    assert '"strict": True' in source
    assert '"require_parameters": True' in source


def test_governance_state_is_fail_closed(tmp_path):
    state = initialize_governance_state(tmp_path / "state.json")
    assert state.publication_authorized is False
    assert state.budget is not None
    assert state.budget.max_usd is None
    assert state.budget.limits.subagent_calls == 3
    assert state.budget.limits.tool_calls == 32
    assert state.budget.limits.provider_attempts == 160
    assert state.budget.limits.retries == 4
    assert state.budget.limits.image_generations == 0
    assert state.budget.limits.vlm_repairs == 0


def test_governance_state_persists_without_secret_fields(tmp_path):
    path = tmp_path / "state.json"
    initialize_governance_state(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = json.dumps(data).lower()
    assert "api_key" not in raw
    assert "openrouter" not in raw


def test_stage_reservations_cover_only_live_agent_stages():
    assert tuple(LiveHermesStructuredRunner._STAGE_RESERVATIONS) == (
        "research_orchestration",
        "pedagogy_agent",
        "script_agent",
        "visual_director",
    )


def test_live_eval_has_no_usd_reservation_and_attempt_quota_matches_iterations():
    reservations = LiveHermesStructuredRunner._STAGE_RESERVATIONS
    assert all(float(item["usd"]) == 0.0 for item in reservations.values())
    assert reservations["research_orchestration"]["provider_attempts"] == 128
    assert reservations["pedagogy_agent"]["provider_attempts"] == 3
    assert reservations["script_agent"]["provider_attempts"] == 3
    assert reservations["visual_director"]["provider_attempts"] == 3
    assert sum(int(item["provider_attempts"]) for item in reservations.values()) == 137


def test_research_gets_delegation_and_web_only():
    source = (ROOT / "live_evaluation" / "hermes_runner.py").read_text(encoding="utf-8")
    assert '["delegation", "web"] if research else []' in source
    assert 'disabled = [] if research else ["*"]' in source


def test_runner_uses_openrouter_explicitly():
    source = (ROOT / "live_evaluation" / "hermes_runner.py").read_text(encoding="utf-8")
    assert 'provider="openrouter"' in source
    assert 'base_url=self.base_url' in source


def test_live_script_never_prints_secret_value():
    source = (ROOT / "scripts" / "run_live_v2d_pilot.py").read_text(encoding="utf-8")
    assert "OPENROUTER_API_KEY" in source
    assert 'replace(secret, "<redacted>")' in source
    assert "print(key)" not in source


def test_workflow_scopes_secret_to_live_job():
    workflow = (ROOT / ".github" / "workflows" / "live-v2d-evaluation.yml").read_text(
        encoding="utf-8"
    )
    assert workflow.count("secrets.OPENROUTER_API_KEY") == 1
    assert "chatgpt/live-v2d-evaluation" in workflow
    assert "workflow_dispatch:" in workflow


def test_research_iteration_budget_is_128_only_for_research():
    source = (ROOT / "live_evaluation" / "hermes_runner.py").read_text(encoding="utf-8")
    assert "max_iterations=128 if research else 3" in source


def test_research_uses_sync_native_fanout_and_host_deterministic_assembly():
    source = (ROOT / "live_evaluation" / "hermes_runner.py").read_text(encoding="utf-8")
    assert "agent._delegate_depth = 1" in source
    assert 'agent._delegate_role = "orchestrator"' in source
    assert "delegate_task(" in source
    assert "background=False" in source
    assert "assemble_specialist_delegation_results(" in source
    assert "then synthesize ResearchOrchestrationResult" not in source


def test_schema_retry_restates_schema_previous_output_and_history():
    task = {"output_schema": {"type": "object", "required": ["research_pack"]}}
    message = LiveHermesStructuredRunner._validation_retry_message(
        task,
        '{"status":"ok"}',
        ValueError("bad schema"),
    )
    assert '"required": ["research_pack"]' in message
    assert '{"status":"ok"}' in message
    assert "Do not call tools or delegate again" in message

    source = (ROOT / "live_evaluation" / "hermes_runner.py").read_text(encoding="utf-8")
    assert 'conversation_history=list((result or {}).get("messages") or [])' in source


def test_live_provider_waits_for_contract_job_before_spending_provider_quota():
    workflow = (ROOT / ".github" / "workflows" / "live-v2d-evaluation.yml").read_text(
        encoding="utf-8"
    )
    assert "live-provider-pilot:\n    needs: live-eval-contract" in workflow
    assert "github.event.pull_request.head.repo.full_name == github.repository" in workflow
    assert "github.head_ref == 'chatgpt/live-v2d-evaluation'" in workflow


def test_live_script_selects_model_via_probe_before_pilot():
    source = (ROOT / "scripts" / "run_live_v2d_pilot.py").read_text(encoding="utf-8")
    assert "select_live_model(api_key=key, candidates=candidates)" in source
    assert "LIVE_MODEL_PROBE=PASS" in source
    assert "model_probe.json" in source



def test_research_host_assembly_has_no_llm_synthesis_turn():
    source = (
        ROOT / "live_evaluation" / "hermes_runner.py"
    ).read_text(encoding="utf-8")
    research_block = source[
        source.index("def _run_research_delegation"):
        source.index("def _delegation_usage")
    ]
    assert "run_conversation(" not in research_block
    assert "delegate_task(" in research_block



def test_live_workflow_cancels_superseded_runs_before_provider_usage():
    workflow = (
        ROOT / ".github" / "workflows" / "live-v2d-evaluation.yml"
    ).read_text(encoding="utf-8")
    assert "concurrency:" in workflow
    assert "cancel-in-progress: true" in workflow
    assert "live-v2d-${{ github.event.pull_request.number || github.ref }}" in workflow
