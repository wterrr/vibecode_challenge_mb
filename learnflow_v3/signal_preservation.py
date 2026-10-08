"""V3-03: fail-closed semantic signal audit and dependency fingerprints.

Reuses frozen V2 hash primitives and V3-02 semantic gate. This is NOT a
renderer, trace oracle or proof that any video frame consumes these signals.
"""
from __future__ import annotations

from enum import Enum
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agent_contracts.lesson import LessonScript, Storyboard
from learnflow_v2.concepts import ConceptRegistry
from learnflow_v2.repair import compute_content_hash
from learnflow_v2.scenegraph import SceneGraph
from .models import SemanticContractError, StateLedger, VisualPatternSpec, VisualTeachingPlan
from .validation import validate_semantic_bundle

SIGNAL_AUDIT_VERSION = "3.0.3"
SEMANTIC_GATE_CONSUMER = "v3.semantic_bundle_validation"

# Every leaf of a V3.0 artifact must have an explicit decision. These patterns
# are exact normalized paths (list indices -> "*"). No catch-all rule.
GATED_PATHS = frozenset((
    "plan.schema_version",
    "plan.learning_objective_ids.*",
    "plan.prerequisite_refs",
    "plan.prerequisite_refs.*.concept_id",
    "plan.prerequisite_refs.*.canonical_key",
    "plan.misconception_refs",
    "plan.misconception_refs.*.concept_id",
    "plan.misconception_refs.*.canonical_key",
    "plan.sections.*.section_id",
    "plan.sections.*.objective_refs.*",
    "plan.beats.*.beat_id",
    "plan.beats.*.section_ref",
    "plan.beats.*.script_segment_ref",
    "plan.beats.*.claim_refs",
    "plan.beats.*.claim_refs.*",
    "plan.beats.*.concept_refs",
    "plan.beats.*.concept_refs.*.concept_id",
    "plan.beats.*.concept_refs.*.canonical_key",
    "pattern.schema_version",
    "pattern.pattern_id",
    "pattern.scene_id",
    "pattern.objective_refs.*",
    "pattern.source_refs.*",
    "pattern.concept_refs.*.concept_id",
    "pattern.concept_refs.*.canonical_key",
    "pattern.state_source.kind",
    "pattern.state_source.ref",
    "pattern.semantic_objects.*.object_id",
    "pattern.semantic_objects.*.concept",
    "pattern.semantic_objects.*.concept.concept_id",
    "pattern.semantic_objects.*.concept.canonical_key",
    "pattern.semantic_objects.*.state_ref",
    "ledger.schema_version",
    "ledger.pattern_ref",
    "ledger.source_ref",
    "ledger.steps.*.step_id",
    "ledger.steps.*.beat_ref",
    "ledger.steps.*.object_states.*.object_id",
))

# Declared but NOT meaningfully consumed by a downstream adapter yet. Future
# owners are explicit, and the release/compile guard refuses these paths.
DEFERRED_PATHS = {
    "plan.lesson_id": "future:lesson-identity",
    "plan.sections.*.learner_state_before": "future:pedagogy-planner",
    "plan.sections.*.learner_state_after": "future:pedagogy-planner",
    "plan.sections.*.visual_teaching_goal": "future:visual-director",
    "plan.sections.*.representation_options.*": "future:pattern-router",
    "plan.sections.*.visual_complexity_budget": "future:pattern-router",
    "plan.sections.*.hero_candidate": "future:hero-planner",
    "plan.beats.*.expected_visible_state_change": "future:beat-visual-binding",
    "plan.beats.*.allowed_static_justification": "future:static-exception-proof",
    "plan.beats.*.importance": "future:beat-grounding",
    "plan.constraints.language": "future:pedagogy-planner",
    "plan.constraints.learner_level": "future:pedagogy-planner",
    "plan.constraints.target_duration_minutes": "future:pedagogy-planner",
    "plan.constraints.cognitive_load_tier": "future:pedagogy-planner",
    "plan.constraints.accessibility": "future:accessibility-gate",
    "plan.constraints.accessibility.*": "future:accessibility-gate",
    "pattern.pattern_type": "future:pattern-router",
    "pattern.semantic_objects.*.kind": "future:specialized-renderer",
    "pattern.visual_constraints": "future:layout-compiler",
    "pattern.fallback_family": "future:pattern-router",
    "pattern.fallback_family.*": "future:pattern-router",
    "pattern.renderer_requirement": "future:render-backend-selector",
    "ledger.ledger_id": "future:artifact-provenance",
    "ledger.steps.*.object_states.*.properties": "future:stateful-renderer",
}
if GATED_PATHS & DEFERRED_PATHS.keys():
    raise RuntimeError("ambiguous V3 signal policy")


