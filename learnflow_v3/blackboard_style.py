"""V3 blackboard look: absolute black + installed Computer Modern Unicode.

Font files are supplied by the operating system (fonts-cmu), never vendored.
Never silently substitute a different font: that would invalidate visual QA.
"""
from __future__ import annotations

from functools import lru_cache
import subprocess

from PIL import ImageFont

from .models import SemanticContractError

BLACK = (0, 0, 0)
WHITE = (236, 236, 236)
GREY = (142, 142, 142)
FAINT = (63, 63, 63)
YELLOW = (244, 216, 44)
CYAN = (83, 196, 231)
GREEN = (95, 208, 156)
RED = (236, 122, 101)
VIOLET = (176, 145, 228)


@lru_cache(maxsize=128)
def cmu_font(size: int, *, mono: bool = False) -> ImageFont.FreeTypeFont:
    """Resolve *real* CMU Serif / CMU Typewriter; refuse font substitution."""
    if size < 9 or size > 128:
        raise SemanticContractError("V3_FONT_SIZE_OUT_OF_BOUNDS")
    expected = "CMU Typewriter Text" if mono else "CMU Serif"
    try:
        p = subprocess.run(
            ["fc-match", "-f", "%{family}\n%{file}\n", expected],
            capture_output=True, check=True, text=True, timeout=6,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SemanticContractError("V3_COMPUTER_MODERN_UNAVAILABLE") from exc
    lines = p.stdout.strip().splitlines()
    if len(lines) < 2 or expected.casefold() not in lines[0].casefold():
        raise SemanticContractError(f"V3_COMPUTER_MODERN_UNAVAILABLE: {expected}")
    try:
        f = ImageFont.truetype(lines[1], size=size)
    except OSError as exc:
        raise SemanticContractError("V3_COMPUTER_MODERN_FONT_UNREADABLE") from exc
    if "cmu" not in " ".join(f.getname()).casefold():
        raise SemanticContractError("V3_COMPUTER_MODERN_FONT_IDENTITY_MISMATCH")
    return f


def text_width(draw, text: str, font) -> float:
    return draw.textbbox((0, 0), text, font=font)[2] - draw.textbbox((0, 0), text, font=font)[0]


def assert_fits(draw, text: str, font, max_width: int, *, role: str) -> None:
    if text_width(draw, text, font) > max_width:
        raise SemanticContractError(f"V3_TEXT_OVERFLOW:{role}")
