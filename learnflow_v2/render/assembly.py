"""Deterministic assembly of already-rendered V2 scene/transition clips."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import tempfile
from typing import Sequence

from learnflow_v2.render.errors import RenderBackendError, RenderInvalidInputError
from learnflow_v2.render.schema import RenderArtifactKind, RenderedArtifact


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
