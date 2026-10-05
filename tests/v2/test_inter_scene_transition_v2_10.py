from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from learnflow_v2.concepts.registry import ConceptRegistry
from learnflow_v2.concepts.schema import ConceptEntry
from learnflow_v2.core.errors import (
    TransitionGeometryError,
    TransitionInvalidInputError,
    TransitionSemanticMismatchError,
    TransitionUnregisteredSemanticKeyError,
)
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.layout.schema import LayoutBox, LayoutGraph, LayoutStrategy, Rect
from learnflow_v2.scenegraph.enums import NodeKind
from learnflow_v2.scenegraph.schema import SceneGraph, SceneNode
from learnflow_v2.transitions import (
    DEFAULT_TRANSITION_CAPABILITIES,
    FULL_TRANSITION_CAPABILITIES,
    MINIMAL_TRANSITION_CAPABILITIES,
    InterSceneTransitionPlan,
    PersistentObjectTransition,
    RendererTransitionCapabilities,
    TransitionOperation,
    TransitionPolicy,
    compile_inter_scene_transition,
    negotiate_operation_capability,
    negotiate_transition_plan,
)


def _registry() -> ConceptRegistry:
    registry = ConceptRegistry()
    registry.register(
        ConceptEntry(
            concept_id="c_prediction",
            canonical_key="concept:prediction",
            label="Prediction",
            aliases=["pred"],
        )
    )
    registry.register(
        ConceptEntry(
            concept_id="c_other",
            canonical_key="concept:other",
            label="Other",
            aliases=["different"],
        )
    )
    return registry


def _layout(
    scene_id: str,
    specs: list[tuple[str, str | None, Rect]],
    *,
    width: float = 1280.0,
    height: float = 720.0,
    profile: str = "16:9_1280x720",
) -> LayoutGraph:
    return LayoutGraph(
        scene_id=scene_id,
        frame_profile_id=profile,
        frame_width=width,
        frame_height=height,
        boxes=[
            LayoutBox(
                node_id=node_id,
                rect=rect,
                zone="CONTENT",
                semantic_key=semantic_key,
            )
            for node_id, semantic_key, rect in specs
        ],
        strategy=LayoutStrategy.CONCEPT_CARD,
    )


def _persistent(**overrides) -> PersistentObjectTransition:
    data = dict(
        transition_item_id="s1__s2::concept:prediction",
        semantic_key="concept:prediction",
        concept_id="c_prediction",
        from_node_id="old_prediction",
        to_node_id="new_prediction",
        requested_operation=TransitionOperation.MOVE,
        effective_operation=TransitionOperation.MOVE,
        source_rect=Rect(x=100, y=100, width=200, height=100),
        target_rect=Rect(x=500, y=200, width=200, height=100),
        source_frame_width=1280,
        source_frame_height=720,
        target_frame_width=1280,
        target_frame_height=720,
        source_zone="CONTENT",
        target_zone="CONTENT",
    )
    data.update(overrides)
    return PersistentObjectTransition(**data)


def _plan(item: PersistentObjectTransition | None = None, **overrides) -> InterSceneTransitionPlan:
    data = dict(
        transition_id="s1__s2",
        from_scene="s1",
        to_scene="s2",
        duration=0.5,
        persistent_objects=(item or _persistent(),),
        departing_node_ids=(),
        entering_node_ids=(),
        unmatched_keys=(),
    )
    data.update(overrides)
    return InterSceneTransitionPlan(**data)


def test_same_semantic_key_different_node_ids_compiles_to_move() -> None:
    registry = _registry()
    before = _layout("s1", [("old_prediction", "concept:prediction", Rect(x=100, y=100, width=200, height=100))])
    after = _layout("s2", [("new_prediction", "concept:prediction", Rect(x=600, y=250, width=200, height=100))])
    plan = compile_inter_scene_transition(before, after, registry)
    assert len(plan.persistent_objects) == 1
    item = plan.persistent_objects[0]
    assert item.semantic_key == "concept:prediction"
    assert item.from_node_id == "old_prediction"
    assert item.to_node_id == "new_prediction"
    assert item.requested_operation is TransitionOperation.MOVE
    assert item.effective_operation is TransitionOperation.MOVE
    assert item.fallback_reason is None
    assert plan.departing_node_ids == ()
    assert plan.entering_node_ids == ()


