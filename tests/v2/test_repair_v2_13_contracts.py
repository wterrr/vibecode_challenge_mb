from __future__ import annotations

import pytest

from learnflow_v2.repair import (
    ArtifactIndex,
    ArtifactInputHash,
    ArtifactKind,
    ArtifactRecord,
    RepairBudgetState,
    RepairDependencyError,
    RepairInvalidInputError,
    RepairNonDeterminismError,
    compute_content_hash,
    make_artifact_record,
)


def test_content_hash_is_deterministic_across_dict_order():
    assert compute_content_hash({"a": 1, "b": 2}) == compute_content_hash({"b": 2, "a": 1})


def test_content_hash_distinguishes_text_and_json_payloads():
    assert compute_content_hash("{}") != compute_content_hash({})


def test_artifact_record_rejects_invalid_hash_and_scope():
    with pytest.raises(RepairInvalidInputError):
        ArtifactRecord(
            artifact_id="layout:s1",
            kind=ArtifactKind.LAYOUT_GRAPH,
            content_hash="bad",
            created_by_phase="layout",
            compiler_version="1",
            scene_id="s1",
        )
    with pytest.raises(RepairInvalidInputError):
        ArtifactRecord(
            artifact_id="layout:s1",
            kind=ArtifactKind.LAYOUT_GRAPH,
            content_hash="0" * 64,
            created_by_phase="layout",
            compiler_version="1",
        )


def test_transition_artifact_requires_explicit_endpoints():
    with pytest.raises(RepairInvalidInputError):
        ArtifactRecord(
            artifact_id="t",
            kind=ArtifactKind.INTER_SCENE_TRANSITION_PLAN,
            content_hash="0" * 64,
            created_by_phase="transition",
            compiler_version="1",
            transition_id="t12",
        )


def test_input_hashes_are_unique_and_canonical_ordered():
    a = ArtifactInputHash(artifact_id="a", content_hash="1" * 64)
    b = ArtifactInputHash(artifact_id="b", content_hash="2" * 64)
    record = ArtifactRecord(
        artifact_id="scene:s1",
        kind=ArtifactKind.SCENE_GRAPH,
        content_hash="3" * 64,
        input_hashes=(b, a),
        created_by_phase="scene",
        compiler_version="1",
        scene_id="s1",
    )
    assert [item.artifact_id for item in record.input_hashes] == ["a", "b"]
    with pytest.raises(RepairInvalidInputError):
        ArtifactRecord(
            artifact_id="scene:s1",
            kind=ArtifactKind.SCENE_GRAPH,
            content_hash="3" * 64,
            input_hashes=(a, a),
            created_by_phase="scene",
            compiler_version="1",
            scene_id="s1",
        )


def test_artifact_index_rejects_stale_input_hash():
    idx = ArtifactIndex()
    parent = make_artifact_record(
        artifact_id="scene:s1", kind=ArtifactKind.SCENE_GRAPH, payload={"x": 1},
        created_by_phase="scene", compiler_version="1", scene_id="s1",
    )
    idx.add(parent)
    child = ArtifactRecord(
        artifact_id="layout:s1",
        kind=ArtifactKind.LAYOUT_GRAPH,
        content_hash="3" * 64,
        input_hashes=(ArtifactInputHash(artifact_id="scene:s1", content_hash="4" * 64),),
        created_by_phase="layout",
        compiler_version="1",
        scene_id="s1",
    )
    with pytest.raises(RepairDependencyError):
        idx.add(child)


def test_cache_reuse_requires_identical_inputs_and_compiler_version():
    idx = ArtifactIndex()
    parent = make_artifact_record(
        artifact_id="scene:s1", kind=ArtifactKind.SCENE_GRAPH, payload={"x": 1},
        created_by_phase="scene", compiler_version="1", scene_id="s1",
    )
    idx.add(parent)
    layout = make_artifact_record(
        artifact_id="layout:s1:v1", kind=ArtifactKind.LAYOUT_GRAPH, payload={"box": 1},
        created_by_phase="layout", compiler_version="compiler-A", inputs=(parent,), scene_id="s1",
    )
    idx.add(layout)
    assert idx.find_reusable(
        kind=ArtifactKind.LAYOUT_GRAPH,
        inputs=(parent,),
        created_by_phase="layout",
        compiler_version="compiler-A",
        scene_id="s1",
    ) == layout
    assert idx.find_reusable(
        kind=ArtifactKind.LAYOUT_GRAPH,
        inputs=(parent,),
        created_by_phase="layout",
        compiler_version="compiler-B",
        scene_id="s1",
    ) is None


def test_same_inputs_different_outputs_are_flagged_nondeterministic():
    idx = ArtifactIndex()
    parent = make_artifact_record(
        artifact_id="scene:s1", kind=ArtifactKind.SCENE_GRAPH, payload={"x": 1},
        created_by_phase="scene", compiler_version="1", scene_id="s1",
    )
    idx.add(parent)
    for artifact_id, payload in (("layout:a", {"box": 1}), ("layout:b", {"box": 2})):
        idx.add(make_artifact_record(
            artifact_id=artifact_id,
            kind=ArtifactKind.LAYOUT_GRAPH,
            payload=payload,
            created_by_phase="layout",
            compiler_version="same",
            inputs=(parent,),
            scene_id="s1",
        ))
    with pytest.raises(RepairNonDeterminismError):
        idx.find_reusable(
            kind=ArtifactKind.LAYOUT_GRAPH,
            inputs=(parent,),
            created_by_phase="layout",
            compiler_version="same",
            scene_id="s1",
        )


