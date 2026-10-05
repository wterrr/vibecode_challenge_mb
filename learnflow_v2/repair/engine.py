"""Selective repair planning, safe graph patches, budgets, and invalidation for CP2.13."""

from __future__ import annotations

from typing import Iterable

from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.qa.critic_schema import (
    CriticPatchOp,
    CriticPatchSuggestion,
    CriticResponse,
    CriticStatus,
    CriticTargetKind,
)
from learnflow_v2.repair.artifacts import ArtifactIndex, compute_content_hash
from learnflow_v2.repair.errors import RepairInvalidInputError, RepairRetryLimitError
from learnflow_v2.repair.schema import (
    ArtifactKind,
    InvalidationResult,
    MAX_LAYOUT_SOLVES,
    MAX_SCENE_REGENERATIONS,
    MAX_VLM_REPAIR_ROUNDS,
    RepairAction,
    RepairBudgetState,
    RepairChangeKind,
    RepairLevel,
    RepairPlan,
    RepairPlanInvalidationResult,
    RepairVerificationResult,
    REPAIR_PATCH_POLICY,
    ScenePatchResult,
)
from learnflow_v2.scenegraph.schema import LayoutHint, SceneGraph, SceneNode, SceneRelation



def classify_patch(patch: CriticPatchSuggestion) -> RepairAction:
    try:
        level, change_kind, deferred = REPAIR_PATCH_POLICY[patch.op]
    except KeyError as exc:
        raise RepairInvalidInputError(f"unsupported critic patch op '{patch.op.value}' for CP2.13") from exc
    target_ids = tuple(f"{target.kind.value}:{target.target_id}" for target in patch.targets)
    return RepairAction(
        patch_id=patch.patch_id,
        op=patch.op,
        patch=patch,
        level=level,
        change_kind=change_kind,
        target_ids=target_ids,
        deferred=deferred,
    )


def build_repair_plan(scene_id: str, critic_response: CriticResponse) -> RepairPlan:
    if not isinstance(critic_response, CriticResponse):
        raise RepairInvalidInputError("build_repair_plan requires a CriticResponse")
    critic_response = CriticResponse.model_validate(critic_response.model_dump(mode="json"))
    if critic_response.status != CriticStatus.REPAIR:
        return RepairPlan(
            scene_id=scene_id,
            actions=(),
            max_level=RepairLevel.AUTO_FIX,
            requires_scene_regeneration=False,
            fallback_required=False,
        )
    actions = tuple(classify_patch(patch) for patch in critic_response.patches)
    max_level = max((action.level for action in actions), default=RepairLevel.AUTO_FIX)
    return RepairPlan(
        scene_id=scene_id,
        actions=actions,
        max_level=max_level,
        requires_scene_regeneration=max_level >= RepairLevel.SCENE_REGENERATION_REQUEST,
        fallback_required=max_level == RepairLevel.FALLBACK,
    )


def _validated_budget(state: RepairBudgetState) -> RepairBudgetState:
    if not isinstance(state, RepairBudgetState):
        raise RepairInvalidInputError("repair budget must be a RepairBudgetState")
    return RepairBudgetState.model_validate(state.model_dump(mode="json"))


def consume_layout_solve(state: RepairBudgetState) -> RepairBudgetState:
    state = _validated_budget(state)
    if state.layout_solves >= MAX_LAYOUT_SOLVES:
        raise RepairRetryLimitError(f"MAX_LAYOUT_SOLVES={MAX_LAYOUT_SOLVES} exhausted")
    return state.model_copy(update={"layout_solves": state.layout_solves + 1})


def consume_vlm_repair_round(state: RepairBudgetState) -> RepairBudgetState:
    state = _validated_budget(state)
    if state.vlm_repair_rounds >= MAX_VLM_REPAIR_ROUNDS:
        raise RepairRetryLimitError(f"MAX_VLM_REPAIR_ROUNDS={MAX_VLM_REPAIR_ROUNDS} exhausted")
    return state.model_copy(update={"vlm_repair_rounds": state.vlm_repair_rounds + 1})


