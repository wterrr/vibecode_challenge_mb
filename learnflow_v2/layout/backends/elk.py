"""ELKJS backend adapter for V2-04 graph layout."""

from __future__ import annotations

import json
import math
from pathlib import Path
import shutil
import subprocess
from typing import Any

from learnflow_v2.core.errors import GraphLayoutBackendError, GraphLayoutBackendUnavailableError
from learnflow_v2.layout.graph import (
    BackendNode,
    BackendRoute,
    BackendLayoutResult,
    GraphLayoutInput,
    PortSide,
)
from learnflow_v2.layout.schema import GraphBackendKind, Point, RoutingStyle


REQUIRED_ELKJS_VERSION = "0.12.0"
ELKJS_REQUIRED_MESSAGE = "elkjs 0.12.0 is required; run npm ci"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def elkjs_version() -> str | None:
    node = shutil.which("node")
    if not node:
        return None
    try:
        res = subprocess.run(
            [node, "-e", "const p=require('elkjs/package.json'); console.log(p.version)"],
            capture_output=True, text=True, shell=False, timeout=5, cwd=str(_project_root()),
        )
    except Exception:
        return None
    return res.stdout.strip() if res.returncode == 0 else None


def elkjs_bundled_import_available() -> bool:
    node = shutil.which("node")
    if not node:
        return False
    try:
        res = subprocess.run(
            [node, "-e", "require('elkjs/lib/elk.bundled.js'); console.log('elkjs bridge import PASS')"],
            capture_output=True, text=True, shell=False, timeout=5, cwd=str(_project_root()),
        )
    except Exception:
        return False
    return res.returncode == 0 and "elkjs bridge import PASS" in res.stdout


def is_available() -> bool:
    return (
        shutil.which("node") is not None
        and elkjs_version() == REQUIRED_ELKJS_VERSION
        and elkjs_bundled_import_available()
    )


def _finite(v: Any) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        raise ValueError("non-finite coordinate")
    return round(float(v), 4)


_SIDE = {PortSide.NORTH: "NORTH", PortSide.EAST: "EAST", PortSide.SOUTH: "SOUTH", PortSide.WEST: "WEST"}


