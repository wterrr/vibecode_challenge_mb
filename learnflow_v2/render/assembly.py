"""Deterministic assembly of already-rendered V2 scene/transition clips."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import tempfile
from typing import Sequence

from learnflow_v2.render.errors import RenderBackendError, RenderInvalidInputError
from learnflow_v2.render.schema import RenderArtifactKind, RenderedArtifact, SubtitleRenderCue


def assemble_video(
    artifacts: Sequence[RenderedArtifact],
    output_path: str | Path,
) -> RenderedArtifact:
    if not artifacts:
        raise RenderInvalidInputError("assembly requires at least one rendered artifact")
    validated = [RenderedArtifact.model_validate(item.model_dump(mode="json")) for item in artifacts]
    width, height, fps = validated[0].width, validated[0].height, validated[0].fps
    for item in validated:
        if item.kind == RenderArtifactKind.VIDEO:
            raise RenderInvalidInputError("nested VIDEO artifact cannot be assembled")
        if (item.width, item.height, item.fps) != (width, height, fps):
            raise RenderInvalidInputError("all clips must share width/height/fps")
        if not Path(item.path).exists():
            raise RenderInvalidInputError(f"rendered clip does not exist: {item.path}")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="learnflow_v2_concat_") as td:
        concat_file = Path(td) / "clips.txt"
        lines = []
        for item in validated:
            escaped = str(Path(item.path).resolve()).replace("'", "'\\''")
            lines.append(f"file '{escaped}'")
        concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-c", "copy", "-map_metadata", "-1", str(output),
        ]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)
        except OSError as exc:
            raise RenderBackendError(f"failed to start ffmpeg assembly: {exc}") from exc
        if proc.returncode != 0:
            raise RenderBackendError(f"ffmpeg assembly failed: {proc.stderr[-1000:]}")
    if not output.exists() or output.stat().st_size <= 0:
        raise RenderBackendError("assembly produced no output")

    frame_count = sum(item.frame_count for item in validated)
    duration = sum(item.duration for item in validated)
    frame_digest = hashlib.sha256(
        "\n".join(item.frame_digest for item in validated).encode("utf-8")
    ).hexdigest()
    source_hash = hashlib.sha256(
        "\n".join(item.source_hash for item in validated).encode("utf-8")
    ).hexdigest()
    return RenderedArtifact(
        artifact_id="video:final",
        kind=RenderArtifactKind.VIDEO,
        path=str(output),
        duration=duration,
        width=width,
        height=height,
        fps=fps,
        frame_count=frame_count,
        frame_digest=frame_digest,
        source_hash=source_hash,
    )


def mux_audio_track(
    video_artifact: RenderedArtifact,
    audio_path: str | Path,
    output_path: str | Path,
) -> RenderedArtifact:
    """Mux one explicit audio track into an already-rendered VIDEO artifact.

    The renderer never synthesizes audio implicitly. Callers provide a concrete
    audio artifact; FFmpeg copies deterministic video bytes and encodes AAC.
    """
    video = RenderedArtifact.model_validate(video_artifact.model_dump(mode="json"))
    if video.kind != RenderArtifactKind.VIDEO:
        raise RenderInvalidInputError("audio mux requires a VIDEO artifact")
    video_path = Path(video.path)
    audio = Path(audio_path)
    if not video_path.exists() or video_path.stat().st_size <= 0:
        raise RenderInvalidInputError("video artifact path does not exist")
    if not audio.exists() or audio.stat().st_size <= 0:
        raise RenderInvalidInputError("audio path does not exist")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video_path),
        "-i", str(audio),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-af", "apad",
        "-shortest", "-map_metadata", "-1",
        str(output),
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)
    except OSError as exc:
        raise RenderBackendError(f"failed to start ffmpeg audio mux: {exc}") from exc
    if proc.returncode != 0:
        raise RenderBackendError(f"ffmpeg audio mux failed: {proc.stderr[-1000:]}")
    if not output.exists() or output.stat().st_size <= 0:
        raise RenderBackendError("audio mux produced no output")

    audio_digest = hashlib.sha256()
    with audio.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            audio_digest.update(chunk)
    source_hash = hashlib.sha256(
        f"{video.source_hash}\n{audio_digest.hexdigest()}\naac-128k-apad".encode("utf-8")
    ).hexdigest()
    return video.model_copy(
        update={
            "path": str(output),
            "source_hash": source_hash,
        }
    )


def _format_srt_timestamp(seconds: float) -> str:
    total_ms = int(round(max(0.0, float(seconds)) * 1000.0))
    hours = total_ms // 3_600_000
    remainder = total_ms % 3_600_000
    minutes = remainder // 60_000
    remainder %= 60_000
    secs = remainder // 1000
    millis = remainder % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _decoded_rgb_digest(path: Path) -> str:
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(path),
        "-map", "0:v:0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    except OSError as exc:
        raise RenderBackendError(f"failed to decode rendered video for digest: {exc}") from exc
    if proc.returncode != 0 or not proc.stdout:
        stderr = proc.stderr.decode("utf-8", errors="replace")
        raise RenderBackendError(f"failed to decode rendered video for digest: {stderr[-1000:]}")
    return hashlib.sha256(proc.stdout).hexdigest()


def burn_subtitles(
    video_artifact: RenderedArtifact,
    cues: Sequence[SubtitleRenderCue],
    output_path: str | Path,
) -> RenderedArtifact:
    """Burn validated subtitle cues into a VIDEO artifact while preserving audio.

    Subtitle text is presentation data; timing/content are explicit typed inputs.
    The function never infers or rewrites narration.
    """
    video = RenderedArtifact.model_validate(video_artifact.model_dump(mode="json"))
    if video.kind != RenderArtifactKind.VIDEO:
        raise RenderInvalidInputError("subtitle burn-in requires a VIDEO artifact")
    source = Path(video.path)
    if not source.exists() or source.stat().st_size <= 0:
        raise RenderInvalidInputError("video artifact path does not exist")
    if not isinstance(cues, (tuple, list)) or not cues:
        raise RenderInvalidInputError("subtitle burn-in requires at least one cue")
    validated = tuple(SubtitleRenderCue.model_validate(cue.model_dump(mode="json") if isinstance(cue, SubtitleRenderCue) else cue) for cue in cues)
    ordered = tuple(sorted(validated, key=lambda cue: (cue.start_seconds, cue.end_seconds, cue.text)))
    previous_end = -1.0
    for cue in ordered:
        if cue.start_seconds < previous_end - 1e-6:
            raise RenderInvalidInputError("subtitle cues must not overlap")
        if cue.end_seconds > video.duration + max(1.0 / video.fps, 1e-3):
            raise RenderInvalidInputError("subtitle cue exceeds video duration")
        previous_end = cue.end_seconds

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="learnflow_v2_subtitles_") as td:
        srt = Path(td) / "subtitles.srt"
        blocks = []
        for index, cue in enumerate(ordered, 1):
            blocks.append(
                f"{index}\n{_format_srt_timestamp(cue.start_seconds)} --> {_format_srt_timestamp(cue.end_seconds)}\n{cue.text}\n"
            )
        srt.write_text("\n".join(blocks), encoding="utf-8")
        escaped_srt = str(srt.resolve()).replace("\\", "/").replace(":", "\\:")
        force_style = (
            "Fontname=DejaVu Sans,Fontsize=22,PrimaryColour=&H00FFFFFF&,"
            "OutlineColour=&H00000000&,Outline=2,Shadow=0,MarginV=36,Alignment=2"
        )
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(source),
            "-vf", f"subtitles='{escaped_srt}':force_style='{force_style}'",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(video.fps),
            "-c:a", "copy", "-map_metadata", "-1",
            str(output),
        ]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)
        except OSError as exc:
            raise RenderBackendError(f"failed to start ffmpeg subtitle burn-in: {exc}") from exc
        if proc.returncode != 0:
            raise RenderBackendError(f"ffmpeg subtitle burn-in failed: {proc.stderr[-1000:]}")
    if not output.exists() or output.stat().st_size <= 0:
        raise RenderBackendError("subtitle burn-in produced no output")

    cue_payload = "\n".join(
        f"{cue.start_seconds:.6f}|{cue.end_seconds:.6f}|{cue.text}" for cue in ordered
    )
    source_hash = hashlib.sha256(
        f"{video.source_hash}\n{cue_payload}\nlibass-subtitles-v1".encode("utf-8")
    ).hexdigest()
    return video.model_copy(
        update={
            "path": str(output),
            "frame_digest": _decoded_rgb_digest(output),
            "source_hash": source_hash,
        }
    )
