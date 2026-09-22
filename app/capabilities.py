"""System and runtime capability detection for LearnFlow AI."""

from pathlib import Path
import shutil
import subprocess
from typing import Callable
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel
from app.config import Settings, get_settings

VIETNAMESE_SAMPLE = "Giải thích quá trình quang hợp"
SUPPORTED_H264_ENCODERS = ["libx264"]

DEFAULT_FONT_CANDIDATES = [
    # 1. Project-provided open font if present
    "assets/fonts/DejaVuSans.ttf",
    # 2. System DejaVu Sans (safe, full unicode/vietnamese support)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    # 3. Alternative system sans fonts
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "DejaVuSans.ttf",
]


class CapabilityReport(BaseModel):
    """Runtime capabilities summary for media generation."""

    ffmpeg: bool
    ffprobe: bool
    ffmpeg_h264: bool
    font_name: str | None = None
    manim: bool = False
    image_generation_configured: bool = False


def check_ffmpeg(lookup_fn: Callable[[str], str | None] = shutil.which) -> bool:
    """Check if ffmpeg executable exists in PATH."""
    return lookup_fn("ffmpeg") is not None


def check_ffprobe(lookup_fn: Callable[[str], str | None] = shutil.which) -> bool:
    """Check if ffprobe executable exists in PATH."""
    return lookup_fn("ffprobe") is not None


def check_h264(runner_fn: Callable[[], str] | None = None) -> bool:
    """Check if ffmpeg has libx264 (or supported H.264) encoder."""
    if runner_fn is None:
        def _default_runner() -> str:
            res = subprocess.run(
                ["ffmpeg", "-encoders"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return res.stdout

        runner_fn = _default_runner

    try:
        output = runner_fn()
        return any(enc in output for enc in SUPPORTED_H264_ENCODERS)
    except Exception:
        return False


def verify_render_vietnamese(font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> bool:
    """Verify that the font can render a Vietnamese sample without error."""
    try:
        img = Image.new("RGB", (320, 60), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), VIETNAMESE_SAMPLE, font=font, fill="black")
        return True
    except Exception:
        return False


def detect_font(
    candidate_paths: list[str] | None = None,
) -> tuple[str | None, bool]:
    """Find a usable sans font for Pillow with Vietnamese diacritic support.

    Returns:
        (font_name_or_path, vietnamese_render_ok)
    """
    paths = candidate_paths if candidate_paths is not None else DEFAULT_FONT_CANDIDATES

    for candidate in paths:
        path = Path(candidate)
        if path.is_file():
            try:
                loaded_font = ImageFont.truetype(str(path), size=18)
                if verify_render_vietnamese(loaded_font):
                    return str(path), True
            except Exception:
                continue

    # Fallback to font name lookup or default
    try:
        loaded_font = ImageFont.truetype("DejaVuSans.ttf", size=18)
        if verify_render_vietnamese(loaded_font):
            return "DejaVuSans.ttf", True
    except Exception:
        pass

    try:
        default_font = ImageFont.load_default()
        if verify_render_vietnamese(default_font):
            return "default", True
    except Exception:
        pass

    return None, False


def check_manim(lookup_fn: Callable[[str], str | None] = shutil.which) -> bool:
    """Check if manim executable is optionally installed.

    Missing Manim does not block CP0 or the application.
    """
    return lookup_fn("manim") is not None


def check_image_generation_configured(settings: Settings | None = None) -> bool:
    """Check if image generation is configured via settings without making API calls."""
    if settings is None:
        settings = get_settings()
    return (
        bool(settings.enable_image_generation)
        and settings.image_provider == "gemini"
        and bool(settings.gemini_api_key and settings.gemini_api_key.strip())
    )


def get_capability_report(
    settings: Settings | None = None,
    lookup_fn: Callable[[str], str | None] = shutil.which,
    runner_fn: Callable[[], str] | None = None,
    candidate_fonts: list[str] | None = None,
) -> CapabilityReport:
    """Detect and return full CapabilityReport."""
    has_ffmpeg = check_ffmpeg(lookup_fn)
    has_ffprobe = check_ffprobe(lookup_fn)
    has_h264 = check_h264(runner_fn) if has_ffmpeg else False
    font_name, _ = detect_font(candidate_fonts)
    has_manim = check_manim(lookup_fn)
    img_configured = check_image_generation_configured(settings)

    return CapabilityReport(
        ffmpeg=has_ffmpeg,
        ffprobe=has_ffprobe,
        ffmpeg_h264=has_h264,
        font_name=font_name,
        manim=has_manim,
        image_generation_configured=img_configured,
    )
