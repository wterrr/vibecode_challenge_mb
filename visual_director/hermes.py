"""Hermes task construction and host-owned reference assembly for semantic visual direction."""

from __future__ import annotations

import json
import re
from typing import Any

from agent_contracts import (
    AgentContractError,
    EvidenceGraph,
    LearningBrief,
    LessonScript,
    PedagogyPlan,
    ResearchPack,
)
from fact_verification import FactVerificationReport
from learnflow_v2.concepts import ConceptRegistry
from script_agent import require_visual_director_ready, validate_lesson_script

from .gate import has_visual_implementation_directive
from .models import VisualDirectorOutput
from .registry import build_visual_concept_registry


_CORE_LAYOUT_INTENTS = ("CONCEPT_CARD", "PROCESS", "COMPARISON", "HIERARCHY")
_CORE_READING_DIRECTIONS = (
    "LEFT_TO_RIGHT",
    "RIGHT_TO_LEFT",
    "TOP_TO_BOTTOM",
    "BOTTOM_TO_TOP",
)
_CORE_DIRECTED_RELATION_KINDS = frozenset(
    {
        "FLOW",
        "CAUSES",
        "DEPENDS_ON",
        "PART_OF",
        "TRANSFORMS_INTO",
        "SEQUENCE_BEFORE",
        "SEQUENCE_AFTER",
    }
)
_RESERVED_LAYOUT_ROLES = frozenset(
    {"title", "safe_title", "header", "caption", "safe_caption", "subtitle"}
)
_SCENE_PURPOSE_BY_TEACHING_FUNCTION = {
    "INTRODUCE": "INTRODUCE",
    "EXPLAIN": "EXPLAIN",
    "COMPARE": "COMPARE",
    "DEMONSTRATE": "DEMONSTRATE",
    "PRACTICE": "DRILLDOWN",
    "CHECK": "RECAP",
    "SUMMARIZE": "SUMMARIZE",
}


def _indexed_array_schema(
    count: int,
    *,
    min_items: int = 0,
    description: str,
) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "array",
        "uniqueItems": True,
        "items": {
            "type": "integer",
            "minimum": 0,
        },
        "description": description,
    }
    if min_items:
        schema["minItems"] = min_items
    if count:
        schema["items"]["maximum"] = count - 1
    else:
        schema["maxItems"] = 0
    return schema


