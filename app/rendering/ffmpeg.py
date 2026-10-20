"""Bounded, resource-conscious FFmpeg scene compilation for production."""
import asyncio
import logging
from pathlib import Path
import subprocess

logger = logging.getLogger(__name__)


class SceneEncodeError(RuntimeError):
    """Safe error code for scene encoding; never expose raw FFmpeg stderr."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _compile_timeout(total_duration: float) -> int:
    # Production CPU can be constrained; bound runtime but allow slow hosts.
    return max(180, min(600, int(total_duration * 8 + 60)))


def _run_ffmpeg_compile(
    image_paths: list[Path],
    durations: list[float],
    total_duration: float,
    output_path: Path,
    fps: int = 24,
) -> None:
    """Compile staged PNG states to 720p H.264 without CPU oversubscription."""
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    n = len(image_paths)
    if n == 0 or n != len(durations):
        raise SceneEncodeError("render_invalid_states", "Scene image states are inconsistent.")
    if not 1 <= fps <= 60 or total_duration <= 0:
        raise SceneEncodeError("render_invalid_states", "Invalid scene timing or frame rate.")

    # A small shared host cannot afford unrestricted decoder, filter and x264
    # threading for each scene. Explicit still-image FPS also avoids dropping
    # 25->24fps frames in the concat stage.
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y"]
    for img, dur in zip(image_paths, durations):
        cmd.extend([
            "-loop", "1", "-framerate", str(fps), "-t", f"{dur:.4f}",
            "-i", str(img),
        ])

    if n > 1:
        filter_expr = f"{''.join(f'[{i}:v]' for i in range(n))}concat=n={n}:v=1:a=0[v]"
        cmd.extend([
            "-filter_complex_threads", "2",
            "-filter_complex", filter_expr,
            "-map", "[v]",
        ])
    else:
        cmd.extend(["-map", "0:v:0"])

    cmd.extend([
        "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "23", "-threads", "2", "-pix_fmt", "yuv420p",
        "-r", str(fps), "-t", f"{total_duration:.4f}",
        "-movflags", "+faststart", str(output_path),
    ])

    timeout = _compile_timeout(total_duration)
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        output_path.unlink(missing_ok=True)
        logger.error("Scene FFmpeg encoder timeout budget_seconds=%d states=%d fps=%d", timeout, n, fps)
        raise SceneEncodeError(
            "render_ffmpeg_timeout", "Scene encoding exceeded its time budget."
        ) from None
    except FileNotFoundError:
        output_path.unlink(missing_ok=True)
        logger.error("Scene FFmpeg executable missing")
        raise SceneEncodeError("render_ffmpeg_missing", "FFmpeg is not installed.") from None

    if proc.returncode != 0:
        output_path.unlink(missing_ok=True)
        # Raw stderr can contain paths and private data; report only the code.
        logger.error("Scene FFmpeg encoder failed returncode=%d states=%d", proc.returncode, n)
        raise SceneEncodeError(
            "render_ffmpeg_encode_failed", "Scene video encoder failed."
        )
    if not output_path.is_file() or output_path.stat().st_size == 0:
        output_path.unlink(missing_ok=True)
        logger.error("Scene FFmpeg encoder produced empty output states=%d", n)
        raise SceneEncodeError(
            "render_ffmpeg_empty_output", "Scene encoder produced an empty video."
        )


async def compile_states_to_video(
    image_paths: list[Path],
    durations: list[float],
    total_duration: float,
    output_path: Path,
    fps: int = 24,
) -> Path:
    """Async wrapper compiling image states to an MP4 video."""
    await asyncio.to_thread(
        _run_ffmpeg_compile,
        image_paths=image_paths,
        durations=durations,
        total_duration=total_duration,
        output_path=output_path,
        fps=fps,
    )
    return output_path
