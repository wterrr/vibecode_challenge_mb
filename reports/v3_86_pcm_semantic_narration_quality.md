# V3-86 — PCM-Grounded Semantic Narration, Visual Decisions and Pedagogical Timing

## Preregister and reuse
Parent Draft PR #122 exact SHA 4bc942e489576a0f8f76db118a0be493a5d19a32. First prereg before implementation: commit 71c5b612222673ac62050011d5f82c0dfc150c80. Same three positive Math/Physics/Physics heldout cases and two negative Chemistry/History ABSTAIN. Original V3-85 artifact 11958076620. No model API (free or paid), main merge, V2 Core or production prompt modifications.

## Observed root issue and bounded change
Original V3-82 narration merely read arithmetic; V3-85 upgraded chart roles but reused that generic narration and kept only two coarse script beats. Voice did not independently explain slope, initial-value intercept or why v(t) shows a plotted quantity rather than a moving physical body. V3-86 builds a finite deterministic, **fact-and-role-grounded six-utterance speech plan per lesson**. Three genuine separately synthesized eSpeak utterances per original claim: ORIENT (chart axes), TRANSFORM (slope/curve and numerical change), INTERPRET (exact result and causal meaning). Each semantic phase is linked to source SHA, original claim ID, independent WAV sample count, exact frame budget and one corresponding host-generated native Manim decision. All media reuse original network-isolated pinned Manim Docker, eSpeak WAV, strict FFmpeg mux and visual/pixel gates.

## Temporal evidence
Utterance sample and frame ranges are genuinely synthesized, not guessed. A decoded H264 gate checks chart axes during spoken orientation, visible curve and vertical slope during spoken transformation, and exact result formula during voiced interpretation; three native samples within each phase. Six phases per lesson, 18 actual WAV segments and 18 physical event witnesses across the locked set. Hostile tests fail closed wrong facts, source, roles, claim identity, phase order, audio gaps, inadequate durations and unsupported questions.

**Important:** This demonstrates audio alignment at the independently generated *semantic utterance segment* level. This is NOT ASR or phoneme-level/word-level alignment and does not prove perceptual understanding. Physics graph point never asserts traveled position or distance. Historical OpenStax source text is curated old evidence, not freshly independently verified. Model-authored pedagogical decisions and six-domain autonomy NOT TESTED.

## Acceptance
3/3 true native H264/AAC MP4, 2/2 ABSTAIN, full FFmpeg decode, exact audio sample/frame budgets, no silent static-card fallback or case substitutions. Run V3-86 plus V3-85/84/83/82/81/80 regressions; V2 Core freeze and V3 benchmark protocol. Keep PR Draft; Final Visual Quality NOT PASS pending human review, learner gain unmeasured and production BLOCKED.

## Verification status
Await exact HEAD GitHub Actions and downloaded native artifact. Never turn absence of failures into a PASS without media proof.

## First real native failure and measured source-level fix
First GitHub Push #38706682459 finished 140+ V3-86 tests but the actual first V3-86 Math video correctly failed the stricter independent visual gate, not arithmetic or audio mux. Uploaded artifact #11958458709 was downloaded; direct ffprobe verifies real 1056-frame H264/AAC MP4. Six separately synthesized WAV budgets: 187,173,186,180,138,192 exact native frames. Decoded early/late chart-ROI pixel changes by audio phase: 4403,5919,4,4405,6988,3; early/late **answer**-ROI changes were 0,0,1199,0,0,1342. Thus INTERPRET physically revealed the result below the plot but its chart itself remained intentionally unchanged. QA was incorrectly inspecting only chart ROI for the interpretation decision. Replaced with phase-scoped ROI: ORIENT/TRANSFORM chart (minimum 850), INTERPRET answer region (minimum 500); preserves real evidence requirement rather than weakening it or faking visual change. New exact-head CI and all three native videos must rerun before Technical PASS.
