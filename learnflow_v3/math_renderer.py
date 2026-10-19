"""V3-08 finite, source-bound mathematics renderers; no generated executable code.

Exact polynomial arithmetic checks all transformation steps and chart points.
Only Pillow/FFmpeg and existing V3 blackboard/decoded-frame utilities are used.
This is a standalone bounded renderer, NOT a general algebra or lesson pipeline.
"""
from __future__ import annotations

import ast
import hashlib
import math
import os
from pathlib import Path
import subprocess
import time
from typing import Literal

from PIL import Image, ImageDraw
from pydantic import Field, StrictInt, model_validator

from learnflow_v2.repair import compute_content_hash
from learnflow_v2.scenegraph import SceneGraph
from learnflow_v2.scenegraph.enums import LayoutIntent, NodeKind, RelationKind, ScenePurpose
from .blackboard_style import BLACK, WHITE, GREY, FAINT, CYAN, GREEN, YELLOW, cmu_font, assert_fits
from .models import SemanticContractError, V3Model
from .sequence_renderer import SequenceRenderProfile, _ease, _ffmpeg_anchor, _mean_absolute_error

VERSION = "v3-08-certified-math-blackboard-v1"
Poly = tuple[int, int, int]  # constant, linear, quadratic coefficients
MAX_COEFFICIENT = 128


class GraphPoint(V3Model):
    point_id: str = Field(min_length=1, max_length=32, pattern=r"^[a-z][a-z0-9_-]*$")
    x: StrictInt = Field(ge=-4, le=4)
    y: StrictInt = Field(ge=-6, le=6)


class FunctionGraph(V3Model):
    scenegraph_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    coefficients: tuple[StrictInt, StrictInt, StrictInt]
    x_domain: tuple[StrictInt, StrictInt]
    steps: tuple[GraphPoint, ...] = Field(min_length=3, max_length=9)

    @model_validator(mode="after")
    def _shape(self):
        if len(set(p.point_id for p in self.steps)) != len(self.steps):
            raise ValueError("V3_08_GRAPH_DUPLICATE_POINT_ID")
        return self


class EquationStep(V3Model):
    step_id: str = Field(min_length=1, max_length=32, pattern=r"^[a-z][a-z0-9_-]*$")
    expression: str = Field(min_length=1, max_length=65)


class EquationDerivation(V3Model):
    scenegraph_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    steps: tuple[EquationStep, ...] = Field(min_length=3, max_length=6)

    @model_validator(mode="after")
    def _shape(self):
        if len(set(s.step_id for s in self.steps)) != len(self.steps):
            raise ValueError("V3_08_EQUATION_DUPLICATE_ID")
        return self


class MathRenderEvidence(V3Model):
    renderer_version: Literal["v3-08-certified-math-blackboard-v1"] = VERSION
    family: Literal["FUNCTION_GRAPH", "EQUATION_DERIVATION"]
    video_path: str
    video_sha256: str
    video_bytes: int
    source_hash: str
    scenegraph_hash: str
    frame_count: int
    fps: int
    duration_seconds: float
    decoded_frame_mae: tuple[float, ...]
    semantic_roi_deltas: tuple[float, ...]
    within_beat_motion_deltas: tuple[float, ...]
    semantic_object_centers: dict[str, tuple[int, int]]
    decoded_qa_pass: Literal[True] = True
    wall_seconds: float


def polynomial_value(coefficients: Poly, x: float) -> float:
    return coefficients[0] + coefficients[1] * x + coefficients[2] * x * x


def graph_source(coefficients: Poly, domain: tuple[int, int]) -> str:
    """Canonical machine-readable chart source, never guessed from an LLM label."""
    return f"f(x) = {coefficients[2]}*x**2 + {coefficients[1]}*x + {coefficients[0]}; domain=[{domain[0]},{domain[1]}]"