def _visual_wire_schema(
    *,
    segment_count: int,
    concept_count: int,
) -> dict[str, Any]:
    """Model-facing schema where every cross-artifact reference is index-based."""

    schema = json.loads(json.dumps(VisualDirectorOutput.model_json_schema()))
    defs = dict(schema.get("$defs") or {})

    storyboard = dict(defs.get("Storyboard") or {})
    storyboard_props = dict(storyboard.get("properties") or {})
    if "script_id" not in storyboard_props:
        raise AgentContractError("Storyboard schema is missing script_id")
    storyboard_props.pop("script_id", None)
    storyboard["properties"] = storyboard_props
    storyboard["required"] = [
        field for field in list(storyboard.get("required") or ())
        if field != "script_id"
    ]
    defs["Storyboard"] = storyboard

    scene = dict(defs.get("StoryboardScene") or {})
    scene_props = dict(scene.get("properties") or {})
    for required_field in ("script_segment_ids", "concept_refs", "continuity_keys"):
        if required_field not in scene_props:
            raise AgentContractError(
                f"StoryboardScene schema is missing {required_field}"
            )
    scene_props.pop("script_segment_ids", None)
    scene_props.pop("concept_refs", None)
    scene_props.pop("continuity_keys", None)
    scene_props["script_segment_indexes"] = _indexed_array_schema(
        segment_count,
        min_items=1,
        description=(
            "Unique zero-based indexes into context.script_segment_catalog. "
            "The host reconstructs exact script_segment_ids."
        ),
    )
    scene["properties"] = scene_props
    scene_required = []
    for field in list(scene.get("required") or ()):
        if field == "script_segment_ids":
            scene_required.append("script_segment_indexes")
        elif field not in {"concept_refs", "continuity_keys"}:
            scene_required.append(field)
    if "script_segment_indexes" not in scene_required:
        scene_required.append("script_segment_indexes")
    scene["required"] = scene_required
    defs["StoryboardScene"] = scene

    graph = dict(defs.get("SceneGraph") or {})
    graph_props = dict(graph.get("properties") or {})
    for required_field in ("scene_id", "purpose"):
        if required_field not in graph_props:
            raise AgentContractError(
                f"SceneGraph schema is missing {required_field}"
            )
    graph_props.pop("scene_id", None)
    graph_props.pop("purpose", None)
    graph_props["scene_index"] = {
        "type": "integer",
        "minimum": 0,
        "description": (
            "Zero-based index into storyboard.scenes. "
            "The host reconstructs the exact scene_id."
        ),
    }
    graph["properties"] = graph_props
    graph["required"] = [
        "scene_index" if field == "scene_id" else field
        for field in list(graph.get("required") or ())
        if field != "purpose"
    ]
    if "scene_index" not in graph["required"]:
        graph["required"].append("scene_index")
    defs["SceneGraph"] = graph

    node = dict(defs.get("SceneNode") or {})
    node_props = dict(node.get("properties") or {})
    if "concept_ref" not in node_props or "semantic_key" not in node_props:
        raise AgentContractError(
            "SceneNode schema is missing canonical concept reference fields"
        )
    node_props.pop("concept_ref", None)
    node_props.pop("semantic_key", None)
    concept_index_schema: dict[str, Any] = {
        "type": "integer",
        "minimum": 0,
        "description": (
            "Optional zero-based index into context.concept_catalog. "
            "Omit for nodes that do not represent a canonical lesson concept. "
            "The host reconstructs concept_ref and semantic_key."
        ),
    }
    if concept_count:
        concept_index_schema["maximum"] = concept_count - 1
    node_props["concept_index"] = concept_index_schema
    node["properties"] = node_props
    node["required"] = [
        field for field in list(node.get("required") or ())
        if field not in {"concept_ref", "semantic_key"}
    ]
    semantic_role = dict(node_props.get("semantic_role") or {})
    semantic_role["description"] = (
        "Optional domain semantic role. Do not use layout-zone roles such as "
        "TITLE, HEADER, CAPTION, SUBTITLE, SAFE_TITLE, or SAFE_CAPTION. For "
        "PROCESS scenes use PROCESS_TOPIC, PROCESS_ACTOR, and PROCESS_STEP roles "
        "only so frozen Core's compact fallback remains valid. For COMPARISON "
        "scenes use exactly one COMPARISON_TOPIC and at least two "
        "COMPARISON_COLUMN roles; attach every remaining node to one column with "
        "PART_OF."
    )
    semantic_role["pattern"] = (
        r"^(?!(?i:title|safe_title|header|caption|safe_caption|subtitle)$).+$"
    )
    node_props["semantic_role"] = semantic_role
    node["properties"] = node_props
    defs["SceneNode"] = node

    # style_refs are symbolic design tokens, never renderer instructions.
    # Keep the wire grammar intentionally narrow so providers cannot encode
    # coordinates, CSS declarations, pixel sizes, or backend names here.
    for def_name in ("SceneGraph", "SceneNode", "SceneRelation"):
        definition = dict(defs.get(def_name) or {})
        properties = dict(definition.get("properties") or {})
        style_refs = dict(properties.get("style_refs") or {})
        if style_refs:
            items = dict(style_refs.get("items") or {})
            items["type"] = "string"
            items["pattern"] = r"^[A-Za-z][A-Za-z0-9.-]{0,63}$"
            style_refs["items"] = items
            style_refs["description"] = (
                "Symbolic style tokens only, for example concept.primary or "
                "emphasis.high. Never emit px values, coordinates, CSS position "
                "directives, renderer/backend names, or implementation commands."
            )
            properties["style_refs"] = style_refs
            definition["properties"] = properties
            defs[def_name] = definition

    layout_intent = dict(defs.get("LayoutIntent") or {})
    layout_intent["enum"] = list(_CORE_LAYOUT_INTENTS)
    defs["LayoutIntent"] = layout_intent

    reading_direction = dict(defs.get("ReadingDirection") or {})
    reading_direction["enum"] = list(_CORE_READING_DIRECTIONS)
    defs["ReadingDirection"] = reading_direction

    # Frozen live Core uses Graphviz for directed PROCESS/HIERARCHY layouts.
    # Graphviz cannot guarantee strict orthogonal fixed-side ports, so expose
    # only the supported AUTO capability to the model.
    port_hint = dict(defs.get("PortHint") or {})
    port_hint["enum"] = ["AUTO"]
    defs["PortHint"] = port_hint

    schema["$defs"] = defs
    return schema


