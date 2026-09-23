"""End-to-end integration and smoke tests for RealVideoPipeline and JobRunner publication invariant."""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import pytest
from fastapi.testclient import TestClient

from app.demo.lesson_plans import DEMO_TCP_PLAN
from app.demo.planner import DemoPlanner
from app.domain.enums import JobStage, JobStatus
from app.domain.errors import PipelineExecutionError
from app.domain.jobs import Job
from app.domain.lesson import LearningRequest
from app.domain.timeline import ResolvedSceneTiming, ResolvedTimeline
from app.main import create_app
from app.pipeline.assembly import VideoAssembler
from app.pipeline.base import LearningVideoPipeline, StageCallback
from app.pipeline.fake import FakePipeline
from app.pipeline.quality_gate import QualityCheck, QualityGate, QualityReport
from app.pipeline.real import RealVideoPipeline
from app.pipeline.timeline import TimelineBuilder
from app.planning.service import PlanningService
from app.rendering.comparison import ComparisonRenderer
from app.rendering.concept_card import ConceptCardRenderer
from app.rendering.illustration import IllustrationRenderer
from app.rendering.process_diagram import ProcessDiagramRenderer
from app.rendering.router import RendererRouter
from app.repositories.sqlite import SqliteJobRepository
from app.runner.job_runner import JobRunner
from app.services.job_service import JobService
from app.storage.local import LocalArtifactStore
from tests.test_quality_gate import _generate_test_mp4


def _create_test_job(
    repo: SqliteJobRepository,
    job_id: str,
    topic: str,
    audience: str = "Developer",
    language: str = "vi",
    target_duration_seconds: int = 90,
) -> Job:
    now = datetime.now(timezone.utc)
    job = Job(
        id=job_id,
        topic=topic,
        audience=audience,
        language=language,
        target_duration_seconds=target_duration_seconds,
        status=JobStatus.QUEUED,
        progress_percent=0,
        created_at=now,
        updated_at=now,
    )
    return repo.create(job)


class MockSpeechProvider:
    """Fast deterministic speech mock producing a minimal silent MP3."""

    def __init__(self, duration: float = 1.8):
        self.duration = duration

    async def synthesize(self, text: str, output_path: Path, language: str):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Create silent mp3
        import subprocess
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi", "-i",
                f"anullsrc=r=48000:cl=stereo:d={self.duration}",
                "-c:a", "libmp3lame", str(output_path)
            ],
            capture_output=True,
            check=False,
        )
        from app.domain.timeline import SubtitleCue
        from app.providers.speech.base import SpeechResult
        return SpeechResult(
            path=str(output_path),
            provider="mock",
            duration_seconds=self.duration,
            subtitle_cues=[
                SubtitleCue(start_seconds=0.0, end_seconds=self.duration, text=text[:30] if text.strip() else "narration")
            ],
        )


@pytest.fixture
def test_setup(tmp_path: Path):
    db_path = str(tmp_path / "test.db")
    artifacts_dir = str(tmp_path / "artifacts")
    repo = SqliteJobRepository(db_path)
    store = LocalArtifactStore(artifacts_dir)
    return repo, store, tmp_path


