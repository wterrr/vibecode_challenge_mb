"""Renderer for VisualIntent.COMPARISON scenes."""

import asyncio
from pathlib import Path
import tempfile
from typing import cast

from app.domain.lesson import ComparisonSpec, ScenePlan
from app.domain.timeline import ResolvedSceneTiming
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


class ComparisonRenderer(SceneRenderer):
    """Renders multi-column comparative analyses, trade-offs, and contrasts."""

    def __init__(self, width: int = 1280, height: int = 720, fps: int = 24):
        self.width = width
        self.height = height
        self.fps = fps

    def _render_state(
        self,
        scene: ScenePlan,
        spec: ComparisonSpec,
        state_idx: int,
        warnings: list[str],
    ) -> Path:
        canvas = SceneCanvas(self.width, self.height)
        scale = canvas.scale

        content_top = canvas.draw_header(
            scene_id=scene.scene_id,
            title=scene.title,
            warnings=warnings,
        )

        pad_x = int(48 * scale)
        gap = int(24 * scale)
        num_cols = len(spec.columns)
        col_w = (self.width - (2 * pad_x) - ((num_cols - 1) * gap)) // num_cols
        card_h = int(380 * scale)

        col_header_font = get_system_font(max(15, int(20 * scale)))
        sub_font = get_system_font(max(12, int(14 * scale)))
        point_font = get_system_font(max(13, int(15 * scale)))

        col_colors = [COLOR_PRIMARY, COLOR_HIGHLIGHT, COLOR_ACCENT]

        for i, col in enumerate(spec.columns):
            is_active = (state_idx == i or state_idx >= num_cols)
            col_x = pad_x + i * (col_w + gap)
            accent_col = col_colors[i % len(col_colors)]

            canvas.draw_card(
                (col_x, content_top, col_x + col_w, content_top + card_h),
                fill=(26, 36, 54) if is_active else COLOR_CARD,
                outline=accent_col if is_active else COLOR_CARD_BORDER,
                radius=10,
            )

            # Title (strictly bounded to column width)
            title_lines = fit_or_truncate_text(
                col.title,
                col_header_font,
                max_width_px=col_w - int(40 * scale),
                max_lines=1,
                draw=canvas.draw,
                warnings=warnings,
            )
            if title_lines:
                canvas.draw.text(
                    (col_x + int(20 * scale), content_top + int(16 * scale)),
                    title_lines[0],
                    font=col_header_font,
                    fill=accent_col,
                )

            # Subtitle if present
            cy = content_top + int(44 * scale)
            if col.subtitle:
                sub_lines = fit_or_truncate_text(
                    col.subtitle,
                    sub_font,
                    max_width_px=col_w - int(40 * scale),
                    max_lines=1,
                    draw=canvas.draw,
                    warnings=warnings,
                )
                if sub_lines:
                    canvas.draw.text((col_x + int(20 * scale), cy), sub_lines[0], font=sub_font, fill=COLOR_TEXT_MUTED)
                    cy += int(20 * scale)

            canvas.draw.line(
                [(col_x + int(20 * scale), cy + int(6 * scale)), (col_x + col_w - int(20 * scale), cy + int(6 * scale))],
                fill=COLOR_CARD_BORDER,
                width=1,
            )

            # Bullet points
            py = cy + int(20 * scale)
            for pt in col.points[:5]:
                circle_r = max(3, int(4 * scale))
                canvas.draw.ellipse(
                    (col_x + int(20 * scale), py + int(6 * scale), col_x + int(20 * scale) + circle_r * 2, py + int(6 * scale) + circle_r * 2),
                    fill=accent_col,
                )
                pt_lines = fit_or_truncate_text(
                    pt,
                    point_font,
                    max_width_px=col_w - int(52 * scale),
                    max_lines=2,
                    draw=canvas.draw,
                    warnings=warnings,
                )
                for line in pt_lines:
                    canvas.draw.text((col_x + int(36 * scale), py), line, font=point_font, fill=COLOR_TEXT_MAIN)
                    py += int(20 * scale)
                py += int(8 * scale)

        tmp_img = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        canvas.image.save(tmp_img.name)
        return Path(tmp_img.name)

    async def render(
        self,
        scene: ScenePlan,
        timing: ResolvedSceneTiming,
        output_path: Path,
    ) -> RenderResult:
        spec = cast(ComparisonSpec, scene.visual_spec)
        warnings: list[str] = []

        num_logical_states = len(spec.columns) + 1  # Col 1 -> Col 2 -> ... -> All columns
        durations = allocate_state_durations(timing.render_duration_seconds, num_logical_states)
        actual_num_states = len(durations)
        state_indices = select_progressive_state_indices(num_logical_states, actual_num_states)

        state_paths: list[Path] = []
        for logical_idx in state_indices:
            state_p = await asyncio.to_thread(
                self._render_state,
                scene=scene,
                spec=spec,
                state_idx=logical_idx,
                warnings=warnings,
            )
            state_paths.append(state_p)

        try:
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

        return RenderResult(
            path=str(output_path),
            width=self.width,
            height=self.height,
            duration_seconds=timing.render_duration_seconds,
            warnings=warnings,
        )
