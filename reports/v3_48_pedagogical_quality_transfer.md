# V3-48 — Pedagogical Animation Quality & Semantic Transfer Audit

**Status:** Implementation submitted for exact-head CI; no human reviewer results, no learner study, no production certification.

## Purpose and frozen evidence
Parent: V3-47 Draft PR #81 at `f6b3919e304482f8b2691dcf877c15b8990f31ca`.
Registration BEFORE implementation: `benchmarks/learnflowbench/v3/v3_48_quality_transfer_preregister.json`, first child commit `c2a4c9d`.

Two **frozen source-matched A/B pairs**, V3-46 run #38200776147 (artifact #11725751836), V3-47 exact-head push #38203160425 (artifact #11726228138), all SHA-locked. V3-47 heldout-process is still only a geometric/ID change, not new curriculum. All sources are explicitly HOST/SYNTHETIC, not new GPT-6 requests. No main merge.

## Research questions and falsification
1. Do V3-47 changes create *observable evidence* at claim/beat-matched timestamps in real H264, without changing the scene wire or WAV?
2. Does the V3-45 model-facing claim bank allow an unsupported mathematical or process subject to use frozen F1/F2/F3 or P1/P2/P3 claims?
3. Can independent humans express blinded preferences/comprehension differences without invented scores?

## Intervention and protocol
- Claim-scope guard in `learnflow_v3/semantic_scene_wire.py`: the **current frozen** F1/F2/F3 claim bank describes *only* 1/2→2/4 with ×2; P1/P2/P3 describe *only* Start→Verify→Finish. Other ratios/graph labels must fail closed until a versioned grounded claim bank is available.
- Negative control: 2/3→4/6 has a mathematically correct equation, equal-size whole, and valid subdivisions, **but is NOT semantically supported by the frozen bank**. Rejecting it establishes a boundary, not generalization.
- Verify three V3-47 exact-head native H264/AAC tracks and frame budget directly with ffprobe and frozen MP4 SHA. Verify V3-46 baselines and exact original narration beat WAV SHA, identical model-facing wire hashes.
- Decode physically matched frames for two prior/current video pairs, count new semantic cue color in grounded source-tile and Verify-node windows. These are **descriptive pixel observations**, not educational scores.
- Freeze 12 physical narrated-beat samples per pair. Export randomized deterministic A/B MP4 files + A/B-only contacts as a **reviewer packet** separate from a provenance/unblinding key, which must NOT be provided to reviewers. Public code means blinding is imperfect if reviewers investigate media hashes; reviewers should only see provided packet.
- Export an **EMPTY** six-axis independent-rater CSV and an **EMPTY** learner-transfer form. No new scores, fake participants or purported learning effects.
- Proposed independent assessment: at least three independent raters; optional learner study of at least twelve consenting learners with counterbalanced assignment and unseen comprehension question. These thresholds indicate **data requirements**, not a sample-size/power justification. No inferential significance will be claimed based on unrun studies.

## Explicit STOP / GO logic
- `TECHNICAL EVALUATION PASS`: both source-matched frozen video pairs, exact source/WAV/hash/codecs/frames, observable event cues, regressions, and clean unscored packet succeed.
- `SEMANTIC TRANSFER NOT CERTIFIED`: the claim bank only supports the original frozen pair. A new 2/3→4/6 lesson is correctly blocked; this is a **bounded negative result**.
- `PEDAGOGICAL QUALITY UNRATED`: without independent review or learners, *no* claim of 3Blue1Brown polish, human preference, comprehension gain, creativity, or six-domain transfer.
- `PRODUCTION BLOCKED` regardless of a technical CI success. All code is offline, host-owned, no provider POST/GET, no free-form LLM Python.
- CI/artifact/SHA on the **final exact HEAD** must be checked before closing this checkpoint.

## Reuse-first files
`scripts/run_v3_48_pedagogical_quality.py`,
`tests/v3/test_v3_48_pedagogical_quality.py`,
`.github/workflows/v3-48-pedagogical-quality.yml`.
Reuses V3-46 physical sample/FFmpeg decoder, V3-47 event geometry/color pixel proof, existing immutable artifacts and V2/V3 benchmark safety gates.
