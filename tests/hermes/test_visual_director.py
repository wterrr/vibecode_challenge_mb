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
from learnflow_v2.scenegraph import LayoutHint, NodeKind, SceneNode, ScenePurpose
from scripts.verify_script_agent import build_fixture, build_script
from scripts.verify_visual_director import build_visual_output
from visual_director import (
    VisualDirectorIssue,
    VisualDirectorOutput,
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
        "concept_registry",
        "concept_order",
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
