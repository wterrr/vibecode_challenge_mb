#!/usr/bin/env python3
"""Verify H-02 through the real pinned Hermes plugin registry and handlers."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERIFY_HOME = ROOT / ".hermes_runtime" / "h02" / "verify-home"
SMOKE_RUNTIME = ROOT / ".hermes_runtime" / "h02" / "registry-smoke-runs"
EXPECTED_TOOLS = {"learnflow_create", "learnflow_run", "learnflow_render"}


def _decode(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError(f"expected object tool result, got {type(value).__name__}")
    return value


def _require_success(name: str, raw) -> dict:
    payload = _decode(raw)
    if payload.get("success") is not True:
        raise RuntimeError(f"{name} failed: {payload}")
    return payload


def _smoke_scene() -> dict:
    return {
        "schema_version": "2.1",
        "scene_id": "h02_pinned_registry_smoke",
        "purpose": "EXPLAIN",
        "concept": "Gradient descent",
        "nodes": [
            {
                "id": "title",
                "kind": "CONCEPT",
                "label": "Gradient descent",
                "semantic_role": "PRIMARY_CONCEPT",
                "style_refs": [],
            }
        ],
        "relations": [],
        "groups": [],
        "layout_intent": {
            "type": "CONCEPT_CARD",
            "reading_direction": "LEFT_TO_RIGHT",
        },
        "style_refs": [],
    }


def _prepare_home_if_needed(home: Path) -> None:
    """Fallback for direct invocations; CI normally prepares/enables this home first."""
    config_path = home / "config.yaml"
    if config_path.exists():
        return
    home.mkdir(parents=True, exist_ok=True)
    base_config = (ROOT / "hermes" / "h01" / "config.yaml").read_text(encoding="utf-8").rstrip()
    config_path.write_text(
        base_config + "\n\nplugins:\n  enabled:\n    - learnflow\n",
        encoding="utf-8",
    )


def main() -> int:
    os.chdir(ROOT)
    home = Path(os.environ.get("HERMES_HOME") or DEFAULT_VERIFY_HOME).expanduser().resolve()
    _prepare_home_if_needed(home)

    os.environ["HERMES_HOME"] = str(home)
    os.environ["HERMES_ENABLE_PROJECT_PLUGINS"] = "true"
    os.environ["LEARNFLOW_H02_RUNTIME_ROOT"] = str(SMOKE_RUNTIME)
    shutil.rmtree(SMOKE_RUNTIME, ignore_errors=True)

    from hermes_cli.plugins import discover_plugins, get_plugin_manager
    from tools.registry import registry

    discover_plugins(force=True)
    rows = get_plugin_manager().list_plugins()
    matches = [row for row in rows if row.get("name") == "learnflow"]
    if len(matches) != 1:
        raise SystemExit(f"H02_PLUGIN_DISCOVERY=FAIL expected one learnflow plugin, got {matches!r}")

    row = matches[0]
    failures = []
    if row.get("source") != "project":
        failures.append(f"source={row.get('source')!r}")
    if row.get("enabled") is not True:
        failures.append(f"enabled={row.get('enabled')!r}")
    if row.get("tools") != 3:
        failures.append(f"tools={row.get('tools')!r}")
    if row.get("error") not in (None, ""):
        failures.append(f"error={row.get('error')!r}")

    registered = set(registry.get_tool_names_for_toolset("learnflow"))
    if registered != EXPECTED_TOOLS:
        failures.append(f"registered_tools={sorted(registered)!r}")

    if failures:
        raise SystemExit("H02_PLUGIN_DISCOVERY=FAIL " + " ".join(failures))

    print("H02_PLUGIN_DISCOVERY=PASS")
    print("plugin=learnflow source=project enabled=true tools=3")

    created = _require_success(
        "learnflow_create",
        registry.dispatch(
            "learnflow_create",
            {"scene_graph": _smoke_scene(), "scene_duration": 0.2},
        ),
    )
    run_id = created["run_id"]
    compiled = _require_success(
        "learnflow_run",
        registry.dispatch("learnflow_run", {"run_id": run_id}),
    )
    rendered = _require_success(
        "learnflow_render",
        registry.dispatch("learnflow_render", {"run_id": run_id}),
    )

    output = SMOKE_RUNTIME / run_id / "render" / "scene.mp4"
    if not output.is_file() or output.stat().st_size <= 0:
        raise SystemExit("H02_PINNED_RUNTIME=FAIL real MP4 missing or empty")
    if compiled.get("stage") != "COMPILED" or rendered.get("stage") != "RENDERED":
        raise SystemExit(
            f"H02_PINNED_RUNTIME=FAIL stages compile={compiled.get('stage')} render={rendered.get('stage')}"
        )

    print("H02_PINNED_RUNTIME=PASS")
    print(f"run_id={run_id} frame_count={rendered['frame_count']} fps={rendered['fps']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
