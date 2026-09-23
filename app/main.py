"""Main entry point for LearnFlow AI FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.config import Settings, get_settings
from app.pipeline.base import LearningVideoPipeline
from app.pipeline.factory import create_pipeline
from app.repositories.base import JobRepository
from app.repositories.sqlite import SqliteJobRepository
from app.runner.job_runner import JobRunner
from app.services.job_service import JobService
from app.storage.base import ArtifactStore
from app.storage.local import LocalArtifactStore
from app.web.routes import router as web_router


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
    app_repository = repository or SqliteJobRepository(app_settings.db_path)
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

    # Mount static files
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Health check
    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    # Include route modules
    app.include_router(api_router)
    app.include_router(web_router)

    return app


app = create_app()
