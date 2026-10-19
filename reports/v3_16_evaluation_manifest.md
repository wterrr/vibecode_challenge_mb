# V3-16 — Human Pilot/Ablation: locked manifest and synthetic rehearsal

**Date:** 2026-10-08  
**Engineering state:** IMPLEMENTED, first and final CI pending. This is a **pre-registered experimental data/design gate, NOT a human experiment**. There are no human raters, no generation/model API calls, no paid spend, no complete V2/V3 12-topic video pairs, no claimed V3 gain.
**Parent:** exact PR #48 HEAD `7bfd72039588e11629f395272ae028b10b48dc6f`; stacked branch `chatgpt/v3-16-evaluation-manifest`. V2 frozen main stays `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6` and may not be merged.

## Reuse-first and controls

- **Authoritative freeze reused** unchanged: `benchmarks/learnflowbench/v3/preregistered_pilot_v1.json` (state `FROZEN_PROTOCOL_UNEXECUTED`), `scripts/verify_v3_benchmark_protocol.validate()`, frozen `learnflow_bench.corpus_sha256/load_corpus`, 100-topic source SHA `4f0e0fc81dee7580df93a1d912b9485de7e5eb1c9fdda699576b48729bf4ab8f`, immutable V2 baseline SHA `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6`. No regeneration of topic IDs, sample seed, metrics, endpoints, thresholds or permission flags.
- Co-primary: **clarity** and **representation_adequacy** on 1–5 expert ordinal rubric; support scores pedagogy sequence, subtitle readability, cognitive load (higher=lower excess load). Paired sample **n=12 TOPICS**, not 24 clips or number of raters. Thresholds locked: per-metric paired average V3−V2 ≥0.5 and wins ≥8/12 plus actual hard safety non-inferiority; confidence interval paired **10,000 topic-resampled bootstrap** at locked seed, includes failed runs in denominator. This is an engineering exploratory pilot target, not powered hypothesis testing or SOTA.
- At least **2 independent blinded domain-competent raters per valid A/B clip**, a third blinded rater required when either co-primary dimension differs by ≥2 ordinal steps; preserve first two ratings, third used as median adjudication. Failed attempted video receives explicit floor 1 per original protocol (with separate failure code), while genuinely unexecuted video is **UNMEASURED** and no headline result is computed. Cost/latency missingness is None, **never zero dollars/time invented**.
- Ablations **E1–E10** are separately declared, identical to frozen PLAN contrasts, all **NOT_RUN**: semantic guards, representation-only controls, pedagogy plan, hero-vs-uniform under fixed time, grounded cues, static-vs-keyframe layout, freeform-vs-certified trace, full regenerate-vs-local repair, deterministic QA-vs-critic, human reference where licensed. No unapproved changes to treatment variables.

## New implementation

- `learnflow_v3/evaluation_pilot.py`: immutable `PilotManifest` and `BlindSlot` with exact 12 locked IDs and topic-query hashes, 24 anonymous A/B empty slots (the public file carries **no V2 or V3 system identity**), 10 ablation records with zero outcomes, study permissions NOT_AUTHORIZED, zero participants/videos/provider calls and checksum. Identity mapping `private_assignment()` follows existing frozen `SHA256(seed|presentation|topic_id)` parity and returns **in memory only**; do not export key in public rater packet. This deterministic publicly reproducible mapping is NOT cryptographically secure blinding: future recruitments must be isolated from the repo/seed/metadata and a privacy review must verify that no system cues leak.
- `GenerationAttempt`: exactly one listed attempt per topic/system and explicit `NOT_RUN/FAILED/VALID_VIDEO` with unmeasured cost/time fields; this checkpoint only allows **AUTHOR_SEEDED_SYNTHETIC** fake executions, not real-provider executions. `BlindedRating`: 5 strict finite integer ordinal scores and no system identity, origin `AUTHOR_SEEDED_SYNTHETIC` only. No actual human data can enter these production-unapproved contracts.
- `rehearsal_analysis()`: validates exact 24 ordered attempted slots and unique IDs, enforces complete rater/adjudicator obligations, records failed-video floor score separately, rejects dropped pairs/orphaned labels, computes per-topic paired deltas, two co-primary mean deltas/wins/ties, fixed 10k *topic* bootstrap 95% percentile interval, synthetic rater mean-absolute disagreement + ordinal quadratic-weighted Cohen kappa, 6-domain + 3-difficulty paired subgroups, and only-if-all-observed aggregate cost/time with P50/P95. Output `SyntheticRehearsal` is always tagged `AUTHOR_SEEDED_REHEARSAL_ONLY_NOT_HUMAN_EVIDENCE`, release blocked, `real_pilot_pass=False`, actual human effect UNMEASURED and real hard safety gate UNMEASURED (None), even when synthetic thresholds are satisfied.
- `scripts/verify_v3_evaluation_manifest.py` emits a **public identity-free** `v3_16_public_blinded_manifest.json`, blank `v3_16_blinded_rater_sheet_TEMPLATE.csv` (12×2 rows), and explicitly `AUTHOR_SEEDED` simulated attempts/ratings + computed bootstrap JSON. Exactly two injected synthetic video failures deliberately stress denominator and invalid-video floor; synthetic video SHA strings are **not actual MP4 files**, and that fact is explicit. The generator does not write any private A/B mapping.
- `tests/v3/test_evaluation_manifest.py` negative matrix: protocol/topic/source tamper, unauthorized human/live permission, leaked A/B system identity, missing/dropped attempts, forced scores for unexecuted video, missing/duplicate raters, wrong third-adjudicator, forged human rating origin/release PASS, missing/negative/NaN cost, synthetic vs actual metric leakage, E1–E10 controls mutation, audit SHA, exact 10k paired topic bootstrap reproducibility. `.github/workflows/v3-evaluation-manifest.yml` runs immutable V2/Hermes/Core/benchmark and V3-02–15 regression plus pure offline report generation; no external reviewers or API calls.

## Why this is NOT the scientific quality acceptance

- **Human trial NOT RUN**. Independent-rater visual clarity, representation adequacy, agreement, user comprehension/transfer, image/video truth judgments, actual dollar cost, real mp4 success across all 12 topics, paired V2/V3 12-topic results and any improvement **UNMEASURED**.
- No real V2 clips or 12 production V3 clips have been generated for this study; V3-15's two author-curated clips are **not** 12 paired real lessons.
- The script's synthetic mean delta and bootstrap CI validate *computation only*, never claim evidentiary effect, safety non-inferiority or eligibility for production publication. The frozen V3-01 `publish_authorized=False`, `human_participants_authorized=False`, `live_generation_authorized=False`, `paid_api_authorized=False`; no attempt to override permissions in V3-16.
- A later explicitly approved execution must configure genuine video provenance, independent blinded raters, adjudication, optional prior-consented outcome measures, privacy and domain-expertise controls, actual provider/model/cost cap and the exact frozen prereg protocol or transparently new version before outcomes. Reviewer blinding and real quality acceptance **remain pending**.

## Reproduce

```bash
python -m pytest -q --confcutdir=tests/v3 tests/v3/test_evaluation_manifest.py
python scripts/verify_v3_evaluation_manifest.py --output-dir /tmp/v3_16_evidence
python scripts/verify_v3_benchmark_protocol.py
python scripts/verify_v2_core_freeze.py
```

**Exactly one next separately authorized checkpoint:** V3-17 Release Candidate & Rollback **gate preparation only**, not unapproved release: must remain BLOCKED while human pilot and V3-13/C7 efficacy are not verified.
