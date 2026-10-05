"""Comprehensive test suite for LearnFlow V2 — CP 2.7: Motion Grammar Tier 1 schema."""

import pytest
from pydantic import ValidationError

from learnflow_v2.core.errors import (
    MotionDuplicateEventIdError,
    MotionGrammarIncompatibleError,
    MotionInvalidInputError,
    MotionInvalidTargetError,
    MotionSceneMismatchError,
    MotionUnsupportedSchemaVersionError,
    MotionUnsupportedTierError,
)
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.motion import (
    TIER_1_MOTION_GRAMMAR,
    TIER_2_3_RESERVED_STYLES,
    TIER_2_3_RESERVED_VERBS,
    V2_MOTION_SCHEMA_VERSION,
    VERB_TARGET_KIND_MAP,
    MotionEvent,
    MotionPlan,
    MotionStyle,
    MotionTargetKind,
    MotionTier,
    MotionTrigger,
    MotionVerb,
    is_tier_1_combination,
    is_tier_1_style,
    is_tier_1_verb,
    validate_motion_plan_with_scenegraph,
)
from learnflow_v2.scenegraph.enums import NodeKind, RelationKind
from learnflow_v2.scenegraph.schema import SceneGraph, SceneNode, SceneRelation


# =========================================================================
# 1. Valid Tier-1 Combinations
# =========================================================================

@pytest.mark.parametrize(
    "verb,style",
    [
        (MotionVerb.ENTER, MotionStyle.FADE),
        (MotionVerb.ENTER, MotionStyle.SLIDE),
        (MotionVerb.ENTER, MotionStyle.REVEAL),
        (MotionVerb.EMPHASIZE, MotionStyle.HIGHLIGHT),
        (MotionVerb.EMPHASIZE, MotionStyle.PULSE),
        (MotionVerb.EMPHASIZE, MotionStyle.FOCUS),
        (MotionVerb.RELATION, MotionStyle.DRAW_EDGE),
        (MotionVerb.RELATION, MotionStyle.PROPAGATE),
        (MotionVerb.TRANSFORM, MotionStyle.MOVE),
        (MotionVerb.EXIT, MotionStyle.FADE),
    ],
)
def test_valid_tier_1_combinations(verb: MotionVerb, style: MotionStyle):
    """Every supported Tier-1 (verb, style) pair must construct cleanly."""
    assert is_tier_1_verb(verb)
    assert is_tier_1_style(style)
    assert is_tier_1_combination(verb, style)

    target_id = "rel_1" if verb == MotionVerb.RELATION else "node_1"
    event = MotionEvent(
        id="evt_01",
        target=target_id,
        verb=verb,
        style=style,
        trigger=MotionTrigger(beat="beat_01"),
    )

    assert event.id == "evt_01"
    assert event.target == target_id
    assert event.target_id == target_id
    assert event.verb == verb
    assert event.style == style
    assert event.trigger is not None
    assert event.trigger.beat == "beat_01"

    # Verify target_kind inference
    expected_kind = MotionTargetKind.RELATION if verb == MotionVerb.RELATION else MotionTargetKind.NODE
    assert event.target_kind == expected_kind


def test_tier_1_matrix_completeness():
    """Verify the authoritative table contains exactly the specified Tier-1 grammar."""
    assert set(TIER_1_MOTION_GRAMMAR.keys()) == {
        MotionVerb.ENTER,
        MotionVerb.EMPHASIZE,
        MotionVerb.RELATION,
        MotionVerb.TRANSFORM,
        MotionVerb.EXIT,
    }
    assert TIER_1_MOTION_GRAMMAR[MotionVerb.ENTER] == {
        MotionStyle.FADE,
        MotionStyle.SLIDE,
        MotionStyle.REVEAL,
    }
    assert TIER_1_MOTION_GRAMMAR[MotionVerb.EMPHASIZE] == {
        MotionStyle.HIGHLIGHT,
        MotionStyle.PULSE,
        MotionStyle.FOCUS,
    }
    assert TIER_1_MOTION_GRAMMAR[MotionVerb.RELATION] == {
        MotionStyle.DRAW_EDGE,
        MotionStyle.PROPAGATE,
    }
    assert TIER_1_MOTION_GRAMMAR[MotionVerb.TRANSFORM] == {
        MotionStyle.MOVE,
    }
    assert TIER_1_MOTION_GRAMMAR[MotionVerb.EXIT] == {
        MotionStyle.FADE,
    }


