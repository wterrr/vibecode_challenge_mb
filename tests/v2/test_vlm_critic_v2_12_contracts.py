from __future__ import annotations

import pytest
from pydantic import ValidationError

from learnflow_v2.layout.schema import LayoutStrategy
from learnflow_v2.motion.enums import MotionStyle
from learnflow_v2.qa import (
    CriticIssue,
    CriticIssueSeverity,
    CriticIssueType,
    CriticPatchOp,
    CriticPatchSuggestion,
    CriticResponse,
    CriticStatus, CriticTargetKind, CriticTargetRef,
    QAInvalidInputError,
)
from learnflow_v2.scenegraph.enums import PreferredRegion
from tests.v2.critic_v2_12_helpers import pass_response, repair_response


def test_pass_response_has_no_issues_or_patches():
    response = pass_response()
    assert response.status == CriticStatus.PASS
    assert response.issues == ()
    assert response.patches == ()


def test_pass_response_with_issue_rejected():
    with pytest.raises(QAInvalidInputError):
        CriticResponse(
            status=CriticStatus.PASS,
            issues=(CriticIssue(issue_id="i", issue_type=CriticIssueType.READABILITY, severity=CriticIssueSeverity.LOW, targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),), reason="bad"),),
        )


def test_repair_response_requires_issue_and_patch():
    with pytest.raises(QAInvalidInputError):
        CriticResponse(status=CriticStatus.REPAIR)


def test_prose_response_is_not_a_valid_critic_response():
    with pytest.raises((ValidationError, TypeError)):
        CriticResponse.model_validate("looks good")


def test_pixel_coordinate_fields_are_forbidden():
    data = repair_response().model_dump(mode="json")
    data["patches"][0]["x"] = 583
    with pytest.raises(ValidationError):
        CriticResponse.model_validate(data)


def test_execute_code_patch_op_is_impossible():
    data = repair_response().model_dump(mode="json")
    data["patches"][0]["op"] = "EXECUTE_CODE"
    with pytest.raises(ValidationError):
        CriticResponse.model_validate(data)


@pytest.mark.parametrize(
    "op,extra",
    [
        (CriticPatchOp.SET_REGION, {"region": PreferredRegion.RIGHT}),
        (CriticPatchOp.CHANGE_LAYOUT_STRATEGY, {"layout_strategy": LayoutStrategy.COMPARISON, "_target_kind": CriticTargetKind.SCENE}),
        (CriticPatchOp.INCREASE_GAP, {"normalized_magnitude": 0.2, "_target_kind": CriticTargetKind.SCENE}),
        (CriticPatchOp.CHANGE_IMPORTANCE, {"normalized_magnitude": 0.15}),
        (CriticPatchOp.SCALE_NODE, {"normalized_magnitude": -0.2}),
        (CriticPatchOp.CHANGE_EDGE_STYLE, {"semantic_value": "emphasis.high", "_target_kind": CriticTargetKind.RELATION}),
        (CriticPatchOp.CHANGE_VISUAL_INTENT, {"semantic_value": "comparison"}),
        (CriticPatchOp.CHANGE_MOTION_STYLE, {"motion_style": MotionStyle.PULSE}),
        (CriticPatchOp.REDUCE_MOTION, {}),
    ],
)
def test_whitelisted_patch_ops_have_typed_semantic_parameters(op, extra):
    extra = dict(extra)
    target_kind = extra.pop("_target_kind", CriticTargetKind.NODE)
    target_id = "__scene__" if target_kind == CriticTargetKind.SCENE else ("r1" if target_kind == CriticTargetKind.RELATION else "n1")
    patch = CriticPatchSuggestion(
        patch_id="p",
        op=op,
        targets=(CriticTargetRef(kind=target_kind, target_id=target_id),),
        **extra,
    )
    assert patch.op == op


def test_patch_rejects_wrong_parameter_for_operation():
    with pytest.raises(QAInvalidInputError):
        CriticPatchSuggestion(
            patch_id="p",
            op=CriticPatchOp.SET_REGION,
            targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
            normalized_magnitude=0.2,
        )


def test_patch_rejects_reserved_tier_motion_style():
    with pytest.raises(QAInvalidInputError):
        CriticPatchSuggestion(
            patch_id="p",
            op=CriticPatchOp.CHANGE_MOTION_STYLE,
            targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
            motion_style=MotionStyle.MORPH,
        )


