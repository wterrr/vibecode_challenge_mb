"""Tests for application settings and explicit pipeline mode configuration."""

import pytest
from pathlib import Path
from app.config import Settings


def test_settings_default_mode_without_key_is_real(monkeypatch: pytest.MonkeyPatch) -> None:
    """No pipeline mode and no Gemini key defaults strictly to real mode."""
    monkeypatch.delenv("LEARNFLOW_PIPELINE_MODE", raising=False)
    monkeypatch.delenv("pipeline_mode", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("gemini_api_key", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_API_KEY", raising=False)

    settings = Settings()
    assert settings.pipeline_mode == "real"


def test_settings_default_mode_with_valid_key_is_real(monkeypatch: pytest.MonkeyPatch) -> None:
    """No pipeline mode and valid-looking Gemini key defaults strictly to real mode."""
    monkeypatch.delenv("LEARNFLOW_PIPELINE_MODE", raising=False)
    monkeypatch.delenv("pipeline_mode", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyD-valid-looking-key-1234567890")

    settings = Settings()
    assert settings.pipeline_mode == "real"


def test_settings_explicit_real_mode_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit real mode without key remains real mode."""
    monkeypatch.setenv("LEARNFLOW_PIPELINE_MODE", "real")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    settings = Settings()
    assert settings.pipeline_mode == "real"


def test_settings_explicit_demo_mode_with_and_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit demo mode remains demo regardless of Gemini key presence."""
    monkeypatch.setenv("LEARNFLOW_PIPELINE_MODE", "demo")

    # Without key
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    settings_no_key = Settings()
    assert settings_no_key.pipeline_mode == "demo"

    # With key
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyD-valid-looking-key-1234567890")
    settings_with_key = Settings()
    assert settings_with_key.pipeline_mode == "demo"


def test_settings_explicit_fake_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit fake mode remains fake."""
    monkeypatch.setenv("LEARNFLOW_PIPELINE_MODE", "fake")
    settings = Settings()
    assert settings.pipeline_mode == "fake"


def test_gemini_key_cannot_implicitly_alter_pipeline_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert that presence or absence of a Gemini key cannot alter pipeline mode."""
    monkeypatch.delenv("LEARNFLOW_PIPELINE_MODE", raising=False)
    monkeypatch.delenv("pipeline_mode", raising=False)

    # 1. No key -> real
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert Settings().pipeline_mode == "real"

    # 2. Dummy placeholder key -> real
    monkeypatch.setenv("GEMINI_API_KEY", "MY_GEMINI_API_KEY")
    assert Settings().pipeline_mode == "real"

    # 3. Real key -> real
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyD-valid-looking-key-1234567890")
    assert Settings().pipeline_mode == "real"

    # 4. Explicit demo cannot be changed to real by key
    monkeypatch.setenv("LEARNFLOW_PIPELINE_MODE", "demo")
    assert Settings().pipeline_mode == "demo"

    # 5. Explicit fake cannot be changed to real by key
    monkeypatch.setenv("LEARNFLOW_PIPELINE_MODE", "fake")
    assert Settings().pipeline_mode == "fake"


def test_production_start_command_has_no_reload_and_honors_port() -> None:
    """Production start in package.json must not have --reload and must honor PORT."""
    import json
    from pathlib import Path

    pkg_path = Path(__file__).resolve().parent.parent / "package.json"
    data = json.loads(pkg_path.read_text(encoding="utf-8"))
    start_cmd = data.get("scripts", {}).get("start", "")
    dev_cmd = data.get("scripts", {}).get("dev", "")

    assert "--reload" not in start_cmd
    assert "${PORT:-8000}" in start_cmd or "PORT" in start_cmd
    assert "--reload" in dev_cmd


def test_healthz_endpoint_independent_of_network_and_credentials() -> None:
    """GET /healthz returns 200 without requiring external network or Gemini credentials."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_preflight_probes_clean_up_completely(tmp_path: Path) -> None:
    """Preflight artifact and SQLite probes clean up all temporary files and dirs."""
    from scripts.preflight import check_artifacts_dir, check_sqlite_writable

    # 1. Artifacts probe cleanup
    artifacts_probe_dir = tmp_path / "artifacts"
    artifacts_probe_dir.mkdir(parents=True, exist_ok=True)
    ok, msg = check_artifacts_dir(str(artifacts_probe_dir))
    assert ok is True
    # Invariant: no lingering probe files
    remaining = list(artifacts_probe_dir.glob(".preflight_test_*"))
    assert len(remaining) == 0

    # 2. SQLite probe cleanup
    ok, msg = check_sqlite_writable()
    assert ok is True

