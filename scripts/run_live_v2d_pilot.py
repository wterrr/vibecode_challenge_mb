#!/usr/bin/env python3
"""Run one governed live V2D lesson using the repository OpenRouter secret."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live_evaluation import (
    LIVE_MODEL_CANDIDATES,
    ModelProbeError,
    PILOT_TOPIC_ID,
    run_live_v2d_pilot,
    select_live_model,
)


def _safe_error(exc: BaseException, secret: str) -> str:
    text = f"{type(exc).__name__}: {exc}"
    if secret:
        text = text.replace(secret, "<redacted>")
    return text[-2000:]


_RETRYABLE_PROVIDER_HTTP = re.compile(
    r"\bHTTP\s+(?:404|408|425|429|500|502|503|504)\b",
    re.IGNORECASE,
)
_RESEARCH_FAILURE_MARKERS = (
    "CONCEPT_RESEARCHER",
    "EVIDENCE_RESEARCHER",
    "MISCONCEPTION_RESEARCHER",
    "research fan-out",
)


def _retryable_research_provider_failure(exc: BaseException) -> bool:
    """Only hop models for transient/unavailable provider failures in Research."""

    text = f"{type(exc).__name__}: {exc}"
    if not any(marker in text for marker in _RESEARCH_FAILURE_MARKERS):
        return False
    lowered = text.lower()
    return bool(
        _RETRYABLE_PROVIDER_HTTP.search(text)
        or "rate limited" in lowered
        or "model is unavailable" in lowered
    )


def main() -> int:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        print("LIVE_V2D_PILOT=BLOCKED reason=OPENROUTER_API_KEY missing", file=sys.stderr)
        return 2

    configured = os.environ.get("LEARNFLOW_LIVE_MODEL_CANDIDATES", "").strip()
    candidates = (
        tuple(item.strip() for item in configured.split(",") if item.strip())
        if configured
        else LIVE_MODEL_CANDIDATES
    )
    topic_id = os.environ.get("LEARNFLOW_LIVE_TOPIC_ID", PILOT_TOPIC_ID).strip()
    runtime = ROOT / ".hermes_runtime" / "live-v2d-evaluation"
    selection = None
    probe_rows: list[dict] = []
    runtime_fallbacks: list[dict] = []
    remaining = tuple(candidates)
    report = None
    model = candidates[0] if candidates else "<none>"

    try:
        while remaining:
            selection = select_live_model(api_key=key, candidates=remaining)
            probe_rows.extend(item.to_dict() for item in selection.probes)
            model = selection.selected_model
            print(f"LIVE_MODEL_PROBE=PASS selected={model}")
            try:
                report = run_live_v2d_pilot(
                    api_key=key,
                    model=model,
                    topic_id=topic_id,
                    runtime_root=runtime,
                )
                break
            except BaseException as runtime_exc:
                if not _retryable_research_provider_failure(runtime_exc):
                    raise
                runtime_fallbacks.append(
                    {
                        "model": model,
                        "status": "research_provider_unavailable",
                        "error": _safe_error(runtime_exc, key),
                    }
                )
                print(
                    "LIVE_MODEL_RUNTIME_FALLBACK "
                    f"model={model} reason={_safe_error(runtime_exc, key)}",
                    file=sys.stderr,
                )
                selected_index = remaining.index(model)
                remaining = remaining[selected_index + 1 :]
                selection = None

        if report is None:
            raise ModelProbeError(
                "no live model remained after runtime provider fallbacks",
                (),
            )
    except BaseException as exc:
        runtime.mkdir(parents=True, exist_ok=True)
        if isinstance(exc, ModelProbeError):
            probe_rows.extend(item.to_dict() for item in exc.probes)
        failure = {
            "schema_version": "1.0",
            "evaluation": "governed-live-v2d-pilot",
            "topic_id": topic_id,
            "model": model,
            "success": False,
            "error": _safe_error(exc, key),
            "model_probe": probe_rows,
            "runtime_fallbacks": runtime_fallbacks,
        }
        (runtime / "pilot_failure.json").write_text(
            json.dumps(failure, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"LIVE_V2D_PILOT=FAIL reason={failure['error']}", file=sys.stderr)
        traceback.print_exc()
        return 1

    (runtime / "model_probe.json").write_text(
        json.dumps(
            {
                "selected_model": model,
                "probes": probe_rows,
                "runtime_fallbacks": runtime_fallbacks,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    safe = {
        "topic_id": report["topic_id"],
        "model": report["model"],
        "success": report["success"],
        "scene_count": report["scene_count"],
        "fact_approved_claims": report["fact_approved_claims"],
        "fact_blocked_claims": report["fact_blocked_claims"],
        "objective_count": report["objective_count"],
        "script_segment_count": report["script_segment_count"],
        "runner_usage": report["runner_usage"],
        "governance_events": report["governance_events"],
        "budget": report["budget"],
        "publication_authorized": report["publication_authorized"],
    }
    print("LIVE_V2D_PILOT=PASS")
    print(json.dumps(safe, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
