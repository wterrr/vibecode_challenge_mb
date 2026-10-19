# V3-58 — Matched Pedagogical Animation Ablation & Independent Review Readiness

**Scientific verdict: TECHNICAL PAIRED-NATIVE MEDIA PROOF (local) PASS; independent pedagogical quality UNRATED / NO-GO; model-authored creativity NOT TESTED; production BLOCKED.** 
One Draft child PR stacked on V3-57 Draft PR #91, exact parent HEAD `48a7b8d955a442b5f693c7e8fcaae0f8c44effa8`, not `main`. Initial V3-57 [Push CI #38342127165](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38342127165) and [PR CI #38342132039](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38342132039) remained queued at entry; do **not** claim parent exact-head CI PASS. Frozen **FIRST child commit** `9a2c0b0881e2ca9451888ae09b0cf5ecb560b50d`, registration [here](../benchmarks/learnflowbench/v3/v3_58_matched_pedagogy_preregister.json), before implementation. No provider/model API, no 3B1B copyrighted media, no V2 Core/production prompt changes.

## Reuse-first audit and important parent integrity discovery

- V3-57 `pedagogical_storytelling_slice.py` already offers finite five-beat, host-restricted Attention, Fraction and UNKNOWN process frame rendering; `pedagogical_explanation_adapter.py` binds existing V3-56 research PEC to those approved claims. Reuse those renderers and original TTS audio, rather than generating any arbitrary new model Python or graphics.
- V3-55 `independent_pedagogical_quality.py` defines independent rating categories and explicit `UNRATED`/learning-outcome guards. Its prior sample clips are **not** duration-controlled against V3-57, so the V3-58 *primary* comparison is within-case motion vs static with identical audio/timing, **not** V3-55 vs V3-57 nor 3B1B vs LearnFlow.
- **Observed V3-57 receipt mismatch:** exact three actual source MP4 files contain one fewer video frame than their accompanying `native_frames` receipts (verified by independent ffprobe). All cases have an AAC track slightly longer than the video; the V3-57 final FFmpeg mux uses `-shortest`. The V3-58 renderer treats the **actual decoded movie frames as authoritative**, allows only delta 0 or 1 and reports delta per case. This is a technical evidence correction, **not** a retroactive V3-57 clean PASS. Source unchanged.

## Matched control definition

For each frozen case:

1. **Motion treatment:** the original V3-57 native video; exact host-ledger, same five approved beat narration segments and motion progress.
2. **Static treatment:** for each beat render the **same final state** via `render_image(plan, beat, 1.0)`, holding it for that beat's exact registered duration. Between-beat cuts remain; no new facts or altered narration. The final state's early reveal is a **material confound** (this is a combined motion/reveal treatment, *not* a pure causal measure of motion).
3. Reuse **the original actual AAC packets** with FFmpeg stream copy, neither synthesizing nor re-encoding them. Preserve the original **decoded H264 frame count**, 15 fps, 1280×720 and approximate duration. Compare extracted ADTS AAC packet hashes, FFprobe frame metadata, and directly decoded static end-state frames for each of 5 beats.
4. Prepare six clips as three fixed topic-pairs with deterministic A/B label order. Place the *condition mapping key separately* from the blinded reviewer packet. The conditions are perceptually discernible (one moves, one does not), so this is **masked treatment label**, not double-blind viewing.
5. Provide a **blank** review CSV with ratings for explanatory clarity, visible causal witness, object continuity, typography legibility and narration pacing. Target **three independent complete raters**. No scores, identities or learning gains are fabricated.

### Direct local native MP4 check (not GitHub CI yet)

| Case | Original V3-57 receipt frame claim | Actual H264 frames, BOTH treatments | AAC packet SHA256 (identical within pair) | Decoded static beat state MAE range (0–255) |
|---|---:|---:|---|---|
| Attention reversed query | 358 | **357** | `f099882900b4f8bfa43248f8a2a0b48934b0b10d27976ea71055f8b2f6e5d2a1` | 1.90–2.03 |
| Fraction equivalence | 342 | **341** | `1d30dbab857a3f938d8e2e1e0c52c388c472b9e5ed2b865a98bd44a05d932de7` | 1.73–1.98 |
| Process heldout UNKNOWN | 347 | **346** | `15f49010f34cf311707c8a9c78ffb5b7a8bbe34764b25d22275e16137e1b6c7d` | 1.83–2.15 |

Local native tested SHA pairs: 
- Attention motion `a77222167a03073e508a97c91e7e3536edba5858c1dbc9d9db5adb2ac5a2784d`, static `77d8d16e6699f0faf15e1e87268091ecab68b7534f38a0d2c3647c54322e41f5`.
- Fraction motion `52dc8c8a0025c488960d66ce48a85b89ec91ba66a690d943121a58c5d9a8c421`, static `600e59d8bf4fd132505af125ade320aa71877ec328315a861939e220316891f2`.
- Process motion `ea4ef246e3c3c2de410becd473d79aa80725d465a709fb48f6214366ea2f71bc`, static `5e0f09add7499469f42cdf4a952dc2b6ca2d69c6e7a31936edc85ba34910ad11`.

