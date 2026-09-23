"""Deterministic intrinsic content measurement for LearnFlow V2 layout pipeline.

Measures how much space content intrinsically requires BEFORE any spatial placement
or constraint solving occurs. Uses real font metrics (Pillow) and local image inspection.
No layout solving, no rendering, no absolute coordinates (x/y).
"""

from functools import lru_cache
import math
from pathlib import Path
import re
from typing import Callable, Literal
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from learnflow_v2.core.errors import (
    MeasurementAssetNotFoundError,
    MeasurementFontNotFoundError,
    MeasurementInvalidAssetError,
    MeasurementInvalidInputError,
    MeasurementUnsupportedMathError,
    MeasurementUnsupportedNodeError,
)
from learnflow_v2.scenegraph.enums import NodeKind
from learnflow_v2.scenegraph.schema import SceneNode

# Default system font search paths in order of preference
DEFAULT_SYSTEM_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
]

# Macros/commands requiring full 2D LaTeX rendering engine (unsupported in V2-02)
UNSUPPORTED_MATH_PATTERNS = [
    r"\\begin\{",
    r"\\end\{",
    r"\\int",
    r"\\sum",
    r"\\prod",
    r"\\oint",
    r"\\matrix",
    r"\\pmatrix",
    r"\\bmatrix",
    r"\\align",
    r"\\sqrt",
    r"\\lim",
    r"\\frac\{",
    r"\\over\b",
]


def _check_finite_positive(v: float, name: str, allow_zero: bool = True) -> float:
    """Validate that a float is finite and non-negative (or strictly positive)."""
    if not isinstance(v, (int, float)):
        raise ValueError(f"{name} must be numeric, got {type(v).__name__}")
    if not math.isfinite(v):
        raise ValueError(f"{name} must be a finite number, got {v}")
    if allow_zero:
        if v < 0.0:
            raise ValueError(f"{name} must be non-negative (>= 0.0), got {v}")
    else:
        if v <= 0.0:
            raise ValueError(f"{name} must be strictly positive (> 0.0), got {v}")
    return float(v)


# ---------------------------------------------------------------------------
# Strict Measurement Models
# ---------------------------------------------------------------------------


class IntrinsicSize(BaseModel):
    """Deterministic intrinsic dimension contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    width: float = Field(..., ge=0.0, description="Intrinsically required width in pixels")
    height: float = Field(..., ge=0.0, description="Intrinsically required height in pixels")
    minimum_readable_width: float = Field(..., ge=0.0, description="Lower bound width before content becomes unreadable")
    minimum_readable_height: float = Field(..., ge=0.0, description="Lower bound height before content becomes unreadable")

    @field_validator("width", "height", "minimum_readable_width", "minimum_readable_height")
    @classmethod
    def validate_finite(cls, v: float, info) -> float:
        return _check_finite_positive(v, info.field_name, allow_zero=True)


class WrapCandidate(BaseModel):
    """A deterministic text wrapping candidate for a specific maximum width."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_width: float = Field(..., gt=0.0, description="Target constraint width tested")
    width: float = Field(..., ge=0.0, description="Actual measured width of the wrapped lines")
    height: float = Field(..., ge=0.0, description="Actual measured height of the wrapped lines")
    line_count: int = Field(..., ge=1, description="Number of wrapped lines")
    lines: list[str] = Field(..., min_length=1, description="Ordered wrapped text lines")
    had_overflow_token: bool = Field(default=False, description="Whether an unbreakable token exceeded max_width")
    had_emergency_break: bool = Field(default=False, description="Whether an emergency token split was applied")

    @field_validator("max_width")
    @classmethod
    def validate_max_width(cls, v: float) -> float:
        return _check_finite_positive(v, "max_width", allow_zero=False)

    @field_validator("width", "height")
    @classmethod
    def validate_dimensions(cls, v: float, info) -> float:
        return _check_finite_positive(v, info.field_name, allow_zero=True)


