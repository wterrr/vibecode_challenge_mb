"""Memory-bounded RGB frame hashing for the isolated paid live pilot.

Core Freeze is immutable. The frozen subtitle renderer still enforces every
typed cue check, produces the subtitle-burned real MP4, and computes the exact
SHA-256 of *all* decoded RGB bytes. Only the digest transport changes from a
fully buffered subprocess.run() to streaming subprocess.Popen(). The temporary
substitution is scoped to the synchronous call and always restored.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import tempfile
from typing import Sequence

import learnflow_v2.render.assembly as frozen_assembly
from learnflow_v2.render import burn_subtitles
from learnflow_v2.render.errors import RenderBackendError
from learnflow_v2.render.schema import RenderedArtifact, SubtitleRenderCue


def stream_decoded_rgb_digest(path: Path) -> str:
    """Bit-identical to the frozen decoder digest at O(1) Python buffer size."""
    command = [
        "ffmpeg", "-v", "error", "-i", str(path),
        "-map", "0:v:0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ]
    digest = hashlib.sha256()
    count = 0
    with tempfile.TemporaryFile(mode="w+b") as stderr_file:
        try:
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=stderr_file
            )
        except OSError as exc:
            raise RenderBackendError(
                f"failed to decode rendered video for digest: {exc}"
            ) from exc
        assert process.stdout is not None
        try:
            while True:
                chunk = process.stdout.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                count += len(chunk)
            exit_code = process.wait()
        except BaseException:
            process.kill()
            process.wait()
            raise
        finally:
            process.stdout.close()
        if exit_code != 0 or count == 0:
            stderr_file.seek(0)
            stderr = stderr_file.read()[-1000:].decode(
                "utf-8", errors="replace"
            )
            raise RenderBackendError(
                f"failed to decode rendered video for digest: {stderr}"
            )
    print(f"LIVE_RGB_DIGEST_STREAMED bytes={count} sha256=complete", flush=True)
    return digest.hexdigest()


def burn_subtitles_with_streaming_digest(
    video: RenderedArtifact,
    cues: Sequence[SubtitleRenderCue],
    output_path: str | Path,
) -> RenderedArtifact:
    """Use the frozen validator/subtitle FFmpeg path, swap only digest I/O."""
    original = frozen_assembly._decoded_rgb_digest
    frozen_assembly._decoded_rgb_digest = stream_decoded_rgb_digest
    try:
        return burn_subtitles(video, cues, output_path)
    finally:
        frozen_assembly._decoded_rgb_digest = original
