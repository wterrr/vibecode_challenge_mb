# V3-26 — Real Chromium E2E and Independent Review Readiness

**Status:** Engineering implementation candidate; exact HEAD CI required. Not a human evaluation, learner-effect claim, paid provider, production release or modification to V3-16 locked preregistration.

## Why this is necessary

V3-25 produced source-grounded H264/AAC reviewer kits, anonymous A/B orders, a rubric and offline response parser. Earlier JavaScript syntax tests and media checks did NOT prove the actual reviewer HTML was usable inside a browser: an attempted assistant-container Chromium launch was blocked by host policy. V3-26 runs actual Playwright Chromium on GitHub Ubuntu with BOTH original locally distributed reviewer HTML files, not a mocked website, synthetic video, JavaScript-only check or static screenshot.

## Specific real-browser acceptance

- Render original physical-audio V3-20, native V3-22 and corrected V3-24 H264/AAC with identical source trace, utterance timings, AAC bytes and 1280x720 at 24fps. Generate R01/R02 packages using the V3-25 source-verified anonymous assignment, with admin mapping stored separately.
- Browser opens the actual file:// review.html of EACH reviewer kit. Metadata must load, AAC codec must be supported, real H264 pixels must be nonblack in screenshots, unmuted HTMLMediaElement playback must advance currentTime, and FFmpeg must independently decode a non-silent original AAC track. Audio audible to a human is not measured.
- Simulate seek near each video end and observe actual ended event and reviewer UI completion status. This deliberately shortened playback is not a person watching the full lecture.
- Verify real UI rejection of no consent checkbox, no video completion, missing clarity score, missing issue category and missing timestamp. Then programmatically enter nine synthetic test ratings per clip, annotation, source timestamp, viewing context and transfer answer, trigger an actual browser download event and validate actual saved JSON.
- Import both browser-exported synthetic response JSON files with the source-attested real H264 media and V3-25 importer. Reject tampering, duplicate reviewers, stale video hashes, incomplete rubric. Retain ONLY technical screenshots, diagnostics, and zero-human-participant engineering receipt. Delete browser-generated synthetic responses, synthetic score aggregates and private participant data before artifact upload. Never describe synthetic values as human ratings.
- The backend supplies an issue taxonomy chosen explicitly by reviewer: aesthetic (motion/style/layout), readability (font/caption/index), pedagogy (causal sequence/candidate-leftmost explanation), technical (render/sync/trace), audio (voice/timing), or no_issue. The output is a timestamped category inventory and rater disagreement report, not LLM-guessed sentiment. Old submissions without this field remain unclassified_legacy.

## Independent reviewer protocol: PREPARED ONLY / NO RECRUITMENT

When a future study owner independently authorizes participation: recruit at least two domain-competent, mutually independent reviewers, record verified eligibility/expertise and informed consent outside anonymous response JSON, and retain opt-out rights. Separate the admin condition key and private consent ledger. Give each reviewer ONLY that person's reviewer ZIP, never the admin key. Ensure equal physical viewing/audio conditions; reviewers must actually watch both whole clips (without automation seeks), record anchored 1–5 co-primary clarity and representation adequacy and other dimensions, choose the category, note timestamp/reason, and complete an application question. Preserve full negative evidence. When there is absolute disagreement >=2 in co-primary scores, use an actual independent third expert to adjudicate. Do not report adjudicated results without a real adjudicator.

Collect JSON privately with no IDs or participant names in git/CI artifacts. Run the existing offline response importer using the actual media-root and admin manifest; label outputs self-reports unless independent identity/consent source was verified outside browser. A browser consent checkbox, media completed event and JSON fields CANNOT prove an independent human study. The A/B condition labels are masked, not true blinded content, and the Binary Search example was repeatedly used in development. It is excluded from the frozen V3-16 12-topic confirmatory study; use any review only for exploratory diagnostic interpretation. Differences in transfer questions and carryover prevent causal learning-gain claims.

## Governance and result limits

