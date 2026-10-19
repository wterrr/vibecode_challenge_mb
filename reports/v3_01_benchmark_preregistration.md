# V3-01 — Benchmark Preregistration Acceptance Report

**Date:** 2026-10-08  
**Status:** **PASS (offline protocol freeze, no actual V3 quality measurement)**  
**Repo:** https://github.com/wterrr/vibecode_challenge_mb  
**Base main:** `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6`  
**Branch:** `chatgpt/v3-01-benchmark-preregistration`  
**Initial code commit:** `793bbfaf18f9b54f35c87428c3d66d7006a6efc6`  
**No merge authorization:** branch/PR only, main and frozen Core unchanged.

## 1. Research basis and reuse-first decision

Read canonical `PLAN_V3.md` §§6–8 and 8.3, `LEARNFLOW_V3_RESEARCH_NOTES.md`, final #181/V3-00E audit and the pre-existing `benchmarks/learnflowbench/README.md`, `corpus_v1.json`, `learnflow_bench/corpus.py`. **REUSE:** frozen V1 corpus, established `load_corpus()`, `corpus_sha256()`, Core Freeze verifier and LearnFlowBench's existing CI/metric integrity. **NEW (minimal glue):** exact versioned prereg manifest, a fail-closed sampling/permission verifier, mutation tests and offline-only CI. No copied upstream Code2Video/ALGOGEN/Manim code. No generated rendering code or new model orchestration.

## 2. Exact locked study corpus

Source unchanged: `benchmarks/learnflowbench/corpus_v1.json`, SHA-256 `4f0e0fc81dee7580df93a1d912b9485de7e5eb1c9fdda699576b48729bf4ab8f`, 100 frozen topics. Select 12 topics by seeded SHA-256 ranking of `seed|topic_id` within 12 fixed domain×difficulty strata (2 per domain, 4 easy / 4 medium / 4 hard). Records are locked in `benchmarks/learnflowbench/v3/preregistered_pilot_v1.json`:

| Topic ID | Domain | Difficulty |
| --- | --- | --- |
| `lfb-006-cs` | cs | easy |
| `lfb-016-cs` | cs | hard |
| `lfb-019-math` | math | easy |
| `lfb-026-math` | math | medium |
| `lfb-046-physics` | physics | medium |
| `lfb-050-physics` | physics | hard |
| `lfb-052-biology` | biology | easy |
| `lfb-064-biology` | biology | hard |
| `lfb-069-chemistry` | chemistry | easy |
| `lfb-078-chemistry` | chemistry | medium |
| `lfb-092-history-general` | history_general | medium |
| `lfb-094-history-general` | history_general | hard |

**Contamination rule:** known #181 Binary Search `lfb-005-cs` is diagnostic-only; not among scored pilot topics, and cannot be used as the sole V3 success demonstration.

## 3. Locked scoring and governance

- Pair `v2d_frozen` vs future `v3_candidate`. For representation attribution hold script/audio/evidence constant; for full end-to-end outcomes, use same untouched corpus input and matching model/seed/attempt budget, but treat script differences as outcomes.
- Primary paired blinded expert rubric: **explanation clarity** and **representation adequacy**, 1–5 ordinal. Two independent trained/domain-competent raters minimum, third adjudicator if primary rating differs ≥2; hidden randomized A/B identity.
- Engineering pilot target: average ≥+0.5 points on **both** primary metrics and wins on ≥8/12 topic pairs each, plus zero fatal factual/semantic/geometry/subtitle/security violations. Report per-topic outcomes, failed attempts in all denominators, stratified breakdowns, paired bootstrap 95% CIs and rater agreement. These targets are neither tested nor claimed as statistical significance.
- Unrun outcomes are `UNMEASURED`. Invalid clips receive predeclared score 1 and remain separately recorded as reliability failures. No success-only filtering, topic replacement or post-hoc change in metrics.
- Future model policy free-only `nvidia/nemotron-3.5-lightning:free`, availability **not probed**. If unavailable, STOP and version a prospective amendment. Paid API and live study **not authorized**; cost cap unset and requires user approval. Existing three-fixture V1/V2 benchmark cannot be substituted for V2D human video-quality evidence.

## 4. Evidence and exact commands

**CI:** [V3-01 Benchmark Preregistration Offline #37729383829](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37729383829) on code SHA `793bbfaf18f9b54f35c87428c3d66d7006a6efc6` — **SUCCESS**.

```text
V3_BENCHMARK_PREREG=PASS topics=12 domains=6 easy=4 medium=4 hard=4
LIVE_PROVIDER=NOT_AUTHORIZED
24 passed
LEARNFLOW_BENCH_CONTRACT=PASS
CORE_FREEZE=PASS
```

Run locally with existing project test dependencies:

```bash
python scripts/verify_v3_benchmark_protocol.py
pytest -q --confcutdir=tests/hermes tests/hermes/test_v3_benchmark_preregistration.py
python scripts/verify_learnflow_bench.py
python scripts/verify_v2_core_freeze.py
```

Mutation suite catches altered corpus digest/base SHA, sampling/exclusion/stratum, duplicate/replaced tasks, paid fallback, retry bias, unverified model availability falsely promoted, invalid/missing rating conflation, primary metric switching, edited thresholds, dropped failed trials, unauthorized usage and cost cap tampering.

## 5. Review decision and limits

**V3-01 = PASS** as a reproducible, frozen benchmark protocol with the explicit limitations above. This is **not** evidence of human visual improvement, generalization, semantic accuracy over 12 completed videos, V3 deployment reliability or learning transfer. No render, human rating, external paid call or model probe was performed. No protected `learnflow_v2/**`, baseline fixture, old corpus, model default or historical #181 artifact changed.

**Exactly one next checkpoint: V3-02 — Canonical Semantic Contracts.** Before implementing it, inspect V2 SceneGraph/ConceptRegistry and compatible maintained libraries (license first), then build only missing typed V3 semantic contracts and signal-preservation checks. Do not begin V3-02 until explicitly requested; do not authorize live evaluation as an accidental side effect.
