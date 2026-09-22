"""Renderer for VisualIntent.CONCEPT_CARD scenes."""

import asyncio
from pathlib import Path
import tempfile
from typing import cast

from app.domain.lesson import ConceptCardSpec, ScenePlan
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


class ConceptCardRenderer(SceneRenderer):
    """Renders structured conceptual definitions, key bullet points, and emphasis badges."""

    def __init__(self, width: int = 1280, height: int = 720, fps: int = 24):
        self.width = width
        self.height = height
        self.fps = fps

    def _render_state(
        self,
        scene: ScenePlan,
        spec: ConceptCardSpec,
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
        usable_w = self.width - (2 * pad_x)

        # 1. Main Heading Card
        head_card_h = int(120 * scale)
        canvas.draw_card(
            (pad_x, content_top, pad_x + usable_w, content_top + head_card_h),
            fill=COLOR_CARD,
            outline=COLOR_PRIMARY if state_idx == 0 else COLOR_CARD_BORDER,
            radius=10,
        )

        term_font = get_system_font(max(18, int(26 * scale)))
        term_lines = fit_or_truncate_text(
            spec.heading,
            term_font,
            max_width_px=usable_w - int(48 * scale),
            max_lines=2,
            draw=canvas.draw,
            warnings=warnings,
        )
        line_y = content_top + int(24 * scale)
        for line in term_lines:
            canvas.draw.text((pad_x + int(24 * scale), line_y), line, font=term_font, fill=COLOR_PRIMARY)
            line_y += int(32 * scale)

        current_y = content_top + head_card_h + int(24 * scale)

        # 2. Key Points (Shown in State 1 and State 2)
        if state_idx >= 1 and spec.points:
            kp_title_font = get_system_font(max(13, int(16 * scale)))
            canvas.draw.text(
                (pad_x, current_y),
                "KEY CONCEPTS / NỘI DUNG CHÍNH:",
                font=kp_title_font,
                fill=COLOR_SECONDARY,
            )
            current_y += int(28 * scale)

            kp_font = get_system_font(max(13, int(16 * scale)))
            for kp in spec.points[:4]:
                circle_r = max(3, int(5 * scale))
                canvas.draw.ellipse(
                    (pad_x + int(8 * scale), current_y + int(6 * scale), pad_x + int(8 * scale) + circle_r * 2, current_y + int(6 * scale) + circle_r * 2),
                    fill=COLOR_ACCENT,
                )
                kp_lines = fit_or_truncate_text(
                    kp,
                    kp_font,
                    max_width_px=usable_w - int(48 * scale),
                    max_lines=2,
                    draw=canvas.draw,
                    warnings=warnings,
                )
                for line in kp_lines:
                    canvas.draw.text((pad_x + int(32 * scale), current_y), line, font=kp_font, fill=COLOR_TEXT_MAIN)
                    current_y += int(24 * scale)
                current_y += int(8 * scale)

        # 3. Emphasis Badges / Highlights (Shown in State 2 if present)
        if state_idx >= 2 and spec.emphasis:
            em_y = min(current_y + int(10 * scale), self.height - int(90 * scale))
            em_font = get_system_font(max(12, int(14 * scale)))
            bx = pad_x
            by = em_y
            row_count = 1

            for em in spec.emphasis:
                # Ensure individual badge text fits within usable width
                em_lines = fit_or_truncate_text(
                    em,
                    em_font,
                    max_width_px=usable_w - int(24 * scale),
                    max_lines=1,
                    draw=canvas.draw,
                    warnings=warnings,
                )
                em_text = em_lines[0] if em_lines else ""
                if not em_text:
                    continue

                bbox = canvas.draw.textbbox((0, 0), em_text, font=em_font)
                bw = (bbox[2] - bbox[0]) + int(24 * scale)
                bh = (bbox[3] - bbox[1]) + int(12 * scale)

                # Check if badge exceeds current row
                if bx + bw > pad_x + usable_w and bx > pad_x:
                    if row_count < 2 and (by + bh + int(8 * scale) + bh) <= self.height - int(12 * scale):
                        row_count += 1
                        bx = pad_x
                        by += bh + int(8 * scale)
                    else:
                        # Cannot fit more rows; truncate or skip remaining
                        if warnings is not None:
                            warnings.append(f"Emphasis badge '{em}' omitted due to canvas overflow")
                        continue

                # Final clamp against right canvas boundary
                if bx + bw > pad_x + usable_w:
                    bw = (pad_x + usable_w) - bx

                canvas.draw.rounded_rectangle(
                    (bx, by, bx + bw, by + bh),
                    radius=int(6 * scale),
                    fill=(30, 45, 65),
                    outline=COLOR_HIGHLIGHT,
                )
                canvas.draw.text((bx + int(12 * scale), by + int(6 * scale)), em_text, font=em_font, fill=COLOR_HIGHLIGHT)
                bx += bw + int(16 * scale)

        tmp_img = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        canvas.image.save(tmp_img.name)
        return Path(tmp_img.name)

    async def render(
        self,
        scene: ScenePlan,
        timing: ResolvedSceneTiming,
        output_path: Path,
    ) -> RenderResult:
        spec = cast(ConceptCardSpec, scene.visual_spec)
        warnings: list[str] = []

        num_logical_states = 1
        if spec.points:
            num_logical_states = 2
        if spec.emphasis:
            num_logical_states = 3

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
