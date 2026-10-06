# LearnFlow V2.1 Experimental Implementation

Source of truth: `PLAN_V2.md`.

## Current status

Implemented and reviewed checkpoints:

```text
V2-00  Freeze V1 + baseline                 PASS
V2-01  ConceptRegistry + SceneGraph         PASS
V2-02  Intrinsic measurement                PASS
V2-03  Layout zones + Kiwi constraints      PASS
V2-04  Graph layout                         PASS
V2-05  Collision + optimization             PASS
V2-06  Continuity layout                    PASS
V2-07  Motion Grammar Tier 1                PASS
V2-08  Narration Beat Alignment             PASS
V2-09  Motion Scheduler + Compiler          PASS
V2-10  Persistent Inter-Scene Transitions   PASS
V2-11  Deterministic QA                     PASS
V2-12  Optional VLM Critic                  PASS
V2-13  Repair + Dependency Invalidation     PASS
V2-14  Video Critic                         PASS
```

The V2C component checkpoints are complete, but **Core Gate is not yet passed**.

Current Core Gate decision for engine commit
`ca20c79c0e17f990ebfb4ed06f9b8988dbe74305` is:

```text
BLOCKED
```

Run the fail-closed evaluator with:

```bash
python scripts/evaluate_v2_core_gate.py
```

See `benchmarks/core_gate/README.md`.

## Why Core Gate is currently blocked

The repository still lacks evidence required by `PLAN_V2.md` for the following reasons:

1. **No V2 renderer/production integration exists.** The V2 packages compile semantics, layout, motion, transitions, QA, critic and repair artifacts, but there is no `learnflow_v2.render` end-to-end pixel/video path to benchmark.
2. **No frozen V2 end-to-end benchmark result exists** comparable to the frozen V1 baseline under `benchmarks/baselines/v1/`.
3. **No agreed V1-vs-V2 static-quality metric artifact exists**, so `V2 static quality > V1 baseline` cannot be claimed scientifically yet.

Missing evidence is treated as `BLOCKED`, never as an implicit PASS. Hermes/V2D must not start until Core Gate is actually satisfied.

## Architectural boundary

```text
LLM / agents decide meaning
        ↓
ConceptRegistry + SceneGraph
        ↓
deterministic Layout Engine
        ↓
Motion Grammar + Scheduler/Compiler
        ↓
InterSceneTransitionPlan
        ↓
renderer (still missing in V2)
        ↓
Deterministic QA
        ↓
optional VLM Critic
        ↓
typed Repair Engine + invalidation
        ↓
Video Critic
```

Non-negotiable rules:

- no arbitrary generated rendering code;
- no LLM-generated pixel coordinates;
- semantic identity is canonical through `ConceptRegistry`;
- cross-scene continuity is a typed transition artifact;
- VLM may diagnose and propose typed patches but does not own geometry/pixels;
- deterministic QA cannot be overridden by the critic;
- local repair must invalidate only affected downstream artifacts;
- deterministic artifacts are hash/provenance tracked;
- V1 remains the production rollback baseline until Core Gate passes.

## Current modules

- `learnflow_v2.core` — canonical serialization, JSON-safe values, structured errors.
- `learnflow_v2.concepts` — canonical lesson-level semantic identity.
- `learnflow_v2.scenegraph` — semantic visual IR and V1 adapter.
- `learnflow_v2.layout` — intrinsic measurement, safe zones, Kiwi/ELK/Graphviz layout, collision repair, feasibility scoring and continuity.
- `learnflow_v2.motion` — Tier-1 semantic motion grammar, narration beats, scheduling and property-track compilation.
- `learnflow_v2.transitions` — semantic cross-scene persistence and renderer capability negotiation.
- `learnflow_v2.qa` — deterministic scene QA plus optional structured VLM critic.
- `learnflow_v2.repair` — typed repair planning, artifact provenance/cache reuse, dependency invalidation and deterministic re-check binding.
- `learnflow_v2.videoqa` — structured whole-video critic for visual variety, continuity, style, pacing and pedagogical alignment.
- `learnflow_v2.core_gate` — fail-closed Core Gate evidence schema and evaluator.

## V1 baseline

V1 remains frozen under `app/` and has deterministic benchmark fixtures/results under:

```text
benchmarks/fixtures/v1/
benchmarks/baselines/v1/baseline.json
scripts/capture_v1_baseline.py
```

This is the comparison baseline. Do not replace it while evaluating V2.

## Next engineering work

The next work is **not Hermes**. It is to close Core Gate evidence gaps:

```text
V2 renderer / integration
        ↓
frozen V2 end-to-end benchmark
        ↓
agreed V1↔V2 static-quality metric
        ↓
measure all Core Gate criteria
        ↓
CORE GATE PASS
        ↓
CORE FREEZE
        ↓
V2D / Hermes
```
