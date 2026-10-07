#!/usr/bin/env python3
"""Run one governed live V2D lesson using the repository OpenRouter secret."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from live_evaluation import (
    LIVE_MODEL_CANDIDATES,
    ModelProbeError,
    PILOT_TOPIC_ID,
    initialize_governance_state,
    run_live_v2d_pilot,
    select_live_model,
)
from agent_contracts import BudgetUsage
from runtime_governance import BudgetCharge, HardBudgetController, SpendCategory
from runtime_governance.hermes_plugin import load_state, save_state


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


def _retryable_research_model_incompatibility(exc: BaseException) -> bool:
    """Hop free models only for leaf-output failures attributable to model behavior.

    Keep this deliberately narrow so application/contract bugs still fail closed.
    """

    text = f"{type(exc).__name__}: {exc}"
    if not any(marker in text for marker in _RESEARCH_FAILURE_MARKERS):
        return False
    lowered = text.lower()
    return bool(
        "failed output schema validation" in lowered
        or "response stopped" in lowered and "repetition" in lowered
        or "repetition detected" in lowered
    )


def _probe_request_count(probes) -> int:
    return sum(max(1, int(getattr(item, "request_count", 1) or 1)) for item in probes)



def _charge_probe_attempts(count: int) -> None:
    if count <= 0:
        return
    state = load_state()
    if state.budget is None:
        raise RuntimeError("live evaluation governance budget is not initialized")
    controller = HardBudgetController(state.budget)
    controller.authorize(
        BudgetCharge(
            charge_id=f"live-eval:model-probe:{count}",
            category=SpendCategory.LLM,
            amount_usd=0.0,
            usage=BudgetUsage(provider_attempts=count),
            reason=f"reserve {count} OpenRouter capability probe attempt(s)",
        )
    )
    save_state(
        state.model_copy(update={"budget": controller.ledger})
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
    governance_root = runtime / "governance"
    if governance_root.exists():
        shutil.rmtree(governance_root)
    state_path = governance_root / "state.json"
    events_path = governance_root / "events.jsonl"
    os.environ["LEARNFLOW_GOVERNANCE_STATE"] = str(state_path)
    os.environ["LEARNFLOW_GOVERNANCE_EVENTS"] = str(events_path)
    initialize_governance_state(state_path)

    selection = None
    probe_rows: list[dict] = []
    runtime_fallbacks: list[dict] = []
    remaining = tuple(candidates)
    report = None
    model = candidates[0] if candidates else "<none>"

    try:
        while remaining:
            try:
                selection = select_live_model(api_key=key, candidates=remaining)
            except ModelProbeError as probe_exc:
                _charge_probe_attempts(_probe_request_count(probe_exc.probes))
                raise
            _charge_probe_attempts(_probe_request_count(selection.probes))
            probe_rows.extend(item.to_dict() for item in selection.probes)
            model = selection.selected_model
            print(f"LIVE_MODEL_PROBE=PASS selected={model}")
            try:
                report = run_live_v2d_pilot(
                    api_key=key,
                    model=model,
                    topic_id=topic_id,
                    runtime_root=runtime,
                    preserve_governance=True,
                )
                break
            except BaseException as runtime_exc:
                provider_failure = _retryable_research_provider_failure(runtime_exc)
                model_incompatible = _retryable_research_model_incompatibility(
                    runtime_exc
                )
                if not provider_failure and not model_incompatible:
                    raise
                fallback_status = (
                    "research_provider_unavailable"
                    if provider_failure
                    else "research_model_incompatible"
                )
                runtime_fallbacks.append(
                    {
                        "model": model,
                        "status": fallback_status,
                        "error": _safe_error(runtime_exc, key),
                    }
                )
                print(
                    "LIVE_MODEL_RUNTIME_FALLBACK "
                    f"model={model} status={fallback_status} "
                    f"reason={_safe_error(runtime_exc, key)}",
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
        "production_output_gate": report["production_output_gate"],
    }
    print("LIVE_V2D_PILOT=PASS")
    print(json.dumps(safe, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