def test_patch_rejects_multiline_semantic_payload():
    with pytest.raises(QAInvalidInputError):
        CriticPatchSuggestion(
            patch_id="p",
            op=CriticPatchOp.CHANGE_VISUAL_INTENT,
            targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
            semantic_value="write_python\nprint('x')",
        )


def test_response_canonicalizes_issue_and_patch_order():
    r1 = repair_response()
    assert CriticResponse.model_validate_json(r1.to_canonical_json()) == r1


def test_semantic_patch_cannot_smuggle_pixel_assignment_or_code():
    for value in ("x=583", "print('x')", "SET_PIXEL 10 20", "ffmpeg -i input"):
        with pytest.raises(QAInvalidInputError):
            CriticPatchSuggestion(
                patch_id="p",
                op=CriticPatchOp.CHANGE_VISUAL_INTENT,
                targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
                semantic_value=value,
            )


def test_typed_targets_disambiguate_node_and_relation_namespaces():
    node_ref = CriticTargetRef(kind=CriticTargetKind.NODE, target_id="same")
    relation_ref = CriticTargetRef(kind=CriticTargetKind.RELATION, target_id="same")
    assert node_ref != relation_ref
    issue = CriticIssue(
        issue_id="typed",
        issue_type=CriticIssueType.CONTINUITY,
        severity=CriticIssueSeverity.MEDIUM,
        targets=(node_ref, relation_ref),
        reason="Typed identities stay distinct.",
    )
    assert {(t.kind, t.target_id) for t in issue.targets} == {
        (CriticTargetKind.NODE, "same"),
        (CriticTargetKind.RELATION, "same"),
    }


def test_scene_target_uses_reserved_typed_identity_only():
    with pytest.raises(QAInvalidInputError):
        CriticTargetRef(kind=CriticTargetKind.SCENE, target_id="n1")
    with pytest.raises(QAInvalidInputError):
        CriticTargetRef(kind=CriticTargetKind.NODE, target_id="__scene__")


def test_critic_request_response_canonical_round_trip_enforces_schema():
    from tests.v2.critic_v2_12_helpers import good_request
    request = good_request()
    assert type(request).from_canonical_json(request.to_canonical_json()) == request
    response = repair_response()
    assert type(response).from_canonical_json(response.to_canonical_json()) == response


