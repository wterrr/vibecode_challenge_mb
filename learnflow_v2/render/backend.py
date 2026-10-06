"""Deterministic Pillow + FFmpeg backend for LearnFlow V2.

The backend consumes solved geometry and compiled renderer-neutral motion. It never
accepts arbitrary drawing code or LLM-provided pixel commands.
"""

from __future__ import annotations

import hashlib
import io
import math
from pathlib import Path
import subprocess
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.layout.schema import LayoutGraph, Rect, RoutedEdge
from learnflow_v2.motion.compiler import CompiledMotionArtifact, PropertyTrack, PropertyTrackKind
from learnflow_v2.motion.enums import MotionTargetKind
from learnflow_v2.render.errors import RenderBackendError, RenderInvalidInputError
from learnflow_v2.render.schema import RenderArtifactKind, RenderProfile, RenderedArtifact
from learnflow_v2.scenegraph.schema import SceneGraph, SceneNode
from learnflow_v2.transitions.schema import InterSceneTransitionPlan, TransitionOperation


_BG = (15, 17, 22)
_EDGE = (119, 133, 158)
_TEXT = (241, 245, 249)
DEFAULT_TEXT_FONT_SIZE_PX = 18
_TEXT_PADDING_X = 10
_TEXT_PADDING_Y = 8
_KIND_COLORS = {
    "TEXT": (39, 46, 60),
    "MATH": (35, 60, 78),
    "CONCEPT": (32, 67, 105),
    "SHAPE": (55, 65, 81),
    "IMAGE": (67, 57, 85),
    "ICON": (66, 61, 45),
    "CHART": (42, 78, 65),
    "CODE": (41, 48, 63),
    "GROUP": (53, 55, 70),
    "CONTAINER": (45, 52, 64),
    "CALLOUT": (91, 67, 38),
    "EQUATION": (40, 65, 83),
}


def _source_hash(*objects: object) -> str:
    parts: list[str] = []
    for obj in objects:
        if obj is None:
            parts.append("null")
        elif hasattr(obj, "to_canonical_json"):
            parts.append(obj.to_canonical_json())  # type: ignore[union-attr]
        else:
            parts.append(canonical_json(obj))
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _font(size: int) -> ImageFont.ImageFont:
    size = max(10, int(size))
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def _ease(name: str, t: float) -> float:
    t = min(1.0, max(0.0, t))
    if name == "ease_in":
        return t * t
    if name == "ease_out":
        return 1.0 - (1.0 - t) * (1.0 - t)
    if name == "ease_in_out":
        return 2.0 * t * t if t < 0.5 else 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0
    return t


def _sample_track(track: PropertyTrack, time_s: float) -> float:
    keyframes = track.keyframes
    if time_s <= keyframes[0].time:
        return keyframes[0].value
    if time_s >= keyframes[-1].time:
        return keyframes[-1].value
    for left, right in zip(keyframes, keyframes[1:]):
        if left.time <= time_s <= right.time:
            span = max(right.time - left.time, 1e-9)
            alpha = _ease(right.easing, (time_s - left.time) / span)
            return left.value + (right.value - left.value) * alpha
    return keyframes[-1].value


def _property_at(
    tracks: tuple[PropertyTrack, ...],
    target: str,
    target_kind: MotionTargetKind,
    property_kind: PropertyTrackKind,
    time_s: float,
    default: float,
) -> tuple[float, PropertyTrack | None]:
    candidates = [
        tr for tr in tracks
        if tr.target == target and tr.target_kind == target_kind and tr.property_kind == property_kind
    ]
    if not candidates:
        return default, None
    candidates.sort(key=lambda tr: (tr.start_time, tr.track_id))
    started = [tr for tr in candidates if tr.start_time <= time_s + 1e-9]
    track = started[-1] if started else candidates[0]
    return _sample_track(track, time_s), track


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = current + " " + word
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _node_text(node: SceneNode) -> str:
    # Must match LayoutRouter measurement semantics exactly: content wins over label.
    return node.content or node.label or node.semantic_role or node.kind.value


