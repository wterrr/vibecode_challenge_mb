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

Current checkpoint: H-01 Hermes bootstrap.

H-01 is limited to:

- pinned Hermes runtime metadata;
- OpenRouter/model configuration;
- project context;
- structured one-shot smoke testing;
- trajectory/session export;
- bootstrap documentation and tests.

Do not implement the LearnFlow Hermes plugin, research agents, pedagogy agents, Script Agent, Visual Director, QA routing, Skills, or Kanban in H-01.

## H-01 smoke safety

The H-01 live smoke must be read-only. It may read `hermes/h01/smoke_fixture.txt` and return the expected sentinel, but it must not edit repository files.

Never commit API keys or copy them into logs. `OPENROUTER_API_KEY` belongs only in the local ignored `.env` file or process environment.

## Verification

For H-01 offline verification:

```bash
python scripts/run_hermes_h01_smoke.py --offline-fixture hermes/h01/fixtures/stream_success.jsonl
pytest -q tests/hermes/test_h01_bootstrap.py
python scripts/verify_v2_core_freeze.py
```

A checkpoint is not considered H-01 PASS until the real OpenRouter smoke returns `H01_LIVE=PASS`.