def test_same_label_different_semantic_keys_do_not_match() -> None:
    registry = _registry()
    before = _layout("s1", [("a", None, Rect(x=10, y=10, width=100, height=60))])
    after = _layout("s2", [("b", None, Rect(x=50, y=50, width=100, height=60))])
    before_scene = SceneGraph(
        scene_id="s1",
        nodes=[SceneNode(id="a", kind=NodeKind.CONCEPT, label="Prediction", concept_ref="c_prediction", semantic_key="concept:prediction")],
    )
    after_scene = SceneGraph(
        scene_id="s2",
        nodes=[SceneNode(id="b", kind=NodeKind.CONCEPT, label="Prediction", concept_ref="c_other", semantic_key="concept:other")],
    )
    plan = compile_inter_scene_transition(before, after, registry, from_scene_graph=before_scene, to_scene_graph=after_scene)
    assert plan.persistent_objects == ()
    assert plan.departing_node_ids == ("a",)
    assert plan.entering_node_ids == ("b",)
    assert plan.unmatched_keys == ("concept:other", "concept:prediction")


def test_unknown_layout_semantic_key_is_rejected() -> None:
    registry = _registry()
    before = _layout("s1", [("a", "concept:ghost", Rect(x=10, y=10, width=100, height=60))])
    after = _layout("s2", [("b", "concept:ghost", Rect(x=50, y=50, width=100, height=60))])
    with pytest.raises(TransitionUnregisteredSemanticKeyError):
        compile_inter_scene_transition(before, after, registry)


def test_ambiguous_semantic_identity_never_arbitrarily_matches() -> None:
    registry = _registry()
    before = _layout(
        "s1",
        [
            ("a1", "concept:prediction", Rect(x=10, y=10, width=100, height=60)),
            ("a2", "concept:prediction", Rect(x=150, y=10, width=100, height=60)),
        ],
    )
    after = _layout("s2", [("b", "concept:prediction", Rect(x=50, y=50, width=100, height=60))])
    plan = compile_inter_scene_transition(before, after, registry)
    assert plan.persistent_objects == ()
    assert plan.unmatched_keys == ("concept:prediction",)
    assert plan.departing_node_ids == ("a1", "a2")
    assert plan.entering_node_ids == ("b",)
    assert any("AMBIGUOUS_SEMANTIC_KEY:concept:prediction" in d for d in plan.diagnostics)


def test_move_unsupported_falls_back_to_fade_with_provenance() -> None:
    registry = _registry()
    before = _layout("s1", [("a", "concept:prediction", Rect(x=10, y=10, width=100, height=60))])
    after = _layout("s2", [("b", "concept:prediction", Rect(x=50, y=50, width=100, height=60))])
    plan = compile_inter_scene_transition(before, after, registry, capabilities=MINIMAL_TRANSITION_CAPABILITIES)
    item = plan.persistent_objects[0]
    assert item.requested_operation is TransitionOperation.MOVE
    assert item.effective_operation is TransitionOperation.FADE
    assert item.fallback_reason == "BACKEND_UNSUPPORTED_MOVE"
    assert item.is_fallback


def test_move_supported_never_unnecessarily_fades() -> None:
    registry = _registry()
    before = _layout("s1", [("a", "concept:prediction", Rect(x=10, y=10, width=100, height=60))])
    after = _layout("s2", [("b", "concept:prediction", Rect(x=50, y=50, width=100, height=60))])
    plan = compile_inter_scene_transition(before, after, registry, capabilities=DEFAULT_TRANSITION_CAPABILITIES)
    assert plan.persistent_objects[0].effective_operation is TransitionOperation.MOVE
    assert plan.persistent_objects[0].fallback_reason is None


