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
    assert '"tools": [tool_definition]' in source
    assert '_RESPONSE_FORMAT_MODELS' in source
    assert 'final_payload["response_format"] = {"type": "json_object"}' in source
    assert '"require_parameters": True' in source
    tool_payload_block = source[
        source.index("tool_payload: dict[str, Any] = {"):
        source.index('if model.startswith("google/gemma-4-"):', source.index("tool_payload: dict[str, Any] = {"))
    ]
    assert '"tool_choice"' not in tool_payload_block
    assert '"tools": [tool_definition]' in tool_payload_block
    assert 'message["tool_calls"]' in source
    assert '"role": "tool"' in source
    assert '"type": "json_schema"' not in source


def test_governance_state_is_fail_closed(tmp_path):
    state = initialize_governance_state(tmp_path / "state.json")
    assert state.publication_authorized is False
    assert state.budget is not None
    assert state.budget.max_usd is None
    assert state.budget.limits.subagent_calls == 3 * len(LIVE_MODEL_CANDIDATES)
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
    assert 'tool_payload["reasoning_effort"] = "medium"' in source
    assert 'final_payload["reasoning_effort"] = "medium"' in source
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



def test_runtime_model_fallback_is_restricted_to_research_provider_or_model_failures():
    source = (
        ROOT / "scripts" / "run_live_v2d_pilot.py"
    ).read_text(encoding="utf-8")
    assert "_retryable_research_provider_failure" in source
    assert "_retryable_research_model_incompatibility" in source
    assert "CONCEPT_RESEARCHER" in source
    assert "EVIDENCE_RESEARCHER" in source
    assert "MISCONCEPTION_RESEARCHER" in source
    assert "404|408|425|429|500|502|503|504" in source
    assert "failed output schema validation" in source
    assert "repetition detected" in source
    assert "LIVE_MODEL_RUNTIME_FALLBACK" in source
    assert '"runtime_fallbacks": runtime_fallbacks' in source


def test_runtime_model_fallback_classifies_provider_vs_model_failures_narrowly():
    from scripts.run_live_v2d_pilot import (
        _retryable_research_model_incompatibility,
        _retryable_research_provider_failure,
    )

    provider = RuntimeError(
        "CONCEPT_RESEARCHER failed: HTTP 429: Provider returned error"
    )
    schema = RuntimeError(
        "EVIDENCE_RESEARCHER failed output schema validation"
    )
    repetition = RuntimeError(
        "MISCONCEPTION_RESEARCHER failed: Response Stopped — Repetition Detected"
    )
    repair_exhausted = RuntimeError(
        "MISCONCEPTION_RESEARCHER schema repair failed after 2 bounded attempts: "
        "output is missing required fields ['claims', 'examples', 'misconceptions']"
    )
    nonresearch = RuntimeError(
        "pedagogy_agent failed output schema validation"
    )

    assert _retryable_research_provider_failure(provider)
    assert not _retryable_research_model_incompatibility(provider)

    assert not _retryable_research_provider_failure(schema)
    assert _retryable_research_model_incompatibility(schema)
    assert _retryable_research_model_incompatibility(repetition)
    assert _retryable_research_model_incompatibility(repair_exhausted)

    assert not _retryable_research_provider_failure(nonresearch)
    assert not _retryable_research_model_incompatibility(nonresearch)



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


def test_research_fanout_seals_every_workspace_fallback():
    source = (
        ROOT / "live_evaluation" / "hermes_runner.py"
    ).read_text(encoding="utf-8")
    helper = source[
        source.index("def _isolated_research_workspace"):
        source.index("class LiveHermesStructuredRunner")
    ]
    research_block = source[
        source.index("def _run_research_delegation"):
        source.index("def _delegation_usage")
    ]
    assert 'TemporaryDirectory(' in helper
    assert '"learnflow-research-context-"' in helper
    assert "from tools.terminal_scope import terminal_scope" in helper
    assert 'terminal_scope({"TERMINAL_CWD": isolated})' in helper
    assert 'os.environ["TERMINAL_CWD"] = isolated' in helper
    assert "hints.working_dir = Path(isolated)" in helper
    assert "os.chdir(isolated)" in helper
    assert "with _isolated_research_workspace(agent):" in research_block


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
    assert "_probe_request_count(selection.probes)" in source
    assert "_probe_request_count(probe_exc.probes)" in source
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



