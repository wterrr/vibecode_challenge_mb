# V3-56 — User-Supplied Timed Transcript × Native MP4 Semantic-Witness Audit

**Checkpoint and scope:** same Draft PR #90, stacked on Draft PR #89; no merge `main`, no provider API, no production/Hermes/V2 Core source modifications. This addendum follows the earlier preregistered 12-lesson-anchor design and the native PCM + video timing research. No claim to have performed licensed ASR or manually verified the actual spoken audio.

## Evidence accession and scientific distinctions

The user supplied a text transcript containing explicit `(M:SS)` markers for **3Blue1Brown — Attention in Transformers, Deep Learning Chapter 6**.

- Original text upload: SHA256 `4a6eed896d548af41526e4995b66d7ef35951a6bfdfe1d106ee8764d2a98f3a5`, **31,405 bytes**, 64 lines, **449 timestamped segments**, 449 unique monotonically increasing timestamps, from **00:00** to **25:45**. No extraction model/version, confidence, forced-alignment method, or manual audio verification procedure was provided. Approximately the last **24 seconds** of the film are not covered by a transcript cue.
- Original full user MP4 rehashed **again**: SHA256 `439e154fffbb8696a37753d765c4f64bc06d25fbb17cb3d98bcc842045d85cb9`, 56,718,320 bytes, 26:09.191, H264 1280×720 30fps, AAC soundtrack.
- Reused 12 frozen Attention anchor IDs from PR #90 and sampled **8 native frames at 2-second separation for each anchor, 96 new direct native decoded frames**, independently visible contact sheets across 3 private inspection pages. For each anchor the file contains the user-transcript timestamp and individual phrase SHA, user-uploaded source line, observed screenshot content, 2-second candidate appearance bracket and actual native-frame SHA.
- The report **does not republish** the original full transcript, full audio, copyrighted 3B1B video or screenshots to GitHub. Only hashes, indices, source-line identifiers, and a short independent semantic paraphrase are stored.
- Two distinct clocks: **USER_TIMED_TEXT** is not native speech word onset. **NATIVE_SCREEN_VISIBILITY** is evidenced by decoded frames, but a two-second sample bracket is not an exact edit/animation frame or a learning metric. Offsets between the two are exploratory **text-cue-to-visual** observations, *not independently verified speech-to-visual latency*. Native PCM was decoded in the previous V3-56 audit but **no validated ASR/manual native spoken-word listening** has been performed. Never assign native WER, phrase correctness, phoneme timings or listener confidence.

## 12 direct native-screen and user-transcript correspondence cases

Each transcript cue below is taken from the actual uploaded document (source-provenance marker and phrase SHA in [machine receipt](../research/v3_56_user_timestamped_transcript_receipt.json)). Native screen appearance candidates are bracketed from 2-second sampled screenshots, not assumed exact first frames.

| Frozen anchor | User transcript time | What the text *reports* | Actual visible native frame evidence | Bracket (s) |
|---|---|---|---|---|
| `mole` | **02:00** | Introduces three contexts to motivate polysemy | 01:58 still figures; 02:00 first letters of example; 02:02–02:06 all three word contexts are built | 118–120 |
| `running_sentence` | **04:35** | Gives the running example of a fluffy blue creature in a forest | 04:33 text begins, 04:35 phrase and creature illustration established, 04:39–04:43 adjectives highlighted | 271–273 |
| `query_motivating` | **06:19** | A noun asks whether there are adjectives ahead of it | Bubble emerges around 06:17, clear on the `creature` token 06:19; later neighboring adjectives answer | 375–377 |
| `query_to_key` | **07:47** | A second matrix maps tokens to keys | 07:47 comic about learned head, 07:49 switch to token-wise `W_K` projections | 467–469 |
| `score_matrix` | **08:27** | Compare a key and query using dot products | 08:28 Q/K grid constructed, 08:36–08:38 dot magnitude becomes salient | 506–508 |
| `softmax` | **09:52** | Normalize a column of attention scores with softmax | 09:50 the word Softmax! appears in bubble, 09:52 persists, 09:54–10:00 matrix rotates into column view | 588–590 |
| `mask` | **12:13** | Force future-token cells to negative infinity before softmax | 12:15 comparison of raw/normalized patterns; by 12:19 masked entries read `−∞`, soon output columns normalize | 737–739 |
| `values` | **13:44** | Value matrix converts embeddings to update vectors | 13:44 `fluffy creature` semantic geometry, 13:48 red `W_V` matrix, 13:50 projected Value diagram | 826–828 |
| `weighting` | **14:42** | Multiply each value by its column attention weight | Score/value matrix held 14:36–14:42, individual column weights revealed 14:44, weighted pieces 14:46–14:50 | 882–884 |
| `multihead` | **20:37** | One attention head becomes many parallel heads | 20:35 single-head grid; 20:37 flips into many planes, 20:39–20:45 explicitly labeled multi-headed attention | 1235–1237 |
| `output` | **22:45** | Value-up maps together become one output matrix | 22:44–22:50 head-specific value-up panels, distinct Output matrix visible 22:52 | 1370–1372 |
| `return_context` | **23:35** | Repeat attention and MLP blocks through Transformer | 23:29 network+MLP; 23:35–23:43 stacked layers recur and form a full model | 1413–1415 |

