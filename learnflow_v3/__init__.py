"""V3 Canonical Semantic Contracts. Only typed artifacts and validation, no renderer."""
from .models import (
    V3_SCHEMA_VERSION,
    CanonicalConceptRef, LedgerStep, ObjectKind, ObjectState,
    RepresentationType, SemanticContractError, SemanticObject, StateLedger,
    StateSource, StateSourceKind, TeachingBeat, TeachingSection,
    VisualPatternSpec, VisualTeachingConstraints, VisualTeachingPlan,
)
from .validation import validate_semantic_bundle
from .pattern_router import RouteReason, RouteStatus, VariantAttempt, VisualPatternRoute, route_visual_pattern
from .binary_search_trace import (
    BinarySearchInput, BinarySearchTrace, SearchStep, VerifiedBinarySearchProof,
    VerifiedBinarySearchRoute, make_binary_search_trace, verify_binary_search_trace,
    to_binary_search_state_ledger, verify_binary_search_ledger, certify_and_route_binary_search,
)

__all__ = [
    "V3_SCHEMA_VERSION", "CanonicalConceptRef", "LedgerStep",
    "ObjectKind", "ObjectState", "RepresentationType", "SemanticContractError",
    "SemanticObject", "StateLedger", "StateSource", "StateSourceKind",
    "TeachingBeat", "TeachingSection", "VisualPatternSpec",
    "VisualTeachingConstraints", "VisualTeachingPlan", "validate_semantic_bundle",
    "RouteReason", "RouteStatus", "VariantAttempt", "VisualPatternRoute", "route_visual_pattern",
    "BinarySearchInput", "BinarySearchTrace", "SearchStep", "VerifiedBinarySearchProof",
    "VerifiedBinarySearchRoute", "make_binary_search_trace", "verify_binary_search_trace",
    "to_binary_search_state_ledger", "verify_binary_search_ledger", "certify_and_route_binary_search",
]
