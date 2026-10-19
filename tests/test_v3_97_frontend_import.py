"""V3-97 integration checks: existing website is default, uploaded archive is opt-in."""
import importlib.util
from pathlib import Path
import tempfile
import zipfile
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("v397_import", HERE / "scripts" / "import_v3_97_frontend_zip.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_rejects_unverified_archive():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        archive = root / "other.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("learnflow-landing/src/App.jsx", "tampered")
        try:
            module.import_archive(archive, root / "fe")
        except ValueError as exc:
            assert "SHA mismatch" in str(exc)
        else:
            raise AssertionError("Must reject unknown frontend ZIP")
        assert not (root / "fe").exists()


def test_source_archive_import_when_supplied():
    """Optional: set V397_FE_ZIP to the actual uploaded asset; never fake a video."""
    import os
    filename = os.getenv("V397_FE_ZIP")
    if not filename:
        return
    with tempfile.TemporaryDirectory() as temp:
        target = Path(temp) / "fe"
        module.import_archive(Path(filename), target)
        assert (target / "src" / "App.jsx").exists()
        assert (target / "public" / "media" / "learnflow-product-film.mp4").stat().st_size > 0
        assert (target / "public" / "mascots" / "learner.png").stat().st_size > 0


def test_dist_requires_actual_vite_build():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        try:
            module.install_dist(root / "fe", root / "static")
        except ValueError as exc:
            assert "npm run build" in str(exc)
        else:
            raise AssertionError("Missing React build cannot be served")


def test_react_landing_router_returns_503_without_build():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.web.react_landing as landing
    app = FastAPI()
    app.include_router(landing.router)
    with patch.object(landing, "_INDEX", Path("/v397-absent-frontend/index.html")):
        response = TestClient(app).get("/")
        assert response.status_code == 503
        assert "bundle missing" in response.json()["detail"]