def test_paid_openrouter_models_fail_closed_before_request(tmp_path):
    from openrouter_policy import require_free_openrouter_model
    from live_evaluation.model_probe import select_live_model

    with pytest.raises(ValueError, match="Paid OpenRouter model is forbidden"):
        require_free_openrouter_model("openai/gpt-6-luna")

    with pytest.raises(ValueError, match="Paid OpenRouter model is forbidden"):
        select_live_model(
            api_key="not-used-because-policy-blocks-first",
            candidates=("openai/gpt-6-luna",),
        )

    with pytest.raises(ValueError, match="Paid OpenRouter model is forbidden"):
        LiveHermesStructuredRunner(
            model="openai/gpt-6-luna",
            api_key="not-used",
            repo_root=tmp_path,
        )


def test_all_default_live_models_are_free_variants():
    assert LIVE_MODEL_CANDIDATES
    assert all(model.endswith(":free") for model in LIVE_MODEL_CANDIDATES)



def test_model_probe_requires_native_tool_call_roundtrip():
    source = (
        ROOT / "live_evaluation" / "model_probe.py"
    ).read_text(encoding="utf-8")
    tool_payload_block = source[
        source.index("tool_payload: dict[str, Any] = {"):
        source.index(
            'if model.startswith("google/gemma-4-"):',
            source.index("tool_payload: dict[str, Any] = {"),
        )
    ]
    assert '"tools": [tool_definition]' in tool_payload_block
    assert '"tool_choice"' not in tool_payload_block
    assert 'message["tool_calls"]' in source
    assert '"native_tool_call_missing"' in source
    assert '"role": "tool"' in source
    assert "request_count=2" in source
    assert "fake" in source.lower() and "tool call" in source.lower()


def test_probe_request_accounting_counts_http_roundtrips():
    from live_evaluation.model_probe import ModelProbeResult
    from scripts.run_live_v2d_pilot import _probe_request_count

    probes = (
        ModelProbeResult("a:free", False, "http_429", request_count=1),
        ModelProbeResult("b:free", True, "pass", request_count=2),
    )
    assert _probe_request_count(probes) == 3



def test_standard_agents_can_use_full_three_turn_schema_budget():
    source = (
        ROOT / "live_evaluation" / "hermes_runner.py"
    ).read_text(encoding="utf-8")
    assert "while True:" in source
    assert "if attempts >= 3:" in source
    assert 'task_id=f"live-eval:{stage}:schema-retry:{attempts - 1}"' in source
    assert "max_iterations=128 if research else 3" in source



def test_research_schema_repair_replaces_only_invalid_leaf(monkeypatch, tmp_path):
    from research_orchestration import build_research_orchestration_plan
    from scripts.verify_research_orchestration import LearningBrief

    brief = LearningBrief(
        brief_id="brief.repair",
        user_query="Explain Python variables.",
        learner_level="beginner",
        target_duration_minutes=2,
        language="en",
    )
    plan = build_research_orchestration_plan(brief)
    payload = {
        "results": [
            {
                "task_index": 1,
                "status": "completed",
                "truncated": False,
                "schema_valid": False,
                "schema_errors": ["calls was unexpected"],
                "summary": '{"calls":[{"name":"web_search"}]}',
                "tokens": {"input": 5, "output": 2},
                "api_calls": 1,
                "cost_usd": 0.0,
                "cost_status": "free",
                "schema_retries": 0,
            }
        ]
    }
    repaired_summary = json.dumps(
        {
            "sources": [
                {
                    "title": "Python Tutorial",
                    "locator": "https://docs.python.org/3/tutorial/",
                    "source_type": "DOCUMENT",
                }
            ],
            "claims": [
                {
                    "statement": "Python assignment statements bind names to values.",
                    "source_indexes": [0],
                    "confidence": 0.9,
                }
            ],
        }
    )

    class FakeRepairAgent:
        session_prompt_tokens = 11
        session_completion_tokens = 7
        session_estimated_cost_usd = 0.0
        session_cost_status = "free"

        def run_conversation(self, **kwargs):
            assert "NO tools" in kwargs["user_message"]
            return {
                "final_response": repaired_summary,
                "api_calls": 1,
            }

        def close(self):
            pass

    runner = LiveHermesStructuredRunner(
        model="apodex/apodex-1.1-mini:free",
        api_key="not-used",
        repo_root=tmp_path,
    )
    monkeypatch.setattr(runner, "_reserve", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        runner,
        "_agent",
        lambda **kwargs: FakeRepairAgent(),
    )

    runner._repair_invalid_research_results(
        delegation_payload=payload,
        plan=plan,
    )

    repaired = payload["results"][0]
    assert repaired["schema_valid"] is True
    assert repaired["schema_errors"] == []
    assert repaired["summary"] == repaired_summary
    assert repaired["schema_retries"] == 1
    assert repaired["api_calls"] == 2
    assert repaired["tokens"] == {"input": 16, "output": 9}