def consume_scene_regeneration(state: RepairBudgetState) -> RepairBudgetState:
    state = _validated_budget(state)
    if state.scene_regenerations >= MAX_SCENE_REGENERATIONS:
        raise RepairRetryLimitError(f"MAX_SCENE_REGENERATIONS={MAX_SCENE_REGENERATIONS} exhausted")
    return state.model_copy(update={"scene_regenerations": state.scene_regenerations + 1})


def next_repair_level(current: RepairLevel, state: RepairBudgetState) -> RepairLevel:
    if not isinstance(current, RepairLevel):
        raise RepairInvalidInputError("current repair level must be a RepairLevel")
    state = _validated_budget(state)
    if current >= RepairLevel.FALLBACK:
        return RepairLevel.FALLBACK
    candidate = RepairLevel(int(current) + 1)
    if candidate == RepairLevel.SCENE_REGENERATION_REQUEST and state.scene_regenerations >= MAX_SCENE_REGENERATIONS:
        return RepairLevel.FALLBACK
    return candidate


def _replace_node(graph: SceneGraph, node_id: str, replacement: SceneNode) -> SceneGraph:
    nodes = [replacement if node.id == node_id else node for node in graph.nodes]
    return graph.model_copy(update={"nodes": nodes})


def _replace_relation(graph: SceneGraph, relation_id: str, replacement: SceneRelation) -> SceneGraph:
    relations = [replacement if relation.id == relation_id else relation for relation in graph.relations]
    return graph.model_copy(update={"relations": relations})


def _find_node(graph: SceneGraph, node_id: str) -> SceneNode:
    for node in graph.nodes:
        if node.id == node_id:
            return node
    raise RepairInvalidInputError(f"repair patch references unknown node '{node_id}'")


def _find_relation(graph: SceneGraph, relation_id: str) -> SceneRelation:
    for relation in graph.relations:
        if relation.id == relation_id:
            return relation
    raise RepairInvalidInputError(f"repair patch references unknown relation '{relation_id}'")


def _node_target(patch: CriticPatchSuggestion) -> str:
    if len(patch.targets) != 1 or patch.targets[0].kind != CriticTargetKind.NODE:
        raise RepairInvalidInputError(f"patch '{patch.patch_id}' requires exactly one NODE target")
    return patch.targets[0].target_id


