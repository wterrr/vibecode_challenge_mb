"""Deterministic production mathematical motion scenes (V3 integration slice).

The model selects a typed mathematical representation, never executes Python,
creates executable expressions, or authors pixel coordinates. The host owns
function evaluation, derivatives, geometry, identities and animation timing.

This is a reusable *function-graph* family, not a topic-specific script. It is
not an implementation of all research-only V3 SceneGraph families.
"""
from __future__ import annotations

import asyncio
import math
import os
from pathlib import Path
import subprocess
import time
from typing import cast

from PIL import Image, ImageDraw

from app.domain.lesson import FunctionGraphSpec, ScenePlan
from app.domain.timeline import ResolvedSceneTiming
from app.rendering.base import RenderResult, SceneRenderer
from app.rendering.typography import get_system_font

BG = (5, 7, 17)
GRID = (32, 41, 59)
AXIS = (116, 132, 153)
CURVE = (92, 218, 245)
SECANT = (250, 193, 90)
TANGENT = (192, 155, 245)
DOT = (255, 255, 255)
TEXT = (235, 241, 251)
MUTED = (162, 179, 199)


def value_and_slope(spec: FunctionGraphSpec, x: float) -> tuple[float, float]:
    """Host-computed analytic derivative, no model arithmetic is trusted."""
    if spec.function == "polynomial":
        f = sum(c * x ** i for i, c in enumerate(spec.coefficients))
        d = sum(i * c * x ** (i - 1) for i, c in enumerate(spec.coefficients) if i)
    elif spec.function == "sine":
        f, d = math.sin(x), math.cos(x)
    elif spec.function == "cosine":
        f, d = math.cos(x), -math.sin(x)
    elif spec.function == "exponential":
        f = d = math.exp(x)
    else:
        raise ValueError("Unsupported graph family")
    if not (math.isfinite(f) and math.isfinite(d)):
        raise ValueError("Nonfinite graph or derivative")
    return f, d