@pytest.mark.asyncio
async def test_real_pipeline_stage_order_and_publication(test_setup) -> None:
    repo, store, tmp_path = test_setup

    # Create job in DB
    job = _create_test_job(
        repo=repo,
        job_id="job_real_1",
        topic="How does the TCP three-way handshake work?",
        audience="Developer",
        language="vi",
        target_duration_seconds=90,
    )

    recorded_stages: list[tuple[JobStage, int]] = []

    async def on_stage(stage: JobStage, progress: int) -> None:
        recorded_stages.append((stage, progress))

    # Fast test renderer producing small MP4 scenes
    class FastRenderer:
        async def render(self, scene, timing, output_path: Path):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            _generate_test_mp4(output_path, width=640, height=360, duration=timing.render_duration_seconds, with_audio=False)
            from app.rendering.base import RenderResult
            return RenderResult(
                path=str(output_path),
                width=640,
                height=360,
                duration_seconds=timing.render_duration_seconds,
            )

    fast_renderer = FastRenderer()
    router = RendererRouter(
        concept_renderer=fast_renderer,
        process_renderer=fast_renderer,
        comparison_renderer=fast_renderer,
        illustration_renderer=fast_renderer,
    )

    pipeline = RealVideoPipeline(
        planning_service=PlanningService(planner=DemoPlanner()),
        timeline_builder=TimelineBuilder(
            speech_provider=MockSpeechProvider(duration=1.8),
            artifact_store=store,
        ),
        renderer_router=router,
        video_assembler=VideoAssembler(fps=12),
        quality_gate=QualityGate(expected_width=640, expected_height=360, min_size_bytes=1000),
        artifact_store=store,
        repository=repo,
    )

    await pipeline.process(job, on_stage)

    # 1. Verify exact 6 stages and percentages
    expected_sequence = [
        (JobStage.PLANNING, 10),
        (JobStage.VALIDATING_PLAN, 25),
        (JobStage.AUDIO, 40),
        (JobStage.RENDERING, 60),
        (JobStage.ASSEMBLING, 80),
        (JobStage.VALIDATING_OUTPUT, 90),
    ]
    assert recorded_stages == expected_sequence

    # 2. Verify plan.json is persisted
    plan_path = store.get_path(job.id, "plan.json")
    assert plan_path.exists()
    assert "TCP" in plan_path.read_text(encoding="utf-8")

    # 3. Verify final.mp4 is published
    final_path = store.get_final_path(job.id)
    assert final_path is not None
    assert final_path.exists()
    assert final_path.stat().st_size > 1000

    # 4. Verify candidate final.pending.mp4 no longer exists
    pending_path = store.get_pending_final_path(job.id)
    assert not pending_path.exists()

    # 5. Verify artifact metadata recorded in repo
    updated_job = repo.get(job.id)
    assert updated_job is not None
    assert updated_job.artifact_path == "final.mp4"
    assert updated_job.artifact_metadata is not None
    assert updated_job.artifact_metadata["width"] == 640
    assert updated_job.artifact_metadata["height"] == 360


