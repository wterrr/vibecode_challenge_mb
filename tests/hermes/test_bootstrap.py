from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "hermes" / "bootstrap" / "status.json"
CONFIG = ROOT / "hermes" / "bootstrap" / "config.yaml"
OFFLINE = ROOT / "hermes" / "bootstrap" / "fixtures" / "successful_tool_roundtrip.jsonl"


def test_bootstrap_pins_runtime_and_records_live_pass():
    data = json.loads(STATUS.read_text(encoding="utf-8"))
    assert data["stage"] == "hermes-bootstrap"
    assert data["state"] == "PASS"
    assert data["hermes"]["release_tag"] == "v2026.9.24"
    assert data["hermes"]["package_version"] == "0.21.5"
    assert data["hermes"]["commit"] == "f97608f178d1ffeca59860195ab7da295f7c8e5f"
    assert data["provider"]["id"] == "openrouter"
    assert data["provider"]["primary_model"] == "openai/gpt-6-luna"
    assert data["provider"]["free_fallback_model"] == "nvidia/nemotron-3.5-lightning:free"
    assert data["live_verification"]["status"] == "PASS"
    assert data["live_verification"]["fallback_used"] is True


def test_bootstrap_config_contains_no_secret_and_uses_openrouter():
    text = CONFIG.read_text(encoding="utf-8")
    assert 'default: "openai/gpt-6-luna"' in text
    assert 'provider: "openrouter"' in text
    assert "sk-or-" not in text
    assert "OPENROUTER_API_KEY=" not in text


def test_runtime_and_secrets_are_ignored():
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".hermes_runtime/" in ignore
    assert ".env" in ignore
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "OPENROUTER_API_KEY=" in env_example
    assert "sk-or-v1-" not in env_example


def test_install_wrappers_pin_exact_commit():
    expected = "f97608f178d1ffeca59860195ab7da295f7c8e5f"
    sh = (ROOT / "scripts" / "install_hermes_bootstrap.sh").read_text(encoding="utf-8")
    ps1 = (ROOT / "scripts" / "install_hermes_bootstrap.ps1").read_text(encoding="utf-8")
    assert expected in sh
    assert expected in ps1
    assert "raw.githubusercontent.com/NousResearch/hermes-agent/$PIN/" in sh
    assert "raw.githubusercontent.com/NousResearch/hermes-agent/$Pin/" in ps1


def test_runner_pins_project_local_binary_before_global_install():
    text = (ROOT / "scripts" / "run_hermes_bootstrap_smoke.py").read_text(encoding="utf-8")
    assert 'INSTALL_DIR / "venv" / "bin" / "hermes"' in text
    assert "shutil.which" not in text
    assert "def verify_installed_pin(status: dict[str, Any])" in text
    assert 'expected = status["hermes"]["commit"]' in text


def test_runner_declares_primary_and_free_fallback():
    text = (ROOT / "scripts" / "run_hermes_bootstrap_smoke.py").read_text(encoding="utf-8")
    assert 'PRIMARY_MODEL = "openai/gpt-6-luna"' in text
    assert 'FREE_FALLBACK_MODEL = "nvidia/nemotron-3.5-lightning:free"' in text
    assert '"fallback_used": passed_model == FREE_FALLBACK_MODEL' in text


def test_offline_stream_contract_passes():
    proc = subprocess.run(
        [sys.executable, "scripts/run_hermes_bootstrap_smoke.py", "--offline-fixture", str(OFFLINE)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "HERMES_BOOTSTRAP_OFFLINE=PASS" in proc.stdout
    assert '"tool_name": "read_file"' in proc.stdout


def test_offline_stream_fails_without_tool_roundtrip(tmp_path):
    broken = tmp_path / "broken.jsonl"
    broken.write_text(
        "\n".join([
            json.dumps({"type":"system","subtype":"init","model":"openai/gpt-6-luna","session_id":"broken"}),
            json.dumps({"type":"result","session_id":"broken","exit_code":0,"text":"HERMES_BOOTSTRAP_OK:LEARNFLOW-BOOTSTRAP-FIXTURE-v1"}),
        ]) + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, "scripts/run_hermes_bootstrap_smoke.py", "--offline-fixture", str(broken)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 1
    assert "agent did not call a tool" in proc.stderr
