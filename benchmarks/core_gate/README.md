# LearnFlow V2 Core Gate

This directory contains **frozen evidence**, not optimistic status flags.

`PLAN_V2.md` defines the Core Gate. The evaluator remains fail-closed:

- missing evidence → `BLOCKED`, never `PASS`;
- benchmark metrics cannot be satisfied by unit/contract tests alone;
- VLM-outage and local-repair-scope invariants may use contract-test evidence;
- any measured threshold violation → `FAIL`;
- repository-level prerequisites can block the gate even when supplied metrics pass.

## Official corrected benchmark

Engine commit:

```text
fdad3db1340d8b28175ab5382d800ff79df9a8a0
```

Benchmark:

```text
v2-core-gate-v2
```

Official GitHub Actions provenance:

```text
workflow run:     37412433812
artifact id:      11389249199
artifact digest:  sha256:5f5b167471779668f0c51b34090d2f54521f974019e294bef26c9a9d3e69e242
raw result SHA:   16ee5c9f5684b53596f890e3978147e11c7df33f281bd48955a8bd01e2fe2609
spec SHA:         e20ab43e2a7622af8dc47c00c0c5692b42cceb05723ec93a70981effd62a9cfd
full V2 tests:    959 passed (10 deprecation warnings)
```

Current decision: **CORE GATE PASS**.

Run:

```bash
python scripts/evaluate_v2_core_gate.py
```

The command exits `0` only for a full PASS.

## Official measured results

| Metric | Requirement | Official result |
|---|---:|---:|
| Render success | `>= 98%` | **100% (3/3)** |
| Fatal clipping | `= 0` | **0 / 9 scenes** |
| Fatal overlap | conservative `= 0` | **0 / 9 scenes** |
| Invalid MotionPlan | `= 0` | **0 / 9 scenes** |
| Selective repair success | `>= 90%` | **100% (9/9)** |
| Reproducibility | `100%` | **100% (3/3 lessons, two renders each)** |
| V1→V2 critical regression | `= 0` | **0 / 3 lessons** |
| V2 static quality delta | `> 0` | **+6.0680719** |
| VLM unavailable | deterministic mode still works | **PASS** |
| Local repair scope | unrelated scenes are not rebuilt | **PASS** |

The corrected `static_composition_proxy_v2` compares the same pre-subtitle visual layer on both sides:

```text
V1 = 66.15013163
V2 = 72.21820353
Δ  = +6.06807190
```

This metric measures only deterministic static-composition characteristics. It is **not** a human
aesthetic/comprehension score and must not be used to claim 3Blue1Brown-level quality.

## Evidence discipline

`v2-core-gate-v1` is invalidated. Its V1 static frames included burned subtitles while V2's did not,
and its renderer/layout text-fit contract was weaker. The frozen corrected source of truth is:

```text
benchmarks/specs/v2_core_gate_v2.json
benchmarks/baselines/v2/result.json
benchmarks/baselines/v2/core_gate_evidence.json
benchmarks/baselines/v2/core_gate_report.json
benchmarks/core_gate/static_quality_metric.json
benchmarks/core_gate/evidence.json
```

Full generated videos, representative frames and repair clips remain in official Actions artifact
`11389249199`; binary media are intentionally not committed.

Known benchmark coverage limitation: the three lessons contain no persistent-object MOVE transition.
CP2.10 has dedicated regression coverage, but this Core Gate run is not end-to-end evidence for that
specific transition mode.

Subtitle note: the frozen V1 benchmark speech provider truncates subtitle text to 40 characters.
V2 matches that parity contract in this benchmark. This is a known baseline limitation, not a claim
that subtitle UX is production-complete.

The next roadmap step is **CORE FREEZE**, not Hermes/V2D.
