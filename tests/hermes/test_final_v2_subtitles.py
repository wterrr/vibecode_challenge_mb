"""Offline final V2 subtitle preflight; never makes provider/API calls."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from lesson_pipeline.subtitle_policy import (
    MAX_SUBTITLE_CHARS, MAX_SUBTITLE_WORDS,
    _clean_text, check_safe_subtitle_band, normalize_tts_subtitles,
)


@dataclass
class Cue:
    start_seconds: float
    end_seconds: float
    text: str


@dataclass
class Rect:
    y: float
    height: float


@dataclass
class Box:
    node_id: str
    rect: Rect


@dataclass
class Layout:
    frame_height: float
    boxes: tuple


def test_short_tts_pages_preserve_all_words_and_do_not_overlap():
    cues = [
        Cue(.1, 6.2, "A very long narration with multiple concepts and definitions that absolutely must not occupy four lines on the video frame."),
        Cue(6.1, 9.0, "The mid point is updated and low moves."),
    ]
    pages = normalize_tts_subtitles(cues, audio_duration=10, scene_duration=10)
    assert len(pages) > 2
    assert all(len(p.text) <= MAX_SUBTITLE_CHARS and len(p.text.split()) <= MAX_SUBTITLE_WORDS for p in pages)
    assert all(b.start_seconds >= a.end_seconds - 1e-6 for a, b in zip(pages, pages[1:]))
    assert " ".join(p.text for p in pages) == " ".join(_clean_text(c.text) for c in cues)


def test_tts_fail_closed_on_absent_or_unsafe_cues():
    with pytest.raises(ValueError):
        normalize_tts_subtitles([], audio_duration=5, scene_duration=5)
    with pytest.raises(ValueError):
        normalize_tts_subtitles(
            [Cue(1, 1.1, "this is an extremely long string which must be chunked into multiple distinct pages")],
            audio_duration=5, scene_duration=5,
        )


def test_safe_subtitle_band_fails_if_scene_content_intersects():
    check_safe_subtitle_band(Layout(720, (Box("safe", Rect(500, 90)),)))
    with pytest.raises(ValueError, match="intersects"):
        check_safe_subtitle_band(Layout(720, (Box("unsafe", Rect(590, 40)),)))


def test_no_frozen_core_modification_or_paid_on_push():
    root = Path(__file__).resolve().parents[2]
    policy = (root / "lesson_pipeline" / "production.py").read_text()
    adapter = (root / "lesson_pipeline" / "subtitle_render_adapter.py").read_text()
    workflow = (root / ".github" / "workflows" / "live-v2d-evaluation.yml").read_text()
    assert "normalize_tts_subtitles" in policy
    assert "check_safe_subtitle_band(layout)" in policy
    assert "burn_short_subtitles" in policy
    assert "Fontsize=12" in adapter
    assert "stream_decoded_rgb_digest" in adapter
    assert "confirm_final_paid_run" in workflow
    push_rules = workflow.split("  push:", 1)[1].split("  pull_request:", 1)[0]
    assert "      - chatgpt/live-v2d-gpt6-luna-paid-pilot" not in push_rules
