"""Pipeline factory constructing dependencies and assembling pipelines based on configuration."""

import logging
from typing import Any, Literal

from app.config import Settings, is_real_gemini_key
from app.demo.planner import DemoPlanner
from app.domain.lesson import LearningRequest, LessonPlan
from app.pipeline.assembly import VideoAssembler
from app.pipeline.base import LearningVideoPipeline
from app.pipeline.fake import FakePipeline
from app.pipeline.quality_gate import QualityGate
from app.pipeline.real import RealVideoPipeline
from app.pipeline.timeline import TimelineBuilder
from app.planning.service import PlanningService
from app.providers.image.base import ImageProvider
from app.providers.image.gemini import GeminiImageProvider
from app.providers.llm.base import LessonPlanner, PlannerProviderError
from app.providers.llm.gemini import GeminiLessonPlanner
from app.providers.speech.edge import EdgeSpeechProvider
from app.rendering.comparison import ComparisonRenderer
from app.rendering.concept_card import ConceptCardRenderer
from app.rendering.illustration import IllustrationRenderer
from app.rendering.process_diagram import ProcessDiagramRenderer
from app.rendering.router import RendererRouter
from app.repositories.base import JobRepository
from app.storage.base import ArtifactStore

logger = logging.getLogger(__name__)


class UnconfiguredPlanner(LessonPlanner):
    """Planner stub that raises a clear error if Gemini API key is missing."""

    async def create_plan(self, request: LearningRequest) -> LessonPlan:
        raise PlannerProviderError(
            code="planner_not_configured",
            message="Gemini API key is not configured. Set GEMINI_API_KEY or use LEARNFLOW_PIPELINE_MODE=demo.",
            retryable=False,
        )

    async def repair_plan(
        self,
        request: LearningRequest,
        invalid_plan: LessonPlan,
        errors: list[Any],
    ) -> LessonPlan:
        return await self.create_plan(request)


def create_pipeline(
    settings: Settings,
    repository: JobRepository,
    artifact_store: ArtifactStore,
) -> LearningVideoPipeline:
    """Construct a LearningVideoPipeline (real, demo, or fake) matching the settings."""
    mode = settings.pipeline_mode.lower().strip()
    logger.info("Initializing pipeline in mode: %s", mode)

    if mode == "fake":
        if settings.environment == "production":
            raise ValueError(
                "FakePipeline cannot be used when environment=production. Set LEARNFLOW_PIPELINE_MODE=real or demo."
            )
        return FakePipeline()

    # Determine render profile dimensions and limits
    if settings.render_profile == "test":
        width = 640
        height = 360
        fps = 12
        min_size_bytes = 20_000
    else:
        width = 1280
        height = 720
        fps = 24
        min_size_bytes = 50_000

    # 1. Lesson Planner
    if mode == "demo":
        planner: LessonPlanner = DemoPlanner(strict=True)
    elif mode == "real":
        if not is_real_gemini_key(settings.gemini_api_key):
            logger.warning("GEMINI_API_KEY is not configured with a valid key; using UnconfiguredPlanner.")
            planner = UnconfiguredPlanner()
        else:
            planner = GeminiLessonPlanner(
                api_key=settings.gemini_api_key,
                model=settings.gemini_planner_model,
            )
    else:
        raise ValueError(f"Unsupported pipeline mode '{mode}'. Choose 'real', 'demo', or 'fake'.")

    planning_service = PlanningService(planner=planner)

    # 2. Speech Provider & Timeline Builder
    speech_provider = EdgeSpeechProvider(
        voice_vi=settings.tts_voice_vi,
        voice_en=settings.tts_voice_en,
    )
    timeline_builder = TimelineBuilder(
        speech_provider=speech_provider,
        artifact_store=artifact_store,
    )

    # 3. Optional Image Provider
    image_provider: ImageProvider | None = None
    if settings.enable_image_generation and settings.image_provider == "gemini" and settings.gemini_api_key:
        image_provider = GeminiImageProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_image_model,
        )

    # 4. Renderers & Router
    concept_renderer = ConceptCardRenderer(width=width, height=height, fps=fps)
    process_renderer = ProcessDiagramRenderer(width=width, height=height, fps=fps)
    comparison_renderer = ComparisonRenderer(width=width, height=height, fps=fps)
    illustration_renderer = IllustrationRenderer(
        width=width,
        height=height,
        fps=fps,
        image_provider=image_provider,
        enable_image_generation=settings.enable_image_generation,
    )

    renderer_router = RendererRouter(
        concept_renderer=concept_renderer,
        process_renderer=process_renderer,
        comparison_renderer=comparison_renderer,
        illustration_renderer=illustration_renderer,
        image_provider=image_provider,
        enable_image_generation=settings.enable_image_generation,
    )

    # 5. Video Assembler & Quality Gate
    video_assembler = VideoAssembler(fps=fps)
    quality_gate = QualityGate(
        expected_width=width,
        expected_height=height,
        min_size_bytes=min_size_bytes,
    )

    # 6. RealVideoPipeline
    return RealVideoPipeline(
        planning_service=planning_service,
        timeline_builder=timeline_builder,
        renderer_router=renderer_router,
        video_assembler=video_assembler,
        quality_gate=quality_gate,
        artifact_store=artifact_store,
        repository=repository,
    )