def apply_safe_scenegraph_patches(
    scene_graph: SceneGraph,
    patches: Iterable[CriticPatchSuggestion],
) -> ScenePatchResult:
    """Apply only CP2.13 graph-safe whitelist patches; keep all other patches deferred."""
    if not isinstance(scene_graph, SceneGraph):
        raise RepairInvalidInputError("apply_safe_scenegraph_patches requires a SceneGraph")
    original_json = canonical_json(scene_graph)
    graph = SceneGraph.model_validate(scene_graph.model_dump(mode="json"))
    applied: list[str] = []
    deferred: list[str] = []
    noop: list[str] = []
    change_kinds: list[RepairChangeKind] = []

    validated_patches: list[CriticPatchSuggestion] = []
    for patch in patches:
        if not isinstance(patch, CriticPatchSuggestion):
            raise RepairInvalidInputError("repair patches must be CriticPatchSuggestion instances")
        validated_patches.append(CriticPatchSuggestion.model_validate(patch.model_dump(mode="json")))
    ordered_patches = sorted(tuple(validated_patches), key=lambda patch: patch.patch_id)
    if len({patch.patch_id for patch in ordered_patches}) != len(ordered_patches):
        raise RepairInvalidInputError("patch IDs must be unique")
    conflict_keys = [
        (patch.op.value, tuple(sorted((target.kind.value, target.target_id) for target in patch.targets)))
        for patch in ordered_patches
    ]
    if len(conflict_keys) != len(set(conflict_keys)):
        raise RepairInvalidInputError("cannot apply duplicate repair operations to the same typed targets")

    for patch in ordered_patches:
        action = classify_patch(patch)
        if action.deferred:
            deferred.append(patch.patch_id)
            continue

        patch_before = canonical_json(graph)
        if patch.op == CriticPatchOp.SET_REGION:
            node_id = _node_target(patch)
            node = _find_node(graph, node_id)
            current_hint = node.layout_hint or LayoutHint()
            replacement = node.model_copy(
                update={"layout_hint": current_hint.model_copy(update={"preferred_region": patch.region})}
            )
            graph = _replace_node(graph, node_id, replacement)
        elif patch.op == CriticPatchOp.CHANGE_IMPORTANCE:
            node_id = _node_target(patch)
            node = _find_node(graph, node_id)
            current_hint = node.layout_hint or LayoutHint()
            assert patch.normalized_magnitude is not None
            importance = min(1.0, max(0.0, current_hint.importance + patch.normalized_magnitude))
            replacement = node.model_copy(
                update={"layout_hint": current_hint.model_copy(update={"importance": importance})}
            )
            graph = _replace_node(graph, node_id, replacement)
        elif patch.op == CriticPatchOp.ADD_EMPHASIS:
            node_id = _node_target(patch)
            node = _find_node(graph, node_id)
            style_refs = sorted(set(node.style_refs) | {"emphasis.high"})
            graph = _replace_node(graph, node_id, node.model_copy(update={"style_refs": style_refs}))
        elif patch.op == CriticPatchOp.REMOVE_DECORATION:
            node_id = _node_target(patch)
            node = _find_node(graph, node_id)
            style_refs = [
                style
                for style in node.style_refs
                if not (style.startswith("decoration.") or style.startswith("decorative."))
            ]
            graph = _replace_node(graph, node_id, node.model_copy(update={"style_refs": style_refs}))
        elif patch.op == CriticPatchOp.CHANGE_EDGE_STYLE:
            if len(patch.targets) != 1 or patch.targets[0].kind != CriticTargetKind.RELATION:
                raise RepairInvalidInputError(f"patch '{patch.patch_id}' requires exactly one RELATION target")
            relation_id = patch.targets[0].target_id
            relation = _find_relation(graph, relation_id)
            assert patch.semantic_value is not None
            style_refs = sorted(set(relation.style_refs) | {patch.semantic_value})
            graph = _replace_relation(graph, relation_id, relation.model_copy(update={"style_refs": style_refs}))
        else:
            deferred.append(patch.patch_id)
            change_kinds.append(action.change_kind)
            continue

        if canonical_json(graph) == patch_before:
            noop.append(patch.patch_id)
        else:
            applied.append(patch.patch_id)
            change_kinds.append(action.change_kind)

    # Re-validate copied graph through public schema, not model_copy only.
    graph = SceneGraph.model_validate(graph.model_dump(mode="json"))
    repaired_json = canonical_json(graph)
    if canonical_json(scene_graph) != original_json:
        raise RepairInvalidInputError("repair mutated source SceneGraph")

    return ScenePatchResult(
        scene_id=scene_graph.scene_id,
        original_scene_hash=compute_content_hash(scene_graph),
        repaired_scene_hash=compute_content_hash(graph),
        scene_graph=graph,
        applied_patch_ids=tuple(applied),
        deferred_patch_ids=tuple(deferred),
        noop_patch_ids=tuple(noop),
        change_kinds=tuple(change_kinds),
    )


def verify_repaired_scene(
    patch_result: ScenePatchResult,
    deterministic_report: "DeterministicQAReport",
    *,
    qa_input_scene_hash: str,
) -> RepairVerificationResult:
    from learnflow_v2.qa.schema import DeterministicQAReport

    if not isinstance(patch_result, ScenePatchResult):
        raise RepairInvalidInputError("verify_repaired_scene requires ScenePatchResult")
    if not isinstance(deterministic_report, DeterministicQAReport):
        raise RepairInvalidInputError("verify_repaired_scene requires DeterministicQAReport")
    patch_result = ScenePatchResult.model_validate(patch_result.model_dump(mode="json"))
    deterministic_report = DeterministicQAReport.model_validate(deterministic_report.model_dump(mode="json"))
    if deterministic_report.scene_id != patch_result.scene_id:
        raise RepairInvalidInputError("deterministic re-check scene_id must match repaired scene")
    return RepairVerificationResult(
        scene_id=patch_result.scene_id,
        repaired_scene_hash=patch_result.repaired_scene_hash,
        qa_input_scene_hash=qa_input_scene_hash,
        deterministic_report=deterministic_report,
        approved=deterministic_report.passed,
    )