**Native frame-level samples at 2-second intervals cannot establish sub-second speech or object onsets**. The source time from the user's file usually denotes the *start of one short transcript chunk*, not its duration or a definitive microphone-timed phoneme boundary.

## Important source disagreement inventory (do not silently normalize)

1. **02:00—word misrecognition plausible:** user transcript says **`American true mole`**; native on-screen English text at 02:02 visibly says **`American shrew mole`**. This is **text transcript vs visual label discrepancy**; it does *not* prove what the speaker pronounced until the source audio is independently reviewed. Label `TEXT_VISUAL_LEXICAL_DISCREPANCY`, not an invented ASR WER or human correction.
2. **05:45—misaligned previous proxy description:** user's source begins the caveat "making up" the adjective-noun head example around **05:45**, and continues discussing limited model interpretability through 06:10; previous V3-56 external-caption audit summarized this as "05:57 made-up" and that cue was overly late for the beginning of the caveat. The new transcript supports marking the scope as explicitly *illustrative*, without assuming the actual learned head behaves in this way.
3. **04:35 visual and text coincide closely in sampled frames**, but this is a visually plausible synchronization of written text to a caption start, not measured native word alignment.
4. **09:50 on-screen Softmax precedes the user transcript cue of 09:52**; the screen can intentionally anticipate a named operation, and there is no reason to enforce "same second exactly" for all narration.
5. **12:13 conceptual setup vs 12:19 `−∞` cells:** the explanation prepares an operation before rendering its computed consequence.
6. **22:45 explanation of the shared output matrix precedes the visibly labeled Output matrix around 22:52.** This is a *candidate staged reveal*, not a certified 7-second acoustic delay.

A possible text-level transcription error elsewhere labels an *attention* head as "intention" around 05:48; it must remain a marked suspect until a native listener or acoustic ASR confirms rather than secretly correcting the user's file.

## Pedagogical decision grammar — evidence versus hypothesis

The user transcript increases the specificity of the **script/content sequencing** significantly. In the source text:

- **Problem then mechanism:** multi-sense `mole` (02:00) and spatial `tower` examples are used before matrix operators and parameter counts. The difficulty is framed as the *lack of token context*, not "learn to multiply matrices".
- **Overt simplification and uncertainty:** around 04:42, 05:04, **05:45–06:10**, the script differentiates simplified teaching assumptions from actual learned-head interpretability. The model hypothesis remains an imagined aid, not mechanistic introspection proof.
- **Question → Query:** from 06:14 the concept "need adjective information" is posed as a question, 06:19 on-screen and in user text, then query vectors and `W_Q` are introduced (~06:34–06:46).
- **Concrete pair → global matrix:** one Q/K match precedes computing all dot products (~08:27–08:41); the grid becomes visible while the text explains why dot magnitude matters.
- **Purpose of normalization → operator:** first require weights in [0,1] and column sums of 1 (~09:36–09:44); *then* give softmax at 09:52. This is reasoning-led, not formula-led decoration.
- **Counterexample/failure then fix:** explain that simply zeroing future positions would break column normalization (~12:06–12:11); *then* show `−∞` input scores before softmax (~12:13–12:22). To teach causal masking, animate the **failed naïve approach** and the corrected invariant, grounded in host-verified arithmetic.
- **Selection before transport:** Q/K and softmax determine relevance; only **13:10–15:39** does the lesson explain what the Value vector transports and how `ΔE` is accumulated. Distinguish two typed causal mechanisms.
- **Pedagogically justified hold:** 14:36–14:42 attention pattern is fairly static while transcript explains value vectors. The word text supports an explanatory purpose; PCM energy alone cannot prove actual delivery or that stillness improves learning.
- **One-to-many and return to whole:** 20:31 one head becomes multi-head; 22:16–23:17 output-matrix implementation detail is framed as potentially distracting; 23:19+ the whole model is revisited, with a forward bridge to the next chapter.
- **Explicit scope and omissions:** author's text signals when a concept is a simplified representation, when details are postponed, and when alternative derivations are not explained. LearnFlow prompts should specify **deliberate omission** and **resolution of deferred concepts**, rather than rendering all technically possible details.

