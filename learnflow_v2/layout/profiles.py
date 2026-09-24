"""Deterministic frame profiles and named safe regions for LearnFlow V2 layout.

Implements:
- 16:9 standard landscape profile (e.g. 1280x720)
- 9:16 standard portrait profile (e.g. 720x1280)
- Global safe-edge insets
- Named non-overlapping safe zones derived from proportional insets
- Grid specification for column/row alignment
"""

from typing import Literal
from learnflow_v2.core.errors import LayoutInvalidInputError
from learnflow_v2.core.errors import LayoutInvalidInputError
from learnflow_v2.layout.schema import FrameInsets, FrameProfile, GridSpec, Rect
import math
from typing import Any


def _strict_profile_dimension(v: Any, name: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)) or float(v) <= 0:
        raise LayoutInvalidInputError(f"{name} must be a finite positive real number")
    return float(v)


def create_frame_profile_16_9(
    width: float = 1280.0,
    height: float = 720.0,
) -> FrameProfile:
    """Generate a 16:9 landscape FrameProfile with deterministically derived safe regions.

    Safe zones:
    - SAFE_EDGE: outer safe margin (5% all sides)
    - SAFE_TITLE (TITLE): top title region (15% safe height)
    - SAFE_CONTENT (CONTENT): primary central content area (70% safe height)
    - SAFE_CAPTION (CAPTION): bottom caption/subtitle area (11% safe height)
    """
    w = round(_strict_profile_dimension(width, "width"), 2)
    h = round(_strict_profile_dimension(height, "height"), 2)

    # 5% safe margin insets
    pad_x = round(w * 0.05, 2)
    pad_y = round(h * 0.05, 2)
    insets = FrameInsets(top=pad_y, right=pad_x, bottom=pad_y, left=pad_x)

    safe_x = pad_x
    safe_y = pad_y
    safe_w = round(w - 2 * pad_x, 2)
    safe_h = round(h - 2 * pad_y, 2)

    # Proportional zone heights and gaps within safe area
    title_h = round(safe_h * 0.15, 2)
    gap_1 = round(safe_h * 0.02, 2)
    content_h = round(safe_h * 0.70, 2)
    gap_2 = round(safe_h * 0.02, 2)
    caption_h = round(safe_h - title_h - gap_1 - content_h - gap_2, 2)

    title_y = safe_y
    content_y = round(title_y + title_h + gap_1, 2)
    caption_y = round(content_y + content_h + gap_2, 2)

    safe_title = Rect(x=safe_x, y=title_y, width=safe_w, height=title_h)
    safe_content = Rect(x=safe_x, y=content_y, width=safe_w, height=content_h)
    safe_caption = Rect(x=safe_x, y=caption_y, width=safe_w, height=caption_h)
    safe_edge = Rect(x=safe_x, y=safe_y, width=safe_w, height=safe_h)

    zones = {
        "SAFE_EDGE": safe_edge,
        "SAFE_TITLE": safe_title,
        "SAFE_CONTENT": safe_content,
        "SAFE_CAPTION": safe_caption,
        # Normalized aliases
        "TITLE": safe_title,
        "CONTENT": safe_content,
        "CAPTION": safe_caption,
    }

    grid = GridSpec(
        columns=12,
        rows=6,
        horizontal_gap=round(w * 0.0125, 2),
        vertical_gap=round(h * 0.02, 2),
    )

    return FrameProfile(
        id=f"16:9_{int(w)}x{int(h)}",
        width=w,
        height=h,
        aspect_ratio="16:9",
        safe_edge_insets=insets,
        zones=zones,
        grid=grid,
    )