def verify_function_graph(spec: FunctionGraph, graph: SceneGraph) -> None:
    if compute_content_hash(graph) != spec.scenegraph_sha256:
        raise SemanticContractError("V3_08_GRAPH_SOURCE_HASH_MISMATCH")
    if graph.purpose not in (ScenePurpose.DEMONSTRATE, ScenePurpose.EXPLAIN):
        raise SemanticContractError("V3_08_GRAPH_PURPOSE_UNSUPPORTED")
    if graph.layout_intent.type not in (LayoutIntent.ILLUSTRATION, LayoutIntent.FREEFORM):
        raise SemanticContractError("V3_08_GRAPH_LAYOUT_UNSUPPORTED")
    if len(graph.nodes) != 1 or graph.nodes[0].kind != NodeKind.CHART or graph.relations or graph.groups:
        raise SemanticContractError("V3_08_GRAPH_REQUIRES_ONE_CHART")
    if graph.nodes[0].content != graph_source(spec.coefficients, spec.x_domain):
        raise SemanticContractError("V3_08_GRAPH_SOURCE_DRIFT")
    c0, c1, c2 = spec.coefficients
    if max(map(abs, spec.coefficients)) > 12:
        raise SemanticContractError("V3_08_GRAPH_COEFFICIENT_LIMIT")
    a, b = spec.x_domain
    if not (-4 <= a < b <= 4):
        raise SemanticContractError("V3_08_GRAPH_DOMAIN_INVALID")
    xs = [p.x for p in spec.steps]
    if xs[0] != a or xs[-1] != b or any(v >= w for v, w in zip(xs, xs[1:])):
        raise SemanticContractError("V3_08_GRAPH_POINT_ORDER_OR_COVERAGE")
    for step in spec.steps:
        if polynomial_value(spec.coefficients, step.x) != step.y:
            raise SemanticContractError(f"V3_08_GRAPH_POINT_REPLAY_MISMATCH:{step.point_id}")
    # For a degree-2 function, extrema occur at endpoints or its vertex.
    candidates = [float(a), float(b)]
    if c2:
        vertex = -c1 / (2 * c2)
        if a < vertex < b:
            candidates.append(vertex)
    if any(abs(polynomial_value(spec.coefficients, x)) > 5.5 for x in candidates):
        raise SemanticContractError("V3_08_GRAPH_CURVE_OUTSIDE_SAFE_AXIS")


def _poly_add(a: Poly, b: Poly) -> Poly:
    result = tuple(x + y for x, y in zip(a, b))
    if max(map(abs, result)) > MAX_COEFFICIENT:
        raise SemanticContractError("V3_08_ALGEBRA_COEFFICIENT_LIMIT")
    return result  # type: ignore[return-value]


def _poly_mul(a: Poly, b: Poly) -> Poly:
    full = [0] * 5
    for i, v in enumerate(a):
        for j, w in enumerate(b):
            full[i + j] += v * w
    if full[3] or full[4]:
        raise SemanticContractError("V3_08_ALGEBRA_DEGREE_EXCEEDED")
    if max(map(abs, full)) > MAX_COEFFICIENT:
        raise SemanticContractError("V3_08_ALGEBRA_COEFFICIENT_LIMIT")
    return tuple(full[:3])  # type: ignore[return-value]


def parse_polynomial(expression: str) -> Poly:
    """A restricted AST *data* interpreter, never Python eval/exec."""
    try:
        node = ast.parse(expression, mode="eval").body
    except (SyntaxError, ValueError) as exc:
        raise SemanticContractError("V3_08_INVALID_MATH_EXPRESSION") from exc

    def walk(n: ast.AST, depth: int = 0) -> Poly:
        if depth > 14:
            raise SemanticContractError("V3_08_ALGEBRA_DEPTH_LIMIT")
        if isinstance(n, ast.Constant) and type(n.value) is int and abs(n.value) <= MAX_COEFFICIENT:
            return (n.value, 0, 0)
        if isinstance(n, ast.Name) and n.id == "x":
            return (0, 1, 0)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            p = walk(n.operand, depth + 1)
            return p if isinstance(n.op, ast.UAdd) else _poly_mul(p, (-1, 0, 0))
        if isinstance(n, ast.BinOp):
            if isinstance(n.op, ast.Pow):
                # Literal exponent only; no dynamic powers or AST execution.
                if not isinstance(n.right, ast.Constant) or type(n.right.value) is not int or n.right.value not in (0, 1, 2):
                    raise SemanticContractError("V3_08_ALGEBRA_POWER_UNSUPPORTED")
                p = walk(n.left, depth + 1)
                if n.right.value == 0:
                    return (1, 0, 0)
                if n.right.value == 1:
                    return p
                return _poly_mul(p, p)
            a, b = walk(n.left, depth + 1), walk(n.right, depth + 1)
            if isinstance(n.op, ast.Add):
                return _poly_add(a, b)
            if isinstance(n.op, ast.Sub):
                return _poly_add(a, _poly_mul(b, (-1, 0, 0)))
            if isinstance(n.op, ast.Mult):
                return _poly_mul(a, b)
        raise SemanticContractError("V3_08_ALGEBRA_OPERATOR_NOT_ALLOWLISTED")

    return walk(node)


