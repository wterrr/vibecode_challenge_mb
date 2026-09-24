"""Strict, immutable Pydantic schema for LearnFlow V2 layout layer.

Geometry is allowed here (downstream from SceneGraph).
All models enforce:
- extra='forbid'
- frozen=True
- Finite numeric validation (no NaN or Inf)
- Non-negative coordinates and strictly positive dimensions.
"""

from enum import Enum
import math
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from learnflow_v2.core.jsonsafe import ensure_json_safe_dict


def _check_finite_number(val: Any, name: str) -> float:
    """Ensure a value is a real Python/JSON number, not bool/string/NaN/Inf."""
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise ValueError(f"{name} must be a real finite number, got {type(val).__name__}")
    f_val = float(val)
    if not math.isfinite(f_val):
        raise ValueError(f"{name} must be a finite number, got {val}")
    return f_val

def _check_strict_int(val: Any, name: str) -> int:
    """Strict integer validator that rejects bool/string and accepts only ints."""
    if isinstance(val, bool) or not isinstance(val, int):
        raise ValueError(f"{name} must be an integer, got {type(val).__name__}")
    return val


class Rect(BaseModel):
    """2D rectangle with non-negative coordinates and strictly positive dimensions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    x: float = Field(..., ge=0.0, description="X coordinate of top-left corner")
    y: float = Field(..., ge=0.0, description="Y coordinate of top-left corner")
    width: float = Field(..., gt=0.0, description="Width of the rectangle (must be > 0)")
    height: float = Field(..., gt=0.0, description="Height of the rectangle (must be > 0)")

    @field_validator("x", "y", "width", "height", mode="before")
    @classmethod
    def validate_finite(cls, v: Any, info: Any) -> float:
        return _check_finite_number(v, info.field_name)

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return round(self.x + self.width, 4)

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return round(self.y + self.height, 4)

    @property
    def center_x(self) -> float:
        return round(self.x + self.width / 2.0, 4)

    @property
    def center_y(self) -> float:
        return round(self.y + self.height / 2.0, 4)

    def contains_point(self, px: float, py: float) -> bool:
        return self.left <= px <= self.right and self.top <= py <= self.bottom

    def contains_rect(self, other: "Rect", tol: float = 1e-4) -> bool:
        return (
            other.left >= self.left - tol
            and other.right <= self.right + tol
            and other.top >= self.top - tol
            and other.bottom <= self.bottom + tol
        )

    def intersects(self, other: "Rect", tol: float = 1e-4) -> bool:
        return not (
            other.right <= self.left + tol
            or other.left >= self.right - tol
            or other.bottom <= self.top + tol
            or other.top >= self.bottom - tol
        )


class FrameInsets(BaseModel):
    """Safe edge insets from the frame boundaries."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    top: float = Field(default=0.0, ge=0.0)
    right: float = Field(default=0.0, ge=0.0)
    bottom: float = Field(default=0.0, ge=0.0)
    left: float = Field(default=0.0, ge=0.0)

    @field_validator("top", "right", "bottom", "left", mode="before")
    @classmethod
    def validate_finite(cls, v: Any, info: Any) -> float:
        return _check_finite_number(v, info.field_name)


class LayoutZone(BaseModel):
    """Named safe region within a frame profile."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(..., min_length=1, description="Identifier of the safe zone")
    rect: Rect = Field(..., description="Rectangular boundary of the zone")
    description: str | None = Field(default=None, description="Optional semantic description")


class GridSpec(BaseModel):
    """Lightweight deterministic layout grid specification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    columns: int = Field(default=12, ge=1, description="Number of columns")
    rows: int = Field(default=6, ge=1, description="Number of rows")
    horizontal_gap: float = Field(default=16.0, ge=0.0, description="Horizontal gap between columns")
    vertical_gap: float = Field(default=16.0, ge=0.0, description="Vertical gap between rows")

    @field_validator("columns", "rows", mode="before")
    @classmethod
    def validate_strict_ints(cls, v: Any, info: Any) -> int:
        return _check_strict_int(v, info.field_name)

    @field_validator("horizontal_gap", "vertical_gap", mode="before")
    @classmethod
    def validate_finite(cls, v: Any, info: Any) -> float:
        return _check_finite_number(v, info.field_name)


