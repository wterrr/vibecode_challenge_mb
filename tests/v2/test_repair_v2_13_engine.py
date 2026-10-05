from __future__ import annotations

import pytest

from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.layout.schema import LayoutStrategy
from learnflow_v2.qa import (
    CriticIssue,
    CriticIssueSeverity,
    CriticIssueType,
    CriticPatchOp,
    CriticPatchSuggestion,
    CriticResponse,
    CriticStatus,
    CriticTargetKind,
    CriticTargetRef,
)
from learnflow_v2.repair import (
    MAX_LAYOUT_SOLVES,
    MAX_SCENE_REGENERATIONS,
    MAX_VLM_REPAIR_ROUNDS,
    RepairBudgetState,
    RepairChangeKind,
    RepairLevel,
    RepairRetryLimitError,
    apply_safe_scenegraph_patches,
    build_repair_plan,
    classify_patch,
    consume_layout_solve,
    consume_scene_regeneration,
    consume_vlm_repair_round,
    next_repair_level,
)
from tests.v2.repair_v2_13_helpers import patch_importance, patch_region, scene


def test_patch_classification_covers_escalation_levels():
    rewrap = CriticPatchSuggestion(
        patch_id="rewrap",
        op=CriticPatchOp.REWRAP_TEXT,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
    )
    layout = CriticPatchSuggestion(
        patch_id="layout",
        op=CriticPatchOp.CHANGE_LAYOUT_STRATEGY,
        targets=(CriticTargetRef(kind=CriticTargetKind.SCENE, target_id="__scene__"),),
        layout_strategy=LayoutStrategy.COMPARISON,
    )
    visual = CriticPatchSuggestion(
        patch_id="visual",
        op=CriticPatchOp.CHANGE_VISUAL_INTENT,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
        semantic_value="comparison",
    )
    assert classify_patch(rewrap).level == RepairLevel.AUTO_FIX
    assert classify_patch(patch_region()).level == RepairLevel.NODE_PATCH
    assert classify_patch(layout).level == RepairLevel.GROUP_LAYOUT_PATCH
    assert classify_patch(visual).level == RepairLevel.SCENE_REGENERATION_REQUEST


def test_repair_plan_is_deterministic_and_marks_regeneration():
    visual = CriticPatchSuggestion(
        patch_id="visual",
        op=CriticPatchOp.CHANGE_VISUAL_INTENT,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
        semantic_value="comparison",
    )
    issue = CriticIssue(
        issue_id="i-visual",
        issue_type=CriticIssueType.PEDAGOGICAL_ALIGNMENT,
        severity=CriticIssueSeverity.HIGH,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
        reason="visual metaphor is wrong",
    )
    response = CriticResponse(status=CriticStatus.REPAIR, issues=(issue,), patches=(visual,))
    plan_a = build_repair_plan("s1", response)
    plan_b = build_repair_plan("s1", response)
    assert plan_a == plan_b
    assert plan_a.max_level == RepairLevel.SCENE_REGENERATION_REQUEST
    assert plan_a.requires_scene_regeneration is True


def test_safe_node_patches_are_applied_without_mutating_source():
    original = scene("s1")
    before = canonical_json(original)
    result = apply_safe_scenegraph_patches(original, (patch_region(), patch_importance()))
    assert canonical_json(original) == before
    node = next(node for node in result.scene_graph.nodes if node.id == "n1")
    assert node.layout_hint is not None
    assert node.layout_hint.preferred_region.value == "RIGHT"
    assert node.layout_hint.importance == pytest.approx(0.7)
    assert result.applied_patch_ids == ("p-importance", "p-region")
    assert result.deferred_patch_ids == ()
    assert result.change_kinds == (RepairChangeKind.GEOMETRY_ONLY,)
    assert result.original_scene_hash != result.repaired_scene_hash


def test_same_safe_patch_replay_produces_identical_scene_hash():
    original = scene("s1")
    a = apply_safe_scenegraph_patches(original, (patch_region(),))
    b = apply_safe_scenegraph_patches(original, (patch_region(),))
    assert a.repaired_scene_hash == b.repaired_scene_hash
    assert canonical_json(a.scene_graph) == canonical_json(b.scene_graph)


