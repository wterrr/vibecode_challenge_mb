"""LearnFlow V2 structured error definitions."""

from typing import Any


class LearnFlowV2Error(Exception):
    """Base error for all LearnFlow V2 domain and semantic operations."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


class ConceptRegistryCollisionError(LearnFlowV2Error):
    """Raised when registering a concept that collides with an existing ID, canonical key, or alias."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("CONCEPT_REGISTRY_COLLISION", message, details)


class ConceptRegistryUnknownRefError(LearnFlowV2Error):
    """Raised when a concept reference or alias cannot be resolved."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("CONCEPT_REGISTRY_UNKNOWN_REF", message, details)


class SceneGraphUnknownConceptRefError(LearnFlowV2Error):
    """Raised when a SceneGraph node references an unknown concept in the registry."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("SCENEGRAPH_UNKNOWN_CONCEPT_REF", message, details)


class SceneGraphSemanticKeyMismatchError(LearnFlowV2Error):
    """Raised when a node semantic_key does not match its concept_ref canonical_key."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("SCENEGRAPH_SEMANTIC_KEY_MISMATCH", message, details)


class SceneGraphIncompleteSemanticIdentityError(LearnFlowV2Error):
    """Raised when a SceneNode specifies concept_ref without semantic_key or vice versa."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("SCENEGRAPH_INCOMPLETE_SEMANTIC_IDENTITY", message, details)


class SceneGraphDuplicateNodeIdError(LearnFlowV2Error):
    """Raised when duplicate node IDs exist within a single SceneGraph."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("SCENEGRAPH_DUPLICATE_NODE_ID", message, details)


class SceneGraphInvalidRelationRefError(LearnFlowV2Error):
    """Raised when a relation references a non-existent source or target node."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("SCENEGRAPH_INVALID_RELATION_REF", message, details)


class SceneGraphInvalidGroupRefError(LearnFlowV2Error):
    """Raised when a group references a non-existent node or contains duplicate members."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("SCENEGRAPH_INVALID_GROUP_REF", message, details)


class SceneGraphDuplicateRelationIdError(LearnFlowV2Error):
    """Raised when duplicate relation IDs exist within a single SceneGraph."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("SCENEGRAPH_DUPLICATE_RELATION_ID", message, details)


class SceneGraphDuplicateGroupIdError(LearnFlowV2Error):
    """Raised when duplicate group IDs exist within a single SceneGraph."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("SCENEGRAPH_DUPLICATE_GROUP_ID", message, details)


class SceneGraphInvalidLayoutRefError(LearnFlowV2Error):
    """Raised when layout hints reference non-existent node IDs."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("SCENEGRAPH_INVALID_LAYOUT_REF", message, details)


class MeasurementInvalidInputError(LearnFlowV2Error):
    """Raised when measurement input is empty, whitespace-only, or invalid."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MEASUREMENT_INVALID_INPUT", message, details)


class MeasurementFontNotFoundError(LearnFlowV2Error):
    """Raised when a requested or fallback font cannot be found or loaded."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MEASUREMENT_FONT_NOT_FOUND", message, details)


class MeasurementAssetNotFoundError(LearnFlowV2Error):
    """Raised when a local asset file is not found on disk."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MEASUREMENT_ASSET_NOT_FOUND", message, details)


class MeasurementInvalidAssetError(LearnFlowV2Error):
    """Raised when an asset file is corrupt, unreadable, or has non-positive geometry."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MEASUREMENT_INVALID_ASSET", message, details)


class MeasurementUnsupportedNodeError(LearnFlowV2Error):
    """Raised when a node kind cannot be measured by intrinsic measurement."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MEASUREMENT_UNSUPPORTED_NODE", message, details)


class MeasurementUnsupportedMathError(LearnFlowV2Error):
    """Raised when mathematical syntax is beyond the conservative supported subset."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MEASUREMENT_UNSUPPORTED_MATH", message, details)


class LayoutInvalidInputError(LearnFlowV2Error):
    """Raised when layout compiler input is invalid or contradictory."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("LAYOUT_INVALID_INPUT", message, details)


class LayoutUnsatisfiableError(LearnFlowV2Error):
    """Raised when linear layout constraints cannot be satisfied."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("LAYOUT_UNSATISFIABLE", message, details)


class LayoutPreflightFailedError(LearnFlowV2Error):
    """Raised when a solved LayoutGraph fails preflight validation."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("LAYOUT_PREFLIGHT_FAILED", message, details)


class GraphLayoutInvalidInputError(LearnFlowV2Error):
    """Raised when V2 graph-layout input is invalid."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("GRAPH_LAYOUT_INVALID_INPUT", message, details)


class GraphLayoutBackendUnavailableError(LearnFlowV2Error):
    """Raised when a requested graph-layout backend is unavailable."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("GRAPH_LAYOUT_BACKEND_UNAVAILABLE", message, details)


class GraphLayoutBackendError(LearnFlowV2Error):
    """Raised when a graph-layout backend fails or returns malformed output."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("GRAPH_LAYOUT_BACKEND_ERROR", message, details)