def test_explicit_valid_target_kind_accepted():
    """Explicitly providing the correct target_kind is accepted."""
    ev_node = MotionEvent(
        id="e1",
        target="concept_a",
        verb=MotionVerb.ENTER,
        style=MotionStyle.FADE,
        target_kind=MotionTargetKind.NODE,
    )
    assert ev_node.target_kind == MotionTargetKind.NODE

    ev_rel = MotionEvent(
        id="e2",
        target="flow_r1",
        verb=MotionVerb.RELATION,
        style=MotionStyle.DRAW_EDGE,
        target_kind=MotionTargetKind.RELATION,
    )
    assert ev_rel.target_kind == MotionTargetKind.RELATION


# =========================================================================
# 2. Invalid Category / Style Combinations
# =========================================================================

@pytest.mark.parametrize(
    "verb,style",
    [
        (MotionVerb.ENTER, MotionStyle.PULSE),
        (MotionVerb.ENTER, MotionStyle.DRAW_EDGE),
        (MotionVerb.EMPHASIZE, MotionStyle.FADE),
        (MotionVerb.RELATION, MotionStyle.MOVE),
        (MotionVerb.TRANSFORM, MotionStyle.HIGHLIGHT),
        (MotionVerb.EXIT, MotionStyle.PROPAGATE),
        (MotionVerb.ENTER, MotionStyle.HIGHLIGHT),
        (MotionVerb.EMPHASIZE, MotionStyle.MOVE),
        (MotionVerb.TRANSFORM, MotionStyle.FADE),
        (MotionVerb.EXIT, MotionStyle.SLIDE),
    ],
)
def test_invalid_combinations_rejected(verb: MotionVerb, style: MotionStyle):
    """Incompatible cross-category verb and style pairs must be rejected."""
    assert not is_tier_1_combination(verb, style)

    with pytest.raises(MotionGrammarIncompatibleError) as exc_info:
        MotionEvent(
            id="e_invalid",
            target="target_1",
            verb=verb,
            style=style,
        )
    assert exc_info.value.code == "MOTION_GRAMMAR_INCOMPATIBLE"


# =========================================================================
# 3. Arbitrary / Unknown Commands Rejected
# =========================================================================

@pytest.mark.parametrize("bad_verb", ["SPIN", "BOUNCE", "FLY_AROUND", "ZOOM", "WIGGLE"])
def test_arbitrary_verbs_rejected(bad_verb: str):
    """Unknown arbitrary verbs must fail schema validation."""
    with pytest.raises(ValidationError):
        MotionEvent(
            id="e1",
            target="node_1",
            verb=bad_verb,  # type: ignore[arg-type]
            style=MotionStyle.FADE,
        )


@pytest.mark.parametrize("bad_style", ["ZOOM_EXPLOSION", "EXPLODE", "ROTATE_360", "FLIP"])
def test_arbitrary_styles_rejected(bad_style: str):
    """Unknown arbitrary styles must fail schema validation."""
    with pytest.raises(ValidationError):
        MotionEvent(
            id="e1",
            target="node_1",
            verb=MotionVerb.ENTER,
            style=bad_style,  # type: ignore[arg-type]
        )


def test_extra_fields_forbidden():
    """Unrestricted arbitrary command/render kwargs must be strictly rejected."""
    with pytest.raises(ValidationError):
        MotionEvent.model_validate(
            {
                "id": "e1",
                "target": "node_1",
                "verb": "ENTER",
                "style": "FADE",
                "duration_ms": 500,  # forbidden in semantic schema
                "easing": "ease-in-out",  # forbidden in semantic schema
            }
        )

    with pytest.raises(ValidationError):
        MotionPlan.model_validate(
            {
                "schema_version": "2.1",
                "scene_id": "s1",
                "events": [],
                "render_engine": "manim",  # forbidden
            }
        )


