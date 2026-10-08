"""V3-04 semantic-only Visual Pattern Router (no renderer/MP4/LLM).

Reuse: existing VisualTeachingPlan/PatternSpec/StateLedger, V2 SceneGraph
purpose/layout enums, V3-02 cross-artifact gate and V3-03 signal audit.
No upstream source copied and no frozen V2 changes.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from learnflow_v2.repair import compute_content_hash
from learnflow_v2.scenegraph import LayoutIntent, ScenePurpose
from learnflow_v2.scenegraph.enums import NodeKind, RelationKind
from .models import (
    ObjectKind, RepresentationType, SemanticContractError, StateLedger,
    StateSourceKind, VisualPatternSpec, VisualTeachingPlan,
)
from .signal_preservation import SignalAudit, audit_signal_preservation
from visual_director.gate import validate_visual_director_output
from visual_director.models import VisualDirectorOutput

ROUTER_VERSION = "v3-04-pattern-router-v1"


class RouteStatus(str, Enum):
    SELECTED_UNRENDERABLE = "SELECTED_UNRENDERABLE"
    ABSTAIN = "ABSTAIN"


class RouteReason(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    FALLBACK_WITHIN_FAMILY = "FALLBACK_WITHIN_FAMILY"
    MULTI_SECTION_UNSUPPORTED = "MULTI_SECTION_UNSUPPORTED"
    NOT_IN_SECTION_OPTIONS = "NOT_IN_SECTION_OPTIONS"
    CROSS_FAMILY_FALLBACK = "CROSS_FAMILY_FALLBACK"
    MISMATCHED_LAYOUT_INTENT = "MISMATCHED_LAYOUT_INTENT"
    MISMATCHED_SCENE_PURPOSE = "MISMATCHED_SCENE_PURPOSE"
    DYNAMIC_EVIDENCE_MISSING = "DYNAMIC_EVIDENCE_MISSING"
    INVALID_STATE_OR_OBJECT_KINDS = "INVALID_STATE_OR_OBJECT_KINDS"
    TOO_LITTLE_VISUAL_BUDGET = "TOO_LITTLE_VISUAL_BUDGET"
    NO_SUPPORTED_VARIANT = "NO_SUPPORTED_VARIANT"


# Representations are bounded by schema from V3-02. Each fallback is within
# the exact SAME semantic family, keeps the required semantic evidence and does
# NOT silently convert dynamic teaching into a static card.
VARIANT_TABLE: dict[RepresentationType, tuple[tuple[str, int], ...]] = {
    RepresentationType.WORKED_EXAMPLE_BOARD: (("TRACE_SPOTLIGHT", 6), ("TRACE_COMPACT", 3)),
    RepresentationType.PROCESS_FLOW: (("PROCESS_NETWORK", 6), ("PROCESS_LINEAR", 3)),
    RepresentationType.EQUATION_GRAPH: (("EQUATION_SPOTLIGHT", 6), ("EQUATION_COMPACT", 3)),
    RepresentationType.CONCEPT_CARD: (("INTENTIONAL_RECAP_CARD", 1),),
}
LAYOUT_COMPATIBILITY = {
    RepresentationType.WORKED_EXAMPLE_BOARD: frozenset((LayoutIntent.PROCESS, LayoutIntent.GRID)),
    RepresentationType.PROCESS_FLOW: frozenset((LayoutIntent.PROCESS, LayoutIntent.HIERARCHY)),
    RepresentationType.EQUATION_GRAPH: frozenset((LayoutIntent.ILLUSTRATION, LayoutIntent.GRID, LayoutIntent.FREEFORM)),
    RepresentationType.CONCEPT_CARD: frozenset((LayoutIntent.CONCEPT_CARD,)),
}
PURPOSE_COMPATIBILITY = {
    RepresentationType.WORKED_EXAMPLE_BOARD: frozenset((ScenePurpose.DEMONSTRATE, ScenePurpose.DRILLDOWN)),
    RepresentationType.PROCESS_FLOW: frozenset((ScenePurpose.EXPLAIN, ScenePurpose.DEMONSTRATE)),
    RepresentationType.EQUATION_GRAPH: frozenset((ScenePurpose.EXPLAIN, ScenePurpose.DEMONSTRATE)),
    RepresentationType.CONCEPT_CARD: frozenset((ScenePurpose.RECAP, ScenePurpose.SUMMARIZE)),
}


class VariantAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    variant: str
    family: RepresentationType
    accepted: bool
    reason: RouteReason


class VisualPatternRoute(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    router_version: Literal["v3-04-pattern-router-v1"] = ROUTER_VERSION
    status: RouteStatus
    reason: RouteReason
    scene_id: str
    pattern_id: str
    representation: RepresentationType
    selected_variant: str | None = None
    fallback_used: bool = False
    attempts: tuple[VariantAttempt, ...] = ()
    source_audit_hash: str
    decision_hash: str
    render_ready: Literal[False] = False
    renderer_implementation: Literal["NOT_IMPLEMENTED"] = "NOT_IMPLEMENTED"

    @model_validator(mode="after")
    def _consistent(self):
        if self.status == RouteStatus.ABSTAIN:
            if self.selected_variant is not None or self.fallback_used:
                raise ValueError("abstention cannot select a variant")
        else:
            if not self.selected_variant or not any(
                a.accepted and a.variant == self.selected_variant and a.family == self.representation
                for a in self.attempts
            ):
                raise ValueError("route requires accepted same-family variant")
        return self

    def require_renderer(self) -> None:
        raise SemanticContractError("V3_04_NO_RENDERER_PROOF: semantic routing is never render-ready")


def _dynamic(plan: VisualTeachingPlan) -> bool:
    return any(b.expected_visible_state_change is not None for b in plan.beats)


def _static(plan: VisualTeachingPlan) -> bool:
    return all(b.allowed_static_justification for b in plan.beats)


def _semantic_reason(*, plan, pattern, ledger, scenegraph) -> RouteReason | None:
    family = pattern.pattern_type
    if len(plan.sections) != 1:
        return RouteReason.MULTI_SECTION_UNSUPPORTED
    section = plan.sections[0]
    if family not in section.representation_options:
        return RouteReason.NOT_IN_SECTION_OPTIONS
    # Do not trust cross-family fallback directives, even if they are legal
    # values of the V3-02 enum. Semantic family is never replaced by a card.
    if any(x != family for x in pattern.fallback_family):
        return RouteReason.CROSS_FAMILY_FALLBACK
    if scenegraph.layout_intent.type not in LAYOUT_COMPATIBILITY[family]:
        return RouteReason.MISMATCHED_LAYOUT_INTENT
    if scenegraph.purpose not in PURPOSE_COMPATIBILITY[family]:
        return RouteReason.MISMATCHED_SCENE_PURPOSE

    object_kinds = {o.kind for o in pattern.semantic_objects}
    if family == RepresentationType.WORKED_EXAMPLE_BOARD:
        if (
            not _dynamic(plan)
            or pattern.state_source.kind != StateSourceKind.VERIFIED_TRACE
            or ledger is None
            or len(ledger.steps) < 2
        ):
            return RouteReason.DYNAMIC_EVIDENCE_MISSING
        if ObjectKind.SEQUENCE not in object_kinds or pattern.renderer_requirement != "STATEFUL_SEQUENCE":
            return RouteReason.INVALID_STATE_OR_OBJECT_KINDS
    elif family == RepresentationType.PROCESS_FLOW:
        graph_kinds = {r.kind for r in scenegraph.relations}
        if (
            ObjectKind.PROCESS not in object_kinds
            or len(scenegraph.nodes) < 2
            or not graph_kinds.intersection((RelationKind.FLOW, RelationKind.SEQUENCE_BEFORE))
            or pattern.renderer_requirement != "PROCESS"
        ):
            return RouteReason.INVALID_STATE_OR_OBJECT_KINDS
        if _dynamic(plan):
            # No process state-renderer exists. No silent static fallback.
            return RouteReason.DYNAMIC_EVIDENCE_MISSING
        if pattern.state_source.kind != StateSourceKind.STATIC:
            return RouteReason.DYNAMIC_EVIDENCE_MISSING
    elif family == RepresentationType.EQUATION_GRAPH:
        if (
            ObjectKind.EQUATION not in object_kinds
            or not any(n.kind in (NodeKind.MATH, NodeKind.EQUATION) for n in scenegraph.nodes)
            or pattern.renderer_requirement != "MATH"
        ):
            return RouteReason.INVALID_STATE_OR_OBJECT_KINDS
        if _dynamic(plan) or pattern.state_source.kind != StateSourceKind.STATIC:
            return RouteReason.DYNAMIC_EVIDENCE_MISSING
    elif family == RepresentationType.CONCEPT_CARD:
        if (
            not _static(plan)
            or section.representation_options != (RepresentationType.CONCEPT_CARD,)
            or any(o.kind not in (ObjectKind.LABEL,) for o in pattern.semantic_objects)
            or pattern.state_source.kind != StateSourceKind.STATIC
            or pattern.renderer_requirement != "STATIC"
        ):
            return RouteReason.INVALID_STATE_OR_OBJECT_KINDS
    else:
        return RouteReason.NO_SUPPORTED_VARIANT
    return None


def _supported_topology(*, family: RepresentationType, variant: str, scenegraph) -> bool:
    """Never flatten branching semantics into a linear flow as a fallback."""
    if family != RepresentationType.PROCESS_FLOW:
        return True
    edges = [r for r in scenegraph.relations if r.kind in (
        RelationKind.FLOW, RelationKind.SEQUENCE_BEFORE,
    )]
    ins = {n.id: 0 for n in scenegraph.nodes}
    outs = {n.id: 0 for n in scenegraph.nodes}
    for rel in edges:
        outs[rel.source] += 1
        ins[rel.target] += 1
    branches = any(n > 1 for n in (*ins.values(), *outs.values()))
    if variant == "PROCESS_NETWORK":
        return branches
    if variant == "PROCESS_LINEAR":
        if branches or len(edges) != len(scenegraph.nodes) - 1:
            return False
        starts = [node for node in ins if ins[node] == 0]
        ends = [node for node in outs if outs[node] == 0]
        if len(starts) != 1 or len(ends) != 1:
            return False
        adjacency = {rel.source: rel.target for rel in edges}
        reached = {starts[0]}
        cur = starts[0]
        while cur in adjacency:
            cur = adjacency[cur]
            if cur in reached:
                return False
            reached.add(cur)
        return len(reached) == len(scenegraph.nodes) and cur == ends[0]
    return False


def route_visual_pattern(
    *,
    plan: VisualTeachingPlan,
    pattern: VisualPatternSpec,
    ledger: StateLedger,
    registry,
    script,
    storyboard,
    scenegraph,
    verified_trace_refs: tuple[str, ...] = (),
) -> VisualPatternRoute:
    """Fail closed on broken bundle; otherwise choose a bounded semantic variant.

    The input PatternSpec and relevant V2 evidence must already exist, as the
    router cannot invent trustworthy semantic objects or a V3 renderer.
    """
    # Reuse V2 Visual Director's teaching-function/purpose/semantic gate.
    # A valid SceneGraph alone need not match its storyboard scene purpose.
    visual_output = VisualDirectorOutput(storyboard=storyboard, scenegraphs=(scenegraph,))
    reviewed = validate_visual_director_output(visual_output, script=script, registry=registry)
    if not reviewed.ready_for_core:
        raise SemanticContractError(
            "V2_VISUAL_DIRECTOR_GATE_FAILED: "
            + ", ".join(issue.value for issue in reviewed.issues)
        )
    audit: SignalAudit = audit_signal_preservation(
        plan=plan, pattern=pattern, ledger=ledger, registry=registry,
        script=script, storyboard=storyboard, scenegraph=scenegraph,
        verified_trace_refs=verified_trace_refs,
    )
    family = pattern.pattern_type
    issue = _semantic_reason(plan=plan, pattern=pattern, ledger=ledger, scenegraph=scenegraph)
    attempts: list[VariantAttempt] = []
    chosen = None
    reason = issue or RouteReason.NO_SUPPORTED_VARIANT
    if issue is None:
        budget = plan.sections[0].visual_complexity_budget
        for variant, min_budget in VARIANT_TABLE[family]:
            enough_budget = budget >= min_budget
            topology_ok = _supported_topology(family=family, variant=variant, scenegraph=scenegraph)
            accepted = enough_budget and topology_ok
            attempts.append(VariantAttempt(
                variant=variant, family=family, accepted=accepted,
                reason=(RouteReason.ELIGIBLE if accepted
                        else (RouteReason.TOO_LITTLE_VISUAL_BUDGET if not enough_budget
                              else RouteReason.NO_SUPPORTED_VARIANT)),
            ))
            if accepted:
                chosen = variant
                break
        if chosen is not None:
            reason = RouteReason.FALLBACK_WITHIN_FAMILY if len(attempts) > 1 else RouteReason.ELIGIBLE
        else:
            reason = (RouteReason.TOO_LITTLE_VISUAL_BUDGET
                      if all(a.reason == RouteReason.TOO_LITTLE_VISUAL_BUDGET for a in attempts)
                      else RouteReason.NO_SUPPORTED_VARIANT)
    status = RouteStatus.SELECTED_UNRENDERABLE if chosen else RouteStatus.ABSTAIN
    fallback = bool(chosen and len(attempts) > 1)
    content = {
        "router_version": ROUTER_VERSION, "status": status.value,
        "reason": reason.value, "scene_id": pattern.scene_id,
        "pattern_id": pattern.pattern_id, "representation": family.value,
        "selected_variant": chosen, "fallback_used": fallback,
        "attempts": [x.model_dump(mode="json") for x in attempts],
        "source_audit_hash": audit.audit_hash,
        "render_ready": False, "renderer_implementation": "NOT_IMPLEMENTED",
    }
    return VisualPatternRoute(**content, decision_hash=compute_content_hash(content))