class TextMeasurement(BaseModel):
    """Intrinsic measurement result for text-based semantic nodes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["text"] = "text"
    content: str = Field(..., min_length=1)
    font_name: str = Field(..., min_length=1)
    font_size: float = Field(..., gt=0.0)
    line_height: float = Field(..., gt=0.0)
    width: float = Field(..., ge=0.0)
    height: float = Field(..., ge=0.0)
    minimum_readable_width: float = Field(..., ge=0.0)
    minimum_readable_height: float = Field(..., ge=0.0)
    line_count: int = Field(..., ge=1)
    lines: list[str] = Field(..., min_length=1)
    wrap_candidates: list[WrapCandidate] = Field(default_factory=list)

    @field_validator("font_size", "line_height")
    @classmethod
    def validate_positive_metrics(cls, v: float, info) -> float:
        return _check_finite_positive(v, info.field_name, allow_zero=False)

    @field_validator("width", "height", "minimum_readable_width", "minimum_readable_height")
    @classmethod
    def validate_finite_dimensions(cls, v: float, info) -> float:
        return _check_finite_positive(v, info.field_name, allow_zero=True)


class MathMeasurement(BaseModel):
    """Intrinsic measurement result for mathematical expressions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["math"] = "math"
    expression: str = Field(..., min_length=1)
    font_name: str = Field(..., min_length=1)
    font_size: float = Field(..., gt=0.0)
    width: float = Field(..., ge=0.0)
    height: float = Field(..., ge=0.0)
    minimum_readable_width: float = Field(..., ge=0.0)
    minimum_readable_height: float = Field(..., ge=0.0)
    is_structural: bool = Field(default=False, description="Whether sub/superscript or fraction adjustment was applied")

    @field_validator("font_size")
    @classmethod
    def validate_font_size(cls, v: float) -> float:
        return _check_finite_positive(v, "font_size", allow_zero=False)

    @field_validator("width", "height", "minimum_readable_width", "minimum_readable_height")
    @classmethod
    def validate_math_dimensions(cls, v: float, info) -> float:
        return _check_finite_positive(v, info.field_name, allow_zero=True)


class AssetMeasurement(BaseModel):
    """Intrinsic measurement result for local raster images/assets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["asset"] = "asset"
    asset_path: str = Field(..., min_length=1)
    width: float = Field(..., gt=0.0)
    height: float = Field(..., gt=0.0)
    aspect_ratio: float = Field(..., gt=0.0)
    minimum_readable_width: float = Field(..., gt=0.0)
    minimum_readable_height: float = Field(..., gt=0.0)
    format: str = Field(..., min_length=1)

    @field_validator("width", "height", "aspect_ratio", "minimum_readable_width", "minimum_readable_height")
    @classmethod
    def validate_strictly_positive(cls, v: float, info) -> float:
        return _check_finite_positive(v, info.field_name, allow_zero=False)


class IconMeasurement(BaseModel):
    """Intrinsic measurement result for iconography."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["icon"] = "icon"
    name: str = Field(..., min_length=1)
    width: float = Field(..., gt=0.0)
    height: float = Field(..., gt=0.0)
    aspect_ratio: float = Field(default=1.0, gt=0.0)
    minimum_readable_width: float = Field(..., gt=0.0)
    minimum_readable_height: float = Field(..., gt=0.0)
    em_size: float = Field(..., gt=0.0)

    @field_validator("width", "height", "aspect_ratio", "minimum_readable_width", "minimum_readable_height", "em_size")
    @classmethod
    def validate_icon_positive(cls, v: float, info) -> float:
        return _check_finite_positive(v, info.field_name, allow_zero=False)