def test_research_schema_repair_is_no_tool_and_bounded():
    source = (
        ROOT / "live_evaluation" / "hermes_runner.py"
    ).read_text(encoding="utf-8")
    repair_block = source[
        source.index("def _repair_invalid_research_results"):
        source.index("def _run_research_delegation")
    ]
    assert "range(1, 3)" in repair_block
    assert "research_leaf_repair=True" in repair_block
    assert "You have NO tools in this repair pass" in repair_block
    assert "schema repair failed after" in repair_block



def test_visual_output_preflights_against_frozen_core_layout():
    source = (
        ROOT / "live_evaluation" / "hermes_runner.py"
    ).read_text(encoding="utf-8")
    helper = source[
        source.index("def _require_frozen_core_layout_compatible"):
        source.index("def _parse_output")
    ]
    assert "from learnflow_v2.layout import compile_scene_layout" in helper
    assert "LayoutUnsatisfiableError" in helper
    assert "compile_scene_layout(candidate)" in helper
    assert "except layout_errors as exc" in helper
    assert "not layout-compatible with frozen" in helper
    assert "CONCEPT_CARD" in helper


def test_visual_parse_runs_core_layout_preflight_before_acceptance():
    source = (
        ROOT / "live_evaluation" / "hermes_runner.py"
    ).read_text(encoding="utf-8")
    visual_block = source[
        source.index('if stage == "visual_director":'):
        source.index("return output_model.model_validate_json(candidate)")
    ]
    assert "_require_frozen_core_layout_compatible" in visual_block
    assert "validated = output_model.model_validate" in visual_block
    assert "return validated" in visual_block


def test_visual_preflight_aggregates_all_incompatible_scenes():
    source = (
        ROOT / "live_evaluation" / "hermes_runner.py"
    ).read_text(encoding="utf-8")
    helper = source[
        source.index("def _require_frozen_core_layout_compatible"):
        source.index("def _parse_output")
    ]

    assert "failures: list[tuple[str, Exception]] = []" in helper
    assert "failures.append((graph.scene_id, exc))" in helper
    assert "if failures:" in helper
    assert "for scene_id, exc in failures" in helper
    assert "Repair every listed scene in one response" in helper
    assert "from failures[0][1]" in helper


def test_visual_task_states_specialized_layout_topology_contracts():
    import ast

    source = (
        ROOT / "visual_director" / "hermes.py"
    ).read_text(encoding="utf-8")
    module = ast.parse(source)
    builder = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "build_visual_director_task"
    )
    guidance = "\n".join(
        node.value
        for node in ast.walk(builder)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )

    assert (
        "For PROCESS, emit exactly one PROCESS_TOPIC, at least one "
        "PROCESS_ACTOR, and at least one PROCESS_STEP"
    ) in guidance
    assert "every node in that scene must use one of those roles" in guidance
    assert (
        "For COMPARISON, emit exactly one COMPARISON_TOPIC and at least two "
        "COMPARISON_COLUMN nodes"
    ) in guidance
    assert "source=member and target=column" in guidance
    assert "choose CONCEPT_CARD rather than labeling it PROCESS or COMPARISON" in guidance



def test_probe_matches_pinned_hermes_auto_tool_selection():
    source = (
        ROOT / "live_evaluation" / "model_probe.py"
    ).read_text(encoding="utf-8")
    block = source[
        source.index("tool_payload: dict[str, Any] = {"):
        source.index('if model.startswith("google/gemma-4-"):', source.index("tool_payload: dict[str, Any] = {"))
    ]
    assert '"tools": [tool_definition]' in block
    assert '"tool_choice"' not in block
    assert "expected exactly one native tool call" in source
    assert 'function.get("name") != "probe_noop"' in source