@pytest.mark.parametrize(
    "op,target,extra",
    [
        (CriticPatchOp.CHANGE_LAYOUT_STRATEGY, CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"), {"layout_strategy": LayoutStrategy.COMPARISON}),
        (CriticPatchOp.REROUTE_EDGE, CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"), {}),
        (CriticPatchOp.SET_REGION, CriticTargetRef(kind=CriticTargetKind.RELATION, target_id="r1"), {"region": PreferredRegion.RIGHT}),
        (CriticPatchOp.SCALE_NODE, CriticTargetRef(kind=CriticTargetKind.SCENE, target_id="__scene__"), {"normalized_magnitude": 0.2}),
    ],
)
def test_patch_rejects_semantically_wrong_target_kind(op, target, extra):
    with pytest.raises(QAInvalidInputError):
        CriticPatchSuggestion(patch_id="bad-kind", op=op, targets=(target,), **extra)


def test_change_motion_style_rejects_relation_target_for_node_only_style():
    with pytest.raises(QAInvalidInputError):
        CriticPatchSuggestion(
            patch_id="bad-motion-kind",
            op=CriticPatchOp.CHANGE_MOTION_STYLE,
            targets=(CriticTargetRef(kind=CriticTargetKind.RELATION, target_id="r1"),),
            motion_style=MotionStyle.PULSE,
        )


def test_change_motion_style_accepts_relation_style_for_relation_target():
    patch = CriticPatchSuggestion(
        patch_id="relation-motion",
        op=CriticPatchOp.CHANGE_MOTION_STYLE,
        targets=(CriticTargetRef(kind=CriticTargetKind.RELATION, target_id="r1"),),
        motion_style=MotionStyle.DRAW_EDGE,
    )
    assert patch.motion_style == MotionStyle.DRAW_EDGE


def test_repair_response_rejects_unrelated_non_scene_patch_target():
    issue = CriticIssue(
        issue_id="i1",
        issue_type=CriticIssueType.READABILITY,
        severity=CriticIssueSeverity.MEDIUM,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
        reason="n1 is hard to read",
    )
    patch = CriticPatchSuggestion(
        patch_id="p1",
        op=CriticPatchOp.SCALE_NODE,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n2"),),
        normalized_magnitude=0.2,
    )
    with pytest.raises(QAInvalidInputError):
        CriticResponse(status=CriticStatus.REPAIR, issues=(issue,), patches=(patch,))


def test_repair_response_allows_scene_scope_patch_for_local_issue():
    issue = CriticIssue(
        issue_id="i1",
        issue_type=CriticIssueType.SPATIAL_BALANCE,
        severity=CriticIssueSeverity.MEDIUM,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
        reason="scene balance is poor",
    )
    patch = CriticPatchSuggestion(
        patch_id="p1",
        op=CriticPatchOp.CHANGE_LAYOUT_STRATEGY,
        targets=(CriticTargetRef(kind=CriticTargetKind.SCENE, target_id="__scene__"),),
        layout_strategy=LayoutStrategy.COMPARISON,
    )
    response = CriticResponse(status=CriticStatus.REPAIR, issues=(issue,), patches=(patch,))
    assert response.status == CriticStatus.REPAIR

@pytest.mark.parametrize("value", ["pixel 583", "move x 583 y 200", "coordinate 583 200", "position 583 200"])
def test_semantic_patch_cannot_smuggle_coordinates_as_free_text(value):
    with pytest.raises(QAInvalidInputError):
        CriticPatchSuggestion(
            patch_id="coord-smuggle",
            op=CriticPatchOp.CHANGE_VISUAL_INTENT,
            targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
            semantic_value=value,
        )


def test_patch_target_policy_has_no_mutable_backing_alias():
    policy = CriticPatchSuggestion._STRICT_TARGET_KINDS
    with pytest.raises(TypeError):
        policy[CriticPatchOp.SET_REGION] = frozenset({CriticTargetKind.RELATION})
    assert policy[CriticPatchOp.SET_REGION] == frozenset({CriticTargetKind.NODE})


def test_group_patch_ops_require_group_target_kind():
    group = CriticTargetRef(kind=CriticTargetKind.GROUP, target_id="g1")
    group2 = CriticTargetRef(kind=CriticTargetKind.GROUP, target_id="g2")
    assert CriticPatchSuggestion(patch_id="split", op=CriticPatchOp.SPLIT_GROUP, targets=(group,)).op == CriticPatchOp.SPLIT_GROUP
    assert CriticPatchSuggestion(patch_id="merge", op=CriticPatchOp.MERGE_GROUP, targets=(group, group2)).op == CriticPatchOp.MERGE_GROUP
    with pytest.raises(QAInvalidInputError):
        CriticPatchSuggestion(
            patch_id="bad-split",
            op=CriticPatchOp.SPLIT_GROUP,
            targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
        )


def test_issue_and_patch_ids_are_canonical_nonblank_strings():
    issue = CriticIssue(
        issue_id=" issue ",
        issue_type=CriticIssueType.READABILITY,
        severity=CriticIssueSeverity.LOW,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
        reason="readability",
    )
    patch = CriticPatchSuggestion(
        patch_id=" patch ",
        op=CriticPatchOp.REWRAP_TEXT,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
    )
    assert issue.issue_id == "issue"
    assert patch.patch_id == "patch"
    with pytest.raises(QAInvalidInputError):
        CriticIssue(
            issue_id="   ",
            issue_type=CriticIssueType.READABILITY,
            severity=CriticIssueSeverity.LOW,
            targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
            reason="readability",
        )


def test_group_split_merge_cardinality_is_explicit():
    g1 = CriticTargetRef(kind=CriticTargetKind.GROUP, target_id="g1")
    g2 = CriticTargetRef(kind=CriticTargetKind.GROUP, target_id="g2")
    with pytest.raises(QAInvalidInputError):
        CriticPatchSuggestion(patch_id="split-many", op=CriticPatchOp.SPLIT_GROUP, targets=(g1, g2))
    with pytest.raises(QAInvalidInputError):
        CriticPatchSuggestion(patch_id="merge-one", op=CriticPatchOp.MERGE_GROUP, targets=(g1,))
    merged = CriticPatchSuggestion(patch_id="merge-two", op=CriticPatchOp.MERGE_GROUP, targets=(g1, g2))
    assert len(merged.targets) == 2