def test_layout_and_motion_patches_are_deferred_not_silently_executed():
    layout = CriticPatchSuggestion(
        patch_id="layout",
        op=CriticPatchOp.CHANGE_LAYOUT_STRATEGY,
        targets=(CriticTargetRef(kind=CriticTargetKind.SCENE, target_id="__scene__"),),
        layout_strategy=LayoutStrategy.COMPARISON,
    )
    motion = CriticPatchSuggestion(
        patch_id="motion",
        op=CriticPatchOp.REDUCE_MOTION,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
    )
    original = scene("s1")
    result = apply_safe_scenegraph_patches(original, (layout, motion))
    assert result.applied_patch_ids == ()
    assert result.deferred_patch_ids == ("layout", "motion")
    assert result.original_scene_hash == result.repaired_scene_hash
    assert result.change_kinds == ()


def test_style_patch_changes_style_without_geometry_or_audio_semantics():
    patch = CriticPatchSuggestion(
        patch_id="emphasis",
        op=CriticPatchOp.ADD_EMPHASIS,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
    )
    result = apply_safe_scenegraph_patches(scene("s1"), (patch,))
    node = next(node for node in result.scene_graph.nodes if node.id == "n1")
    assert "emphasis.high" in node.style_refs
    assert result.change_kinds == (RepairChangeKind.STYLE_ONLY,)


def test_hard_retry_limits_are_enforced_exactly():
    state = RepairBudgetState()
    for _ in range(MAX_LAYOUT_SOLVES):
        state = consume_layout_solve(state)
    with pytest.raises(RepairRetryLimitError):
        consume_layout_solve(state)

    state = RepairBudgetState()
    for _ in range(MAX_VLM_REPAIR_ROUNDS):
        state = consume_vlm_repair_round(state)
    with pytest.raises(RepairRetryLimitError):
        consume_vlm_repair_round(state)

    state = RepairBudgetState()
    for _ in range(MAX_SCENE_REGENERATIONS):
        state = consume_scene_regeneration(state)
    with pytest.raises(RepairRetryLimitError):
        consume_scene_regeneration(state)


def test_escalation_falls_back_after_scene_regeneration_budget_exhausted():
    state = RepairBudgetState(scene_regenerations=MAX_SCENE_REGENERATIONS)
    assert next_repair_level(RepairLevel.SCENEGRAPH_RECOMPILE, state) == RepairLevel.FALLBACK


def test_escalation_progression_is_monotonic():
    state = RepairBudgetState()
    levels = [RepairLevel.AUTO_FIX]
    for _ in range(4):
        levels.append(next_repair_level(levels[-1], state))
    assert levels == [
        RepairLevel.AUTO_FIX,
        RepairLevel.NODE_PATCH,
        RepairLevel.GROUP_LAYOUT_PATCH,
        RepairLevel.SCENEGRAPH_RECOMPILE,
        RepairLevel.SCENE_REGENERATION_REQUEST,
    ]


def test_build_plan_revalidates_model_construct_critic_response():
    forged_patch = CriticPatchSuggestion.model_construct(
        patch_id="forged",
        op=CriticPatchOp.SET_REGION,
        targets=(),
        normalized_magnitude=None,
        region=None,
        layout_strategy=None,
        motion_style=None,
        semantic_value=None,
    )
    forged_response = CriticResponse.model_construct(
        schema_version="2.1", status=CriticStatus.REPAIR, issues=(), patches=(forged_patch,)
    )
    with pytest.raises(Exception):
        build_repair_plan("s1", forged_response)


def test_apply_revalidates_forged_patch_and_scenegraph():
    forged_patch = CriticPatchSuggestion.model_construct(
        patch_id="forged",
        op=CriticPatchOp.SET_REGION,
        targets=(),
        normalized_magnitude=None,
        region=None,
        layout_strategy=None,
        motion_style=None,
        semantic_value=None,
    )
    with pytest.raises(Exception):
        apply_safe_scenegraph_patches(scene("s1"), (forged_patch,))