def test_advanced_operation_fallback_is_deterministic() -> None:
    assert negotiate_operation_capability(TransitionOperation.MORPH, DEFAULT_TRANSITION_CAPABILITIES) == (
        TransitionOperation.MOVE,
        "BACKEND_UNSUPPORTED_MORPH",
    )
    assert negotiate_operation_capability(TransitionOperation.MORPH, MINIMAL_TRANSITION_CAPABILITIES) == (
        TransitionOperation.FADE,
        "BACKEND_UNSUPPORTED_MORPH",
    )
    assert negotiate_operation_capability(TransitionOperation.RESIZE, FULL_TRANSITION_CAPABILITIES) == (
        TransitionOperation.RESIZE,
        None,
    )


def test_different_frame_profiles_preserve_native_coordinate_spaces() -> None:
    registry = _registry()
    before = _layout(
        "s1",
        [("a", "concept:prediction", Rect(x=128, y=72, width=256, height=144))],
        width=1280,
        height=720,
        profile="16:9_1280x720",
    )
    after = _layout(
        "s2",
        [("b", "concept:prediction", Rect(x=72, y=128, width=144, height=256))],
        width=720,
        height=1280,
        profile="9:16_720x1280",
    )
    plan = compile_inter_scene_transition(before, after, registry)
    item = plan.persistent_objects[0]
    assert item.source_frame_width == 1280
    assert item.source_frame_height == 720
    assert item.target_frame_width == 720
    assert item.target_frame_height == 1280
    assert item.normalized_displacement_x == pytest.approx(0.0)
    assert item.normalized_displacement_y == pytest.approx(0.0)
    assert item.normalized_scale_x == pytest.approx(1.0)
    assert item.normalized_scale_y == pytest.approx(1.0)
    assert plan.metadata["from_frame_profile_id"] == "16:9_1280x720"
    assert plan.metadata["to_frame_profile_id"] == "9:16_720x1280"


def test_compilation_is_canonically_deterministic() -> None:
    registry = _registry()
    before = _layout(
        "s1",
        [
            ("z", "concept:prediction", Rect(x=10, y=10, width=100, height=60)),
            ("x", None, Rect(x=300, y=10, width=100, height=60)),
        ],
    )
    after = _layout(
        "s2",
        [
            ("y", None, Rect(x=300, y=10, width=100, height=60)),
            ("a", "concept:prediction", Rect(x=50, y=50, width=100, height=60)),
        ],
    )
    p1 = compile_inter_scene_transition(before, after, registry)
    p2 = compile_inter_scene_transition(before, after, registry)
    assert p1.to_canonical_json() == p2.to_canonical_json()


def test_compiler_does_not_mutate_source_artifacts() -> None:
    registry = _registry()
    before = _layout("s1", [("a", "concept:prediction", Rect(x=10, y=10, width=100, height=60))])
    after = _layout("s2", [("b", "concept:prediction", Rect(x=50, y=50, width=100, height=60))])
    before_json = canonical_json(before)
    after_json = canonical_json(after)
    registry_json = registry.to_canonical_json()
    compile_inter_scene_transition(before, after, registry)
    assert canonical_json(before) == before_json
    assert canonical_json(after) == after_json
    assert registry.to_canonical_json() == registry_json


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_plan_rejects_invalid_duration(bad: float) -> None:
    with pytest.raises((TransitionInvalidInputError, ValidationError)):
        _plan(duration=bad)


def test_plan_rejects_same_scene() -> None:
    with pytest.raises(TransitionInvalidInputError):
        _plan(from_scene="same", to_scene="same")


def test_plan_rejects_duplicate_semantic_key_and_item_id() -> None:
    item = _persistent()
    duplicate = _persistent(to_node_id="another_target")
    with pytest.raises(TransitionInvalidInputError):
        _plan(persistent_objects=(item, duplicate))


