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
from app.rendering.function_graph import FunctionGraphRenderer
from app.rendering.array_trace import ArrayTraceRenderer
from app.rendering.process_diagram import ProcessDiagramRenderer
from app.rendering.router import RendererRouter
from app.repositories.base import JobRepository
from app.storage.base import ArtifactStore

logger = logging.getLogger(__name__)


class UnconfiguredPlanner(LessonPlanner):
    """Fail the job clearly when the configured planner lacks an API key."""

    def __init__(self, provider: str = "gemini"):
        self.provider = provider

    async def create_plan(self, request: LearningRequest) -> LessonPlan:
        env_var = "OPENROUTER_API_KEY" if self.provider == "openrouter" else "GEMINI_API_KEY"
        raise PlannerProviderError(
            code="planner_not_configured",
            message=f"{self.provider} planner API key is not configured. Set {env_var}.",
            retryable=False,
        )

    async def repair_plan(
        self,
        request: LearningRequest,
        invalid_plan: LessonPlan,
        errors: list[Any],
    ) -> LessonPlan:
        return await self.create_plan(request)


def _attach_v3_preview(
    *, settings: Settings, pipeline: LearningVideoPipeline, artifact_store: ArtifactStore,
) -> LearningVideoPipeline:
    if settings.v3_event_alignment_enabled and not (
        settings.v3_narrated_lesson_enabled and settings.v3_binary_preview_enabled
    ):
        raise RuntimeError("V3-20 requires BOTH binary and narrated developer previews")
    if settings.v3_narrated_lesson_enabled and not settings.v3_binary_preview_enabled:
        raise RuntimeError("V3-19 requires explicit V3 binary preview enabled")
    if not (settings.v3_binary_preview_enabled or settings.v3_gpt_array_preview_enabled):
        return pipeline  # no imports or changes whatsoever for both OFF flags
    if settings.environment.strip().lower() not in ("development", "test"):
        raise RuntimeError("V3 preview forbidden outside development/test")
    from app.pipeline.v3_preview import V3OfflinePreviewPipeline
    return V3OfflinePreviewPipeline(
        legacy=pipeline, artifacts=artifact_store,
        gpt_array_enabled=settings.v3_gpt_array_preview_enabled,
        openrouter_api_key=settings.openrouter_api_key,
    )


def create_pipeline(
    settings: Settings,
    repository: JobRepository,
    artifact_store: ArtifactStore,
) -> LearningVideoPipeline:
    """Construct a LearningVideoPipeline (real, demo, or fake) matching the settings."""
    mode = settings.pipeline_mode.lower().strip()
    logger.info("Initializing pipeline in mode: %s", mode)
    if ((settings.v3_binary_preview_enabled or settings.v3_narrated_lesson_enabled or
         settings.v3_event_alignment_enabled or settings.v3_gpt_array_preview_enabled) and
        settings.environment.strip().lower() not in ("development", "test")):
        raise RuntimeError("V3 developer preview must not run in production")

    if mode == "fake":
        if settings.environment == "production":
            raise ValueError(
                "FakePipeline cannot be used when environment=production. Set LEARNFLOW_PIPELINE_MODE=real or demo."
            )
        return _attach_v3_preview(settings=settings, pipeline=FakePipeline(),
                                  artifact_store=artifact_store)

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
    elif mode == "real" and settings.planner_provider == "openrouter":
        if not settings.openrouter_api_key or len(settings.openrouter_api_key) < 16:
            # Keep development/test bootable without paid secrets.
            # Production rejects this configuration during startup validation.
            logger.warning("OPENROUTER_API_KEY is not configured; using UnconfiguredPlanner.")
            planner = UnconfiguredPlanner("openrouter")
        else:
            from app.providers.llm.openrouter_paid import OpenRouterPaidLessonPlanner
            planner = OpenRouterPaidLessonPlanner(
                api_key=settings.openrouter_api_key,
                model=settings.openrouter_planner_model,
                tokens=settings.paid_planner_max_tokens,
            )
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

    planning_service = PlanningService(\n        planner=planner,\n        enforce_visual_teaching=(mode == 'real' and settings.environment.strip().lower() in ('production','prod')),\n    )

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

    graph_renderer = FunctionGraphRenderer(width=width, height=height, fps=fps)
    array_renderer = ArrayTraceRenderer(width=width, height=height, fps=fps)

    renderer_router = RendererRouter(
        concept_renderer=concept_renderer,
        graph_renderer=graph_renderer,
        array_renderer=array_renderer,
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
    built = RealVideoPipeline(
        planning_service=planning_service,
        timeline_builder=timeline_builder,
        renderer_router=renderer_router,
        video_assembler=video_assembler,
        quality_gate=quality_gate,
        artifact_store=artifact_store,
        repository=repository,
    )
    return _attach_v3_preview(settings=settings,pipeline=built,
                              artifact_store=artifact_store)