class FrameProfile(BaseModel):
    """Specification of target frame dimensions, safe margins, named zones, and grid."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1, description="Profile identifier, e.g., '16:9_1280x720'")
    width: float = Field(..., gt=0.0, description="Physical frame width in pixels")
    height: float = Field(..., gt=0.0, description="Physical frame height in pixels")
    aspect_ratio: str = Field(..., description="Semantic aspect ratio, e.g. '16:9' or '9:16'")
    safe_edge_insets: FrameInsets = Field(..., description="Insets defining global safe-edge region")
    zones: dict[str, Rect] = Field(..., description="Named safe region rects")
    grid: GridSpec = Field(default_factory=GridSpec, description="Grid specification")

    @field_validator("width", "height", mode="before")
    @classmethod
    def validate_finite(cls, v: Any, info: Any) -> float:
        return _check_finite_number(v, info.field_name)

    @model_validator(mode="after")
    def validate_profile_structure(self) -> "FrameProfile":
        # Declared aspect ratio must agree with frame geometry.
        expected_ratios = {
            "16:9": 16.0 / 9.0,
            "9:16": 9.0 / 16.0,
        }
        if self.aspect_ratio in expected_ratios:
            actual = self.width / self.height
            expected = expected_ratios[self.aspect_ratio]
            # Allow equivalent scaled profiles while rejecting materially wrong ratios.
            if abs(actual - expected) > 1e-4:
                raise ValueError(
                    f"FrameProfile aspect_ratio '{self.aspect_ratio}' does not match "
                    f"dimensions {self.width}x{self.height} (actual={actual:.8f}, expected={expected:.8f})"
                )

        # Safe edge insets must define a real positive region.
        total_h_insets = self.safe_edge_insets.left + self.safe_edge_insets.right
        total_v_insets = self.safe_edge_insets.top + self.safe_edge_insets.bottom
        if total_h_insets >= self.width:
            raise ValueError(
                f"safe_edge_insets horizontal ({total_h_insets}) must be strictly less than width ({self.width})"
            )
        if total_v_insets >= self.height:
            raise ValueError(
                f"safe_edge_insets vertical ({total_v_insets}) must be strictly less than height ({self.height})"
            )

        safe = self.safe_edge_rect
        for z_name, z_rect in self.zones.items():
            if not z_name or not str(z_name).strip():
                raise ValueError("FrameProfile zone names must be non-empty strings")
            # All configured zones must be finite, positive, and inside the physical frame.
            if (
                z_rect.left < -1e-4
                or z_rect.top < -1e-4
                or z_rect.right > self.width + 1e-4
                or z_rect.bottom > self.height + 1e-4
            ):
                raise ValueError(
                    f"Zone '{z_name}' ({z_rect.left}, {z_rect.top}, {z_rect.right}, {z_rect.bottom}) "
                    f"must be inside frame ({self.width}, {self.height})"
                )
            # Safe/profile semantic zones are deliberately defined within SAFE_EDGE.
            if z_name in {
                "SAFE_EDGE",
                "SAFE_TITLE",
                "SAFE_CONTENT",
                "SAFE_CAPTION",
                "TITLE",
                "CONTENT",
                "CAPTION",
                "TOP_HOOK",
                "PRIMARY_CONTENT",
                "SUBTITLE_ZONE",
                "BOTTOM_UI_SAFE",
            } and not safe.contains_rect(z_rect, tol=1e-2):
                raise ValueError(
                    f"Zone '{z_name}' must be contained within safe_edge_rect "
                    f"({safe.left}, {safe.top}, {safe.right}, {safe.bottom})"
                )
        return self

    @property
    def safe_edge_rect(self) -> Rect:
        """The global safe-edge boundary rectangle derived from insets."""
        sx = self.safe_edge_insets.left
        sy = self.safe_edge_insets.top
        sw = self.width - (self.safe_edge_insets.left + self.safe_edge_insets.right)
        sh = self.height - (self.safe_edge_insets.top + self.safe_edge_insets.bottom)
        return Rect(x=sx, y=sy, width=sw, height=sh)

    def get_zone(self, name: str) -> Rect:
        """Retrieve a zone by name or common alias, falling back to safe_edge_rect."""
        if name in self.zones:
            return self.zones[name]
        # Normalized alias mappings
        aliases = {
            "TITLE": ["SAFE_TITLE", "TOP_HOOK"],
            "CONTENT": ["SAFE_CONTENT", "PRIMARY_CONTENT"],
            "CAPTION": ["SAFE_CAPTION", "SUBTITLE_ZONE"],
            "SAFE_TITLE": ["TITLE", "TOP_HOOK"],
            "SAFE_CONTENT": ["CONTENT", "PRIMARY_CONTENT"],
            "SAFE_CAPTION": ["CAPTION", "SUBTITLE_ZONE"],
            "TOP_HOOK": ["TITLE", "SAFE_TITLE"],
            "PRIMARY_CONTENT": ["CONTENT", "SAFE_CONTENT"],
            "SUBTITLE_ZONE": ["CAPTION", "SAFE_CAPTION"],
            "SAFE_EDGE": ["EDGE"],
        }
        for alt in aliases.get(name, []):
            if alt in self.zones:
                return self.zones[alt]
        if name == "SAFE_EDGE":
            return self.safe_edge_rect
        raise KeyError(f"Zone '{name}' not found in profile '{self.id}' (available: {list(self.zones.keys())})")


V2_LAYOUT_SCHEMA_VERSION = "2.1"


class RoutingStyle(str, Enum):
    """Finite physical edge routing representations."""

    ORTHOGONAL = "ORTHOGONAL"
    POLYLINE = "POLYLINE"
    SPLINE = "SPLINE"


class GraphBackendKind(str, Enum):
    """Finite graph-layout backend identifiers stored in artifacts."""

    ELK = "ELK"
    GRAPHVIZ = "GRAPHVIZ"


class Point(BaseModel):
    """Strict immutable 2D point for routed edge geometry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")

    @field_validator("x", "y", mode="before")
    @classmethod
    def validate_finite(cls, v: Any, info: Any) -> float:
        return _check_finite_number(v, info.field_name)


