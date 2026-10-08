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



def test_short_caption_policy_is_explicit_opt_in_and_legacy_default():
    root = Path(__file__).resolve().parents[2]
    source = (root / "lesson_pipeline" / "production.py").read_text()
    assert 'os.environ.get("LEARNFLOW_SHORT_TTS_SUBTITLES") == "1"' in source
    assert '"tts_short_pages_opt_in_v1" if use_short_cues' in source
    assert "else \"deterministic_script_segments\"" in source
    assert "check_safe_subtitle_band(layout)" in source
    assert "normalize_tts_subtitles(" in source


def test_no_api_provider_or_raw_auth_artifact_on_push():
    root = Path(__file__).resolve().parents[2]
    workflow = (root / ".github" / "workflows" / "live-v2d-evaluation.yml").read_text()
    provider = workflow.split("  live-provider-pilot:", 1)[1].split("    runs-on:", 1)[0]
    assert "github.event_name == 'workflow_dispatch'" in provider
    assert "github.event_name == 'push'" not in provider
    assert "github.event_name == 'pull_request'" not in provider
    assert "steps.redact_evidence.outcome == 'success'" in workflow
    assert "path: .hermes_runtime/approved-live-v2d-evidence" in workflow
    assert "path: .hermes_runtime/live-v2d-evaluation\n" not in workflow
