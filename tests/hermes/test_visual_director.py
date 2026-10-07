from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import AgentContractError, Storyboard, StoryboardScene, TeachingFunction
from learnflow_v2.scenegraph import (
    LayoutHint,
    LayoutIntent,
    LayoutIntentSpec,
    NodeKind,
    RelationKind,
    SceneNode,
    ScenePurpose,
)
from scripts.verify_script_agent import build_fixture, build_script
from scripts.verify_visual_director import build_visual_output
from visual_director import (
    VisualDirectorIssue,
    VisualDirectorOutput,
    assemble_visual_director_wire,
    build_visual_concept_registry,
    build_visual_director_task,
    require_core_ready,
    validate_visual_director_output,
)


def fixture():
    brief, pack, evidence_graph, report, pedagogy = build_fixture()
    script = build_script(pedagogy)
    registry = build_visual_concept_registry(pedagogy)
    output = build_visual_output(script, registry)
    return brief, pack, evidence_graph, report, pedagogy, script, registry, output


def validate(output, script, registry):
    return validate_visual_director_output(output, script=script, registry=registry)


def test_acceptance_verifier_passes():
    proc = subprocess.run(
        [sys.executable, "scripts/verify_visual_director.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "VISUAL_DIRECTOR=PASS" in proc.stdout
    assert "no_pixel_coordinates=PASS" in proc.stdout


def test_deterministic_registry_is_stable_and_precedes_scene_generation():
    *_, pedagogy, script, registry, _ = fixture()
    registry_2 = build_visual_concept_registry(pedagogy)
    assert registry.to_canonical_json() == registry_2.to_canonical_json()
    assert len(registry.all_concepts()) == len(pedagogy.concept_order)
    assert all(item.canonical_key.startswith("concept:") for item in registry.all_concepts())


def test_good_visual_output_is_core_ready():
    *_, script, registry, output = fixture()
    result = validate(output, script, registry)
    assert result.ready_for_core
    assert result.issues == ()
    require_core_ready(result)


def test_task_revalidates_script_and_exposes_semantic_context_only():
    brief, pack, evidence_graph, report, pedagogy, script, _, _ = fixture()
    task = build_visual_director_task(
        brief, pack, evidence_graph, report, pedagogy, script
    )
    context = json.loads(task["context"])
    assert set(context) == {
        "lesson_script",
        "script_segment_catalog",
        "concept_registry",
        "concept_order",
        "concept_catalog",
        "required_ids",
        "instructions",
    }
    assert "research_pack" not in context
    assert "selected_fact_claims" not in context
    assert context["required_ids"]["script_id"] == script.script_id


def test_task_rejects_script_that_fails_visual_director_readiness():
    brief, pack, evidence_graph, report, pedagogy, script, _, _ = fixture()
    segments = list(script.segments)
    segments[0] = segments[0].model_copy(
        update={"spoken_text": "Put the title at left: 120px."}
    )
    unsafe = script.model_copy(update={"segments": tuple(segments)})
    with pytest.raises(AgentContractError, match="not ready"):
        build_visual_director_task(
            brief, pack, evidence_graph, report, pedagogy, unsafe
        )


def test_storyboard_must_cover_script_exactly_once_and_in_order():
    *_, script, registry, output = fixture()
    scenes = output.storyboard.scenes[:-1]
    bad = output.model_copy(
        update={
            "storyboard": Storyboard(
                storyboard_id=output.storyboard.storyboard_id,
                script_id=script.script_id,
                scenes=scenes,
            ),
            "scenegraphs": output.scenegraphs[:-1],
        }
    )
    result = validate(bad, script, registry)
    assert VisualDirectorIssue.STORYBOARD_SCRIPT_COVERAGE in result.issues


def test_scenegraphs_must_match_storyboard_one_for_one_and_in_order():
    *_, script, registry, output = fixture()
    graphs = list(output.scenegraphs)
    graphs[0], graphs[1] = graphs[1], graphs[0]
    result = validate(
        output.model_copy(update={"scenegraphs": tuple(graphs)}),
        script,
        registry,
    )
    assert VisualDirectorIssue.SCENEGRAPH_SCENE_COVERAGE in result.issues


def test_teaching_function_must_match_mapped_script_segments():
    *_, script, registry, output = fixture()
    scenes = list(output.storyboard.scenes)
    scenes[1] = scenes[1].model_copy(
        update={"teaching_function": TeachingFunction.COMPARE}
    )
    bad_storyboard = output.storyboard.model_copy(update={"scenes": tuple(scenes)})
    result = validate(
        output.model_copy(update={"storyboard": bad_storyboard}),
        script,
        registry,
    )
    assert VisualDirectorIssue.TEACHING_FUNCTION_MISMATCH in result.issues


def test_scene_purpose_must_match_teaching_function_semantics():
    *_, script, registry, output = fixture()
    graphs = list(output.scenegraphs)
    graphs[1] = graphs[1].model_copy(update={"purpose": ScenePurpose.COMPARE})
    result = validate(
        output.model_copy(update={"scenegraphs": tuple(graphs)}),
        script,
        registry,
    )
    assert VisualDirectorIssue.SCENE_PURPOSE_MISMATCH in result.issues


def test_unknown_concept_ref_is_rejected():
    *_, script, registry, output = fixture()
    scenes = list(output.storyboard.scenes)
    scenes[1] = scenes[1].model_copy(
        update={
            "concept_refs": ("c_unknown",),
            "continuity_keys": ("concept:unknown",),
        }
    )
    graphs = list(output.scenegraphs)
    graphs[1] = graphs[1].model_copy(
        update={
            "nodes": [
                SceneNode(
                    id="unknown",
                    kind=NodeKind.CONCEPT,
                    label="Unknown",
                    concept_ref="c_unknown",
                    semantic_key="concept:unknown",
                )
            ],
            "relations": [],
        }
    )
    bad = output.model_copy(
        update={
            "storyboard": output.storyboard.model_copy(update={"scenes": tuple(scenes)}),
            "scenegraphs": tuple(graphs),
        }
    )
    result = validate(bad, script, registry)
    assert VisualDirectorIssue.UNKNOWN_CONCEPT_REF in result.issues
    assert VisualDirectorIssue.REGISTRY_VALIDATION_FAILED in result.issues


def test_semantic_key_must_match_registry_identity():
    *_, script, registry, output = fixture()
    graphs = list(output.scenegraphs)
    nodes = list(graphs[1].nodes)
    nodes[0] = nodes[0].model_copy(update={"semantic_key": "concept:wrong"})
    graphs[1] = graphs[1].model_copy(update={"nodes": nodes})
    result = validate(
        output.model_copy(update={"scenegraphs": tuple(graphs)}),
        script,
        registry,
    )
    assert VisualDirectorIssue.REGISTRY_VALIDATION_FAILED in result.issues


def test_storyboard_and_scenegraph_concept_sets_must_match():
    *_, script, registry, output = fixture()
    graphs = list(output.scenegraphs)
    graphs[1] = graphs[1].model_copy(update={"nodes": [graphs[1].nodes[0]], "relations": []})
    result = validate(
        output.model_copy(update={"scenegraphs": tuple(graphs)}),
        script,
        registry,
    )
    assert VisualDirectorIssue.SCENE_CONCEPT_SET_MISMATCH in result.issues


def test_continuity_keys_are_canonical_keys_for_scene_concepts():
    *_, script, registry, output = fixture()
    scenes = list(output.storyboard.scenes)
    scenes[1] = scenes[1].model_copy(update={"continuity_keys": ("concept:wrong",)})
    result = validate(
        output.model_copy(
            update={"storyboard": output.storyboard.model_copy(update={"scenes": tuple(scenes)})}
        ),
        script,
        registry,
    )
    assert VisualDirectorIssue.CONTINUITY_KEY_MISMATCH in result.issues


def test_empty_scenegraph_is_rejected():
    *_, script, registry, output = fixture()
    graphs = list(output.scenegraphs)
    graphs[0] = graphs[0].model_copy(update={"nodes": []})
    result = validate(
        output.model_copy(update={"scenegraphs": tuple(graphs)}),
        script,
        registry,
    )
    assert VisualDirectorIssue.EMPTY_SCENEGRAPH in result.issues


def test_visual_metadata_cannot_smuggle_pixel_or_renderer_instructions():
    *_, script, registry, output = fixture()
    scenes = list(output.storyboard.scenes)
    scenes[0] = scenes[0].model_copy(
        update={"visual_intent": "Place the title at left: 120px using FFmpeg."}
    )
    result = validate(
        output.model_copy(
            update={"storyboard": output.storyboard.model_copy(update={"scenes": tuple(scenes)})}
        ),
        script,
        registry,
    )
    assert VisualDirectorIssue.VISUAL_IMPLEMENTATION_DIRECTIVE in result.issues


def test_scenegraph_schema_rejects_geometry_fields():
    with pytest.raises(ValidationError):
        SceneNode(id="n1", kind=NodeKind.TEXT, x=120)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        LayoutHint(width=640)  # type: ignore[call-arg]


def test_visual_director_output_schema_is_semantic_only():
    schema = VisualDirectorOutput.model_json_schema()
    serialized = json.dumps(schema).lower()
    for forbidden in (
        '"x":',
        '"y":',
        '"pixel_x"',
        '"pixel_y"',
        '"font_size"',
        '"renderer"',
        '"ffmpeg"',
    ):
        assert forbidden not in serialized


def test_visual_director_surface_does_not_import_geometry_motion_or_renderer():
    paths = [
        ROOT / "visual_director" / "models.py",
        ROOT / "visual_director" / "registry.py",
        ROOT / "visual_director" / "gate.py",
        ROOT / "visual_director" / "hermes.py",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()
    for forbidden in (
        "from learnflow_v2.render",
        "import learnflow_v2.render",
        "from learnflow_v2.layout",
        "import learnflow_v2.layout",
        "from learnflow_v2.motion",
        "import learnflow_v2.motion",
        "deterministicpillowrenderer(",
    ):
        assert forbidden not in source



def _wire_visual_payload(output, script, registry, concept_order):
    payload = output.model_dump(mode="json")
    segment_index = {
        segment.segment_id: index
        for index, segment in enumerate(script.segments)
    }
    concept_entries = tuple(registry.resolve(item) for item in concept_order)
    concept_index = {
        entry.concept_id: index
        for index, entry in enumerate(concept_entries)
    }

    storyboard = payload["storyboard"]
    storyboard.pop("script_id", None)
    for scene in storyboard["scenes"]:
        scene["script_segment_indexes"] = [
            segment_index[item] for item in scene.pop("script_segment_ids")
        ]
        scene.pop("concept_refs", None)
        scene.pop("continuity_keys", None)

    scene_index = {
        scene["scene_id"]: index
        for index, scene in enumerate(storyboard["scenes"])
    }
    for graph in payload["scenegraphs"]:
        graph["scene_index"] = scene_index[graph.pop("scene_id")]
        graph.pop("purpose", None)
        for node in graph["nodes"]:
            ref = node.pop("concept_ref", None)
            node.pop("semantic_key", None)
            if ref is not None:
                node["concept_index"] = concept_index[ref]
    return payload


def test_visual_wire_schema_uses_indexes_for_all_dynamic_refs():
    brief, pack, evidence_graph, report, pedagogy, script, _, _ = fixture()
    task = build_visual_director_task(
        brief, pack, evidence_graph, report, pedagogy, script
    )
    schema = task["output_schema"]
    serialized = json.dumps(schema)
    scene_props = schema["$defs"]["StoryboardScene"]["properties"]
    graph_props = schema["$defs"]["SceneGraph"]["properties"]
    node_props = schema["$defs"]["SceneNode"]["properties"]
    storyboard_props = schema["$defs"]["Storyboard"]["properties"]

    assert "script_segment_indexes" in scene_props
    assert "script_segment_ids" not in scene_props
    assert "concept_refs" not in scene_props
    assert "continuity_keys" not in scene_props
    assert "scene_index" in graph_props
    assert "scene_id" not in graph_props
    assert "purpose" not in graph_props
    assert "concept_index" in node_props
    assert "concept_ref" not in node_props
    assert "semantic_key" not in node_props
    assert "script_id" not in storyboard_props
    assert "concept_catalog" in json.loads(task["context"])
    assert "script_segment_catalog" in json.loads(task["context"])
    assert '"x":' not in serialized.lower()
    assert '"y":' not in serialized.lower()


def test_host_assembles_visual_dynamic_refs_and_derives_concept_sets():
    *_, pedagogy, script, registry, output = fixture()
    wire = _wire_visual_payload(
        output,
        script,
        registry,
        pedagogy.concept_order,
    )
    assembled = assemble_visual_director_wire(
        wire,
        script=script,
        registry=registry,
        concept_order=pedagogy.concept_order,
    )
    assert assembled.to_canonical_json() == output.to_canonical_json()

    result = validate(assembled, script, registry)
    assert result.ready_for_core
    assert VisualDirectorIssue.SCENE_CONCEPT_SET_MISMATCH not in result.issues


def test_host_rejects_direct_dynamic_visual_references():
    *_, pedagogy, script, registry, output = fixture()
    wire = _wire_visual_payload(
        output,
        script,
        registry,
        pedagogy.concept_order,
    )
    wire["storyboard"]["scenes"][1]["concept_refs"] = ["c_forbidden"]
    with pytest.raises(AgentContractError, match="host-owned concept_refs"):
        assemble_visual_director_wire(
            wire,
            script=script,
            registry=registry,
            concept_order=pedagogy.concept_order,
        )


def test_host_rejects_duplicate_scenegraph_indexes():
    *_, pedagogy, script, registry, output = fixture()
    wire = _wire_visual_payload(
        output,
        script,
        registry,
        pedagogy.concept_order,
    )
    wire["scenegraphs"][1]["scene_index"] = wire["scenegraphs"][0]["scene_index"]
    with pytest.raises(AgentContractError, match="more than one SceneGraph"):
        assemble_visual_director_wire(
            wire,
            script=script,
            registry=registry,
            concept_order=pedagogy.concept_order,
        )



def test_visual_wire_schema_restricts_frozen_core_layout_vocabulary():
    brief, pack, evidence_graph, report, pedagogy, script, _, _ = fixture()
    task = build_visual_director_task(
        brief, pack, evidence_graph, report, pedagogy, script
    )
    schema = task["output_schema"]
    assert schema["$defs"]["LayoutIntent"]["enum"] == [
        "CONCEPT_CARD",
        "PROCESS",
        "COMPARISON",
        "HIERARCHY",
    ]
    assert schema["$defs"]["ReadingDirection"]["enum"] == [
        "LEFT_TO_RIGHT",
        "RIGHT_TO_LEFT",
        "TOP_TO_BOTTOM",
        "BOTTOM_TO_TOP",
    ]


def test_host_rejects_layout_zone_role_before_frozen_core():
    *_, pedagogy, script, registry, output = fixture()
    wire = _wire_visual_payload(
        output,
        script,
        registry,
        pedagogy.concept_order,
    )
    wire["scenegraphs"][0]["nodes"][0]["semantic_role"] = "TITLE"
    with pytest.raises(AgentContractError, match="layout-zone vocabulary"):
        assemble_visual_director_wire(
            wire,
            script=script,
            registry=registry,
            concept_order=pedagogy.concept_order,
        )


def test_host_rejects_unsupported_layout_intent_before_frozen_core():
    *_, pedagogy, script, registry, output = fixture()
    wire = _wire_visual_payload(
        output,
        script,
        registry,
        pedagogy.concept_order,
    )
    wire["scenegraphs"][0]["layout_intent"]["type"] = LayoutIntent.ILLUSTRATION.value
    with pytest.raises(AgentContractError, match="not supported by frozen Core"):
        assemble_visual_director_wire(
            wire,
            script=script,
            registry=registry,
            concept_order=pedagogy.concept_order,
        )



def test_host_derives_scene_purpose_from_teaching_function():
    *_, pedagogy, script, registry, output = fixture()
    wire = _wire_visual_payload(
        output,
        script,
        registry,
        pedagogy.concept_order,
    )
    # CHECK is a valid Script/Storyboard teaching function but is intentionally
    # not a ScenePurpose enum member. The host maps it to RECAP before Core.
    wire["storyboard"]["scenes"][0]["teaching_function"] = "CHECK"
    assembled = assemble_visual_director_wire(
        wire,
        script=script,
        registry=registry,
        concept_order=pedagogy.concept_order,
    )
    assert assembled.scenegraphs[0].purpose.value == "RECAP"


def test_host_rejects_model_owned_scene_purpose():
    *_, pedagogy, script, registry, output = fixture()
    wire = _wire_visual_payload(
        output,
        script,
        registry,
        pedagogy.concept_order,
    )
    wire["scenegraphs"][0]["purpose"] = "CHECK"
    with pytest.raises(AgentContractError, match="host-owned scene_id/purpose"):
        assemble_visual_director_wire(
            wire,
            script=script,
            registry=registry,
            concept_order=pedagogy.concept_order,
        )



def test_host_rejects_unsupported_directed_relation_before_frozen_core():
    *_, pedagogy, script, registry, output = fixture()
    wire = _wire_visual_payload(
        output,
        script,
        registry,
        pedagogy.concept_order,
    )
    process_index = next(
        index
        for index, graph in enumerate(wire["scenegraphs"])
        if graph["layout_intent"]["type"] == LayoutIntent.PROCESS.value
    )
    wire["scenegraphs"][process_index]["relations"][0]["kind"] = RelationKind.LABELS.value
    with pytest.raises(AgentContractError, match="directed-layout relations"):
        assemble_visual_director_wire(
            wire,
            script=script,
            registry=registry,
            concept_order=pedagogy.concept_order,
        )


def test_concept_card_may_keep_non_directed_annotation_relation():
    *_, pedagogy, script, registry, output = fixture()
    wire = _wire_visual_payload(
        output,
        script,
        registry,
        pedagogy.concept_order,
    )
    concept_card_index = next(
        index
        for index, graph in enumerate(wire["scenegraphs"])
        if graph["layout_intent"]["type"] == LayoutIntent.CONCEPT_CARD.value
        and graph["relations"]
    )
    assembled = assemble_visual_director_wire(
        wire,
        script=script,
        registry=registry,
        concept_order=pedagogy.concept_order,
    )
    assert assembled.scenegraphs[concept_card_index].layout_intent.type == LayoutIntent.CONCEPT_CARD



def test_visual_task_guides_core_feasible_semantic_topology():
    brief, pack, evidence_graph, report, pedagogy, script, _, _ = fixture()
    task = build_visual_director_task(
        brief, pack, evidence_graph, report, pedagogy, script
    )
    instructions = "\n".join(json.loads(task["context"])["instructions"])
    assert "Keep each SceneGraph semantically minimal" in instructions
    assert "Prefer CONCEPT_CARD" in instructions
    assert "frozen Core cannot lay out without scaling" in instructions