The above is a falsifiable research hypothesis about effective teaching design and a verified *order in the submitted text*, not a randomized/controlled measurement of learning.

## Concrete V3 PEC and agent changes (research-only; not implemented)

Extend current V3 research-side `narration_visual_evidence.text_cue_source` with a distinct `USER_SUPPLIED_TIMED_TRANSCRIPT_UNVERIFIED` classification. Record source text file SHA, source exact fragment SHA, native video SHA, and physical sampled visible interval separately. An externally supplied timestamp **cannot** promote `audio_content_certification` to native-word alignment, regardless of apparent visual synchronization.

Suggested properties: `pedagogical_beat_kind=PROBLEM_SETUP|QUESTION|CONSTRAINT|COUNTEREXAMPLE|OPERATION|OBSERVE_HOLD|CLOSURE`, `learning_claim_id`, `source_text_cue_s`, `native_visual_witness_window_s`, `witness_evidence_grade`, `speech_verification=UNKNOWN|MANUALLY_HEARD|ASR_CHECKED`, `semantic_referent_id`, `deferred_idea_resolution_beat_id`. All host-validated with nonnegative durations and no unsupported new renderer operations.

Existing V3-55 `intro/compare/normalize/inspect/transport/compose` finite director operations remain reusable for a small illustrative Attention calculation. Not yet demonstrated: generalized mental-model misconception and later closure, voice-to-scene verified referent binding, text→geometry→matrix transitions, host-certified false-approach/normalization invariant pairs, or narration-inferred holds. **Do not compare quality causally**: V3-55 is 63.8s/15fps and 3B1B source is 1569.19s/30fps. V2 Core remains frozen.

## Acceptance and next bounded step

| Gate | Verdict |
|---|---|
| User-provided timestamped transcript file/accession | **PASS**, 449 sorted unique cues with SHA |
| User text × original native MP4 screen correspondence | **BOUNDED PASS**, 12/12 sampled semantic witnesses |
| Independent native audio spoken-word accuracy | **NO-GO**, no known ASR engine/provenance or independent listening |
| Native word-level phoneme forced alignment | **NOT VERIFIED**, no available forced aligner/model |
| Research pedagogical visual/sequencing mechanisms | **BOUNDED RESEARCH GO**, no learning gains measured |
| V3 agent architecture proposal | **RESEARCH-ONLY GO**, runtime still NO-GO |
| Exact-head CI | Requires GitHub result; never infer PASS from queued |
| Production | **BLOCKED** |

Recommended action within V3-56: use the *user-provided transcript* as an unverified hypothesis to manually audit the specific suspected words (02:00 `true/shrew`, 05:45 example caveat) and to spot-check the 12 cue timings against original AAC. A real listener/ASR in a later environment must verify each phoneme or phrase independently; merely having the text with timecodes satisfies textual temporal data availability, **not native word accuracy**. No fresh paid model API should be called.

**Reproducibility:** [receipt](../research/v3_56_user_timestamped_transcript_receipt.json), [offline validator](../scripts/verify_v3_56_user_timestamped_transcript.py) supporting `--source-path` and `--video-path` for local full-file SHA and segment matching, and offline mutation tests in `tests/v3/test_v3_56_user_timestamped_transcript.py`. Original transcript/video remain external to GitHub.
