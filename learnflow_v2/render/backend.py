"""Renderer backend protocol for LearnFlow V2."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from learnflow_v2.layout.schema import LayoutGraph
from learnflow_v2.motion.compiler import CompiledMotionArtifact
from learnflow_v2.render.schema import RenderedScene, RendererCapabilities
from learnflow_v2.scenegraph.schema import SceneGraph


class RendererBackend(Protocol):
    @property
    def capabilities(self) -> RendererCapabilities: ...

    def render(
        self,
        *,
        scene_graph: SceneGraph,
        layout_graph: LayoutGraph,
        motion: CompiledMotionArtifact,
        output_path: Path,
        audio_path: Path | None = None,
    ) -> RenderedScene: ...
