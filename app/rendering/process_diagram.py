"""Renderer for VisualIntent.PROCESS_DIAGRAM scenes."""

import asyncio
from pathlib import Path
import tempfile
from typing import cast

from app.domain.lesson import ProcessDiagramSpec, ScenePlan
from app.domain.timeline import ResolvedSceneTiming
from app.rendering.base import RenderResult, SceneRenderer
from app.rendering.canvas import (
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


class ProcessDiagramRenderer(SceneRenderer):
    """Renders sequential processes, actor interactions, and multi-step workflows."""

    def __init__(self, width: int = 1280, height: int = 720, fps: int = 24):
        self.width = width
        self.height = height
        self.fps = fps

    def _render_state(
        self,
        scene: ScenePlan,
        spec: ProcessDiagramSpec,
        active_step_idx: int,
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
        usable_w = self.width - (2 * pad_x)

        # Optional Actor Bar if actors exist
        actor_map = {a.id: a.label for a in spec.actors}
        current_y = content_top

        num_steps = len(spec.steps)
        gap = int(20 * scale)
        arrow_w = int(24 * scale)
        total_gaps_w = (num_steps - 1) * (gap + arrow_w)
        step_w = max(int(100 * scale), (usable_w - total_gaps_w) // num_steps)
        card_h = int(280 * scale)
        card_y = current_y + int(24 * scale)

        step_font = get_system_font(max(12, int(14 * scale)))
        label_font = get_system_font(max(13, int(16 * scale)))
        desc_font = get_system_font(max(11, int(13 * scale)))

        for i, step in enumerate(spec.steps):
            x = pad_x + i * (step_w + gap + arrow_w)
            is_active = (i == active_step_idx or active_step_idx < 0 or active_step_idx >= num_steps)

            outline_col = COLOR_PRIMARY if is_active else COLOR_CARD_BORDER
            fill_col = (38, 52, 75) if is_active else COLOR_CARD
            canvas.draw_card(
                (x, card_y, x + step_w, card_y + card_h),
                fill=fill_col,
                outline=outline_col,
                radius=8,
            )

            # Step order pill (measured to content)
            order_text = f"#{step.order}"
            order_bbox = canvas.draw.textbbox((0, 0), order_text, font=step_font)
            order_w = (order_bbox[2] - order_bbox[0]) + int(14 * scale)
            pill_w = max(int(46 * scale), order_w)
            pill_h = int(22 * scale)
            pill_rect = (x + int(10 * scale), card_y + int(12 * scale), x + int(10 * scale) + pill_w, card_y + int(12 * scale) + pill_h)
            canvas.draw.rounded_rectangle(
                pill_rect,
                radius=int(4 * scale),
                fill=COLOR_PRIMARY if is_active else (20, 28, 42),
            )
            canvas.draw.text(
                (x + int(16 * scale), card_y + int(15 * scale)),
                order_text,
                font=step_font,
                fill=COLOR_TEXT_MAIN if is_active else COLOR_TEXT_MUTED,
            )

            # Actor flow: From -> To
            ly = card_y + int(42 * scale)
            if step.from_actor or step.to_actor:
                from_lbl = actor_map.get(step.from_actor or "", step.from_actor or "")
                to_lbl = actor_map.get(step.to_actor or "", step.to_actor or "")
                flow_text = f"{from_lbl} → {to_lbl}" if (from_lbl and to_lbl) else (from_lbl or to_lbl)
                flow_lines = fit_or_truncate_text(
                    flow_text,
                    step_font,
                    max_width_px=step_w - int(20 * scale),
                    max_lines=1,
                    draw=canvas.draw,
                    warnings=warnings,
                )
                if flow_lines:
                    canvas.draw.text((x + int(10 * scale), ly), flow_lines[0], font=step_font, fill=COLOR_SECONDARY)
                    ly += int(20 * scale)

            # Step Label
            label_lines = fit_or_truncate_text(
                step.label,
                label_font,
                max_width_px=step_w - int(20 * scale),
                max_lines=2,
                draw=canvas.draw,
                warnings=warnings,
            )
            for l in label_lines:
                canvas.draw.text(
                    (x + int(10 * scale), ly),
                    l,
                    font=label_font,
                    fill=COLOR_HIGHLIGHT if is_active else COLOR_TEXT_MAIN,
                )
                ly += int(20 * scale)

            # Step Description
            if step.description:
                desc_lines = fit_or_truncate_text(
                    step.description,
                    desc_font,
                    max_width_px=step_w - int(20 * scale),
                    max_lines=5,
                    draw=canvas.draw,
                    warnings=warnings,
                )
                dy = ly + int(8 * scale)
                for dl in desc_lines:
                    canvas.draw.text(
                        (x + int(10 * scale), dy),
                        dl,
                        font=desc_font,
                        fill=COLOR_TEXT_MAIN if is_active else COLOR_TEXT_MUTED,
                    )
                    dy += int(17 * scale)

            # Connecting arrow to next step
            if i < num_steps - 1:
                arrow_x = x + step_w + int(gap // 2)
                arrow_y = card_y + int(card_h // 2)
                arrow_len = arrow_w + int(gap // 2)
                canvas.draw.line(
                    [(arrow_x, arrow_y), (arrow_x + arrow_len - int(6 * scale), arrow_y)],
                    fill=COLOR_PRIMARY if is_active else COLOR_CARD_BORDER,
                    width=max(2, int(2 * scale)),
                )
                tip = (arrow_x + arrow_len, arrow_y)
                top = (arrow_x + arrow_len - int(8 * scale), arrow_y - int(6 * scale))
                bot = (arrow_x + arrow_len - int(8 * scale), arrow_y + int(6 * scale))
                canvas.draw.polygon([tip, top, bot], fill=COLOR_PRIMARY if is_active else COLOR_CARD_BORDER)

        tmp_img = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        canvas.image.save(tmp_img.name)
        return Path(tmp_img.name)

    async def render(
        self,
        scene: ScenePlan,
        timing: ResolvedSceneTiming,
        output_path: Path,
    ) -> RenderResult:
        spec = cast(ProcessDiagramSpec, scene.visual_spec)
        warnings: list[str] = []

        num_steps = len(spec.steps)
        durations = allocate_state_durations(timing.render_duration_seconds, num_steps)
        actual_num_states = len(durations)
        if actual_num_states == 1:
            state_indices = [-1]  # Illuminate all steps together
        else:
            state_indices = select_progressive_state_indices(num_steps, actual_num_states)

        state_paths: list[Path] = []
        for step_idx in state_indices:
            state_p = await asyncio.to_thread(
                self._render_state,
                scene=scene,
                spec=spec,
                active_step_idx=step_idx,
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
