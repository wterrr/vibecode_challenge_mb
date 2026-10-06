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

Hermes project plugins are disabled by default. Run the pinned H-01 runtime from the repository root with:

```bash
export HERMES_ENABLE_PROJECT_PLUGINS=true
```

and enable the plugin in the Hermes profile:

```bash
.hermes_runtime/hermes-agent/venv/bin/hermes plugins enable learnflow
```

On Windows, use the corresponding `venv\Scripts\hermes.exe` (or `.venv\Scripts\hermes.exe`) installed by H-01.

The repository verifier does not require an LLM/API key. It creates an isolated Hermes home that enables only the LearnFlow project plugin, then checks discovery against the exact pinned H-01 Hermes runtime.

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

The H-02 integration test renders a real short MP4 with FFmpeg; it is not a mocked renderer test.

## H-01 dependency

H-01's offline contract is green, but its real OpenRouter smoke remains a user-local dependency. H-02 can be implemented and independently verified without an API key, but do not rewrite H-01 as PASS or call the sequential Hermes milestone closed until the real H-01 smoke returns `H01_LIVE=PASS`.

## Explicit non-goals

H-02 does not implement LearningBrief/ResearchPack/EvidenceGraph, research delegation, pedagogy, script generation, Visual Director, agent-aware QA routing, budget hooks, Skills, or Kanban. Those remain H-03+.
