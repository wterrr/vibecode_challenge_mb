"""Production Learning Video Pipeline executing end-to-end AI planning, audio, rendering, and assembly."""

import json
import logging
import math
import os
from pathlib import Path

from app.domain.enums import JobStage
from app.domain.errors import PipelineExecutionError
from app.domain.jobs import Job
from app.domain.lesson import LearningRequest
from app.pipeline.assembly import VideoAssembler
from app.pipeline.base import LearningVideoPipeline, StageCallback
from app.pipeline.quality_gate import QualityGate
from app.pipeline.timeline import TimelineBuilder
from app.planning.service import PlanningService
from app.planning.validator import validate_lesson_plan
from app.providers.llm.base import PlannerProviderError
from app.rendering.router import RendererRouter
from app.repositories.base import JobRepository
from app.storage.base import ArtifactStore

logger = logging.getLogger(__name__)


class RealVideoPipeline(LearningVideoPipeline):
    """Orchestrates structured planning, audio synthesis, visual rendering, assembly, and quality gate."""

    requires_published_artifact: bool = True

    def __init__(
        self,
        planning_service: PlanningService,
        timeline_builder: TimelineBuilder,
        renderer_router: RendererRouter,
        video_assembler: VideoAssembler,
        quality_gate: QualityGate,
        artifact_store: ArtifactStore,
        repository: JobRepository,
    ):
        self.planning_service = planning_service
        self.timeline_builder = timeline_builder
        self.renderer_router = renderer_router
        self.video_assembler = video_assembler
        self.quality_gate = quality_gate
        self.artifact_store = artifact_store
        self.repository = repository

    async def process(
        self,
        job: Job,
        on_stage: StageCallback,
    ) -> None:
        """Process a learning video job through all 6 stages strictly in order."""
        request = LearningRequest(
            topic=job.topic,
            audience=job.audience,
            language=job.language,
            target_duration_seconds=job.target_duration_seconds,
        )

        # =====================================================================
        # Stage 1: PLANNING (10%)
        # =====================================================================
        await on_stage(JobStage.PLANNING, 10)
        logger.info("Stage 1/6: PLANNING for job=%s", job.id)

        try:
            plan = await self.planning_service.build_valid_plan(request)
        except PlannerProviderError as err:
            logger.error(
                "Planner provider failed job=%s code=%s message=%s",
                job.id,
                err.code,
                err.message,
            )
            raise PipelineExecutionError(
                code=err.code,
                message=err.message,
                stage=JobStage.PLANNING,
                retryable=err.retryable,
            ) from None
        except PipelineExecutionError:
            raise
        except Exception as exc:
            logger.error(
                "Unexpected planning exception job=%s type=%s",
                job.id,
                type(exc).__name__,
            )
            raise PipelineExecutionError(
                code="planning_failed",
                message="An unexpected error occurred during lesson planning.",
                stage=JobStage.PLANNING,
                retryable=False,
            ) from exc

        # =====================================================================
        # Stage 2: VALIDATING_PLAN (25%)
        # =====================================================================
        await on_stage(JobStage.VALIDATING_PLAN, 25)
        logger.info("Stage 2/6: VALIDATING_PLAN for job=%s", job.id)

        issues = validate_lesson_plan(request, plan)
        errors = [issue for issue in issues if issue.severity == "error"]
        if errors:
            logger.error("Final plan validation failed with %d errors for job=%s", len(errors), job.id)
            raise PipelineExecutionError(
                code="plan_validation_failed",
                message="The generated lesson plan could not be validated.",
                stage=JobStage.VALIDATING_PLAN,
                retryable=False,
            )

        # Persist plan in DB
        self.repository.set_plan(job.id, plan)

        # Atomically persist plan.json in artifacts
        job_dir = self.artifact_store.get_job_dir(job.id, create=True)
        plan_path = self.artifact_store.get_path(job.id, "plan.json")
        tmp_plan_path = self.artifact_store.get_path(
            job.id, f"plan.tmp_{os.getpid()}_{id(plan)}.json"
        )
        plan_dict = plan.model_dump(mode="json")
        tmp_plan_path.write_text(
            json.dumps(plan_dict, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp_plan_path, plan_path)

        # =====================================================================
        # Stage 3: AUDIO (40%)
        # =====================================================================
        await on_stage(JobStage.AUDIO, 40)
        logger.info("Stage 3/6: AUDIO synthesis and timeline build for job=%s", job.id)
        timeline = await self.timeline_builder.build(job.id, plan)

        # =====================================================================
        # Stage 4: RENDERING (60%)
        # =====================================================================
        await on_stage(JobStage.RENDERING, 60)
        logger.info("Stage 4/6: RENDERING scenes for job=%s (scenes=%d)", job.id, len(plan.scenes))

        # Timeline sanity check
        if len(plan.scenes) != len(timeline.scenes):
            raise PipelineExecutionError(
                code="timeline_scene_mismatch",
                message="Resolved timeline does not match the lesson plan.",
                stage=JobStage.RENDERING,
                retryable=False,
            )

        for s, t in zip(plan.scenes, timeline.scenes):
            if s.scene_id != t.scene_id:
                raise PipelineExecutionError(
                    code="timeline_scene_mismatch",
                    message="Resolved timeline does not match the lesson plan.",
                    stage=JobStage.RENDERING,
                    retryable=False,
                )

        scene_paths: list[Path] = []
        for scene, timing in zip(plan.scenes, timeline.scenes):
            scene_path = self.artifact_store.get_path(job.id, "scenes", f"{scene.scene_id}.mp4")
            scene_path.parent.mkdir(parents=True, exist_ok=True)

            renderer = self.renderer_router.get_renderer(scene.visual_intent)
            try:
                result = await renderer.render(
                    scene=scene,
                    timing=timing,
                    output_path=scene_path,
                )
            except Exception as exc:
                logger.error(
                    "Scene rendering exception scene=%s intent=%s type=%s",
                    scene.scene_id,
                    scene.visual_intent.value,
                    type(exc).__name__,
                )
                raise PipelineExecutionError(
                    code="render_failed",
                    message="A scene could not be rendered.",
                    stage=JobStage.RENDERING,
                    retryable=False,
                ) from exc

            # Verify render result
            if (
                not scene_path.exists()
                or not scene_path.is_file()
                or scene_path.stat().st_size == 0
                or not result.duration_seconds
                or not math.isfinite(result.duration_seconds)
                or result.duration_seconds <= 0
            ):
                logger.error("Scene render invalid result for scene=%s", scene.scene_id)
                raise PipelineExecutionError(
                    code="render_failed",
                    message="A scene could not be rendered.",
                    stage=JobStage.RENDERING,
                    retryable=False,
                )

            scene_paths.append(scene_path)

        # =====================================================================
        # Stage 5: ASSEMBLING (80%)
        # =====================================================================
        await on_stage(JobStage.ASSEMBLING, 80)
        logger.info("Stage 5/6: ASSEMBLING candidate video for job=%s", job.id)

        pending_path = self.artifact_store.get_pending_final_path(job.id)
        await self.video_assembler.assemble(
            job_id=job.id,
            scene_video_paths=scene_paths,
            timeline=timeline,
            output_path=pending_path,
        )

        # =====================================================================
        # Stage 6: VALIDATING_OUTPUT (90%)
        # =====================================================================
        await on_stage(JobStage.VALIDATING_OUTPUT, 90)
        logger.info("Stage 6/6: VALIDATING_OUTPUT Quality Gate for job=%s", job.id)

        report = await self.quality_gate.validate(
            candidate_path=pending_path,
            timeline=timeline,
            plan=plan,
        )

        if not report.passed:
            failed_checks = [c.name for c in report.checks if not c.passed]
            logger.error("Quality gate failed for job=%s checks=%s", job.id, failed_checks)
            raise PipelineExecutionError(
                code="quality_gate_failed",
                message="The generated video did not pass final validation.",
                stage=JobStage.VALIDATING_OUTPUT,
                retryable=False,
            )

        # Quality Gate passed: atomically promote final.pending.mp4 -> final.mp4
        self.artifact_store.publish_final(job.id)
        logger.info("Published final video artifact for job=%s", job.id)

        # Persist relative artifact path and normalized metadata
        self.repository.set_artifact(
            job.id,
            artifact_path="final.mp4",
            metadata=report.metadata,
        )