def test_noop_patch_does_not_claim_a_scene_change():
    original = scene("s1")
    first = apply_safe_scenegraph_patches(original, (patch_region(),))
    second = apply_safe_scenegraph_patches(first.scene_graph, (patch_region(),))
    assert second.applied_patch_ids == ()
    assert second.noop_patch_ids == ("p-region",)
    assert second.change_kinds == ()
    assert second.original_scene_hash == second.repaired_scene_hash


def test_budget_functions_revalidate_model_construct_bypass():
    forged = RepairBudgetState.model_construct(layout_solves=999, vlm_repair_rounds=0, scene_regenerations=0)
    with pytest.raises(Exception):
        consume_layout_solve(forged)


def test_repair_action_preserves_full_typed_patch_parameters():
    patch = patch_importance("importance-full")
    action = classify_patch(patch)
    assert action.patch == patch
    assert action.patch.normalized_magnitude == pytest.approx(0.2)
    assert action.patch.targets[0].target_id == "n1"


def test_repaired_scene_requires_deterministic_recheck_before_approval():
    from learnflow_v2.qa import DeterministicQAReport, QAIssue, QAIssueCode, QAIssueSeverity
    from learnflow_v2.repair import verify_repaired_scene

    result = apply_safe_scenegraph_patches(scene("s1"), (patch_region(),))
    passed = DeterministicQAReport(scene_id="s1", passed=True, issues=())
    verified = verify_repaired_scene(result, passed, qa_input_scene_hash=result.repaired_scene_hash)
    assert verified.approved is True

    issue = QAIssue(
        issue_id="FRAME_OVERFLOW:fatal",
        code=QAIssueCode.FRAME_OVERFLOW,
        severity=QAIssueSeverity.ERROR,
        object_ids=("n1",),
        message="still broken",
        evidence={},
    )
    failed = DeterministicQAReport(scene_id="s1", passed=False, issues=(issue,))
    rejected = verify_repaired_scene(result, failed, qa_input_scene_hash=result.repaired_scene_hash)
    assert rejected.approved is False


def test_repair_verification_rejects_scene_mismatch_and_forged_approval():
    from learnflow_v2.qa import DeterministicQAReport
    from learnflow_v2.repair import RepairVerificationResult, verify_repaired_scene

    result = apply_safe_scenegraph_patches(scene("s1"), (patch_region(),))
    with pytest.raises(Exception):
        verify_repaired_scene(result, DeterministicQAReport(scene_id="other", passed=True, issues=()), qa_input_scene_hash=result.repaired_scene_hash)
    with pytest.raises(Exception):
        RepairVerificationResult(
            scene_id="s1",
            repaired_scene_hash=result.repaired_scene_hash,
            qa_input_scene_hash=result.repaired_scene_hash,
            deterministic_report=DeterministicQAReport(scene_id="s1", passed=True, issues=()),
            approved=False,
        )


def test_repair_recheck_rejects_stale_pre_repair_hash():
    from learnflow_v2.qa import DeterministicQAReport
    from learnflow_v2.repair import verify_repaired_scene

    result = apply_safe_scenegraph_patches(scene("s1"), (patch_region(),))
    report = DeterministicQAReport(scene_id="s1", passed=True, issues=())
    with pytest.raises(Exception):
        verify_repaired_scene(result, report, qa_input_scene_hash=result.original_scene_hash)


def test_duplicate_same_operation_same_target_is_rejected_not_ordered_by_patch_id():
    a = patch_region("a")
    b = patch_region("b")
    with pytest.raises(Exception):
        apply_safe_scenegraph_patches(scene("s1"), (a, b))


def test_repair_action_revalidates_forged_embedded_patch():
    from learnflow_v2.repair import RepairAction
    forged = CriticPatchSuggestion.model_construct(
        patch_id="x", op=CriticPatchOp.SET_REGION, targets=(), normalized_magnitude=None,
        region=None, layout_strategy=None, motion_style=None, semantic_value=None,
    )
    with pytest.raises(Exception):
        RepairAction(
            patch_id="x", op=CriticPatchOp.SET_REGION, patch=forged,
            level=RepairLevel.NODE_PATCH, change_kind=RepairChangeKind.GEOMETRY_ONLY,
            target_ids=(), deferred=False,
        )