class GraphLayoutUnsupportedDirectionError(LearnFlowV2Error):
    """Raised when V2-04 graph layout is requested for an unsupported direction."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("GRAPH_LAYOUT_UNSUPPORTED_DIRECTION", message, details)


class GraphLayoutUnsupportedCapabilityError(LearnFlowV2Error):
    """Raised when a backend cannot honestly provide a requested capability."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("GRAPH_LAYOUT_UNSUPPORTED_CAPABILITY", message, details)


class MotionError(LearnFlowV2Error):
    """Base error for motion grammar and motion plan operations."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, details)


class MotionGrammarIncompatibleError(MotionError):
    """Raised when a motion verb and style combination is invalid."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MOTION_GRAMMAR_INCOMPATIBLE", message, details)


class MotionUnsupportedTierError(MotionError):
    """Raised when a Tier-2/Tier-3 or unsupported verb/style/capability is used in Tier-1."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MOTION_UNSUPPORTED_TIER", message, details)


class MotionDuplicateEventIdError(MotionError):
    """Raised when duplicate event IDs exist within a MotionPlan."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MOTION_DUPLICATE_EVENT_ID", message, details)


class MotionInvalidTargetError(MotionError):
    """Raised when a motion event references an unknown target or invalid target type."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MOTION_INVALID_TARGET", message, details)


class MotionSceneMismatchError(MotionError):
    """Raised when MotionPlan scene_id does not match the SceneGraph scene_id."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MOTION_SCENE_MISMATCH", message, details)


class MotionUnsupportedSchemaVersionError(MotionError):
    """Raised when a MotionPlan has an unsupported schema version."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MOTION_UNSUPPORTED_SCHEMA_VERSION", message, details)


class MotionInvalidInputError(MotionError):
    """Raised when a MotionPlan or MotionEvent input is malformed or invalid."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MOTION_INVALID_INPUT", message, details)


class MotionBeatError(MotionError):
    """Base error for narration beat alignment and timing operations."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, details)


class MotionBeatTimingError(MotionBeatError):
    """Raised when word or phrase timing input is invalid, negative, non-finite, or malformed."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MOTION_BEAT_TIMING_ERROR", message, details)


class MotionUnknownBeatError(MotionBeatError):
    """Raised when an event trigger references a semantic beat ID not found in the beat map."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MOTION_UNKNOWN_BEAT", message, details)


class MotionBeatAmbiguityError(MotionBeatError):
    """Raised when a beat reference matches multiple ambiguous beats or aliases."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MOTION_BEAT_AMBIGUOUS", message, details)


class MotionSchedulerError(MotionError):
    """Base error for motion scheduling operations."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, details)


class MotionDependencyCycleError(MotionSchedulerError):
    """Raised when a cycle is detected in the motion event dependency DAG."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MOTION_DEPENDENCY_CYCLE", message, details)


class MotionLifecycleError(MotionSchedulerError):
    """Raised when an event violates target lifecycle (e.g. before ENTER, after EXIT, duplicate EXIT)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MOTION_LIFECYCLE_ERROR", message, details)


class MotionConflictError(MotionSchedulerError):
    """Raised when simultaneous or conflicting operations are scheduled on the same target."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MOTION_CONFLICT_ERROR", message, details)


class MotionCognitiveBudgetExceededError(MotionSchedulerError):
    """Raised when simultaneous motion count exceeds the configured cognitive budget and cannot be deferred."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MOTION_COGNITIVE_BUDGET_EXCEEDED", message, details)


class MotionScheduleTimingError(MotionSchedulerError):
    """Raised when scheduled timing violates temporal bounds or scene boundaries."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MOTION_SCHEDULE_TIMING_ERROR", message, details)


class MotionCompilerError(MotionError):
    """Base error for motion compilation operations."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, details)


class MotionCompilationError(MotionCompilerError):
    """Raised when compiling an event or property track fails or encounters unsupported grammar."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("MOTION_COMPILATION_ERROR", message, details)


class TransitionError(LearnFlowV2Error):
    """Base error for cross-scene transition planning, capabilities, and compilation."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, details)


class TransitionInvalidInputError(TransitionError):
    """Raised when transition planning inputs are invalid, malformed, or missing required registries."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("TRANSITION_INVALID_INPUT", message, details)


class TransitionUnregisteredSemanticKeyError(TransitionError):
    """Raised when a candidate persistent object semantic key is not registered in ConceptRegistry."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("TRANSITION_UNREGISTERED_SEMANTIC_KEY", message, details)


class TransitionUnsupportedCapabilityError(TransitionError):
    """Raised when a renderer backend cannot provide even minimal transition capabilities."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("TRANSITION_UNSUPPORTED_CAPABILITY", message, details)


class TransitionSemanticMismatchError(TransitionError):
    """Raised when semantic identities or scene graph topologies conflict during transition compilation."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("TRANSITION_SEMANTIC_MISMATCH", message, details)


class TransitionGeometryError(TransitionError):
    """Raised when transition source or target geometry is missing, invalid, or non-finite."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("TRANSITION_GEOMETRY_ERROR", message, details)