def _validate_indexes(
    value: Any,
    *,
    count: int,
    field_name: str,
    min_items: int = 0,
) -> list[int]:
    if not isinstance(value, list):
        raise AgentContractError(f"{field_name} must be an array")
    if len(value) < min_items:
        raise AgentContractError(
            f"{field_name} must contain at least {min_items} item(s)"
        )

    indexes: list[int] = []
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool):
            raise AgentContractError(f"{field_name} entries must be integers")
        if item < 0 or item >= count:
            raise AgentContractError(
                f"{field_name} index {item} is outside 0..{count - 1}"
            )
        indexes.append(item)
    if len(indexes) != len(set(indexes)):
        raise AgentContractError(f"{field_name} must be unique")
    return indexes


def _sanitize_symbolic_style_refs(graph: dict[str, Any]) -> dict[str, Any]:
    """Drop only invalid implementation-bearing style tokens.

    style_refs have no semantic authority; they are optional symbolic styling
    hints. Semantic roles, visual intent, content, relations, and concept
    identity are deliberately untouched and remain fail-closed at the gate.
    """

    token_pattern = re.compile(r"^[A-Za-z][A-Za-z0-9.-]{0,63}$")

    def clean(values: Any) -> list[str]:
        if not isinstance(values, list):
            return []
        kept: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            if not token_pattern.fullmatch(value):
                continue
            if has_visual_implementation_directive(value):
                continue
            kept.append(value)
        return kept

    graph["style_refs"] = clean(graph.get("style_refs"))
    for collection_name in ("nodes", "relations"):
        collection = graph.get(collection_name)
        if not isinstance(collection, list):
            continue
        cleaned_collection: list[Any] = []
        for item in collection:
            if not isinstance(item, dict):
                cleaned_collection.append(item)
                continue
            normalized = dict(item)
            normalized["style_refs"] = clean(normalized.get("style_refs"))
            cleaned_collection.append(normalized)
        graph[collection_name] = cleaned_collection
    return graph


def _negotiate_comparison_topology(
    graph: dict[str, Any],
    *,
    position: int,
) -> dict[str, Any]:
    """Make COMPARISON topology honest before frozen-Core validation.

    Explicit PART_OF membership is preserved. A missing membership may be
    reconstructed only when the node's semantic layout hint keeps it near
    exactly one comparison column. If membership is still ambiguous, degrade
    only that scene to CONCEPT_CARD instead of inventing semantic grouping.
    """

    layout_intent = dict(graph.get("layout_intent") or {})
    if str(layout_intent.get("type") or "CONCEPT_CARD").upper() != "COMPARISON":
        return graph

    nodes = graph.get("nodes")
    relations = graph.get("relations")
    if not isinstance(nodes, list):
        raise AgentContractError(
            f"scenegraphs[{position}].nodes must be an array"
        )
    if not isinstance(relations, list):
        raise AgentContractError(
            f"scenegraphs[{position}].relations must be an array"
        )

    topic_ids = [
        str(node.get("id"))
        for node in nodes
        if isinstance(node, dict)
        and str(node.get("semantic_role") or "") == "COMPARISON_TOPIC"
    ]
    column_ids = [
        str(node.get("id"))
        for node in nodes
        if isinstance(node, dict)
        and str(node.get("semantic_role") or "") == "COMPARISON_COLUMN"
    ]

    def downgrade() -> dict[str, Any]:
        layout_intent["type"] = "CONCEPT_CARD"
        graph["layout_intent"] = layout_intent
        style_refs = list(graph.get("style_refs") or ())
        marker = "host.fallback.comparison_to_concept_card"
        if marker not in style_refs:
            style_refs.append(marker)
        graph["style_refs"] = style_refs
        return graph

    if len(topic_ids) != 1 or len(column_ids) < 2:
        return downgrade()

    topic_id = topic_ids[0]
    column_set = set(column_ids)
    member_nodes = [
        node
        for node in nodes
        if isinstance(node, dict)
        and str(node.get("id")) not in column_set | {topic_id}
    ]
    member_ids = {str(node.get("id")) for node in member_nodes}

    memberships: dict[str, set[str]] = {member_id: set() for member_id in member_ids}
    for relation in relations:
        if not isinstance(relation, dict):
            raise AgentContractError(
                f"scenegraphs[{position}].relations entries must be objects"
            )
        if str(relation.get("kind") or "") != "PART_OF":
            continue
        source = str(relation.get("source") or "")
        target = str(relation.get("target") or "")
        if source in memberships and target in column_set:
            memberships[source].add(target)

    generated: list[dict[str, Any]] = []
    for node in member_nodes:
        node_id = str(node.get("id"))
        if memberships[node_id]:
            continue
        layout_hint = node.get("layout_hint")
        keep_near = (
            list(layout_hint.get("keep_near") or ())
            if isinstance(layout_hint, dict)
            else []
        )
        nearby_columns = sorted(
            {str(item) for item in keep_near if str(item) in column_set}
        )
        if len(nearby_columns) == 1:
            target = nearby_columns[0]
            generated.append(
                {
                    "id": f"host:comparison-membership:{node_id}",
                    "source": node_id,
                    "target": target,
                    "kind": "PART_OF",
                    "source_port": "AUTO",
                    "target_port": "AUTO",
                    "style_refs": ["host.generated.comparison_membership"],
                }
            )
            memberships[node_id].add(target)

    if any(len(columns) != 1 for columns in memberships.values()):
        return downgrade()

    if generated:
        graph["relations"] = [*relations, *generated]
    return graph