# =========================================================================
# 4. Tier Capability Boundary (Tier 2/3 Reserved Features)
# =========================================================================

def test_tier_2_camera_verb_rejected_in_tier_1():
    """Reserved CAMERA verb must be rejected for Tier-1 MotionPlan."""
    assert MotionVerb.CAMERA in TIER_2_3_RESERVED_VERBS
    with pytest.raises(MotionUnsupportedTierError) as exc_info:
        MotionEvent(
            id="e_cam",
            target="scene_view",
            verb=MotionVerb.CAMERA,
            style=MotionStyle.FADE,  # even with a valid style
        )
    assert exc_info.value.code == "MOTION_UNSUPPORTED_TIER"


@pytest.mark.parametrize(
    "reserved_style",
    [
        MotionStyle.SCALE_IN,
        MotionStyle.DRAW,
        MotionStyle.GLOW,
        MotionStyle.UNDERLINE,
        MotionStyle.RESIZE,
        MotionStyle.MORPH,
        MotionStyle.REPLACE,
        MotionStyle.TRACE_PATH,
        MotionStyle.PUSH,
        MotionStyle.PAN,
        MotionStyle.FOCUS_REGION,
        MotionStyle.RESET,
        MotionStyle.COLLAPSE,
    ],
)
def test_tier_2_3_reserved_styles_rejected_in_tier_1(reserved_style: MotionStyle):
    """Reserved Tier-2/Tier-3 styles must be explicitly rejected as unsupported in Tier 1."""
    assert reserved_style in TIER_2_3_RESERVED_STYLES
    with pytest.raises(MotionUnsupportedTierError) as exc_info:
        MotionEvent(
            id="e_reserved",
            target="target_1",
            verb=MotionVerb.TRANSFORM,
            style=reserved_style,
        )
    assert exc_info.value.code == "MOTION_UNSUPPORTED_TIER"


# =========================================================================
# 5. Event Integrity & Validation
# =========================================================================

@pytest.mark.parametrize("empty_val", ["", "   ", "\t\n"])
def test_empty_event_id_rejected(empty_val: str):
    """Empty or whitespace-only event IDs must be rejected."""
    with pytest.raises((MotionInvalidInputError, ValidationError)):
        MotionEvent(
            id=empty_val,
            target="node_1",
            verb=MotionVerb.ENTER,
            style=MotionStyle.FADE,
        )


@pytest.mark.parametrize("empty_val", ["", "   ", "\t\n"])
def test_empty_target_rejected(empty_val: str):
    """Empty or whitespace-only targets must be rejected."""
    with pytest.raises((MotionInvalidInputError, ValidationError)):
        MotionEvent(
            id="e1",
            target=empty_val,
            verb=MotionVerb.ENTER,
            style=MotionStyle.FADE,
        )


@pytest.mark.parametrize("empty_val", ["", "   ", "\t\n"])
def test_empty_trigger_beat_rejected(empty_val: str):
    """Empty or whitespace-only trigger beats must be rejected."""
    with pytest.raises((MotionInvalidInputError, ValidationError)):
        MotionTrigger(beat=empty_val)


def test_trigger_string_coercion():
    """String trigger values are automatically coerced into MotionTrigger(beat=...)."""
    event = MotionEvent(
        id="e1",
        target="concept_a",
        verb=MotionVerb.ENTER,
        style=MotionStyle.FADE,
        trigger="prediction_phrase",  # type: ignore[arg-type]
    )
    assert isinstance(event.trigger, MotionTrigger)
    assert event.trigger.beat == "prediction_phrase"


