"""LearnFlow V2 cross-scene transitions module.

Provides first-class InterSceneTransitionPlan artifact, persistent-object
transforms, renderer capability negotiation, and deterministic fallbacks.
"""

from learnflow_v2.transitions.capabilities import (
    DEFAULT_TRANSITION_CAPABILITIES,
    FULL_TRANSITION_CAPABILITIES,
    MINIMAL_TRANSITION_CAPABILITIES,
    RendererTransitionCapabilities,
    negotiate_operation_capability,
    negotiate_transition_plan,
)
from learnflow_v2.transitions.compiler import (
    DEFAULT_TRANSITION_POLICY,
    TransitionPolicy,
    compile_inter_scene_transition,
)
from learnflow_v2.transitions.schema import (
    TIER_1_TRANSITION_OPERATIONS,
    TIER_2_TRANSITION_OPERATIONS,
    V2_TRANSITION_SCHEMA_VERSION,
    InterSceneTransitionPlan,
    PersistentObjectTransition,
    TransitionOperation,
)

__all__ = [
    "DEFAULT_TRANSITION_CAPABILITIES",
    "DEFAULT_TRANSITION_POLICY",
    "FULL_TRANSITION_CAPABILITIES",
    "InterSceneTransitionPlan",
    "MINIMAL_TRANSITION_CAPABILITIES",
    "PersistentObjectTransition",
    "RendererTransitionCapabilities",
    "TIER_1_TRANSITION_OPERATIONS",
    "TIER_2_TRANSITION_OPERATIONS",
    "TransitionOperation",
    "TransitionPolicy",
    "V2_TRANSITION_SCHEMA_VERSION",
    "compile_inter_scene_transition",
    "negotiate_operation_capability",
    "negotiate_transition_plan",
]