def test_live_pilot_uses_production_media_gate_not_smoke_duration():
    pilot = (ROOT / "live_evaluation" / "pilot.py").read_text(encoding="utf-8")
    production = (ROOT / "lesson_pipeline" / "production.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "live-v2d-evaluation.yml").read_text(
        encoding="utf-8"
    )

    assert "duration_resolver=lambda _scene, _script: 0.35" not in pilot
    assert "build_production_media(" in pilot
    assert "EdgeSpeechProvider" in pilot
    assert "production_output_gate" in pilot
    assert "edge-tts" in workflow

    assert "MIN_TARGET_DURATION_RATIO" in production
    assert '"audio_stream_present"' in production
    assert '"motion_every_scene"' in production
    assert '"transition_coverage"' in production
    assert '"subtitle_coverage"' in production
    assert "create_narration_beat_map_fallback" in production
    assert "resolve_motion_plan_timing" in production
    assert "compile_inter_scene_transition" in production
    assert "render_transition_video" in production


def test_visual_director_code_nodes_use_content_for_visible_code():
    import ast

    source = (ROOT / "visual_director" / "hermes.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    builder = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "build_visual_director_task"
    )
    guidance = "\n".join(
        node.value
        for node in ast.walk(builder)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )
    assert "For CODE nodes" in guidance
    assert "learner-visible code expression/snippet in content" in guidance


def test_script_agent_has_target_duration_word_budget():
    source = (ROOT / "script_agent" / "hermes.py").read_text(encoding="utf-8")
    assert "target_words_min" in source
    assert "brief.target_duration_minutes * 130" in source
    assert "brief.target_duration_minutes * 160" in source
    assert "Target total spoken narration length" in source


def test_production_subtitles_are_script_timed_not_provider_timed():
    source = (ROOT / "lesson_pipeline" / "production.py").read_text(encoding="utf-8")
    assert "provider_cues.json" in source
    assert "deterministic_script_segments" in source
    assert "if narration.subtitle_cues:" not in source
    assert "for phrase_index, phrase in enumerate(beat_map.phrases)" in source


def test_governance_subagent_cap_covers_runtime_model_fallbacks(tmp_path):
    state = initialize_governance_state(
        tmp_path / "state.json",
        runtime_model_attempts=2,
    )
    assert state.budget is not None
    assert state.budget.limits.subagent_calls == 6

    source = (ROOT / "scripts" / "run_live_v2d_pilot.py").read_text(
        encoding="utf-8"
    )
    assert "runtime_model_attempts=len(candidates)" in source


def test_production_transition_text_fit_falls_back_without_weakening_core():
    source = (ROOT / "lesson_pipeline" / "production.py").read_text(encoding="utf-8")
    assert "MINIMAL_TRANSITION_CAPABILITIES" in source
    assert "FADE_FOR_INTERPOLATION_TEXT_FIT" in source
    assert 'if "does not fit solved LayoutGraph box" not in message' in source
    assert "RenderInvalidInputError" in source
    assert "except RenderInvalidInputError" in source


def test_visual_director_live_schema_exposes_only_auto_ports():
    from visual_director.hermes import _visual_wire_schema

    schema = _visual_wire_schema(segment_count=1, concept_count=1)
    assert schema["$defs"]["PortHint"]["enum"] == ["AUTO"]


def test_visual_director_host_negotiates_directed_ports_to_auto():
    source = (ROOT / "visual_director" / "hermes.py").read_text(encoding="utf-8")
    assert 'layout_type in {"PROCESS", "HIERARCHY"}' in source
    assert 'relation["source_port"] = "AUTO"' in source
    assert 'relation["target_port"] = "AUTO"' in source
    assert "Graphviz cannot guarantee strict orthogonal fixed-side ports" in source


def test_comparison_topology_host_uses_explicit_keep_near_membership():
    from visual_director.hermes import _negotiate_comparison_topology

    graph = {
        "layout_intent": {"type": "COMPARISON"},
        "nodes": [
            {"id": "topic", "semantic_role": "COMPARISON_TOPIC"},
            {"id": "left", "semantic_role": "COMPARISON_COLUMN"},
            {"id": "right", "semantic_role": "COMPARISON_COLUMN"},
            {
                "id": "member",
                "semantic_role": "DETAIL",
                "layout_hint": {"keep_near": ["left"]},
            },
        ],
        "relations": [],
    }
    negotiated = _negotiate_comparison_topology(graph, position=0)
    assert negotiated["layout_intent"]["type"] == "COMPARISON"
    generated = [
        relation
        for relation in negotiated["relations"]
        if relation["id"].startswith("host:comparison-membership:")
    ]
    assert generated == [
        {
            "id": "host:comparison-membership:member",
            "source": "member",
            "target": "left",
            "kind": "PART_OF",
            "source_port": "AUTO",
            "target_port": "AUTO",
            "style_refs": ["host.generated.comparison_membership"],
        }
    ]


