# V3-04 — Visual Pattern Router: deterministic eligibility & abstention

**Date:** 2026-10-08
**Verdict:** **PASS — OFFLINE ROUTING ONLY; RENDER NOT READY**
**Repository:** https://github.com/wterrr/vibecode_challenge_mb
**Stack base:** PR [#36](https://github.com/wterrr/vibecode_challenge_mb/pull/36), head `437766397ea4a170e7d0671f0cfb4885947724a5`. Its bases [#35](https://github.com/wterrr/vibecode_challenge_mb/pull/35) and [#34](https://github.com/wterrr/vibecode_challenge_mb/pull/34) remain unmerged.
**Branch:** `chatgpt/v3-04-visual-pattern-router`; source code reviewed at commit `9c6532076834bb3dae03699ed8f90ca98c67e068`. `main` unchanged `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6`.

## 1. Reuse-first implementation audit

| Existing code or external source | Choice | Technical rationale |
| --- | --- | --- |
| V2 `visual_director/gate.py::validate_visual_director_output` | **REUSE directly** | Accept/reject teaching function, purpose, canonical concept, continuity and scene references before any routing |
| V2 `learnflow_v2/scenegraph/enums.py` | **REUSE directly** | Exact `ScenePurpose`, `LayoutIntent`, `RelationKind`, `NodeKind` finite taxonomies; semantic layout, not coordinate ownership |
| V2 `learnflow_v2/repair::compute_content_hash` | **REUSE directly** | Deterministic evidence/decision hash; no fork of hashing/invalidation logic |
| V3-02 `VisualTeachingPlan`, `VisualPatternSpec`, `StateLedger` | **REUSE directly** | Cross-artifact IDs, bounded `RepresentationType`, beat/source/state provenance |
| V3-03 `audit_signal_preservation` | **REUSE directly** | Recomputes typed semantic bindings, trace declarations and unused-signal inventory; cannot be bypassed by caller-supplied arbitrary hash |
| V2 `LayoutGraph` physical solvers | **DEFER / no changes** | Coordinates/rendering belong to V3-06+, outside V3-04; no reason to invoke solver yet |
| Manim Community / Code2Video | **NOT IMPORTED** | Optional rendering/planning libraries, not necessary for deterministic routing; revisit with pinned commit/license/deps at renderer checkpoint |
| ALGOGEN-lab | **LICENSE BLOCKED / STUDY ONLY** | No copying from code lacking verified reusable license |

Only new logic is the small project-owned bounded eligibility/variant table in `learnflow_v3/pattern_router.py`, public import in `learnflow_v3/__init__.py`, offline tests and CI. No external source code was copied, no new dependencies or model calls.

## 2. Frozen routing behavior

| Existing typed family | Positive conditions | Variants / fallback boundary |
| --- | --- | --- |
| `WORKED_EXAMPLE_BOARD` | Explicit section option; `DEMONSTRATE/DRILLDOWN` purpose; `PROCESS/GRID` layout; verified-ref declaration, `SEQUENCE` semantic object, dynamic teaching beat, ≥2 ledger steps, stateful requirement | `TRACE_SPOTLIGHT` budget ≥6 → same-family `TRACE_COMPACT` budget ≥3; missing dynamics/steps always abstains |
| `PROCESS_FLOW` | Explicit section option; `EXPLAIN/DEMONSTRATE`; `PROCESS/HIERARCHY` layout; typed `PROCESS` and directed `FLOW/SEQUENCE_BEFORE` relation; static teaching beats | `PROCESS_NETWORK` if branching graph and budget ≥6; `PROCESS_LINEAR` iff directed single path and budget ≥3. Branching at budget 3 → ABSTAIN, never flattened |
| `EQUATION_GRAPH` | Explicit section option, `EQUATION` semantic object, V2 MATH/EQUATION node, `ILLUSTRATION/GRID/FREEFORM` intent, static proof context | `EQUATION_SPOTLIGHT` budget ≥6 → `EQUATION_COMPACT` budget ≥3, same semantic equation family |
| `CONCEPT_CARD` | **Only explicitly requested** as section's sole option; static justification, `RECAP/SUMMARIZE` purpose, `CONCEPT_CARD` intent, LABEL objects and STATIC requirement | `INTENTIONAL_RECAP_CARD` only; never available as an implicit fallback for process, worked example or equation |

All pattern choices originate from an **existing valid** `VisualPatternSpec`; the router does not invent concept IDs, code, traces or graphical assets. For incompatible layout intent, unallowed section options, wrong purpose/object types, missing dynamic evidence, cross-family fallback or insufficient visual budget, routing fails closed or produces typed `ABSTAIN` reason. No arbitrary Python, pixel coordinate fields, promoted paid-provider model or renderer code.

Output `VisualPatternRoute`: schema/version, status `SELECTED_UNRENDERABLE` vs `ABSTAIN`, stable selected family/variant, ordered evidence attempts, fallback bit, exact V3-03 source audit hash and deterministic decision hash. `render_ready` is type-locked to **False**, `renderer_implementation` to **NOT_IMPLEMENTED**, and `require_renderer()` always raises `V3_04_NO_RENDERER_PROOF`. A semantic selection does **not** license generating/running a video, asserting pixels changed or claiming learning gains.

## 3. Measured offline evidence (source commit)

First offline run [#37732597453](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37732597453) **FAILED 1/58**: branched process with insufficient budget was incorrectly collapsed into linear. Root cause: budget-only fallback eligibility ignored topology. The implementation was corrected to check branching degrees, directed single-path connectivity and budget together (and to reuse Visual Director's purpose/cross-scene gate). The successful correction [#37732710523](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37732710523) validated the fix.

Final code commit [`9c653207`](https://github.com/wterrr/vibecode_challenge_mb/commit/9c6532076834bb3dae03699ed8f90ca98c67e068), offline [run #37732962363](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37732962363) **SUCCESS**:

```text
60 passed    # V3-02/V3-03/V3-04 typed routing and mutation
39 passed    # frozen V2 concept/SceneGraph/repair
46 passed    # Visual Director and numeric-semantic drift
V3_BENCHMARK_PREREG=PASS topics=12 domains=6 easy=4 medium=4 hard=4
LEARNFLOW_BENCH_CONTRACT=PASS
CORE_FREEZE=PASS
```

Reproduction:
```bash
python -m pytest -q --confcutdir=tests/v3 tests/v3/test_contracts.py tests/v3/test_signal_preservation.py tests/v3/test_pattern_router.py
python -m pytest -q --confcutdir=tests/v2 tests/v2/test_concept_registry.py tests/v2/test_scenegraph_validation.py tests/v2/test_repair_v2_13_contracts.py
python -m pytest -q --confcutdir=tests/hermes tests/hermes/test_visual_director.py tests/hermes/test_final_v2_semantic_consistency.py
python scripts/verify_v3_benchmark_protocol.py
python scripts/verify_learnflow_bench.py
python scripts/verify_v2_core_freeze.py
```

Tests include valid worked-example source/compact fallback; missing verified steps; branching preservation at high/low budgets; simple directed chain and budget mutation; static equation, explicit recap-only card; forbidden cross-family fallback, unsupported enums, wrong layout/purpose; stale concept/trace; wrong object type; deterministic decision hashes; attempted forging of render_ready; and public API import. No actual MP4 produced. No human-quality measurement or live provider calls.

## 4. Residual reviewer attacks and gates

- Pattern choice is **bounded selection from a pre-existing V3-02 spec**, not an independent novel semantic planner. A malformed or underspecified plan must be rejected by upstream validators; eligibility is intentionally conservative.
- Eligibility uses project-owned semantic graph topology and object kinds. **It does not prove an actual renderer can instantiate that graph, preserve temporal transitions, or draw anything.** Verified-trace ID membership remains an upstream assertion, not an algorithm oracle. Consequently `SELECTED_UNRENDERABLE` is the correct status, not `READY`.
- Routing currently requires one TeachingSection per scene; multi-section specs abstain rather than silently dropping uncovered beats. Partial or cross-family fallback never changes pedagogical family to cards.
- No new V3 renderer or protocol-based real video quality comparison. No backend/Manim performance/security/license conclusions beyond absence of use at this checkpoint.
- Frozen V2 Core, benchmark corpus, free default model, original #181 evidence and rollback are unchanged. No merge to `main`. PR review must preserve #34 → #35 → #36 → V3-04 ordering.

**Checkpoint gate: PASS for offline semantic routing and explicit abstention/fallback only.** Next one checkpoint, only when requested: **V3-05 Binary Search Trace Adapter**. It must supply independent algorithmic oracle tests; V3-04 must not be used to claim trace truth.
