# LearnFlow V2 Core Gate

This directory contains **evidence**, not optimistic status flags.

`PLAN_V2.md` defines the Core Gate. The evaluator is deliberately fail-closed:

- missing evidence → `BLOCKED`, never `PASS`;
- benchmark metrics cannot be satisfied by unit/contract tests alone;
- VLM-outage and local-repair-scope invariants may use contract-test evidence;
- any measured threshold violation → `FAIL`;
- repository-level prerequisites can block the gate even when supplied metrics pass.

Official engine commit under evaluation:

```text
25c27da43e6645d2e9ac704958d619e3c96aa4b2
```

Official frozen benchmark:

```text
benchmark_id: v2-core-gate-v1
GitHub Actions run: 37404184018
artifact id: 11386363669
artifact digest: sha256:155be2d732cad1d85cc020f3cbe897d40fef346a148df82f44096f5bce15e59b
spec SHA-256: 03e5506a4d90f057e3131cc99734b5e0c113d727f76894887348a3a4a303eeed
```

Current decision: **CORE GATE PASS**.

Run:

```bash
python scripts/evaluate_v2_core_gate.py
```

The command exits `0` only for a full Core Gate PASS; `2` means FAIL/BLOCKED.

## Official measured results

| Metric | Requirement | Result |
|---|---:|---:|
| Render success | `>= 98%` | **100% (3/3)** |
| Fatal clipping | `= 0` | **0 / 9 scenes** |
| Fatal overlap | conservative `= 0` | **0 / 9 scenes** |
| Invalid MotionPlan | `= 0` | **0 / 9 scenes** |
| Selective repair success | `>= 90%` | **100% (9/9)** |
| Reproducibility | `100%` | **100% (3/3 lessons, two runs each)** |
| V1→V2 critical regression | `= 0` | **0 / 3 lessons** |
| V2 static quality delta | `> 0` | **+5.54192634** |
| VLM unavailable | deterministic mode still works | **PASS** |
| Local repair scope | unrelated scenes are not rebuilt | **PASS** |

The static-quality result uses the frozen `static_composition_proxy_v1` metric:
V1 = **69.1192536**, V2 = **74.66117994**.

This proxy measures deterministic static composition characteristics only. It is **not** a human aesthetic score and does not justify a claim of 3Blue1Brown-level quality.

Persistent evidence lives under:

```text
benchmarks/baselines/v2/result.json
benchmarks/baselines/v2/core_gate_evidence.json
benchmarks/baselines/v2/core_gate_report.json
benchmarks/core_gate/static_quality_metric.json
```

The full videos, representative frames, repair clips, and raw result remain in the official GitHub Actions artifact. Binary media are intentionally not committed to the repository.
