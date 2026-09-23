#!/usr/bin/env python3
"""Capture and verify LearnFlow V1 baseline performance against frozen contracts.

Exercises the real deterministic V1 downstream media path:
- Deterministic offline speech provider (no Edge TTS network)
- Real V1 TimelineBuilder
- Real V1 CP5 visual renderers (Pillow + FFmpeg, no FastRenderer stub)
- Real V1 VideoAssembler (FFmpeg concatenation & subtitles)
- Real V1 QualityGate (ffprobe verification)
- Fully isolated temporary SQLite and artifact storage
- Strict enforcement of baseline.json contracts (scene counts, intent sequences,
  language, stage order, required artifact name, derived quality gate result).
"""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.domain.enums import JobStage, JobStatus
from app.domain.errors import JobError
from app.domain.jobs import Job
from app.domain.lesson import LearningRequest, LessonPlan
from app.domain.timeline import SubtitleCue
from app.pipeline.assembly import VideoAssembler
from app.pipeline.quality_gate import QualityGate
from app.pipeline.real import RealVideoPipeline
from app.pipeline.timeline import TimelineBuilder
from app.planning.service import PlanningService
from app.providers.llm.base import LessonPlanner
from app.providers.speech.base import SpeechProvider, SpeechResult
from app.rendering.comparison import ComparisonRenderer
from app.rendering.concept_card import ConceptCardRenderer
from app.rendering.illustration import IllustrationRenderer
from app.rendering.process_diagram import ProcessDiagramRenderer
from app.rendering.router import RendererRouter
from app.repositories.sqlite import SqliteJobRepository
from app.runner.job_runner import JobRunner
from app.storage.local import LocalArtifactStore


class BaselineContractError(RuntimeError):
    """Raised when an execution or manifest invariant is violated."""
    pass


class StageTrackingSqliteJobRepository(SqliteJobRepository):
    """Benchmark-only SQLite repository wrapper recording deduplicated stage transitions."""

    def __init__(self, db_path: str | Path) -> None:
        super().__init__(db_path)
        self.recorded_stages: list[str] = []

    def update_state(
        self,
        job_id: str,
        *,
        status: JobStatus,
        stage: JobStage | None,
        progress_percent: int,
        error: JobError | None = None,
        increment_attempt: bool = False,
    ) -> Job | None:
        if stage is not None:
            stage_str = stage.value if isinstance(stage, JobStage) else str(stage)
            if not self.recorded_stages or self.recorded_stages[-1] != stage_str:
                self.recorded_stages.append(stage_str)
        return super().update_state(
            job_id,
            status=status,
            stage=stage,
            progress_percent=progress_percent,
            error=error,
            increment_attempt=increment_attempt,
        )


def validate_plan_against_baseline(
    plan: LessonPlan,
    spec: dict[str, Any],
) -> None:
    """Enforce exact scene count, visual intent sequence, and language contracts."""
    expected_scene_count = spec.get("scene_count")
    if expected_scene_count is not None and len(plan.scenes) != expected_scene_count:
        raise BaselineContractError(
            f"Scene count mismatch: expected {expected_scene_count}, got {len(plan.scenes)}"
        )

    expected_intents = spec.get("visual_intent_sequence")
    if expected_intents is not None:
        actual_intents = [s.visual_intent.value for s in plan.scenes]
        if actual_intents != expected_intents:
            raise BaselineContractError(
                f"Visual intent sequence mismatch: expected {expected_intents}, got {actual_intents}"
            )

    expected_language = spec.get("language")
    if expected_language is not None and plan.language != expected_language:
        raise BaselineContractError(
            f"Language mismatch: expected {expected_language!r}, got {plan.language!r}"
        )


def validate_stages_against_baseline(
    actual_stages: list[str],
    spec: dict[str, Any],
) -> None:
    """Enforce exact stage sequence from start to validation."""
    expected_stages = spec.get("expected_terminal_stages")
    if expected_stages is not None and actual_stages != expected_stages:
        raise BaselineContractError(
            f"Terminal stages mismatch: expected {expected_stages}, got {actual_stages}"
        )


def validate_artifact_against_baseline(
    final_artifact_name: str,
    spec: dict[str, Any],
    global_invariants: dict[str, Any],
) -> None:
    """Enforce expected final artifact name against baseline specification."""
    expected_artifact = (
        spec.get("required_final_artifact")
        or global_invariants.get("final_artifact_name", "final.mp4")
    )
    if final_artifact_name != expected_artifact:
        raise BaselineContractError(
            f"Required final artifact mismatch: expected {expected_artifact!r}, got {final_artifact_name!r}"
        )


