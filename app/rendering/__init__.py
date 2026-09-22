"""Generic visual rendering engine for educational video scenes."""

from app.rendering.base import RenderResult, SceneRenderer
from app.rendering.comparison import ComparisonRenderer
from app.rendering.concept_card import ConceptCardRenderer
from app.rendering.illustration import IllustrationRenderer
from app.rendering.process_diagram import ProcessDiagramRenderer
from app.rendering.router import RendererRouter

__all__ = [
    "RenderResult",
    "SceneRenderer",
    "ConceptCardRenderer",
    "ProcessDiagramRenderer",
    "ComparisonRenderer",
    "IllustrationRenderer",
    "RendererRouter",
]
