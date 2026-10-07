"""One-topic live V2D pilot on the frozen LearnFlowBench corpus."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any

from agent_contracts import (
    BudgetLedger,
    BudgetLimits,
    BudgetSpend,
    BudgetUsage,
    LearningBrief,
)
from learnflow_bench import load_corpus
from runtime_governance import GovernanceState

from .hermes_runner import LiveHermesStructuredRunner
from .model_probe import LIVE_MODEL_CANDIDATES

ROOT = Path(__file__).resolve().parents[1]
PILOT_TOPIC_ID = "lfb-001-cs"
DEFAULT_LIVE_MODEL = LIVE_MODEL_CANDIDATES[0]


def _load_capability_plugin():
    plugin_dir = ROOT / ".hermes" / "plugins" / "learnflow"
    package_name = "learnflow_live_eval_capability"
    for name in list(sys.modules):
        if name == package_name or name.startswith(package_name + "."):
            del sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        package_name,
        plugin_dir / "__init__.py",
        submodule_search_locations=[str(plugin_dir)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load LearnFlow capability plugin")
    module = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = module
    spec.loader.exec_module(module)
    return module


def build_pilot_brief(topic_id: str = PILOT_TOPIC_ID) -> LearningBrief:
    corpus = load_corpus()
    topic = next((item for item in corpus.topics if item.topic_id == topic_id), None)
    if topic is None:
        raise KeyError(f"frozen LearnFlowBench topic not found: {topic_id}")
    return LearningBrief(
        brief_id=f"live-eval:{topic.topic_id}",
        user_query=topic.query,
        learner_level=topic.learner_level,
        target_duration_minutes=topic.target_duration_minutes,
        language=topic.language,
        constraints=(
            "Use only the frozen benchmark topic as the lesson request.",
            "Do not publish or upload the output.",
            "Preserve provenance and all accepted typed stage gates.",
        ),
    )


def initialize_governance_state(
    path: str | Path,
    *,
    runtime_model_attempts: int | None = None,
) -> GovernanceState:
    model_attempts = (
        len(LIVE_MODEL_CANDIDATES)
        if runtime_model_attempts is None
        else max(1, int(runtime_model_attempts))
    )
    state = GovernanceState(
        state_id="live-eval.pilot",
        budget=BudgetLedger(
            ledger_id="live-eval.pilot",
            max_usd=None,
            spent=BudgetSpend(),
            limits=BudgetLimits(
                # Each runtime model attempt may launch the same three sealed
                # research specialists. Provider/model fallback keeps one
                # cumulative governance ledger, so the cap must bound the full
                # candidate sequence rather than only the first attempt.
                subagent_calls=3 * model_attempts,
                vlm_repairs=0,
                image_generations=0,
                tool_calls=32,
                provider_attempts=1600,
                retries=4,
            ),
            usage=BudgetUsage(),
        ),
        publication_authorized=False,
    )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(state.to_canonical_json(), encoding="utf-8")
    return state


def _governance_event_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "event_count": 0,
            "post_api_requests": 0,
            "api_errors": 0,
            "provider_attempts": 0,
            "tool_calls": 0,
            "blocked_tool_calls": 0,
            "subagent_starts": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "observed_cost_usd": 0.0,
        }
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    api = [row for row in rows if row.get("event") == "post_api_request"]
    api_errors = [row for row in rows if row.get("event") == "api_request_error"]
    tool_attempts = [row for row in rows if row.get("event") == "pre_tool_call"]
    return {
        "event_count": len(rows),
        "post_api_requests": len(api),
        "api_errors": len(api_errors),
        "provider_attempts": len(api) + len(api_errors),
        "tool_calls": sum(not bool(row.get("blocked")) for row in tool_attempts),
        "blocked_tool_calls": sum(bool(row.get("blocked")) for row in tool_attempts),
        "subagent_starts": sum(row.get("event") == "subagent_start" for row in rows),
        "input_tokens": sum(int(row.get("input_tokens") or 0) for row in api),
        "output_tokens": sum(int(row.get("output_tokens") or 0) for row in api),
        "observed_cost_usd": round(
            sum(float(row.get("estimated_cost_usd") or 0.0) for row in api),
            8,
        ),
        "cost_statuses": sorted(
            {str(row.get("cost_status") or "unknown") for row in api}
        ),
    }


def _reset_runtime_preserving_hermes_home(
    runtime: Path,
    *,
    preserve_governance: bool = False,
) -> None:
    """Clear pilot-owned artifacts without deleting the active Hermes profile.

    When a provider fallback re-runs the pilot, keep governance state/events so
    usage accounting remains cumulative across failed model attempts.
    """

    runtime = runtime.resolve()
    raw_home = str(os.environ.get("HERMES_HOME") or "").strip()
    hermes_home = Path(raw_home).expanduser().resolve() if raw_home else None

    if not runtime.exists():
        runtime.mkdir(parents=True, exist_ok=True)
        return

    for child in runtime.iterdir():
        child_resolved = child.resolve()
        preserves_hermes = (
            hermes_home is not None
            and (
                child_resolved == hermes_home
                or child_resolved in hermes_home.parents
            )
        )
        preserves_governance = (
            preserve_governance
            and child.name == "governance"
        )
        if preserves_hermes or preserves_governance:
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    runtime.mkdir(parents=True, exist_ok=True)


def run_live_v2d_pilot(
    *,
    api_key: str,
    model: str = DEFAULT_LIVE_MODEL,
    topic_id: str = PILOT_TOPIC_ID,
    runtime_root: str | Path | None = None,
    preserve_governance: bool = False,
) -> dict[str, Any]:
    runtime = (
        Path(runtime_root).resolve()
        if runtime_root is not None
        else (ROOT / ".hermes_runtime" / "live-v2d-evaluation").resolve()
    )
    _reset_runtime_preserving_hermes_home(
        runtime,
        preserve_governance=preserve_governance,
    )

    state_path = runtime / "governance" / "state.json"
    events_path = runtime / "governance" / "events.jsonl"
    os.environ["LEARNFLOW_GOVERNANCE_STATE"] = str(state_path)
    os.environ["LEARNFLOW_GOVERNANCE_EVENTS"] = str(events_path)
    os.environ["HERMES_ENABLE_PROJECT_PLUGINS"] = "true"
    if not preserve_governance or not state_path.is_file():
        initialize_governance_state(state_path)

    from lesson_pipeline import CapabilityCoreGateway, run_lesson_pipeline

    brief = build_pilot_brief(topic_id)
    runner = LiveHermesStructuredRunner(
        model=model,
        api_key=api_key,
        repo_root=ROOT,
    )
    plugin = _load_capability_plugin()
    gateway = CapabilityCoreGateway(
        create=plugin.handle_create,
        run=plugin.handle_run,
        render=plugin.handle_render,
        repo_root=ROOT,
    )

    result = run_lesson_pipeline(
        brief,
        runner=runner,
        core_gateway=gateway,
        runtime_root=runtime / "lesson-runs",
    )

    # The first Core pass above is a semantic/capability integration pass. The
    # production media pass reuses the accepted typed artifacts, adds real TTS,
    # narration-resolved Tier-1 motion, inter-scene transitions, subtitles, and
    # a fail-closed output-quality gate. Keep these imports lazy so the offline
    # contract job does not need network speech dependencies.
    import asyncio
    from app.providers.speech.edge import EdgeSpeechProvider
    from learnflow_v2.render import SubtitleRenderCue
    from lesson_pipeline.production import (
        SynthesizedNarration,
        build_production_media,
        probe_media_duration,
    )

    speech = EdgeSpeechProvider(timeout=60.0)

    def synthesize_narration(text: str, output_path: Path, language: str) -> SynthesizedNarration:
        speech_result = asyncio.run(
            speech.synthesize(text, output_path, language)
        )
        duration = (
            float(speech_result.duration_seconds)
            if speech_result.duration_seconds is not None
            else probe_media_duration(speech_result.path)
        )
        cues = tuple(
            SubtitleRenderCue(
                start_seconds=float(cue.start_seconds),
                end_seconds=float(cue.end_seconds),
                text=cue.text,
            )
            for cue in speech_result.subtitle_cues
            if float(cue.end_seconds) > float(cue.start_seconds)
        )
        return SynthesizedNarration(
            path=Path(speech_result.path),
            duration_seconds=duration,
            subtitle_cues=cues,
            provider=speech_result.provider,
        )

    production = build_production_media(
        result,
        create=plugin.handle_create,
        run=plugin.handle_run,
        render=plugin.handle_render,
        repo_root=ROOT,
        synthesize_narration=synthesize_narration,
    )
    result = result.model_copy(update={"final_video": production.final_video})

    state = GovernanceState.model_validate_json(state_path.read_text(encoding="utf-8"))
    report = {
        "schema_version": "1.0",
        "evaluation": "governed-live-v2d-pilot",
        "topic_id": topic_id,
        "model": model,
        "success": True,
        "run_id": result.run_id,
        "scene_count": len(result.scenegraphs),
        "final_video": result.final_video.path,
        "final_video_exists": Path(result.final_video.path).is_file(),
        "fact_approved_claims": len(result.fact_verification.approved_claim_ids),
        "fact_blocked_claims": len(result.fact_verification.blocked_claim_ids),
        "objective_count": len(result.pedagogy_plan.learning_objectives),
        "script_segment_count": len(result.lesson_script.segments),
        "runner_usage": runner.usage_summary(),
        "governance_events": _governance_event_summary(events_path),
        "budget": (
            None
            if state.budget is None
            else state.budget.model_dump(mode="json")
        ),
        "publication_authorized": state.publication_authorized,
        "production_output_gate": production.report,
    }
    report_path = runtime / "pilot_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    secret = api_key.strip()
    for path in (report_path, events_path, state_path):
        if path.is_file() and secret and secret in path.read_text(encoding="utf-8"):
            raise RuntimeError(f"secret material leaked into evaluation artifact: {path}")

    return report