def test_mismatched_target_kind_rejected():
    """Explicitly specifying wrong target_kind for verb must fail."""
    # Node verb targeting RELATION kind
    with pytest.raises(MotionInvalidTargetError) as exc_info:
        MotionEvent(
            id="e1",
            target="edge_1",
            verb=MotionVerb.ENTER,
            style=MotionStyle.FADE,
            target_kind=MotionTargetKind.RELATION,
        )
    assert exc_info.value.code == "MOTION_INVALID_TARGET"

    # Relation verb targeting NODE kind
    with pytest.raises(MotionInvalidTargetError) as exc_info2:
        MotionEvent(
            id="e2",
            target="concept_1",
            verb=MotionVerb.RELATION,
            style=MotionStyle.DRAW_EDGE,
            target_kind=MotionTargetKind.NODE,
        )
    assert exc_info2.value.code == "MOTION_INVALID_TARGET"


# =========================================================================
# 6. Plan Integrity & Duplicate ID Rejection
# =========================================================================

def test_duplicate_event_ids_rejected():
    """Duplicate event IDs within the same MotionPlan must be rejected."""
    events = [
        MotionEvent(id="evt_same", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
        MotionEvent(id="evt_same", target="n2", verb=MotionVerb.EXIT, style=MotionStyle.FADE),
    ]
    with pytest.raises(MotionDuplicateEventIdError) as exc_info:
        MotionPlan(scene_id="s1", events=events)
    assert exc_info.value.code == "MOTION_DUPLICATE_EVENT_ID"


@pytest.mark.parametrize("empty_val", ["", "   ", "\t\n"])
def test_empty_scene_id_rejected(empty_val: str):
    """Empty or whitespace-only scene_id in MotionPlan must be rejected."""
    with pytest.raises((MotionInvalidInputError, ValidationError)):
        MotionPlan(scene_id=empty_val, events=[])


# =========================================================================
# 7. Versioning
# =========================================================================

def test_supported_schema_version_accepted():
    """Supported schema version 2.1 is accepted by default or when explicitly provided."""
    plan = MotionPlan(scene_id="s1", events=[])
    assert plan.schema_version == V2_MOTION_SCHEMA_VERSION
    assert plan.schema_version == "2.1"

    plan_explicit = MotionPlan(schema_version="2.1", scene_id="s1", events=[])
    assert plan_explicit.schema_version == "2.1"


@pytest.mark.parametrize("unsupported_version", ["1.0", "2.0", "3.0", "v2", "beta"])
def test_unsupported_schema_version_rejected(unsupported_version: str):
    """Unsupported schema versions must be rejected with MotionUnsupportedSchemaVersionError."""
    with pytest.raises(MotionUnsupportedSchemaVersionError) as exc_info:
        MotionPlan(schema_version=unsupported_version, scene_id="s1", events=[])
    assert exc_info.value.code == "MOTION_UNSUPPORTED_SCHEMA_VERSION"


# =========================================================================
# 8. Deterministic Serialization & Narrative Order Preservation
# =========================================================================

def test_deterministic_serialization_reproducibility():
    """Multiple identical plans must serialize to byte-for-byte identical canonical JSON."""
    events1 = [
        MotionEvent(id="e1", target="a", verb=MotionVerb.ENTER, style=MotionStyle.SLIDE, trigger="intro"),
        MotionEvent(id="e2", target="a", verb=MotionVerb.EMPHASIZE, style=MotionStyle.PULSE, trigger="highlight"),
        MotionEvent(id="e3", target="r1", verb=MotionVerb.RELATION, style=MotionStyle.DRAW_EDGE, trigger="connect"),
    ]
    events2 = [
        MotionEvent(id="e1", target="a", verb=MotionVerb.ENTER, style=MotionStyle.SLIDE, trigger="intro"),
        MotionEvent(id="e2", target="a", verb=MotionVerb.EMPHASIZE, style=MotionStyle.PULSE, trigger="highlight"),
        MotionEvent(id="e3", target="r1", verb=MotionVerb.RELATION, style=MotionStyle.DRAW_EDGE, trigger="connect"),
    ]

    p1 = MotionPlan(scene_id="scene_det", events=events1)
    p2 = MotionPlan(scene_id="scene_det", events=events2)

    json1 = p1.to_canonical_json()
    json2 = p2.to_canonical_json()

    assert json1 == json2
    assert json1 == canonical_json(p1)


def test_narrative_order_preserved():
    """Events must maintain their narrative sequence and NOT be sorted by ID."""
    events = [
        MotionEvent(id="z_third", target="c", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
        MotionEvent(id="a_first", target="a", verb=MotionVerb.ENTER, style=MotionStyle.SLIDE),
        MotionEvent(id="m_second", target="b", verb=MotionVerb.EMPHASIZE, style=MotionStyle.PULSE),
    ]
    plan = MotionPlan(scene_id="scene_order", events=events)
    json_out = plan.to_canonical_json()

    # Verify positions in serialized string
    pos_z = json_out.find('"z_third"')
    pos_a = json_out.find('"a_first"')
    pos_m = json_out.find('"m_second"')

    assert pos_z < pos_a < pos_m, "Event sequence in JSON must strictly follow narrative order"


# =========================================================================
# 9. Round-Trip Stability
# =========================================================================

def test_canonical_json_round_trip():
    """Model -> canonical JSON -> parsed model -> canonical JSON produces identical representation."""
    original = MotionPlan(
        schema_version="2.1",
        scene_id="scene_rt",
        events=[
            MotionEvent(
                id="e1",
                target="node_x",
                verb=MotionVerb.ENTER,
                style=MotionStyle.REVEAL,
                trigger=MotionTrigger(beat="beat_x"),
            ),
            MotionEvent(
                id="e2",
                target="rel_xy",
                verb=MotionVerb.RELATION,
                style=MotionStyle.PROPAGATE,
                trigger=MotionTrigger(beat="beat_rel"),
            ),
            MotionEvent(
                id="e3",
                target="node_x",
                verb=MotionVerb.TRANSFORM,
                style=MotionStyle.MOVE,
                trigger=MotionTrigger(beat="beat_move"),
            ),
            MotionEvent(
                id="e4",
                target="node_x",
                verb=MotionVerb.EXIT,
                style=MotionStyle.FADE,
                trigger=MotionTrigger(beat="beat_exit"),
            ),
        ],
    )

    first_json = original.to_canonical_json()
    parsed = MotionPlan.from_canonical_json(first_json)

    assert parsed.scene_id == original.scene_id
    assert parsed.schema_version == original.schema_version
    assert len(parsed.events) == len(original.events)

    for p_ev, o_ev in zip(parsed.events, original.events):
        assert p_ev.id == o_ev.id
        assert p_ev.target == o_ev.target
        assert p_ev.target_kind == o_ev.target_kind
        assert p_ev.verb == o_ev.verb
        assert p_ev.style == o_ev.style
        assert p_ev.trigger == o_ev.trigger

    second_json = parsed.to_canonical_json()
    assert first_json == second_json


# =========================================================================
# 10. SceneGraph Validation Integration
# =========================================================================

def _build_fixture_scenegraph() -> SceneGraph:
    return SceneGraph(
        scene_id="scene_test",
        nodes=[
            SceneNode(id="n_pred", kind=NodeKind.CONCEPT, label="Prediction"),
            SceneNode(id="n_loss", kind=NodeKind.CONCEPT, label="Loss"),
        ],
        relations=[
            SceneRelation(id="r_flow", source="n_pred", target="n_loss", kind=RelationKind.FLOW),
        ],
    )


def test_valid_scenegraph_validation():
    """A well-formed MotionPlan matching SceneGraph topology passes validation."""
    sg = _build_fixture_scenegraph()
    plan = MotionPlan(
        scene_id="scene_test",
        events=[
            MotionEvent(id="e1", target="n_pred", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
            MotionEvent(id="e2", target="n_loss", verb=MotionVerb.ENTER, style=MotionStyle.SLIDE),
            MotionEvent(id="e3", target="r_flow", verb=MotionVerb.RELATION, style=MotionStyle.DRAW_EDGE),
            MotionEvent(id="e4", target="n_loss", verb=MotionVerb.EMPHASIZE, style=MotionStyle.PULSE),
            MotionEvent(id="e5", target="n_pred", verb=MotionVerb.TRANSFORM, style=MotionStyle.MOVE),
            MotionEvent(id="e6", target="n_pred", verb=MotionVerb.EXIT, style=MotionStyle.FADE),
        ],
    )

    validate_motion_plan_with_scenegraph(plan, sg)
    plan.validate_with_scenegraph(sg)


def test_scenegraph_scene_id_mismatch_rejected():
    """MotionPlan scene_id not matching SceneGraph scene_id must fail."""
    sg = _build_fixture_scenegraph()
    plan = MotionPlan(
        scene_id="other_scene",
        events=[
            MotionEvent(id="e1", target="n_pred", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
        ],
    )
    with pytest.raises(MotionSceneMismatchError) as exc_info:
        validate_motion_plan_with_scenegraph(plan, sg)
    assert exc_info.value.code == "MOTION_SCENE_MISMATCH"


def test_unknown_node_target_rejected():
    """Node-oriented verb targeting non-existent node ID must fail."""
    sg = _build_fixture_scenegraph()
    plan = MotionPlan(
        scene_id="scene_test",
        events=[
            MotionEvent(id="e1", target="ghost_node", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
        ],
    )
    with pytest.raises(MotionInvalidTargetError) as exc_info:
        validate_motion_plan_with_scenegraph(plan, sg)
    assert exc_info.value.code == "MOTION_INVALID_TARGET"
    assert "ghost_node" in str(exc_info.value)


def test_node_verb_targeting_relation_rejected():
    """Node-oriented verb targeting a relation ID must fail."""
    sg = _build_fixture_scenegraph()
    plan = MotionPlan(
        scene_id="scene_test",
        events=[
            MotionEvent(id="e1", target="r_flow", verb=MotionVerb.ENTER, style=MotionStyle.FADE),
        ],
    )
    with pytest.raises(MotionInvalidTargetError) as exc_info:
        validate_motion_plan_with_scenegraph(plan, sg)
    assert exc_info.value.code == "MOTION_INVALID_TARGET"
    assert "must target a SceneNode" in str(exc_info.value)


def test_unknown_relation_target_rejected():
    """Relation-oriented verb targeting non-existent relation ID must fail."""
    sg = _build_fixture_scenegraph()
    plan = MotionPlan(
        scene_id="scene_test",
        events=[
            MotionEvent(id="e1", target="ghost_relation", verb=MotionVerb.RELATION, style=MotionStyle.DRAW_EDGE),
        ],
    )
    with pytest.raises(MotionInvalidTargetError) as exc_info:
        validate_motion_plan_with_scenegraph(plan, sg)
    assert exc_info.value.code == "MOTION_INVALID_TARGET"
    assert "ghost_relation" in str(exc_info.value)


def test_relation_verb_targeting_node_rejected():
    """Relation-oriented verb targeting a node ID must fail."""
    sg = _build_fixture_scenegraph()
    plan = MotionPlan(
        scene_id="scene_test",
        events=[
            MotionEvent(id="e1", target="n_pred", verb=MotionVerb.RELATION, style=MotionStyle.DRAW_EDGE),
        ],
    )
    with pytest.raises(MotionInvalidTargetError) as exc_info:
        validate_motion_plan_with_scenegraph(plan, sg)
    assert exc_info.value.code == "MOTION_INVALID_TARGET"
    assert "must target a SceneRelation" in str(exc_info.value)


# =========================================================================
# 11. SceneGraph Independence
# =========================================================================

def test_scenegraph_has_no_motion_fields():
    """SceneGraph and its constituent elements remain strictly motion-agnostic."""
    sg_fields = set(SceneGraph.model_fields.keys())
    assert "motion" not in sg_fields
    assert "motion_plan" not in sg_fields
    assert "events" not in sg_fields
    assert "animation" not in sg_fields

    n_fields = set(SceneNode.model_fields.keys())
    assert "motion" not in n_fields
    assert "events" not in n_fields
    assert "animation" not in n_fields

    r_fields = set(SceneRelation.model_fields.keys())
    assert "motion" not in r_fields
    assert "events" not in r_fields
    assert "animation" not in r_fields


# =========================================================================
# 12. Structural Immutability of MotionPlan
# =========================================================================

def test_motion_plan_events_normalized_to_tuple():
    """MotionPlan accepts list input but normalizes internally to an immutable tuple."""
    e1 = MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE)
    e2 = MotionEvent(id="e2", target="n2", verb=MotionVerb.EXIT, style=MotionStyle.FADE)

    plan = MotionPlan(scene_id="scene_imm", events=[e1, e2])
    assert isinstance(plan.events, tuple)
    assert len(plan.events) == 2
    assert plan.events[0] == e1
    assert plan.events[1] == e2


def test_runtime_append_to_events_impossible():
    """Attempting to append to plan.events must raise AttributeError."""
    e1 = MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE)
    plan = MotionPlan(scene_id="scene_imm", events=[e1])

    with pytest.raises(AttributeError):
        plan.events.append(e1)  # type: ignore[attr-defined]


def test_runtime_reassignment_of_events_rejected():
    """Attempting to reassign plan.events must raise ValidationError/TypeError due to frozen model."""
    e1 = MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE)
    plan = MotionPlan(scene_id="scene_imm", events=[e1])

    with pytest.raises((ValidationError, TypeError)):
        plan.events = (e1, e1)  # type: ignore[misc]


def test_runtime_item_assignment_to_events_rejected():
    """Attempting item assignment on plan.events must raise TypeError."""
    e1 = MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE)
    plan = MotionPlan(scene_id="scene_imm", events=[e1])

    with pytest.raises(TypeError):
        plan.events[0] = e1  # type: ignore[index]


def test_duplicate_invariant_cannot_be_bypassed_after_validation():
    """Validated MotionPlan cannot be mutated to inject duplicate event IDs."""
    e1 = MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE)
    plan = MotionPlan(scene_id="scene_imm", events=[e1])

    # Cannot append duplicate
    with pytest.raises(AttributeError):
        plan.events.append(e1)  # type: ignore[attr-defined]

    # Cannot extend duplicate
    with pytest.raises(AttributeError):
        plan.events.extend([e1])  # type: ignore[attr-defined]

    # Model remains intact with exactly 1 event
    assert len(plan.events) == 1
    assert plan.events[0].id == "e1"


