#!/usr/bin/env python3
"""Run one governed live V2D lesson using the repository OpenRouter secret."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live_evaluation import DEFAULT_LIVE_MODEL, PILOT_TOPIC_ID, run_live_v2d_pilot


def _safe_error(exc: BaseException, secret: str) -> str:
    text = f"{type(exc).__name__}: {exc}"
    if secret:
        text = text.replace(secret, "<redacted>")
    return text[-2000:]


def main() -> int:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        print("LIVE_V2D_PILOT=BLOCKED reason=OPENROUTER_API_KEY missing", file=sys.stderr)
        return 2

    model = os.environ.get("LEARNFLOW_LIVE_MODEL", DEFAULT_LIVE_MODEL).strip()
    topic_id = os.environ.get("LEARNFLOW_LIVE_TOPIC_ID", PILOT_TOPIC_ID).strip()
    runtime = ROOT / ".hermes_runtime" / "live-v2d-evaluation"

    try:
        report = run_live_v2d_pilot(
            api_key=key,
            model=model,
            topic_id=topic_id,
            runtime_root=runtime,
        )
    except BaseException as exc:
        runtime.mkdir(parents=True, exist_ok=True)
        failure = {
            "schema_version": "1.0",
            "evaluation": "governed-live-v2d-pilot",
            "topic_id": topic_id,
            "model": model,
            "success": False,
            "error": _safe_error(exc, key),
        }
        (runtime / "pilot_failure.json").write_text(
            json.dumps(failure, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"LIVE_V2D_PILOT=FAIL reason={failure['error']}", file=sys.stderr)
        traceback.print_exc()
        return 1

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
