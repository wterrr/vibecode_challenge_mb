from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_contracts import AgentContractError, PedagogyExample, Storyboard
from end_to_end_orchestration import STAGE_ORDER, run_end_to_end
from end_to_end_orchestration.core import _parse_response
from research_orchestration import ResearchOrchestrationResult, ResearchRole
from scripts.verify_end_to_end_orchestration import build_fixture_runner
from scripts.verify_script_agent import build_fixture, build_script
from scripts.verify_visual_director import build_visual_output
from visual_director import build_visual_concept_registry


class FakeCoreGateway:
    def __init__(self, tmp_path: Path):
        self.tmp_path = tmp_path
        self.calls = 0

    def render_lesson(self, *, scenegraphs, storyboard_scenes, script, output_path):
        from end_to_end_orchestration.models import SceneRenderReceipt
        from learnflow_v2.render import RenderArtifactKind, RenderedArtifact

        self.calls += 1
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake-mp4")
        receipts = tuple(
            SceneRenderReceipt(
                scene_id=graph.scene_id,
                capability_run_id=f"run{index:013d}",
                output=f"scene-{index}.mp4",
                duration=1.0,
                frame_digest="a" * 64,
                source_hash="b" * 64,
            )
            for index, graph in enumerate(scenegraphs, start=1)
        )
        artifact = RenderedArtifact(
            artifact_id="video:final",
            kind=RenderArtifactKind.VIDEO,
            path=str(output),
            duration=float(len(scenegraphs)),
            width=1280,
            height=720,
            fps=30,
            frame_count=30 * len(scenegraphs),
            frame_digest="c" * 64,
            source_hash="d" * 64,
        )
        return receipts, artifact


def test_acceptance_verifier_is_wired():
    text = (ROOT / "scripts" / "verify_end_to_end_orchestration.py").read_text(
        encoding="utf-8"
    )
    assert "END_TO_END_ORCHESTRATION=PASS" in text
    assert "learnflow_capability_pipeline=PASS" in text


def test_stage_order_is_explicit_and_complete():
    assert STAGE_ORDER == (
        "research_orchestration",
        "fact_verification",
        "pedagogy_agent",
        "script_agent",
        "visual_director",
        "core_v2",
        "video_assembly",
    )


def test_good_chain_reaches_core_and_writes_bundle(tmp_path):
    brief, runner = build_fixture_runner()
    core = FakeCoreGateway(tmp_path)
    result = run_end_to_end(
        brief,
        runner=runner,
        core_gateway=core,
        runtime_root=tmp_path / "runs",
    )
    assert core.calls == 1
    assert [item["stage"] for item in runner.calls] == [
        "research_orchestration",
        "pedagogy_agent",
        "script_agent",
        "visual_director",
    ]
    assert Path(result.final_video.path).is_file()
    run_dir = Path(result.artifact_root)
    assert (run_dir / "artifact_manifest.json").is_file()
    assert len(list((run_dir / "scenegraphs").glob("*.json"))) == len(result.scenegraphs)


def test_same_semantic_chain_has_stable_run_id(tmp_path):
    brief1, runner1 = build_fixture_runner()
    brief2, runner2 = build_fixture_runner()
    one = run_end_to_end(
        brief1,
        runner=runner1,
        core_gateway=FakeCoreGateway(tmp_path),
        runtime_root=tmp_path / "a",
    )
    two = run_end_to_end(
        brief2,
        runner=runner2,
        core_gateway=FakeCoreGateway(tmp_path),
        runtime_root=tmp_path / "b",
    )
    assert one.run_id == two.run_id


def test_invalid_pedagogy_stops_before_script_visual_and_core(tmp_path):
    brief, pack, graph, _report, pedagogy = build_fixture()
    script = build_script(pedagogy)
    registry = build_visual_concept_registry(pedagogy)
    visual = build_visual_output(script, registry)
    research = ResearchOrchestrationResult(
        research_pack=pack,
        evidence_graph=graph,
        specialist_roles=(ResearchRole.CONCEPT, ResearchRole.EVIDENCE),
    )
    invalid = pedagogy.model_copy(
        update={
            "worked_examples": (
                PedagogyExample(
                    example_id="bad",
                    concept="second",
                    description="Blocked claim.",
                    claim_ids=("C2",),
                ),
            )
        }
    )

    class Runner:
        calls = []
        def run(self, *, stage, task, output_model):
            self.calls.append(stage)
            return {
                "research_orchestration": research,
                "pedagogy_agent": invalid,
                "script_agent": script,
                "visual_director": visual,
            }[stage]

    runner = Runner()
    core = FakeCoreGateway(tmp_path)
    with pytest.raises(AgentContractError, match="not ready"):
        run_end_to_end(
            brief,
            runner=runner,
            core_gateway=core,
            runtime_root=tmp_path / "runs",
        )
    assert runner.calls == ["research_orchestration", "pedagogy_agent"]
    assert core.calls == 0


