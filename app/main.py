"""Main entry point for LearnFlow AI FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit
import os
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import router as api_router
from app.api.v3_offline import router as v3_offline_router
from app.api.v3_ai import router as v3_ai_router
from app.config import Settings, get_settings
from app.pipeline.base import LearningVideoPipeline
from app.pipeline.factory import create_pipeline
from app.repositories.base import JobRepository
from app.repositories.factory import create_job_repository
from app.runner.job_runner import JobRunner
from app.services.job_service import JobService
from app.storage.base import ArtifactStore
from app.storage.local import LocalArtifactStore
from app.web.routes import router as web_router
from app.auth.single_admin import AdminGuard, PostgresSingleAdmin, router as auth_router

def validate_production_settings(settings: Settings) -> None:
    """Production fails at startup, not by silently falling back."""
    from app.config import is_real_gemini_key
    from app.repositories.postgres import normalize_database_url
    if settings.environment.strip().lower() not in ("production", "prod"):
        return
    if settings.pipeline_mode != "real":
        raise RuntimeError("Production requires LEARNFLOW_PIPELINE_MODE=real")
    normalize_database_url(settings.database_url)
    if not settings.auth_enabled:
        raise RuntimeError("Production requires AUTH_ENABLED=true")
    if not settings.admin_username or len(settings.admin_password) < 16:
        raise RuntimeError("Production requires ADMIN_USERNAME and ADMIN_PASSWORD secret (16+ characters)")
    if len(settings.auth_secret_key) < 32:
        raise RuntimeError("Production requires stable AUTH_SECRET_KEY secret (32+ characters)")
    u = urlsplit(settings.public_origin)
    if u.scheme != "https" or not u.hostname or u.username or u.password or u.path not in ("","/") or u.query or u.fragment:
        raise RuntimeError("PUBLIC_ORIGIN must be an external HTTPS origin without a path")
    if settings.planner_provider == "openrouter":
        if len(settings.openrouter_api_key) < 16 or not settings.openrouter_planner_model.startswith("openai/") or settings.openrouter_planner_model.endswith(":free"):
            raise RuntimeError("Production requires a paid OpenRouter model and OPENROUTER_API_KEY")
    elif settings.planner_provider == "gemini":
        if not is_real_gemini_key(settings.gemini_api_key):
            raise RuntimeError("Production requires GEMINI_API_KEY")
    else:
        raise RuntimeError("Unsupported production planner provider")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    # Start the async background job runner
    await app.state.runner.start()
    yield
    # Stop background runner cleanly
    await app.state.runner.stop()


def create_app(
    *,
    settings: Settings | None = None,
    repository: JobRepository | None = None,
    artifact_store: ArtifactStore | None = None,
    pipeline: LearningVideoPipeline | None = None,
) -> FastAPI:
    """Create and configure FastAPI application with explicit dependencies."""
    app_settings = settings or get_settings()
    validate_production_settings(app_settings)
    production = app_settings.environment.strip().lower() in ("production", "prod")
    if app_settings.auth_enabled:
        if len(app_settings.auth_secret_key) < 32 or len(app_settings.admin_password) < 16:
            raise RuntimeError("Auth requires AUTH_SECRET_KEY (32+) and ADMIN_PASSWORD (16+) secrets")
        if not app_settings.public_origin:
            raise RuntimeError("Auth requires PUBLIC_ORIGIN")
        app_auth_store = PostgresSingleAdmin(
            app_settings.database_url, app_settings.admin_username, app_settings.admin_password
        )
    else:
        app_auth_store = None
    app_repository = repository or create_job_repository(app_settings)
    app_artifact_store = artifact_store or LocalArtifactStore(app_settings.artifacts_dir)
    app_pipeline = pipeline or create_pipeline(
        app_settings,
        app_repository,
        app_artifact_store,
    )
    app_runner = JobRunner(
        repository=app_repository,
        pipeline=app_pipeline,
        artifact_store=app_artifact_store,
    )
    app_job_service = JobService(
        repository=app_repository,
        artifact_store=app_artifact_store,
        runner=app_runner,
    )

    app = FastAPI(
        title="LearnFlow AI",
        description="AI Learning Video Studio",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Attach container dependencies to app.state
    app.state.settings = app_settings
    app.state.repository = app_repository
    app.state.artifact_store = app_artifact_store
    app.state.pipeline = app_pipeline
    app.state.runner = app_runner
    app.state.job_service = app_job_service
    app.state.auth_store = app_auth_store
    app.state.auth_key = app_settings.auth_secret_key
    app.state.auth_secure = production

    # Mount static files
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Health check
    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    # Include route modules
    app.include_router(auth_router)
    app.include_router(api_router)
    app.include_router(v3_offline_router)  # always 404 if default-OFF, no preview publication
    app.include_router(v3_ai_router)  # dev-local only, OFF by default; no regular job publication
    # V3-97: React UI only by explicit opt-in in a local dev/test environment.
    # Existing /api/jobs, V2, V3 previews and Jinja homepage remain the default.
    import os
    if production or os.getenv("LEARNFLOW_REACT_LANDING", "0") == "1":
        from app.web.react_landing import router as react_landing_router
        app.include_router(react_landing_router)
    app.include_router(web_router)

    if production:
        app.add_middleware(TrustedHostMiddleware,
            allowed_hosts=[urlsplit(app_settings.public_origin).hostname], www_redirect=False)
    if app_auth_store is not None:
        app.add_middleware(AdminGuard, key=app_settings.auth_secret_key,
            origin=app_settings.public_origin, store=app_auth_store,
            secure=production, daily_limit=app_settings.daily_paid_job_limit)
    return app


app = create_app()