def test_persistent_object_rejects_fallback_without_reason() -> None:
    with pytest.raises(TransitionInvalidInputError):
        _persistent(effective_operation=TransitionOperation.FADE, fallback_reason=None)


def test_persistent_object_rejects_reason_without_fallback() -> None:
    with pytest.raises(TransitionInvalidInputError):
        _persistent(fallback_reason="SHOULD_NOT_EXIST")


def test_persistent_object_rejects_invalid_fallback_chain() -> None:
    with pytest.raises(TransitionInvalidInputError):
        _persistent(
            requested_operation=TransitionOperation.MOVE,
            effective_operation=TransitionOperation.RESIZE,
            fallback_reason="INVALID",
        )


def test_persistent_object_rejects_rect_outside_declared_frame() -> None:
    with pytest.raises(TransitionGeometryError):
        _persistent(source_rect=Rect(x=1200, y=100, width=200, height=100))


def test_persistent_object_rejects_forged_derived_geometry() -> None:
    with pytest.raises(TransitionGeometryError):
        _persistent(normalized_displacement_x=99.0)


def test_canonical_deserialization_enforces_fallback_invariants() -> None:
    good = _plan().to_canonical_json()
    bad = good.replace('"effective_operation": "MOVE"', '"effective_operation": "FADE"')
    with pytest.raises((TransitionInvalidInputError, ValidationError)):
        InterSceneTransitionPlan.from_canonical_json(bad)


def test_capabilities_require_fade_fallback() -> None:
    with pytest.raises(TransitionInvalidInputError):
        RendererTransitionCapabilities(supported_operations=(TransitionOperation.MOVE,))


def test_capability_declaration_is_deterministically_ordered() -> None:
    caps = RendererTransitionCapabilities(
        supported_operations={TransitionOperation.RESIZE, TransitionOperation.FADE, TransitionOperation.MOVE}
    )
    assert caps.supported_operations == (
        TransitionOperation.FADE,
        TransitionOperation.MOVE,
        TransitionOperation.RESIZE,
    )


def test_transition_plan_negotiation_does_not_mutate_source() -> None:
    source = _plan()
    before = source.to_canonical_json()
    negotiated = negotiate_transition_plan(source, MINIMAL_TRANSITION_CAPABILITIES)
    assert source.to_canonical_json() == before
    assert negotiated.persistent_objects[0].effective_operation is TransitionOperation.FADE
    assert negotiated.persistent_objects[0].fallback_reason == "BACKEND_UNSUPPORTED_MOVE"


def test_scene_graph_and_layout_semantic_conflict_is_rejected() -> None:
    registry = _registry()
    before = _layout("s1", [("a", "concept:other", Rect(x=10, y=10, width=100, height=60))])
    after = _layout("s2", [("b", "concept:prediction", Rect(x=50, y=50, width=100, height=60))])
    before_scene = SceneGraph(
        scene_id="s1",
        nodes=[SceneNode(id="a", kind=NodeKind.CONCEPT, concept_ref="c_prediction", semantic_key="concept:prediction")],
    )
    after_scene = SceneGraph(
        scene_id="s2",
        nodes=[SceneNode(id="b", kind=NodeKind.CONCEPT, concept_ref="c_prediction", semantic_key="concept:prediction")],
    )
    with pytest.raises(TransitionSemanticMismatchError):
        compile_inter_scene_transition(before, after, registry, from_scene_graph=before_scene, to_scene_graph=after_scene)


def test_scene_graph_layout_extra_node_is_rejected() -> None:
    registry = _registry()
    before = _layout("s1", [("layout_only", "concept:prediction", Rect(x=10, y=10, width=100, height=60))])
    after = _layout("s2", [("b", "concept:prediction", Rect(x=50, y=50, width=100, height=60))])
    before_scene = SceneGraph(scene_id="s1", nodes=[])
    with pytest.raises(TransitionSemanticMismatchError):
        compile_inter_scene_transition(before, after, registry, from_scene_graph=before_scene)


