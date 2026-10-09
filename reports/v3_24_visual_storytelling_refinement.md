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