class ElkBackend:
    """Real local elkjs backend through a stdin/stdout MJS bridge."""

    name = GraphBackendKind.ELK

    def __init__(self, timeout: float = 8.0) -> None:
        self.timeout = timeout

    def layout(self, graph_input: GraphLayoutInput) -> BackendLayoutResult:
        node_exe = shutil.which("node")
        if not node_exe:
            raise GraphLayoutBackendUnavailableError("Node executable is not available")
        if elkjs_version() != REQUIRED_ELKJS_VERSION or not elkjs_bundled_import_available():
            raise GraphLayoutBackendUnavailableError(ELKJS_REQUIRED_MESSAGE)

        ports_by_node: dict[str, list[dict[str, str]]] = {n.id: [] for n in graph_input.nodes}
        edge_payload = []
        used_ports: set[str] = set()
        for e in graph_input.edges:
            source_port = None
            target_port = None
            if e.source_side is not None:
                source_port = f"{e.source}__out__{_SIDE[e.source_side]}__{e.id}"
                used_ports.add(source_port)
                ports_by_node[e.source].append({"id": source_port, "side": _SIDE[e.source_side]})
            if e.target_side is not None:
                target_port = f"{e.target}__in__{_SIDE[e.target_side]}__{e.id}"
                used_ports.add(target_port)
                ports_by_node[e.target].append({"id": target_port, "side": _SIDE[e.target_side]})
            edge_payload.append({"id": e.id, "source": e.source, "target": e.target, "source_port": source_port, "target_port": target_port})

        payload = {
            "id": graph_input.id,
            "direction": graph_input.direction.value,
            "nodes": [
                {"id": n.id, "width": n.width, "height": n.height, "ports": sorted(ports_by_node[n.id], key=lambda p: p["id"])}
                for n in graph_input.nodes
            ],
            "edges": edge_payload,
            "spacing": {"nodeNode": 48, "nodeNodeBetweenLayers": 80, "edgeNode": 20, "edgeEdge": 12},
        }
        bridge = Path(__file__).with_name("elk_bridge.mjs")
        try:
            res = subprocess.run(
                [node_exe, str(bridge)],
                input=json.dumps(payload, separators=(",", ":"), sort_keys=True),
                capture_output=True, text=True, shell=False, timeout=self.timeout, cwd=str(_project_root()),
            )
        except subprocess.TimeoutExpired as exc:
            raise GraphLayoutBackendError("ELK subprocess timed out", {"timeout": self.timeout}) from exc
        if res.returncode != 0:
            raise GraphLayoutBackendError("ELK subprocess failed", {"stderr_preview": res.stderr[:300]})
        try:
            raw = json.loads(res.stdout)
            return self._parse(raw, graph_input)
        except GraphLayoutBackendError:
            raise
        except Exception as exc:
            raise GraphLayoutBackendError("ELK returned malformed output") from exc

    def _parse(self, raw: dict[str, Any], graph_input: GraphLayoutInput) -> BackendLayoutResult:
        try:
            if not isinstance(raw, dict):
                raise GraphLayoutBackendError("ELK returned non-object output")
            node_ids = {n.id for n in graph_input.nodes}
            edge_ids = {e.id for e in graph_input.edges}
            nodes: list[BackendNode] = []
            for child in raw.get("children", []):
                if not isinstance(child, dict):
                    raise GraphLayoutBackendError("ELK returned malformed node")
                nid = child.get("id")
                if nid not in node_ids:
                    raise GraphLayoutBackendError("ELK returned unknown node")
                x = _finite(child.get("x"))
                y = _finite(child.get("y"))
                w = _finite(child.get("width"))
                h = _finite(child.get("height"))
                if w <= 0 or h <= 0:
                    raise GraphLayoutBackendError("ELK returned non-positive node dimensions")
                nodes.append(BackendNode(id=nid, x=x, y=y, width=w, height=h))

            routes: list[BackendRoute] = []
            for edge in raw.get("edges", []):
                if not isinstance(edge, dict):
                    raise GraphLayoutBackendError("ELK returned malformed edge")
                eid = edge.get("id")
                if eid not in edge_ids:
                    raise GraphLayoutBackendError("ELK returned unknown edge")
                sections = edge.get("sections") or []
                if not sections:
                    raise GraphLayoutBackendError("ELK returned edge without sections")
                pts: list[Point] = []
                for sec in sections:
                    if not isinstance(sec, dict):
                        raise GraphLayoutBackendError("ELK returned malformed edge section")
                    sp = sec.get("startPoint")
                    ep = sec.get("endPoint")
                    if not isinstance(sp, dict) or not isinstance(ep, dict):
                        raise GraphLayoutBackendError("ELK edge section missing endpoint")
                    if not pts:
                        pts.append(Point(x=_finite(sp.get("x")), y=_finite(sp.get("y"))))
                    for bp in sec.get("bendPoints") or []:
                        if not isinstance(bp, dict):
                            raise GraphLayoutBackendError("ELK returned malformed bend point")
                        p = Point(x=_finite(bp.get("x")), y=_finite(bp.get("y")))
                        if p != pts[-1]:
                            pts.append(p)
                    end = Point(x=_finite(ep.get("x")), y=_finite(ep.get("y")))
                    if end != pts[-1]:
                        pts.append(end)
                src_edge = next(e for e in graph_input.edges if e.id == eid)
                sp = f"{src_edge.source}__out__{_SIDE[src_edge.source_side]}__{src_edge.id}" if src_edge.source_side is not None else None
                tp = f"{src_edge.target}__in__{_SIDE[src_edge.target_side]}__{src_edge.id}" if src_edge.target_side is not None else None
                routes.append(BackendRoute(edge_id=eid, source=src_edge.source, target=src_edge.target, points=pts, routing_style=RoutingStyle.ORTHOGONAL, source_port=sp, target_port=tp))
            if {n.id for n in nodes} != node_ids:
                raise GraphLayoutBackendError("ELK output missing node")
            if {r.edge_id for r in routes} != edge_ids:
                raise GraphLayoutBackendError("ELK output missing edge")
            return BackendLayoutResult(nodes=sorted(nodes, key=lambda n: n.id), routes=sorted(routes, key=lambda r: r.edge_id), backend=GraphBackendKind.ELK, diagnostics={"elkjs_version": REQUIRED_ELKJS_VERSION})
        except GraphLayoutBackendError:
            raise
        except Exception as exc:
            raise GraphLayoutBackendError("ELK returned malformed output") from exc
