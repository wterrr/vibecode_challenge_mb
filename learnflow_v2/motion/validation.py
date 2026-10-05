"""Semantic cross-model validation for MotionPlan against SceneGraph."""

from learnflow_v2.core.errors import (
    MotionDuplicateEventIdError,
    MotionInvalidTargetError,
    MotionSceneMismatchError,
)
from learnflow_v2.motion.enums import MotionTargetKind, MotionVerb
from learnflow_v2.motion.schema import MotionPlan
from learnflow_v2.scenegraph.schema import SceneGraph


def validate_motion_plan_with_scenegraph(
    plan: MotionPlan,
    graph: SceneGraph,
) -> None:
    """Validate a MotionPlan against an explicit SceneGraph.

    Verifications:
    1. plan.scene_id matches graph.scene_id (raises MotionSceneMismatchError).
    2. Event IDs are unique within the plan (raises MotionDuplicateEventIdError).
    3. Node-targeting events (ENTER, EMPHASIZE, TRANSFORM, EXIT) target an existing SceneGraph node ID
       (raises MotionInvalidTargetError if unknown or if targeting a relation ID).
    4. Relation-targeting events (RELATION) target an existing SceneGraph relation ID
       (raises MotionInvalidTargetError if unknown or if targeting a node ID).
    """
    if plan.scene_id != graph.scene_id:
        raise MotionSceneMismatchError(
            f"MotionPlan scene_id '{plan.scene_id}' does not match SceneGraph scene_id '{graph.scene_id}'"
        )

    seen_ids: set[str] = set()
    for ev in plan.events:
        if ev.id in seen_ids:
            raise MotionDuplicateEventIdError(
                f"Duplicate motion event ID '{ev.id}' in MotionPlan for scene '{plan.scene_id}'"
            )
        seen_ids.add(ev.id)

    node_ids = {n.id for n in graph.nodes}
    relation_ids = {r.id for r in graph.relations}

    for ev in plan.events:
        is_relation_event = (
            ev.verb == MotionVerb.RELATION or ev.target_kind == MotionTargetKind.RELATION
        )

        if is_relation_event:
            # Must target a relation
            if ev.target in node_ids and ev.target not in relation_ids:
                raise MotionInvalidTargetError(
                    f"Motion event '{ev.id}' uses relation verb '{ev.verb.value}' targeting node '{ev.target}', "
                    f"but RELATION verbs must target a SceneRelation in scene '{graph.scene_id}'"
                )
            if ev.target not in relation_ids:
                raise MotionInvalidTargetError(
                    f"Motion event '{ev.id}' targets unknown relation '{ev.target}' in scene '{graph.scene_id}'"
                )
        else:
            # Must target a node
            if ev.target in relation_ids and ev.target not in node_ids:
                raise MotionInvalidTargetError(
                    f"Motion event '{ev.id}' uses node verb '{ev.verb.value}' targeting relation '{ev.target}', "
                    f"but node-oriented verbs must target a SceneNode in scene '{graph.scene_id}'"
                )
            if ev.target not in node_ids:
                raise MotionInvalidTargetError(
                    f"Motion event '{ev.id}' targets unknown node '{ev.target}' in scene '{graph.scene_id}'"
                )
