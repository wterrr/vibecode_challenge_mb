"""Graphviz dot backend adapter for V2-04 graph layout."""

from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from typing import Any

from learnflow_v2.core.errors import (
    GraphLayoutBackendError,
    GraphLayoutBackendUnavailableError,
    GraphLayoutUnsupportedCapabilityError,
)
from learnflow_v2.layout.graph import BackendNode, BackendRoute, BackendLayoutResult, GraphLayoutInput, LayoutDirection
from learnflow_v2.layout.schema import GraphBackendKind, Point, RoutingStyle

GV_DPI = 72.0  # dot JSON coordinates are points; width/height attributes are inches.


def dot_version() -> str | None:
    exe = shutil.which("dot")
    if not exe:
        return None
    try:
        res = subprocess.run([exe, "-V"], capture_output=True, text=True, shell=False, timeout=5)
    except Exception:
        return None
    out = (res.stderr or res.stdout).strip()
    return out or None


def is_available() -> bool:
    return shutil.which("dot") is not None


def _rankdir(direction: LayoutDirection) -> str:
    return {
        LayoutDirection.RIGHT: "LR",
        LayoutDirection.LEFT: "RL",
        LayoutDirection.DOWN: "TB",
        LayoutDirection.UP: "BT",
    }[direction]


def _finite(v: Any) -> float:
    f = float(v)
    if not math.isfinite(f):
        raise ValueError("non-finite")
    return round(f, 4)


def _parse_bb(bb: str) -> tuple[float, float, float, float]:
    vals = [float(x) for x in bb.split(",")]
    if len(vals) != 4:
        raise ValueError("bad bb")
    return tuple(vals)  # type: ignore[return-value]


