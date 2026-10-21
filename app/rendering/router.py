"""Router registry mapping VisualIntent enums to specialized SceneRenderer instances."""

from app.domain.enums import VisualIntent
from app.providers.image.base import ImageProvider
from app.rendering.base import SceneRenderer
from app.rendering.comparison import ComparisonRenderer
from app.rendering.concept_card import ConceptCardRenderer
from app.rendering.illustration import IllustrationRenderer
from app.rendering.function_graph import FunctionGraphRenderer
from app.rendering.array_trace import ArrayTraceRenderer
from app.rendering.code2video_scene import Code2VideoSceneRenderer
from app.rendering.central_force_motion import CentralForceMotionRenderer
from app.rendering.process_diagram import ProcessDiagramRenderer


class RendererRouter:
    """Dispatches scene rendering based purely on typed VisualIntent without domain branching."""

    def __init__(
        self,
        concept_renderer: SceneRenderer | None = None,
        process_renderer: SceneRenderer | None = None,
        comparison_renderer: SceneRenderer | None = None,
        illustration_renderer: SceneRenderer | None = None,
        graph_renderer: SceneRenderer | None = None,
        array_renderer: SceneRenderer | None = None,
        central_force_renderer: SceneRenderer | None = None,
        code2video_renderer: SceneRenderer | None = None,
        image_provider: ImageProvider | None = None,
        enable_image_generation: bool = False,
    ):
        default_illustration = illustration_renderer or IllustrationRenderer(
            image_provider=image_provider,
            enable_image_generation=enable_image_generation,
        )
        self._registry: dict[VisualIntent, SceneRenderer] = {
            VisualIntent.CONCEPT_CARD: concept_renderer or ConceptCardRenderer(),
            VisualIntent.PROCESS_DIAGRAM: process_renderer or ProcessDiagramRenderer(),
            VisualIntent.COMPARISON: comparison_renderer or ComparisonRenderer(),
            VisualIntent.ILLUSTRATION: default_illustration,
            VisualIntent.FUNCTION_GRAPH: graph_renderer or FunctionGraphRenderer(),
            VisualIntent.ARRAY_TRACE: array_renderer or ArrayTraceRenderer(),
            VisualIntent.CENTRAL_FORCE_MOTION: central_force_renderer or CentralForceMotionRenderer(),
            VisualIntent.CODE2VIDEO_SCENE: code2video_renderer or Code2VideoSceneRenderer(),
        }

    def get_renderer(self, intent: VisualIntent) -> SceneRenderer:
        """Retrieve the configured SceneRenderer for the given VisualIntent."""
        renderer = self._registry.get(intent)
        if not renderer:
            raise ValueError(f"No renderer registered for VisualIntent: {intent}")
        return renderer
