# H-02 — LearnFlow Hermes plugin

H-02 exposes the frozen LearnFlow Core V2 as a small Hermes project plugin without making renderer internals agent-callable.

## Capability surface

The project plugin lives at:

```text
.hermes/plugins/learnflow/
```

It registers one toolset, `learnflow`, with exactly three tools:

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
  .hermes_runtime/h02/runs/<run_id>/render/scene.mp4
```

The model never receives an output-path parameter, render profile, FPS, CRF, FFmpeg expression, arbitrary Python renderer code, or pixel coordinates.

## Boundary

H-02 may import only public LearnFlow package facades. In particular, the plugin must not import `learnflow_v2.render.backend` or construct `DeterministicPillowRenderer` directly.

The render profile is fixed by the adapter:

```text
profile_id = hermes-h02
fps        = 30
crf        = 18
preset     = medium
```

Runtime output is always owned by the adapter under the ignored `.hermes_runtime/h02/runs/` tree. `LEARNFLOW_H02_RUNTIME_ROOT` exists only as an operator/test override and is not a model-facing tool argument.

## Hermes project-plugin activation

Hermes project plugins are disabled by default and require `HERMES_ENABLE_PROJECT_PLUGINS=true`.

At the exact H-01 pin (`f97608f178d1ffeca59860195ab7da295f7c8e5f`), the runtime loader scans project plugins but the `hermes plugins enable` CLI enumerates bundled/user plugins only. Do **not** rely on `hermes plugins enable learnflow` for this project-local plugin.

Instead, run the H-02 verifier with the pinned Hermes Python. It enables `learnflow` in the selected Hermes profile through the pinned config API, installs the plugin declaration through Hermes' own `plugin_python_deps.install_for_plugin_dir()`, discovers the project plugin, and dispatches create → run → render through the real Hermes tool registry.

Linux/macOS against the project-local H-01 profile:

```bash
HERMES_HOME="$PWD/.hermes_runtime/home" \
HERMES_ENABLE_PROJECT_PLUGINS=true \
.hermes_runtime/hermes-agent/venv/bin/python \
scripts/verify_hermes_h02_plugin.py
```

If the installer created `.venv` rather than `venv`, use that path.

PowerShell:

```powershell
$env:HERMES_HOME = (Resolve-Path ".hermes_runtime\home").Path
$env:HERMES_ENABLE_PROJECT_PLUGINS = "true"

$HermesPython = ".hermes_runtime\hermes-agent\venv\Scripts\python.exe"
if (-not (Test-Path $HermesPython)) {
    $HermesPython = ".hermes_runtime\hermes-agent\.venv\Scripts\python.exe"
}

& $HermesPython scripts\verify_hermes_h02_plugin.py
```

No LLM/API key is required for H-02 verification.

## Verification

Local contract/integration verification:

```bash
pytest -q --confcutdir=tests/hermes tests/hermes/test_h02_plugin.py
python scripts/verify_v2_core_freeze.py
```

Pinned Hermes discovery verification after installing H-01:

```bash
HERMES_ENABLE_PROJECT_PLUGINS=true \
  .hermes_runtime/hermes-agent/venv/bin/python \
  scripts/verify_hermes_h02_plugin.py
```

The H-02 integration test renders a real short MP4 with FFmpeg; it is not a mocked renderer test. The accepted PR run also executes all three capability tools through the exact pinned Hermes registry.

## H-01 dependency

H-01's offline contract is green, but its real OpenRouter smoke remains a user-local dependency. H-02 can be implemented and independently verified without an API key, but do not rewrite H-01 as PASS or call the sequential Hermes milestone closed until the real H-01 smoke returns `H01_LIVE=PASS`.

## Explicit non-goals

H-02 does not implement LearningBrief/ResearchPack/EvidenceGraph, research delegation, pedagogy, script generation, Visual Director, agent-aware QA routing, budget hooks, Skills, or Kanban. Those remain H-03+.