class FunctionGraphRenderer(SceneRenderer):
    """Draw true changing secants/tangents or scan a curve at 24fps.

    Display geometry is computed from a fixed numeric domain and bounded
    typed models. Subtitle region (>=590px at 720p) is reserved.
    """

    def __init__(self, width: int = 1280, height: int = 720, fps: int = 24):
        if width < 480 or height < 270 or not 6 <= fps <= 30:
            raise ValueError("Unsupported math animation output profile")
        self.width, self.height, self.fps = width, height, fps

    def _geometry(self, spec: FunctionGraphSpec):
        a = spec.focus_x
        # Keep source-independent geometry: the prompt cannot author pixels.
        xlo, xhi = a - 2.6, a + 2.6
        samples = [(xlo + (xhi - xlo) * i / 180) for i in range(181)]
        ys = [value_and_slope(spec, x)[0] for x in samples]
        ys.append(0.0)
        ymin, ymax = min(ys), max(ys)
        span = max(ymax - ymin, 1.8)
        ymin -= span * .16
        ymax += span * .16
        xleft, xright = .075 * self.width, .74 * self.width
        ytop, ybottom = .17 * self.height, .77 * self.height

        def xy(x, y):
            return (int(xleft + (x - xlo) / (xhi - xlo) * (xright - xleft)),
                    int(ybottom - (y - ymin) / (ymax - ymin) * (ybottom - ytop)))

        return xlo, xhi, ymin, ymax, xy

    def _frame(self, scene: ScenePlan, spec: FunctionGraphSpec, progress: float) -> Image.Image:
        im = Image.new("RGB", (self.width, self.height), BG)
        draw = ImageDraw.Draw(im)
        sc = self.height / 720
        title_font = get_system_font(max(17, int(32 * sc)))
        body_font = get_system_font(max(12, int(22 * sc)))
        num_font = get_system_font(max(11, int(19 * sc)))
        heading = "ĐỒ THỊ HÀM SỐ" if scene.title else "FUNCTION GRAPH"
        draw.text((int(75 * self.width / 1280), int(35 * sc)),
                  scene.title[:70], font=title_font, fill=TEXT)

        xlo, xhi, ymin, ymax, xy = self._geometry(spec)
        ax0 = xy(0, 0)
        for tick in range(-12, 13):
            x = tick / 2
            if xlo <= x <= xhi:
                px = xy(x, 0)[0]
                draw.line((px, int(.17*self.height), px, int(.77*self.height)),
                          fill=GRID, width=1)
            y = tick * max((ymax-ymin)/12, .3)
            if ymin <= y <= ymax:
                py = xy(0, y)[1]
                draw.line((int(.075*self.width), py, int(.74*self.width), py),
                          fill=GRID, width=1)
        if xlo <= 0 <= xhi:
            draw.line((ax0[0], int(.17*self.height), ax0[0], int(.77*self.height)), fill=AXIS, width=2)
        if ymin <= 0 <= ymax:
            draw.line((int(.075*self.width), ax0[1], int(.74*self.width), ax0[1]), fill=AXIS, width=2)

        # In the reveal stage only a growing prefix is visible; after that
        # the stable curve persists while the semantically relevant geometry moves.
        reveal_progress = min(1.0, progress / .25)
        amount = max(2, int(180 * reveal_progress))
        curve_points = []
        for i in range(amount + 1):
            x = xlo + (xhi-xlo) * i / 180
            y, _ = value_and_slope(spec, x)
            curve_points.append(xy(x, y))
        if len(curve_points) > 1:
            draw.line(curve_points, fill=CURVE, width=max(2, int(4 * sc)), joint="curve")

        # Graph stage: stable object P, persistent curve and changing Q/scan P.
        a = spec.focus_x
        if spec.motion_kind == "slope_scan":
            # A focus point travels along the curve and its tangent rotates.
            t = min(1.0, max(0.0, (progress - .25) / .75))
            a = xlo + .6 + (xhi-xlo-1.2) * t
        p_y, p_slope = value_and_slope(spec, a)
        p_px = xy(a, p_y)
        if progress >= .25:
            if spec.motion_kind == "secant_to_tangent":
                t = min(1.0, max(0.0, (progress - .25) / .75))
                h = 1.55 * (1.0 - t)**3 + .035
                q_y, _ = value_and_slope(spec, a+h)
                slope = (q_y - p_y)/h
                q_px = xy(a+h, q_y)
                draw.ellipse((q_px[0]-6, q_px[1]-6, q_px[0]+6, q_px[1]+6), fill=SECANT)
                draw.text((q_px[0]+8, q_px[1]-22), "Q", font=num_font, fill=SECANT)
                color = TANGENT if t >= .9 else SECANT
                label = f"h = {h:.2f}"
            else:
                slope = p_slope
                color = TANGENT
                label = f"x = {a:.2f}"

            # A line segment inside the plot viewport, drawn from a mathematically
            # calculated derivative/secant, not LLM-provided slope values.
            extent = .82
            segment = [xy(a-extent, p_y - slope*extent), xy(a+extent, p_y + slope*extent)]
            # Pillow drawing is clipped at the image boundary; ensure line
            # remains inside the graph rectangle by shortening large slopes.
            if max(abs(z[1]-p_px[1]) for z in segment) > .28*self.height:
                extent *= (.28*self.height) / max(abs(z[1]-p_px[1]) for z in segment)
                segment = [xy(a-extent, p_y-slope*extent), xy(a+extent, p_y+slope*extent)]
            draw.line(segment, fill=color, width=max(2, int(4 * sc)))
            draw.ellipse((p_px[0]-7, p_px[1]-7, p_px[0]+7, p_px[1]+7), fill=DOT)
            draw.text((p_px[0]+11, p_px[1]-20), "P", font=num_font, fill=DOT)
            side_x = int(.78 * self.width)
            draw.text((side_x, int(.28*self.height)), label, font=body_font, fill=SECANT)
            draw.text((side_x, int(.38*self.height)), f"f(x) = {p_y:.2f}", font=num_font, fill=TEXT)
            draw.text((side_x, int(.47*self.height)), f"slope = {slope:.2f}",
                      font=num_font, fill=color)
            if spec.motion_kind == "secant_to_tangent":
                draw.text((side_x, int(.56*self.height)), "secant → tangent",
                          font=get_system_font(max(11,int(17*sc))), fill=MUTED)
        draw.line((int(.07*self.width), int(.80*self.height),
                   int(.93*self.width), int(.80*self.height)), fill=GRID, width=2)
        # Keep the whole lower 18% unused; audio subtitle overlay owns it.
        return im

    def _render_sync(self, scene: ScenePlan, timing: ResolvedSceneTiming, path: Path) -> None:
        spec = cast(FunctionGraphSpec, scene.visual_spec)
        path.parent.mkdir(parents=True, exist_ok=True)
        frames = max(24, int(round(timing.render_duration_seconds * self.fps)))
        cmd = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{self.width}x{self.height}", "-r", str(self.fps), "-i", "-",
            "-an", "-c:v", "libx264", "-preset", "ultrafast",
            "-crf", "23", "-threads", "2", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(path),
        ]
        proc = None
        budget = max(180, min(600, int(timing.render_duration_seconds*9+60)))
        start = time.monotonic()
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            assert proc.stdin is not None
            for i in range(frames):
                if time.monotonic() - start > budget:
                    raise TimeoutError("Math animation exceeded bounded encoder budget")
                frame = self._frame(scene, spec, i / max(1, frames-1))
                proc.stdin.write(frame.tobytes())
            proc.stdin.close()
            if proc.wait(timeout=max(1.0, budget-(time.monotonic()-start))) != 0:
                raise RuntimeError("Math animation encoder returned nonzero exit")
            if not path.is_file() or path.stat().st_size < 1000:
                raise RuntimeError("Math animation encoder returned empty MP4")
        except (OSError, TimeoutError, RuntimeError):
            if proc and proc.poll() is None:
                proc.kill()
                proc.wait()
            path.unlink(missing_ok=True)
            raise

    async def render(self, scene: ScenePlan, timing: ResolvedSceneTiming,
                     output_path: Path) -> RenderResult:
        if not isinstance(scene.visual_spec, FunctionGraphSpec):
            raise ValueError("Function graph scene contract mismatch")
        await asyncio.to_thread(self._render_sync, scene, timing, Path(output_path))
        return RenderResult(path=str(output_path), width=self.width,
                            height=self.height,
                            duration_seconds=timing.render_duration_seconds, warnings=[])
