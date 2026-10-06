"""Frozen deterministic static-composition proxy for LearnFlow Core Gate benchmark.

The formula is specified in benchmarks/specs/v2_core_gate_v1.json and must not
be changed after the first benchmark execution. This is intentionally a narrow
proxy for static composition/readability, not a human aesthetic score.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import subprocess
from typing import Iterable

from PIL import Image
import numpy as np


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


def _background_rgb(rgb: np.ndarray) -> np.ndarray:
    h, w, _ = rgb.shape
    ph = max(1, int(round(h * 0.05)))
    pw = max(1, int(round(w * 0.05)))
    patches = np.concatenate([
        rgb[:ph, :pw].reshape(-1, 3),
        rgb[:ph, -pw:].reshape(-1, 3),
        rgb[-ph:, :pw].reshape(-1, 3),
        rgb[-ph:, -pw:].reshape(-1, 3),
    ], axis=0)
    return np.median(patches, axis=0)


def score_frame(path: Path) -> StaticFrameScore:
    with Image.open(path) as im:
        rgb = np.asarray(im.convert("RGB"), dtype=np.float64)
    bg = _background_rgb(rgb)
    distance = np.sqrt(np.sum((rgb - bg) ** 2, axis=2))
    foreground = distance > 24.0
    foreground_fraction = float(np.mean(foreground))

    luma = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
    contrast = _clip01(float(np.std(luma)) / 64.0)
    occupancy = _clip01(1.0 - abs(foreground_fraction - 0.30) / 0.30)

    h, w = foreground.shape
    mh = max(1, int(round(h * 0.04)))
    mw = max(1, int(round(w * 0.04)))
    margin_mask = np.zeros_like(foreground, dtype=bool)
    margin_mask[:mh, :] = True
    margin_mask[-mh:, :] = True
    margin_mask[:, :mw] = True
    margin_mask[:, -mw:] = True
    margin_foreground = float(np.mean(foreground[margin_mask])) if np.any(margin_mask) else 0.0
    safe_margin = 1.0 - _clip01(margin_foreground / 0.08)

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
    mean = lambda attr: sum(getattr(item, attr) for item in scores) / len(scores)
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
