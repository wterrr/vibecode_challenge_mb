# V3-24 — Visual Clarity & Pedagogical Storytelling Refinement

**Branch/authority:** PR #58 candidate, stacked on PR #57. No `main` merge, V2 Core modification, production API, paid LLM calls or human experiment. Preserve V3-20 audio and semantic proof, V3-22 native 720p24fps output and V3-23 unmeasured human-quality gate.

## Confirmed prior-media issues and why this checkpoint exists

- V3-22 real native 1280×720/24fps H264 media uses Computer Modern and 32px actions/captions but inherits V3-06 **~23px pointer/index labels** and developer wording `Verified leftmost-index trace / immutable item IDs`.
- The single source example `[0,2,4,7,11,15,15,21,30]`, target 15 has certified comparisons at midpoint **4 (11, too small)**, **6 (15, candidate)** and **5 (15, earlier candidate)**; final result index **5**. Merely pointing at MID and reporting MATCH misses why binary search should check left.
- The source V3-20 media has 541 H264 frames at 12fps and 10 actual spoken utterance/event boundaries. V3-22 has 1082 frames at 24fps, original AAC packets copied bit-identically. **Utterance boundaries are not measured word-level onsets**.
- V3-23 did not run an independent human viewer study; readability, cognitive load, pronunciation, aesthetics and comprehension effects remain **UNMEASURED**.

## Source-preserving implementation

Introduce `learnflow_v3/teaching_storyboard.py`, reusing the V3-22 oracle-native H264 renderer (Pillow + installed OS Computer Modern), frame pacing/32px original captions, `_source_evidence`/V3-20 physical WAV proof and no-clobber stream-copy AAC encoding. **No video upscale, fabricated instruction from an LLM or rerendered TTS.**

Visual design changes are authored as overlays **on the same source-certified sequence renderer**, not generic concept cards:

1. Replace engineer-facing microcopy with `Every comparison narrows the search`; preserve original binary search title and target.
2. Redraw pointer labels at **32px CMU** and index labels at **29px CMU** using original item centers and oracle pointer positions; never move array item identities.
3. Use semantic event-specific narrative headline: make goal explicit (`FIRST 15`), on equality distinguish a provisional `candidate` from final leftmost answer, and direct the viewer to search left while the APPLY utterance plays.
4. **Protect against future-state leakage:** oracle steps internally carry candidate index after each compare. A source step indexed by the *future* visual state would expose candidate=5 during the previous APPLY. Derive visible candidate using event provenance: OBSERVE uses the last already-applied candidate; APPLY uses the just-applied step's candidate; RESULT uses the certified result. Required transition **none → index 6 → persist index 6 → index 5**.
5. Preserve source sentence text in burned captions, physical audio start times, exact source trace and same H264 dimensions/FPS/frame count as V3-22. Encode original eSpeak AAC packets with `-c:a copy`. No guesses about word/phoneme timing.

## Mandatory actual decoded-quality and mutation checks

- Render **three real same-source H264/AAC MP4s**: V3-20 360p, baseline V3-22 720p and new V3-24 720p. Programmatic before/after screenshot contact sheet at eight fixed timestamps.
- Verify source trace/event proof, original SRT hash, byte-identical AAC ADTS packet hash, 1082 H264 frames at 1280×720/24fps, semantic frame replay with 4 anchor frames per utterance, and three APPLY→next OBSERVE/RESULT ROI transitions. Confirm actual before/after frame-pixel differences rather than asserting a redraw succeeded.
- Negative tests: wrong MP4 hash/audio, forged human-education/word-level/release claims, unsafe output overwrite, wrong scripted leftmost handling, early candidate reveal, future oracle state leakage. Re-run protected V3-22, V3-20, frozen V2/Hermes, preregistration, LearnFlowBench and Core Freeze.

## Bounded acceptance and limits

Engineering technical PASS requires exact final PR-head GitHub Actions and actual downloadable MP4/artifact review. This is an **author-designed, source-grounded explanation change**, not causal evidence of learner learning gain. Perceptual legibility at actual viewer distance, 3Blue1Brown aesthetics/learning parity, word-level alignment, naturalness of original eSpeak speech, 12-topic pilot results and commercial voice/output rights remain **UNMEASURED / BLOCKED**. Human reviewer packet from V3-23 stays unscored, and publishing remains forbidden.

**Decision:** PENDING EXACT-HEAD CI AND REAL BEFORE/AFTER MP4; do not declare quality PASS without the evidence.


