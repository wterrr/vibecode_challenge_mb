"""Unit tests for V1 baseline contracts and invariant enforcement.

Tests are cheap, network-free, and run without FFmpeg or heavy rendering.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import pytest

from app.domain.enums import JobStage, JobStatus
from app.domain.jobs import Job
from app.domain.lesson import LessonPlan
from scripts.capture_v1_baseline import (
    BaselineContractError,
    StageTrackingSqliteJobRepository,
    validate_artifact_against_baseline,
    validate_plan_against_baseline,
    validate_quality_gate_result,
    validate_stages_against_baseline,
)


@pytest.fixture
def baseline_manifest() -> dict:
    manifest_path = Path("benchmarks/baselines/v1/baseline.json")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


@pytest.fixture
def tcp_fixture_plan() -> LessonPlan:
    fixture_path = Path("benchmarks/fixtures/v1/tcp_three_way_handshake.json")
    return LessonPlan.model_validate(json.loads(fixture_path.read_text(encoding="utf-8")))


def test_valid_fixture_and_spec_passes(baseline_manifest, tcp_fixture_plan):
    spec = baseline_manifest["lessons"]["tcp_three_way_handshake"]
    # Must not raise
    validate_plan_against_baseline(tcp_fixture_plan, spec)


def test_scene_count_mismatch_raises(baseline_manifest, tcp_fixture_plan):
    spec = dict(baseline_manifest["lessons"]["tcp_three_way_handshake"])
    spec["scene_count"] = 999
    with pytest.raises(BaselineContractError, match="Scene count mismatch"):
        validate_plan_against_baseline(tcp_fixture_plan, spec)


def test_visual_intent_sequence_mismatch_raises(baseline_manifest, tcp_fixture_plan):
    spec = dict(baseline_manifest["lessons"]["tcp_three_way_handshake"])
    spec["visual_intent_sequence"] = ["illustration", "illustration", "illustration"]
    with pytest.raises(BaselineContractError, match="Visual intent sequence mismatch"):
        validate_plan_against_baseline(tcp_fixture_plan, spec)


def test_language_mismatch_raises(baseline_manifest, tcp_fixture_plan):
    spec = dict(baseline_manifest["lessons"]["tcp_three_way_handshake"])
    spec["language"] = "en"
    with pytest.raises(BaselineContractError, match="Language mismatch"):
        validate_plan_against_baseline(tcp_fixture_plan, spec)


def test_stage_sequence_matches_expected(baseline_manifest):
    spec = baseline_manifest["lessons"]["tcp_three_way_handshake"]
    actual_stages = [
        "planning",
        "validating_plan",
        "audio",
        "rendering",
        "assembling",
        "validating_output",
    ]
    # Must not raise
    validate_stages_against_baseline(actual_stages, spec)


def test_stage_sequence_missing_stage_raises(baseline_manifest):
    spec = baseline_manifest["lessons"]["tcp_three_way_handshake"]
    actual_stages = ["planning", "validating_plan", "audio", "rendering"]
    with pytest.raises(BaselineContractError, match="Terminal stages mismatch"):
        validate_stages_against_baseline(actual_stages, spec)


def test_stage_sequence_reordered_raises(baseline_manifest):
    spec = baseline_manifest["lessons"]["tcp_three_way_handshake"]
    actual_stages = [
        "planning",
        "validating_plan",
        "rendering",  # out of order: rendering before audio
        "audio",
        "assembling",
        "validating_output",
    ]
    with pytest.raises(BaselineContractError, match="Terminal stages mismatch"):
        validate_stages_against_baseline(actual_stages, spec)


def test_artifact_name_mismatch_raises(baseline_manifest):
    spec = baseline_manifest["lessons"]["tcp_three_way_handshake"]
    global_invariants = baseline_manifest["media_invariants"]
    # Must pass for correct name
    validate_artifact_against_baseline("final.mp4", spec, global_invariants)
    # Must reject wrong name
    with pytest.raises(BaselineContractError, match="Required final artifact mismatch"):
        validate_artifact_against_baseline("output.mp4", spec, global_invariants)


def test_quality_gate_result_derivation_pass(baseline_manifest):
    spec = baseline_manifest["lessons"]["tcp_three_way_handshake"]
    global_invariants = baseline_manifest["media_invariants"]

    result = validate_quality_gate_result(
        job_status=JobStatus.SUCCEEDED,
        artifact_path="/tmp/artifacts/job_1/final.mp4",
        artifact_exists=True,
        artifact_size=50_000,
        required_artifact_name="final.mp4",
        spec=spec,
        global_invariants=global_invariants,
    )
    assert result is True


def test_quality_gate_result_derivation_failures(baseline_manifest):
    spec = baseline_manifest["lessons"]["tcp_three_way_handshake"]
    global_invariants = baseline_manifest["media_invariants"]

    # Status failed
    with pytest.raises(BaselineContractError, match="Quality gate execution check failed"):
        validate_quality_gate_result(
            job_status=JobStatus.FAILED,
            artifact_path="/tmp/artifacts/job_1/final.mp4",
            artifact_exists=True,
            artifact_size=50_000,
            required_artifact_name="final.mp4",
            spec=spec,
            global_invariants=global_invariants,
        )

    # Artifact does not exist
    with pytest.raises(BaselineContractError, match="Quality gate execution check failed"):
        validate_quality_gate_result(
            job_status=JobStatus.SUCCEEDED,
            artifact_path="/tmp/artifacts/job_1/final.mp4",
            artifact_exists=False,
            artifact_size=0,
            required_artifact_name="final.mp4",
            spec=spec,
            global_invariants=global_invariants,
        )

    # Artifact too small
    with pytest.raises(BaselineContractError, match="Quality gate execution check failed"):
        validate_quality_gate_result(
            job_status=JobStatus.SUCCEEDED,
            artifact_path="/tmp/artifacts/job_1/final.mp4",
            artifact_exists=True,
            artifact_size=500,
            required_artifact_name="final.mp4",
            spec=spec,
            global_invariants=global_invariants,
        )

    # Artifact name mismatch in path
    with pytest.raises(BaselineContractError, match="Quality gate execution check failed"):
        validate_quality_gate_result(
            job_status=JobStatus.SUCCEEDED,
            artifact_path="/tmp/artifacts/job_1/wrong_name.mp4",
            artifact_exists=True,
            artifact_size=50_000,
            required_artifact_name="final.mp4",
            spec=spec,
            global_invariants=global_invariants,
        )


def test_stage_tracking_repository_deduplication():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test.db"
        repo = StageTrackingSqliteJobRepository(db_path)

        now = datetime.now(timezone.utc)
        job = Job(
            id="job_test_stage",
            topic="Test Topic",
            audience="Developer",
            language="vi",
            target_duration_seconds=60,
            created_at=now,
            updated_at=now,
        )
        repo.create(job)

        # Transition stages with consecutive duplicates
        repo.update_state(job.id, status=JobStatus.RUNNING, stage=JobStage.PLANNING, progress_percent=5)
        repo.update_state(job.id, status=JobStatus.RUNNING, stage=JobStage.PLANNING, progress_percent=10)
        repo.update_state(job.id, status=JobStatus.RUNNING, stage=JobStage.VALIDATING_PLAN, progress_percent=20)
        repo.update_state(job.id, status=JobStatus.RUNNING, stage=JobStage.AUDIO, progress_percent=35)
        repo.update_state(job.id, status=JobStatus.RUNNING, stage=JobStage.RENDERING, progress_percent=50)
        repo.update_state(job.id, status=JobStatus.RUNNING, stage=JobStage.ASSEMBLING, progress_percent=75)
        repo.update_state(job.id, status=JobStatus.RUNNING, stage=JobStage.VALIDATING_OUTPUT, progress_percent=90)
        repo.update_state(job.id, status=JobStatus.SUCCEEDED, stage=JobStage.VALIDATING_OUTPUT, progress_percent=100)

        assert repo.recorded_stages == [
            "planning",
            "validating_plan",
            "audio",
            "rendering",
            "assembling",
            "validating_output",
        ]
