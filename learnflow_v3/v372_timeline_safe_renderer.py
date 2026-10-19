"""V3-72 research-only native renderer: measured layout + bounded marker path.

This is a NEW source renderer for versioned correction candidates. The V3-57
originals and nine V3-59/V3-61 masked clips remain byte-for-byte frozen.
No post-hoc coverup on screenshot pixels; each frame is rendered from scene
geometry, approved source facts and unchanged narration beats.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from PIL import Image, ImageDraw

from learnflow_v3.pedagogical_storytelling_slice import (
    WIDTH, HEIGHT, FPS, BLACK, WHITE, SOFT, CYAN, AMBER, GREEN,
    Plan, plan, validate, facts, font, text
)

SAFE_CASES = ("attention_reversed_query", "process_heldout_unknown")
ACTION_RECT = (510, 283, 770, 393)
START_RECT = (100, 283, 360, 393)
PROCESS_MARKER_START = 380
PROCESS_MARKER_ENDPOINT = 488


class VisualCollision(ValueError):
    pass


@dataclass(frozen=True)
class Layout:
    score_a_y: int = 358
    score_b_y: int = 460
    score_a_label_y: int = 320
    score_b_label_y: int = 421
    score_bar_left: int = 355
    score_bar_width: int = 592
    score_bar_height: int = 41
    action_left: int = 510
    action_marker_endpoint_x: int = PROCESS_MARKER_ENDPOINT
    marker_radius: int = 13
    marker_stroke: int = 3
    geometry_clearance: int = 6


SAFE_LAYOUT = Layout()


def require(ok: bool, code: str) -> None:
    if not ok:
        raise VisualCollision("V372_" + code)


def overlap(a: tuple, b: tuple, clearance: int = 0) -> bool:
    """Rectangle intersection including a claimed exclusion clearance."""
    return (a[0] < b[2] + clearance and
            a[2] + clearance > b[0] and
            a[1] < b[3] + clearance and
            a[3] + clearance > b[1])


def text_bounds(msg: str, x: int, y: int, size: int = 24) -> tuple:
    canvas = Image.new("RGB", (1, 1))
    d = ImageDraw.Draw(canvas)
    return d.textbbox((x, y), msg, font=font(size))


def verified_progress(progress: float) -> float:
    require(isinstance(progress, (int, float)) and math.isfinite(progress) and
            0 <= progress <= 1, "NONFINITE_OR_OUT_OF_RANGE_TIME")
    return float(progress)


def frame_geometry(case_id: str, beat: int, progress: float,
                   geometry: Layout = SAFE_LAYOUT) -> dict:
    """Reject material collisions for ALL intermediate frames, not endpoints.

    Used by the actual renderer and by an independent full-timeline sweep.
    """
    t = verified_progress(progress)
    require(case_id in SAFE_CASES and 0 <= beat < 5, "CASE_OR_BEAT")
    require(geometry.geometry_clearance >= 6, "LOOSENED_CLEARANCE")
    if case_id == "attention_reversed_query":
        a = facts(case_id)
        label_a = text_bounds(f"score A = {a['scores'][0]:.3f}",
                              geometry.score_bar_left, geometry.score_a_label_y)
        label_b = text_bounds(f"score B = {a['scores'][1]:.3f}",
                              geometry.score_bar_left, geometry.score_b_label_y)
        xa, w, h = (geometry.score_bar_left, geometry.score_bar_width,
                    geometry.score_bar_height)
        bar_a = (xa, geometry.score_a_y, xa + w, geometry.score_a_y + h)
        bar_b = (xa, geometry.score_b_y, xa + w, geometry.score_b_y + h)
        for label in (label_a, label_b):
            for bar in (bar_a, bar_b):
                require(not overlap(label, bar, geometry.geometry_clearance),
                        "ATTENTION_SCORE_TEXT_BAR_COLLISION")
        require(not overlap(bar_a, bar_b, geometry.geometry_clearance),
                "ATTENTION_BARS_COLLIDE")
        require(bar_b[3] <= 506 and bar_a[1] >= 345 and
                label_a[1] > 314 and label_b[3] < bar_b[1],
                "ATTENTION_RESERVED_REGIONS")
        return {"score_labels": (label_a, label_b), "score_bars": (bar_a, bar_b),
                "beat": beat, "progress": t,
                "timeline_geometry": "CLEAR"}
    center_x = PROCESS_MARKER_START + (
        geometry.action_marker_endpoint_x - PROCESS_MARKER_START) * t
    radius_with_outline = geometry.marker_radius + geometry.marker_stroke
    require(geometry.action_left == ACTION_RECT[0],
            "ACTION_BOUNDARY_UNCERTIFIED")
    # Node interiors extend at x >= 510 for y=337. Marker and stroke must
    # remain wholly outside that boundary, with >= 6px air gap.
    require(center_x + radius_with_outline + geometry.geometry_clearance <=
            geometry.action_left, "PROCESS_MARKER_PENETRATES_ACTION")
    require(center_x - radius_with_outline >=
            START_RECT[2] + 4, "PROCESS_MARKER_PENETRATES_START")
    require(geometry.action_marker_endpoint_x > PROCESS_MARKER_START,
            "PROCESS_REVERSED_OR_ZERO_PATH")
    return {"center_x": center_x, "center_y": 337,
            "draw_radius": geometry.marker_radius,
            "rightmost_stroked_px": center_x + radius_with_outline,
            "action_left": geometry.action_left,
            "gap_px": geometry.action_left - center_x - radius_with_outline,
            "action_active": beat > 2 or (beat == 2 and t >= 1.0),
            "condition": "UNKNOWN_NOT_VERIFIED",
            "timeline_geometry": "CLEAR"}


def _base_chrome(p: Plan, idx: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    frame = Image.new("RGB", (WIDTH, HEIGHT), BLACK)
    d = ImageDraw.Draw(frame)
    title = {"attention_reversed_query": "Attention: relevance to context",
             "process_heldout_unknown": "Process: evidence before a verdict"}[p.case_id]
    text(d, (74, 48), "LEARNFLOW   /   EVIDENCE-BOUND TEACHING", 19, CYAN)
    text(d, (74, 92), title, 42)
    text(d, (1175, 57), f"{idx+1:02d} / 05", 23, SOFT, anchor="ra")
    d.line((74, 159, 1206, 159), fill=(61, 65, 77), width=2)
    words = p.beats[idx].narration.split()
    current = ""
    lines = []
    for word in words:
        following = (current + " " + word).strip()
        if d.textbbox((0, 0), following, font=font(23))[2] > 1120 and current:
            lines.append(current)
            current = word
        else:
            current = following
    if current:
        lines.append(current)
    require(len(lines) <= 2, "NARRATION_OVERFLOW")
    for k, line in enumerate(lines):
        text(d, (74, 592 + 31*k), line, 23)
    b = p.beats[idx]
    text(d, (74, 653),
         f"CLAIM {b.claim_id}  |  REF {b.referent_id}  |  {b.operation}", 17, SOFT)
    for j in range(5):
        x = 74 + j*232
        d.rounded_rectangle((x, 686, x+205, 693), radius=3,
                            fill=CYAN if j <= idx else (45, 49, 62))
    return frame, d


def render_safe_frame(p: Plan, idx: int, progress: float,
                      geometry: Layout = SAFE_LAYOUT) -> Image.Image:
    """Native scene construction from semantics; never image overlay patch."""
    validate(p)
    require(p.case_id in SAFE_CASES, "CASE_OR_BEAT")
    state = frame_geometry(p.case_id, idx, progress, geometry)
    t = state["progress"] if "progress" in state else verified_progress(progress)
    im, d = _base_chrome(p, idx)
    if p.case_id == "attention_reversed_query":
        ev = facts(p.case_id)
        for x, label, color in (
            (270, "QUERY [0,1]", CYAN),
            (635, "KEY A [1,0]", SOFT),
            (1000, "KEY B [0,1]", AMBER)
        ):
            d.rounded_rectangle((x-146, 235, x+146, 314), outline=color,
                                radius=12, width=3)
            text(d, (x, 273), label, 25, color, anchor="mm")
        if idx >= 1:
            d.line((416, 278, 488, 278), fill=SOFT, width=4)
            d.line((785, 278, 851, 278), fill=AMBER, width=4)
            score_rects = state["score_bars"]
            for j, title in enumerate(
                (f"score A = {ev['scores'][0]:.3f}",
                 f"score B = {ev['scores'][1]:.3f}")
            ):
                box = score_rects[j]
                y = geometry.score_a_label_y if j == 0 else geometry.score_b_label_y
                text(d, (geometry.score_bar_left, y), title, 24, SOFT)
                d.rounded_rectangle(box, radius=11, outline=(83, 92, 111), width=2)
                scale = 0.01 if j == 0 else (t if idx == 1 else 1)
                width = round(max(0, min(1, ev["scores"][j]*scale)) *
                              geometry.score_bar_width)
                if width >= 5:
                    d.rounded_rectangle((box[0]+2, box[1]+2,
                                         box[0]+width, box[3]-2),
                                        radius=9, fill=SOFT if j == 0 else AMBER)
        if idx >= 2:
            # Late reveal: source ledger weights appear after normalized cue,
            # preserving the V3-59 causal research honesty without overwriting it.
            if idx > 2 or t >= 1.0:
                text(d, (95, 370), f"w(A) = {ev['weights'][0]:.3f}", 21, CYAN)
                text(d, (95, 463), f"w(B) = {ev['weights'][1]:.3f}", 21, AMBER)
            else:
                text(d, (95, 370), "Normalize scores", 21, WHITE)
                text(d, (95, 463), "before weights", 21, SOFT)
            d.ellipse((976, 462, 1009, 495), fill=AMBER)
            if idx == 2:
                d.rounded_rectangle((355, 519, 900, 538), radius=7,
                                    outline=SOFT, width=2)
                if t:
                    d.rounded_rectangle((357, 521,
                                         357 + round(535*ev["weights"][1]*t), 536),
                                        radius=6, fill=GREEN)
                text(d, (377, 552),
                     "softmax: exp(score) / sum(exp(scores))", 19, GREEN)
        if idx == 3:
            d.line((355, 512, 355 + round(545*t), 512), fill=GREEN, width=7)
        if idx >= 3:
            text(d, (666, 552),
                 f"context = [{ev['context'][0]:.3f}, {ev['context'][1]:.3f}]",
                 28, GREEN, anchor="mm")
        if idx == 0:
            text(d, (640, 526), "Which value carries more information?",
                 25, AMBER, anchor="mm")
    else:
        nodes = (("START", 230), ("ACTION", 640), ("CHECK", 1050))
        # Connectors are behind nodes; the certified marker stays wholly on the
        # START->ACTION external edge, never at the text-bearing node interior.
        d.line((360, 337, 510, 337), fill=SOFT, width=5)
        d.line((770, 337, 920, 337), fill=SOFT, width=5)
        for j, (name, x) in enumerate(nodes):
            active_action = state["action_active"] if idx == 2 else idx >= 3
            color = (GREEN if j == 1 and active_action else
                     CYAN if j == 0 else
                     AMBER if j == 2 and idx >= 3 else (55, 67, 86))
            d.rounded_rectangle((x-130, 283, x+130, 393), radius=24, fill=color)
            text(d, (x, 338), name, 31, BLACK, anchor="mm")
        if idx == 2:
            cx = state["center_x"]
            d.line((PROCESS_MARKER_START, 337, round(cx), 337),
                   fill=AMBER, width=6)
            r = geometry.marker_radius
            d.ellipse((round(cx-r), 337-r, round(cx+r), 337+r),
                      fill=WHITE, outline=AMBER, width=geometry.marker_stroke)
        if idx == 3:
            d.arc((915-round(75*t), 255-round(50*t),
                   1185+round(75*t), 421+round(50*t)),
                  0, 360, fill=AMBER, width=6)
        if idx >= 3:
            text(d, (635, 482), "Outcome: UNKNOWN, not PASS or FAIL",
                 29, AMBER, anchor="mm")
        elif idx == 0:
            text(d, (635, 490), "What evidence would be needed at CHECK?",
                 26, AMBER, anchor="mm")
    return im


def verify_entire_timeline(case_id: str, boundaries: list[int],
                           geometry: Layout = SAFE_LAYOUT) -> dict:
    require(case_id in SAFE_CASES and len(boundaries) == 6 and
            boundaries[0] == 0 and
            all(isinstance(x, int) for x in boundaries) and
            all(b > a for a, b in zip(boundaries, boundaries[1:])),
            "TIMELINE_BOUNDARIES")
    checked = 0
    for idx in range(5):
        begin, stop = boundaries[idx], boundaries[idx+1]
        for frame_id in range(begin, stop):
            # The same progress function is used by render-native, not a
            # sparse sample. 1.0 is reached at 58% of a beat.
            j = frame_id - begin
            progress = min(1.0, j / max(1, int((stop-begin)*.58)))
            frame_geometry(case_id, idx, progress, geometry)
            checked += 1
    return {"case_id": case_id, "validated_frames": checked,
            "all_frames_no_overlap": True, "source": "HOST_ONLY"}
