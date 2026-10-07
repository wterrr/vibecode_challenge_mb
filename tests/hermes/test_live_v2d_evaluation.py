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
from live_evaluation.pilot import _reset_runtime_preserving_hermes_home


def test_pilot_topic_is_frozen_corpus_member():
    brief = build_pilot_brief(PILOT_TOPIC_ID)
    assert brief.brief_id == f"live-eval:{PILOT_TOPIC_ID}"
    assert brief.target_duration_minutes == 3
    assert brief.language == "en"


def test_unknown_pilot_topic_fails_closed():
    with pytest.raises(KeyError):
        build_pilot_brief("not-in-frozen-corpus")


def test_live_model_candidates_prioritize_specialist_schema_reliability():
    assert LIVE_MODEL_CANDIDATES == (
        "google/gemma-4-31b-it:free",
        "poolside/laguna-s-2.1:free",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "apodex/apodex-1.1-mini:free",
    )
    assert DEFAULT_LIVE_MODEL == LIVE_MODEL_CANDIDATES[0]
    assert all("qwen/qwen3.8-27b:free" != item for item in LIVE_MODEL_CANDIDATES)
    assert all("nemotron-3-super" not in item for item in LIVE_MODEL_CANDIDATES)


def test_model_probe_matches_actual_hermes_free_endpoint_requirements():
    source = (ROOT / "live_evaluation" / "model_probe.py").read_text(encoding="utf-8")
    assert '"tools": [' in source
    assert '_RESPONSE_FORMAT_MODELS' in source
    assert 'payload["response_format"] = {"type": "json_object"}' in source
    assert '"require_parameters": True' in source
    assert '"tool_choice"' not in source
    assert '"type": "json_schema"' not in source


def test_governance_state_is_fail_closed(tmp_path):
    state = initialize_governance_state(tmp_path / "state.json")
    assert state.publication_authorized is False
    assert state.budget is not None
    assert state.budget.max_usd is None
    assert state.budget.limits.subagent_calls == 3
    assert state.budget.limits.tool_calls == 32
    assert state.budget.limits.provider_attempts == 1600
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
    assert reservations["research_orchestration"]["provider_attempts"] == 384
    assert reservations["pedagogy_agent"]["provider_attempts"] == 3
    assert reservations["script_agent"]["provider_attempts"] == 3
    assert reservations["visual_director"]["provider_attempts"] == 3
    assert sum(int(item["provider_attempts"]) for item in reservations.values()) == 393


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
    provider_block = workflow[workflow.index("live-provider-pilot:"):]
    assert "github.event_name == 'workflow_dispatch'" in provider_block
    assert "github.event_name == 'pull_request'" not in provider_block.split("steps:", 1)[0]


def test_live_script_selects_model_via_probe_before_pilot():
    source = (ROOT / "scripts" / "run_live_v2d_pilot.py").read_text(encoding="utf-8")
    assert "select_live_model(api_key=key, candidates=remaining)" in source
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



def test_runner_uses_conditional_json_object_wire_constraint():
    source = (
        ROOT / "live_evaluation" / "hermes_runner.py"
    ).read_text(encoding="utf-8")
    assert 'request_overrides: dict[str, Any] = {}' in source
    assert 'if self.model.startswith(("google/gemma-4-", "apodex/apodex-")):' in source
    assert 'request_overrides["response_format"] = {"type": "json_object"}' in source



def test_probe_uses_specialist_shaped_nested_contract_with_reasoning_enabled():
    source = (
        ROOT / "live_evaluation" / "model_probe.py"
    ).read_text(encoding="utf-8")
    assert '"max_tokens": 4096' in source
    assert "_SPECIALIST_PROBE_OBJECT" in source
    assert '"source_indexes": [0]' in source
    assert '"claim_indexes": [0]' in source
    assert 'google/gemma-4-' in source
    assert 'payload["reasoning_effort"] = "medium"' in source
    assert "parsed != _SPECIALIST_PROBE_OBJECT" in source
    assert "finish_reason=" in source
    assert "response_prefix=" in source



def test_live_runner_uses_model_compatible_wire_overrides():
    source = (
        ROOT / "live_evaluation" / "hermes_runner.py"
    ).read_text(encoding="utf-8")
    assert 'google/gemma-4-' in source
    assert 'apodex/apodex-' in source
    assert 'request_overrides["response_format"] = {"type": "json_object"}' in source
    assert 'request_overrides["reasoning_effort"] = "medium"' in source
    assert 'poolside/laguna' not in source[source.index("request_overrides:"):source.index("agent = AIAgent(")]
    assert '"max_tokens"' not in source



def test_runtime_reset_preserves_active_hermes_home(tmp_path, monkeypatch):
    runtime = tmp_path / "live-v2d"
    hermes_home = runtime / "hermes-home"
    hermes_home.mkdir(parents=True)
    config = hermes_home / "config.yaml"
    config.write_text(
        "delegation:\n  max_spawn_depth: 2\n",
        encoding="utf-8",
    )
    stale = runtime / "stale-artifact.txt"
    stale.write_text("old", encoding="utf-8")

    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    _reset_runtime_preserving_hermes_home(runtime)

    assert config.is_file()
    assert "max_spawn_depth: 2" in config.read_text(encoding="utf-8")
    assert not stale.exists()


def test_research_delegation_surfaces_native_hermes_rejection():
    source = (
        ROOT / "live_evaluation" / "hermes_runner.py"
    ).read_text(encoding="utf-8")
    assert "Hermes delegate_task rejected research fan-out:" in source



def test_candidate_chain_diversifies_free_upstream_providers():
    providers = [model.split("/", 1)[0] for model in LIVE_MODEL_CANDIDATES]
    assert providers == ["google", "poolside", "nvidia", "apodex"]
    assert len(set(providers)) == len(providers)