## Verified code-head closure and independent full-video/frame inspection (2026-10-09)

- **Exact implementation SHA `398c3d749a2dae4ad223384328c6d2592ac810c8`: 24/24 commit-scoped GitHub Actions SUCCESS**, including real [V3-24 workflow #37872412940](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37872412940). Workflow log: **7 new V3-24**, **8 native V3-22**, **15 V3-20**, **39 Frozen V2**, **86 Hermes** tests PASS; preregistered 12-topic V3 benchmark, LearnFlowBench and Core Freeze PASS.
- Independently downloaded actual [artifact #11591067933](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37872412940/artifacts/11591067933): ZIP includes original source H264/AAC MP4/SRT/event proof, V3-22 native 720p baseline, V3-24 native 720p target, SHA-bound receipts, JSON quality evidence and before/after frame contact sheet. Verified **16 members** and extracted/read actual decoded frame images and QA receipt.
- Baseline native V3-22 H264 file SHA-256 `7942d193f0b14c9ced4999909fbaa4efd45e72d40c01a3994dbba8bfc8cbe17e`; final V3-24 H264 file SHA-256 **`a070e70e0110d889bcc6421738044d752012fb42f977ddb7faf18faf80896fc0`**. Both 1280×720 / 24fps / 1082 frames, and V3-24 reuses exact original V3-20 AAC packet digest/event proof/physical SRT timing.
- **40 certified oracle image anchors replayed** from independently decoded V3-24 MP4: maximum RGB full-frame MAE **0.4362** (0–255 mean channel error). No selected APPLY→OBSERVE/RESULT pointer/candidate rewind: three inspected ROI boundaries **479→480 = 0**, **641→642 = 0**, **803→804 = 0**. Eight actual source-matched V3-22/V3-24 frame comparisons show nonidentical rendered pixels with full-frame RGB MAE **2.8755–6.2296**, proving a perceptible structural redraw occurred rather than unchanged copied video; these values are not human visual preference measurements.
- **Manual decoded-image reinspection** at 17.333s and 26.750s found the first V3-24 implementation had accidentally erased half the top horizontal separator and left the green candidate index unexplained. Fixed at implementation SHA `398c3d7`: separator is continuous at pixel y151 and candidate is labeled `BEST SO FAR / INDEX 6` in a separate learner-visible band only after the source-certified APPLY event. Source readout at 26.75s: MID now examines index 5, candidate still 6, and headline asks whether an earlier match exists. The first draft's 24/24 CI PASS **did not detect** the broken line; the final commit adds explicit geometric and no-premature-badge regressions.
- **Honest residual limits:** macro layout remains sparse/black-board-like; original eSpeak voice quality/word-level timing, 3Blue1Brown parity, audience-device readability, independent human transfer accuracy, generalization across the frozen 12 topics, and commercial voice rights are UNMEASURED/UNVERIFIED. **Learner-quality approval and production publication remain BLOCKED.**

**Decision:** V3-24 **BOUNDED OFFLINE ENGINEERING PASS at code SHA `398c3d7`**. The documentation-only follow-up commit that carries this closure is a *different SHA* and must be checked independently; do not inherit CI status across commits. PR #58 stays stacked on #57; do not merge `main` or promote to production.


### V3-24/V3-25 follow-up: candidate outline exact cell-fit correction (2026-10-09)

Manual user feedback: the candidate's green outline looks wider/longer than the gray array slot. Confirmed in `learnflow_v3/teaching_storyboard.py`: the old overlay was hard-coded `(x-46,341,x+46,425)` with radius 10, width 3, while `learnflow_v3/sequence_renderer.py` draws source cells centered at `round(288*sy)` with half width `max(10,min(round(34*sx),round(gap*.42)))`, half height `round(34*sy)`, radius `round(10*sy)`, stroke `max(2,round(2*sy))`. At 1280×720 on the 9-item example, the green rectangle was 92×84 px versus the gray cell **90×90 px**. The green border now derives the exact gray rect, radius and stroke from the native renderer's geometry (not an invented fixed box) and is source-bound to the certified candidate. Dedicated tests check all four sides, green-pixel extent, candidate semantic event and layouts for 1/6/9/16 cells. This is a narrowly scoped visual bugfix; no change to algorithm, source narration/SRT/AAC, audience claims or production permissions. The new exact-code-HEAD real MP4 CI must PASS before closing this issue.
