"""Deterministic semantic gate for Hermes-generated visual direction."""

from __future__ import annotations

import re

from agent_contracts import (
    AgentContractError,
    LessonScript,
    StoryboardScene,
    TeachingFunction,
)
from learnflow_v2.concepts import ConceptRegistry
from learnflow_v2.core.errors import LearnFlowV2Error
from learnflow_v2.scenegraph import SceneGraph, ScenePurpose, validate_scenegraph_with_registry

from .models import VisualDirectorIssue, VisualDirectorOutput, VisualDirectorValidation


_ALLOWED_PURPOSES = {
    TeachingFunction.INTRODUCE: {ScenePurpose.INTRODUCE},
    TeachingFunction.EXPLAIN: {ScenePurpose.EXPLAIN, ScenePurpose.DRILLDOWN},
    TeachingFunction.COMPARE: {ScenePurpose.COMPARE},
    TeachingFunction.DEMONSTRATE: {ScenePurpose.DEMONSTRATE},
    TeachingFunction.PRACTICE: {ScenePurpose.DRILLDOWN, ScenePurpose.DEMONSTRATE},
    TeachingFunction.CHECK: {ScenePurpose.RECAP, ScenePurpose.DRILLDOWN},
    TeachingFunction.SUMMARIZE: {ScenePurpose.SUMMARIZE, ScenePurpose.RECAP},
}

_BOUNDARY_PATTERNS = (
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:px|pixels?)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:x|y|left|top|right|bottom|width|height|font[_-]?size|x_px|y_px|pixel_x|pixel_y)"
        r"\s*[:=]\s*-?\d+(?:\.\d+)?",
        re.IGNORECASE,
    ),
    re.compile(r"\bposition\s*:\s*(?:absolute|fixed)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:ffmpeg|deterministicpillowrenderer|render_scene_video|pillow renderer|manim renderer)\b",
        re.IGNORECASE,
    ),
)


def _sorted_unique(values) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def _metadata_has_boundary_directive(scene: StoryboardScene, graph: SceneGraph) -> bool:
    values: list[str] = [scene.visual_intent, *scene.continuity_keys, *graph.style_refs]
    for node in graph.nodes:
        if node.semantic_role:
            values.append(node.semantic_role)
        values.extend(node.style_refs)
    for relation in graph.relations:
        values.extend(relation.style_refs)
    for group in graph.groups:
        if group.semantic_role:
            values.append(group.semantic_role)
    text = "\n".join(values)
    return any(pattern.search(text) for pattern in _BOUNDARY_PATTERNS)


