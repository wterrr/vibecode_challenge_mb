from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PIN = ROOT / "hermes" / "h01" / "pin.json"
CONFIG = ROOT / "hermes" / "h01" / "config.yaml"
OFFLINE = ROOT / "hermes" / "h01" / "fixtures" / "stream_success.jsonl"


def test_h01_pins_stable_hermes_release_and_openrouter_model():
    data = json.loads(PIN.read_text(encoding="utf-8"))
    assert data["checkpoint"] == "H-01"
    assert data["state"] == "IMPLEMENTED_AWAITING_LIVE_SMOKE"
    assert data["hermes"]["release_tag"] == "v2026.9.24"
    assert data["hermes"]["package_version"] == "0.21.5"
    assert data["hermes"]["commit"] == "f97608f178d1ffeca59860195ab7da295f7c8e5f"
    assert data["provider"] == {
        "id": "openrouter",
        "api_key_env": "OPENROUTER_API_KEY",
        "model": "openai/gpt-6-luna",
    }


def test_h01_config_contains_no_secret_and_uses_openrouter():
    text = CONFIG.read_text(encoding="utf-8")
    assert 'default: "openai/gpt-6-luna"' in text
    assert 'provider: "openrouter"' in text
    assert "sk-or-" not in text
    assert "OPENROUTER_API_KEY=" not in text


def test_h01_project_rules_preserve_core_freeze_boundary():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "benchmarks/core_freeze/manifest.json" in text
    assert "CORE UNFREEZE" in text
    assert "A checkpoint is not considered H-01 PASS until" in text


def test_h01_runtime_and_secrets_are_ignored():
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".hermes_runtime/" in ignore
    assert ".env" in ignore
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "OPENROUTER_API_KEY=" in env_example
    assert "sk-or-v1-" not in env_example


def test_h01_install_wrappers_pin_exact_commit():
    expected = "f97608f178d1ffeca59860195ab7da295f7c8e5f"
    sh = (ROOT / "scripts" / "install_hermes_h01.sh").read_text(encoding="utf-8")
    ps1 = (ROOT / "scripts" / "install_hermes_h01.ps1").read_text(encoding="utf-8")
    assert expected in sh
    assert expected in ps1
    assert "raw.githubusercontent.com/NousResearch/hermes-agent/$PIN/" in sh
    assert "raw.githubusercontent.com/NousResearch/hermes-agent/$Pin/" in ps1


def test_h01_offline_stream_contract_passes():
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_hermes_h01_smoke.py",
            "--offline-fixture",
            str(OFFLINE),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "H01_OFFLINE=PASS" in proc.stdout
    assert '"tool_name": "read_file"' in proc.stdout


def test_h01_offline_stream_fails_without_tool_roundtrip(tmp_path):
    broken = tmp_path / "broken.jsonl"
    broken.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "system",
                        "subtype": "init",
                        "model": "openai/gpt-6-luna",
                        "session_id": "broken",
                    }
                ),
                json.dumps(
                    {
                        "type": "result",
                        "session_id": "broken",
                        "exit_code": 0,
                        "text": "HERMES_H01_OK:LEARNFLOW-H01-FIXTURE-v1",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_hermes_h01_smoke.py",
            "--offline-fixture",
            str(broken),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "agent did not call a tool" in proc.stderr