class MeasurementPolicy(BaseModel):
    """Configuration and constraint preferences for intrinsic measurement."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    font_path: str | None = Field(default=None, description="Explicit path to TrueType font file")
    preferred_font_size: float = Field(default=24.0, gt=0.0, description="Target font size for measurement")
    minimum_font_size: float = Field(default=14.0, gt=0.0, description="Minimum legible font size for readable bounds")
    line_spacing: float = Field(default=1.25, ge=1.0, description="Multiplier for line height calculation")
    candidate_max_widths: list[float] = Field(
        default_factory=lambda: [250.0, 400.0, 600.0, 900.0, 1200.0],
        description="Candidate target widths to generate wrapping alternatives",
    )
    emergency_break_long_tokens: bool = Field(
        default=False,
        description="If True, long unbreakable tokens are split into lines. If False, overflow is allowed and flagged.",
    )

    @field_validator("preferred_font_size", "minimum_font_size", "line_spacing")
    @classmethod
    def validate_policy_scalars(cls, v: float, info) -> float:
        return _check_finite_positive(v, info.field_name, allow_zero=False)

    @field_validator("candidate_max_widths")
    @classmethod
    def validate_widths(cls, widths: list[float]) -> list[float]:
        if not widths:
            raise ValueError("candidate_max_widths must contain at least one candidate width")
        validated: set[float] = set()
        for w in widths:
            val = _check_finite_positive(w, "candidate_max_width", allow_zero=False)
            validated.add(val)
        return sorted(validated)

    @model_validator(mode="after")
    def validate_font_size_range(self) -> "MeasurementPolicy":
        if self.minimum_font_size > self.preferred_font_size:
            raise ValueError(
                f"minimum_font_size ({self.minimum_font_size}) must be <= preferred_font_size ({self.preferred_font_size})"
            )
        return self


# ---------------------------------------------------------------------------
# Font Loading & Pillow Helpers
# ---------------------------------------------------------------------------


def resolve_font_path(explicit_path: str | Path | None = None) -> Path:
    """Resolve font path from explicit configuration or standard system locations."""
    if explicit_path:
        p = Path(explicit_path)
        if p.is_file():
            return p
        raise MeasurementFontNotFoundError(
            f"Requested font file not found: {explicit_path}",
            details={"requested_path": str(explicit_path)},
        )

    for cand in DEFAULT_SYSTEM_FONTS:
        p = Path(cand)
        if p.is_file():
            return p

    raise MeasurementFontNotFoundError(
        "No usable TrueType font found in standard system directories. "
        "Install DejaVu Sans or supply an explicit font_path in MeasurementPolicy.",
        details={"checked_paths": DEFAULT_SYSTEM_FONTS},
    )


@lru_cache(maxsize=32)
def _load_truetype_font(font_path_str: str, size: int) -> ImageFont.FreeTypeFont:
    """Cached loader for FreeType font instances."""
    try:
        return ImageFont.truetype(font_path_str, size)
    except Exception as exc:
        raise MeasurementFontNotFoundError(
            f"Failed to load font from '{font_path_str}': {exc}",
            details={"font_path": font_path_str, "error": str(exc)},
        ) from exc


def _get_draw_context() -> ImageDraw.ImageDraw:
    """Lightweight 1x1 scratch image draw context for deterministic bounding box calculations."""
    return ImageDraw.Draw(Image.new("RGBA", (1, 1)))


def _measure_text_bbox(font: ImageFont.FreeTypeFont, text: str) -> tuple[float, float]:
    """Measure visual width and height of a single line of text."""
    if not text:
        return 0.0, 0.0
    draw = _get_draw_context()
    bbox = draw.textbbox((0, 0), text, font=font)
    w = max(0.0, float(bbox[2] - bbox[0]))
    h = max(0.0, float(bbox[3] - bbox[1]))
    return w, h


# ---------------------------------------------------------------------------
# Intrinsic Measurement Implementations
# ---------------------------------------------------------------------------


def measure_text(
    text: str,
    policy: MeasurementPolicy | None = None,
) -> TextMeasurement:
    """Deterministically measure the intrinsic bounds and wrap candidates of text content."""
    policy = policy or MeasurementPolicy()

    if text is None or not text.strip():
        raise MeasurementInvalidInputError(
            "Text measurement input must not be empty or whitespace-only",
            details={"text": text},
        )

    font_path = resolve_font_path(policy.font_path)
    font_name = font_path.name
    font_size = policy.preferred_font_size
    font = _load_truetype_font(str(font_path), int(round(font_size)))

    ascent, descent = font.getmetrics()
    base_line_height = ascent + descent
    line_height = round(max(float(base_line_height), font_size * policy.line_spacing), 2)

    # 1. Natural multi-line or single-line measurement
    raw_lines = text.split("\n")
    line_widths = [_measure_text_bbox(font, l)[0] for l in raw_lines if l]
    natural_width = round(max(line_widths) if line_widths else 0.0, 2)
    natural_line_count = len(raw_lines)
    if natural_line_count == 1:
        _, raw_h = _measure_text_bbox(font, text)
        natural_height = round(max(float(base_line_height), raw_h), 2)
    else:
        natural_height = round((natural_line_count - 1) * line_height + base_line_height, 2)

    # 2. Minimum readable bounds at minimum_font_size
    min_font_size = policy.minimum_font_size
    min_font = _load_truetype_font(str(font_path), int(round(min_font_size)))
    min_ascent, min_descent = min_font.getmetrics()
    min_line_height = round(max(float(min_ascent + min_descent), min_font_size * policy.line_spacing), 2)

    words = text.split()
    word_min_widths = [_measure_text_bbox(min_font, w)[0] for w in words]
    min_readable_width = round(max(word_min_widths) if word_min_widths else 0.0, 2)
    min_readable_height = round(min_line_height, 2)

    # 3. Generate wrap candidates across policy widths
    wrap_candidates: list[WrapCandidate] = []
    for max_w in policy.candidate_max_widths:
        candidate = _generate_wrap_candidate(
            text=text,
            max_width=max_w,
            font=font,
            line_height=line_height,
            base_line_height=base_line_height,
            emergency_break=policy.emergency_break_long_tokens,
        )
        wrap_candidates.append(candidate)

    return TextMeasurement(
        kind="text",
        content=text,
        font_name=font_name,
        font_size=font_size,
        line_height=line_height,
        width=natural_width,
        height=natural_height,
        minimum_readable_width=min_readable_width,
        minimum_readable_height=min_readable_height,
        line_count=natural_line_count,
        lines=raw_lines,
        wrap_candidates=wrap_candidates,
    )


def _generate_wrap_candidate(
    text: str,
    max_width: float,
    font: ImageFont.FreeTypeFont,
    line_height: float,
    base_line_height: float,
    emergency_break: bool,
) -> WrapCandidate:
    """Deterministically assemble words into wrapped lines fitting within max_width,
    strictly preserving explicit hard line breaks.
    """
    hard_segments = text.split("\n")
    all_lines: list[str] = []
    had_overflow = False
    had_emergency_break = False

    for segment in hard_segments:
        words = segment.split()
        if not words:
            # Preserve empty line
            all_lines.append("")
            continue

        seg_lines: list[str] = []
        current_line: list[str] = []

        for word in words:
            w_word, _ = _measure_text_bbox(font, word)
            if not current_line:
                if w_word <= max_width:
                    current_line = [word]
                else:
                    if emergency_break:
                        had_emergency_break = True
                        rem = word
                        while rem:
                            fit_idx = 1
                            while fit_idx <= len(rem) and _measure_text_bbox(font, rem[:fit_idx])[0] <= max_width:
                                fit_idx += 1
                            if fit_idx == 1:
                                part = rem[:1]
                                rem = rem[1:]
                            else:
                                part = rem[: fit_idx - 1]
                                rem = rem[fit_idx - 1 :]
                            if rem:
                                seg_lines.append(part)
                            else:
                                current_line = [part]
                    else:
                        current_line = [word]
                        had_overflow = True
            else:
                candidate_line = " ".join(current_line + [word])
                w_cand, _ = _measure_text_bbox(font, candidate_line)
                if w_cand <= max_width:
                    current_line.append(word)
                else:
                    seg_lines.append(" ".join(current_line))
                    if w_word > max_width and emergency_break:
                        had_emergency_break = True
                        rem = word
                        while rem:
                            fit_idx = 1
                            while fit_idx <= len(rem) and _measure_text_bbox(font, rem[:fit_idx])[0] <= max_width:
                                fit_idx += 1
                            if fit_idx == 1:
                                part = rem[:1]
                                rem = rem[1:]
                            else:
                                part = rem[: fit_idx - 1]
                                rem = rem[fit_idx - 1 :]
                            if rem:
                                seg_lines.append(part)
                            else:
                                current_line = [part]
                    else:
                        current_line = [word]
                        if w_word > max_width:
                            had_overflow = True

        if current_line:
            seg_lines.append(" ".join(current_line))

        all_lines.extend(seg_lines)

    # Measure wrapped dimensions
    if not all_lines:
        cand_w, cand_h = 0.0, 0.0
    else:
        line_widths = [_measure_text_bbox(font, l)[0] for l in all_lines if l]
        cand_w = round(max(line_widths) if line_widths else 0.0, 2)
        if len(all_lines) == 1:
            _, raw_h = _measure_text_bbox(font, all_lines[0])
            cand_h = round(max(float(base_line_height), raw_h), 2)
        else:
            cand_h = round((len(all_lines) - 1) * line_height + base_line_height, 2)

    return WrapCandidate(
        max_width=max_width,
        width=cand_w,
        height=cand_h,
        line_count=max(1, len(all_lines)),
        lines=all_lines,
        had_overflow_token=had_overflow,
        had_emergency_break=had_emergency_break,
    )


def measure_math(
    expression: str,
    policy: MeasurementPolicy | None = None,
) -> MathMeasurement:
    """Deterministically measure mathematical expressions supported by V2-02."""
    policy = policy or MeasurementPolicy()

    if expression is None or not expression.strip():
        raise MeasurementInvalidInputError(
            "Math measurement expression must not be empty or whitespace-only",
            details={"expression": expression},
        )

    clean_expr = expression.strip()

    # Reject complex LaTeX environments requiring a full 2D TeX typesetting engine
    for pat in UNSUPPORTED_MATH_PATTERNS:
        if re.search(pat, clean_expr):
            raise MeasurementUnsupportedMathError(
                f"Math expression contains unsupported complex LaTeX syntax matching '{pat}'. "
                "V2-02 supports Unicode educational formulas, power notation (^), and subscripts (_).",
                details={"expression": clean_expr, "pattern": pat},
            )

    font_path = resolve_font_path(policy.font_path)
    font_name = font_path.name
    font_size = policy.preferred_font_size
    font = _load_truetype_font(str(font_path), int(round(font_size)))

    ascent, descent = font.getmetrics()
    base_line_height = ascent + descent

    # Detect lightweight structural notation (e.g. x^2, y_1)
    has_superscript = "^" in clean_expr
    has_subscript = "_" in clean_expr
    is_structural = has_superscript or has_subscript

    if is_structural:
        # Measure base and sub/superscript elements with conservative typographic layout
        parts = re.split(r"([\^_][a-zA-Z0-9\+\-]+)", clean_expr)
        total_width = 0.0
        script_font = _load_truetype_font(str(font_path), int(round(font_size * 0.75)))
        for p in parts:
            if not p:
                continue
            if p.startswith("^") or p.startswith("_"):
                w_s, _ = _measure_text_bbox(script_font, p[1:])
                total_width += w_s
            else:
                w_b, _ = _measure_text_bbox(font, p)
                total_width += w_b
        width = round(total_width, 2)
        height = round(base_line_height * 1.3, 2)  # Conservative vertical expansion for sub/superscript
    else:
        w_plain, h_plain = _measure_text_bbox(font, clean_expr)
        width = round(w_plain, 2)
        height = round(max(float(base_line_height), h_plain), 2)

    # Minimum readable bounds at minimum_font_size
    min_font_size = policy.minimum_font_size
    min_font = _load_truetype_font(str(font_path), int(round(min_font_size)))
    min_w, min_h = _measure_text_bbox(min_font, clean_expr)
    min_readable_width = round(min_w, 2)
    min_readable_height = round(min_h, 2)

    return MathMeasurement(
        kind="math",
        expression=clean_expr,
        font_name=font_name,
        font_size=font_size,
        width=width,
        height=height,
        minimum_readable_width=min_readable_width,
        minimum_readable_height=min_readable_height,
        is_structural=is_structural,
    )


def measure_asset(
    asset_path: str | Path,
    policy: MeasurementPolicy | None = None,
) -> AssetMeasurement:
    """Deterministically inspect a local image file and return its pixel dimensions and aspect ratio."""
    p = Path(asset_path)
    if not p.is_file():
        raise MeasurementAssetNotFoundError(
            f"Local asset file does not exist: {asset_path}",
            details={"path": str(asset_path)},
        )

    try:
        with Image.open(p) as img:
            w, h = img.size
            img_format = img.format or "UNKNOWN"
    except Exception as exc:
        raise MeasurementInvalidAssetError(
            f"Cannot decode or read asset file: {asset_path} ({exc})",
            details={"path": str(asset_path), "error": str(exc)},
        ) from exc

    if w <= 0 or h <= 0 or not math.isfinite(w) or not math.isfinite(h):
        raise MeasurementInvalidAssetError(
            f"Asset '{asset_path}' has non-positive or invalid pixel dimensions: {w}x{h}",
            details={"width": w, "height": h},
        )

    aspect_ratio = round(float(w) / float(h), 4)
    if not math.isfinite(aspect_ratio) or aspect_ratio <= 0.0:
        raise MeasurementInvalidAssetError(
            f"Asset '{asset_path}' produced non-finite or invalid aspect ratio: {aspect_ratio}",
            details={"aspect_ratio": aspect_ratio},
        )

    min_w = round(min(float(w), 32.0), 2)
    min_h = round(min(float(h), 32.0 / aspect_ratio), 2)

    return AssetMeasurement(
        kind="asset",
        asset_path=str(p.resolve()),
        width=float(w),
        height=float(h),
        aspect_ratio=aspect_ratio,
        minimum_readable_width=min_w,
        minimum_readable_height=min_h,
        format=img_format,
    )


def measure_icon(
    name: str,
    policy: MeasurementPolicy | None = None,
) -> IconMeasurement:
    """Deterministically measure an icon primitive using an em-based square bounding policy."""
    if not name or not name.strip():
        raise MeasurementInvalidInputError("Icon name must not be empty or whitespace-only")

    policy = policy or MeasurementPolicy()
    em_size = float(policy.preferred_font_size)
    min_em_size = float(policy.minimum_font_size)

    return IconMeasurement(
        kind="icon",
        name=name.strip(),
        width=em_size,
        height=em_size,
        aspect_ratio=1.0,
        minimum_readable_width=min_em_size,
        minimum_readable_height=min_em_size,
        em_size=em_size,
    )


def measure_node(
    node: SceneNode,
    policy: MeasurementPolicy | None = None,
    asset_resolver: Callable[[str], Path | str] | None = None,
) -> TextMeasurement | MathMeasurement | AssetMeasurement | IconMeasurement:
    """Primary dispatch entry point to measure any measurable SceneNode intrinsically."""
    policy = policy or MeasurementPolicy()

    if node.kind in (NodeKind.TEXT, NodeKind.CONCEPT, NodeKind.CALLOUT, NodeKind.CODE):
        content = node.content if node.content is not None else node.label
        if content is None or not content.strip():
            raise MeasurementInvalidInputError(
                f"Node '{node.id}' of kind {node.kind.value} has no readable text content or label",
                details={"node_id": node.id, "kind": node.kind.value},
            )
        return measure_text(content, policy)

    elif node.kind in (NodeKind.MATH, NodeKind.EQUATION):
        content = node.content if node.content is not None else node.label
        if content is None or not content.strip():
            raise MeasurementInvalidInputError(
                f"Math node '{node.id}' of kind {node.kind.value} has no expression content or label",
                details={"node_id": node.id, "kind": node.kind.value},
            )
        return measure_math(content, policy)

    elif node.kind == NodeKind.IMAGE:
        ref = node.content if node.content is not None else node.label
        if ref is None or not ref.strip():
            raise MeasurementInvalidInputError(
                f"IMAGE node '{node.id}' must provide a local asset path in content or label",
                details={"node_id": node.id},
            )
        path = asset_resolver(ref) if asset_resolver else Path(ref)
        return measure_asset(path, policy)

    elif node.kind == NodeKind.ICON:
        name = node.label or node.content or node.id
        return measure_icon(name, policy)

    else:
        raise MeasurementUnsupportedNodeError(
            f"Node kind '{node.kind.value}' does not support standalone intrinsic measurement",
            details={"node_id": node.id, "kind": node.kind.value},
        )