def validate_visual_director_output(
    output: VisualDirectorOutput,
    *,
    script: LessonScript,
    registry: ConceptRegistry,
) -> VisualDirectorValidation:
    """Validate Script coverage, semantic identity, and Visual/Core boundary."""

    issues: list[VisualDirectorIssue] = []

    storyboard_coverage_failed = False
    try:
        output.storyboard.validate_against_script(script)
    except AgentContractError:
        storyboard_coverage_failed = True
        issues.append(VisualDirectorIssue.STORYBOARD_SCRIPT_COVERAGE)

    storyboard_scene_ids = [scene.scene_id for scene in output.storyboard.scenes]
    graph_scene_ids = [graph.scene_id for graph in output.scenegraphs]
    scene_coverage_error_ids: list[str] = []
    if storyboard_scene_ids != graph_scene_ids:
        scene_coverage_error_ids = sorted(set(storyboard_scene_ids) ^ set(graph_scene_ids))
        if not scene_coverage_error_ids:
            scene_coverage_error_ids = storyboard_scene_ids
        issues.append(VisualDirectorIssue.SCENEGRAPH_SCENE_COVERAGE)

    segment_by_id = {segment.segment_id: segment for segment in script.segments}
    graph_by_id = {graph.scene_id: graph for graph in output.scenegraphs}
    registry_schema = registry.to_schema()
    registry_ids = {entry.concept_id for entry in registry_schema.concepts}
    canonical_by_id = {
        entry.concept_id: entry.canonical_key for entry in registry_schema.concepts
    }

    teaching_function_scene_ids: list[str] = []
    purpose_scene_ids: list[str] = []
    unknown_concept_refs: list[str] = []
    continuity_scene_ids: list[str] = []
    concept_set_scene_ids: list[str] = []
    empty_scene_ids: list[str] = []
    registry_invalid_scene_ids: list[str] = []
    boundary_violation_scene_ids: list[str] = []

    for scene in output.storyboard.scenes:
        mapped_segments = [
            segment_by_id.get(segment_id) for segment_id in scene.script_segment_ids
        ]
        known_segments = [segment for segment in mapped_segments if segment is not None]
        if (
            len(known_segments) != len(mapped_segments)
            or any(segment.teaching_function != scene.teaching_function for segment in known_segments)
        ):
            teaching_function_scene_ids.append(scene.scene_id)

        unknown = set(scene.concept_refs) - registry_ids
        unknown_concept_refs.extend(sorted(unknown))

        known_refs = [ref for ref in scene.concept_refs if ref in canonical_by_id]
        expected_continuity = {canonical_by_id[ref] for ref in known_refs}
        if set(scene.continuity_keys) != expected_continuity:
            continuity_scene_ids.append(scene.scene_id)

        graph = graph_by_id.get(scene.scene_id)
        if graph is None:
            continue

        if not graph.nodes:
            empty_scene_ids.append(scene.scene_id)

        if graph.purpose not in _ALLOWED_PURPOSES.get(scene.teaching_function, set()):
            purpose_scene_ids.append(scene.scene_id)

        graph_concept_refs = {
            node.concept_ref for node in graph.nodes if node.concept_ref is not None
        }
        if graph_concept_refs != set(scene.concept_refs):
            concept_set_scene_ids.append(scene.scene_id)

        try:
            validate_scenegraph_with_registry(graph, registry)
        except LearnFlowV2Error:
            registry_invalid_scene_ids.append(scene.scene_id)

        if _metadata_has_boundary_directive(scene, graph):
            boundary_violation_scene_ids.append(scene.scene_id)

    if teaching_function_scene_ids:
        issues.append(VisualDirectorIssue.TEACHING_FUNCTION_MISMATCH)
    if purpose_scene_ids:
        issues.append(VisualDirectorIssue.SCENE_PURPOSE_MISMATCH)
    if unknown_concept_refs:
        issues.append(VisualDirectorIssue.UNKNOWN_CONCEPT_REF)
    if continuity_scene_ids:
        issues.append(VisualDirectorIssue.CONTINUITY_KEY_MISMATCH)
    if concept_set_scene_ids:
        issues.append(VisualDirectorIssue.SCENE_CONCEPT_SET_MISMATCH)
    if empty_scene_ids:
        issues.append(VisualDirectorIssue.EMPTY_SCENEGRAPH)
    if registry_invalid_scene_ids:
        issues.append(VisualDirectorIssue.REGISTRY_VALIDATION_FAILED)
    if boundary_violation_scene_ids:
        issues.append(VisualDirectorIssue.VISUAL_IMPLEMENTATION_DIRECTIVE)

    # Keep a local variable so the coverage exception is intentionally consumed
    # only into the stable issue code above.
    _ = storyboard_coverage_failed

    return VisualDirectorValidation(
        storyboard_id=output.storyboard.storyboard_id,
        issues=tuple(issues),
        scene_coverage_error_ids=_sorted_unique(scene_coverage_error_ids),
        teaching_function_scene_ids=_sorted_unique(teaching_function_scene_ids),
        purpose_scene_ids=_sorted_unique(purpose_scene_ids),
        unknown_concept_refs=_sorted_unique(unknown_concept_refs),
        continuity_scene_ids=_sorted_unique(continuity_scene_ids),
        concept_set_scene_ids=_sorted_unique(concept_set_scene_ids),
        empty_scene_ids=_sorted_unique(empty_scene_ids),
        registry_invalid_scene_ids=_sorted_unique(registry_invalid_scene_ids),
        boundary_violation_scene_ids=_sorted_unique(boundary_violation_scene_ids),
    )


def require_core_ready(validation: VisualDirectorValidation) -> None:
    if validation.ready_for_core:
        return
    raise AgentContractError(
        "Visual Director output is not Core-ready: "
        f"issues={[issue.value for issue in validation.issues]!r}, "
        f"scene_coverage_error_ids={validation.scene_coverage_error_ids!r}, "
        f"teaching_function_scene_ids={validation.teaching_function_scene_ids!r}, "
        f"purpose_scene_ids={validation.purpose_scene_ids!r}, "
        f"unknown_concept_refs={validation.unknown_concept_refs!r}, "
        f"continuity_scene_ids={validation.continuity_scene_ids!r}, "
        f"concept_set_scene_ids={validation.concept_set_scene_ids!r}, "
        f"empty_scene_ids={validation.empty_scene_ids!r}, "
        f"registry_invalid_scene_ids={validation.registry_invalid_scene_ids!r}, "
        f"boundary_violation_scene_ids={validation.boundary_violation_scene_ids!r}"
    )
