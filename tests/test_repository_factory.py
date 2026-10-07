"""Repository backend-selection tests that do not require a live database."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.repositories import factory
from app.repositories.sqlite import SqliteJobRepository


def test_development_without_database_url_keeps_sqlite_fallback(tmp_path):
    settings = Settings(
        environment="development",
        database_url="",
        db_path=str(tmp_path / "dev.db"),
    )
    selected = factory.create_job_repository(settings)
    assert isinstance(selected, SqliteJobRepository)


def test_production_without_database_url_fails_closed(tmp_path):
    settings = Settings(
        environment="production",
        database_url="",
        db_path=str(tmp_path / "must-not-exist.db"),
    )
    with pytest.raises(RuntimeError, match="DATABASE_URL is required in production"):
        factory.create_job_repository(settings)
    assert not (tmp_path / "must-not-exist.db").exists()


def test_database_url_takes_priority_over_sqlite(monkeypatch, tmp_path):
    captured = {}

    class DummyPostgresRepository:
        def __init__(self, database_url: str):
            captured["database_url"] = database_url

    monkeypatch.setattr(factory, "PostgresJobRepository", DummyPostgresRepository)
    settings = Settings(
        environment="development",
        database_url="postgresql://user:pass@db.example/learnflow",
        db_path=str(tmp_path / "unused.db"),
    )
    selected = factory.create_job_repository(settings)
    assert isinstance(selected, DummyPostgresRepository)
    assert captured["database_url"] == settings.database_url
    assert not (tmp_path / "unused.db").exists()


def test_settings_repr_redacts_database_credentials():
    settings = Settings(
        database_url="postgresql://secret-user:secret-pass@db.example/learnflow"
    )
    rendered = repr(settings)
    assert "secret-user" not in rendered
    assert "secret-pass" not in rendered
    assert "***REDACTED***" in rendered
