"""Decoded-video temporal quality gate for certified production motion intents.

This cannot certify human pedagogical quality. It *can* reject a frozen or
corrupted MP4 that falsely claims verified semantic motion. Semantic trace
correctness is independently checked by the host's trace oracle.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
import subprocess

from app.domain.enums import VisualIntent

SEMANTIC_MOTION_INTENTS = frozenset({
    VisualIntent.ARRAY_TRACE,
    VisualIntent.FUNCTION_GRAPH,
    VisualIntent.CENTRAL_FORCE_MOTION,
    VisualIntent.CODE2VIDEO_SCENE,
})
SAMPLE_WIDTH, SAMPLE_HEIGHT = 160, 90
MIN_MEAN_DELTA = 0.70


def _decoded_luma_at(video: Path, seconds: float) -> bytes:
    result = subprocess.run([
        "ffmpeg", "-nostdin", "-v", "error",
        "-ss", f"{seconds:.3f}", "-i", str(video),
        "-frames:v", "1",
        "-vf", "crop=iw*0.90:ih*0.32:iw*0.05:ih*0.22,scale=160:90",
        "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
       timeout=25, check=False)
    expected = SAMPLE_WIDTH*SAMPLE_HEIGHT
    if result.returncode != 0 or len(result.stdout) != expected:
        raise ValueError("Semantic motion decoded frame unavailable")
    return result.stdout


def decoded_motion_delta(video: Path, duration: float) -> float:
    """Three decoded samples from pointer/array/curve viewport, excluding status and subtitle text."""
    if duration < 1.0 or not video.is_file():
        raise ValueError("Semantic video missing or too short")
    snapshots = [_decoded_luma_at(video, duration*t) for t in (.15,.50,.85)]
    deltas = [
        sum(abs(x-y) for x,y in zip(a,b)) / len(a)
        for a,b in zip(snapshots,snapshots[1:])
    ]
    value = max(deltas)
    if value < MIN_MEAN_DELTA:
        raise ValueError("semantic_motion_frames_static")
    return round(value,3)


async def verify_semantic_scene(video: Path, duration: float) -> float:
    return await asyncio.to_thread(decoded_motion_delta, Path(video), duration)
