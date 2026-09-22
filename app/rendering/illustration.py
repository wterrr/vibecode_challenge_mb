"""Renderer for VisualIntent.ILLUSTRATION scenes with deterministic diagrammatic fallback."""

import asyncio
import logging
from pathlib import Path
import tempfile
from typing import cast
import uuid

from PIL import Image, ImageDraw

from app.domain.lesson import IllustrationSpec, ScenePlan
from app.domain.timeline import ResolvedSceneTiming
from app.providers.image.base import ImageProvider
from app.providers.image.prompts import build_illustration_prompt
from app.rendering.base import RenderResult, SceneRenderer
from app.rendering.canvas import (
    COLOR_ACCENT,
    COLOR_CARD,
    COLOR_CARD_BORDER,
    COLOR_HIGHLIGHT,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    SceneCanvas,
)
from app.rendering.ffmpeg import compile_states_to_video
from app.rendering.transitions import allocate_state_durations, select_progressive_state_indices
from app.rendering.typography import fit_or_truncate_text, get_system_font

logger = logging.getLogger(__name__)


class IllustrationRenderer(SceneRenderer):
    """Renders visual scenes with schematic educational framing, heading, and key points."""

    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        fps: int = 24,
        image_provider: ImageProvider | None = None,
        enable_image_generation: bool = False,
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.image_provider = image_provider
        self.enable_image_generation = enable_image_generation

    def _render_state(
        self,
        scene: ScenePlan,
        spec: IllustrationSpec,
        state_idx: int,
        warnings: list[str],
        generated_image_path: Path | None = None,
    ) -> Path:
        canvas = SceneCanvas(self.width, self.height)
        scale = canvas.scale

        content_top = canvas.draw_header(
            scene_id=scene.scene_id,
            title=scene.title,
            warnings=warnings,
        )

        pad_x = int(48 * scale)
        usable_w = self.width - (2 * pad_x)

        # Central Visual Framing Container
        visual_h = int(240 * scale)
        panel_box = (pad_x, content_top, pad_x + usable_w, content_top + visual_h)

        # Draw AI Image or Fallback Schematic Diagram
        composed_ai_image = False
        if generated_image_path is not None and generated_image_path.exists():
            try:
                with Image.open(generated_image_path) as src_img:
                    src_w, src_h = src_img.size
                    if src_w > 0 and src_h > 0:
                        # Aspect-ratio preserving cover with center crop
                        panel_w = usable_w
                        scale_factor = max(panel_w / src_w, visual_h / src_h)
                        new_w = max(1, int(src_w * scale_factor))
                        new_h = max(1, int(src_h * scale_factor))
                        resized = src_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                        left = (new_w - panel_w) // 2
                        top = (new_h - visual_h) // 2
                        cropped = resized.crop((left, top, left + panel_w, top + visual_h)).convert("RGB")

                        # Rounded mask matching card radius
                        radius = int(12 * scale)
                        mask = Image.new("L", (panel_w, visual_h), 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.rounded_rectangle((0, 0, panel_w, visual_h), radius=radius, fill=255)

                        canvas.image.paste(cropped, (pad_x, content_top), mask=mask)
                        composed_ai_image = True
            except Exception as e:
                logger.warning("Failed composing AI image into canvas, falling back to schematic diagram: %s", e)
                composed_ai_image = False

        if not composed_ai_image:
            canvas.draw_card(
                panel_box,
                fill=(20, 28, 44),
                outline=COLOR_PRIMARY if state_idx >= 1 else COLOR_CARD_BORDER,
                radius=12,
            )

            # Schematic educational circular diagram
            cx = pad_x + (usable_w // 2)
            cy = content_top + (visual_h // 2)
            r_outer = int(75 * scale)
            canvas.draw.ellipse(
                (cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer),
                fill=(26, 38, 62),
                outline=COLOR_PRIMARY,
                width=max(2, int(2 * scale)),
            )
            r_inner = int(45 * scale)
            canvas.draw.ellipse(
                (cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner),
                fill=(36, 52, 85),
                outline=COLOR_ACCENT,
                width=max(2, int(2 * scale)),
            )

            center_font = get_system_font(max(13, int(15 * scale)))
            canvas.draw.text(
                (cx - int(32 * scale), cy - int(9 * scale)),
                "DIAGRAM",
                font=center_font,
                fill=COLOR_TEXT_MAIN,
            )
        else:
            # Draw frame border over the composite image
            canvas.draw.rounded_rectangle(
                panel_box,
                outline=COLOR_PRIMARY if state_idx >= 1 else COLOR_CARD_BORDER,
                width=max(1, int(2 * scale)),
                radius=int(12 * scale),
            )

        # Bottom Fallback Card: Heading & Points (Shown in State 1+)
        card_y = content_top + visual_h + int(16 * scale)
        card_h = int(140 * scale)
        canvas.draw_card(
            (pad_x, card_y, pad_x + usable_w, card_y + card_h),
            fill=COLOR_CARD,
            outline=COLOR_HIGHLIGHT if state_idx >= 1 else COLOR_CARD_BORDER,
            radius=8,
        )

        head_font = get_system_font(max(14, int(18 * scale)))
        head_lines = fit_or_truncate_text(
            spec.fallback_heading,
            head_font,
            max_width_px=usable_w - int(32 * scale),
            max_lines=1,
            draw=canvas.draw,
            warnings=warnings,
        )
        if head_lines:
            canvas.draw.text((pad_x + int(16 * scale), card_y + int(14 * scale)), head_lines[0], font=head_font, fill=COLOR_HIGHLIGHT)

        # Points
        if state_idx >= 1 and spec.fallback_points:
            pt_font = get_system_font(max(12, int(14 * scale)))
            py = card_y + int(44 * scale)
            for pt in spec.fallback_points[:3]:
                circle_r = max(3, int(4 * scale))
                canvas.draw.ellipse(
                    (pad_x + int(16 * scale), py + int(5 * scale), pad_x + int(16 * scale) + circle_r * 2, py + int(5 * scale) + circle_r * 2),
                    fill=COLOR_ACCENT,
                )
                pt_lines = fit_or_truncate_text(
                    pt,
                    pt_font,
                    max_width_px=usable_w - int(48 * scale),
                    max_lines=1,
                    draw=canvas.draw,
                    warnings=warnings,
                )
                if pt_lines:
                    canvas.draw.text((pad_x + int(30 * scale), py), pt_lines[0], font=pt_font, fill=COLOR_TEXT_MAIN)
                    py += int(20 * scale)

        tmp_img = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        canvas.image.save(tmp_img.name)
        return Path(tmp_img.name)

    async def render(
        self,
        scene: ScenePlan,
        timing: ResolvedSceneTiming,
        output_path: Path,
    ) -> RenderResult:
        spec = cast(IllustrationSpec, scene.visual_spec)
        warnings: list[str] = []

        generated_image_path: Path | None = None
        if self.enable_image_generation and self.image_provider is not None:
            try:
                prompt = build_illustration_prompt(scene, spec)
                temp_gen_path = output_path.parent / f"{output_path.stem}_ai_gen_{uuid.uuid4().hex[:8]}.png"
                result = await self.image_provider.generate(
                    prompt=prompt,
                    output_path=temp_gen_path,
                )
                if Path(result.path).exists():
                    generated_image_path = Path(result.path)
            except Exception as exc:
                warnings.append("AI illustration unavailable; deterministic fallback used.")
                logger.warning(
                    "AI illustration generation failed for scene %s; using deterministic fallback: %s",
                    scene.scene_id,
                    getattr(exc, "code", type(exc).__name__),
                )
                generated_image_path = None

        num_logical_states = 2
        durations = allocate_state_durations(timing.render_duration_seconds, num_logical_states)
        actual_num_states = len(durations)
        state_indices = select_progressive_state_indices(num_logical_states, actual_num_states)

        state_paths: list[Path] = []
        try:
            for logical_idx in state_indices:
                state_p = await asyncio.to_thread(
                    self._render_state,
                    scene=scene,
                    spec=spec,
                    state_idx=logical_idx,
                    warnings=warnings,
                    generated_image_path=generated_image_path,
                )
                state_paths.append(state_p)

            await compile_states_to_video(
                image_paths=state_paths,
                durations=durations,
                total_duration=timing.render_duration_seconds,
                output_path=output_path,
                fps=self.fps,
            )
        finally:
            for p in state_paths:
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass
            if generated_image_path is not None and generated_image_path.exists():
                try:
                    generated_image_path.unlink(missing_ok=True)
                except Exception:
                    pass

        return RenderResult(
            path=str(output_path),
            width=self.width,
            height=self.height,
            duration_seconds=timing.render_duration_seconds,
            warnings=warnings,
        )
