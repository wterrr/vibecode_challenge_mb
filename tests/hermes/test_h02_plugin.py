from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = ROOT / ".hermes" / "plugins" / "learnflow"


class FakeContext:
    def __init__(self) -> None:
        self.tools: list[dict] = []

    def register_tool(self, **kwargs) -> None:
        self.tools.append(kwargs)


def _load_plugin():
    package_name = "learnflow_h02_test_plugin"
    for key in list(sys.modules):
        if key == package_name or key.startswith(package_name + "."):
            sys.modules.pop(key, None)
    spec = importlib.util.spec_from_file_location(
        package_name,
        PLUGIN_DIR / "__init__.py",
        submodule_search_locations=[str(PLUGIN_DIR)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = module
    spec.loader.exec_module(module)
    return module


def _decode(raw: str) -> dict:
    payload = json.loads(raw)
    assert isinstance(payload, dict)
    return payload


def _scene_payload() -> dict:
    return {
        "schema_version": "2.1",
        "scene_id": "h02_smoke",
        "purpose": "EXPLAIN",
        "concept": "Gradient descent",
        "nodes": [
            {
                "id": "title",
                "kind": "CONCEPT",
                "label": "Gradient descent",
                "semantic_role": "PRIMARY_CONCEPT",
                "style_refs": [],
            }
        ],
        "relations": [],
        "groups": [],
        "layout_intent": {
            "type": "CONCEPT_CARD",
            "reading_direction": "LEFT_TO_RIGHT",
        },
        "style_refs": [],
    }


def test_registers_exact_bounded_tool_surface():
    plugin = _load_plugin()
    ctx = FakeContext()
    plugin.register(ctx)

    assert [item["name"] for item in ctx.tools] == [
        "learnflow_create",
        "learnflow_run",
        "learnflow_render",
    ]
    assert {item["toolset"] for item in ctx.tools} == {"learnflow"}

    schemas = {item["name"]: item["schema"] for item in ctx.tools}
    create_props = set(schemas["learnflow_create"]["parameters"]["properties"])
    assert create_props == {"scene_graph", "motion_plan", "scene_duration"}
    assert set(schemas["learnflow_run"]["parameters"]["properties"]) == {"run_id"}
    assert set(schemas["learnflow_render"]["parameters"]["properties"]) == {"run_id"}

    forbidden_model_controls = {
        "output_path",
        "path",
        "fps",
        "crf",
        "preset",
        "render_profile",
        "renderer",
        "x",
        "y",
    }
    for schema in schemas.values():
        assert forbidden_model_controls.isdisjoint(schema["parameters"]["properties"])


def test_plugin_does_not_import_renderer_internals_or_execute_arbitrary_code():
    source = (PLUGIN_DIR / "tools.py").read_text(encoding="utf-8")
    assert "learnflow_v2.render.backend" not in source
    assert "DeterministicPillowRenderer" not in source
    assert "import subprocess" not in source
    assert "from subprocess" not in source
    assert "eval(" not in source
    assert "exec(" not in source
    assert "from learnflow_v2.render import" in source


def test_create_rejects_agent_geometry_without_writing_runtime(monkeypatch, tmp_path):
    plugin = _load_plugin()
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("LEARNFLOW_H02_RUNTIME_ROOT", str(runtime))

    scene = _scene_payload()
    scene["nodes"][0]["x"] = 123
    result = _decode(
        plugin.handle_create(
            {
                "scene_graph": scene,
                "scene_duration": 0.2,
            }
        )
    )

    assert result["success"] is False
    assert result["error"]["code"] == "H02_BOUNDARY_VIOLATION"
    assert "$.scene_graph.nodes[0].x" in result["forbidden_paths"]
    assert not runtime.exists()


def test_render_rejects_agent_renderer_controls(monkeypatch, tmp_path):
    plugin = _load_plugin()
    monkeypatch.setenv("LEARNFLOW_H02_RUNTIME_ROOT", str(tmp_path / "runtime"))
    result = _decode(plugin.handle_render({"run_id": "0" * 16, "fps": 120}))
    assert result["success"] is False
    assert result["error"]["code"] == "H02_UNEXPECTED_ARGUMENT"


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is required for real H-02 render")
def test_create_run_render_real_mp4(monkeypatch, tmp_path):
    plugin = _load_plugin()
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("LEARNFLOW_H02_RUNTIME_ROOT", str(runtime))

    created = _decode(
        plugin.handle_create(
            {
                "scene_graph": _scene_payload(),
                "scene_duration": 0.2,
            }
        )
    )
    assert created["success"] is True
    assert created["stage"] == "CREATED"
    run_id = created["run_id"]

    compiled = _decode(plugin.handle_run({"run_id": run_id}))
    assert compiled["success"] is True
    assert compiled["stage"] == "COMPILED"
    assert compiled["layout_feasible"] is True

    rendered = _decode(plugin.handle_render({"run_id": run_id}))
    assert rendered["success"] is True
    assert rendered["stage"] == "RENDERED"
    assert rendered["output"] == f".hermes_runtime/h02/runs/{run_id}/render/scene.mp4"
    assert rendered["frame_count"] == 6
    assert rendered["fps"] == 30

    physical = runtime / run_id / "render" / "scene.mp4"
    assert physical.is_file()
    assert physical.stat().st_size > 0
    assert (runtime / run_id / "render" / "artifact.json").is_file()
    assert (runtime / run_id / "layout.json").is_file()
    assert (runtime / run_id / "compiled_motion.json").is_file()

    # Re-render is deterministic at the adapter level and does not expose a new output path.
    cached = _decode(plugin.handle_render({"run_id": run_id}))
    assert cached["success"] is True
    assert cached["cached"] is True
    assert cached["frame_digest"] == rendered["frame_digest"]
