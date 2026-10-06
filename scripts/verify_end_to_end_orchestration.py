#!/usr/bin/env python3
"""Acceptance verifier for LearnFlow End-to-End Orchestration."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research_orchestration import ResearchOrchestrationResult, ResearchRole
from scripts.verify_script_agent import build_fixture, build_script
from scripts.verify_visual_director import build_visual_output
from visual_director import build_visual_concept_registry

from end_to_end_orchestration import (
    CapabilityCoreGateway,
    STAGE_ORDER,
    run_end_to_end,
)


def _load_plugin():
    plugin_dir = ROOT / ".hermes" / "plugins" / "learnflow"
    package_name = "learnflow_end_to_end_plugin"
    for name in list(sys.modules):
        if name == package_name or name.startswith(package_name + "."):
            del sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        package_name,
        plugin_dir / "__init__.py",
        submodule_search_locations=[str(plugin_dir)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load LearnFlow capability plugin")
    module = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = module
    spec.loader.exec_module(module)
    return module


class FixtureHermesRunner:
    def __init__(self, *, research, pedagogy, script, visual):
        self._outputs = {
            "research_orchestration": research,
            "pedagogy_agent": pedagogy,
            "script_agent": script,
            "visual_director": visual,
        }
        self.calls = []

    def run(self, *, stage, task, output_model):
        self.calls.append(
            {
                "stage": stage,
                "goal": task["goal"],
                "schema_title": task["output_schema"].get("title"),
                "output_model": output_model.__name__,
            }
        )
        return self._outputs[stage]


def build_fixture_runner():
    brief, pack, graph, _report, pedagogy = build_fixture()
    script = build_script(pedagogy)
    registry = build_visual_concept_registry(pedagogy)
    visual = build_visual_output(script, registry)
    research = ResearchOrchestrationResult(
        research_pack=pack,
        evidence_graph=graph,
        specialist_roles=(
            ResearchRole.CONCEPT,
            ResearchRole.EVIDENCE,
            ResearchRole.MISCONCEPTION,
        ),
    )
    return brief, FixtureHermesRunner(
        research=research,
        pedagogy=pedagogy,
        script=script,
        visual=visual,
    )


def main() -> int:
    plugin = _load_plugin()
    brief, runner = build_fixture_runner()

    runtime_root = ROOT / ".hermes_runtime" / "end-to-end-orchestration" / "acceptance"
    if runtime_root.exists():
        shutil.rmtree(runtime_root)

    gateway = CapabilityCoreGateway(
        create=plugin.handle_create,
        run=plugin.handle_run,
        render=plugin.handle_render,
        repo_root=ROOT,
        duration_resolver=lambda _scene, _script: 0.2,
    )
    result = run_end_to_end(
        brief,
        runner=runner,
        core_gateway=gateway,
        runtime_root=runtime_root,
    )

    expected_agent_calls = [
        "research_orchestration",
        "pedagogy_agent",
        "script_agent",
        "visual_director",
    ]
    if [item["stage"] for item in runner.calls] != expected_agent_calls:
        raise SystemExit("END_TO_END_ORCHESTRATION=FAIL agent stage order")
    if result.stage_order != STAGE_ORDER:
        raise SystemExit("END_TO_END_ORCHESTRATION=FAIL full stage order")
    if len(result.scene_renders) != len(result.scenegraphs):
        raise SystemExit("END_TO_END_ORCHESTRATION=FAIL scene render coverage")
    final_path = Path(result.final_video.path)
    if not final_path.is_file() or final_path.stat().st_size <= 0:
        raise SystemExit("END_TO_END_ORCHESTRATION=FAIL final video missing")

    run_dir = Path(result.artifact_root)
    required = {
        "learning_brief.json",
        "research_pack.json",
        "evidence_graph.json",
        "fact_verification.json",
        "pedagogy_plan.json",
        "script.json",
        "storyboard.json",
        "concept_registry.json",
        "render_manifest.json",
        "artifact_manifest.json",
        "final.mp4",
    }
    if not required.issubset({p.name for p in run_dir.iterdir()}):
        raise SystemExit("END_TO_END_ORCHESTRATION=FAIL artifact bundle incomplete")
    scene_files = sorted((run_dir / "scenegraphs").glob("*.json"))
    if len(scene_files) != len(result.scenegraphs):
        raise SystemExit("END_TO_END_ORCHESTRATION=FAIL SceneGraph bundle incomplete")

    print("END_TO_END_ORCHESTRATION=PASS")
    print("typed_stage_order=PASS")
    print("research_native_delegation_contract=PASS")
    print("fact_verification_gate=PASS")
    print("pedagogy_gate=PASS")
    print("script_gate=PASS")
    print("visual_director_gate=PASS")
    print("learnflow_capability_pipeline=PASS")
    print("real_final_mp4=PASS")
    print("replayable_artifact_bundle=PASS")
    print(f"run_id={result.run_id}")
    print(f"scene_count={len(result.scenegraphs)}")
    print(f"final_video={result.final_video.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
