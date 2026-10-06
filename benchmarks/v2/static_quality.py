"""Frozen deterministic static-composition proxy for LearnFlow Core Gate benchmark.

The formula is specified in benchmarks/specs/v2_core_gate_v1.json and must not
be changed after the first benchmark execution. This is intentionally a narrow
proxy for static composition/readability, not a human aesthetic score.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Iterable

from PIL import Image, ImageStat


@dataclass(frozen=True)
class StaticFrameScore:
    contrast: float
    occupancy_balance: float
    safe_margin: float
    total: float


def _clip01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def extract_frame(video_path: Path, timestamp: float, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{timestamp:.6f}",
        "-i", str(video_path),
        "-frames:v", "1",
        "-f", "image2",
        str(output_path),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if proc.returncode != 0 or not output_path.exists():
        raise RuntimeError(f"ffmpeg frame extraction failed: {proc.stderr[-1000:]}")
    return output_path


def _background_rgb(image: Image.Image) -> tuple[float, float, float]:
    w, h = image.size
    pw = max(1, int(round(w * 0.05)))
    ph = max(1, int(round(h * 0.05)))
    patches = [
        image.crop((0, 0, pw, ph)),
        image.crop((w - pw, 0, w, ph)),
        image.crop((0, h - ph, pw, h)),
        image.crop((w - pw, h - ph, w, h)),
    ]
    pixels: list[tuple[int, int, int]] = []
    for patch in patches:
        pixels.extend(list(patch.getdata()))
    channels = [sorted(pixel[index] for pixel in pixels) for index in range(3)]
    mid = len(pixels) // 2
    return tuple(float(channel[mid]) for channel in channels)  # type: ignore[return-value]


def score_frame(path: Path) -> StaticFrameScore:
    with Image.open(path) as src:
        image = src.convert("RGB")
        w, h = image.size
        bg = _background_rgb(image)
        pixels = list(image.getdata())

        foreground_flags: list[bool] = []
        for r, g, b in pixels:
            distance_sq = (r - bg[0]) ** 2 + (g - bg[1]) ** 2 + (b - bg[2]) ** 2
            foreground_flags.append(distance_sq > 24.0 ** 2)
        foreground_fraction = sum(foreground_flags) / len(foreground_flags)

        luma = image.convert("L")
        contrast = _clip01(float(ImageStat.Stat(luma).stddev[0]) / 64.0)
        occupancy = _clip01(1.0 - abs(foreground_fraction - 0.30) / 0.30)

        mh = max(1, int(round(h * 0.04)))
        mw = max(1, int(round(w * 0.04)))
        margin_count = 0
        margin_foreground = 0
        for y in range(h):
            row = y * w
            for x in range(w):
                if y < mh or y >= h - mh or x < mw or x >= w - mw:
                    margin_count += 1
                    if foreground_flags[row + x]:
                        margin_foreground += 1
        margin_fraction = margin_foreground / margin_count if margin_count else 0.0
        safe_margin = 1.0 - _clip01(margin_fraction / 0.08)

    total = 100.0 * (0.40 * contrast + 0.35 * occupancy + 0.25 * safe_margin)
    return StaticFrameScore(
        contrast=round(contrast, 8),
        occupancy_balance=round(occupancy, 8),
        safe_margin=round(safe_margin, 8),
        total=round(total, 8),
    )


def aggregate_static_quality(paths: Iterable[Path]) -> dict:
    scores = [score_frame(path) for path in paths]
    if not scores:
        raise ValueError("static quality requires at least one frame")

    def mean(attr: str) -> float:
        return sum(getattr(item, attr) for item in scores) / len(scores)

    return {
        "metric_id": "static_composition_proxy_v1",
        "frame_count": len(scores),
        "contrast": round(mean("contrast"), 8),
        "occupancy_balance": round(mean("occupancy_balance"), 8),
        "safe_margin": round(mean("safe_margin"), 8),
        "score": round(mean("total"), 8),
        "frames": [
            {
                "contrast": item.contrast,
                "occupancy_balance": item.occupancy_balance,
                "safe_margin": item.safe_margin,
                "total": item.total,
            }
            for item in scores
        ],
    }
