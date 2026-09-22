"""Canvas creation, theme styling, and base graphical primitives for scene rendering."""

from PIL import Image, ImageDraw

from app.rendering.typography import fit_or_truncate_text, get_system_font

# Design theme constants: deep slate aesthetic with clean accent highlights
COLOR_BG = (15, 23, 42)          # Slate 900
COLOR_CARD = (30, 41, 59)        # Slate 800
COLOR_CARD_BORDER = (51, 65, 85) # Slate 700
COLOR_PRIMARY = (56, 189, 248)    # Sky 400
COLOR_SECONDARY = (129, 140, 248)# Indigo 400
COLOR_ACCENT = (52, 211, 153)    # Emerald 400
COLOR_TEXT_MAIN = (248, 250, 252)# Slate 50
COLOR_TEXT_MUTED = (148, 163, 184)# Slate 400
COLOR_HIGHLIGHT = (251, 191, 36) # Amber 400


class SceneCanvas:
    """A 16:9 drawing canvas with structured header, footer, and content area."""

    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height
        self.image = Image.new("RGB", (width, height), COLOR_BG)
        self.draw = ImageDraw.Draw(self.image)
        self.scale = height / 720.0  # Reference base height

    def draw_header(
        self,
        scene_id: str,
        title: str,
        step_num: int | None = None,
        warnings: list[str] | None = None,
    ) -> int:
        """Draw the standardized scene header with badge and title. Returns header bottom Y."""
        pad_x = int(48 * self.scale)
        top_y = int(32 * self.scale)

        badge_font = get_system_font(max(12, int(14 * self.scale)))
        title_font = get_system_font(max(18, int(28 * self.scale)))

        # 1. Badge (bounded)
        raw_badge = f"SCENE {step_num}" if step_num else scene_id.upper()
        max_badge_w = int(200 * self.scale)
        badge_lines = fit_or_truncate_text(
            raw_badge,
            badge_font,
            max_width_px=max_badge_w,
            max_lines=1,
            draw=self.draw,
            warnings=warnings,
        )
        badge_text = badge_lines[0] if badge_lines else raw_badge
        bbox = self.draw.textbbox((0, 0), badge_text, font=badge_font)
        bw = (bbox[2] - bbox[0]) + int(16 * self.scale)
        bh = (bbox[3] - bbox[1]) + int(8 * self.scale)
        badge_rect = (pad_x, top_y, pad_x + bw, top_y + bh)
        self.draw.rounded_rectangle(badge_rect, radius=int(4 * self.scale), fill=COLOR_CARD, outline=COLOR_PRIMARY)
        self.draw.text((pad_x + int(8 * self.scale), top_y + int(4 * self.scale)), badge_text, font=badge_font, fill=COLOR_PRIMARY)

        # 2. Title
        title_x = pad_x + bw + int(16 * self.scale)
        max_title_w = max(int(50 * self.scale), self.width - title_x - pad_x)
        title_lines = fit_or_truncate_text(
            title,
            title_font,
            max_width_px=max_title_w,
            max_lines=1,
            draw=self.draw,
            warnings=warnings,
        )
        if title_lines:
            self.draw.text((title_x, top_y + int(2 * self.scale)), title_lines[0], font=title_font, fill=COLOR_TEXT_MAIN)

        # 3. Subtle horizontal divider
        line_y = top_y + bh + int(20 * self.scale)
        self.draw.line([(pad_x, line_y), (self.width - pad_x, line_y)], fill=COLOR_CARD_BORDER, width=max(1, int(1 * self.scale)))

        return line_y + int(20 * self.scale)

    def draw_card(
        self,
        rect: tuple[int, int, int, int],
        fill: tuple[int, int, int] = COLOR_CARD,
        outline: tuple[int, int, int] = COLOR_CARD_BORDER,
        radius: int = 8,
    ) -> None:
        """Draw a rounded rectangular card container."""
        scaled_radius = max(2, int(radius * self.scale))
        self.draw.rounded_rectangle(rect, radius=scaled_radius, fill=fill, outline=outline, width=max(1, int(1 * self.scale)))
