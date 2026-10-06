# LearnFlow Agent Instructions

## Project goal

LearnFlow V2 generates educational videos through a typed semantic pipeline. Hermes is the control plane; LearnFlow Core V2 is the deterministic production engine.

## Architecture boundary

Hermes may own research strategy, evidence judgment, pedagogy, narrative, semantic visual direction, semantic QA, orchestration, and repair intent.

Hermes must not own geometry, pixel coordinates, renderer implementation, layout constraints, timeline arithmetic, schema validation, codec validation, retry accounting, cost accounting, atomic publication, or security policy.

## Frozen Core

The current Core Freeze is authoritative at:

- `benchmarks/core_freeze/manifest.json`
- `scripts/verify_v2_core_freeze.py`

Before changing any Core-adjacent implementation, run:

```bash
python scripts/verify_v2_core_freeze.py
```

Do not modify files protected by the Core Freeze manifest during routine Hermes work. A genuine Core change requires the explicit CORE UNFREEZE → regression → Core Gate → evidence freeze → new Core Freeze cycle.

## Hermes checkpoint discipline

Work one Hermes checkpoint at a time in the order defined by `PLAN_V2.md`.

Current implementation checkpoint: H-02 LearnFlow plugin.

H-01 implementation and offline CI are complete, but its real OpenRouter smoke is still a required dependency. A checkpoint is not considered H-01 PASS until the real OpenRouter smoke returns `H01_LIVE=PASS`. Do not rewrite H-01 as PASS without that evidence.

H-02 is limited to:

- a project-local Hermes plugin under `.hermes/plugins/learnflow/`;
- the bounded capability tools `learnflow_create`, `learnflow_run`, and `learnflow_render`;
- consuming public frozen Core V2 package facades;
- controlled run artifacts under `.hermes_runtime/h02/runs/`;
- plugin-discovery, boundary, compile, render, and Core Freeze regression tests;
- H-02 documentation and checkpoint evidence.

Do not implement H-03+ agent contracts, research delegation, pedagogy agents, Script Agent, Visual Director, agent-aware QA routing, budget hooks, Skills, or Kanban during H-02.

## H-02 capability safety

The model-facing H-02 surface is semantic only. It must not accept arbitrary output paths, pixel coordinates, absolute font sizes, renderer code, FFmpeg expressions, FPS/CRF/preset overrides, or renderer objects.

`learnflow_render` must call the public `learnflow_v2.render.render_scene_video` facade. H-02 must not import `learnflow_v2.render.backend` or instantiate `DeterministicPillowRenderer` directly.

Project plugins are trusted-code opt-in. Enable project-plugin discovery only for this trusted repository with `HERMES_ENABLE_PROJECT_PLUGINS=true`.

## H-01 smoke safety

The H-01 live smoke must be read-only. It may read `hermes/h01/smoke_fixture.txt` and return the expected sentinel, but it must not edit repository files. Use `openai/gpt-6-luna` as the primary model; the only accepted no-credit fallback for H-01 is `nvidia/nemotron-3.5-lightning:free`, and the result must record which model actually passed.

Never commit API keys or copy them into logs. `OPENROUTER_API_KEY` belongs only in the local ignored `.env` file or process environment.

## Verification

H-02 verification:

```bash
pytest -q --confcutdir=tests/hermes tests/hermes/test_h02_plugin.py
python scripts/verify_v2_core_freeze.py
```

After installing the exact H-01 Hermes pin, verify real project-plugin discovery with:

```bash
HERMES_ENABLE_PROJECT_PLUGINS=true \
  .hermes_runtime/hermes-agent/venv/bin/python \
  scripts/verify_hermes_h02_plugin.py
```

H-01 live verification remains separately required:

```bash
python scripts/run_hermes_h01_smoke.py
```

The sequential Hermes milestone is not closed until H-01 has real live evidence and H-02 has its own accepted verification evidence.