def verify_equation_derivation(spec: EquationDerivation, graph: SceneGraph) -> Poly:
    if compute_content_hash(graph) != spec.scenegraph_sha256:
        raise SemanticContractError("V3_08_EQUATION_SOURCE_HASH_MISMATCH")
    if graph.purpose not in (ScenePurpose.EXPLAIN, ScenePurpose.DEMONSTRATE):
        raise SemanticContractError("V3_08_EQUATION_PURPOSE_UNSUPPORTED")
    if graph.layout_intent.type not in (LayoutIntent.PROCESS, LayoutIntent.HIERARCHY):
        raise SemanticContractError("V3_08_EQUATION_LAYOUT_UNSUPPORTED")
    if graph.groups or len(graph.nodes) != len(spec.steps) or len(graph.relations) != len(spec.steps) - 1:
        raise SemanticContractError("V3_08_EQUATION_TOPOLOGY_SIZE_MISMATCH")
    nodes = {n.id: n for n in graph.nodes}
    for step in spec.steps:
        node = nodes.get(step.step_id)
        if node is None or node.kind != NodeKind.EQUATION or node.content != step.expression:
            raise SemanticContractError("V3_08_EQUATION_SOURCE_DRIFT")
    for previous, current, rel in zip(spec.steps, spec.steps[1:], graph.relations):
        if (rel.source != previous.step_id or rel.target != current.step_id or
            rel.kind not in (RelationKind.EQUIVALENT_TO, RelationKind.TRANSFORMS_INTO)):
            raise SemanticContractError("V3_08_EQUATION_TRANSFORMATION_IDENTITY_MISMATCH")
    polys = [parse_polynomial(step.expression) for step in spec.steps]
    if any(p != polys[0] for p in polys[1:]):
        raise SemanticContractError("V3_08_EQUATION_NOT_SYMBOLICALLY_EQUIVALENT")
    if len({s.expression for s in spec.steps}) != len(spec.steps):
        raise SemanticContractError("V3_08_EQUATION_NO_EFFECTIVE_TRANSFORM")
    return polys[0]



def pretty_polynomial(coefficients: Poly) -> str:
    """Conventional printed algebra; source/provenance remains canonical."""
    terms = []
    for power, coefficient in ((2, coefficients[2]), (1, coefficients[1]), (0, coefficients[0])):
        if not coefficient:
            continue
        magnitude = abs(coefficient)
        factor = ("x²" if power == 2 else "x" if power == 1 else "")
        label = ("" if magnitude == 1 and power else str(magnitude)) + factor
        if not terms:
            terms.append(("-" if coefficient < 0 else "") + label)
        else:
            terms.append((" − " if coefficient < 0 else " + ") + label)
    return "f(x) = " + ("".join(terms) if terms else "0")


def pretty_expression(expression: str) -> str:
    """Typography for an *already verified* AST. Not a symbolic proof engine."""
    root = ast.parse(expression, mode="eval").body

    def show(node, parent_precedence=0):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return str(node.value)
        if isinstance(node, ast.Name) and node.id == "x":
            return "x"
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = ("−" if isinstance(node.op, ast.USub) else "+") + show(node.operand, 3)
            return f"({value})" if 3 < parent_precedence else value
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Pow):
                base = show(node.left, 4)
                return base + {0: "⁰", 1: "¹", 2: "²"}[node.right.value]
            if isinstance(node.op, (ast.Add, ast.Sub)):
                prec = 1
                op = " + " if isinstance(node.op, ast.Add) else " − "
                value = show(node.left, prec) + op + show(node.right, prec + (1 if isinstance(node.op, ast.Sub) else 0))
            elif isinstance(node.op, ast.Mult):
                prec = 2
                if all(isinstance(x, ast.Name) and x.id == "x" for x in (node.left, node.right)):
                    value = "x²"
                elif isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Name):
                    value = show(node.left, prec) + show(node.right, prec)
                elif isinstance(node.left, ast.BinOp) and isinstance(node.right, ast.BinOp):
                    value = show(node.left, prec + 1) + show(node.right, prec + 1)
                else:
                    value = show(node.left, prec + 1) + "·" + show(node.right, prec + 1)
            else:
                raise SemanticContractError("V3_08_PRETTY_EXPRESSION_UNSUPPORTED")
            return f"({value})" if prec < parent_precedence else value
        raise SemanticContractError("V3_08_PRETTY_EXPRESSION_UNSUPPORTED")

    return show(root)