def _layout_text_in_rect(draw: ImageDraw.ImageDraw, text: str, rect: Rect):
    font_size = DEFAULT_TEXT_FONT_SIZE_PX
    font = _font(font_size)
    inner_width = max(1, int(round(rect.width)) - _TEXT_PADDING_X * 2)
    inner_height = max(1, int(round(rect.height)) - _TEXT_PADDING_Y * 2)
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        if paragraph.strip():
            lines.extend(_wrap_text(draw, paragraph, font, inner_width))
        else:
            lines.append("")
    ascent, descent = font.getmetrics() if hasattr(font, "getmetrics") else (font_size, 0)
    line_h = max(ascent + descent, int(round(font_size * 1.25)))
    widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        widths.append(max(0, bbox[2] - bbox[0]))
    text_width = max(widths, default=0)
    text_height = line_h * len(lines)
    fits = text_width <= inner_width and text_height <= inner_height
    return font, tuple(lines), line_h, text_width, text_height, inner_width, inner_height, fits


def _rect_tuple(rect: Rect) -> tuple[int, int, int, int]:
    return (
        int(round(rect.x)),
        int(round(rect.y)),
        int(round(rect.x + rect.width)),
        int(round(rect.y + rect.height)),
    )


def _interpolate_rect(a: Rect, b: Rect, t: float) -> Rect:
    return Rect(
        x=a.x + (b.x - a.x) * t,
        y=a.y + (b.y - a.y) * t,
        width=a.width + (b.width - a.width) * t,
        height=a.height + (b.height - a.height) * t,
    )


