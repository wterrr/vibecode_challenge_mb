"""Deterministic lesson-wide concept identity for Visual Director."""

from __future__ import annotations

from agent_contracts import PedagogyPlan
from learnflow_v2.concepts import (
    ConceptEntry,
    ConceptRegistry,
    deterministic_concept_id,
    normalize_canonical_key,
)


def build_visual_concept_registry(pedagogy: PedagogyPlan) -> ConceptRegistry:
    """Build canonical identities before Hermes creates any SceneGraph.

    Visual Director receives this registry as immutable context. It does not invent
    concept IDs or canonical semantic keys scene-by-scene.
    """

    registry = ConceptRegistry()
    for concept in pedagogy.concept_order:
        canonical_key = normalize_canonical_key(concept)
        registry.register(
            ConceptEntry(
                concept_id=deterministic_concept_id(canonical_key),
                canonical_key=canonical_key,
                label=concept,
                provenance=f"pedagogy:{pedagogy.plan_id}",
            )
        )
    return registry