def create_frame_profile_9_16(
    width: float = 720.0,
    height: float = 1280.0,
) -> FrameProfile:
    """Generate a 9:16 portrait FrameProfile with deterministically derived safe regions.

    Safe zones:
    - SAFE_EDGE: outer safe margin (5% horizontal, 6% top, 10% bottom for mobile UI)
    - TOP_HOOK (TITLE, SAFE_TITLE): top title region (14% safe height)
    - PRIMARY_CONTENT (CONTENT, SAFE_CONTENT): middle primary content region (65% safe height)
    - SUBTITLE_ZONE (CAPTION, SAFE_CAPTION): subtitle zone (13% safe height)
    - BOTTOM_UI_SAFE: bottom UI buffer region (5% safe height)
    """
    w = round(_strict_profile_dimension(width, "width"), 2)
    h = round(_strict_profile_dimension(height, "height"), 2)

    pad_left = round(w * 0.05, 2)
    pad_right = round(w * 0.05, 2)
    pad_top = round(h * 0.06, 2)
    pad_bottom = round(h * 0.10, 2)  # Extra room for TikTok/Reels/Shorts bottom controls
    insets = FrameInsets(top=pad_top, right=pad_right, bottom=pad_bottom, left=pad_left)

    safe_x = pad_left
    safe_y = pad_top
    safe_w = round(w - pad_left - pad_right, 2)
    safe_h = round(h - pad_top - pad_bottom, 2)

    hook_h = round(safe_h * 0.14, 2)
    gap_1 = round(safe_h * 0.02, 2)
    content_h = round(safe_h * 0.65, 2)
    gap_2 = round(safe_h * 0.02, 2)
    sub_h = round(safe_h * 0.12, 2)
    gap_3 = round(safe_h * 0.01, 2)
    bottom_ui_h = round(safe_h - hook_h - gap_1 - content_h - gap_2 - sub_h - gap_3, 2)

    hook_y = safe_y
    content_y = round(hook_y + hook_h + gap_1, 2)
    sub_y = round(content_y + content_h + gap_2, 2)
    bottom_ui_y = round(sub_y + sub_h + gap_3, 2)

    top_hook = Rect(x=safe_x, y=hook_y, width=safe_w, height=hook_h)
    primary_content = Rect(x=safe_x, y=content_y, width=safe_w, height=content_h)
    subtitle_zone = Rect(x=safe_x, y=sub_y, width=safe_w, height=sub_h)
    bottom_ui_safe = Rect(x=safe_x, y=bottom_ui_y, width=safe_w, height=bottom_ui_h)
    safe_edge = Rect(x=safe_x, y=safe_y, width=safe_w, height=safe_h)

    zones = {
        "SAFE_EDGE": safe_edge,
        "TOP_HOOK": top_hook,
        "PRIMARY_CONTENT": primary_content,
        "SUBTITLE_ZONE": subtitle_zone,
        "BOTTOM_UI_SAFE": bottom_ui_safe,
        # Normalized aliases
        "SAFE_TITLE": top_hook,
        "TITLE": top_hook,
        "SAFE_CONTENT": primary_content,
        "CONTENT": primary_content,
        "SAFE_CAPTION": subtitle_zone,
        "CAPTION": subtitle_zone,
    }

    grid = GridSpec(
        columns=6,
        rows=12,
        horizontal_gap=round(w * 0.02, 2),
        vertical_gap=round(h * 0.015, 2),
    )

    return FrameProfile(
        id=f"9:16_{int(w)}x{int(h)}",
        width=w,
        height=h,
        aspect_ratio="9:16",
        safe_edge_insets=insets,
        zones=zones,
        grid=grid,
    )


# Standard singleton instances
PROFILE_16_9 = create_frame_profile_16_9(1280.0, 720.0)
PROFILE_9_16 = create_frame_profile_9_16(720.0, 1280.0)

_PROFILES = {
    "16:9": PROFILE_16_9,
    "16:9_1280x720": PROFILE_16_9,
    "9:16": PROFILE_9_16,
    "9:16_720x1280": PROFILE_9_16,
}


def get_frame_profile(profile_spec: str | FrameProfile) -> FrameProfile:
    """Resolve a FrameProfile instance from identifier or return as-is.

    Raises:
        LayoutInvalidInputError: If profile_spec is not a known identifier or valid FrameProfile.
    """
    if isinstance(profile_spec, FrameProfile):
        return profile_spec
    if isinstance(profile_spec, str) and profile_spec in _PROFILES:
        return _PROFILES[profile_spec]
    raise LayoutInvalidInputError(
        f"Unknown frame profile '{profile_spec}'. Supported: {list(_PROFILES.keys())}",
        details={"profile_spec": str(profile_spec), "supported_profiles": list(_PROFILES.keys())},
    )
