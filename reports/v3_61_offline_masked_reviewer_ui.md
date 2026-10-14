# V3-61 — Offline Masked Reviewer UX & Submission Integrity

**Parent:** V3-60 Draft PR #96, HEAD `42dfb0216ea82c9fe22d7995e1f99fd02acbe0d1`. **Prereg FIRST child commit:** `f4b59c994819c99532c4389034d878bd3c42fbb0` (before implementation). **Date:** 2026-10-14. This checkpoint does **not** change any native video, treatment mapping, V2 Core, production prompt or model API usage.

## Gap and scope

V3-60 froze nine condition-masked V3-59 native MP4s, research scoring schema and a coordinator-level score-lock/analyze CLI, but reviewers had to play local videos manually and edit 9-row CSVs. V3-61 adds a **human-usable offline browser player** and exact-schema local CSV export. It does **not** recruit participants or fabricate ratings. The scientific V3-60 evaluation remains **UNRATED** until an actual eligible external panel submits genuine scores.

Source artifact: successful V3-60 run [#38495153475](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38495153475), masked-only artifact `11863660782`. Parent V3-60 preregistration immutable hash manifest is imported by V3-61, not retyped or modified.

## Implementation

- First child prereg: `benchmarks/learnflowbench/v3/v3_61_offline_review_ui_preregister.json`.
- Deterministic builder: `scripts/build_v3_61_review_ui.py`. Reuses `scripts/run_v3_60_independent_review.py` for SHA, H.264/AAC, complete frame and audio parity checks. Copies only the nine frozen masked MP4s and two static UI files.
- Browser: `learnflow_v3/review_ui/v361_reviewer.js` and `v361.css`. Three assigned forms use existing V3-60 counterbalanced `template_rows`; HTML config embeds only masked filenames and case IDs. No external JavaScript/CDN, fetch, analytics, network submission, storage or admin treatment key; restrictive `connect-src 'none'` CSP.
- Reviewer enters a pseudonymous ID, watches each local clip, scores clarity / causal witness / semantic continuity / legibility / pacing, rates confidence, annotates time-specific failures for any <=2 score, and exports a nine-row CSV with exactly the V3-60 fields. Direct download only; coordinator SHA-locks the combined file using V3-60 `seal` **before** opening any admin treatment mapping. The UI's video-ended/progress check is an imperfect self-attestation aid, not proof of human attention.
- Fail-closed tests: `tests/v3/test_v3_61_review_ui.py` (missing/extra/changed mask, prereg, form rotation), `tests/v3/test_v3_61_reviewer_ui.cjs` (CSV schema, injection, tamper/partial scores), and real Chromium `tests/v3/test_v3_61_browser_smoke.py` (open file:// forms, premature navigation denied, no remote network). Browser scripted scores use `TEST_ONLY_BROWSER`, are ephemeral in CI and **never** count as human review or get published.
- Dedicated offline GitHub workflow: `.github/workflows/v3-61-offline-reviewer-ui.yml`. It downloads only original frozen V3-60 masked artifact, verifies every native frame/audio packet, runs tests and emits downloadable HTML+MP4 bundle.

## Measurable, honest state

| Gate | Result |
| --- | --- |
| 9 frozen video SHA-256 | PASS in native CI at run #38496732232 |
| Full H.264/AAC FFmpeg decode/parity | PASS in native CI at run #38496732232 |
| 3 assigned forms, 9 clips each, no admin mapping | PASS |
| Native Node CSV and Python negative tests | PASS |
| Real Chromium basic file-mode smoke with 0 network | PASS |
| End-to-end 9-clip TEST-ONLY browser CSV download | Dedicated strict rerun in progress; do not claim success prematurely |
| Valid external reviewers | **0** |
| Real human quality, learning gain, model authoring | **UNRATED / NOT_MEASURED / NOT_TESTED** |
| Production | **BLOCKED** |

## Limitations and next research gate

The browser cannot attest real identity, informed consent, noncollusion, genuine watching, comprehension, or assessor independence. Treatment is visually inferable, so this is **condition-masked, not double-blind**. The original V3-58 static treatment confounds motion with early answer exposure. No new efficacy result is produced by UI tests. To close V3-60 scientific gate, recruit at least 3 external humans, assign one form each, keep treatment key separately sealed, collect complete nine-video ratings, lock original CSV by SHA prior to unblinding, independently audit reviewer provenance, and report paired ordinal deltas without claiming learner impact.

**Verdict:** V3-61 *collection infrastructure* technically ready subject to exact-head final CI; human educational quality **NO-GO / UNRATED**.
