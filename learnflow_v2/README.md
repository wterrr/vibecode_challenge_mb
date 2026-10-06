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
V2 Renderer + Assembly                      PASS
Frozen V2 End-to-End Benchmark              PASS
CORE GATE                                   PASS
```

Official Core Gate engine commit:

```text
25c27da43e6645d2e9ac704958d619e3c96aa4b2
```

Official benchmark run: `37404184018`.

Run the fail-closed evaluator with:

```bash
python scripts/evaluate_v2_core_gate.py
```

See `benchmarks/core_gate/README.md` and `benchmarks/baselines/v2/`.

## Core Gate evidence

The frozen `v2-core-gate-v1` benchmark reuses exactly the three frozen V1 lessons:

- `photosynthesis`
- `ram_vs_ssd`
- `tcp_three_way_handshake`

Official results:

```text
render success                 100% (3/3)
fatal clipping                 0 / 9 scenes
fatal overlap                  0 / 9 scenes
invalid MotionPlan             0 / 9 scenes
selective repair success       100% (9/9)
deterministic reproducibility  100% (3/3)
V1→V2 critical regression      0 / 3
static composition delta       +5.54192634
VLM unavailable contract       PASS
local repair isolation         PASS
```

All three V2 final videos preserve the frozen V1 media contract:

```text
video codec: H.264
audio codec: AAC
resolution: 640x360
duration: 7.0s
```

The static-composition score is a narrow deterministic proxy, not a human aesthetic score.

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
deterministic V2 renderer + AAC mux + assembly
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
- V1 remains the rollback baseline until V2 Core Freeze is completed.

## Current modules

- `learnflow_v2.core` — canonical serialization, JSON-safe values, structured errors.
- `learnflow_v2.concepts` — canonical lesson-level semantic identity.
- `learnflow_v2.scenegraph` — semantic visual IR and V1 adapter.
- `learnflow_v2.layout` — measurement, safe zones, constraints, graph/specialized layout, production LayoutRouter, collision/preflight and continuity.
- `learnflow_v2.motion` — Tier-1 semantic motion grammar, narration beats, scheduling and property-track compilation.
- `learnflow_v2.transitions` — semantic cross-scene persistence and renderer capability negotiation.
- `learnflow_v2.qa` — deterministic scene QA plus optional structured VLM critic.
- `learnflow_v2.repair` — typed repair planning, artifact provenance/cache reuse, dependency invalidation and deterministic re-check binding.
- `learnflow_v2.videoqa` — structured whole-video critic for visual variety, continuity, style, pacing and pedagogical alignment.
- `learnflow_v2.render` — deterministic Pillow/FFmpeg renderer, Tier-1 motion playback, persistent MOVE transitions, AAC mux and video assembly.
- `learnflow_v2.core_gate` — fail-closed Core Gate evidence schema and evaluator.

## V1 and V2 baselines

V1 remains frozen under:

```text
benchmarks/fixtures/v1/
benchmarks/baselines/v1/baseline.json
```

V2 Core Gate evidence is frozen under:

```text
benchmarks/specs/v2_core_gate_v1.json
benchmarks/baselines/v2/
```

## Next engineering step

Core Gate is now satisfied. The next step from `PLAN_V2.md` is **CORE FREEZE**.

Do not start Hermes/V2D until Core Freeze explicitly records the accepted engine commit, benchmark evidence, rollback boundary and frozen contracts.