def invalidate_for_repair_plan(index: ArtifactIndex, plan: RepairPlan) -> RepairPlanInvalidationResult:
    """Union plan-level invalidation so every stale artifact is rebuilt at most once."""
    if not isinstance(plan, RepairPlan):
        raise RepairInvalidInputError("invalidate_for_repair_plan requires a RepairPlan")
    plan = RepairPlan.model_validate(plan.model_dump(mode="json"))
    kinds = tuple(sorted({action.change_kind for action in plan.actions}, key=lambda kind: kind.value))
    roots: set[str] = set()
    invalidated: set[str] = set()
    transitions: set[str] = set()
    for kind in kinds:
        result = invalidate_for_scene_change(index, scene_id=plan.scene_id, change_kind=kind)
        roots.update(result.root_artifact_ids)
        invalidated.update(result.invalidated_artifact_ids)
        transitions.update(result.affected_transition_ids)
    return RepairPlanInvalidationResult(
        scene_id=plan.scene_id,
        change_kinds=kinds,
        root_artifact_ids=tuple(sorted(roots)),
        invalidated_artifact_ids=tuple(sorted(invalidated)),
        affected_transition_ids=tuple(sorted(transitions)),
    )


_INVALIDATION_ROOT_KIND: dict[RepairChangeKind, ArtifactKind] = {
    RepairChangeKind.GEOMETRY_ONLY: ArtifactKind.LAYOUT_GRAPH,
    RepairChangeKind.STYLE_ONLY: ArtifactKind.RENDERED_SCENE,
    RepairChangeKind.MOTION_ONLY: ArtifactKind.MOTION_PLAN,
    RepairChangeKind.NARRATION: ArtifactKind.NARRATION,
    RepairChangeKind.SCENEGRAPH_STRUCTURE: ArtifactKind.SCENE_GRAPH,
}


def invalidate_for_scene_change(
    index: ArtifactIndex,
    *,
    scene_id: str,
    change_kind: RepairChangeKind,
) -> InvalidationResult:
    root_kind = _INVALIDATION_ROOT_KIND[change_kind]
    roots = index.find(kind=root_kind, scene_id=scene_id)
    if not roots:
        raise RepairInvalidInputError(
            f"no {root_kind.value} artifact registered for scene '{scene_id}' invalidation"
        )
    root_ids = tuple(record.artifact_id for record in roots)
    invalidated = set(index.downstream_closure(root_ids, include_roots=True))

    # Style-only changes do not affect transition planning geometry, but a rendered
    # transition touching this scene may need its visual appearance refreshed.
    if change_kind == RepairChangeKind.STYLE_ONLY:
        transition_render_ids = [
            record.artifact_id
            for record in index.records
            if record.kind == ArtifactKind.RENDERED_TRANSITION
            and (record.from_scene_id == scene_id or record.to_scene_id == scene_id)
        ]
        for transition_render_id in transition_render_ids:
            invalidated.update(index.downstream_closure((transition_render_id,), include_roots=True))

    transition_ids = sorted({
        record.transition_id
        for record in index.records
        if record.artifact_id in invalidated and record.transition_id is not None
    })
    return InvalidationResult(
        scene_id=scene_id,
        change_kind=change_kind,
        root_artifact_ids=root_ids,
        invalidated_artifact_ids=tuple(sorted(invalidated)),
        affected_transition_ids=tuple(transition_ids),
    )
