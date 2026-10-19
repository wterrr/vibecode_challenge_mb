"""V3.0 cross-artifact validator: reuse V2 registry, graph, script and #181 guard."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Iterable

from agent_contracts.lesson import LessonScript, Storyboard
from learnflow_v2.concepts import ConceptRegistry
from learnflow_v2.scenegraph import SceneGraph, validate_scenegraph_with_registry
from live_evaluation.semantic_consistency import assert_semantic_consistency
from .models import (
    CanonicalConceptRef, SemanticContractError, StateLedger, StateSourceKind,
    VisualPatternSpec, VisualTeachingPlan,
)


def validate_semantic_bundle(
    *,
    plan: VisualTeachingPlan,
    pattern: VisualPatternSpec,
    ledger: StateLedger | None,
    registry: ConceptRegistry,
    script: LessonScript,
    storyboard: Storyboard,
    scenegraph: SceneGraph,
    verified_trace_refs: Iterable[str] = (),
) -> None:
    """Fail-closed complete semantic binding, without claiming rendered pixel proof.

    VERIFIED_TRACE is accepted only when a caller supplies an independently
    verified source ID; this function itself does not certify trace correctness.
    """
    def fail(msg: str) -> None:
        raise SemanticContractError(msg)

    def concepts(refs: Iterable[CanonicalConceptRef], label: str) -> None:
        for ref in refs:
            try:
                entry = registry.get(ref.concept_id)  # exact concept ID, never alias/fuzzy
            except Exception as exc:
                fail(f"{label}: unknown concept_ref {ref.concept_id}: {exc}")
            if entry.canonical_key != ref.canonical_key:
                fail(f"{label}: canonical key mismatch for {ref.concept_id}")

    concepts(plan.prerequisite_refs, "prerequisites")
    concepts(plan.misconception_refs, "misconceptions")
    script_ids = {seg.segment_id for seg in script.segments}
    script_segments = {seg.segment_id: seg for seg in script.segments}
    seen_beats = set()
    for beat in plan.beats:
        concepts(beat.concept_refs, "beat")
        seen_beats.update(ref.concept_id for ref in beat.concept_refs)
        if beat.script_segment_ref not in script_ids:
            fail(f"unknown script segment: {beat.script_segment_ref}")
        script_segment = script_segments[beat.script_segment_ref]
        if not set(beat.claim_refs) <= set(script_segment.claim_ids):
            fail(f"beat {beat.beat_id} claims not grounded in its script segment")
        if not set(script_segment.objective_ids) <= set(plan.learning_objective_ids):
            fail(f"script {script_segment.segment_id} objective outside plan")
    concepts(pattern.concept_refs, "pattern")
    for obj in pattern.semantic_objects:
        if obj.concept is not None:
            concepts((obj.concept,), f"object {obj.object_id}")
    if not set(pattern.objective_refs) <= set(plan.learning_objective_ids):
        fail("pattern refers to unknown objective")
    if not set(c.concept_id for c in pattern.concept_refs) <= seen_beats:
        fail("pattern concepts are not taught in its beats")
    if not set(o.concept.concept_id for o in pattern.semantic_objects if o.concept) <= set(
        c.concept_id for c in pattern.concept_refs
    ):
        fail("semantic object concept not in pattern")
    expected_script_sources = {f"script:{b.script_segment_ref}" for b in plan.beats}
    if not expected_script_sources <= set(pattern.source_refs):
        fail("pattern missing script sources for teaching beats")
    for ref in pattern.source_refs:
        if ref.startswith("script:") and ref[len("script:"):] not in script_ids:
            fail(f"pattern unknown script source: {ref}")
    if pattern.state_source.kind == StateSourceKind.VERIFIED_TRACE:
        if ledger is None:
            fail("verified trace requires a state ledger")
        if pattern.state_source.ref not in set(verified_trace_refs):
            fail("trace provenance unverified")
    elif ledger is not None and ledger.source_ref != pattern.state_source.ref:
        fail("static ledger source differs from pattern")
    if ledger is not None:
        if ledger.pattern_ref != pattern.pattern_id or ledger.source_ref != pattern.state_source.ref:
            fail("state ledger/pattern source mismatch")
        if {x.object_id for x in pattern.semantic_objects} != {
            x.object_id for x in ledger.steps[0].object_states
        }:
            fail("state ledger object identity coverage mismatch")
        beat_order = {b.beat_id: i for i, b in enumerate(plan.beats)}
        observed = []
        for step in ledger.steps:
            if step.beat_ref not in beat_order:
                fail(f"orphan ledger beat: {step.beat_ref}")
            observed.append(beat_order[step.beat_ref])
        if observed != sorted(observed):
            fail("ledger step causality order broken")
        dynamic_beats = {b.beat_id for b in plan.beats if b.expected_visible_state_change}
        if not dynamic_beats <= {x.beat_ref for x in ledger.steps}:
            fail("dynamic teaching beat missing ledger state step")
    if pattern.scene_id != scenegraph.scene_id:
        fail("pattern and SceneGraph scene identity mismatch")
    try:
        validate_scenegraph_with_registry(scenegraph, registry)
        storyboard.validate_against_script(script)
    except Exception as exc:
        fail(f"frozen V2 graph/storyboard validation: {exc}")
    scenes = {s.scene_id: s for s in storyboard.scenes}
    scene = scenes.get(pattern.scene_id)
    if scene is None:
        fail("pattern scene absent in storyboard")
    if set(scene.concept_refs) != {c.concept_id for c in pattern.concept_refs}:
        fail("storyboard/pattern concept coverage mismatch")
    if set(scene.script_segment_ids) != {b.script_segment_ref for b in plan.beats}:
        fail("storyboard/plan script coverage mismatch")
    graph_refs = {n.concept_ref for n in scenegraph.nodes if n.concept_ref is not None}
    if graph_refs != {c.concept_id for c in pattern.concept_refs}:
        fail("SceneGraph/pattern concept coverage mismatch")
    # Reuse the existing, intentionally narrow numeric worked-example drift
    # validator; no claim of proof for arbitrary natural-language meaning.
    try:
        assert_semantic_consistency(SimpleNamespace(
            concept_registry=registry.to_schema(),
            lesson_script=script,
            storyboard=storyboard,
            scenegraphs=(scenegraph,),
        ))
    except Exception as exc:
        fail(f"existing numeric worked-example gate: {exc}")