class RoutedEdge(BaseModel):
    """Replayable physical route for a semantic directed edge."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    edge_id: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    source_port: str | None = Field(default=None)
    target_port: str | None = Field(default=None)
    points: list[Point] = Field(..., min_length=2)
    routing_style: RoutingStyle = Field(...)
    backend: GraphBackendKind = Field(...)


class LayoutStrategy(str, Enum):
    """Layout strategies supported by the V2 layout artifact layer.

    V2-03 template strategies remain unchanged. V2-04 directed graph layouts use
    DIRECTED_GRAPH while their semantic graph subtype is recorded separately in
    LayoutGraph.metadata["graph_kind"] as GraphLayoutKind.
    """

    CONCEPT_CARD = "CONCEPT_CARD"
    COMPARISON = "COMPARISON"
    IMAGE_TEXT = "IMAGE_TEXT"
    QUOTE = "QUOTE"
    DIRECTED_GRAPH = "DIRECTED_GRAPH"


SIMPLE_LAYOUT_STRATEGIES = frozenset({
    LayoutStrategy.CONCEPT_CARD,
    LayoutStrategy.COMPARISON,
    LayoutStrategy.IMAGE_TEXT,
    LayoutStrategy.QUOTE,
})
"""Authoritative strategy set accepted by the simple template layout compiler."""


class LayoutBox(BaseModel):
    """Assigned placement box for a single SceneGraph node."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str = Field(..., min_length=1, description="Associated SceneNode ID")
    rect: Rect = Field(..., description="Solved bounding rectangle")
    zone: str = Field(..., description="Target layout zone or safe region")
    strategy_role: str | None = Field(default=None, description="Semantic role in layout strategy")


class LayoutGraph(BaseModel):
    """Strict, versioned, replayable LayoutGraph artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.1"] = Field(default=V2_LAYOUT_SCHEMA_VERSION, description="Layout artifact schema version")
    scene_id: str = Field(..., min_length=1, description="Source SceneGraph ID")
    frame_profile_id: str = Field(..., min_length=1, description="FrameProfile identifier")
    frame_width: float = Field(..., gt=0.0, description="Frame width")
    frame_height: float = Field(..., gt=0.0, description="Frame height")
    boxes: list[LayoutBox] = Field(default_factory=list, description="Solved node layout boxes")
    routed_edges: list[RoutedEdge] = Field(default_factory=list, description="Solved routed edge geometry")
    strategy: LayoutStrategy = Field(..., description="Layout strategy applied")
    feasible: bool = Field(default=True, description="Whether layout solver found feasible solution")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Deterministic layout metadata")

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if v != V2_LAYOUT_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported schema_version '{v}', expected '{V2_LAYOUT_SCHEMA_VERSION}'"
            )
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata_json_safe(cls, v: dict[str, Any]) -> dict[str, Any]:
        return ensure_json_safe_dict(v, path="metadata")

    @field_validator("frame_width", "frame_height", mode="before")
    @classmethod
    def validate_finite(cls, v: Any, info: Any) -> float:
        return _check_finite_number(v, info.field_name)

    @field_validator("boxes")
    @classmethod
    def validate_boxes(cls, boxes: list[LayoutBox]) -> list[LayoutBox]:
        # Enforce deterministic order by node_id
        return sorted(boxes, key=lambda b: b.node_id)

    @field_validator("routed_edges")
    @classmethod
    def validate_routed_edges(cls, edges: list[RoutedEdge]) -> list[RoutedEdge]:
        # Enforce deterministic order by edge_id
        return sorted(edges, key=lambda e: e.edge_id)
