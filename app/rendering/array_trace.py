"""Production adapter for the existing independently verified V3 array renderer.

Unlike developer-only V3 integration_slice, this adapter consumes a typed
model-proposed *input*, generates its own verified V3 algorithm trace, reuses
V3's stable-item-id frame geometry, and produces native 720p H264 directly for
RealVideoPipeline. No model-authored Python, step values or magic answers.
"""
from __future__ import annotations

import asyncio
from bisect import bisect_left
import hashlib
import logging
from pathlib import Path
import subprocess
import time
from typing import cast

from app.domain.lesson import ArrayTraceSpec, ScenePlan
from app.domain.timeline import ResolvedSceneTiming
from app.rendering.base import RenderResult, SceneRenderer
from learnflow_v3.binary_search_trace import (
    make_binary_search_trace, verify_binary_search_trace,
)
from learnflow_v3.sequence_renderer import (
    SequenceRenderProfile, draw_binary_search_frame, _validate_visual_labels,
)

log = logging.getLogger(__name__)


def verified_array_trace(spec: ArrayTraceSpec):
    """Verify both the source array and every trace transition independently."""
    # Pydantic's typed limits must be respected even when callers bypass
    # full lesson planning and call this renderer directly.
    spec = ArrayTraceSpec.model_validate(spec.model_dump(mode="json"))
    values = tuple(spec.values)
    trace = make_binary_search_trace(
        values=values, target=spec.target, source_ref="trace:production_array_scene",
    )
    proof = verify_binary_search_trace(trace)
    oracle_i = bisect_left(values, spec.target)
    expected = oracle_i if oracle_i < len(values) and values[oracle_i] == spec.target else None
    if proof.oracle_index != expected or trace.result_index != expected:
        raise ValueError("Independent binary search replay rejected")
    if len(trace.steps) < 2:
        raise ValueError("Algorithm animation requires multiple actual states")
    return trace


def beat_boundaries(timing: ResolvedSceneTiming, state_count: int) -> tuple[float, ...]:
    """Monotone scene-local motion boundaries derived from actual spoken duration.

    Subtitle cues are audio-aligned when available; in the fallback case they
    are length-proportional estimates. These boundaries do *not* claim
    independently verified word-to-animation alignment.
    """
    duration = timing.render_duration_seconds
    audible = min(timing.audio_duration_seconds, duration)
    cues = sorted(
        [c for c in timing.subtitle_cues
         if timing.start_seconds <= c.start_seconds < timing.start_seconds + audible],
        key=lambda c: c.start_seconds,
    )
    if len(cues) >= state_count:
        positions = [0.0]
        for i in range(1, state_count):
            cue = cues[i * len(cues) // state_count]
            positions.append(max(0.0, cue.start_seconds - timing.start_seconds))
        positions.append(duration)
        if all(b-a >= 0.08 for a,b in zip(positions,positions[1:])):
            return tuple(positions)
    # The verified algorithm trace has more comparison beats than actual
    # utterance segments; use a bounded audio-duration-driven distribution.
    return tuple(audible*i/state_count for i in range(state_count)) + (duration,)


class ArrayTraceRenderer(SceneRenderer):
    """Reuses verified V3 binary-search geometry with the production timeline."""

    def __init__(self, width: int = 1280, height: int = 720, fps: int = 24):
        self.profile = SequenceRenderProfile(
            width=width, height=height, fps=fps, seconds_per_step=1.0,
        )

    def _render_sync(self, scene: ScenePlan, timing: ResolvedSceneTiming, path: Path) -> None:
        if not isinstance(scene.visual_spec, ArrayTraceSpec):
            raise ValueError("Expected verified array_trace spec")
        trace = verified_array_trace(scene.visual_spec)
        _validate_visual_labels(self.profile, trace.query.values, trace.query.target)
        stages = beat_boundaries(timing, len(trace.steps))
        if len(stages) != len(trace.steps)+1:
            raise ValueError("Invalid timed algorithm beat count")

        path.parent.mkdir(parents=True, exist_ok=True)
        fps = self.profile.fps
        frames = max(fps, round(timing.render_duration_seconds*fps))
        cmd = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s:v", f"{self.profile.width}x{self.profile.height}",
            "-r", str(fps), "-i", "pipe:0", "-an",
            "-c:v", "libx264", "-preset", "ultrafast", "-threads", "2",
            "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path),
        ]
        proc = None
        start = time.monotonic()
        budget = max(180, min(600, int(timing.render_duration_seconds*9+60)))
        seen_states: set[int] = set()
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            assert proc.stdin is not None
            index = 0
            for k in range(frames):
                if time.monotonic()-start > budget:
                    raise TimeoutError("Verified trace rendering exceeded bounded CPU budget")
                seconds = k/fps
                while index+1 < len(trace.steps) and seconds >= stages[index+1]:
                    index += 1
                seen_states.add(index)
                beat_len = max(.08, stages[index+1]-stages[index])
                local = max(0.0,min(1.0,(seconds-stages[index])/beat_len))
                # The existing V3 renderer's first 32% of each beat tweens
                # pointer boundaries. Stretch that real geometric transition
                # over the full beat; preserve final highlighting near the end.
                motion_progress = local*.34 if index else local
                frame = draw_binary_search_frame(
                    trace=trace, step_index=index, progress=motion_progress,
                    subtitle="", profile=self.profile,
                )
                proc.stdin.write(frame.tobytes())
            proc.stdin.close()
            if proc.wait(timeout=max(1.0,budget-(time.monotonic()-start))) != 0:
                raise RuntimeError("Verified trace H264 encoder failed")
            if len(seen_states) < min(2,len(trace.steps)):
                raise ValueError("Verified trace motion states not represented")
            if not path.is_file() or path.stat().st_size < 1000:
                raise RuntimeError("Verified trace output missing")
        except (OSError, RuntimeError, ValueError, TimeoutError):
            if proc is not None and proc.poll() is None:
                proc.kill()
            if proc is not None:
                proc.wait()
            path.unlink(missing_ok=True)
            raise
        log.info(
            "Verified array trace rendered scene=%s states=%d trace_hash=%s",
            scene.scene_id, len(trace.steps), trace.trace_sha256[:16],
        )

    async def render(self, scene: ScenePlan, timing: ResolvedSceneTiming,
                     output_path: Path) -> RenderResult:
        await asyncio.to_thread(self._render_sync, scene, timing, Path(output_path))
        return RenderResult(
            path=str(output_path), width=self.profile.width,
            height=self.profile.height, duration_seconds=timing.render_duration_seconds,
            warnings=[],
        )
