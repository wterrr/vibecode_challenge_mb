# LearnFlow V2 Core Gate

This directory contains **evidence**, not optimistic status flags.

`PLAN_V2.md` defines the Core Gate. The evaluator is deliberately fail-closed:

- missing evidence → `BLOCKED`, never `PASS`;
- benchmark metrics cannot be satisfied by unit/contract tests alone;
- VLM-outage and local-repair-scope invariants may use contract-test evidence;
- any measured threshold violation → `FAIL`;
- repository-level prerequisites can block the gate even when supplied metrics pass.

Current engine commit under evaluation:

```text
ca20c79c0e17f990ebfb4ed06f9b8988dbe74305
```

Current known state is **BLOCKED**. The deterministic V2 renderer baseline now exists, but there is still no frozen V2 end-to-end benchmark result and no agreed V1-vs-V2 static-quality metric artifact. The checked-in evidence manifest is intentionally still bound to the pre-renderer CP2.14 engine commit until a new reproducible benchmark run refreshes it.

Run:

```bash
python scripts/evaluate_v2_core_gate.py
```

The command exits `0` only for a full Core Gate PASS; `2` means FAIL/BLOCKED.

## Core Gate metrics

| Metric | Requirement | Evidence class |
|---|---|---|
| Render success | `>= 98%` | Benchmark |
| Fatal clipping | `= 0` | Benchmark |
| Fatal overlap | plan says `~= 0`; evaluator conservatively requires `0` | Benchmark |
| Invalid MotionPlan | `= 0` | Benchmark |
| Selective repair success | `>= 90%` | Benchmark |
| Reproducibility | `100%` deterministic scenes | Benchmark |
| V1→V2 critical regression | `= 0` | Benchmark |
| V2 static quality delta | `> 0` vs V1 on agreed metric | Benchmark |
| VLM unavailable | deterministic mode still works | Contract test or benchmark |
| Local repair scope | unrelated scenes are not rebuilt | Contract test or benchmark |

Do not add a benchmark evidence record until the referenced run actually exists and is reproducible.