def test_canonical_serialization_preserves_json_array_format():
    """Canonical JSON output must serialize events as a normal JSON array."""
    import json

    e1 = MotionEvent(id="e1", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE)
    plan = MotionPlan(scene_id="scene_imm", events=[e1])

    serialized = plan.to_canonical_json()
    parsed_json = json.loads(serialized)

    assert "events" in parsed_json
    assert isinstance(parsed_json["events"], list)
    assert len(parsed_json["events"]) == 1
    assert parsed_json["events"][0]["id"] == "e1"


# =========================================================================
# 13. Immutability of Tier-1 Grammar Contract
# =========================================================================

def test_tier_1_grammar_mapping_mutation_rejected():
    """Attempting to mutate TIER_1_MOTION_GRAMMAR must fail with TypeError."""
    with pytest.raises(TypeError):
        TIER_1_MOTION_GRAMMAR[MotionVerb.ENTER] = frozenset({MotionStyle.PULSE})  # type: ignore[index]

    with pytest.raises(TypeError):
        del TIER_1_MOTION_GRAMMAR[MotionVerb.ENTER]  # type: ignore[misc]

    with pytest.raises(TypeError):
        VERB_TARGET_KIND_MAP[MotionVerb.ENTER] = MotionTargetKind.RELATION  # type: ignore[index]


