# V3-01 — Frozen Tier-1 benchmark preregistration

**Status: FROZEN_PROTOCOL_UNEXECUTED (2026-10-08)**. Authoritative contract: `preregistered_pilot_v1.json`. Benchmark design only, **not** a model/video run or proof of V3 quality.

## Dataset, contamination and topic selection

Read-only source: `benchmarks/learnflowbench/corpus_v1.json` (100 topics), SHA-256 `4f0e0fc81dee7580df93a1d912b9485de7e5eb1c9fdda699576b48729bf4ab8f`; baseline commit `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6`. Six domains: CS, math, physics, biology, chemistry, history/general; difficulty: 34 easy, 33 medium, 33 hard.

**Binary Search `lfb-005-cs` is excluded from confirmatory evaluation**, as Action #181 exposed and tested it with a known find-16/finding-24 mismatch. It remains diagnostic only, not evidence that future V3 generalizes.

**Sampling:** 12 locked domain×difficulty strata in JSON; within each, choose the lexicographically minimum SHA-256 digest of UTF-8 `seed|topic_id`. Seed `learnflow-v3-01-20261008-stratified-v1`, chosen before outcomes. Exactly 2 topics per domain, exactly 4 easy, 4 medium, 4 hard. Corpus query/learner/duration/language remain unchanged. No replacements.

| Domain | Difficulty | Locked topic |
|---|---|---|
| cs | easy | `lfb-006-cs` |
| cs | hard | `lfb-016-cs` |
| math | easy | `lfb-019-math` |
| math | medium | `lfb-026-math` |
| physics | medium | `lfb-046-physics` |
| physics | hard | `lfb-050-physics` |
| biology | easy | `lfb-052-biology` |
| biology | hard | `lfb-064-biology` |
| chemistry | easy | `lfb-069-chemistry` |
| chemistry | medium | `lfb-078-chemistry` |
| history_general | medium | `lfb-092-history-general` |
| history_general | hard | `lfb-094-history-general` |

## Controlled comparisons

- **E2 representation ablation:** identical fact pack, objective, vetted script, narration audio, timing and seed; only rendering/pattern intervention differs. This isolates representation quality.
- **End-to-end matched comparison:** same corpus input, provider+model revision, learner/length constraints, seed and a single attempt each; scripts may differ (an outcome, not a controlled variable). Failures on either side remain in the denominator of **all 12 assigned topic pairs**.
- **Frozen V2D ≠ one historical #181 video** and V1/V2 Core three-fixture static proxy ≠ human aesthetics. No post-hoc topic dropping, model switching, silent retry, free-to-paid fallback, selective successful-only reporting or fabricated cost.
- Proposed exact free-model candidate: `nvidia/nemotron-3.5-lightning:free` (availability **UNVERIFIED**, no probe); if unavailable, STOP and amend a new protocol version *before* any comparable generation.

## Preregistered measures

**Two co-primary human metrics (1–5):** (a) clarity of visual explanation, (b) adequacy of chosen visual representation. At least two independent blinded domain-competent raters per topic/system, randomised anonymous A/B order derived from the fixed hash rule; key inaccessible to raters. Third blinded adjudicator if absolute primary score disagreement ≥2. Keep raw ratings and annotate time-indexed failures.

**Rubric:** 1 unusable/wrong; 2 confusing; 3 understandable with meaningful weaknesses; 4 clear and well integrated; 5 exemplary. Also rate pedagogy sequence, subtitle readability and cognitive load (5 = low unnecessary load). Semantic/factual accuracy is a hard gate, **not** offset by beauty. Invalid output gets an explicit floor rating of 1 for intention-to-evaluate engineering pilot *and* separate reliability failure; truly unexecuted scores are **UNMEASURED**, not 1/0.

**Provisional engineering pilot threshold (locked before results):** paired average V3−V2 ≥ +0.5 for **both** co-primary ratings, and ≥8/12 topic wins on **each**, with zero critical semantic errors, fatal clipping/subtitle issues, unsafe export or frozen Core regression. This is not a powered hypothesis test or SOTA claim. Report all 12 raw pairs, negative cases, paired bootstrap 95% percentile CI (10,000 resamples with fixed seed), by-domain/difficulty results, inter-rater agreement and cost/latency from attempted runs including failures.

**Supporting metrics:** render success / 12 attempts per system; semantic/trace agreement; observable essential-beat coverage and visual event alignment; generic-card collapse on eligible scenes; hard geometry; wall time P50/P95; usage/token/cost when actually observed. Optional consented student learning transfer is **not part of V3-01**, requires separate study and is UNMEASURED.

## Evidence governance and reuse-first

The existing LearnFlowBench corpus loader and SHA256 implementation are **reused** in `scripts/verify_v3_benchmark_protocol.py`. No copied external code, new renderer, new agents or live-model invocation. The original V1/V2 fixtures, Core manifest, V2 default free model and #181 artifacts are immutable.

Live evaluation, actual cost, human recruitment, V3 implementation and any paid API invocation are **not authorized by this protocol**; `cost_cap_usd` is unset and requires explicit approval. No benchmark claim can be made from this schema alone. Protocol revision requires a **new versioned JSON** before seeing outcomes, with transparency about contamination.

### Acceptance: V3-01 only

```bash
python scripts/verify_v3_benchmark_protocol.py
pytest -q --confcutdir=tests/hermes tests/hermes/test_v3_benchmark_preregistration.py
python scripts/verify_learnflow_bench.py
python scripts/verify_v2_core_freeze.py
```

These must pass in free/offline CI; no generated MP4 is expected from a preregistration checkpoint. **Exactly one next checkpoint upon PASS: V3-02 — Canonical Semantic Contracts**, reusing existing SceneGraph and ConceptRegistry with typed adapters.
