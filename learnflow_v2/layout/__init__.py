"""LearnFlow V2 Layout subsystem (intrinsic measurement + constraint layout)."""

from learnflow_v2.layout.constraints import (
    LayoutItemInput,
    solve_layout,
)
from learnflow_v2.layout.measurement import (
    AssetMeasurement,
    IconMeasurement,
    IntrinsicSize,
    MathMeasurement,
    MeasurementPolicy,
    TextMeasurement,
    WrapCandidate,
    measure_asset,
    measure_icon,
    measure_math,
    measure_node,
    measure_text,
    resolve_font_path,
)
from learnflow_v2.layout.preflight import (
    PreflightReport,
    GraphPreflightReport,
    validate_layout_graph,
    validate_graph_layout,
)
from learnflow_v2.layout.profiles import (
    PROFILE_16_9,
    PROFILE_9_16,
    create_frame_profile_16_9,
    create_frame_profile_9_16,
    get_frame_profile,
)
from learnflow_v2.layout.schema import (
    FrameInsets,
    FrameProfile,
    GridSpec,
    LayoutBox,
    LayoutGraph,
    LayoutStrategy,
    SIMPLE_LAYOUT_STRATEGIES,
    LayoutZone,
    Point,
    RoutedEdge,
    RoutingStyle,
    GraphBackendKind,
    Rect,
)

from learnflow_v2.layout.collision import (
    CollisionPair,
    SeparationAxis,
    SeparationOrdering,
    SeparationConstraint,
    detect_box_collisions,
    choose_separation_constraint,
)
from learnflow_v2.layout.score import (
    LayoutFeasibilityReport,
    SoftLayoutScore,
    SoftScoreWeights,
    evaluate_feasibility,
    compute_soft_score,
)
from learnflow_v2.layout.optimization import (
    MAX_LAYOUT_SOLVES,
    LayoutCandidate,
    LayoutOptimizationResult,
    choose_best_candidate,
    optimize_simple_layout,
    evaluate_graph_candidate,
)

__all__ = [
    # Measurement
    "AssetMeasurement",
    "IconMeasurement",
    "IntrinsicSize",
    "MathMeasurement",
    "MeasurementPolicy",
    "TextMeasurement",
    "WrapCandidate",
    "measure_asset",
    "measure_icon",
    "measure_math",
    "measure_node",
    "measure_text",
    "resolve_font_path",
    # Schema
    "Rect",
    "FrameInsets",
    "LayoutZone",
    "GridSpec",
    "FrameProfile",
    "LayoutStrategy",
    "SIMPLE_LAYOUT_STRATEGIES",
    "LayoutBox",
    "LayoutGraph",
    # Profiles
    "PROFILE_16_9",
    "PROFILE_9_16",
    "create_frame_profile_16_9",
    "create_frame_profile_9_16",
    "get_frame_profile",
    # Constraints
    "LayoutItemInput",
    "solve_layout",
    # Preflight
    "PreflightReport",
    "validate_layout_graph",
    "build_graph_layout_input",
    "layout_directed_graph",
    "LayoutDirection",
    "GraphLayoutKind",
    "validate_graph_layout",
    "GraphPreflightReport",
    "GraphBackendKind",
    "RoutingStyle",
    "RoutedEdge",
    "Point",
    # Collision (V2-05)
    "CollisionPair",
    "SeparationAxis",
    "SeparationOrdering",
    "SeparationConstraint",
    "detect_box_collisions",
    "choose_separation_constraint",
    # Score & Feasibility (V2-05)
    "LayoutFeasibilityReport",
    "SoftLayoutScore",
    "SoftScoreWeights",
    "evaluate_feasibility",
    "compute_soft_score",
    # Optimization & Candidates (V2-05)
    "MAX_LAYOUT_SOLVES",
    "LayoutCandidate",
    "LayoutOptimizationResult",
    "choose_best_candidate",
    "optimize_simple_layout",
    "evaluate_graph_candidate",
]

from learnflow_v2.layout.graph import GraphLayoutKind, LayoutDirection, layout_directed_graph, build_graph_layout_input
