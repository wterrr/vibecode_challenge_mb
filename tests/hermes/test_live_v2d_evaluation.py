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


def test_default_live_model_is_accepted_free_fallback():
    assert DEFAULT_LIVE_MODEL == "nvidia/nemotron-3.5-lightning:free"


def test_governance_state_is_fail_closed(tmp_path):
    state = initialize_governance_state(tmp_path / "state.json")
    assert state.publication_authorized is False
    assert state.budget is not None
    assert state.budget.max_usd == 0.25
    assert state.budget.limits.subagent_calls == 3
    assert state.budget.limits.tool_calls == 32
    assert state.budget.limits.provider_attempts == 16
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


def test_primary_reservations_fit_under_hard_usd_cap():
    total = sum(
        float(item["usd"])
        for item in LiveHermesStructuredRunner._STAGE_RESERVATIONS.values()
    )
    assert total == pytest.approx(0.20)
    assert total < 0.25


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
