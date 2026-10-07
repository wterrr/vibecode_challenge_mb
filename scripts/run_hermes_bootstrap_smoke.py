#!/usr/bin/env python3
"""Hermes bootstrap smoke runner."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
STATUS_PATH = ROOT / "hermes" / "bootstrap" / "status.json"
CONFIG_TEMPLATE = ROOT / "hermes" / "bootstrap" / "config.yaml"
RUNTIME = ROOT / ".hermes_runtime"
HERMES_HOME = RUNTIME / "home"
INSTALL_DIR = RUNTIME / "hermes-agent"
BOOTSTRAP_RESULT_DIR = RUNTIME / "bootstrap"

PRIMARY_MODEL = "nvidia/nemotron-3.5-lightning:free"
FREE_FALLBACK_MODELS = (
    "google/gemma-4-31b-it:free",
    "poolside/laguna-s-2.1:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "apodex/apodex-1.1-mini:free",
)
ALLOWED_LIVE_MODELS = (PRIMARY_MODEL, *FREE_FALLBACK_MODELS)
EXPECTED_SENTINEL = "HERMES_BOOTSTRAP_OK:LEARNFLOW-BOOTSTRAP-FIXTURE-v1"


class SmokeValidationError(RuntimeError):
    pass


def load_status() -> dict[str, Any]:
    return json.loads(STATUS_PATH.read_text(encoding="utf-8"))


def load_project_openrouter_key(env: dict[str, str]) -> None:
    if env.get("OPENROUTER_API_KEY"):
        return
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != "OPENROUTER_API_KEY":
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if value:
            env["OPENROUTER_API_KEY"] = value
        return


def parse_stream_json(text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SmokeValidationError(
                f"line {line_no} is not valid JSON: {exc.msg}"
            ) from exc
        if not isinstance(item, dict):
            raise SmokeValidationError(f"line {line_no} is not a JSON object")
        events.append(item)
    if not events:
        raise SmokeValidationError("empty stream")
    return events


def validate_events(
    events: list[dict[str, Any]], expected_model: str
) -> dict[str, Any]:
    init = next(
        (
            event
            for event in events
            if event.get("type") == "system" and event.get("subtype") == "init"
        ),
        None,
    )
    if init is None:
        raise SmokeValidationError("missing system/init event")
    if init.get("model") != expected_model:
        raise SmokeValidationError(
            f"wrong model: expected {expected_model!r}, got {init.get('model')!r}"
        )

    tool_uses = [event for event in events if event.get("type") == "tool_use"]
    tool_results = [event for event in events if event.get("type") == "tool_result"]
    if not tool_uses:
        raise SmokeValidationError("agent did not call a tool")
    if not tool_results:
        raise SmokeValidationError("tool call has no tool_result")

    successful_result = None
    for use in tool_uses:
        for result in tool_results:
            same_id = bool(
                use.get("tool_call_id")
                and use.get("tool_call_id") == result.get("tool_call_id")
            )
            same_name = bool(
                not use.get("tool_call_id")
                and use.get("name") == result.get("name")
            )
            if (same_id or same_name) and not result.get("is_error", False):
                successful_result = result
                break
        if successful_result is not None:
            break
    if successful_result is None:
        raise SmokeValidationError("no successful tool_use -> tool_result pair")

    terminal = next(
        (event for event in reversed(events) if event.get("type") == "result"),
        None,
    )
    if terminal is None:
        raise SmokeValidationError("missing terminal result event")
    if terminal.get("exit_code") != 0:
        raise SmokeValidationError(
            f"Hermes result exit_code is {terminal.get('exit_code')!r}"
        )
    final_text = str(terminal.get("text") or "")
    if EXPECTED_SENTINEL not in final_text:
        raise SmokeValidationError(
            f"final result missing sentinel {EXPECTED_SENTINEL!r}"
        )
    session_id = str(terminal.get("session_id") or "")
    if not session_id:
        raise SmokeValidationError("terminal result missing session_id")

    return {
        "session_id": session_id,
        "model": init.get("model"),
        "tool_name": successful_result.get("name"),
        "tokens": terminal.get("tokens", {}),
        "duration_ms": terminal.get("duration_ms"),
        "final_text": final_text,
    }


def detect_hermes_binary() -> str:
    explicit = os.environ.get("HERMES_BIN")
    if explicit:
        return explicit
    candidates = [
        INSTALL_DIR / "venv" / "bin" / "hermes",
        INSTALL_DIR / "venv" / "Scripts" / "hermes.exe",
        INSTALL_DIR / ".venv" / "bin" / "hermes",
        INSTALL_DIR / ".venv" / "Scripts" / "hermes.exe",
        INSTALL_DIR / ".venv" / "Scripts" / "hermes-script.py",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise SmokeValidationError(
        "Pinned project-local Hermes binary not found. Run "
        "scripts/install_hermes_bootstrap.sh or scripts/install_hermes_bootstrap.ps1 first."
    )


def verify_installed_pin(status: dict[str, Any]) -> str:
    if not (INSTALL_DIR / ".git").exists():
        raise SmokeValidationError(
            f"project-local Hermes checkout missing: {INSTALL_DIR}"
        )
    proc = subprocess.run(
        ["git", "-C", str(INSTALL_DIR), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SmokeValidationError(
            f"cannot read Hermes checkout HEAD: {proc.stderr.strip()}"
        )
    actual = proc.stdout.strip()
    expected = status["hermes"]["commit"]
    if actual != expected:
        raise SmokeValidationError(
            f"Hermes checkout is not pinned: expected {expected}, got {actual}"
        )
    return actual


def ensure_runtime_config() -> None:
    HERMES_HOME.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CONFIG_TEMPLATE, HERMES_HOME / "config.yaml")


def export_trajectory(
    hermes_bin: str, env: dict[str, str], session_id: str
) -> Path:
    BOOTSTRAP_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    path = BOOTSTRAP_RESULT_DIR / "trajectory.jsonl"
    if path.exists():
        path.unlink()
    proc = subprocess.run(
        [
            hermes_bin,
            "sessions",
            "export",
            str(path),
            "--session-id",
            session_id,
            "--format",
            "jsonl",
            "--redact",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SmokeValidationError(
            "trajectory export failed: "
            + (proc.stderr.strip() or proc.stdout.strip())
        )
    if not path.is_file() or path.stat().st_size == 0:
        raise SmokeValidationError("trajectory export produced no JSONL artifact")
    return path


def smoke_prompt() -> str:
    return (
        "LearnFlow Hermes Bootstrap read-only smoke test. "
        "Use a file-reading tool to read hermes/bootstrap/tool_read_fixture.txt. "
        "Do not edit or create repository files. "
        "After the tool succeeds, answer exactly "
        f"{EXPECTED_SENTINEL}"
    )


def run_model_attempt(
    hermes_bin: str, env: dict[str, str], model: str
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any] | None, str | None]:
    command = [
        hermes_bin,
        "chat",
        "--provider",
        "openrouter",
        "--model",
        model,
        "--toolsets",
        "file",
        "--source",
        "tool",
        "--max-turns",
        "6",
        "-q",
        smoke_prompt(),
        "--format",
        "stream-json",
    ]
    proc = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    try:
        events = parse_stream_json(proc.stdout)
        summary = validate_events(events, model)
    except SmokeValidationError as exc:
        return proc, None, str(exc)

    if proc.returncode != 0:
        return proc, None, f"Hermes process exit code {proc.returncode}"
    return proc, summary, None


def safe_failure_note(
    proc: subprocess.CompletedProcess[str], error: str | None, env: dict[str, str]
) -> str:
    note = error or f"exit_code={proc.returncode}"
    stderr = proc.stderr.strip()
    if stderr:
        note = f"{note}; stderr={stderr[-600:]}"
    key = env.get("OPENROUTER_API_KEY")
    if key:
        note = note.replace(key, "<redacted>")
    return note.replace("\n", " ")


def run_live(selected_model: str | None = None) -> int:
    status = load_status()
    env = os.environ.copy()
    load_project_openrouter_key(env)
    if not env.get("OPENROUTER_API_KEY"):
        print(
            "HERMES_BOOTSTRAP_LIVE=BLOCKED reason=OPENROUTER_API_KEY missing; "
            "set it in the ignored .env or process environment",
            file=sys.stderr,
        )
        return 2

    verify_installed_pin(status)
    ensure_runtime_config()
    hermes_bin = detect_hermes_binary()

    BOOTSTRAP_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    env["HERMES_HOME"] = str(HERMES_HOME)

    if selected_model is not None:
        if selected_model not in ALLOWED_LIVE_MODELS:
            print(
                "HERMES_BOOTSTRAP_LIVE=BLOCKED reason=model is outside the Hermes Bootstrap allowlist",
                file=sys.stderr,
            )
            return 2
        models = [selected_model]
    else:
        models = list(ALLOWED_LIVE_MODELS)

    attempts: list[dict[str, Any]] = []
    passed_proc: subprocess.CompletedProcess[str] | None = None
    passed_summary: dict[str, Any] | None = None
    passed_model: str | None = None

    for model in models:
        require_free_openrouter_model(model)
        proc, summary, error = run_model_attempt(hermes_bin, env, model)
        attempts.append(
            {
                "model": model,
                "passed": summary is not None,
                "failure": None if summary is not None else safe_failure_note(
                    proc, error, env
                ),
            }
        )
        if summary is not None:
            passed_proc = proc
            passed_summary = summary
            passed_model = model
            break
        print(
            f"HERMES_BOOTSTRAP_MODEL_ATTEMPT=FAIL model={model} "
            f"reason={attempts[-1]['failure']}",
            file=sys.stderr,
        )

    if passed_proc is None or passed_summary is None or passed_model is None:
        print("HERMES_BOOTSTRAP_LIVE=FAIL reason=all allowed model attempts failed", file=sys.stderr)
        return 1

    stream_path = BOOTSTRAP_RESULT_DIR / "smoke_stream.jsonl"
    stream_path.write_text(passed_proc.stdout, encoding="utf-8")

    trajectory_path = export_trajectory(
        hermes_bin, env, passed_summary["session_id"]
    )
    result = {
        "stage": "hermes-bootstrap",
        "state": "PASS",
        "hermes_commit": status["hermes"]["commit"],
        "provider": "openrouter",
        "model": passed_model,
        "fallback_used": passed_model != PRIMARY_MODEL,
        "attempted_models": [attempt["model"] for attempt in attempts],
        "session_id": passed_summary["session_id"],
        "tool_name": passed_summary["tool_name"],
        "tokens": passed_summary["tokens"],
        "duration_ms": passed_summary["duration_ms"],
        "stream_path": str(stream_path.relative_to(ROOT)),
        "trajectory_path": str(trajectory_path.relative_to(ROOT)),
    }
    result_path = BOOTSTRAP_RESULT_DIR / "result.json"
    result_path.write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print("HERMES_BOOTSTRAP_LIVE=PASS")
    print(json.dumps(result, indent=2))
    return 0


def run_offline(path: Path, expected_model: str) -> int:
    try:
        summary = validate_events(
            parse_stream_json(path.read_text(encoding="utf-8")),
            expected_model,
        )
    except (OSError, SmokeValidationError) as exc:
        print(f"HERMES_BOOTSTRAP_OFFLINE=FAIL reason={exc}", file=sys.stderr)
        return 1
    print("HERMES_BOOTSTRAP_OFFLINE=PASS")
    print(json.dumps(summary, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--offline-fixture",
        type=Path,
        help="validate a captured stream-json fixture without running Hermes",
    )
    parser.add_argument(
        "--model",
        choices=ALLOWED_LIVE_MODELS,
        help=(
            "run only one accepted free Hermes Bootstrap model; default live mode tries "
            "the free-only allowlist in order"
        ),
    )
    args = parser.parse_args()
    if args.offline_fixture is not None:
        return run_offline(args.offline_fixture, args.model or PRIMARY_MODEL)
    return run_live(args.model)


if __name__ == "__main__":
    sys.exit(main())
