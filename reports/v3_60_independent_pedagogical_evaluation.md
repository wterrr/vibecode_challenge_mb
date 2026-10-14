# V3-60 — Independent Pedagogical Quality Evaluation | Evidence

**Research parent:** Draft PR #93, frozen HEAD `506b3ccf3bf23aa3163d585496f1e91046109b18`. **Prereg:** first branch commit `89c7e92ed81f9b49685f51319da8b8ddc0bc9b79`, registered before implementation (2026-10-14).

## Scientific question

Independent humans rate whether the V3-59 causal reveal explains its evidence better than the frozen V3-57 motion and V3-58 static end-state. Treatment is condition-masked, **not double-blind**. This is NOT a study of learning gain or model authorship.

## Native evidence independently rechecked

Source: V3-59 successful push workflow [#38380316466](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38380316466). Masked nine-video artifact ID `11803826367`; separately held admin SHA/treatment mapping artifact `11804490041`. Every MP4 SHA-256 matched the public preregistered digest, every video was fully decoded with FFmpeg, all videos have H.264/AAC, 1280×720 at 15 FPS. Physical decoded frames per arm: attention_reversed_query 355, fraction_equivalence 340, process_heldout_unknown 344. All three arms within each case share frame count and AAC elementary bitstream SHA. No audio, clip or timeline substitution.

Verified review package contains exactly 9 condition-masked MP4, 3 blank rotated order CSV reviewer templates, written instructions and masked manifest. The admin treatment key is **never** included in the reviewer package. No human rating was generated.

## Implementation scope

- `benchmarks/learnflowbench/v3/v3_60_independent_review_preregister.json`: immutable frozen native media checksums, outcomes and 3+ reviewer protocol.
- `scripts/run_v3_60_independent_review.py`: `verify`, `prepare`, `seal`, `analyze`. Enforce 9 native digests, physical decoded frames/AAC parity, score completeness, duplicates, low-score timestamps, score locking before treatment disclosure; analyze ordinal within-rater within-topic deltas only after separate key/attestations.
- `tests/v3/test_v3_60_independent_review.py`: hostile malformed-data tests. All synthetic rows are marked `TEST_ONLY`.
- `.github/workflows/v3-60-independent-review.yml`: offline tests + recover native source artifact, full decode, masked packet upload, no model calls.
- `docs/v3_60_independent_reviewer_protocol.md`: human coordinator's eligibility, conflict, consent, masked review, scoring, original lock and release protocol.

## Prespecified analysis

Three complete independent external human reviewers minimum, each scores nine video clips across clarity, causal witness, semantic continuity, legibility and pacing (ordinal 1–5). Main estimand is per-reviewer/topic paired causal-minus-original causal_witness, secondary causal-minus-static and legibility. Descriptive topic medians, reviewer-topic pair ranges, and no p-values with non-independent repetitions. The frozen directional screen requires both causal-witness medians >= +0.5, at least 2/3 topic medians nonnegative against both other arms, and legibility median causal-original >= -0.5. Even a passing screen is **not** proof of improved learning.

**Validity limitations:** static ablation advances the answer as well as removing motion, so this is not a pure motion counterfactual; treatment may be inferred by visual content; three synthetic research topics do not generalize to a real product audience; there is no word-level narration evidence.

## Current results (do not invent missing human data)

| Requirement | Actual |
| --- | --- |
| Native 9-video SHA, media, decoded frame, audio parity | **PASS in local physical audit** |
| Real independent submitted reviewers | **0** |
| Complete independently collected masked review panels | **0** |
| Locked human rating dataset | **NONE** |
| Attestation/consent and eligibility audit | **NOT DONE** |
| Pedagogical quality | **UNRATED_NO_REVIEWERS** |
| Human learning gain | **NOT_MEASURED** |
| Genuine model pedagogy/creativity | **NOT_TESTED** |
| Production | **BLOCKED** |

## Acceptance remaining

Exact-head workflow must PASS both strict negative tests and native re-verification/upload of masked kit; inspect logs and artifact. Then obtain real human reviewers, keep treatment key secret, seal scores before opening key, audit provenance, and only then report descriptive differences and failures. Don't silently promote to a product or claim human success. Do not merge main, edit V2 Core/production prompts, or call model APIs.

**Current verdict:** technical study kit ready; human quality gate remains **NO-GO / UNRATED**.
