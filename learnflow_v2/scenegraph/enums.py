"""Finite taxonomic enumerations for SceneGraph V2."""

from enum import Enum


class NodeKind(str, Enum):
    """Finite taxonomic kinds of visual semantic nodes."""

    TEXT = "TEXT"
    MATH = "MATH"
    CONCEPT = "CONCEPT"
    SHAPE = "SHAPE"
    IMAGE = "IMAGE"
    ICON = "ICON"
    CHART = "CHART"
    CODE = "CODE"
    GROUP = "GROUP"
    CONTAINER = "CONTAINER"
    CALLOUT = "CALLOUT"
    EQUATION = "EQUATION"


class RelationKind(str, Enum):
    """Finite taxonomic kinds of semantic relationships between nodes."""

    FLOW = "FLOW"
    CAUSES = "CAUSES"
    DEPENDS_ON = "DEPENDS_ON"
    COMPARES_WITH = "COMPARES_WITH"
    CONTRASTS_WITH = "CONTRASTS_WITH"
    PART_OF = "PART_OF"
    GROUP_WITH = "GROUP_WITH"
    LABELS = "LABELS"
    ANNOTATES = "ANNOTATES"
    TRANSFORMS_INTO = "TRANSFORMS_INTO"
    EQUIVALENT_TO = "EQUIVALENT_TO"
    SEQUENCE_BEFORE = "SEQUENCE_BEFORE"
    SEQUENCE_AFTER = "SEQUENCE_AFTER"


class ScenePurpose(str, Enum):
    """Pedagogical goal of the scene."""

    EXPLAIN = "EXPLAIN"
    INTRODUCE = "INTRODUCE"
    COMPARE = "COMPARE"
    DEMONSTRATE = "DEMONSTRATE"
    SUMMARIZE = "SUMMARIZE"
    RECAP = "RECAP"
    DRILLDOWN = "DRILLDOWN"


class LayoutIntent(str, Enum):
    """High-level semantic layout intent."""

    CONCEPT_CARD = "CONCEPT_CARD"
    PROCESS = "PROCESS"
    COMPARISON = "COMPARISON"
    ILLUSTRATION = "ILLUSTRATION"
    GRID = "GRID"
    FREEFORM = "FREEFORM"
    TIMELINE = "TIMELINE"
    HIERARCHY = "HIERARCHY"


class ReadingDirection(str, Enum):
    """Reading flow direction across the scene."""

    LEFT_TO_RIGHT = "LEFT_TO_RIGHT"
    RIGHT_TO_LEFT = "RIGHT_TO_LEFT"
    TOP_TO_BOTTOM = "TOP_TO_BOTTOM"
    BOTTOM_TO_TOP = "BOTTOM_TO_TOP"
    RADIAL = "RADIAL"
    BIDIRECTIONAL = "BIDIRECTIONAL"


class PreferredRegion(str, Enum):
    """Abstract spatial intent region. No pixel coordinates."""

    CENTER = "CENTER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    TOP_LEFT = "TOP_LEFT"
    TOP_RIGHT = "TOP_RIGHT"
    BOTTOM_LEFT = "BOTTOM_LEFT"
    BOTTOM_RIGHT = "BOTTOM_RIGHT"


class PortHint(str, Enum):
    """Abstract port connection direction. No coordinate offsets."""

    AUTO = "AUTO"
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    CENTER = "CENTER"
