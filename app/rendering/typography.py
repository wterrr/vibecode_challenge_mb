"""Pillow typography and text layout utilities supporting Unicode and Vietnamese."""

import logging
from PIL import ImageDraw, ImageFont

from app.capabilities import detect_font

logger = logging.getLogger(__name__)

_DEFAULT_FONT_PATH: str | None = None


def get_system_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a TrueType font capable of rendering Vietnamese diacritics."""
    global _DEFAULT_FONT_PATH
    if _DEFAULT_FONT_PATH is None:
        detected, _ = detect_font()
        _DEFAULT_FONT_PATH = detected or ""

    if _DEFAULT_FONT_PATH:
        try:
            return ImageFont.truetype(_DEFAULT_FONT_PATH, size=size)
        except Exception as e:
            logger.warning("Failed loading font %s: %s", _DEFAULT_FONT_PATH, e)

    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def _split_long_token(
    token: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width_px: int,
    draw: ImageDraw.ImageDraw,
) -> list[str]:
    """Split an unbroken token into chunks that each fit within max_width_px."""
    if not token or max_width_px <= 0:
        return []

    token_bbox = draw.textbbox((0, 0), token, font=font)
    if (token_bbox[2] - token_bbox[0]) <= max_width_px:
        return [token]

    chunks: list[str] = []
    current_chars: list[str] = []

    for char in token:
        trial = "".join(current_chars + [char])
        bbox = draw.textbbox((0, 0), trial, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width_px:
            current_chars.append(char)
        else:
            if current_chars:
                chunks.append("".join(current_chars))
                current_chars = [char]
            else:
                # Even a single character exceeds max_width_px; keep single char
                chunks.append(char)
                current_chars = []

    if current_chars:
        chunks.append("".join(current_chars))

    return chunks


def wrap_text_to_width(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width_px: int,
    draw: ImageDraw.ImageDraw,
) -> list[str]:
    """Break text into wrapped lines that each strictly fit within max_width_px.

    Handles ordinary whitespace-separated prose and long unbroken tokens
    (identifiers, URLs, technical terms) by splitting at character boundaries
    using actual Pillow font metrics.
    """
    words = text.split()
    if not words or max_width_px <= 0:
        return []

    lines: list[str] = []
    current_line: list[str] = []

    for word in words:
        trial = " ".join(current_line + [word]) if current_line else word
        bbox = draw.textbbox((0, 0), trial, font=font)
        line_w = bbox[2] - bbox[0]
        if line_w <= max_width_px:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = []

            # Check if word alone fits
            w_bbox = draw.textbbox((0, 0), word, font=font)
            word_w = w_bbox[2] - w_bbox[0]
            if word_w <= max_width_px:
                current_line = [word]
            else:
                # Long unbroken token: split at character boundaries
                chunks = _split_long_token(word, font, max_width_px, draw)
                if chunks:
                    lines.extend(chunks[:-1])
                    current_line = [chunks[-1]]

    if current_line:
        lines.append(" ".join(current_line))

    return lines


def fit_or_truncate_text(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width_px: int,
    max_lines: int,
    draw: ImageDraw.ImageDraw,
    warnings: list[str] | None = None,
) -> list[str]:
    """Wrap text to max_width_px and truncate with ellipsis if exceeding max_lines.

    Ensures the final truncated line with ellipsis strictly obeys max_width_px.
    """
    if max_lines <= 0 or max_width_px <= 0:
        return []

    lines = wrap_text_to_width(text, font, max_width_px, draw)
    if len(lines) <= max_lines:
        return lines

    if warnings is not None:
        warnings.append(
            f"Text truncated: original {len(lines)} lines reduced to {max_lines}"
        )

    truncated = lines[:max_lines]
    last = truncated[-1]

    ellipsis = "..."
    # If standard 3-dot ellipsis alone exceeds width, try single glyph '…'
    e_bbox = draw.textbbox((0, 0), ellipsis, font=font)
    if (e_bbox[2] - e_bbox[0]) > max_width_px:
        ellipsis = "…"

    # Trim characters from last line until last + ellipsis <= max_width_px
    while last and (draw.textbbox((0, 0), last + ellipsis, font=font)[2] - draw.textbbox((0, 0), last + ellipsis, font=font)[0]) > max_width_px:
        last = last[:-1]

    last = last.rstrip()
    if last:
        truncated[-1] = last + ellipsis
    else:
        # If no prefix character could fit before ellipsis
        e_width = draw.textbbox((0, 0), ellipsis, font=font)[2] - draw.textbbox((0, 0), ellipsis, font=font)[0]
        if e_width <= max_width_px:
            truncated[-1] = ellipsis
        else:
            truncated[-1] = ""

    return truncated
