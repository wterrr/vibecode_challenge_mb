"""Offline VibeHost-compatible FFmpeg assembly regression tests.

The full audiovisual fixture executes inside the production Docker image.
No speech provider or paid LLM requests are made.
"""
import asyncio
import shutil
import subprocess

import pytest

from app.domain.errors import PipelineExecutionError
from app.domain.timeline import ResolvedSceneTiming, ResolvedTimeline, SubtitleCue
from app.pipeline import assembly as assembly_module
from app.pipeline.assembly import VideoAssembler, assembly_timeout_budget


def make_timeline(tmp_path, *, with_subtitles=True):
    scenes = []
    videos = []
    for index in (0, 1):
        name = f"s0{index + 1}_derivative"
        begin = float(index * 2)
        cues = (
            [SubtitleCue(
                start_seconds=begin + 0.2,
                end_seconds=begin + 1.7,
                text="Đạo hàm cho biết tốc độ biến thiên tức thời.",
            )]
            if with_subtitles else []
        )
        audio = tmp_path / f"{name}.padded.wav"
        video = tmp_path / f"{name}.mp4"
        scenes.append(ResolvedSceneTiming(
            scene_id=name,
            raw_audio_path=str(audio),
            padded_audio_path=str(audio),
            audio_duration_seconds=1.7,
            render_duration_seconds=2.0,
            start_seconds=begin,
            end_seconds=begin + 2.0,
            subtitle_cues=cues,
        ))
        videos.append(video)
    return ResolvedTimeline(scenes=scenes, total_duration_seconds=4.0), videos


def test_assembly_timeout_budget_scales_safely():
    assert assembly_timeout_budget(4.0) == 180
    assert assembly_timeout_budget(90.0) == 720
    assert assembly_timeout_budget(120.0) == 900
    with pytest.raises(ValueError):
        assembly_timeout_budget(float("nan"))


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome,expected_code", [
    ("timeout", "assembly_timeout"),
    ("nonzero", "assembly_ffmpeg_failed"),
    ("empty", "assembly_empty_output"),
])
async def test_assembly_failure_removes_partial_output_and_respects_override(
    monkeypatch, tmp_path, outcome, expected_code,
):
    timeline, videos = make_timeline(tmp_path)
    target = tmp_path / "final.pending.mp4"
    target.write_bytes(b"partial")

    calls = []
    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(cmd, 1)
        if outcome == "nonzero":
            return subprocess.CompletedProcess(cmd, 1, "", "SECRET stderr")
        target.unlink(missing_ok=True)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(assembly_module.subprocess, "run", fake_run)
    assembler = VideoAssembler(fps=24, timeout_seconds=1.5)
    with pytest.raises(PipelineExecutionError) as captured:
        await assembler.assemble("job-offline", videos, timeline, target)
    assert captured.value.code == expected_code
    assert "SECRET" not in str(captured.value)
    assert not target.exists()
    assert len(calls) == 1
    args, opts = calls[0]
    assert opts["timeout"] == 1.5
    assert "-threads" in args and args[args.index("-threads") + 1] == "2"
    assert "-preset" in args and args[args.index("-preset") + 1] == "ultrafast"
    assert "-filter_threads" in args and args[args.index("-filter_threads") + 1] == "2"


@pytest.mark.asyncio
@pytest.mark.parametrize("with_subtitles", [True, False])
async def test_native_production_720p_audio_video_assembly(tmp_path, with_subtitles):
    """End-to-end 720p H264+AAC final.pending.mp4 with/without burned captions."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("Only run natively in production Docker with FFmpeg")

    timeline, videos = make_timeline(tmp_path, with_subtitles=with_subtitles)
    for item in timeline.scenes:
        video = tmp_path / f"{item.scene_id}.mp4"
        audio = tmp_path / f"{item.scene_id}.padded.wav"
        subprocess.run([
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=navy:s=1280x720:r=24:d=2",
            "-t", "2", "-an", "-c:v", "libx264", "-preset", "ultrafast",
            "-threads", "2", "-pix_fmt", "yuv420p", str(video),
        ], check=True, timeout=40)
        subprocess.run([
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
            "-t", "2", "-c:a", "pcm_s16le", str(audio),
        ], check=True, timeout=40)

    target = tmp_path / "final.pending.mp4"
    await VideoAssembler(fps=24).assemble(
        "offline-assembly", videos, timeline, target,
    )
    assert target.is_file() and target.stat().st_size > 1000
    assert (tmp_path / "subtitles.srt").is_file()
    if with_subtitles:
        assert "Đạo hàm" in (tmp_path / "subtitles.srt").read_text()
    else:
        assert (tmp_path / "subtitles.srt").read_text() == ""

    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_format", "-show_streams",
        "-of", "json", str(target),
    ], check=True, capture_output=True, text=True, timeout=20)
    import json
    data = json.loads(probe.stdout)
    streams = data["streams"]
    video = next(s for s in streams if s.get("codec_type") == "video")
    audio = next(s for s in streams if s.get("codec_type") == "audio")
    assert video["codec_name"] == "h264" and video["pix_fmt"] == "yuv420p"
    assert video["width"] == 1280 and video["height"] == 720
    assert audio["codec_name"] == "aac"
    assert abs(float(data["format"]["duration"]) - 4.0) < 0.3