def test_nested_grammar_style_collections_immutable():
    """Nested style collections must be frozensets and reject runtime mutation."""
    enter_styles = TIER_1_MOTION_GRAMMAR[MotionVerb.ENTER]
    assert isinstance(enter_styles, frozenset)

    with pytest.raises(AttributeError):
        enter_styles.add(MotionStyle.PULSE)  # type: ignore[attr-defined]

    with pytest.raises(AttributeError):
        enter_styles.remove(MotionStyle.FADE)  # type: ignore[attr-defined]


def test_validation_remains_unchanged_after_attempted_mutation():
    """Validator enforces immutable rules: ENTER + FADE is valid, ENTER + PULSE is invalid."""
    # Attempt mutation (which fails)
    try:
        TIER_1_MOTION_GRAMMAR[MotionVerb.ENTER] = frozenset({MotionStyle.PULSE})  # type: ignore[index]
    except TypeError:
        pass

    # ENTER + FADE must remain valid
    ev_valid = MotionEvent(id="e_v", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE)
    assert ev_valid.verb == MotionVerb.ENTER
    assert ev_valid.style == MotionStyle.FADE

    # ENTER + PULSE must remain invalid
    with pytest.raises(MotionGrammarIncompatibleError):
        MotionEvent(id="e_inv", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.PULSE)