def _draw_partial_polyline(draw: ImageDraw.ImageDraw, edge: RoutedEdge, progress: float, *, fill: tuple[int, int, int], width: int = 3) -> None:
    progress = min(1.0, max(0.0, progress))
    points = [(p.x, p.y) for p in edge.points]
    lengths: list[float] = []
    total = 0.0
    for a, b in zip(points, points[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        lengths.append(length)
        total += length
    if total <= 1e-9 or progress <= 0.0:
        return
    remaining = total * progress
    rendered: list[tuple[float, float]] = [points[0]]
    for index, length in enumerate(lengths):
        a, b = points[index], points[index + 1]
        if remaining >= length:
            rendered.append(b)
            remaining -= length
            continue
        ratio = remaining / max(length, 1e-9)
        rendered.append((a[0] + (b[0] - a[0]) * ratio, a[1] + (b[1] - a[1]) * ratio))
        break
    if len(rendered) >= 2:
        draw.line(rendered, fill=fill, width=width, joint="curve")


class DeterministicPillowRenderer:
    """Deterministic renderer from typed V2 artifacts to RGB frames."""

    def validate_scene_inputs(
        self,
        scene_graph: SceneGraph,
        layout_graph: LayoutGraph,
        motion: CompiledMotionArtifact | None,
    ) -> tuple[SceneGraph, LayoutGraph, CompiledMotionArtifact | None]:
        scene_graph = SceneGraph.model_validate(scene_graph.model_dump(mode="json"))
        layout_graph = LayoutGraph.model_validate(layout_graph.model_dump(mode="json"))
        if scene_graph.scene_id != layout_graph.scene_id:
            raise RenderInvalidInputError("SceneGraph and LayoutGraph scene_id must match")
        if motion is not None:
            motion = CompiledMotionArtifact.model_validate_json(motion.to_canonical_json())
            if motion.scene_id != scene_graph.scene_id:
                raise RenderInvalidInputError("CompiledMotionArtifact scene_id must match scene")
        if not layout_graph.feasible:
            raise RenderInvalidInputError("renderer refuses infeasible LayoutGraph")
        node_ids = {node.id for node in scene_graph.nodes}
        box_ids = {box.node_id for box in layout_graph.boxes}
        if node_ids != box_ids:
            raise RenderInvalidInputError(
                f"LayoutGraph must exactly cover SceneGraph nodes; missing={sorted(node_ids-box_ids)}, extra={sorted(box_ids-node_ids)}"
            )
        relation_map = {rel.id: rel for rel in scene_graph.relations}
        relation_ids = set(relation_map)
        routed_edge_ids = {edge.edge_id for edge in layout_graph.routed_edges}
        for edge in layout_graph.routed_edges:
            relation = relation_map.get(edge.edge_id)
            if relation is None:
                raise RenderInvalidInputError(
                    f"routed edge '{edge.edge_id}' has no matching semantic relation"
                )
            if edge.source != relation.source or edge.target != relation.target:
                raise RenderInvalidInputError(
                    f"routed edge '{edge.edge_id}' endpoints contradict semantic relation"
                )
        if motion is not None:
            for track in motion.tracks:
                if track.target_kind == MotionTargetKind.NODE and track.target not in node_ids:
                    raise RenderInvalidInputError(f"motion track '{track.track_id}' references unknown node")
                if track.target_kind == MotionTargetKind.RELATION:
                    if track.target not in relation_ids:
                        raise RenderInvalidInputError(f"motion track '{track.track_id}' references unknown relation")
                    if track.target not in routed_edge_ids:
                        raise RenderInvalidInputError(
                            f"motion track '{track.track_id}' targets relation '{track.target}' without routed edge geometry"
                        )
        return scene_graph, layout_graph, motion

    def render_frame(
        self,
        scene_graph: SceneGraph,
        layout_graph: LayoutGraph,
        motion: CompiledMotionArtifact | None,
        time_s: float,
        *,
        hidden_node_ids: frozenset[str] = frozenset(),
    ) -> Image.Image:
        if not isinstance(hidden_node_ids, frozenset):
            raise RenderInvalidInputError("hidden_node_ids must be a frozenset")
        scene_graph, layout_graph, motion = self.validate_scene_inputs(scene_graph, layout_graph, motion)
        node_ids = {node.id for node in scene_graph.nodes}
        unknown_hidden = set(hidden_node_ids) - node_ids
        if unknown_hidden:
            raise RenderInvalidInputError(f"hidden_node_ids contains unknown nodes {sorted(unknown_hidden)}")
        duration = motion.scene_duration if motion is not None else max(0.0, time_s)
        if not math.isfinite(time_s) or time_s < 0.0 or (motion is not None and time_s > duration + 1e-6):
            raise RenderInvalidInputError("frame timestamp outside scene duration")
        width, height = int(round(layout_graph.frame_width)), int(round(layout_graph.frame_height))
        image = Image.new("RGB", (width, height), _BG)
        node_map = {node.id: node for node in scene_graph.nodes}
        tracks = motion.tracks if motion is not None else tuple()

        # Relations first so nodes sit above them.
        for edge in layout_graph.routed_edges:
            progress, _ = _property_at(
                tracks, edge.edge_id, MotionTargetKind.RELATION, PropertyTrackKind.EDGE_DRAW_PROGRESS, time_s, 1.0
            )
            _draw_partial_polyline(ImageDraw.Draw(image), edge, progress, fill=_EDGE)
            pulse, _ = _property_at(
                tracks, edge.edge_id, MotionTargetKind.RELATION, PropertyTrackKind.PROPAGATION_PROGRESS, time_s, 0.0
            )
            if pulse > 0.0 and len(edge.points) >= 2:
                a, b = edge.points[0], edge.points[-1]
                px = a.x + (b.x - a.x) * pulse
                py = a.y + (b.y - a.y) * pulse
                d = ImageDraw.Draw(image)
                d.ellipse((px-6, py-6, px+6, py+6), fill=(90, 200, 250))

        for box in layout_graph.boxes:
            if box.node_id in hidden_node_ids:
                continue
            node = node_map[box.node_id]
            opacity, _ = _property_at(
                tracks, box.node_id, MotionTargetKind.NODE, PropertyTrackKind.OPACITY, time_s, 1.0
            )
            reveal, _ = _property_at(
                tracks, box.node_id, MotionTargetKind.NODE, PropertyTrackKind.REVEAL_PROGRESS, time_s, 1.0
            )
            emphasis, _ = _property_at(
                tracks, box.node_id, MotionTargetKind.NODE, PropertyTrackKind.EMPHASIS_INTENSITY, time_s, 0.0
            )
            translation, translation_track = _property_at(
                tracks, box.node_id, MotionTargetKind.NODE, PropertyTrackKind.TRANSLATION_PROGRESS, time_s, 1.0
            )
            rect = box.rect
            dx = dy = 0.0
            if translation_track is not None:
                metadata = dict(translation_track.metadata)
                if metadata.get("direction") == "up":
                    dy = (1.0 - translation) * max(12.0, min(height * 0.06, rect.height * 0.35))
                elif metadata.get("direction") == "down":
                    dy = -(1.0 - translation) * max(12.0, min(height * 0.06, rect.height * 0.35))
                else:
                    # Scene-local MOVE is a renderer policy: deterministic offset -> solved resting geometry.
                    dx = -(1.0 - translation) * max(16.0, min(width * 0.04, rect.width * 0.30))
            moved = Rect(x=max(0.0, rect.x + dx), y=max(0.0, rect.y + dy), width=rect.width, height=rect.height)
            self._draw_node(image, node, moved, opacity=opacity, reveal=reveal, emphasis=emphasis)
        return image

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
        layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        x0, y0, x1, y1 = _rect_tuple(rect)
        x1 = max(x0 + 1, int(round(x0 + (x1 - x0) * reveal)))
        alpha = int(round(opacity * 255))
        base = _KIND_COLORS.get(node.kind.value, (48, 55, 70))
        fill = tuple(min(255, int(c + emphasis * 26)) for c in base) + (alpha,)
        outline = (90, 200, 250, alpha) if emphasis > 0.05 else (102, 116, 139, alpha)
        border = 2 + int(round(emphasis * 4))
        radius = max(4, min(18, int(min(rect.width, rect.height) * 0.08)))
        draw.rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=fill, outline=outline, width=border)
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
                draw.text((tx, ty), line, font=font, fill=_TEXT + (alpha,))
                ty += line_h
        mask = layer.getchannel("A")
        if reveal < 0.999:
            reveal_x = max(x0, min(int(round(rect.x + rect.width * reveal)), int(round(rect.x + rect.width))))
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rectangle((reveal_x, y0, int(round(rect.x + rect.width)), int(round(rect.y + rect.height))), fill=0)
        image.paste(layer.convert("RGB"), mask=mask)


def _encode_frames(
    frames: Iterable[Image.Image],
    *,
    output_path: Path,
    width: int,
    height: int,
    fps: int,
    crf: int,
    preset: str,
) -> tuple[int, str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(fps),
        "-i", "-", "-an", "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-map_metadata", "-1", str(output_path),
    ]
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        raise RenderBackendError(f"failed to start ffmpeg: {exc}") from exc
    digest = hashlib.sha256()
    count = 0
    assert proc.stdin is not None
    try:
        for frame in frames:
            rgb = frame.convert("RGB")
            if rgb.size != (width, height):
                raise RenderBackendError("renderer produced inconsistent frame dimensions")
            payload = rgb.tobytes()
            digest.update(payload)
            proc.stdin.write(payload)
            count += 1
        proc.stdin.close()
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr is not None else ""
        return_code = proc.wait()
    except Exception:
        proc.kill()
        raise
    if return_code != 0:
        raise RenderBackendError(f"ffmpeg encoding failed: {stderr[-1000:]}")
    if count <= 0 or not output_path.exists() or output_path.stat().st_size <= 0:
        raise RenderBackendError("ffmpeg produced no valid output")
    return count, digest.hexdigest()


def render_scene_video(
    scene_graph: SceneGraph,
    layout_graph: LayoutGraph,
    motion: CompiledMotionArtifact,
    output_path: str | Path,
    *,
    profile: RenderProfile = RenderProfile(profile_id="default"),
    renderer: DeterministicPillowRenderer | None = None,
) -> RenderedArtifact:
    renderer = renderer or DeterministicPillowRenderer()
    profile = RenderProfile.model_validate(profile.model_dump(mode="json"))
    scene_graph, layout_graph, validated_motion = renderer.validate_scene_inputs(scene_graph, layout_graph, motion)
    if validated_motion is None:
        raise RenderInvalidInputError("scene video rendering requires compiled motion artifact")
    motion = validated_motion
    width, height = int(round(layout_graph.frame_width)), int(round(layout_graph.frame_height))
    frame_count = max(1, int(round(motion.scene_duration * profile.fps)))
    rendered_duration = frame_count / profile.fps

    def frames() -> Iterable[Image.Image]:
        for index in range(frame_count):
            yield renderer.render_frame(scene_graph, layout_graph, motion, min(index / profile.fps, motion.scene_duration))

    count, digest = _encode_frames(
        frames(), output_path=Path(output_path), width=width, height=height,
        fps=profile.fps, crf=profile.crf, preset=profile.preset,
    )
    return RenderedArtifact(
        artifact_id=f"scene:{scene_graph.scene_id}",
        kind=RenderArtifactKind.SCENE,
        path=str(Path(output_path)),
        duration=rendered_duration,
        width=width, height=height, fps=profile.fps, frame_count=count,
        frame_digest=digest,
        source_hash=_source_hash(scene_graph, layout_graph, motion, profile),
    )


def render_transition_video(
    source_scene: SceneGraph,
    source_layout: LayoutGraph,
    target_scene: SceneGraph,
    target_layout: LayoutGraph,
    plan: InterSceneTransitionPlan,
    output_path: str | Path,
    *,
    profile: RenderProfile = RenderProfile(profile_id="default"),
    renderer: DeterministicPillowRenderer | None = None,
) -> RenderedArtifact:
    renderer = renderer or DeterministicPillowRenderer()
    profile = RenderProfile.model_validate(profile.model_dump(mode="json"))
    source_scene, source_layout, _ = renderer.validate_scene_inputs(source_scene, source_layout, None)
    target_scene, target_layout, _ = renderer.validate_scene_inputs(target_scene, target_layout, None)
    plan = InterSceneTransitionPlan.from_canonical_json(plan.to_canonical_json())
    if plan.from_scene != source_scene.scene_id or plan.to_scene != target_scene.scene_id:
        raise RenderInvalidInputError("transition plan endpoints do not match supplied scenes")
    sw, sh = int(round(source_layout.frame_width)), int(round(source_layout.frame_height))
    tw, th = int(round(target_layout.frame_width)), int(round(target_layout.frame_height))
    if (sw, sh) != (tw, th):
        raise RenderInvalidInputError("baseline transition renderer requires equal output frame dimensions")

    source_nodes = {node.id: node for node in source_scene.nodes}
    target_nodes = {node.id: node for node in target_scene.nodes}
    source_boxes = {box.node_id: box for box in source_layout.boxes}
    target_boxes = {box.node_id: box for box in target_layout.boxes}
    for item in plan.persistent_objects:
        if item.from_node_id not in source_nodes or item.from_node_id not in source_boxes:
            raise RenderInvalidInputError(
                f"persistent transition '{item.transition_item_id}' references unknown source node '{item.from_node_id}'"
            )
        if item.to_node_id not in target_nodes or item.to_node_id not in target_boxes:
            raise RenderInvalidInputError(
                f"persistent transition '{item.transition_item_id}' references unknown target node '{item.to_node_id}'"
            )
        if (
            abs(item.source_frame_width - source_layout.frame_width) > 1e-4
            or abs(item.source_frame_height - source_layout.frame_height) > 1e-4
            or abs(item.target_frame_width - target_layout.frame_width) > 1e-4
            or abs(item.target_frame_height - target_layout.frame_height) > 1e-4
        ):
            raise RenderInvalidInputError(
                f"persistent transition '{item.transition_item_id}' frame geometry contradicts supplied layouts"
            )
        if item.source_rect != source_boxes[item.from_node_id].rect or item.target_rect != target_boxes[item.to_node_id].rect:
            raise RenderInvalidInputError(
                f"persistent transition '{item.transition_item_id}' geometry contradicts supplied LayoutGraph boxes"
            )
    unknown_departing = set(plan.departing_node_ids) - set(source_nodes)
    unknown_entering = set(plan.entering_node_ids) - set(target_nodes)
    if unknown_departing or unknown_entering:
        raise RenderInvalidInputError(
            f"transition plan contains unknown entering/departing nodes; "
            f"departing={sorted(unknown_departing)}, entering={sorted(unknown_entering)}"
        )

    move_items = tuple(item for item in plan.persistent_objects if item.effective_operation == TransitionOperation.MOVE)
    hidden_source = frozenset(item.from_node_id for item in move_items)
    hidden_target = frozenset(item.to_node_id for item in move_items)
    source_bg = renderer.render_frame(source_scene, source_layout, None, 0.0, hidden_node_ids=hidden_source)
    target_bg = renderer.render_frame(target_scene, target_layout, None, 0.0, hidden_node_ids=hidden_target)
    frame_count = max(1, int(round(plan.duration * profile.fps)))
    rendered_duration = frame_count / profile.fps

    def frames() -> Iterable[Image.Image]:
        for index in range(frame_count):
            p = 1.0 if frame_count == 1 else index / (frame_count - 1)
            frame = Image.blend(source_bg, target_bg, p)
            for item in move_items:
                rect = _interpolate_rect(item.source_rect, item.target_rect, p)
                source_node = source_nodes[item.from_node_id]
                target_node = target_nodes[item.to_node_id]
                node = source_node if p < 0.5 else target_node
                renderer._draw_node(frame, node, rect, opacity=1.0, reveal=1.0, emphasis=0.0)
            yield frame

    count, digest = _encode_frames(
        frames(), output_path=Path(output_path), width=sw, height=sh,
        fps=profile.fps, crf=profile.crf, preset=profile.preset,
    )
    return RenderedArtifact(
        artifact_id=f"transition:{plan.transition_id}",
        kind=RenderArtifactKind.TRANSITION,
        path=str(Path(output_path)),
        duration=rendered_duration,
        width=sw, height=sh, fps=profile.fps, frame_count=count,
        frame_digest=digest,
        source_hash=_source_hash(source_scene, source_layout, target_scene, target_layout, plan, profile),
    )