def _draw_header(d: ImageDraw.ImageDraw, profile: SequenceRenderProfile, heading: str):
    sx, sy = profile.width / 960, profile.height / 540
    font = cmu_font(max(12, round(33 * sy)))
    assert_fits(d, heading, font, round(profile.width * .86), role="MATH_TITLE")
    d.text((round(65 * sx), round(30 * sy)), heading, font=font, fill=WHITE)
    d.line((round(65 * sx), round(97 * sy), round(895 * sx), round(97 * sy)), fill=FAINT, width=max(1, round(2 * sy)))
    return sx, sy


def _graph_pixel(profile: SequenceRenderProfile, x: float, y: float) -> tuple[int, int]:
    sx, sy = profile.width / 960, profile.height / 540
    return round((485 + x * 82) * sx), round((288 - y * 23) * sy)


def draw_function_frame(spec: FunctionGraph, graph: SceneGraph, step_index: int,
                        profile: SequenceRenderProfile, progress: float = 1.0) -> Image.Image:
    if not 0 <= step_index < len(spec.steps):
        raise SemanticContractError("V3_08_GRAPH_FRAME_INDEX_INVALID")
    progress = _ease(progress)
    w, h = profile.width, profile.height
    image = Image.new("RGB", (w, h), BLACK)
    d = ImageDraw.Draw(image)
    sx, sy = _draw_header(d, profile, "A function, traced point by point")
    minor = cmu_font(max(11, round(17 * sy)))
    label = cmu_font(max(12, round(22 * sy)))
    formula = pretty_polynomial(spec.coefficients)
    assert_fits(d, formula, label, round(750 * sx), role="FUNCTION_LABEL")
    d.text((round(80 * sx), round(112 * sy)), formula, font=label, fill=CYAN)
    x0, y0 = _graph_pixel(profile, -4, 0)
    x1, _ = _graph_pixel(profile, 4, 0)
    _, ytop = _graph_pixel(profile, 0, 6)
    _, ybottom = _graph_pixel(profile, 0, -6)
    d.line((x0, y0, x1, y0), fill=GREY, width=max(1, round(2 * sy)))
    d.line((round(485 * sx), ytop, round(485 * sx), ybottom), fill=GREY, width=max(1, round(2 * sy)))
    for x in range(-4, 5, 2):
        px, py = _graph_pixel(profile, x, 0)
        d.line((px, py - 4, px, py + 4), fill=GREY)
        d.text((px, py + 11 * sy), str(x), font=minor, fill=GREY, anchor="mt")
    for y in range(-4, 5, 2):
        px, py = _graph_pixel(profile, 0, y)
        d.line((px - 4, py, px + 4, py), fill=GREY)
        if y:
            d.text((px - 15 * sx, py), str(y), font=minor, fill=GREY, anchor="rm")
    start, end = spec.x_domain
    full = [_graph_pixel(profile, start + (end - start) * i / 160,
                         polynomial_value(spec.coefficients, start + (end - start) * i / 160))
            for i in range(161)]
    d.line(full, fill=FAINT, width=max(2, round(2 * sy)), joint="curve")
    target = spec.steps[step_index]
    prev_x = spec.steps[step_index - 1].x if step_index else float(start)
    active_x = prev_x + (target.x - prev_x) * progress
    if step_index == 0:
        active_x = float(start)
    n = max(1, round(160 * (active_x - start) / (end - start)))
    reveal = [_graph_pixel(profile, start + (active_x - start) * i / n,
                           polynomial_value(spec.coefficients, start + (active_x - start) * i / n))
              for i in range(n + 1)]
    if len(reveal) > 1:
        d.line(reveal, fill=YELLOW, width=max(2, round(4 * sy)), joint="curve")
    current_y = polynomial_value(spec.coefficients, active_x)
    cx, cy = _graph_pixel(profile, active_x, current_y)
    r = round((4 + 9 * progress) * sy)
    d.ellipse((cx-r, cy-r, cx+r, cy+r), outline=YELLOW, width=max(2, round(2 * sy)))
    d.ellipse((cx-3, cy-3, cx+3, cy+3), fill=YELLOW)
    # Certified state text, not an inferred float from raster geometry.
    detail = f"Point {target.point_id}: ({target.x}, {target.y})"
    assert_fits(d, detail, label, round(500 * sx), role="GRAPH_POINT")
    d.text((round(640 * sx), round(455 * sy)), detail, font=label, fill=GREEN, anchor="mm")
    d.text((round(70 * sx), round(500 * sy)),
           f"Point {step_index + 1}/{len(spec.steps)}  |  x grows from {start} to {end}",
           font=minor, fill=GREY)
    return image


