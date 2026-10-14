"""V3-74 guarded *actual host Manim* process-renderer QA integration.

Not a general Manim/Visual Director coverage claim. Supports the existing
typed V3-45 ordered_process horizontal bounded graph only. V3-73 immutable
Frame IR validates every physical traversal frame BEFORE Docker invocation;
existing V3-45 decoded-H264 process overlap witness is required AFTER mux.
Unsupported semantic families and missing evidence FAIL CLOSED.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw

from learnflow_v3.creative_manim_ablation import Blocked
from learnflow_v3.semantic_scene_wire import SceneWire, process_edge_layout
from learnflow_v3.generalized_temporal_visual_qa import (
    FPS, Rect, Object, Edge, Frame, make_text, marker, validate_timeline,
)
from learnflow_v3.process_edge_visual_qa import inspect_first_edge

V3_74_SUPPORTED = "ordered_process"
W, H, SCALE = 1280, 720, 90
CURSOR_BOUND_RADIUS_PX = 8.25  # slightly larger than native Dot radius .09*90
NATIVE_PIXELS_GATE = "EXISTING_V345_DECODED_FIRST_EDGE_ONLY"


def need(ok, code):
    if not ok:
        raise Blocked("V374_" + code)


def world_to_pixel(x, y):
    return (W/2+x*SCALE, H/2-y*SCALE)


def node_rect(node):
    cx, cy = world_to_pixel(node.x, node.y)
    return Rect(cx - node.width*SCALE/2, cy - node.height*SCALE/2,
                cx + node.width*SCALE/2, cy + node.height*SCALE/2)


def node_caption(node):
    b = node_rect(node)
    # Conservative host-side proxy only: Manim CMU glyphs are NOT Pillow
    # glyphs. Never imply pixel-certified all-video typography from this.
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    from learnflow_v3.pedagogical_storytelling_slice import font
    f = font(25)
    size = d.textbbox((0, 0), node.text, font=f)
    x = round((b.left+b.right-(size[2]-size[0]))/2 - size[0])
    y = round((b.top+b.bottom-(size[3]-size[1]))/2 - size[1])
    return make_text(f"{node.id}_caption", node.text, x, y,
                     fontsize=25, parent_id=node.id)


def traversal_segments(scene: SceneWire, beat_frames: list[int]) -> list[dict]:
    need(scene.family == V3_74_SUPPORTED, "NO_EXPORTER_FOR_FAMILY")
    need(len(beat_frames) == 4 and all(type(v) is int and v > 25
                                      for v in beat_frames), "AUDIO_CLOCK_UNCERTIFIED")
    objs = {v.id: v for v in scene.graphics if v.kind == "node"}
    edges = {v.id: v for v in scene.graphics if v.kind == "edge"}
    need(len(objs) == 3 and len(edges) == 2, "UNSUPPORTED_PROCESS_TOPOLOGY")
    paths = process_edge_layout(scene)
    for name, edge in edges.items():
        a, b = objs[edge.src], objs[edge.dst]
        p = paths[name]
        need(abs(a.y-b.y) < 1e-6 and
             abs(p["src"][1]-p["dst"][1]) < 1e-6 and
             p["src"][0] < p["dst"][0],
             "NO_EXPORTER_FOR_NON_HORIZONTAL_OR_REVERSED_PATH")
    segments = []
    offset = 0
    for index, (beat, duration) in enumerate(zip(scene.beats, beat_frames)):
        for event in beat.events:
            if event.kind != "traverse_edge":
                continue
            need(event.target in edges and not event.source,
                 "UNCERTIFIED_TRAVERSAL_EDGE")
            start = offset+int(duration*event.at)
            end = offset+int(duration*(event.at+event.span))
            need(start >= offset and end <= offset+duration and end-start >= 3,
                 "TRAVERSAL_FRAME_WINDOW_INVALID")
            segments.append({"beat": index, "edge_id": event.target,
                             "first_frame": start, "last_frame_exclusive": end,
                             "frames": end-start})
        offset += duration
    need(len(segments) == 2 and
         {s["edge_id"] for s in segments} == set(edges),
         "TRAVERSAL_COVERAGE_INCOMPLETE")
    return segments


def certify_before_render(scene: SceneWire, beat_frames: list[int],
                          *, marker_end_override_world=None) -> dict:
    segments = traversal_segments(scene, beat_frames)
    nodes = {v.id: v for v in scene.graphics if v.kind == "node"}
    worldpaths = process_edge_layout(scene)
    records = []
    for segment in segments:
        wire = next(v for v in scene.graphics
                    if v.id == segment["edge_id"])
        a, b = nodes[wire.src], nodes[wire.dst]
        source, target = worldpaths[wire.id]["src"], worldpaths[wire.id]["dst"]
        if marker_end_override_world is not None:
            # TEST-ONLY hostile intrusion; never called from real runner.
            target = (marker_end_override_world, target[1])
        geometry = [Object(n.id, "box", node_rect(n), fill="#34465a")
                    for n in nodes.values()]
        geometry.extend(node_caption(n) for n in nodes.values())
        edge = Edge(f"route_{wire.id}", a.id, b.id,
                    world_to_pixel(0, source[1])[1])
        frames = []
        for offset in range(segment["frames"]):
            progress = offset/max(1, segment["frames"]-1)
            x = source[0]+(target[0]-source[0])*progress
            y = source[1]+(target[1]-source[1])*progress
            cx, cy = world_to_pixel(x, y)
            point = marker("moving_cursor", cx, cy, edge.edge_id,
                           radius=CURSOR_BOUND_RADIUS_PX)
            frames.append(Frame(offset, tuple(geometry+[point]), (edge,)))
        try:
            checked = validate_timeline(tuple(frames),
                                        expected_frames=len(frames))
        except (ValueError, TypeError) as exc:
            raise Blocked("V374_GENERIC_V373_TIMELINE_REJECTED:"+
                          str(exc)[:160]) from None
        records.append({**segment,
                        "v373_geometry_frames_checked": checked["checked_frames"],
                        "v373_max_step_px": checked["max_observed_step_px"],
                        "geometry_status": checked["geometry"],
                        "node_boundary": "CERTIFIED_FOR_EXPORTED_ROI"})
    return {"checkpoint": "V3-74", "family": V3_74_SUPPORTED,
            "supported_graph": "3_NODES_2_HORIZONTAL_EDGES",
            "total_video_frames_expected": sum(beat_frames),
            "traversal_frame_count": sum(r["frames"] for r in records),
            "traversal_segments": records,
            "source_compiler": "V3-45_HOST_MANIM_NOT_LLMPYTHON",
            "generic_contract": "V3-73_VALIDATE_TIMELINE",
            "scope": "PROCESS_NODES_AND_CURSOR_EXPORTED_ROI_ONLY",
            "typography_actual_manim": "NOT_PIXEL_CERTIFIED",
            "synthetic_model_origin": True}


def enforce_after_native(scene: SceneWire, beat_frames: list[int],
                         movie: Path, upstream_gate: dict) -> dict:
    need(upstream_gate["checkpoint"] == "V3-74" and
         upstream_gate["family"] == scene.family and
         upstream_gate["traversal_frame_count"] > 0,
         "MISSING_VALIDATED_UPSTREAM_RECEIPT")
    need(movie.is_file() and movie.stat().st_size > 1000,
         "MISSING_NATIVE_MOVIE")
    try:
        subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel",
                        "error", "-xerror", "-i", str(movie),
                        "-map", "0:v:0", "-f", "null", "-"],
                       stdout=subprocess.DEVNULL, check=True, timeout=140)
    except (OSError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired):
        raise Blocked("V374_FULL_NATIVE_DECODE_FAILED") from None
    # Actual decoded H264 pixel ROI witness: reuse V3-45-FIX directly.
    # Importantly, do NOT substitute declared rectangle geometry for pixels.
    actual = inspect_first_edge(movie, scene, beat_frames, require_fixed=True)
    need(actual["new_edge_pixels_inside_source_node"] <= 8 and
         actual["new_edge_pixels_inside_target_node"] <= 8 and
         actual["cursor_pixels_changed_on_source_caption"] <= 8 and
         actual["new_edge_pixels_in_open_gap"] >= 100,
         "DECODED_FIRST_EDGE_PIXEL_GATE_FAILED")
    return {
        "checkpoint": "V3-74", "status": "PASS_BOUNDED_REAL_MANIM_PROCESS_ROUTE",
        "output_mp4_sha256": sha256(movie.read_bytes()).hexdigest(),
        "pre_render_geometry": upstream_gate,
        "post_render_native": {
            "full_decode": "PASS",
            "decoded_pixel_witness": actual,
            "pixel_scope": NATIVE_PIXELS_GATE,
            "uninspected_rendered_objects": "NOT_CERTIFIED",
        },
        "source_authorship": "SYNTHETIC_HOST_JSON_NOT_MODEL",
        "human_quality": "UNRATED",
        "learning_gain": "NOT_MEASURED",
        "production": "BLOCKED",
    }
