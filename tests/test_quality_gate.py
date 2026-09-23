"""Unit and integration tests for Quality Gate and artifact validation."""

import subprocess
from pathlib import Path
import pytest

from app.demo.lesson_plans import DEMO_TCP_PLAN
from app.domain.timeline import ResolvedSceneTiming, ResolvedTimeline
from app.pipeline.quality_gate import QualityGate


def _generate_test_mp4(
    path: Path,
    width: int = 640,
    height: int = 360,
    duration: float = 2.0,
    fps: int = 12,
    with_audio: bool = True,
) -> Path:
    """Generate a tiny synthetic MP4 using ffmpeg for testing."""
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", f"color=c=navy:s={width}x{height}:d={duration}:r={fps}",
    ]
    if with_audio:
        cmd.extend([
            "-f", "lavfi",
            "-i", f"anullsrc=r=48000:cl=stereo:d={duration}",
            "-c:a", "aac",
        ])
    cmd.extend([
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(path),
    ])
    res = subprocess.run(cmd, capture_output=True, check=False)
    assert res.returncode == 0, f"FFmpeg error: {res.stderr.decode()}"
    return path


@pytest.fixture
def sample_timeline() -> ResolvedTimeline:
    """Provide a minimal timeline matching ~2.0s duration."""
    return ResolvedTimeline(
        job_id="test_job",
        scenes=[
            ResolvedSceneTiming(
                scene_id="s01",
                raw_audio_path="a.mp3",
                padded_audio_path="a_pad.wav",
                audio_duration_seconds=1.8,
                render_duration_seconds=2.0,
                start_seconds=0.0,
                end_seconds=2.0,
            )
        ],
        total_duration_seconds=2.0,
    )


@pytest.mark.asyncio
async def test_quality_gate_passes_valid_video(tmp_path: Path, sample_timeline: ResolvedTimeline) -> None:
    candidate = tmp_path / "valid.mp4"
    _generate_test_mp4(candidate, width=640, height=360, duration=2.0, with_audio=True)

    gate = QualityGate(expected_width=640, expected_height=360, min_size_bytes=1000)
    report = await gate.validate(candidate, sample_timeline, DEMO_TCP_PLAN)

    assert report.passed is True
    assert report.metadata["filename"] == "final.mp4"
    assert report.metadata["width"] == 640
    assert report.metadata["height"] == 360
    assert report.metadata["size_bytes"] == candidate.stat().st_size
    assert report.metadata["video_codec"] == "h264"
    assert report.metadata["audio_codec"] == "aac"
    assert 1.8 <= report.metadata["duration_seconds"] <= 2.2


@pytest.mark.asyncio
async def test_quality_gate_fails_missing_file(sample_timeline: ResolvedTimeline) -> None:
    non_existent = Path("/tmp/does_not_exist_12345.mp4")
    gate = QualityGate()
    report = await gate.validate(non_existent, sample_timeline, DEMO_TCP_PLAN)

    assert report.passed is False
    assert any(c.name == "file_exists" and not c.passed for c in report.checks)
    assert report.metadata == {}


@pytest.mark.asyncio
async def test_quality_gate_fails_below_min_size(tmp_path: Path, sample_timeline: ResolvedTimeline) -> None:
    tiny_file = tmp_path / "tiny.mp4"
    tiny_file.write_bytes(b"dummy corrupted short content")

    gate = QualityGate(min_size_bytes=50_000)
    report = await gate.validate(tiny_file, sample_timeline, DEMO_TCP_PLAN)

    assert report.passed is False
    assert any(c.name == "minimum_size" and not c.passed for c in report.checks)


@pytest.mark.asyncio
async def test_quality_gate_fails_video_without_audio(tmp_path: Path, sample_timeline: ResolvedTimeline) -> None:
    no_audio = tmp_path / "no_audio.mp4"
    _generate_test_mp4(no_audio, width=640, height=360, duration=2.0, with_audio=False)

    gate = QualityGate(expected_width=640, expected_height=360, min_size_bytes=1000)
    report = await gate.validate(no_audio, sample_timeline, DEMO_TCP_PLAN)

    assert report.passed is False
    assert any(c.name == "audio_stream_exists" and not c.passed for c in report.checks)


@pytest.mark.asyncio
async def test_quality_gate_fails_resolution_mismatch(tmp_path: Path, sample_timeline: ResolvedTimeline) -> None:
    wrong_res = tmp_path / "wrong_res.mp4"
    _generate_test_mp4(wrong_res, width=640, height=360, duration=2.0, with_audio=True)

    # Expecting 1280x720, but candidate is 640x360
    gate = QualityGate(expected_width=1280, expected_height=720, min_size_bytes=1000)
    report = await gate.validate(wrong_res, sample_timeline, DEMO_TCP_PLAN)

    assert report.passed is False
    assert any(c.name == "resolution_match" and not c.passed for c in report.checks)


@pytest.mark.asyncio
async def test_quality_gate_fails_duration_tolerance(tmp_path: Path, sample_timeline: ResolvedTimeline) -> None:
    long_video = tmp_path / "long.mp4"
    # Timeline expects 2.0s, but candidate is 5.0s (difference 3.0s > tolerance ~0.75s)
    _generate_test_mp4(long_video, width=640, height=360, duration=5.0, with_audio=True)

    gate = QualityGate(expected_width=640, expected_height=360, min_size_bytes=1000)
    report = await gate.validate(long_video, sample_timeline, DEMO_TCP_PLAN)

    assert report.passed is False
    assert any(c.name == "duration_within_tolerance" and not c.passed for c in report.checks)