def draw_equation_frame(spec: EquationDerivation, graph: SceneGraph, step_index: int,
                        profile: SequenceRenderProfile, progress: float = 1.0) -> Image.Image:
    if not 0 <= step_index < len(spec.steps):
        raise SemanticContractError("V3_08_EQUATION_FRAME_INDEX_INVALID")
    w, h = profile.width, profile.height
    image = Image.new("RGB", (w, h), BLACK)
    d = ImageDraw.Draw(image)
    sx, sy = _draw_header(d, profile, "Why these expressions are equal")
    font = cmu_font(max(13, round(29 * sy)))
    small = cmu_font(max(10, round(17 * sy)))
    # Stable semantic row identity; limit to six rows so bottom subtitle stays free.
    for i, step in enumerate(spec.steps):
        y = round((158 + i * 54) * sy)
        if y > round(450 * sy):
            raise SemanticContractError("V3_08_EQUATION_ROW_OVERFLOW")
        expression = pretty_expression(step.expression)
        assert_fits(d, expression, font, round(740 * sx), role="EQUATION")
        center = round(480 * sx)
        glyph = d.textbbox((0, 0), expression, font=font)
        half = (glyph[2] - glyph[0]) / 2
        left = round(center - half)
        d.text((center, y), expression, font=font, anchor="mt",
               fill=WHITE if i == step_index else GREEN if i < step_index else GREY)
        d.text((round(148 * sx), y), f"{i + 1:02d}", font=small,
               fill=YELLOW if i == step_index else GREY)
        if i == step_index:
            end = round(left + 2 * half * _ease(progress))
            d.line((left, y + round(32 * sy), end, y + round(32 * sy)),
                   fill=YELLOW, width=max(2, round(3 * sy)))
        if i < len(spec.steps) - 1:
            d.text((center, y + round(37 * sy)), "=", font=small, fill=CYAN,
                   anchor="mt")
    d.text((round(65 * sx), round(497 * sy)),
           f"Equivalent for every x  |  Transformation {step_index + 1}/{len(spec.steps)}",
           font=small, fill=GREY)
    return image


