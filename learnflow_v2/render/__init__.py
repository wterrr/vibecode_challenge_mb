"""Deterministic renderer boundary for LearnFlow V2."""

from learnflow_v2.render.backend import RendererBackend
from learnflow_v2.render.errors import RenderAssemblyError, RenderBackendError, RenderError, RenderInvalidInputError
from learnflow_v2.render.schema import (
    FrameRenderDigest,
    RenderBackendKind,
    RenderedScene,
    RenderedVideo,
    RendererCapabilities,
    TextRenderEvidence,
    V2_RENDER_SCHEMA_VERSION,
)

__all__ = [
    "FrameRenderDigest",
    "RenderAssemblyError",
    "RenderBackend",
    "RenderBackendKind",
    "RenderBackendError",
    "RenderError",
    "RenderInvalidInputError",
    "RenderedScene",
    "RenderedVideo",
    "RendererCapabilities",
    "TextRenderEvidence",
    "V2_RENDER_SCHEMA_VERSION",
]
from learnflow_v2.render.assembly import assemble_rendered_scenes
from learnflow_v2.render.pillow_ffmpeg import PillowFFmpegRenderer

__all__ += ["PillowFFmpegRenderer", "assemble_rendered_scenes"]