def test_invalid_script_stops_before_visual_and_core(tmp_path):
    brief, runner = build_fixture_runner()
    bad_script = runner._outputs["script_agent"]
    segments = list(bad_script.segments)
    segments[0] = segments[0].model_copy(
        update={"spoken_text": "Put this at left: 120px."}
    )
    runner._outputs["script_agent"] = bad_script.model_copy(
        update={"segments": tuple(segments)}
    )
    core = FakeCoreGateway(tmp_path)
    with pytest.raises(AgentContractError, match="not ready"):
        run_end_to_end(
            brief,
            runner=runner,
            core_gateway=core,
            runtime_root=tmp_path / "runs",
        )
    assert [item["stage"] for item in runner.calls] == [
        "research_orchestration",
        "pedagogy_agent",
        "script_agent",
    ]
    assert core.calls == 0


def test_invalid_visual_stops_before_core(tmp_path):
    brief, runner = build_fixture_runner()
    visual = runner._outputs["visual_director"]
    scenes = list(visual.storyboard.scenes)
    scenes[0] = scenes[0].model_copy(
        update={"visual_intent": "Place title at x=100."}
    )
    runner._outputs["visual_director"] = visual.model_copy(
        update={
            "storyboard": visual.storyboard.model_copy(
                update={"scenes": tuple(scenes)}
            )
        }
    )
    core = FakeCoreGateway(tmp_path)
    with pytest.raises(AgentContractError, match="not Core-ready"):
        run_end_to_end(
            brief,
            runner=runner,
            core_gateway=core,
            runtime_root=tmp_path / "runs",
        )
    assert core.calls == 0


def test_fact_verification_occurs_before_pedagogy_context(tmp_path):
    brief, runner = build_fixture_runner()

    original = runner.run
    def run(*, stage, task, output_model):
        if stage == "pedagogy_agent":
            context = json.loads(task["context"])
            claim_ids = [item["claim_id"] for item in context["research"]["claims"]]
            assert claim_ids == ["C1"]
            assert context["fact_verification"]["blocked_claim_ids"] == ["C2"]
        return original(stage=stage, task=task, output_model=output_model)

    runner.run = run
    run_end_to_end(
        brief,
        runner=runner,
        core_gateway=FakeCoreGateway(tmp_path),
        runtime_root=tmp_path / "runs",
    )


def test_visual_task_is_created_only_after_script_gate(tmp_path):
    brief, runner = build_fixture_runner()
    run_end_to_end(
        brief,
        runner=runner,
        core_gateway=FakeCoreGateway(tmp_path),
        runtime_root=tmp_path / "runs",
    )
    assert runner.calls[-1]["stage"] == "visual_director"


def test_core_receives_exact_visual_scene_order(tmp_path):
    brief, runner = build_fixture_runner()

    class InspectCore(FakeCoreGateway):
        def render_lesson(self, *, scenegraphs, storyboard_scenes, script, output_path):
            assert [g.scene_id for g in scenegraphs] == [s.scene_id for s in storyboard_scenes]
            return super().render_lesson(
                scenegraphs=scenegraphs,
                storyboard_scenes=storyboard_scenes,
                script=script,
                output_path=output_path,
            )

    run_end_to_end(
        brief,
        runner=runner,
        core_gateway=InspectCore(tmp_path),
        runtime_root=tmp_path / "runs",
    )


def test_capability_failure_is_fail_closed():
    with pytest.raises(RuntimeError, match="learnflow_create failed"):
        _parse_response(
            json.dumps(
                {
                    "success": False,
                    "error": {"code": "TEST", "message": "blocked"},
                }
            ),
            action="learnflow_create",
        )


def test_artifact_manifest_hashes_typed_files(tmp_path):
    brief, runner = build_fixture_runner()
    result = run_end_to_end(
        brief,
        runner=runner,
        core_gateway=FakeCoreGateway(tmp_path),
        runtime_root=tmp_path / "runs",
    )
    manifest = json.loads(
        (Path(result.artifact_root) / "artifact_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    paths = {item["path"] for item in manifest["artifacts"]}
    assert "learning_brief.json" in paths
    assert "render_manifest.json" in paths
    assert any(path.startswith("scenegraphs/") for path in paths)


def test_orchestration_surface_does_not_import_renderer_backend():
    files = [
        ROOT / "end_to_end_orchestration" / "coordinator.py",
        ROOT / "end_to_end_orchestration" / "core.py",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in files).lower()
    assert "learnflow_v2.render.backend" not in source
    assert "deterministicpillowrenderer" not in source
    assert ".hermes.plugins.learnflow" not in source


def test_no_later_stage_implementation_leaks_into_this_checkpoint():
    files = list((ROOT / "end_to_end_orchestration").glob("*.py"))
    source = "\n".join(path.read_text(encoding="utf-8") for path in files).lower()
    for forbidden in (
        "agent-aware qa",
        "pre_tool_call",
        "post_tool_call",
        "budgetledger(",
        "kanban",
    ):
        assert forbidden not in source
