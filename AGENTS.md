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

## Hermes stage discipline

Work one named Hermes stage at a time in the order defined by `PLAN_V2.md`. Names in source control, runtime paths, CI, logs, status files, tests, and documentation must describe their purpose. Do not introduce opaque ordinal checkpoint codes.

Accepted stages:

- **Hermes Bootstrap — PASS.** The live OpenRouter smoke passed on 2026-10-06. The primary model was attempted first; the accepted free fallback `nvidia/nemotron-3.5-lightning:free` completed the read-tool round-trip. Offline verification and the Core Freeze guard also passed.
- **LearnFlow Capability Plugin — PASS.** The exact pinned Hermes runtime discovers the project plugin and dispatches `learnflow_create → learnflow_run → learnflow_render`. Integration verification renders a real MP4 and preserves the Core Freeze boundary.

Current stage: **Agent Contracts — IMPLEMENTED / VERIFYING**. The typed artifacts and regression verifier exist on the active branch; do not mark the stage PASS until CI and Core Freeze verification pass.

Do not implement Research Orchestration, Fact Verification, Pedagogy Agent, Script Agent, Visual Director, Agent-Aware QA, Hooks + Budget, Skills, or Kanban Durability during Agent Contracts. This stage defines data contracts only.

## LearnFlow Capability Plugin safety

The project-local plugin lives at `.hermes/plugins/learnflow/` and exposes exactly:

- `learnflow_create`
- `learnflow_run`
- `learnflow_render`

The model-facing surface is semantic only. It must not accept arbitrary output paths, pixel coordinates, absolute font sizes, renderer code, FFmpeg expressions, FPS/CRF/preset overrides, or renderer objects.

`learnflow_render` must call the public `learnflow_v2.render.render_scene_video` facade. The plugin must not import `learnflow_v2.render.backend` or instantiate `DeterministicPillowRenderer` directly.

Controlled artifacts belong under `.hermes_runtime/learnflow-plugin/runs/`. `LEARNFLOW_PLUGIN_RUNTIME_ROOT` is an operator/test override and is not a model-facing tool argument.

Project plugins are trusted-code opt-in. Enable project-plugin discovery only for this trusted repository with `HERMES_ENABLE_PROJECT_PLUGINS=true`.

## Hermes Bootstrap safety

The live smoke is read-only. It may read `hermes/bootstrap/tool_read_fixture.txt` and return the expected sentinel, but it must not edit repository files.

Use `openai/gpt-6-luna` as the primary model and `nvidia/nemotron-3.5-lightning:free` as the accepted no-credit fallback. Record which model actually passed.

Never commit API keys or copy them into logs. `OPENROUTER_API_KEY` belongs only in the local ignored `.env` file or process environment.

## Verification

Hermes Bootstrap:

```bash
python scripts/run_hermes_bootstrap_smoke.py --offline-fixture hermes/bootstrap/fixtures/successful_tool_roundtrip.jsonl
pytest -q --confcutdir=tests/hermes tests/hermes/test_bootstrap.py
python scripts/verify_v2_core_freeze.py
```

LearnFlow Capability Plugin:

```bash
pytest -q --confcutdir=tests/hermes tests/hermes/test_learnflow_plugin.py
python scripts/verify_v2_core_freeze.py
```

Pinned-runtime discovery and execution:

```bash
HERMES_ENABLE_PROJECT_PLUGINS=true \
  .hermes_runtime/hermes-agent/venv/bin/python \
  scripts/verify_learnflow_plugin.py
```

## Agent Contracts boundary

The public control-plane contracts live in `agent_contracts/`. Keep them renderer-independent and geometry-free.

Agent Contracts may define strict artifact schemas, cross-artifact reference validation, canonical serialization, provenance, run-audit records, and budget state. They must not execute research, generate pedagogy/script/storyboards with an LLM, invoke rendering, or implement delegation/hooks.

Verification:

```bash
python scripts/verify_agent_contracts.py
pytest -q --confcutdir=tests/hermes tests/hermes/test_agent_contracts.py
python scripts/verify_v2_core_freeze.py
```
