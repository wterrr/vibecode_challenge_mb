"""Deterministic short TTS captions for the isolated final V2 evaluation."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Sequence

MAX_SUBTITLE_WORDS = 12
MAX_SUBTITLE_CHARS = 72
MIN_PAGE_SECONDS = 0.35
BOTTOM_SAFE_BAND_PX = 115.0


@dataclass(frozen=True)
class SubtitlePage:
    start_seconds: float
    end_seconds: float
    text: str


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace(chr(96), "").replace("**", "").strip()).strip()


def _page_words(text: str) -> tuple[str, ...]:
    words = text.split()
    pages: list[str] = []
    pending: list[str] = []
    for word in words:
        if len(word) > MAX_SUBTITLE_CHARS:
            raise ValueError("subtitle contains a token too long to display safely")
        candidate = " ".join((*pending, word))
        if pending and (len(pending) >= MAX_SUBTITLE_WORDS or len(candidate) > MAX_SUBTITLE_CHARS):
            pages.append(" ".join(pending))
            pending = []
        pending.append(word)
    if pending:
        pages.append(" ".join(pending))
    return tuple(pages)


def normalize_tts_subtitles(
    cues: Sequence[Any], *, audio_duration: float, scene_duration: float
) -> tuple[SubtitlePage, ...]:
    """Use real TTS sentence timing, split long sentences, and reject bad timing."""
    if audio_duration <= 0 or scene_duration <= 0 or not cues:
        raise ValueError("timed TTS narration cues required")
    end_of_audio = min(float(audio_duration), float(scene_duration))
    source = sorted(cues, key=lambda x: (float(x.start_seconds), float(x.end_seconds)))
    result: list[SubtitlePage] = []
    for i, cue in enumerate(source):
        text = _clean_text(str(cue.text))
        if not text:
            continue
        start = max(0.0, float(cue.start_seconds))
        end = min(end_of_audio, float(cue.end_seconds))
        if i + 1 < len(source):
            end = min(end, max(start, float(source[i + 1].start_seconds)))
        if result:
            start = max(start, result[-1].end_seconds)
        if end <= start:
            raise ValueError("TTS cue timing has a non-positive interval")
        pages = _page_words(text)
        if (end - start) / len(pages) < MIN_PAGE_SECONDS:
            raise ValueError("TTS subtitle interval too short for readable pages")
        current = start
        for index, page in enumerate(pages):
            page_end = end if index == len(pages) - 1 else start + (end - start) * (index + 1) / len(pages)
            if page_end - current < MIN_PAGE_SECONDS - 1e-6:
                raise ValueError("subtitle page too brief for legible timing")
            result.append(SubtitlePage(current, page_end, page))
            current = page_end
    if not result:
        raise ValueError("no nonempty TTS subtitle pages")
    if any(b.start_seconds < a.end_seconds - 1e-6 for a, b in zip(result, result[1:])):
        raise ValueError("overlapping subtitle pages after normalization")
    return tuple(result)


def check_safe_subtitle_band(layout: Any, *, safe_band_px: float = BOTTOM_SAFE_BAND_PX) -> None:
    """Never place captions over accepted pedagogical content geometry."""
    band_top = float(layout.frame_height) - safe_band_px
    if band_top <= 0:
        raise ValueError("video frame too short for safe subtitle band")
    intersecting = [
        box.node_id for box in layout.boxes
        if float(box.rect.y) + float(box.rect.height) > band_top + 1e-4
    ]
    if intersecting:
        raise ValueError(f"subtitle safe band intersects scene content: {sorted(intersecting)}")
