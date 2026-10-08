"""Readable pilot-only subtitle burn-in; frozen LearnFlow Core remains unmodified."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import tempfile
from typing import Sequence

from learnflow_v2.render.errors import RenderBackendError, RenderInvalidInputError
from learnflow_v2.render.schema import RenderArtifactKind, RenderedArtifact, SubtitleRenderCue
from lesson_pipeline.media_digest_adapter import stream_decoded_rgb_digest

# Fontsize=12 tested on actual 720p run #180; Core's fontsize=22 was oversized.
_SUBTITLE_STYLE = (
    "Fontname=DejaVu Sans,Fontsize=12,PrimaryColour=&H00FFFFFF&,"
    "OutlineColour=&H00000000&,Outline=1,Shadow=0,MarginV=20,Alignment=2"
)


def _timestamp(seconds: float) -> str:
    total_ms = int(round(max(0.0, seconds) * 1000))
    return (f"{total_ms // 3600000:02}:"
            f"{(total_ms % 3600000) // 60000:02}:"
            f"{(total_ms % 60000) // 1000:02},"
            f"{total_ms % 1000:03}")


def burn_short_subtitles(
    video_artifact: RenderedArtifact,
    cues: Sequence[SubtitleRenderCue],
    output_path: str | Path,
) -> RenderedArtifact:
    """Validated cues, bounded libass text, and exact streaming RGB SHA256."""
    video = RenderedArtifact.model_validate(video_artifact.model_dump(mode="json"))
    if video.kind != RenderArtifactKind.VIDEO:
        raise RenderInvalidInputError("subtitle burn-in requires a VIDEO artifact")
    source = Path(video.path)
    if not source.is_file() or source.stat().st_size <= 0:
        raise RenderInvalidInputError("video artifact path does not exist")
    if not isinstance(cues, (list, tuple)) or not cues:
        raise RenderInvalidInputError("subtitle burn-in requires nonempty cues")
    validated = tuple(SubtitleRenderCue.model_validate(
        c.model_dump(mode="json") if isinstance(c, SubtitleRenderCue) else c
    ) for c in cues)
    ordered = tuple(sorted(validated, key=lambda c: (c.start_seconds, c.end_seconds, c.text)))
    for index, cue in enumerate(ordered):
        if index and cue.start_seconds < ordered[index - 1].end_seconds - 1e-6:
            raise RenderInvalidInputError("subtitle cues must not overlap")
        if cue.end_seconds > video.duration + max(1.0 / video.fps, 1e-3):
            raise RenderInvalidInputError("subtitle cue exceeds video duration")
        if len(cue.text) > 72 or len(cue.text.split()) > 12 or chr(96) in cue.text:
            raise RenderInvalidInputError("subtitle text violates short-page/readability contract")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="learnflow_short_subtitles_") as td:
        srt = Path(td) / "subtitles.srt"
        srt.write_text("\n".join(
            f"{index}\n{_timestamp(c.start_seconds)} --> {_timestamp(c.end_seconds)}\n{c.text}\n"
            for index, c in enumerate(ordered, 1)
        ), encoding="utf-8")
        escaped = str(srt.resolve()).replace("\\", "/").replace(":", "\\:")
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
            "-vf", f"subtitles='{escaped}':force_style='{_SUBTITLE_STYLE}'",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(video.fps),
            "-c:a", "copy", "-map_metadata", "-1", str(output),
        ]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        except OSError as exc:
            raise RenderBackendError(f"subtitle burn failed to start: {exc}") from exc
        if proc.returncode:
            raise RenderBackendError(f"subtitle burn failed: {proc.stderr[-1000:]}")
    if not output.is_file() or output.stat().st_size <= 0:
        raise RenderBackendError("subtitle burn produced no valid output")
    cue_payload = "\n".join(f"{c.start_seconds:.6f}|{c.end_seconds:.6f}|{c.text}" for c in ordered)
    source_hash = hashlib.sha256(
        f"{video.source_hash}\n{cue_payload}\nlibass-short-safe-v1".encode("utf-8")
    ).hexdigest()
    return video.model_copy(update={
        "path": str(output),
        "frame_digest": stream_decoded_rgb_digest(output),
        "source_hash": source_hash,
    })