class GraphvizBackend:
    """Real local dot -Tjson0 backend with safe internal IDs."""

    name = GraphBackendKind.GRAPHVIZ

    def __init__(self, timeout: float = 8.0) -> None:
        self.timeout = timeout

    def layout(self, graph_input: GraphLayoutInput) -> BackendLayoutResult:
        if not shutil.which("dot"):
            raise GraphLayoutBackendUnavailableError("Graphviz dot executable is not available")
        if graph_input.strict_orthogonal and any(e.source_side is not None or e.target_side is not None for e in graph_input.edges):
            raise GraphLayoutUnsupportedCapabilityError(
                "Graphviz dot cannot honestly guarantee strict orthogonal fixed-side directional ports"
            )
        dot = self._build_dot(graph_input)
        try:
            res = subprocess.run(["dot", "-Tjson0"], input=dot, capture_output=True, text=True, shell=False, timeout=self.timeout)
        except subprocess.TimeoutExpired as exc:
            raise GraphLayoutBackendError("Graphviz subprocess timed out", {"timeout": self.timeout}) from exc
        if res.returncode != 0:
            raise GraphLayoutBackendError("Graphviz dot failed", {"stderr_preview": res.stderr[:300]})
        try:
            raw = json.loads(res.stdout)
            return self._parse(raw, graph_input)
        except GraphLayoutBackendError:
            raise
        except Exception as exc:
            raise GraphLayoutBackendError("Graphviz returned malformed JSON layout") from exc

    def _build_dot(self, graph_input: GraphLayoutInput) -> str:
        node_map = {node.id: f"n{i:03d}" for i, node in enumerate(sorted(graph_input.nodes, key=lambda n: n.id))}
        lines = [
            "digraph G {",
            f'  graph [rankdir="{_rankdir(graph_input.direction)}", splines="polyline", nodesep="0.55", ranksep="0.85"];',
            '  node [shape="box", fixedsize="true", label="", margin="0", width="1", height="1"];',
            '  edge [arrowsize="0.7"];',
        ]
        for node in sorted(graph_input.nodes, key=lambda n: n.id):
            # inches in DOT, pixels/points internally.
            lines.append(f'  {node_map[node.id]} [width="{node.width / GV_DPI:.6f}", height="{node.height / GV_DPI:.6f}"];')
        for edge in sorted(graph_input.edges, key=lambda e: e.id):
            lines.append(f"  {node_map[edge.source]} -> {node_map[edge.target]} [id=\"{edge.id}\"];")
        lines.append("}")
        return "\n".join(lines)

    def _parse_edge_pos(self, pos: str, bb_top: float) -> list[Point]:
        tokens = pos.split()
        pts: list[Point] = []
        for tok in tokens:
            if tok.startswith("e,") or tok.startswith("s,"):
                parts = tok.split(",")
                if len(parts) >= 3:
                    x, y = float(parts[1]), float(parts[2])
                else:
                    continue
            else:
                if not re.match(r"^-?\d+(\.\d+)?,-?\d+(\.\d+)?$", tok):
                    continue
                x, y = [float(v) for v in tok.split(",")]
            p = Point(x=round(x, 4), y=round(bb_top - y, 4))
            if not pts or pts[-1] != p:
                pts.append(p)
        # Graphviz puts arrow endpoint first as e,x,y, followed by source-to-target
        # route points. Move the e-point to the end to preserve semantic source->target.
        if len(pts) >= 2 and pos.startswith("e,"):
            pts = pts[1:] + pts[:1]
        return pts

    def _parse(self, raw: dict[str, Any], graph_input: GraphLayoutInput) -> BackendLayoutResult:
        _, _, _, top = _parse_bb(raw["bb"])
        sorted_nodes = sorted(graph_input.nodes, key=lambda n: n.id)
        backend_to_id = {f"n{i:03d}": n.id for i, n in enumerate(sorted_nodes)}
        expected_backend = set(backend_to_id)
        nodes: list[BackendNode] = []
        for obj in raw.get("objects", []):
            name = obj.get("name")
            if name not in expected_backend:
                continue
            x_str, y_str = obj["pos"].split(",")
            cx = float(x_str)
            cy_top = top - float(y_str)
            node_id = backend_to_id[name]
            src = next(n for n in graph_input.nodes if n.id == node_id)
            nodes.append(BackendNode(
                id=node_id,
                x=round(cx - src.width / 2, 4),
                y=round(cy_top - src.height / 2, 4),
                width=round(src.width, 4),
                height=round(src.height, 4),
            ))
        if {n.id for n in nodes} != {n.id for n in graph_input.nodes}:
            raise GraphLayoutBackendError("Graphviz output missing node")
        routes: list[BackendRoute] = []
        unmatched = list(sorted(graph_input.edges, key=lambda e: e.id))
        for eobj in raw.get("edges", []):
            eid = eobj.get("id")
            if eid is None:
                # json0 may omit id; fallback by tail/head mapping and consume deterministically.
                tail_name = raw["objects"][eobj["tail"]]["name"]
                head_name = raw["objects"][eobj["head"]]["name"]
                src_id = backend_to_id[tail_name]
                tgt_id = backend_to_id[head_name]
                match = [e for e in unmatched if e.source == src_id and e.target == tgt_id]
                if not match:
                    raise GraphLayoutBackendError("Graphviz output edge cannot be mapped")
                edge = match[0]
                unmatched.remove(edge)
            else:
                match = [e for e in unmatched if e.id == eid]
                if not match:
                    raise GraphLayoutBackendError("Graphviz output unknown edge")
                edge = match[0]
                unmatched.remove(edge)
            pts = self._parse_edge_pos(eobj.get("pos", ""), top)
            if len(pts) < 2:
                raise GraphLayoutBackendError("Graphviz output missing route points")
            routes.append(BackendRoute(edge_id=edge.id, source=edge.source, target=edge.target, points=pts, routing_style=RoutingStyle.POLYLINE, source_port=None, target_port=None))
        if {r.edge_id for r in routes} != {e.id for e in graph_input.edges}:
            raise GraphLayoutBackendError("Graphviz output missing edge")
        return BackendLayoutResult(nodes=sorted(nodes, key=lambda n: n.id), routes=sorted(routes, key=lambda r: r.edge_id), backend=GraphBackendKind.GRAPHVIZ, diagnostics={"dot_version": dot_version(), "dpi": GV_DPI})