def validate_quality_gate_result(
    *,
    job_status: JobStatus,
    artifact_path: str | None,
    artifact_exists: bool,
    artifact_size: int,
    required_artifact_name: str,
    spec: dict[str, Any],
    global_invariants: dict[str, Any],
) -> bool:
    """Derive quality gate pass from execution and publication invariants."""
    expected_qg = spec.get("quality_gate_expected") or global_invariants.get("quality_gate", "pass")

    passed = (
        job_status == JobStatus.SUCCEEDED
        and artifact_exists
        and artifact_size > 10_000
        and (artifact_path is not None and Path(artifact_path).name == required_artifact_name)
    )

    if expected_qg == "pass" and not passed:
        raise BaselineContractError(
            f"Quality gate execution check failed: status={job_status}, "
            f"artifact_exists={artifact_exists}, size={artifact_size}, artifact_path={artifact_path}"
        )
    return passed


class DeterministicBenchmarkSpeechProvider(SpeechProvider):
    """Network-free deterministic speech provider generating synthetic audio."""

    def __init__(self, scene_duration: float = 2.0) -> None:
        self.scene_duration = scene_duration

    async def synthesize(
        self,
        text: str,
        output_path: Path,
        language: str,
    ) -> SpeechResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Generate silent mp3 audio of precise deterministic duration
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi", "-i",
                f"anullsrc=r=48000:cl=stereo:d={self.scene_duration}",
                "-c:a", "libmp3lame", str(output_path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return SpeechResult(
            path=str(output_path),
            provider="deterministic_benchmark",
            duration_seconds=self.scene_duration,
            subtitle_cues=[
                SubtitleCue(
                    start_seconds=0.0,
                    end_seconds=self.scene_duration,
                    text=text[:40] if text else "Lesson narration",
                )
            ],
        )


class FixedPlanPlanner(LessonPlanner):
    """Serves a static prevalidated LessonPlan without external LLM calls."""

    def __init__(self, plan: LessonPlan) -> None:
        self.plan = plan

    async def create_plan(self, request: LearningRequest) -> LessonPlan:
        return self.plan

    async def repair_plan(
        self,
        request: LearningRequest,
        invalid_plan: LessonPlan,
        errors: list[Any],
    ) -> LessonPlan:
        return self.plan


def _probe_video(path: Path) -> dict[str, Any]:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=codec_name,codec_type,width,height:format=duration",
        "-of", "json",
        str(path),
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return json.loads(res.stdout)


async def run_benchmark_lesson(
    lesson_key: str,
    fixture_path: Path,
    expected_spec: dict[str, Any],
    global_invariants: dict[str, Any],
) -> dict[str, Any]:
    """Run a single lesson plan through the full downstream V1 pipeline."""
    plan_dict = json.loads(fixture_path.read_text(encoding="utf-8"))
    plan = LessonPlan.model_validate(plan_dict)

    # 1. Enforce plan baseline contracts (scene count, intent sequence, language)
    validate_plan_against_baseline(plan, expected_spec)

    # 2. Enforce required final artifact name contract
    required_artifact_name = (
        expected_spec.get("required_final_artifact")
        or global_invariants.get("final_artifact_name", "final.mp4")
    )
    validate_artifact_against_baseline(required_artifact_name, expected_spec, global_invariants)

    with tempfile.TemporaryDirectory(prefix=f"learnflow_bench_{lesson_key}_") as temp_dir:
        temp_path = Path(temp_dir)
        repo = StageTrackingSqliteJobRepository(str(temp_path / "bench.db"))
        store = LocalArtifactStore(str(temp_path / "artifacts"))

        job_id = f"job_v1_bench_{lesson_key}"
        now = datetime.now(timezone.utc)
        job = Job(
            id=job_id,
            topic=plan.topic,
            audience=plan.audience,
            language=plan.language,
            target_duration_seconds=expected_spec.get("target_duration_seconds", 90),
            status=JobStatus.QUEUED,
            created_at=now,
            updated_at=now,
        )
        repo.create(job)

        width = expected_spec.get("expected_width", global_invariants.get("width", 640))
        height = expected_spec.get("expected_height", global_invariants.get("height", 360))
        fps = global_invariants.get("fps", 12)

        router = RendererRouter(
            concept_renderer=ConceptCardRenderer(width=width, height=height, fps=fps),
            process_renderer=ProcessDiagramRenderer(width=width, height=height, fps=fps),
            comparison_renderer=ComparisonRenderer(width=width, height=height, fps=fps),
            illustration_renderer=IllustrationRenderer(width=width, height=height, fps=fps),
        )

        pipeline = RealVideoPipeline(
            planning_service=PlanningService(planner=FixedPlanPlanner(plan)),
            timeline_builder=TimelineBuilder(
                speech_provider=DeterministicBenchmarkSpeechProvider(scene_duration=2.0),
                artifact_store=store,
            ),
            renderer_router=router,
            video_assembler=VideoAssembler(fps=fps),
            quality_gate=QualityGate(
                expected_width=width,
                expected_height=height,
                min_size_bytes=10_000,
            ),
            artifact_store=store,
            repository=repo,
        )

        runner = JobRunner(
            repository=repo,
            pipeline=pipeline,
            artifact_store=store,
        )

        t_start = time.perf_counter()
        await runner._process_job(job_id)
        total_render_seconds = round(time.perf_counter() - t_start, 2)

        # 3. Enforce exact stage sequence contract
        validate_stages_against_baseline(repo.recorded_stages, expected_spec)

        # 4. Invariant checks
        job_final = repo.get(job_id)
        assert job_final is not None, f"Job {job_id} missing from repository"

        final_artifact = store.get_path(job_id, required_artifact_name)
        artifact_exists = final_artifact.exists()
        file_size = final_artifact.stat().st_size if artifact_exists else 0

        # 5. Derive quality gate execution result rather than hardcoding True
        quality_gate_passed = validate_quality_gate_result(
            job_status=job_final.status,
            artifact_path=job_final.artifact_path,
            artifact_exists=artifact_exists,
            artifact_size=file_size,
            required_artifact_name=required_artifact_name,
            spec=expected_spec,
            global_invariants=global_invariants,
        )

        # 6. ffprobe verification using manifest contracts
        probe_data = _probe_video(final_artifact)
        streams = probe_data.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        duration = float(probe_data.get("format", {}).get("duration", 0.0))

        assert v_stream is not None, "Missing video stream"
        assert a_stream is not None, "Missing audio stream"

        video_codec = v_stream.get("codec_name")
        audio_codec = a_stream.get("codec_name")
        out_width = v_stream.get("width")
        out_height = v_stream.get("height")

        expected_video_codec = expected_spec.get("expected_video_codec", global_invariants.get("video_codec", "h264"))
        expected_audio_codec = expected_spec.get("expected_audio_codec", global_invariants.get("audio_codec", "aac"))

        if video_codec != expected_video_codec:
            raise BaselineContractError(f"Video codec mismatch: expected {expected_video_codec}, got {video_codec}")
        if audio_codec != expected_audio_codec:
            raise BaselineContractError(f"Audio codec mismatch: expected {expected_audio_codec}, got {audio_codec}")
        if out_width != width:
            raise BaselineContractError(f"Width mismatch: expected {width}, got {out_width}")
        if out_height != height:
            raise BaselineContractError(f"Height mismatch: expected {height}, got {out_height}")

        d_min, d_max = expected_spec.get("valid_duration_range", (3.0, 60.0))
        if not (d_min <= duration <= d_max):
            raise BaselineContractError(f"Duration {duration}s outside range [{d_min}, {d_max}]")

        intents = [s.visual_intent.value for s in plan.scenes]

        return {
            "lesson_key": lesson_key,
            "status": "PASS",
            "scene_count": len(plan.scenes),
            "intent_sequence": intents,
            "render_success": True,
            "quality_gate_pass": quality_gate_passed,
            "video_codec": video_codec,
            "audio_codec": audio_codec,
            "width": out_width,
            "height": out_height,
            "duration_seconds": round(duration, 2),
            "total_render_seconds": total_render_seconds,
            "final_file_size": file_size,
        }


async def main() -> int:
    fixtures_dir = REPO_ROOT / "benchmarks" / "fixtures" / "v1"
    baseline_file = REPO_ROOT / "benchmarks" / "baselines" / "v1" / "baseline.json"

    if not baseline_file.exists():
        print(f"ERROR: Baseline file {baseline_file} not found.", file=sys.stderr)
        return 1

    baseline_manifest = json.loads(baseline_file.read_text(encoding="utf-8"))
    lessons_manifest = baseline_manifest.get("lessons", {})
    global_invariants = baseline_manifest.get("media_invariants", {})

    print("=" * 64)
    print("  LearnFlow V1 Baseline Capture & Verification")
    print(f"  Baseline Version: {baseline_manifest.get('baseline_version')}")
    print("=" * 64)
    print("\nRunning deterministic downstream V1 pipeline (network-free)...")

    results: list[dict[str, Any]] = []
    all_passed = True

    for lesson_key, spec in lessons_manifest.items():
        fixture_file = fixtures_dir / spec.get("fixture_file", f"{lesson_key}.json")
        if not fixture_file.exists():
            print(f"  {lesson_key:<26} FAIL (fixture missing: {fixture_file})")
            all_passed = False
            continue

        try:
            res = await run_benchmark_lesson(lesson_key, fixture_file, spec, global_invariants)
            results.append(res)
            print(f"  {lesson_key:<26} PASS ({res['scene_count']} scenes, {res['duration_seconds']}s, render: {res['total_render_seconds']}s, size: {res['final_file_size']:,} B)")
        except Exception as e:
            print(f"  {lesson_key:<26} FAIL ({type(e).__name__}: {e})")
            all_passed = False

    print("\n" + "=" * 64)
    passed_count = sum(1 for r in results if r.get("status") == "PASS")
    total_count = len(lessons_manifest)
    print(f"V1 BASELINE: {passed_count} / {total_count} PASS")
    print("=" * 64 + "\n")

    return 0 if (all_passed and passed_count == total_count) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
