"""Pilot-only fail-closed worked-example agreement across typed lesson artifacts.

This validator compares explicitly numbered search examples, not arbitrary
numeric literals or speculative semantic similarity.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from learnflow_v2.concepts.normalize import normalize_canonical_key, deterministic_concept_id


class SemanticConsistencyError(ValueError):
    """A referenced worked example changed meaning across stage boundaries."""


@dataclass(frozen=True)
class SearchExample:
    target: int
    values: tuple[int, ...]


def _get(obj: Any, key: str, default: Any = None) -> Any:
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def _numbered_example(value: str) -> SearchExample | None:
    arrays = re.findall(r"\[\s*-?\d+(?:\s*,\s*-?\d+)+\s*\]", value)
    targets = re.findall(r"\b(?:search\s+for|find|target\s*(?:is|=|:))\s*(-?\d+)\b", value, re.I)
    if not arrays or not targets:
        return None
    return SearchExample(int(targets[0]), tuple(int(n) for n in re.findall(r"-?\d+", arrays[0])))


def assert_semantic_consistency(result: Any) -> None:
    """Reject contradictory numeric worked examples before TTS/production.

    Scope: storyboard concept_refs referencing a registry 'Worked example:'
    with a parseable numeric list and target. This narrow contract avoids
    equating unrelated numbers in general teaching content.
    """
    registry = _get(result, "concept_registry")
    concepts = {_get(c, "concept_id"): c for c in _get(registry, "concepts", ())}
    scripts = {_get(s, "segment_id"): s for s in _get(_get(result, "lesson_script"), "segments", ())}
    graphs = {_get(g, "scene_id"): g for g in _get(result, "scenegraphs", ())}
    for scene in _get(_get(result, "storyboard"), "scenes", ()):
        scene_id = _get(scene, "scene_id")
        graph = graphs.get(scene_id)
        if graph is None:
            raise SemanticConsistencyError(f"SEMANTIC_SCENEGRAPH_MISSING scene={scene_id}")
        nodes = _get(graph, "nodes", ())
        for concept_id in _get(scene, "concept_refs", ()):
            entry = concepts.get(concept_id)
            if entry is None:
                raise SemanticConsistencyError(f"SEMANTIC_CONCEPT_REF_UNKNOWN scene={scene_id} concept_ref={concept_id}")
            label = str(_get(entry, "label", ""))
            if not label.casefold().startswith("worked example:"):
                continue
            # These IDs and canonical keys are deterministic products of the
            # registry label. Detect stale keys even when the label is repaired.
            canonical_key = _get(entry, "canonical_key")
            if canonical_key is not None and canonical_key != normalize_canonical_key(label):
                raise SemanticConsistencyError(
                    f"SEMANTIC_REGISTRY_KEY_LABEL_MISMATCH scene={scene_id} concept_ref={concept_id}"
                )
            if canonical_key is not None and concept_id != deterministic_concept_id(canonical_key):
                raise SemanticConsistencyError(
                    f"SEMANTIC_REGISTRY_ID_KEY_MISMATCH scene={scene_id} concept_ref={concept_id}"
                )
            canonical = _numbered_example(label)
            if canonical is None:
                continue  # Non-numeric worked examples remain outside this pilot contract.
            candidates = [("storyboard.visual_intent", _get(scene, "visual_intent", ""))]
            for segment_id in _get(scene, "script_segment_ids", ()):
                segment = scripts.get(segment_id)
                if segment is None:
                    raise SemanticConsistencyError(f"SEMANTIC_SCRIPT_SEGMENT_MISSING scene={scene_id} segment={segment_id}")
                candidates.append((f"script.{segment_id}.subtitle_text", _get(segment, "subtitle_text", "")))
            comparable = 0
            for source, value in candidates:
                observed = _numbered_example(str(value))
                if observed is not None:
                    comparable += 1
                    if observed != canonical:
                        raise SemanticConsistencyError(
                            f"SEMANTIC_WORKED_EXAMPLE_MISMATCH scene={scene_id} concept_ref={concept_id} "
                            f"source={source} registry={canonical} observed={observed}"
                        )
            if comparable == 0:
                raise SemanticConsistencyError(
                    f"SEMANTIC_WORKED_EXAMPLE_UNVERIFIABLE scene={scene_id} concept_ref={concept_id}"
                )
            for node in nodes:
                if _get(node, "concept_ref") == concept_id and canonical_key is not None:
                    node_key = _get(node, "semantic_key")
                    if node_key is not None and node_key != canonical_key:
                        raise SemanticConsistencyError(
                            f"SEMANTIC_NODE_CONCEPT_KEY_MISMATCH scene={scene_id} node={_get(node, 'id')}"
                        )
                role = str(_get(node, "semantic_role", "")).casefold()
                content = str(_get(node, "content", ""))
                if role == "search_target" and re.fullmatch(r"\s*-?\d+\s*", content):
                    if int(content) != canonical.target:
                        raise SemanticConsistencyError(
                            f"SEMANTIC_SCENEGRAPH_TARGET_MISMATCH scene={scene_id} node={_get(node, 'id')}"
                        )
                if role == "search_interval":
                    lists = re.findall(r"\[\s*-?\d+(?:\s*,\s*-?\d+)+\s*\]", content)
                    if lists and tuple(int(n) for n in re.findall(r"-?\d+", lists[0])) != canonical.values:
                        raise SemanticConsistencyError(
                            f"SEMANTIC_SCENEGRAPH_ARRAY_MISMATCH scene={scene_id} node={_get(node, 'id')}"
                        )
                if _get(node, "concept_ref") == concept_id and role == "search_result":
                    if not re.fullmatch(r"\s*-?\d+\s*", content) or int(content) != canonical.target:
                        raise SemanticConsistencyError(
                            f"SEMANTIC_REFERENCED_RESULT_MISMATCH scene={scene_id} node={_get(node, 'id')}"
                        )
