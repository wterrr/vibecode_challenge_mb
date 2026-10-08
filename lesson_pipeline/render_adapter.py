"""Opt-in production raster adapter; the frozen Core source is immutable.

This subclass is selected only in the isolated GPT-6 Luna pilot. The
drawing equations match the pinned frozen backend: only intermediate RGBA
allocation size changes. Regression tests compare final RGB pixel bytes.

Frame inputs come from the validated frozen Core render_scene_video call,
which passes the same immutable objects for every frame; repeated Pydantic
reconstruction is skipped for that identical input tuple only. Every new
set of model identities passes the Core validator first.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

from learnflow_v2.render import DeterministicPillowRenderer
from learnflow_v2.render.backend import (
    _KIND_COLORS,
    _TEXT,
    _TEXT_PADDING_X,
    _TEXT_PADDING_Y,
    DEFAULT_TEXT_FONT_SIZE_PX,
    _layout_text_in_rect,
    _node_text,
    _rect_tuple,
)
from learnflow_v2.layout.schema import Rect
from learnflow_v2.scenegraph.schema import SceneNode


class ProductionPillowRenderer(DeterministicPillowRenderer):
    """Pixel-equivalent local compositing, with per-scene validation caching."""

    def __init__(self) -> None:
        self._cached_inputs = None
        self._cached_validated = None

    def validate_scene_inputs(self, scene_graph, layout_graph, motion):
        requested = (scene_graph, layout_graph, motion)
        if (
            self._cached_inputs is not None
            and all(a is b for a, b in zip(requested, self._cached_inputs))
        ):
            return self._cached_validated
        validated = super().validate_scene_inputs(
            scene_graph, layout_graph, motion
        )
        self._cached_inputs = requested
        self._cached_validated = validated
        return validated

    def _draw_node(
        self,
        image: Image.Image,
        node: SceneNode,
        rect: Rect,
        *,
        opacity: float,
        reveal: float,
        emphasis: float,
    ) -> None:
        opacity = min(1.0, max(0.0, opacity))
        reveal = min(1.0, max(0.0, reveal))
        emphasis = min(1.0, max(0.0, emphasis))
        if opacity <= 0.001 or reveal <= 0.001:
            return
        x0, y0, x1, y1 = _rect_tuple(rect)
        x1 = max(x0 + 1, int(round(x0 + (x1 - x0) * reveal)))
        # The frozen Core paints a full-frame RGBA per node and per frame.
        # This adapter paints exactly the occupied pixels only.
        layer = Image.new(
            "RGBA", (max(1, x1 - x0 + 1), max(1, y1 - y0 + 1)), (0, 0, 0, 0)
        )
        draw = ImageDraw.Draw(layer)
        alpha = int(round(opacity * 255))
        base = _KIND_COLORS.get(node.kind.value, (48, 55, 70))
        fill = tuple(min(255, int(c + emphasis * 26)) for c in base) + (alpha,)
        outline = (90, 200, 250, alpha) if emphasis > 0.05 else (102, 116, 139, alpha)
        border = 2 + int(round(emphasis * 4))
        radius = max(4, min(18, int(min(rect.width, rect.height) * 0.08)))
        draw.rounded_rectangle((0, 0, x1 - x0, y1 - y0), radius=radius, fill=fill, outline=outline, width=border)
        text = _node_text(node)
        font, lines, line_h, text_width, text_height, inner_width, inner_height, fits = _layout_text_in_rect(draw, text, rect)
        if not fits:
            raise RenderInvalidInputError(
                f"Text for node '{node.id}' does not fit solved LayoutGraph box at "
                f"{DEFAULT_TEXT_FONT_SIZE_PX}px; text={text_width}x{text_height}, "
                f"inner_box={inner_width}x{inner_height}"
            )
        if lines:
            full_x1 = int(round(rect.x + rect.width))
            full_y1 = int(round(rect.y + rect.height))
            total_h = line_h * len(lines)
            ty = y0 + max(_TEXT_PADDING_Y, (full_y1 - y0 - total_h) // 2)
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                tw = bbox[2] - bbox[0]
                tx = x0 + max(_TEXT_PADDING_X, (full_x1 - x0 - tw) // 2)
                draw.text((tx - x0, ty - y0), line, font=font, fill=_TEXT + (alpha,))
                ty += line_h
        mask = layer.getchannel("A")
        if reveal < 0.999:
            reveal_x = max(x0, min(int(round(rect.x + rect.width * reveal)), int(round(rect.x + rect.width))))
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rectangle(
                (reveal_x - x0, 0, int(round(rect.x + rect.width)) - x0,
                 int(round(rect.y + rect.height)) - y0),
                fill=0,
            )
        image.paste(layer.convert("RGB"), (x0, y0), mask=mask)

