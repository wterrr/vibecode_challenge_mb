"""V3-96 first-child proof and browser paid-request provenance tests, NO GPT transport."""
from __future__ import annotations
import json
from pathlib import Path
import pytest

from scripts.run_v3_96_real_browser_ui_one_gpt import (
    PROMPT,verify_prereg,ORIGINAL_V393_SHA
)
from learnflow_v3.v395_prompt_to_video import supported_query,paid_wire

def test_new_prompt_first_child_preregistered_and_historical_pr_unchanged():
    p=verify_prereg()
    assert p["parent"]["head_sha"]=="cd2f131e2310006078c06052be296256b5488a32"
    assert p["frozen_novel_prompt"]==PROMPT
    assert p["safety"]["prior_successful_V395_CI_required"]["run_id"]==39201973801
    assert p["model"]["one_paid_post_max"]==1 and p["model"]["retry"]==0
    assert p["model"]["estimated_token_cost_max_usd"]=="0.01"
    assert p["safety"]["no_main_merge"] and p["final_release"]=="BLOCKED"
    assert ORIGINAL_V393_SHA=="1060c980edf45213642606c04beb80d3f115ae7dafd920580a778c226238f96a"

def test_new_text_directly_in_new_gpt_request_not_baked_in_model_response():
    assert supported_query(PROMPT)==PROMPT
    assert PROMPT not in (
        "Can a grid of squares measuring 3x4 be rotated to 4x3 and preserve all 12 pieces?",
        "Why does a 3-by-4 array have the same number of objects as a 4-by-3 array?",
    )
    q=json.loads(paid_wire(PROMPT))
    assert q["messages"][1]["content"].endswith(PROMPT)
    assert q["model"]=="openai/gpt-6-luna"
    assert q["max_completion_tokens"]==16000
    assert q["provider"]["allow_fallbacks"] is False
    assert q["response_format"]["json_schema"]["strict"] is True

def test_browser_exercises_actual_html_controls_in_app_not_fake_payload():
    s=Path("scripts/run_v3_96_real_browser_ui_one_gpt.py").read_text()
    for component in (
        'page.goto(host+"/create"',
        'page.locator("#v395-query").fill(PROMPT)',
        'page.locator("#v395-paid-consent").check()',
        'page.locator("#v395-submit").click()',
        'page.locator("#v395-video").get_attribute("src")',
        'resp=context.request.get(host+video_url',
        '"GENUINE_NEW_GPT_POST"',
        '"GENUINE_GPT_NEW_PROMPT_BROWSER_UI_TO_NATIVE_MP4_TECHNICAL_PASS"',
        'decode_movie(mp4)',
        'video_url==result["video_url"]',
    ):
        assert component in s,component
    assert "post_sender" not in s and "catalog_sender" not in s
    assert "mock_model_used" in s

def test_live_guard_no_retries_and_offline_only_no_provider_key():
    w=Path(".github/workflows/v3-96-one-paid-browser-live.yml").read_text()
    assert "GITHUB_RUN_ATTEMPT" in w
    assert "V396_ANOTHER_PAID_RUN_ALREADY_EXISTS" in w
    assert "V396_EXACT_PARENT_BROWSER_PREFLIGHT_NOT_SUCCESS" in w
    assert "research/V396_REAL_BROWSER_ONE_GPT_POST_TRIGGER.txt" in w
    assert "LEARNFLOW_V3_GPT_ARRAY_PREVIEW: 'true'" in w
    assert "OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}" in w
    assert "playwright" in w.lower()
    assert "uvicorn app.main:app" in w
    assert "on:\n  push:" in w
    offline=Path(".github/workflows/v3-96-browser-gpt-offline.yml").read_text()
    assert "OPENROUTER_API_KEY:" not in offline
    assert "--offline --output" in offline
    assert "curl -fsS http://127.0.0.1:8765/create" in offline

@pytest.mark.parametrize("question",[
    "Can 3 by 4 squares convert into 4 by 3 squares while proving history?",
    "Explain photosynthesis with 3x4 and 4x3 arrays of squares.",
    "Use 3x4 squares to model 4x3 squares and discuss credit cards."
])
def test_no_network_on_mixed_topic(question):
    from learnflow_v3.v395_prompt_to_video import PreviewRejected
    with pytest.raises(PreviewRejected):
        supported_query(question)