@pytest.mark.asyncio
async def test_real_renderer_e2e_integration(test_setup) -> None:
    """E2E test integrating DemoPlanner, real CP5 deterministic renderers, real FFmpeg assembler, and QualityGate."""
    repo, store, tmp_path = test_setup

    job = _create_test_job(
        repo=repo,
        job_id="job_real_renderers_e2e",
        topic="How does the TCP three-way handshake work?",
        audience="Developer",
        language="vi",
        target_duration_seconds=90,
    )

    recorded_stages: list[tuple[JobStage, int]] = []

    async def on_stage(stage: JobStage, progress: int) -> None:
        recorded_stages.append((stage, progress))

    width, height, fps = 640, 360, 12

    # Instantiate REAL CP5 renderers with test profile
    concept_renderer = ConceptCardRenderer(width=width, height=height, fps=fps)
    process_renderer = ProcessDiagramRenderer(width=width, height=height, fps=fps)
    comparison_renderer = ComparisonRenderer(width=width, height=height, fps=fps)
    illustration_renderer = IllustrationRenderer(
        width=width,
        height=height,
        fps=fps,
        enable_image_generation=False,
    )

    router = RendererRouter(
        concept_renderer=concept_renderer,
        process_renderer=process_renderer,
        comparison_renderer=comparison_renderer,
        illustration_renderer=illustration_renderer,
        enable_image_generation=False,
    )

    assembler = VideoAssembler(fps=fps)
    quality_gate = QualityGate(
        expected_width=width,
        expected_height=height,
        min_size_bytes=5_000,
    )

    # Use very short mock audio for fast test execution
    pipeline = RealVideoPipeline(
        planning_service=PlanningService(planner=DemoPlanner()),
        timeline_builder=TimelineBuilder(
            speech_provider=MockSpeechProvider(duration=0.6),
            artifact_store=store,
        ),
        renderer_router=router,
        video_assembler=assembler,
        quality_gate=quality_gate,
        artifact_store=store,
        repository=repo,
    )

    await pipeline.process(job, on_stage)

    # 1. Verify final artifact exists and is non-empty
    final_path = store.get_path(job.id, "final.mp4")
    assert final_path.exists()
    assert final_path.is_file()
    assert final_path.stat().st_size > 5_000

    # 2. Candidate pending file was atomically removed
    pending_path = store.get_pending_final_path(job.id)
    assert not pending_path.exists()

    # 3. Probe with ffprobe to verify video H.264, audio AAC, resolution 640x360
    proc = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_streams",
            "-show_format",
            "-of", "json",
            str(final_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    probe_data = json.loads(proc.stdout)
    streams = probe_data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    assert video_stream is not None, "Video stream must be present"
    assert video_stream.get("codec_name") == "h264", f"Expected h264, got {video_stream.get('codec_name')}"
    assert int(video_stream.get("width", 0)) == 640
    assert int(video_stream.get("height", 0)) == 360

    assert audio_stream is not None, "Audio stream must be present"
    assert audio_stream.get("codec_name") == "aac", f"Expected aac, got {audio_stream.get('codec_name')}"

    # 4. Verify repository record updated
    updated_job = repo.get(job.id)
    assert updated_job is not None
    assert updated_job.artifact_path == "final.mp4"
    assert updated_job.artifact_metadata is not None
    assert updated_job.artifact_metadata["width"] == 640
    assert updated_job.artifact_metadata["height"] == 360
    assert updated_job.artifact_metadata["video_codec"] == "h264"
    assert updated_job.artifact_metadata["audio_codec"] == "aac"


@pytest.mark.asyncio
async def test_real_pipeline_rejects_non_finite_render_duration(test_setup) -> None:
    """Verify that RealVideoPipeline explicitly rejects NaN and Inf render durations."""
    repo, store, _ = test_setup

    class NonFiniteRenderer:
        def __init__(self, bad_duration: float):
            self.bad_duration = bad_duration

        async def render(self, scene, timing, output_path: Path):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            _generate_test_mp4(output_path, width=640, height=360, duration=1.0, with_audio=False)
            from app.rendering.base import RenderResult
            return RenderResult(
                path=str(output_path),
                width=640,
                height=360,
                duration_seconds=self.bad_duration,
            )

    async def dummy_cb(s: JobStage, p: int) -> None:
        pass

    for idx, bad_duration in enumerate([float("nan"), float("inf"), float("-inf"), 0.0, -1.5]):
        job = _create_test_job(
            repo=repo,
            job_id=f"job_bad_duration_{idx}",
            topic="How does the TCP three-way handshake work?",
        )
        bad_renderer = NonFiniteRenderer(bad_duration)
        router = RendererRouter(
            concept_renderer=bad_renderer,
            process_renderer=bad_renderer,
            comparison_renderer=bad_renderer,
            illustration_renderer=bad_renderer,
        )
        pipeline = RealVideoPipeline(
            planning_service=PlanningService(planner=DemoPlanner()),
            timeline_builder=TimelineBuilder(
                speech_provider=MockSpeechProvider(duration=0.5),
                artifact_store=store,
            ),
            renderer_router=router,
            video_assembler=VideoAssembler(fps=12),
            quality_gate=QualityGate(expected_width=640, expected_height=360, min_size_bytes=1000),
            artifact_store=store,
            repository=repo,
        )

        with pytest.raises(PipelineExecutionError) as exc_info:
            await pipeline.process(job, dummy_cb)

        assert exc_info.value.code == "render_failed"
        assert exc_info.value.stage == JobStage.RENDERING


@pytest.mark.asyncio
async def test_job_runner_enforces_artifact_publication_invariant(test_setup) -> None:
    repo, store, _ = test_setup

    class IncompletePipeline(LearningVideoPipeline):
        """Pipeline that returns successfully but fails to publish final.mp4."""
        requires_published_artifact = True

        async def process(self, job: Job, on_stage: StageCallback) -> None:
            await on_stage(JobStage.PLANNING, 10)
            await on_stage(JobStage.VALIDATING_OUTPUT, 90)
            # Intentionally do not publish final.mp4

    pipeline = IncompletePipeline()
    runner = JobRunner(repository=repo, pipeline=pipeline, artifact_store=store)

    job = _create_test_job(
        repo=repo,
        job_id="job_runner_1",
        topic="TCP Handshake",
        audience="Developer",
        language="vi",
        target_duration_seconds=60,
    )

    await runner._process_job(job.id)

    updated_job = repo.get(job.id)
    assert updated_job is not None
    assert updated_job.status == JobStatus.FAILED
    assert updated_job.error is not None
    assert updated_job.error.code == "missing_published_artifact"
    assert updated_job.error.stage == JobStage.VALIDATING_OUTPUT


@pytest.mark.asyncio
async def test_job_runner_allows_fakepipeline_without_artifact(test_setup) -> None:
    repo, store, _ = test_setup

    pipeline = FakePipeline()
    assert pipeline.requires_published_artifact is False

    runner = JobRunner(repository=repo, pipeline=pipeline, artifact_store=store)
    job = _create_test_job(
        repo=repo,
        job_id="job_runner_2",
        topic="Any Topic",
        audience="Student",
        language="en",
        target_duration_seconds=60,
    )

    await runner._process_job(job.id)

    updated_job = repo.get(job.id)
    assert updated_job is not None
    assert updated_job.status == JobStatus.SUCCEEDED
    assert updated_job.progress_percent == 100


def test_video_endpoint_responses(test_setup) -> None:
    repo, store, tmp_path = test_setup

    # 1. Nonexistent job -> 404
    app = create_app(repository=repo, artifact_store=store, pipeline=FakePipeline())
    client = TestClient(app)

    res_404 = client.get("/api/jobs/nonexistent_123/video")
    assert res_404.status_code == 404

    # 2. Running job -> 409
    job_running = _create_test_job(
        repo=repo,
        job_id="job_running_1",
        topic="Running Job",
        audience="Student",
        language="vi",
        target_duration_seconds=60,
    )
    repo.update_state(job_running.id, status=JobStatus.RUNNING, stage=JobStage.RENDERING, progress_percent=60)
    res_409_running = client.get(f"/api/jobs/{job_running.id}/video")
    assert res_409_running.status_code == 409

    # 3. Failed job -> 409
    job_failed = _create_test_job(
        repo=repo,
        job_id="job_failed_1",
        topic="Failed Job",
        audience="Student",
        language="vi",
        target_duration_seconds=60,
    )
    from app.domain.errors import JobError
    repo.update_state(
        job_failed.id,
        status=JobStatus.FAILED,
        stage=JobStage.RENDERING,
        progress_percent=60,
        error=JobError(code="test_err", message="Failed", stage=JobStage.RENDERING),
    )
    res_409_failed = client.get(f"/api/jobs/{job_failed.id}/video")
    assert res_409_failed.status_code == 409

    # 4. Succeeded job with valid published final.mp4 -> 200
    job_succ = _create_test_job(
        repo=repo,
        job_id="job_succ_1",
        topic="How does the TCP three-way handshake work?",
        audience="Developer",
        language="vi",
        target_duration_seconds=60,
    )
    # Generate final.mp4 in artifacts
    final_path = store.get_path(job_succ.id, "final.mp4")
    final_path.parent.mkdir(parents=True, exist_ok=True)
    _generate_test_mp4(final_path, width=640, height=360, duration=2.0, with_audio=True)

    repo.update_state(job_succ.id, status=JobStatus.SUCCEEDED, stage=None, progress_percent=100)
    res_200 = client.get(f"/api/jobs/{job_succ.id}/video")
    assert res_200.status_code == 200
    assert res_200.headers["content-type"] == "video/mp4"
    assert "TCP" in res_200.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_real_mode_missing_key_safe_failure(test_setup) -> None:
    """REAL mode with absent/placeholder Gemini key uses UnconfiguredPlanner and fails safely without synthetic plan."""
    from unittest.mock import patch
    from app.config import Settings
    from app.pipeline.factory import UnconfiguredPlanner, create_pipeline

    repo, store, tmp_path = test_setup
    settings = Settings(
        pipeline_mode="real",
        gemini_api_key="",
        db_path=str(tmp_path / "test.db"),
        artifacts_dir=str(tmp_path / "artifacts"),
    )

    pipeline = create_pipeline(settings, repo, store)
    assert isinstance(pipeline, RealVideoPipeline)
    assert isinstance(pipeline.planning_service.planner, UnconfiguredPlanner)
    assert not isinstance(pipeline.planning_service.planner, DemoPlanner)

    runner = JobRunner(repository=repo, pipeline=pipeline, artifact_store=store)
    job = _create_test_job(
        repo=repo,
        job_id="job_real_no_key",
        topic="Arbitrary topic without Gemini key",
    )

    with patch("app.demo.planner.DemoPlanner") as mock_demo:
        await runner._process_job(job.id)
        assert mock_demo.call_count == 0

    updated_job = repo.get(job.id)
    assert updated_job is not None
    assert updated_job.status == JobStatus.FAILED
    assert updated_job.error is not None
    assert updated_job.error.code == "planner_not_configured"
    assert updated_job.error.stage == JobStage.PLANNING
    # Invariant: artifacts/lesson_plan.json must not exist
    plan_path = store.get_path(job.id, "lesson_plan.json")
    assert not plan_path.exists()


@pytest.mark.asyncio
async def test_real_mode_provider_failure_raises_without_demo_fallback(test_setup) -> None:
    """REAL mode provider failure maps to PipelineExecutionError and never falls back to DemoPlanner."""
    from unittest.mock import AsyncMock, patch
    from app.providers.llm.base import LessonPlanner, PlannerProviderError

    repo, store, tmp_path = test_setup

    class FailingPlanner(LessonPlanner):
        async def create_plan(self, request: LearningRequest):
            raise PlannerProviderError(
                code="planner_timeout",
                message="LLM provider request timed out.",
                retryable=True,
            )

        async def repair_plan(self, request, invalid_plan, errors):
            return await self.create_plan(request)

    planning_service = PlanningService(planner=FailingPlanner())
    router = RendererRouter()
    pipeline = RealVideoPipeline(
        planning_service=planning_service,
        timeline_builder=TimelineBuilder(speech_provider=AsyncMock(), artifact_store=store),
        renderer_router=router,
        video_assembler=VideoAssembler(fps=12),
        quality_gate=QualityGate(expected_width=640, expected_height=360, min_size_bytes=1000),
        artifact_store=store,
        repository=repo,
    )

    job = _create_test_job(
        repo=repo,
        job_id="job_real_provider_fail",
        topic="How does the TCP three-way handshake work?",
    )

    stages_seen: list[tuple[JobStage, int]] = []
    async def stage_cb(stage: JobStage, pct: int):
        stages_seen.append((stage, pct))

    with patch("app.demo.planner.DemoPlanner") as mock_demo:
        with pytest.raises(PipelineExecutionError) as exc_info:
            await pipeline.process(job, on_stage=stage_cb)
        assert mock_demo.call_count == 0

    err = exc_info.value
    assert err.code == "planner_timeout"
    assert err.stage == JobStage.PLANNING
    assert err.retryable is True