def test_comparison_topology_host_downgrades_ambiguous_membership():
    from visual_director.hermes import _negotiate_comparison_topology

    graph = {
        "layout_intent": {"type": "COMPARISON"},
        "nodes": [
            {"id": "topic", "semantic_role": "COMPARISON_TOPIC"},
            {"id": "left", "semantic_role": "COMPARISON_COLUMN"},
            {"id": "right", "semantic_role": "COMPARISON_COLUMN"},
            {"id": "member", "semantic_role": "DETAIL"},
        ],
        "relations": [],
        "style_refs": [],
    }
    negotiated = _negotiate_comparison_topology(graph, position=0)
    assert negotiated["layout_intent"]["type"] == "CONCEPT_CARD"
    assert "host.fallback.comparison_to_concept_card" in negotiated["style_refs"]


def test_visual_preflight_only_falls_back_unsatisfiable_comparison_layout():
    source = (
        ROOT / "live_evaluation" / "hermes_runner.py"
    ).read_text(encoding="utf-8")
    helper = source[
        source.index("def _require_frozen_core_layout_compatible"):
        source.index("def _parse_output")
    ]
    assert 'graph.layout_intent.type.value == "COMPARISON"' in helper
    assert "isinstance(exc, LayoutUnsatisfiableError)" in helper
    assert "host.fallback.comparison_layout_to_concept_card" in helper
    assert 'payload["layout_intent"]["type"] = "CONCEPT_CARD"' in helper
    assert "compile_scene_layout(candidate)" in helper
    assert "failures.append((graph.scene_id, fallback_exc))" in helper


def test_visual_parse_returns_core_negotiated_output():
    source = (
        ROOT / "live_evaluation" / "hermes_runner.py"
    ).read_text(encoding="utf-8")
    visual_block = source[
        source.index('if stage == "visual_director":'):
        source.index("return output_model.model_validate_json(candidate)")
    ]
    assert (
        "validated = LiveHermesStructuredRunner."
        "_require_frozen_core_layout_compatible"
    ) in visual_block


def test_visual_style_refs_are_symbolic_only_in_wire_schema():
    from visual_director.hermes import _visual_wire_schema

    schema = _visual_wire_schema(segment_count=1, concept_count=1)
    for name in ("SceneGraph", "SceneNode", "SceneRelation"):
        items = schema["$defs"][name]["properties"]["style_refs"]["items"]
        assert items["pattern"] == r"^[A-Za-z][A-Za-z0-9.-]{0,63}$"


def test_host_drops_only_implementation_bearing_style_refs():
    from visual_director.hermes import _sanitize_symbolic_style_refs

    graph = {
        "style_refs": ["concept.primary", "font-size:18px", "ffmpeg"],
        "nodes": [
            {
                "id": "n1",
                "semantic_role": "DETAIL",
                "style_refs": ["emphasis.high", "position:absolute"],
            }
        ],
        "relations": [
            {
                "id": "r1",
                "source": "n1",
                "target": "n1",
                "kind": "PART_OF",
                "style_refs": ["edge.strong", "x=100"],
            }
        ],
    }
    cleaned = _sanitize_symbolic_style_refs(graph)
    assert cleaned["style_refs"] == ["concept.primary"]
    assert cleaned["nodes"][0]["style_refs"] == ["emphasis.high"]
    assert cleaned["relations"][0]["style_refs"] == ["edge.strong"]
    assert cleaned["nodes"][0]["semantic_role"] == "DETAIL"