def test_resize_is_optional_and_capability_negotiated() -> None:
    registry = _registry()
    before = _layout("s1", [("a", "concept:prediction", Rect(x=100, y=100, width=100, height=60))])
    after = _layout("s2", [("b", "concept:prediction", Rect(x=100, y=100, width=300, height=180))])
    policy = TransitionPolicy(detect_resize=True, allow_resize=True)
    full = compile_inter_scene_transition(before, after, registry, policy=policy, capabilities=FULL_TRANSITION_CAPABILITIES)
    tier1 = compile_inter_scene_transition(before, after, registry, policy=policy, capabilities=DEFAULT_TRANSITION_CAPABILITIES)
    assert full.persistent_objects[0].requested_operation is TransitionOperation.RESIZE
    assert full.persistent_objects[0].effective_operation is TransitionOperation.RESIZE
    assert tier1.persistent_objects[0].requested_operation is TransitionOperation.RESIZE
    assert tier1.persistent_objects[0].effective_operation is TransitionOperation.MOVE
    assert tier1.persistent_objects[0].fallback_reason == "BACKEND_UNSUPPORTED_RESIZE"


def test_invalid_policy_is_rejected() -> None:
    with pytest.raises(TransitionInvalidInputError):
        TransitionPolicy(detect_resize=False, allow_resize=True)


def test_duration_pair_must_agree() -> None:
    registry = _registry()
    before = _layout("s1", [("a", "concept:prediction", Rect(x=10, y=10, width=100, height=60))])
    after = _layout("s2", [("b", "concept:prediction", Rect(x=50, y=50, width=100, height=60))])
    with pytest.raises(TransitionInvalidInputError):
        compile_inter_scene_transition(before, after, registry, duration=0.5, duration_ms=900)


def test_duration_clamp_is_deterministic_and_auditable() -> None:
    registry = _registry()
    before = _layout("s1", [("a", "concept:prediction", Rect(x=10, y=10, width=100, height=60))])
    after = _layout("s2", [("b", "concept:prediction", Rect(x=50, y=50, width=100, height=60))])
    caps = RendererTransitionCapabilities(
        supported_operations=(TransitionOperation.FADE, TransitionOperation.MOVE),
        min_duration=0.2,
        max_duration=0.4,
    )
    plan = compile_inter_scene_transition(before, after, registry, duration=2.0, capabilities=caps)
    assert plan.duration == pytest.approx(0.4)
    assert any(d.startswith("DURATION_CLAMPED:") for d in plan.diagnostics)


def test_semantic_key_cannot_be_registry_label_or_alias() -> None:
    registry = _registry()
    before = _layout("s1", [("a", "Prediction", Rect(x=10, y=10, width=100, height=60))])
    after = _layout("s2", [("b", "Prediction", Rect(x=50, y=50, width=100, height=60))])
    with pytest.raises(TransitionSemanticMismatchError):
        compile_inter_scene_transition(before, after, registry)


def test_metadata_rejects_non_string_keys_without_coercion() -> None:
    with pytest.raises((TransitionInvalidInputError, ValidationError)):
        _persistent(metadata={1: "bad"})


def test_duration_pair_rejects_bool_values() -> None:
    registry = _registry()
    before = _layout("s1", [("a", "concept:prediction", Rect(x=10, y=10, width=100, height=60))])
    after = _layout("s2", [("b", "concept:prediction", Rect(x=50, y=50, width=100, height=60))])
    with pytest.raises(TransitionInvalidInputError):
        compile_inter_scene_transition(before, after, registry, duration=True, duration_ms=1000)


def test_negotiation_is_idempotent_for_same_capabilities() -> None:
    first = negotiate_transition_plan(_plan(), MINIMAL_TRANSITION_CAPABILITIES)
    second = negotiate_transition_plan(first, MINIMAL_TRANSITION_CAPABILITIES)
    assert first.to_canonical_json() == second.to_canonical_json()
