"""Base interfaces and data structures for scene visual rendering."""

from abc import ABC, abstractmethod
from pathlib import Path
from pydantic import BaseModel, Field

from app.domain.lesson import ScenePlan
from app.domain.timeline import ResolvedSceneTiming


class RenderResult(BaseModel):
    """Result of rendering a visual scene to video."""

    path: str
    width: int
    height: int
    duration_seconds: float
    warnings: list[str] = Field(default_factory=list)


class SceneRenderer(ABC):
    """Abstract interface for rendering a ScenePlan into a video segment."""

    @abstractmethod
    async def render(
        self,
        scene: ScenePlan,
        timing: ResolvedSceneTiming,
        output_path: Path,
    ) -> RenderResult:
        """Render the scene visuals to an MP4 video file at output_path."""
        ...