def assemble_visual_director_wire(
    payload: dict[str, Any],
    *,
    script: LessonScript,
    registry: ConceptRegistry,
    concept_order: tuple[str, ...],
) -> VisualDirectorOutput:
    """Reconstruct all dynamic references deterministically on the host."""

    if not isinstance(payload, dict):
        raise AgentContractError("Visual Director wire output must be an object")

    concept_entries = tuple(registry.resolve(concept) for concept in concept_order)
    segment_ids = tuple(segment.segment_id for segment in script.segments)

    raw_storyboard = payload.get("storyboard")
    if not isinstance(raw_storyboard, dict):
        raise AgentContractError("Visual Director storyboard must be an object")
    if "script_id" in raw_storyboard:
        raise AgentContractError(
            "Visual Director wire storyboard must not emit script_id"
        )

    raw_scenes = raw_storyboard.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise AgentContractError(
            "Visual Director storyboard scenes must be a non-empty array"
        )

    scenes: list[dict[str, Any]] = []
    for position, raw_scene in enumerate(raw_scenes):
        if not isinstance(raw_scene, dict):
            raise AgentContractError(
                f"storyboard.scenes[{position}] must be an object"
            )
        if any(
            field in raw_scene
            for field in ("script_segment_ids", "concept_refs", "continuity_keys")
        ):
            raise AgentContractError(
                "Visual Director wire scenes must use script_segment_indexes and "
                "must not emit host-owned concept_refs/continuity_keys"
            )

        scene = dict(raw_scene)
        segment_indexes = _validate_indexes(
            scene.pop("script_segment_indexes", None),
            count=len(segment_ids),
            field_name=f"storyboard.scenes[{position}].script_segment_indexes",
            min_items=1,
        )
        scene["script_segment_ids"] = [
            segment_ids[index] for index in segment_indexes
        ]
        scene["concept_refs"] = []
        scene["continuity_keys"] = []
        scenes.append(scene)

    raw_graphs = payload.get("scenegraphs")
    if not isinstance(raw_graphs, list) or not raw_graphs:
        raise AgentContractError(
            "Visual Director scenegraphs must be a non-empty array"
        )

    graphs_by_scene_index: dict[int, dict[str, Any]] = {}
    concepts_by_scene_index: dict[int, set[int]] = {}

    for position, raw_graph in enumerate(raw_graphs):
        if not isinstance(raw_graph, dict):
            raise AgentContractError(f"scenegraphs[{position}] must be an object")
        if "scene_id" in raw_graph or "purpose" in raw_graph:
            raise AgentContractError(
                "Visual Director wire SceneGraph must use scene_index and must "
                "not emit host-owned scene_id/purpose"
            )

        graph = dict(raw_graph)
        scene_index = graph.pop("scene_index", None)
        if not isinstance(scene_index, int) or isinstance(scene_index, bool):
            raise AgentContractError(
                f"scenegraphs[{position}].scene_index must be an integer"
            )
        if scene_index < 0 or scene_index >= len(scenes):
            raise AgentContractError(
                f"scenegraphs[{position}].scene_index {scene_index} is outside "
                f"0..{len(scenes) - 1}"
            )
        if scene_index in graphs_by_scene_index:
            raise AgentContractError(
                f"scene_index {scene_index} is used by more than one SceneGraph"
            )

        raw_nodes = graph.get("nodes")
        if not isinstance(raw_nodes, list):
            raise AgentContractError(
                f"scenegraphs[{position}].nodes must be an array"
            )

        nodes: list[dict[str, Any]] = []
        concept_indexes: set[int] = set()
        for node_position, raw_node in enumerate(raw_nodes):
            if not isinstance(raw_node, dict):
                raise AgentContractError(
                    f"scenegraphs[{position}].nodes[{node_position}] must be an object"
                )
            if "concept_ref" in raw_node or "semantic_key" in raw_node:
                raise AgentContractError(
                    "Visual Director wire SceneNode must use concept_index, not "
                    "concept_ref/semantic_key"
                )

            node = dict(raw_node)
            concept_index = node.pop("concept_index", None)
            if concept_index is not None:
                if not isinstance(concept_index, int) or isinstance(concept_index, bool):
                    raise AgentContractError(
                        f"scenegraphs[{position}].nodes[{node_position}].concept_index "
                        "must be an integer"
                    )
                if concept_index < 0 or concept_index >= len(concept_entries):
                    raise AgentContractError(
                        f"scenegraphs[{position}].nodes[{node_position}].concept_index "
                        f"{concept_index} is outside 0..{len(concept_entries) - 1}"
                    )
                entry = concept_entries[concept_index]
                node["concept_ref"] = entry.concept_id
                node["semantic_key"] = entry.canonical_key
                concept_indexes.add(concept_index)
            nodes.append(node)

        graph["nodes"] = nodes
        graph = _sanitize_symbolic_style_refs(graph)
        graph = _negotiate_comparison_topology(
            graph,
            position=position,
        )

        # Defensive host-side capability negotiation. Port hints are geometric
        # preferences, not lesson semantics. Canonicalize unsupported fixed-side
        # hints before the frozen Core layout dry-run so provider variability
        # cannot request a capability the selected backend does not implement.
        layout_intent = dict(graph.get("layout_intent") or {})
        layout_type = str(layout_intent.get("type") or "CONCEPT_CARD").upper()
        if layout_type in {"PROCESS", "HIERARCHY"}:
            raw_relations = graph.get("relations")
            if not isinstance(raw_relations, list):
                raise AgentContractError(
                    f"scenegraphs[{position}].relations must be an array"
                )
            negotiated_relations: list[dict[str, Any]] = []
            for relation_position, raw_relation in enumerate(raw_relations):
                if not isinstance(raw_relation, dict):
                    raise AgentContractError(
                        f"scenegraphs[{position}].relations[{relation_position}] "
                        "must be an object"
                    )
                relation = dict(raw_relation)
                relation["source_port"] = "AUTO"
                relation["target_port"] = "AUTO"
                negotiated_relations.append(relation)
            graph["relations"] = negotiated_relations

        graph["scene_id"] = scenes[scene_index]["scene_id"]
        teaching_function = str(scenes[scene_index]["teaching_function"])
        try:
            graph["purpose"] = _SCENE_PURPOSE_BY_TEACHING_FUNCTION[
                teaching_function
            ]
        except KeyError as exc:
            raise AgentContractError(
                "Storyboard teaching_function has no frozen-Core ScenePurpose "
                f"mapping: {teaching_function!r}"
            ) from exc
        graphs_by_scene_index[scene_index] = graph
        concepts_by_scene_index[scene_index] = concept_indexes

    expected_scene_indexes = set(range(len(scenes)))
    actual_scene_indexes = set(graphs_by_scene_index)
    if actual_scene_indexes != expected_scene_indexes:
        missing = sorted(expected_scene_indexes - actual_scene_indexes)
        extra = sorted(actual_scene_indexes - expected_scene_indexes)
        raise AgentContractError(
            "Visual Director wire must provide exactly one SceneGraph per "
            f"storyboard scene; missing={missing!r}, extra={extra!r}"
        )

    for scene_index, scene in enumerate(scenes):
        ordered_concept_indexes = sorted(concepts_by_scene_index[scene_index])
        scene["concept_refs"] = [
            concept_entries[index].concept_id for index in ordered_concept_indexes
        ]
        scene["continuity_keys"] = [
            concept_entries[index].canonical_key
            for index in ordered_concept_indexes
        ]

    storyboard = dict(raw_storyboard)
    storyboard["script_id"] = script.script_id
    storyboard["scenes"] = scenes

    canonical = dict(payload)
    canonical["storyboard"] = storyboard
    canonical["scenegraphs"] = [
        graphs_by_scene_index[index] for index in range(len(scenes))
    ]
    output = VisualDirectorOutput.model_validate(canonical)

    for graph in output.scenegraphs:
        if graph.layout_intent.type.value not in _CORE_LAYOUT_INTENTS:
            raise AgentContractError(
                "Visual Director layout_intent is not supported by frozen Core; "
                f"scene_id={graph.scene_id!r}, layout_intent={graph.layout_intent.type.value!r}"
            )
        if graph.layout_intent.reading_direction.value not in _CORE_READING_DIRECTIONS:
            raise AgentContractError(
                "Visual Director reading_direction is not supported by frozen Core; "
                f"scene_id={graph.scene_id!r}, "
                f"reading_direction={graph.layout_intent.reading_direction.value!r}"
            )
        for node in graph.nodes:
            role = str(node.semantic_role or "").strip()
            if role and role.casefold() in _RESERVED_LAYOUT_ROLES:
                raise AgentContractError(
                    "Visual Director semantic_role must not use frozen Core layout-zone "
                    f"vocabulary; scene_id={graph.scene_id!r}, node_id={node.id!r}, "
                    f"semantic_role={role!r}"
                )
        if graph.layout_intent.type.value in {"PROCESS", "HIERARCHY"}:
            unsupported_relations = [
                relation
                for relation in graph.relations
                if relation.kind.value not in _CORE_DIRECTED_RELATION_KINDS
            ]
            if unsupported_relations:
                rendered = [
                    f"{relation.id}:{relation.kind.value}"
                    for relation in unsupported_relations
                ]
                raise AgentContractError(
                    "Visual Director directed-layout relations are not supported by "
                    "frozen Core; "
                    f"scene_id={graph.scene_id!r}, unsupported={rendered!r}. "
                    "Use only FLOW, CAUSES, DEPENDS_ON, PART_OF, TRANSFORMS_INTO, "
                    "SEQUENCE_BEFORE, or SEQUENCE_AFTER."
                )
    return output


