#!/usr/bin/env python3
"""Verify H-02 using the real pinned Hermes project-plugin discovery path."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFY_HOME = ROOT / ".hermes_runtime" / "h02" / "verify-home"


def main() -> int:
    os.chdir(ROOT)
    shutil.rmtree(VERIFY_HOME, ignore_errors=True)
    VERIFY_HOME.mkdir(parents=True, exist_ok=True)

    base_config = (ROOT / "hermes" / "h01" / "config.yaml").read_text(encoding="utf-8").rstrip()
    config = base_config + "\n\nplugins:\n  enabled:\n    - learnflow\n"
    (VERIFY_HOME / "config.yaml").write_text(config, encoding="utf-8")

    os.environ["HERMES_HOME"] = str(VERIFY_HOME)
    os.environ["HERMES_ENABLE_PROJECT_PLUGINS"] = "true"

    from hermes_cli.plugins import discover_plugins, get_plugin_manager

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

    if failures:
        raise SystemExit("H02_PLUGIN_DISCOVERY=FAIL " + " ".join(failures))

    print("H02_PLUGIN_DISCOVERY=PASS")
    print("plugin=learnflow source=project enabled=true tools=3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