The source MP4s are **original project host-generated media**, not 3B1B copies. Native media reviewed locally and pair receipts can be reproduced from `scripts/run_v3_58_matched_review.py --v357-dir <existing V3-57 output> --output-dir <fresh output>`; exact-head CI pending. Neither hash matching nor a low image reconstruction error is evidence of comprehension.

## Direct visual inventory — do not mark pedagogical quality PASS

A three-case pair contact sheet and frame snippets were actually opened. The output remains sparse/diagram-oriented, with substantial empty screen area and comparatively small narration/equation text at 1280×720. Native-motion differences are visible, but not every motion reveals a semantic state change.

| Quality observation | Concrete source/media evidence | Risk | Acceptance |
|---|---|---|---|
| Fraction **early-reveal-before-cause** | In V3-57 renderer, `n=6 if idx>=2 else 3`, `scale=2`, and the on-screen label switches immediately to `4 / 6` at the **beginning** of `SUBDIVIDE`; amber split guides animate only *after* the new partition is already drawn | Motion may illustrate decorative tracing of an already-revealed answer instead of causing the 2/3→4/6 mental transition | **KNOWN PEDAGOGICAL BLOCKER**; ensure old 3-cell state persists until host-certified split event, then reveal two child partitions with referent continuity |
| Process **pre-activated action** | `ACTION` node becomes green at `idx>=2` from first frame of `STATE_TRANSITION`, before a green tracking marker travels across the edge | Source→destination causal ordering may be visually inverted | **KNOWN PEDAGOGICAL BLOCKER**; bind state activation to actual marker arrival and graph transition proof |
| Attention normalization already numerically labeled | In `SOFTMAX_NORMALIZATION` beat, final `w(A)`/`w(B)` text is visible before a lower bar grows | Bar may not visually explain softmax arithmetic; visually showing weighted selection is not evidence of how normalization works | **INCOMPLETE EXPLANATION**; register numeric prerequisite trace and actual score-to-weight witness |
| Static controls display the complete final state from beat onset | V3-58 intervention as registered | Confounds motion with answer reveal timing | **INTERPRET REVIEW AS COMBINED INTERVENTION**, no pure animation causal effect |
| Human rating and speech alignment | eSpeak beat segments exist; no human independent ratings or native word alignment | AV technical PASS does not mean timing is pedagogically sound | **UNRATED / NOT_MEASURED** |

These are **source-and-visible-image observations**, not human cognitive test results. The two known early-reveal errors mean a claim like “V3-57 already reasons like 3Blue1Brown” would be ungrounded, regardless of pixel differences.

## Agent-authoring readiness — typed fixture, not real model

New opt-in `learnflow_v3/pedagogical_authoring_readiness.py` accepts a strict `ProposedStory` and five `PedagogicalChoice` entries. It binds immutable V3-57 host-ledger SHA, case, approved operation, approved claim and referent, expected `OBSERVE_HOLD` vs `SEMANTIC_MOTION`, and per-step rationale. It forbids new facts, fictitious motion on a static witness, invented speaker lead/lag, model-authorship origin forgery, unbounded code and `allow_publish=true`.

A deterministic **offline synthetic fixture** passes schema validation in the three registered cases; this demonstrates only *an accept/reject boundary*. The fixture is not authored by an LLM and does **not** demonstrate model ability to invent valid explanations. Narrative strings and geometry are still fixed by the existing V3-57 renderer. Real agent creativity **NOT TESTED** and production stays BLOCKED.

## Independent evaluation and decision gates

The reviewer packet has exactly 6 native MP4 files, one `blank_review.csv` and reviewer instructions. No admin mapping key is included with it. An independent judge should rate each treatment (1–5 or unrated) for the five prereg criteria and record the timestamps for causes of confusion/misleading early reveals. Three complete independent raters targeted; responses verified by ID/clip/score field and duplicates rejected. Until actually supplied, `quality=UNRATED_NO_EXTERNAL_HUMAN_REVIEW` and `human_learning_effect=NOT_MEASURED` are immutable statuses; questionnaire judgments would still not establish measured student learning.

| Gate | Conclusion |
|---|---|
| Local proof of 3× paired H264/AAC with identical AAC packet sequences | **PASS**, exact native decoded count and 15 end-state frames inspected |
| V3-57 original receipt exact frame count | **MISREPORTS ONE EXTRA**, documented/reconciled |
| Human pedagogical quality and blinded ratings | **NO-GO / UNRATED** (0 of planned 3 reviewers) |
| Model-authored pedagogical design | **NO-GO / NOT TESTED** (only synthetic fixture acceptance) |
| Evidence correctness of 2/3→4/6 division timing, transition path causality | **KNOWN VISUAL TIMING GAPS**, no quality GO |
| V2 Core / production prompts | **UNCHANGED** |
| Model API posts | **0** |
| Production release | **BLOCKED** |
| Exact-head GitHub CI | **PENDING**, do not infer completed PASS from queued jobs |

**Recommendation after this strictly isolated checkpoint:** obtain three independent completed review packets, then prioritize a *semantic precondition→transformation→visible consequence* validator in the next checkpoint. Do not add increasingly elaborate prompts as a substitute for actual causality in decoded frames. No claim that the 3B1B film is a matched baseline or that synthetic fixture acceptance proves independent agent creativity.
