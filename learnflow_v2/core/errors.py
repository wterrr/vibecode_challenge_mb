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
