"""V3-73: bounded, renderer-agnostic temporal *geometry contract* and native QA.

Research-only. Unlike V2 static collision detection or V3-72's two named
topics, no semantic topic identifiers, scene-specific coordinates, or rendering
technology are baked into the validator. Renderers must export COMPLETE
per-frame geometry; an omitted/misdeclared object cannot be detected from MP4
pixels and MUST NOT earn an unconditional claim of visual integrity.

Uses the V2 collision convention (positive rectangle intersection), and
reuses V3-72's verified overlap predicate without editing V2 Core.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Sequence

from PIL import Image, ImageDraw

from learnflow_v3.pedagogical_storytelling_slice import font
from learnflow_v3.v372_timeline_safe_renderer import overlap

WIDTH, HEIGHT, FPS = 1280, 720, 15
MIN_CLEARANCE = 6
MAX_STEP = 24.0
BACKGROUND = (10, 13, 21)


class VisualQAError(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise VisualQAError("V373_" + reason)


@dataclass(frozen=True)
class Rect:
    left: float
    top: float
    right: float
    bottom: float

    def tuple(self) -> tuple[float, ...]:
        return (self.left, self.top, self.right, self.bottom)

    def check(self) -> None:
        require(all(type(z) in (int, float) and math.isfinite(z)
                    for z in self.tuple()), "NONFINITE_RECT")
        require(self.left < self.right and self.top < self.bottom,
                "INVALID_RECT")
        require(self.left >= 0 and self.top >= 0 and
                self.right <= WIDTH and self.bottom <= HEIGHT,
                "OBJECT_OFF_CANVAS")


@dataclass(frozen=True)
class Object:
    object_id: str
    kind: str     # box | text | marker
    rect: Rect
    text: str = ""
    at: tuple[int, int] = (0, 0)
    fontsize: int = 24
    parent_id: str = ""
    movable: bool = False
    radius: float = 0.0   # circle radius INCLUDING outline
    edge_id: str = ""
    fill: str = "#26344a"


@dataclass(frozen=True)
class Edge:
    edge_id: str
    source_id: str
    target_id: str
    y: float
    color: str = "#9daebf"


@dataclass(frozen=True)
class Frame:
    index: int
    objects: tuple[Object, ...]
    edges: tuple[Edge, ...] = ()


def text_rect(value: str, at: tuple[int, int], fontsize: int) -> Rect:
    canvas = Image.new("RGB", (1, 1))
    b = ImageDraw.Draw(canvas).textbbox(at, value, font=font(fontsize))
    return Rect(*b)


def make_text(object_id: str, message: str, x: int, y: int,
              *, fontsize: int = 24, parent_id: str = "",
              fill: str = "#e4e9f0") -> Object:
    require(bool(message) and fontsize >= 14 and fontsize <= 64,
            "TEXT_UNMEASURED_OR_UNREADABLE")
    return Object(object_id, "text", text_rect(message, (x, y), fontsize),
                  text=message, at=(x, y), fontsize=fontsize,
                  parent_id=parent_id, fill=fill)


def marker(object_id: str, center_x: float, center_y: float,
           edge_id: str, radius: float = 12, color: str = "#ffffff") -> Object:
    require(type(radius) in (int, float) and math.isfinite(radius) and
            radius >= 5, "MARKER_RADIUS")
    return Object(object_id, "marker",
                  Rect(center_x-radius, center_y-radius,
                       center_x+radius, center_y+radius),
                  movable=True, radius=radius, edge_id=edge_id, fill=color)


def _inside(inner: Rect, outer: Rect, pad: float) -> bool:
    return (inner.left >= outer.left + pad and
            inner.right <= outer.right - pad and
            inner.top >= outer.top + pad and
            inner.bottom <= outer.bottom - pad)


def validate_frame(frame: Frame, *, clearance: int = MIN_CLEARANCE) -> dict:
    require(type(frame.index) is int and frame.index >= 0, "FRAME_INDEX")
    require(type(clearance) is int and clearance >= MIN_CLEARANCE,
            "MINIMUM_CLEARANCE")
    objs = frame.objects
    require(len(objs) >= 3 and len(objs) <= 40, "INCOMPLETE_GEOMETRY")
    names = [x.object_id for x in objs]
    require(all(isinstance(n, str) and len(n) >= 2 for n in names) and
            len(names) == len(set(names)), "OBJECT_IDENTITY")
    lookup = {x.object_id: x for x in objs}
    for obj in objs:
        require(obj.kind in ("box", "text", "marker"), "UNKNOWN_SHAPE_KIND")
        obj.rect.check()
        if obj.kind == "text":
            require(obj.text and type(obj.fontsize) is int and
                    14 <= obj.fontsize <= 64 and
                    text_rect(obj.text, obj.at, obj.fontsize) == obj.rect,
                    "UNMEASURED_TEXT_BBOX")
        if obj.kind == "marker":
            require(obj.movable and obj.edge_id and
                    obj.radius >= 5 and obj.radius <= 40 and
                    abs(obj.rect.right-obj.rect.left-2*obj.radius) < 1e-6 and
                    abs(obj.rect.bottom-obj.rect.top-2*obj.radius) < 1e-6,
                    "UNCERTIFIED_MOVING_MARKER")
        if obj.parent_id:
            parent = lookup.get(obj.parent_id)
            require(parent is not None and parent.kind == "box" and
                    obj.kind == "text" and
                    _inside(obj.rect, parent.rect, clearance),
                    "IMPROPER_PARENT_CONTAINMENT")
        elif obj.kind == "text":
            require(obj.rect.left >= 12 and obj.rect.right <= WIDTH-12,
                    "CHROME_MARGIN")
    seen = set()
    for edge in frame.edges:
        require(edge.edge_id not in seen and len(edge.edge_id) >= 2,
                "DUPLICATE_EDGE")
        seen.add(edge.edge_id)
        src = lookup.get(edge.source_id)
        dst = lookup.get(edge.target_id)
        require(src is not None and dst is not None and
                src.kind == dst.kind == "box" and
                src.rect.right < dst.rect.left and
                type(edge.y) in (int, float) and math.isfinite(edge.y) and
                src.rect.top + clearance <= edge.y <= src.rect.bottom - clearance and
                dst.rect.top + clearance <= edge.y <= dst.rect.bottom - clearance,
                "EDGE_TOPOLOGY_OR_BOUNDARY")
    edge_lookup = {e.edge_id: e for e in frame.edges}
    # Prioritize the specific temporal boundary gate before broad box
    # collision errors regardless of which object was inserted first in IR.
    for obj in objs:
        if obj.kind == "marker":
            edge = edge_lookup.get(obj.edge_id)
            require(edge is not None, "ORPHAN_MARKER")
            src = lookup[edge.source_id].rect
            dst = lookup[edge.target_id].rect
            require(obj.rect.left >= src.right + clearance and
                    obj.rect.right <= dst.left - clearance and
                    obj.rect.top <= edge.y <= obj.rect.bottom,
                    "MARKER_PENETRATES_NODE")
    for i, obj in enumerate(objs):
        for other in objs[i+1:]:
            if not overlap(obj.rect.tuple(), other.rect.tuple(), clearance):
                continue
            # Explicit and narrow text-inside-box only; never let a text
            # label overlap any other box, node or unrelated element.
            if obj.parent_id == other.object_id and obj.kind == "text":
                continue
            if other.parent_id == obj.object_id and other.kind == "text":
                continue
            raise VisualQAError(
                "V373_VISUAL_COLLISION:" + obj.object_id + ":" + other.object_id)
    return {"frame": frame.index, "objects_checked": len(objs),
            "visual_gate": "PASS_FULL_DECLARED_GEOMETRY"}


def validate_timeline(frames: Sequence[Frame],
                      *, expected_frames: int, fps: int = FPS) -> dict:
    require(type(expected_frames) is int and expected_frames > 0 and
            fps == FPS and len(frames) == expected_frames,
            "TIMELINE_INCOMPLETE")
    prior: dict[str, Object] | None = None
    prior_edges: tuple[Edge, ...] | None = None
    names: set[str] | None = None
    max_step = 0.0
    for frame_no, current in enumerate(frames):
        require(current.index == frame_no, "TIMELINE_GAP_OR_REORDER")
        validate_frame(current)
        byid = {o.object_id: o for o in current.objects}
        if prior is not None:
            require(set(byid) == names and current.edges == prior_edges,
                    "SEMANTIC_IDENTITY_OR_EDGE_DRIFT")
            for object_id, obj in byid.items():
                was = prior[object_id]
                require((obj.kind, obj.text, obj.parent_id, obj.edge_id,
                         obj.radius, obj.fontsize, obj.movable) ==
                        (was.kind, was.text, was.parent_id, was.edge_id,
                         was.radius, was.fontsize, was.movable),
                        "SEMANTIC_OBJECT_DRIFT")
                if not obj.movable:
                    require(obj.rect == was.rect, "STATIC_OBJECT_JUMP")
                else:
                    dx = ((obj.rect.left+obj.rect.right) -
                          (was.rect.left+was.rect.right))/2
                    dy = ((obj.rect.top+obj.rect.bottom) -
                          (was.rect.top+was.rect.bottom))/2
                    distance = math.hypot(dx, dy)
                    require(distance <= MAX_STEP+1e-7, "MARKER_TELEPORT")
                    require(dx >= -1e-7, "MARKER_REVERSED_DIRECTION")
                    max_step = max(max_step, distance)
        else:
            names = set(byid)
        prior, prior_edges = byid, current.edges
    return {"checked_frames": expected_frames,
            "max_observed_step_px": round(max_step, 4),
            "geometry": "PASS", "continuity": "PASS",
            "uncertified_pixels": "NOT_CLAIMED",
            "learning_effect": "NOT_MEASURED"}


def render_frame(frame: Frame) -> Image.Image:
    """Draw the SAME validated immutable IR; no separate uninspected overlay."""
    validate_frame(frame)
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    d = ImageDraw.Draw(image)
    objs = {o.object_id: o for o in frame.objects}
    for edge in frame.edges:
        a = objs[edge.source_id].rect
        b = objs[edge.target_id].rect
        d.line((a.right, edge.y, b.left, edge.y), fill=edge.color, width=5)
    # Intentional containment exception: draw node first then its text.
    for obj in frame.objects:
        b = obj.rect
        if obj.kind == "box":
            d.rounded_rectangle(b.tuple(), radius=18, fill=obj.fill,
                                outline="#9aafc2", width=2)
    for obj in frame.objects:
        if obj.kind == "marker":
            d.ellipse(obj.rect.tuple(), fill=obj.fill,
                      outline="#f0ae46", width=2)
        if obj.kind == "text":
            d.text(obj.at, obj.text, font=font(obj.fontsize), fill=obj.fill)
    return image
