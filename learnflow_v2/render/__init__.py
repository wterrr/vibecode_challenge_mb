"""Deterministic pixel/video renderer for LearnFlow V2."""

from learnflow_v2.render.assembly import assemble_video, mux_audio_track
from learnflow_v2.render.backend import (
    DeterministicPillowRenderer,
    render_scene_video,
    render_transition_video,
)
from learnflow_v2.render.errors import RenderBackendError, RenderError, RenderInvalidInputError
from learnflow_v2.render.schema import (
    RenderArtifactKind,
    RenderProfile,
    RenderedArtifact,
    V2_RENDER_SCHEMA_VERSION,
)

__all__ = [
    "DeterministicPillowRenderer",
    "RenderArtifactKind",
    "RenderBackendError",
    "RenderError",
    "RenderInvalidInputError",
    "RenderProfile",
    "RenderedArtifact",
    "V2_RENDER_SCHEMA_VERSION",
    "assemble_video",
    "mux_audio_track",
    "render_scene_video",
    "render_transition_video",
]
