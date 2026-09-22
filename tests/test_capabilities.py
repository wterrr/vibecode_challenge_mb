"""Unit tests for runtime and media capability detection (CP0).

All tests are deterministic and do not call external network services.
"""

import pytest
from app.capabilities import (
    CapabilityReport,
    check_ffmpeg,
    check_ffprobe,
    check_h264,
    check_image_generation_configured,
    check_manim,
    detect_font,
    get_capability_report,
    verify_render_vietnamese,
)
from app.config import Settings
from PIL import ImageFont


def test_ffmpeg_detected():
    """ffmpeg is reported as True when executable is found."""
    mock_lookup = lambda cmd: "/usr/bin/ffmpeg" if cmd == "ffmpeg" else None
    assert check_ffmpeg(lookup_fn=mock_lookup) is True


def test_ffmpeg_absent():
    """ffmpeg is reported as False when executable is missing."""
    mock_lookup = lambda cmd: None
    assert check_ffmpeg(lookup_fn=mock_lookup) is False


def test_ffprobe_detected():
    """ffprobe is reported as True when executable is found."""
    mock_lookup = lambda cmd: "/usr/bin/ffprobe" if cmd == "ffprobe" else None
    assert check_ffprobe(lookup_fn=mock_lookup) is True


def test_ffprobe_absent():
    """ffprobe is reported as False when executable is missing."""
    mock_lookup = lambda cmd: None
    assert check_ffprobe(lookup_fn=mock_lookup) is False


def test_h264_encoder_libx264_present():
    """H.264 detection passes when libx264 is in ffmpeg encoder list."""
    mock_runner = lambda: "Encoders:\n V..... libx264   libx264 H.264 / AVC\n"
    assert check_h264(runner_fn=mock_runner) is True


def test_h264_encoder_unavailable():
    """H.264 detection returns False when libx264 is missing or runner fails."""
    mock_runner = lambda: "Encoders:\n V..... mpeg4   MPEG-4 part 2\n"
    assert check_h264(runner_fn=mock_runner) is False

    error_runner = lambda: (_ for _ in ()).throw(RuntimeError("ffmpeg error"))
    assert check_h264(runner_fn=error_runner) is False


def test_manim_missing_does_not_throw():
    """Missing Manim must return False without throwing an exception."""
    mock_lookup = lambda cmd: None
    result = check_manim(lookup_fn=mock_lookup)
    assert result is False


def test_font_detection_and_fallback():
    """Font detection finds a usable font or falls back gracefully."""
    font_name, render_ok = detect_font()
    assert font_name is not None
    assert render_ok is True

    # Test fallback with nonexistent candidate paths
    font_name_fb, render_ok_fb = detect_font(
        candidate_paths=["/nonexistent/path/font.ttf"]
    )
    assert font_name_fb is not None
    assert render_ok_fb is True


def test_vietnamese_sample_render():
    """The default font can render Vietnamese diacritics without throwing."""
    default_font = ImageFont.load_default()
    assert verify_render_vietnamese(default_font) is True


@pytest.mark.parametrize(
    "enabled,provider,key,expected",
    [
        (False, "gemini", "my-secret-key", False),  # disabled -> false
        (True, "gemini", "", False),                # missing key -> false
        (True, "gemini", "   ", False),             # whitespace key -> false
        (True, "none", "my-secret-key", False),     # wrong provider -> false
        (True, "gemini", "valid-gemini-key", True), # enabled + gemini + key -> true
    ],
)
def test_image_generation_configuration(enabled, provider, key, expected):
    """Image generation capability reflects configuration without calling external API."""
    settings = Settings(
        enable_image_generation=enabled,
        image_provider=provider,
        gemini_api_key=key,
    )
    assert check_image_generation_configured(settings) is expected


def test_no_secret_exposed_in_capability_report_or_settings():
    """Ensure sensitive API keys are never exposed in capability reports or string representations."""
    secret_key = "AIzaSy_SUPER_SECRET_KEY_12345"
    settings = Settings(
        gemini_api_key=secret_key,
        enable_image_generation=True,
        image_provider="gemini",
    )

    report = get_capability_report(settings=settings)
    report_dict = report.model_dump()
    report_str = str(report)

    # Capability report must not contain secret
    assert secret_key not in report_str
    assert "gemini_api_key" not in report_dict
    assert report.image_generation_configured is True

    # Settings representation must mask the secret key
    settings_repr = repr(settings)
    assert secret_key not in settings_repr
    assert "***REDACTED***" in settings_repr
