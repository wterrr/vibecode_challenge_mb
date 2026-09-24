#!/usr/bin/env python3
"""Strict local V2-04 graph backend capability preflight.

This script is the V2 graph capability gate only; it does not wire V2 into app.
Any FAIL or SKIP is a non-zero exit.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learnflow_v2.layout.backends.elk import (
    ELKJS_REQUIRED_MESSAGE,
    REQUIRED_ELKJS_VERSION,
    elkjs_bundled_import_available,
    is_available as elk_available,
    elkjs_version,
)
from learnflow_v2.layout.backends.graphviz import is_available as dot_available, dot_version
from learnflow_v2.layout.graph import layout_directed_graph
from learnflow_v2.layout.profiles import create_frame_profile_16_9
from learnflow_v2.layout.schema import GraphBackendKind
from learnflow_v2.scenegraph.enums import NodeKind, RelationKind
from learnflow_v2.scenegraph.schema import SceneGraph, SceneNode, SceneRelation


def _scene() -> SceneGraph:
    return SceneGraph(
        scene_id="v2_graph_smoke",
        nodes=[
            SceneNode(id="a", kind=NodeKind.CONCEPT, label="A"),
            SceneNode(id="b", kind=NodeKind.CONCEPT, label="B"),
        ],
        relations=[SceneRelation(id="e1", source="a", target="b", kind=RelationKind.FLOW)],
    )


def _measurements() -> dict[str, tuple[float, float]]:
    return {"a": (120.0, 60.0), "b": (120.0, 60.0)}


def main() -> int:
    ok = True
    node = shutil.which("node")
    node_ok = bool(node)
    print(f"Node                 {'PASS' if node_ok else 'FAIL'}")
    ok = ok and node_ok

    version = elkjs_version()
    bundled_ok = elkjs_bundled_import_available()
    elk_ok = node_ok and version == REQUIRED_ELKJS_VERSION and bundled_ok and elk_available()
    elk_label = f"elkjs {REQUIRED_ELKJS_VERSION}"
    if elk_ok:
        print(f"{elk_label:<20} PASS ({version})")
    else:
        detail = f" ({version or 'not found'}; {ELKJS_REQUIRED_MESSAGE})"
        print(f"{elk_label:<20} FAIL{detail}")
    ok = ok and elk_ok

    dot_ok = dot_available()
    dv = dot_version()
    print(f"Graphviz             {'PASS' if dot_ok else 'FAIL'}" + (f" ({dv})" if dv else ""))
    ok = ok and dot_ok

    scene = _scene()
    profile = create_frame_profile_16_9()
    if elk_ok:
        try:
            lg = layout_directed_graph(scene, _measurements(), profile, GraphBackendKind.ELK)
            smoke_ok = len(lg.boxes) == 2 and len(lg.routed_edges) == 1
            print(f"ELK smoke graph       {'PASS' if smoke_ok else 'FAIL'}")
            ok = ok and smoke_ok
        except Exception as exc:
            print(f"ELK smoke graph       FAIL ({type(exc).__name__}: {exc})")
            ok = False
    else:
        print(f"ELK smoke graph       FAIL ({ELKJS_REQUIRED_MESSAGE})")
        ok = False

    if dot_ok:
        try:
            lg = layout_directed_graph(scene, _measurements(), profile, GraphBackendKind.GRAPHVIZ, strict_orthogonal=False)
            smoke_ok = len(lg.boxes) == 2 and len(lg.routed_edges) == 1
            print(f"Graphviz smoke graph  {'PASS' if smoke_ok else 'FAIL'}")
            ok = ok and smoke_ok
        except Exception as exc:
            print(f"Graphviz smoke graph  FAIL ({type(exc).__name__}: {exc})")
            ok = False
    else:
        print("Graphviz smoke graph  FAIL")
        ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