def test_grammar_and_target_kind_no_mutable_backing_dict_reachable():
    """Verify no mutable backing dicts exist in enums module and contracts are truly immutable."""
    import learnflow_v2.motion.enums as motion_enums

    # Backing dicts must NOT exist in the module namespace
    assert not hasattr(motion_enums, "_TIER_1_MOTION_GRAMMAR")
    assert not hasattr(motion_enums, "_VERB_TARGET_KIND_MAP")

    # Public grammar mapping cannot be assigned to
    with pytest.raises(TypeError):
        motion_enums.TIER_1_MOTION_GRAMMAR[MotionVerb.ENTER] = frozenset({MotionStyle.PULSE})  # type: ignore[index]

    # Public grammar entries cannot be deleted
    with pytest.raises(TypeError):
        del motion_enums.TIER_1_MOTION_GRAMMAR[MotionVerb.ENTER]  # type: ignore[misc]

    # Nested style collections are immutable
    for verb, styles in motion_enums.TIER_1_MOTION_GRAMMAR.items():
        assert isinstance(styles, frozenset)
        with pytest.raises(AttributeError):
            styles.add(MotionStyle.PULSE)  # type: ignore[attr-defined]

    # Public target-kind mapping cannot be mutated or deleted
    with pytest.raises(TypeError):
        motion_enums.VERB_TARGET_KIND_MAP[MotionVerb.ENTER] = MotionTargetKind.RELATION  # type: ignore[index]

    with pytest.raises(TypeError):
        del motion_enums.VERB_TARGET_KIND_MAP[MotionVerb.ENTER]  # type: ignore[misc]

    # Failed mutation attempts cannot change validation behavior
    ev_valid = MotionEvent(id="e_ok", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.FADE)
    assert ev_valid.verb == MotionVerb.ENTER
    assert ev_valid.style == MotionStyle.FADE

    with pytest.raises(MotionGrammarIncompatibleError):
        MotionEvent(id="e_bad", target="n1", verb=MotionVerb.ENTER, style=MotionStyle.PULSE)

    # Verify target kind mapping invariants remain exact
    assert motion_enums.VERB_TARGET_KIND_MAP[MotionVerb.ENTER] == MotionTargetKind.NODE
    assert motion_enums.VERB_TARGET_KIND_MAP[MotionVerb.EMPHASIZE] == MotionTargetKind.NODE
    assert motion_enums.VERB_TARGET_KIND_MAP[MotionVerb.TRANSFORM] == MotionTargetKind.NODE
    assert motion_enums.VERB_TARGET_KIND_MAP[MotionVerb.EXIT] == MotionTargetKind.NODE
    assert motion_enums.VERB_TARGET_KIND_MAP[MotionVerb.RELATION] == MotionTargetKind.RELATION

