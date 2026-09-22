"""Fake pipeline implementation for CP2 async testing without AI/media dependencies."""

import asyncio
from app.domain.enums import JobStage
from app.domain.errors import PipelineExecutionError
from app.domain.jobs import Job
from app.pipeline.base import LearningVideoPipeline, StageCallback

FAKE_STAGES: list[tuple[JobStage, int]] = [
    (JobStage.PLANNING, 10),
    (JobStage.VALIDATING_PLAN, 25),
    (JobStage.AUDIO, 40),
    (JobStage.RENDERING, 60),
    (JobStage.ASSEMBLING, 80),
    (JobStage.VALIDATING_OUTPUT, 90),
]


class FakePipeline(LearningVideoPipeline):
    """Simulates pipeline stage transitions with configurable delay and failure injection."""

    def __init__(
        self,
        step_delay_seconds: float = 0.05,
        fail_at_stage: JobStage | None = None,
        failure_error: PipelineExecutionError | None = None,
    ):
        self.step_delay_seconds = step_delay_seconds
        self.fail_at_stage = fail_at_stage
        self.failure_error = failure_error

    async def process(
        self,
        job: Job,
        on_stage: StageCallback,
    ) -> None:
        for stage, progress in FAKE_STAGES:
            if self.fail_at_stage == stage:
                error = self.failure_error or PipelineExecutionError(
                    code="fake_pipeline_failure",
                    message=f"Injected fake pipeline failure at stage {stage.value}",
                    stage=stage,
                    retryable=False,
                )
                raise error

            await on_stage(stage, progress)
            if self.step_delay_seconds > 0:
                await asyncio.sleep(self.step_delay_seconds)