def test_budget_state_rejects_bool_and_over_limit():
    with pytest.raises(RepairInvalidInputError):
        RepairBudgetState(layout_solves=True)
    with pytest.raises(Exception):
        RepairBudgetState(layout_solves=6)


def test_canonical_deserialization_rechecks_artifact_invariants():
    record = ArtifactRecord(
        artifact_id="scene:s1",
        kind=ArtifactKind.SCENE_GRAPH,
        content_hash="a" * 64,
        created_by_phase="scene",
        compiler_version="1",
        scene_id="s1",
    )
    assert ArtifactRecord.from_canonical_json(record.to_canonical_json()) == record


def test_hash_rejects_non_finite_json_payload():
    with pytest.raises(ValueError):
        compute_content_hash({"x": float("nan")})
    with pytest.raises(ValueError):
        compute_content_hash({"x": float("inf")})


def test_artifact_index_revalidates_model_construct_bypass():
    forged = ArtifactRecord.model_construct(
        schema_version="2.1",
        artifact_id="forged",
        kind=ArtifactKind.LAYOUT_GRAPH,
        content_hash="not-a-hash",
        input_hashes=(),
        created_by_phase="layout",
        compiler_version="1",
        scene_id="s1",
        transition_id=None,
        from_scene_id=None,
        to_scene_id=None,
    )
    with pytest.raises(Exception):
        ArtifactIndex().add(forged)


def test_artifact_dependency_cycle_is_rejected():
    idx = ArtifactIndex()
    a = ArtifactRecord(
        artifact_id="a", kind=ArtifactKind.ASSEMBLY, content_hash="a" * 64,
        input_hashes=(ArtifactInputHash(artifact_id="b", content_hash="b" * 64),),
        created_by_phase="assembly", compiler_version="1",
    )
    b = ArtifactRecord(
        artifact_id="b", kind=ArtifactKind.VIDEO_QA, content_hash="b" * 64,
        input_hashes=(ArtifactInputHash(artifact_id="a", content_hash="a" * 64),),
        created_by_phase="video-qa", compiler_version="1",
    )
    idx.add(a, validate_inputs=False)
    with pytest.raises(RepairDependencyError):
        idx.add(b, validate_inputs=False)


def test_repair_action_policy_cannot_be_forged():
    from learnflow_v2.qa import CriticPatchOp, CriticPatchSuggestion, CriticTargetKind, CriticTargetRef
    from learnflow_v2.repair import RepairAction, RepairChangeKind, RepairLevel
    from learnflow_v2.scenegraph.enums import PreferredRegion

    patch = CriticPatchSuggestion(
        patch_id="p",
        op=CriticPatchOp.SET_REGION,
        targets=(CriticTargetRef(kind=CriticTargetKind.NODE, target_id="n1"),),
        region=PreferredRegion.RIGHT,
    )
    with pytest.raises(RepairInvalidInputError):
        RepairAction(
            patch_id="p",
            op=CriticPatchOp.SET_REGION,
            patch=patch,
            level=RepairLevel.FALLBACK,
            change_kind=RepairChangeKind.NARRATION,
            target_ids=("NODE:n1",),
            deferred=True,
        )


def test_repair_policy_mapping_is_immutable():
    from learnflow_v2.qa import CriticPatchOp
    from learnflow_v2.repair import REPAIR_PATCH_POLICY, RepairChangeKind, RepairLevel
    with pytest.raises(TypeError):
        REPAIR_PATCH_POLICY[CriticPatchOp.SET_REGION] = (RepairLevel.FALLBACK, RepairChangeKind.NARRATION, True)


def test_cycle_rejection_rolls_back_index_state():
    idx = ArtifactIndex()
    a = ArtifactRecord(
        artifact_id="a2", kind=ArtifactKind.ASSEMBLY, content_hash="a" * 64,
        input_hashes=(ArtifactInputHash(artifact_id="b2", content_hash="b" * 64),),
        created_by_phase="assembly", compiler_version="1",
    )
    b = ArtifactRecord(
        artifact_id="b2", kind=ArtifactKind.VIDEO_QA, content_hash="b" * 64,
        input_hashes=(ArtifactInputHash(artifact_id="a2", content_hash="a" * 64),),
        created_by_phase="video-qa", compiler_version="1",
    )
    idx.add(a, validate_inputs=False)
    with pytest.raises(RepairDependencyError):
        idx.add(b, validate_inputs=False)
    assert [r.artifact_id for r in idx.records] == ["a2"]


def test_artifact_record_revalidates_forged_nested_input_hash():
    forged_input = ArtifactInputHash.model_construct(artifact_id="parent", content_hash="bad")
    with pytest.raises(Exception):
        ArtifactRecord(
            artifact_id="layout:s1", kind=ArtifactKind.LAYOUT_GRAPH, content_hash="a" * 64,
            input_hashes=(forged_input,), created_by_phase="layout", compiler_version="1", scene_id="s1",
        )