def build_visual_director_task(
    brief: LearningBrief,
    pack: ResearchPack,
    graph: EvidenceGraph,
    fact_report: FactVerificationReport,
    pedagogy: PedagogyPlan,
    script: LessonScript,
) -> dict:
    """Build a semantic-only Hermes task from a deterministically valid script."""

    script_validation = validate_lesson_script(
        script,
        brief=brief,
        pack=pack,
        graph=graph,
        fact_report=fact_report,
        pedagogy=pedagogy,
    )
    require_visual_director_ready(script_validation)

    registry = build_visual_concept_registry(pedagogy)
    concept_entries = tuple(
        registry.resolve(concept) for concept in pedagogy.concept_order
    )
    payload = {
        "lesson_script": json.loads(script.to_canonical_json()),
        "script_segment_catalog": [
            {
                "index": index,
                "segment_id": segment.segment_id,
                "teaching_function": segment.teaching_function.value,
                "spoken_text": segment.spoken_text,
            }
            for index, segment in enumerate(script.segments)
        ],
        "concept_registry": registry.to_schema().model_dump(mode="json"),
        "concept_order": list(pedagogy.concept_order),
        "concept_catalog": [
            {
                "index": index,
                "concept_id": entry.concept_id,
                "canonical_key": entry.canonical_key,
                "label": entry.label,
            }
            for index, entry in enumerate(concept_entries)
        ],
        "required_ids": {"script_id": script.script_id},
        "instructions": [
            "Return one VisualDirectorOutput-shaped JSON object and no prose outside the structured result.",
            "Create a Storyboard plus exactly one SceneGraph for each storyboard scene.",
            (
                "For each storyboard scene return script_segment_indexes, not "
                "script_segment_ids. Indexes reference script_segment_catalog. Cover every "
                "LessonScript segment exactly once and in original order; only group "
                "adjacent segments that share the same teaching_function."
            ),
            (
                "Do not return Storyboard script_id, concept_refs, or continuity_keys. "
                "The host reconstructs those canonical references."
            ),
            (
                "Each SceneGraph returns scene_index, not scene_id or purpose. scene_index "
                "points to the corresponding storyboard scene; the host injects the exact "
                "scene_id and deterministically derives ScenePurpose from that storyboard "
                "scene's teaching_function."
            ),
            (
                "For a SceneNode representing a canonical lesson concept, return "
                "concept_index from concept_catalog and do not return concept_ref or "
                "semantic_key. Omit concept_index for non-concept helper/text/shape nodes. "
                "The host injects exact concept_ref and semantic_key values."
            ),
            "Storyboard scene teaching_function must match every ScriptSegment assigned to that scene.",
            (
                "For CODE nodes, put the exact learner-visible code expression/snippet in "
                "content. Use label only as an optional short semantic label. Never put a "
                "type name such as string/int/float in content when the learner should see "
                "the code expression itself."
            ),
            (
                "For SceneRelation ports, always use AUTO. Frozen live Core's "
                "Graphviz backend does not support strict fixed-side directional ports. "
                "Express direction using source/target and reading_direction instead."
            ),
            (
                "Use only frozen-Core-supported layout intents: CONCEPT_CARD, PROCESS, "
                "COMPARISON, or HIERARCHY; and reading directions LEFT_TO_RIGHT, "
                "RIGHT_TO_LEFT, TOP_TO_BOTTOM, or BOTTOM_TO_TOP."
            ),
            (
                "For PROCESS, emit exactly one PROCESS_TOPIC, at least one "
                "PROCESS_ACTOR, and at least one PROCESS_STEP; every node in that "
                "scene must use one of those roles so frozen Core's compact PROCESS "
                "fallback remains valid."
            ),
            (
                "For COMPARISON, emit exactly one COMPARISON_TOPIC and at least two "
                "COMPARISON_COLUMN nodes. Every other node must belong to exactly one "
                "column using PART_OF with source=member and target=column; do not "
                "leave ungrouped nodes."
            ),
            (
                "If a scene does not satisfy the specialized topology above, choose "
                "CONCEPT_CARD rather than labeling it PROCESS or COMPARISON."
            ),
            (
                "Keep each SceneGraph semantically minimal. Prefer CONCEPT_CARD for "
                "dense explanatory scenes; use PROCESS or HIERARCHY only when a small "
                "directed topology is essential. The host will reject SceneGraphs that "
                "frozen Core cannot lay out without scaling."
            ),
            (
                "semantic_role is domain semantics only. Never use layout-zone role names "
                "TITLE, HEADER, CAPTION, SUBTITLE, SAFE_TITLE, or SAFE_CAPTION."
            ),
            (
                "For PROCESS or HIERARCHY SceneGraphs, relation kinds must be limited to "
                "FLOW, CAUSES, DEPENDS_ON, PART_OF, TRANSFORMS_INTO, SEQUENCE_BEFORE, "
                "or SEQUENCE_AFTER. Do not use LABELS, ANNOTATES, GROUP_WITH, "
                "COMPARES_WITH, CONTRASTS_WITH, or EQUIVALENT_TO in directed layouts."
            ),
            "Use semantic SceneGraph structure only: nodes, relations, groups, symbolic style_refs, LayoutIntent, ReadingDirection, PortHint, and semantic LayoutHint fields.",
            "Layout hints may express preferred_region, relative importance, keep_near, keep_apart, and preferred_order only.",
            "Never output x/y coordinates, pixel values, width/height geometry, absolute font sizes, CSS positioning, renderer commands, FFmpeg commands, Manim/Pillow implementation instructions, or arbitrary rendering code.",
            "Do not decide motion, camera paths, timeline arithmetic, typography sizes, edge coordinates, or final pixels; Core V2 owns those decisions.",
            "Use visual rhythm and diversity when useful, while preserving concept continuity and keeping cognitive load appropriate for the script.",
            "Do not introduce new factual claims. Visual labels/content must stay within the supplied script and canonical concept labels.",
        ],
    }
    return {
        "goal": (
            "Act as LearnFlow Visual Director. Convert the validated LessonScript into "
            "a semantic Storyboard and schema-valid SceneGraph sequence without geometry "
            "or renderer implementation details."
        ),
        "context": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        "output_schema": _visual_wire_schema(
            segment_count=len(script.segments),
            concept_count=len(concept_entries),
        ),
    }
