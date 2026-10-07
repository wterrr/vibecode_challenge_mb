"""OpenRouter model policy for LearnFlow-owned live calls.

The borrowed OpenRouter credential may have paid balance. LearnFlow therefore
fails closed unless every explicitly selected OpenRouter model uses the :free
variant.
"""

from __future__ import annotations


def require_free_openrouter_model(model: str) -> str:
    value = str(model or "").strip()
    if not value:
        raise ValueError("OpenRouter model must not be empty")
    if not value.lower().endswith(":free"):
        raise ValueError(
            f"Paid OpenRouter model is forbidden by LearnFlow policy: {value!r}"
        )
    return value
