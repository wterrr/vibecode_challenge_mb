from __future__ import annotations

from learnflow_v2.repair import RepairChangeKind, invalidate_for_scene_change
from tests.v2.repair_v2_13_helpers import build_artifact_index


def test_geometry_only_repair_is_selective_and_does_not_resynthesize_audio():
    idx = build_artifact_index()
    result = invalidate_for_scene_change(idx, scene_id="s2", change_kind=RepairChangeKind.GEOMETRY_ONLY)
    invalid = set(result.invalidated_artifact_ids)
    assert "layout:s2" in invalid
    assert "render:s2" in invalid
    assert "qa:s2" in invalid
    assert "transition-plan:t12" in invalid
    assert "transition-plan:t23" in invalid
    assert "transition-render:t12" in invalid
    assert "transition-render:t23" in invalid
    assert result.affected_transition_ids == ("t12", "t23")
    assert "assembly" in invalid and "video-qa" in invalid
    assert "audio:s2" not in invalid
    assert "beats:s2" not in invalid
    assert "motion-plan:s2" not in invalid
    assert "render:s1" not in invalid
    assert "render:s3" not in invalid


def test_scenegraph_structure_change_invalidates_required_downstream_not_audio():
    idx = build_artifact_index()
    result = invalidate_for_scene_change(idx, scene_id="s2", change_kind=RepairChangeKind.SCENEGRAPH_STRUCTURE)
    invalid = set(result.invalidated_artifact_ids)
    assert "scene:s2" in invalid
    assert "layout:s2" in invalid
    assert "motion-plan:s2" in invalid
    assert "schedule:s2" in invalid
    assert "render:s2" in invalid
    assert "audio:s2" not in invalid
    assert "narration:s2" not in invalid
    assert "render:s1" not in invalid
    assert "render:s3" not in invalid
    assert result.affected_transition_ids == ("t12", "t23")


def test_narration_change_resynthesizes_only_affected_scene_audio_and_motion_timing():
    idx = build_artifact_index()
    result = invalidate_for_scene_change(idx, scene_id="s2", change_kind=RepairChangeKind.NARRATION)
    invalid = set(result.invalidated_artifact_ids)
    assert "narration:s2" in invalid
    assert "audio:s2" in invalid
    assert "beats:s2" in invalid
    assert "motion-plan:s2" in invalid
    assert "schedule:s2" in invalid
    assert "render:s2" in invalid
    assert "layout:s2" not in invalid
    assert "audio:s1" not in invalid
    assert "transition-plan:t12" not in invalid
    assert "transition-plan:t23" not in invalid


def test_motion_only_change_does_not_relayout_or_resynthesize_audio():
    idx = build_artifact_index()
    result = invalidate_for_scene_change(idx, scene_id="s2", change_kind=RepairChangeKind.MOTION_ONLY)
    invalid = set(result.invalidated_artifact_ids)
    assert "motion-plan:s2" in invalid and "schedule:s2" in invalid and "render:s2" in invalid
    assert "layout:s2" not in invalid
    assert "audio:s2" not in invalid
    assert result.affected_transition_ids == ()


def test_style_only_keeps_layout_and_transition_plan_but_refreshes_touching_transition_render():
    idx = build_artifact_index()
    result = invalidate_for_scene_change(idx, scene_id="s2", change_kind=RepairChangeKind.STYLE_ONLY)
    invalid = set(result.invalidated_artifact_ids)
    assert "render:s2" in invalid and "qa:s2" in invalid
    assert "layout:s2" not in invalid
    assert "audio:s2" not in invalid
    assert "transition-plan:t12" not in invalid
    assert "transition-plan:t23" not in invalid
    assert "transition-render:t12" in invalid
    assert "transition-render:t23" in invalid
    assert result.affected_transition_ids == ("t12", "t23")


def test_replay_invalidation_is_deterministic():
    idx = build_artifact_index()
    a = invalidate_for_scene_change(idx, scene_id="s2", change_kind=RepairChangeKind.GEOMETRY_ONLY)
    b = invalidate_for_scene_change(idx, scene_id="s2", change_kind=RepairChangeKind.GEOMETRY_ONLY)
    assert a == b


def test_repair_plan_invalidation_unions_only_requested_change_families():
    from learnflow_v2.layout.schema import LayoutStrategy
    from learnflow_v2.qa import CriticIssue, CriticIssueSeverity, CriticIssueType, CriticPatchOp, CriticPatchSuggestion, CriticResponse, CriticStatus, CriticTargetKind, CriticTargetRef
    from learnflow_v2.repair import build_repair_plan, invalidate_for_repair_plan

    issue = CriticIssue(
        issue_id="i",
        issue_type=CriticIssueType.SPATIAL_BALANCE,
        severity=CriticIssueSeverity.MEDIUM,
        targets=(CriticTargetRef(kind=CriticTargetKind.SCENE, target_id="__scene__"),),
        reason="layout needs repair",
    )
    patch = CriticPatchSuggestion(
        patch_id="layout",
        op=CriticPatchOp.CHANGE_LAYOUT_STRATEGY,
        targets=(CriticTargetRef(kind=CriticTargetKind.SCENE, target_id="__scene__"),),
        layout_strategy=LayoutStrategy.COMPARISON,
    )
    plan = build_repair_plan("s2", CriticResponse(status=CriticStatus.REPAIR, issues=(issue,), patches=(patch,)))
    result = invalidate_for_repair_plan(build_artifact_index(), plan)
    assert result.change_kinds == (RepairChangeKind.GEOMETRY_ONLY,)
    invalid = set(result.invalidated_artifact_ids)
    assert "layout:s2" in invalid and "render:s2" in invalid
    assert "audio:s2" not in invalid and "render:s1" not in invalid
