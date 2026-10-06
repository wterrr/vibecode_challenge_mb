# LearnFlow Capability Plugin

This stage exposes the frozen LearnFlow Core V2 as a small Hermes project plugin without making renderer internals agent-callable.

## Status

**PASS**

Hermes discovers the project plugin through the exact pinned runtime and successfully dispatches the complete capability sequence:

```text
learnflow_create
  semantic SceneGraph + optional untriggered Tier-1 MotionPlan
        ↓
  controlled deterministic run id

learnflow_run
  run id
        ↓
  public Core V2 compile contracts
  SceneGraph → LayoutGraph → MotionSchedule → CompiledMotionArtifact

learnflow_render
  compiled run id
        ↓
  public learnflow_v2.render.render_scene_video()
        ↓
  .hermes_runtime/learnflow-plugin/runs/<run_id>/render/scene.mp4
```

The integration suite renders a real MP4 with FFmpeg, and the Core Freeze guard remains green.

## Boundary

The model never receives an output-path parameter, render profile, FPS, CRF, FFmpeg expression, arbitrary Python renderer code, or pixel coordinates.

The plugin imports only public LearnFlow package facades. It must not import `learnflow_v2.render.backend` or construct `DeterministicPillowRenderer` directly.

The render profile is fixed by the adapter:

```text
profile_id = hermes-learnflow
fps        = 30
crf        = 18
preset     = medium
```

Runtime output is owned by the adapter under the ignored `.hermes_runtime/learnflow-plugin/runs/` tree. `LEARNFLOW_PLUGIN_RUNTIME_ROOT` exists only as an operator/test override and is not a model-facing tool argument.

## Project-plugin activation

Hermes project plugins are disabled by default and require `HERMES_ENABLE_PROJECT_PLUGINS=true`.

At the exact pinned Hermes commit `f97608f178d1ffeca59860195ab7da295f7c8e5f`, the verifier enables the plugin through the pinned config API, installs declared dependencies through Hermes' own dependency API, discovers the project plugin, and dispatches create → run → render through the real Hermes registry.

PowerShell:

```powershell
$env:HERMES_HOME = (Resolve-Path ".hermes_runtime\home").Path
$env:HERMES_ENABLE_PROJECT_PLUGINS = "true"

$HermesPython = ".hermes_runtime\hermes-agent\venv\Scripts\python.exe"
if (-not (Test-Path $HermesPython)) {
    $HermesPython = ".hermes_runtime\hermes-agent\.venv\Scripts\python.exe"
}

& $HermesPython scripts\verify_learnflow_plugin.py
```

Linux/macOS:

```bash
HERMES_HOME="$PWD/.hermes_runtime/home" \
HERMES_ENABLE_PROJECT_PLUGINS=true \
.hermes_runtime/hermes-agent/venv/bin/python \
scripts/verify_learnflow_plugin.py
```

No LLM/API key is required for plugin verification.

## Verification

```bash
pytest -q --confcutdir=tests/hermes tests/hermes/test_learnflow_plugin.py
python scripts/verify_v2_core_freeze.py
```

## Scope boundary

This stage is only the bounded capability adapter. Agent data contracts, research delegation, pedagogy, script generation, Visual Director behavior, agent-aware QA routing, budget hooks, Skills, and Kanban are separate later stages.