def test_paid_luna_is_allowed_only_for_isolated_one_off_workflow(monkeypatch):
    from openrouter_policy import require_free_openrouter_model

    luna = "openai/gpt-6-luna"
    assert require_free_openrouter_model("google/gemma-4-31b-it:free") == "google/gemma-4-31b-it:free"
    monkeypatch.delenv("LEARNFLOW_PAID_PILOT_MODEL", raising=False)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/chatgpt/live-v2d-gpt6-luna-paid-pilot")
    with pytest.raises(ValueError, match="Paid OpenRouter model"):
        require_free_openrouter_model(luna)

    monkeypatch.setenv("LEARNFLOW_PAID_PILOT_MODEL", luna)
    assert require_free_openrouter_model(luna) == luna
    with pytest.raises(ValueError, match="Paid OpenRouter model"):
        require_free_openrouter_model("openai/gpt-6-sol")

    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    with pytest.raises(ValueError, match="Paid OpenRouter model"):
        require_free_openrouter_model(luna)

    monkeypatch.setenv("GITHUB_REF", "refs/heads/chatgpt/live-v2d-gpt6-luna-paid-pilot")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    with pytest.raises(ValueError, match="Paid OpenRouter model"):
        require_free_openrouter_model(luna)


def test_gpt6_luna_probe_omits_unsupported_temperature_but_preserves_strict_tools(monkeypatch):
    from live_evaluation import model_probe

    assert model_probe._probe_sampling_parameters("openai/gpt-6-luna") == {
        "reasoning_effort": "none"
    }
    assert model_probe._probe_sampling_parameters("google/gemma-4-31b-it:free") == {
        "temperature": 0
    }

    requests = []

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(self.payload).encode("utf-8")

    def fake_urlopen(request, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        requests.append(payload)
        if len(requests) == 1:
            return Response({
                "choices": [{
                    "message": {
                        "content": "",
                        "tool_calls": [{
                            "id": "call_test",
                            "type": "function",
                            "function": {"name": "probe_noop", "arguments": "{}"},
                        }],
                    }
                }]
            })
        return Response({
            "choices": [{
                "message": {
                    "content": json.dumps(model_probe._SPECIALIST_PROBE_OBJECT),
                }
            }]
        })

    monkeypatch.setattr(model_probe, "urlopen", fake_urlopen)
    result = model_probe._probe_one(api_key="fake-key", model="openai/gpt-6-luna")
    assert result.passed and result.request_count == 2
    assert len(requests) == 2
    assert all("temperature" not in request for request in requests)
    assert all(request["reasoning_effort"] == "none" for request in requests)
    assert all(request["provider"]["require_parameters"] for request in requests)
    assert requests[0]["tools"][0]["function"]["name"] == "probe_noop"
    assert requests[1]["messages"][2]["tool_call_id"] == "call_test"


def test_gpt6_luna_hermes_agent_inherits_reasoning_none(monkeypatch):
    import sys
    from types import SimpleNamespace
    from live_evaluation.hermes_runner import LiveHermesStructuredRunner

    constructor_args = []

    class FakeAgent:
        def __init__(self, **kwargs):
            constructor_args.append(kwargs)

    monkeypatch.setitem(sys.modules, "run_agent", SimpleNamespace(AIAgent=FakeAgent))
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv(
        "GITHUB_REF", "refs/heads/chatgpt/live-v2d-gpt6-luna-paid-pilot"
    )
    monkeypatch.setenv("LEARNFLOW_PAID_PILOT_MODEL", "openai/gpt-6-luna")

    runner = LiveHermesStructuredRunner(
        model="openai/gpt-6-luna",
        api_key="fake-key",
        repo_root=ROOT,
    )
    for stage in (
        "research_orchestration",
        "pedagogy_agent",
        "script_agent",
        "visual_director",
    ):
        agent = runner._agent(stage=stage)
        assert agent is not None
        assert constructor_args[-1]["model"] == "openai/gpt-6-luna"
        assert constructor_args[-1]["reasoning_config"] == {
            "enabled": False, "effort": "none"
        }
        assert "reasoning_effort" not in constructor_args[-1]["request_overrides"]
        assert "reasoning" not in constructor_args[-1]["request_overrides"]
    assert constructor_args[0]["enabled_toolsets"] == ["delegation", "web"]


def test_gpt6_luna_no_dual_reasoning_encoding_in_hermes_runner_source():
    """Detect the exact HTTP 400 regression seen in governed live V2D #170."""
    source = (ROOT / "live_evaluation" / "hermes_runner.py").read_text(
        encoding="utf-8"
    )
    agent_block = source.split("def _agent(", 1)[1].split("def run(", 1)[0]
    assert "reasoning_config=luna_reasoning_config" in agent_block
    assert 'request_overrides["reasoning_effort"] = "none"' not in agent_block
    assert '"enabled": False, "effort": "none"' in agent_block
