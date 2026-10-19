"""V3-97 actual built React and FastAPI contract, without real model calls."""
from pathlib import Path
from hashlib import sha256
import re

from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app

ROOT = Path(__file__).resolve().parents[1]
FRONT = ROOT / "frontend" / "learnflow-landing"
BUILD = ROOT / "app" / "static" / "landing"


def test_media_source_and_compiled_assets_are_bit_identical():
    assert (FRONT / "src" / "App.jsx").is_file()
    assert (FRONT / "src" / "api" / "learnflow.js").is_file()
    for row in (FRONT / "asset-manifest.sha256").read_text().splitlines():
        expected, path = row.split(maxsplit=1)
        assert sha256((FRONT / path).read_bytes()).hexdigest() == expected
        assert sha256((BUILD / path.removeprefix("public/")).read_bytes()).hexdigest() == expected


def test_real_fastapi_serves_react_and_existing_api(monkeypatch, tmp_path):
    monkeypatch.setenv("LEARNFLOW_REACT_LANDING", "1")
    settings = Settings(environment="test", pipeline_mode="fake",
                        db_path=str(tmp_path / "jobs.db"),
                        artifacts_dir=str(tmp_path / "artifacts"),
                        v3_gpt_array_preview_enabled=False)
    with TestClient(create_app(settings=settings)) as client:
        home = client.get("/")
        assert home.status_code == 200, home.text[:300]
        assert '<div id="root"' in home.text
        js = re.findall(r'src="(/static/landing/assets/[^"]+\.js)"', home.text)
        assert js and client.get(js[0]).status_code == 200
        for filename in ("mascots/creator.png", "mascots/learner.png",
                         "media/learnflow-product-film.mp4", "media/learnflow-opening-v2-no-loop.mp4"):
            assert client.get("/static/landing/" + filename).status_code == 200
        assert client.get("/healthz").json() == {"status": "ok"}
        assert client.get("/create").status_code == 200
        assert client.get("/library").status_code == 200
        assert client.get("/api/jobs?limit=1").status_code == 200
        assert client.post("/api/v3/ai/array-preview", json={
            "query": "How does a 3 by 4 array become a 4 by 3 array without changing the total?",
            "paid_consent": True, "language": "en"
        }).status_code == 404
        job = client.post("/api/jobs", json={
            "topic": "How does the TCP three-way handshake work?",
            "audience": "Beginner", "language": "en", "target_duration_seconds": 60
        })
        assert job.status_code == 202, job.text
        status = client.get("/api/jobs/" + job.json()["job_id"])
        assert status.status_code == 200
        assert status.json()["topic"] == "How does the TCP three-way handshake work?"


def test_flag_off_preserves_original_landing(monkeypatch, tmp_path):
    monkeypatch.delenv("LEARNFLOW_REACT_LANDING", raising=False)
    settings = Settings(environment="test", pipeline_mode="fake",
                        db_path=str(tmp_path / "legacy.db"),
                        artifacts_dir=str(tmp_path / "artifacts"))
    with TestClient(create_app(settings=settings)) as client:
        home = client.get("/")
        assert home.status_code == 200
        assert "/static/landing/assets/" not in home.text