def test_runtime_model_fallback_is_restricted_to_research_provider_failures():
    source = (
        ROOT / "scripts" / "run_live_v2d_pilot.py"
    ).read_text(encoding="utf-8")
    assert "_retryable_research_provider_failure" in source
    assert "CONCEPT_RESEARCHER" in source
    assert "EVIDENCE_RESEARCHER" in source
    assert "MISCONCEPTION_RESEARCHER" in source
    assert "404|408|425|429|500|502|503|504" in source
    assert "LIVE_MODEL_RUNTIME_FALLBACK" in source
    assert '"runtime_fallbacks": runtime_fallbacks' in source


def test_runtime_model_fallback_does_not_retry_schema_or_nonresearch_errors():
    from scripts.run_live_v2d_pilot import _retryable_research_provider_failure

    assert _retryable_research_provider_failure(
        RuntimeError(
            "CONCEPT_RESEARCHER failed: HTTP 429: Provider returned error"
        )
    )
    assert _retryable_research_provider_failure(
        RuntimeError(
            "EVIDENCE_RESEARCHER failed: HTTP 503: upstream unavailable"
        )
    )
    assert not _retryable_research_provider_failure(
        RuntimeError(
            "EVIDENCE_RESEARCHER failed output schema validation"
        )
    )
    assert not _retryable_research_provider_failure(
        RuntimeError(
            "pedagogy_agent failed: HTTP 429: Provider returned error"
        )
    )



def test_live_runner_assembles_script_dynamic_refs_on_host():
    source = (
        ROOT / "live_evaluation" / "hermes_runner.py"
    ).read_text(encoding="utf-8")
    assert 'if stage == "script_agent":' in source
    assert "assemble_lesson_script_wire" in source
    assert "selected_fact_claim_catalog" in source
    assert "objective_catalog" in source



def test_bootstrap_aligns_delegated_research_budget_and_enables_governance():
    config = (ROOT / "hermes" / "bootstrap" / "config.yaml").read_text(
        encoding="utf-8"
    )
    assert "max_iterations: 128" in config
    assert "plugins:" in config
    assert "- learnflow-governance" in config


def test_research_fanout_uses_isolated_workspace_context():
    source = (
        ROOT / "live_evaluation" / "hermes_runner.py"
    ).read_text(encoding="utf-8")
    research_block = source[
        source.index("def _run_research_delegation"):
        source.index("def _delegation_usage")
    ]
    assert 'TemporaryDirectory(prefix="learnflow-research-context-")' in research_block
    assert 'os.environ["TERMINAL_CWD"] = isolated_cwd' in research_block
    assert 'os.environ["TERMINAL_CWD"] = previous_terminal_cwd' in research_block


def test_runtime_reset_can_preserve_governance_across_fallback(tmp_path, monkeypatch):
    runtime = tmp_path / "live-v2d"
    hermes_home = runtime / "hermes-home"
    governance = runtime / "governance"
    hermes_home.mkdir(parents=True)
    governance.mkdir(parents=True)
    (hermes_home / "config.yaml").write_text("x: 1\n", encoding="utf-8")
    state = governance / "state.json"
    events = governance / "events.jsonl"
    state.write_text('{"kept": true}', encoding="utf-8")
    events.write_text('{"event":"kept"}\n', encoding="utf-8")
    (runtime / "stale.txt").write_text("stale", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    _reset_runtime_preserving_hermes_home(
        runtime,
        preserve_governance=True,
    )

    assert state.read_text(encoding="utf-8") == '{"kept": true}'
    assert events.read_text(encoding="utf-8") == '{"event":"kept"}\n'
    assert not (runtime / "stale.txt").exists()


def test_live_script_accounts_model_probes_before_runtime_fallback():
    source = (
        ROOT / "scripts" / "run_live_v2d_pilot.py"
    ).read_text(encoding="utf-8")
    assert "_charge_probe_attempts" in source
    assert "_charge_probe_attempts(len(selection.probes))" in source
    assert "_charge_probe_attempts(len(probe_exc.probes))" in source
    assert "preserve_governance=True" in source


def test_live_workflow_reacts_to_governance_and_bootstrap_changes():
    workflow = (
        ROOT / ".github" / "workflows" / "live-v2d-evaluation.yml"
    ).read_text(encoding="utf-8")
    assert '"runtime_governance/**"' in workflow
    assert '".hermes/plugins/learnflow-governance/**"' in workflow
    assert '"hermes/bootstrap/config.yaml"' in workflow



def test_host_preauthorizes_direct_research_fanout():
    source = (
        ROOT / "live_evaluation" / "hermes_runner.py"
    ).read_text(encoding="utf-8")
    research_block = source[
        source.index("def _run_research_delegation"):
        source.index("def _delegation_usage")
    ]
    assert 'on_pre_tool_call(' in research_block
    assert '"delegate_task"' in research_block
    assert '"host-research-fanout"' in research_block
    assert "LearnFlow governance rejected research fan-out" in research_block



def test_probe_http_error_detail_redacts_account_metadata():
    from live_evaluation.model_probe import _safe_http_error_detail

    raw = json.dumps(
        {
            "error": {
                "message": "rate limited",
                "code": 429,
                "metadata": {
                    "limit_source": "free-tier",
                    "provider_name": "provider",
                    "headers": {"Authorization": "secret"},
                },
            },
            "user_id": "private-account-id",
        }
    )
    detail = _safe_http_error_detail(raw)
    assert "rate limited" in detail
    assert "429" in detail
    assert "private-account-id" not in detail
    assert "Authorization" not in detail
    assert "secret" not in detail
