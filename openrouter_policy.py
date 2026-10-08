"""OpenRouter model policy for LearnFlow-owned live calls.

Paid calls are forbidden by default. The single user-authorized GPT-6 Luna
experiment requires three matching GitHub Actions environment conditions and
is isolated to its own branch. The production main branch stays free-only.
"""

from __future__ import annotations

import os

PAID_PILOT_MODEL = "openai/gpt-6-luna"
PAID_PILOT_REF = "refs/heads/chatgpt/live-v2d-gpt6-luna-paid-pilot"


def require_free_openrouter_model(model: str) -> str:
    value = str(model or "").strip()
    if not value:
        raise ValueError("OpenRouter model must not be empty")
    if value.lower().endswith(":free"):
        return value
    if (
        value == PAID_PILOT_MODEL
        and os.environ.get("LEARNFLOW_PAID_PILOT_MODEL") == PAID_PILOT_MODEL
        and os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("GITHUB_REF") == PAID_PILOT_REF
    ):
        return value
    raise ValueError(
        f"Paid OpenRouter model is forbidden by LearnFlow policy: {value!r}"
    )
