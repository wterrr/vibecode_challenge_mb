# LearnFlow V2.1 Experimental Implementation

Source of truth: `PLAN_V2.md`.

## Current status

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
V2 Renderer + A/V Assembly                  PASS
Frozen V2 End-to-End Benchmark v2           PASS
CORE GATE                                   PASS
CORE FREEZE                                 NEXT
Hermes / V2D                                NOT YET AUTHORIZED
```

## Official Core Gate evidence

Accepted engine commit:

```text
fdad3db1340d8b28175ab5382d800ff79df9a8a0
```

Corrected benchmark: `v2-core-gate-v2`  
Official workflow run: `37412433812`  
Official artifact: `11389249199`

Measured result:

```text
render success                 100% (3/3)
fatal clipping                 0 / 9
fatal overlap                  0 / 9
invalid MotionPlan             0 / 9
selective repair success       100% (9/9)
deterministic reproducibility  100% (3/3)
V1→V2 critical regressions     0 / 3
static composition delta       +6.0680719
VLM unavailable contract       PASS
local repair isolation         PASS
```

The static-composition metric is a narrow deterministic proxy:
V1 = 66.15013163, V2 = 72.21820353. It is not a human aesthetic score.

Run the fail-closed evaluator with:

```bash
python scripts/evaluate_v2_core_gate.py
```

See `benchmarks/core_gate/README.md` and `benchmarks/baselines/v2/`.

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
deterministic V2 renderer + AAC mux + subtitles + assembly
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
- deterministic QA cannot be overridden by VLM;
- repair invalidates only affected downstream artifacts;
- artifacts retain deterministic provenance/hashes;
- frozen Core Gate benchmark/spec must not be edited after acceptance;
- V1 remains the rollback reference until Core Freeze explicitly records the boundary.

## Evidence caveats

- `v2-core-gate-v1` is invalidated because its V1/V2 static-frame layers were not comparable and its
  text-fit contract was weaker.
- `v2-core-gate-v2` uses the same three V1 lessons and compares pre-subtitle scene clips on both sides.
- The frozen three-lesson corpus does not exercise persistent-object MOVE end-to-end; CP2.10 regression
  tests cover that contract separately.
- The benchmark inherits V1's deterministic 40-character subtitle truncation contract. That preserves
  benchmark parity but is not a claim that subtitle UX is production-complete.

## Core Freeze

Core Freeze is now recorded in `benchmarks/core_freeze/manifest.json` and enforced by
`scripts/verify_v2_core_freeze.py` plus the `V2 Core Freeze Guard` workflow.

Frozen boundary:

```text
accepted Core engine   fdad3db1340d8b28175ab5382d800ff79df9a8a0
official evidence      4b2cc7887773a8fb81dee36010fcae3bc2015ccb
rollback/reference V1  f6dae0e8510a6db8fc49a761eddc2a055ffaefda
benchmark              v2-core-gate-v2
```

Hermes may consume Core through typed contracts and add orchestration outside the protected Core
namespaces. Any protected Core change requires an explicit unfreeze → re-gate → re-freeze cycle.

## Next engineering step

```text
CORE GATE PASS
      ↓
CORE FREEZE COMPLETE
      ↓
V2D / Hermes
      ↓
Hermes Bootstrap
```

The Core is no longer an open implementation surface for routine Hermes work.