- No changes to frozen V3-16 protocol, V2 Core, main or paid model/provider paths.
- Human participants=0, ratings=0, quality preference=UNMEASURED, student learning=UNMEASURED, production=BLOCKED. Third rater never fabricated.
- GitHub artifact permissions are repository-based, not per reviewer. Separate R01/R02/admin archives reduce accidental exposure but approved private distribution controls remain necessary.
- The browser tool checks actual media interaction on Github runner. The assistant container blocked even localhost and file navigation by administrator policy, so no unsupported local Chromium E2E PASS is claimed. Exact code SHA CI, event logs, screenshot receipts and independently inspected artifacts determine a BOUNDED ENGINEERING PASS, not educational performance.

**Implementation:** scripts/run_v3_26_browser_e2e.py, learnflow_v3/independent_quality_pilot.py, tests/v3/test_real_browser_quality_contracts.py, .github/workflows/v3-real-browser-quality-eval.yml, and this report/PLAN/Research Notes. Acceptance to be appended after final exact-HEAD CI.


## Exact code-head Chrome E2E acceptance — 2026-10-09

**Code SHA 2f22aa52e48eb00992f119d1c2197d20ab2c2f0e: 26/26 GitHub Actions SUCCESS**, including dedicated run https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37877573061. Job output: 27 V3-25/26 issue+contract tests PASS, 9 V3-24 tests, 8 native V3-22 tests, 15 source V3-20 tests, 39 Frozen V2 tests, 86 Hermes tests, benchmark preregistration, LearnFlowBench and Core Freeze PASS. The locked V3-16 study is NOT RUN; a benchmark protocol PASS does not mean human quality was measured.

**Real browser failure and actual fix:** Initial GitHub run 37877153402 FAILED at browser media readyState: packaged Playwright Chromium Headless Shell did not decode supplied H264/AAC on that runner. We did NOT relax media gates, use a mock video or substitute mere JS syntax checks. Follow-up code SHA uses Playwright Google Chrome Stable (proprietary codecs supported) and adds explicit media error/readyState/codec diagnostics. Final run reports V3_26_CHROMIUM=PASS, V3_26_UI=PASS and V3_26_HUMANS=NOT_RUN.

**Independent artifact inspection:** Downloaded five exact-code-SHA GitHub artifacts and CRC-checked their ZIPs:
- Chrome real E2E receipt + 6 screenshot PNGs: https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37877573061/artifacts/11593241470
- R01 true reviewer player+MP4: https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37877573061/artifacts/11592279884
- R02 same two MP4s in opposite A/B order: https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37877573061/artifacts/11593331006
- Admin-only source assignment / NOT_RUN report: https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37877573061/artifacts/11593420460
- Actual corrected source-matched H264/AAC and SRT/event proof: https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37877573061/artifacts/11593365777

Each reviewer ZIP contains exactly two real clips, metadata, README and standalone local HTML; neither contains admin mapping, and neither HTML exposes baseline/refined labels. Both baseline H264 SHA256 7942d193f0b14c9ced4999909fbaa4efd45e72d40c01a3994dbba8bfc8cbe17e and V3-24 corrected H264 SHA256 de323f9871575a1c4fa1801295daad85f1922157cf441f92129a1d56d40696af match the locked source. Browser captured real nonblank video pixels for BOTH clips in BOTH packs and four real unmuted playback advances approximately 0.94s each. Four AAC streams independently decoded with non-silent PCM; no actual human listening or naturalness claims.

**Adversarial browser/UI and response path:** Missing consent, unplayed clip, missing clarity rubric, missing event category, and absent timestamp were rejected by actual browser UI. Both actual browser download JSON records imported with the exact media root and admin source proof, producing ONLY self-reported classification inventory and zero learner readiness. R01/R02 synthetic browser ratings were physically purged before artifact retention. E2E receipt asserts actual human participants=0, actual ratings=0, human_study=NOT_RUN and production=BLOCKED. The end event was triggered via deliberate short seek, NOT full 45-second human viewing.

**Scope-compliant scientific verdict: V3-26 BOUNDED REAL-BROWSER ENGINEERING PASS at named SHA.** The reviewer instrument is working and can later support two independent, domain-competent, consented human reviewers only under separate authorization. At this point there are NO real human outcomes, NO V3-16 12-topic quality statistics, NO independent audio-quality evidence, NO 3Blue1Brown parity claim and NO product release approval. Documentation-only follow-up HEAD requires independently checking its own CI and artifacts before reporting 26/26 for that HEAD.