def _encode_math(*, family: Literal["FUNCTION_GRAPH", "EQUATION_DERIVATION"],
                 spec: FunctionGraph | EquationDerivation, graph: SceneGraph,
                 drawer, centers: dict[str, tuple[int, int]], output_path: str | Path,
                 profile: SequenceRenderProfile) -> MathRenderEvidence:
    started = time.monotonic()
    if not isinstance(profile, SequenceRenderProfile):
        profile = SequenceRenderProfile.model_validate(profile)
    count = len(spec.steps) * profile.frames_per_step()
    if count > 600:
        raise SemanticContractError("V3_08_FRAME_BUDGET_EXCEEDED")
    out = Path(output_path).absolute()
    if out.suffix.lower() != ".mp4" or out.exists() or out.is_symlink() or not out.parent.is_dir():
        raise SemanticContractError("V3_08_UNSAFE_OUTPUT_PATH")
    if any(p.is_symlink() for p in (out.parent, *out.parent.parents)):
        raise SemanticContractError("V3_08_SYMLINK_OUTPUT_FORBIDDEN")
    tmp = out.with_name(f".{out.stem}.{compute_content_hash(spec)[:12]}.part.mp4")
    if tmp.exists():
        raise SemanticContractError("V3_08_TEMP_OUTPUT_EXISTS")
    command = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s:v",
               f"{profile.width}x{profile.height}", "-r", str(profile.fps),
               "-i", "pipe:0", "-an", "-c:v", "libx264", "-preset", "ultrafast",
               "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
               "-map_metadata", "-1", str(tmp)]
    proc = None
    try:
        proc = subprocess.Popen(command, stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        assert proc.stdin is not None
        for frame in range(count):
            step, sub = divmod(frame, profile.frames_per_step())
            phase = (sub + .5) / profile.frames_per_step()
            proc.stdin.write(drawer(spec, graph, step, profile, phase).tobytes())
        proc.stdin.close()
        assert proc.stderr is not None
        stderr = proc.stderr.read()
        if proc.wait(timeout=120) != 0 or not tmp.is_file() or tmp.stat().st_size < 1000:
            raise SemanticContractError("V3_08_FFMPEG_FAILED:" + stderr[-200:].decode(errors="replace"))
        indices = [i * profile.frames_per_step() + profile.frames_per_step() // 2
                   for i in range(len(spec.steps))]
        decoded, maes = [], []
        roi = (round(profile.width * .09), round(profile.height * .22),
               round(profile.width * .92), round(profile.height * .88))
        for i, frame in enumerate(indices):
            actual = _ffmpeg_anchor(tmp, at=(frame + .4) / profile.fps, profile=profile)
            expected = drawer(spec, graph, i, profile,
                              (frame % profile.frames_per_step() + .5) / profile.frames_per_step())
            error = _mean_absolute_error(actual, expected)
            if error > 8:
                raise SemanticContractError(f"V3_08_DECODED_FRAME_MISMATCH:{family}:{i}:{error:.3f}")
            decoded.append(actual)
            maes.append(round(error, 3))
        step_deltas = [_mean_absolute_error(a, b, rect=roi) for a, b in zip(decoded, decoded[1:])]
        if any(d < .18 for d in step_deltas):
            raise SemanticContractError("V3_08_NO_SEMANTIC_STATE_CHANGE")
        beat_deltas = []
        for i in range(len(spec.steps)):
            n = profile.frames_per_step()
            early = i * n + max(1, round(n * .12))
            late = i * n + max(2, round(n * .82))
            a = _ffmpeg_anchor(tmp, at=(early + .4) / profile.fps, profile=profile)
            b = _ffmpeg_anchor(tmp, at=(late + .4) / profile.fps, profile=profile)
            delta = _mean_absolute_error(a, b, rect=roi)
            if delta < .035:
                raise SemanticContractError(f"V3_08_NO_WITHIN_BEAT_MOTION:{family}:{i}")
            beat_deltas.append(round(delta, 3))
        try:
            os.link(tmp, out)  # publish without replacing a late-created target
        except FileExistsError as exc:
            raise SemanticContractError("V3_08_OUTPUT_RACE") from exc
        tmp.unlink()
    except Exception:
        if proc is not None and proc.poll() is None:
            proc.kill()
        if proc is not None:
            proc.wait()
        tmp.unlink(missing_ok=True)
        raise
    return MathRenderEvidence(
        family=family, video_path=str(out),
        video_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
        video_bytes=out.stat().st_size, source_hash=compute_content_hash(spec),
        scenegraph_hash=compute_content_hash(graph), frame_count=count,
        fps=profile.fps, duration_seconds=count / profile.fps,
        decoded_frame_mae=tuple(maes),
        semantic_roi_deltas=tuple(round(x, 3) for x in step_deltas),
        within_beat_motion_deltas=tuple(beat_deltas),
        semantic_object_centers=centers, wall_seconds=round(time.monotonic()-started, 3),
    )


def render_function_graph(*, spec: FunctionGraph, graph: SceneGraph,
                          output_path: str | Path,
                          profile: SequenceRenderProfile = SequenceRenderProfile()) -> MathRenderEvidence:
    verify_function_graph(spec, graph)
    centers = {p.point_id: _graph_pixel(profile, p.x, p.y) for p in spec.steps}
    return _encode_math(family="FUNCTION_GRAPH", spec=spec, graph=graph, drawer=draw_function_frame,
                        centers=centers, output_path=output_path, profile=profile)


def render_equation_derivation(*, spec: EquationDerivation, graph: SceneGraph,
                               output_path: str | Path,
                               profile: SequenceRenderProfile = SequenceRenderProfile()) -> MathRenderEvidence:
    verify_equation_derivation(spec, graph)
    centers = {s.step_id: (round(480*profile.width/960), round((158+i*54)*profile.height/540))
               for i, s in enumerate(spec.steps)}
    return _encode_math(family="EQUATION_DERIVATION", spec=spec, graph=graph,
                        drawer=draw_equation_frame, centers=centers,
                        output_path=output_path, profile=profile)
