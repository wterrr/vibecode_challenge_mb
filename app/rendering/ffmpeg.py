"""FFmpeg video compilation routines for static and multi-state scene renders."""

import asyncio
import logging
from pathlib import Path
import subprocess

logger = logging.getLogger(__name__)


def _run_ffmpeg_compile(
    image_paths: list[Path],
    durations: list[float],
    total_duration: float,
    output_path: Path,
    fps: int = 24,
) -> None:
    """Execute FFmpeg to convert a list of image states into an MP4 video clip."""
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    n = len(image_paths)
    if n == 0:
        raise ValueError("Cannot compile zero image states into video.")

    cmd = ["ffmpeg", "-y"]

    if n == 1:
        cmd.extend([
            "-loop", "1",
            "-t", f"{total_duration:.4f}",
            "-i", str(image_paths[0]),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-t", f"{total_duration:.4f}",
            str(output_path),
        ])
    else:
        filter_inputs = []
        for i, (img, dur) in enumerate(zip(image_paths, durations)):
            cmd.extend([
                "-loop", "1",
                "-t", f"{dur:.4f}",
                "-i", str(img),
            ])
            filter_inputs.append(f"[{i}:v]")

        filter_expr = f"{''.join(filter_inputs)}concat=n={n}:v=1:a=0[v]"
        cmd.extend([
            "-filter_complex", filter_expr,
            "-map", "[v]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-t", f"{total_duration:.4f}",
            str(output_path),
        ])

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
        check=False,
    )

    if proc.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
        logger.error("FFmpeg compilation failed returncode=%d stderr=%s", proc.returncode, proc.stderr[-300:])
        raise RuntimeError(f"FFmpeg failed to compile scene video: {output_path.name}")


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