class SignalStatus(str, Enum):
    SEMANTIC_GATED = "SEMANTIC_GATED"
    DECLARED_UNCONSUMED = "DECLARED_UNCONSUMED"


class SignalRoute(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    normalized_path: str
    status: SignalStatus
    consumer: str
    source_value_hash: str


class SignalAudit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: str = SIGNAL_AUDIT_VERSION
    assurance: str = "SEMANTIC_GATE_ONLY_NO_PIXEL_PROOF"
    routes: tuple[SignalRoute, ...]
    source_hashes: dict[str, str]
    semantic_gate_hash: str
    audit_hash: str
    render_ready: bool = False

    @property
    def declared_unconsumed_paths(self) -> tuple[str, ...]:
        return tuple(x.path for x in self.routes if x.status == SignalStatus.DECLARED_UNCONSUMED)

    def require_render_consumption(self) -> None:
        if self.declared_unconsumed_paths:
            raise SemanticContractError(
                "DEAD_SIGNAL_BLOCKED: no verified downstream consumer for "
                + ", ".join(self.declared_unconsumed_paths)
            )
        # This checkpoint does not have a renderer adapter, even if the
        # future policy table eventually classifies all fields.
        raise SemanticContractError("NO_RENDERER_CONSUMPTION_PROOF")


def _iter_leaves(value: Any, path: str):
    """Emit scalar leaves and empty containers; preserve opaque state blobs."""
    if path.endswith((".properties", ".visual_constraints")):
        yield path, value
    elif isinstance(value, dict):
        if not value:
            yield path, value
        else:
            for key in sorted(value):
                yield from _iter_leaves(value[key], f"{path}.{key}")
    elif isinstance(value, list):
        if not value:
            yield path, value
        else:
            for i, item in enumerate(value):
                yield from _iter_leaves(item, f"{path}.{i}")
    else:
        yield path, value


def _canonical_path(path: str) -> str:
    return re.sub(r"(?<=\.)\d+(?=\.|$)", "*", path)


def _route(path: str, value: Any) -> SignalRoute:
    normalized = _canonical_path(path)
    if normalized in GATED_PATHS:
        status, consumer = SignalStatus.SEMANTIC_GATED, SEMANTIC_GATE_CONSUMER
    elif normalized in DEFERRED_PATHS:
        status, consumer = SignalStatus.DECLARED_UNCONSUMED, DEFERRED_PATHS[normalized]
    else:
        raise SemanticContractError(f"UNDECLARED_SEMANTIC_SIGNAL: {path}")
    return SignalRoute(
        path=path, normalized_path=normalized, status=status,
        consumer=consumer, source_value_hash=compute_content_hash({"value": value}),
    )


def audit_signal_preservation(
    *,
    plan: VisualTeachingPlan,
    pattern: VisualPatternSpec,
    ledger: StateLedger | None,
    registry: ConceptRegistry,
    script: LessonScript,
    storyboard: Storyboard,
    scenegraph: SceneGraph,
    verified_trace_refs: tuple[str, ...] = (),
) -> SignalAudit:
    """Require V3-02 semantic gate, then audit every V3 semantic leaf.

    Gated downstream fingerprint excludes deferred fields by construction.
    Any deferred mutation changes source/audit fingerprints but DOES NOT claim
    that a renderer consumed the value; render-ready always remains False.
    """
    if ledger is None:
        raise SemanticContractError("STATE_LEDGER_REQUIRED_FOR_SIGNAL_AUDIT")
    validate_semantic_bundle(
        plan=plan, pattern=pattern, ledger=ledger, registry=registry,
        script=script, storyboard=storyboard, scenegraph=scenegraph,
        verified_trace_refs=verified_trace_refs,
    )
    roots: dict[str, Any] = {"plan": plan, "pattern": pattern, "ledger": ledger}
    leaf_values: dict[str, Any] = {}
    for name, obj in roots.items():
        for path, value in _iter_leaves(obj.model_dump(mode="json"), name):
            if path in leaf_values:
                raise SemanticContractError(f"DUPLICATE_SIGNAL_PATH: {path}")
            leaf_values[path] = value
    routes = tuple(_route(path, leaf_values[path]) for path in sorted(leaf_values))
    if not routes or not any(r.status == SignalStatus.SEMANTIC_GATED for r in routes):
        raise SemanticContractError("SEMANTIC_GATE_HAS_NO_CONSUMED_FIELDS")

    # Reuse V2's deterministic content hash, but never treat a blanket input
    # hash change as proof that a renderer consumed an otherwise dead field.
    source_hashes = {
        "plan": compute_content_hash(plan),
        "pattern": compute_content_hash(pattern),
        "ledger": compute_content_hash(ledger),
        "registry": compute_content_hash(registry.to_schema()),
        "script": compute_content_hash(script),
        "storyboard": compute_content_hash(storyboard),
        "scenegraph": compute_content_hash(scenegraph),
        "verified_trace_refs": compute_content_hash(sorted(set(verified_trace_refs))),
    }
    semantic_gate_hash = compute_content_hash({
        "compiler_version": SIGNAL_AUDIT_VERSION,
        "consumer": SEMANTIC_GATE_CONSUMER,
        "gated_inputs": [
            (r.path, r.source_value_hash)
            for r in routes if r.status == SignalStatus.SEMANTIC_GATED
        ],
        "v2_references": {
            key: source_hashes[key]
            for key in ("registry", "script", "storyboard", "scenegraph", "verified_trace_refs")
        },
    })
    audit_hash = compute_content_hash({
        "version": SIGNAL_AUDIT_VERSION,
        "source_hashes": source_hashes,
        "semantic_gate_hash": semantic_gate_hash,
        "classified_inputs": [
            (r.path, r.status.value, r.consumer, r.source_value_hash)
            for r in routes
        ],
        "render_ready": False,
    })
    return SignalAudit(
        routes=routes, source_hashes=source_hashes,
        semantic_gate_hash=semantic_gate_hash,
        audit_hash=audit_hash,
    )


def assert_mutation_invalidation(before: SignalAudit, after: SignalAudit) -> tuple[str, ...]:
    """Verify a changed leaf impacts its declared stage, or is blocked as unused."""
    old = {x.path: x for x in before.routes}
    new = {x.path: x for x in after.routes}
    altered = tuple(sorted(
        key for key in old.keys() | new.keys()
        if old.get(key) != new.get(key)
    ))
    if not altered and before.source_hashes != after.source_hashes:
        # Changes in original V2 artifacts are also tracked, not silently
        # reusable without validating their semantic gate fingerprint.
        if before.semantic_gate_hash == after.semantic_gate_hash:
            raise SemanticContractError("STALE_CROSS_ARTIFACT_GATE_HASH")
    if not altered:
        raise SemanticContractError("NO_SEMANTIC_MUTATION_DETECTED")
    changed_gated = any(
        (old.get(k) is not None and old[k].status == SignalStatus.SEMANTIC_GATED)
        or (new.get(k) is not None and new[k].status == SignalStatus.SEMANTIC_GATED)
        for k in altered
    )
    if before.audit_hash == after.audit_hash:
        raise SemanticContractError("STALE_AUDIT_HASH")
    if changed_gated and before.semantic_gate_hash == after.semantic_gate_hash:
        raise SemanticContractError("STALE_SEMANTIC_GATE_FINGERPRINT")
    if not changed_gated:
        for k in altered:
            for r in (old.get(k), new.get(k)):
                if r is not None and r.status != SignalStatus.DECLARED_UNCONSUMED:
                    raise SemanticContractError("UNROUTED_SEMANTIC_SIGNAL")
        # Deferred changes may leave SEMANTIC_GATE hash unchanged, but neither
        # before nor after can ever be declared render-ready.
        if before.render_ready or after.render_ready:
            raise SemanticContractError("DEAD_SIGNAL_SILENTLY_ACCEPTED")
    return altered
