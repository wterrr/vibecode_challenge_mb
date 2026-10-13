# V3-56 — Native Attention Narration–Visual Alignment & Pedagogical Decision Audit

**Checkpoint:** continuing V3-56 on [Draft PR #90](https://github.com/wterrr/vibecode_challenge_mb/pull/90). **Study status:** PROXY-CAPTION–TO–NATIVE-VISUAL ALIGNMENT COMPLETE IN BOUNDED SCOPE; NATIVE WORD-LEVEL AUDIO ALIGNMENT NOT VERIFIED; PEDAGOGICAL BENEFIT NOT MEASURED. No provider/model API, no V2 Core or production prompt modifications, no main merge. 

**Input video:** User-uploaded original `Attention in transformers, step-by-step _ Deep Learning Chapter 6.mp4`, SHA256 `439e154fffbb8696a37753d765c4f64bc06d25fbb17cb3d98bcc842045d85cb9`, 26:09.19, 1280×720 H264 30fps, ~47,076 frames, AAC 44.1 kHz. Original MP4 and raw screenshot frames **are not committed to GitHub**. Before this extension, V3-56 Draft #90 was at `97cbcc0868ff4d6d3b8a6d7278140f4969d812f0`, parent PR #89.

**Pre-registration:** `research/v3_56_attention_alignment_preregister.json`, FIRST commit `377d1d03d47135a1b6c113e4e529d9a5ac6bc42c`, before the new alignment matrix or semantic tests.

## 1. Method: explicitly separate independent observation from narrated-language proxy

1. **Direct native image:** Original uploaded encoded MP4 opened with OpenCV at deterministic timestamp targets. Re-decoded 12 focus areas × 5 frames = **60 actual native frames** for this audit (additional to prior pass of 105 full-film every-15s + ~70 dense points). Each local 320×180 grayscale frame SHA and adjacent absolute pixel-difference were measured, with one first-frame SHA per focus area recorded in GitHub. The original 1280×720 stills remain out of the repo. On-screen words/colors, object continuity and static holds were inspected from contact sheets.
2. **Direct original audio, limited scope:** All **1,569.16 seconds** of original AAC were decoded with `ffmpeg -ac 1 -ar 8000 -f s16le` into PCM and RMS was computed per second. This proves audio stream is decodable and present at each focus area. It **does not** recognize words or permit statements that the speaker actually paused (music persists).
3. **Caption-language time cues:** A third-party [2outube timed caption mirror](https://2outube.com/watch?v=eMlx5fFNoYc) provides approximate narration *topics* and coarse start times; [creator-published YouTube chapters](https://www.youtube.com/watch?v=eMlx5fFNoYc) provide second independent chapter anchors; [first-party Read](https://www.3blue1brown.com/lessons/attention/) cross-checks scientific explanatory content. These are **external caption proxies**, NOT ASR/transcription independently verified against the uploaded audio. All quoted wording in this report is minimized or paraphrased. External subtitle errors/time offset possible.
4. **Alignment receipt:** Each of 12 rows contains external cue `transcript_proxy_start_s`, fact paraphrase, five actual native frame seconds, first-frame SHA, observation, 4 pairwise luma change values, five decoded audio RMS samples, semantic relation, and "verified"/"unverified" scopes. See [machine receipt](../research/v3_56_attention_native_caption_alignment.json).
5. **No evaluation laundering:** Frame pixel difference is a *visual-change proxy*, not pedagogical success. Still frames cannot prove whether animations are smooth or whether a learner understands. The presence of spoken audio cannot establish any particular word's timing. There was no provider model call, native ASR model, word-level forced aligner, human-subject study or blind rater.

## 2. Twelve aligned pedagogical decisions

**The caption start is a speech-language cue from a different source; native video time is separately decoded.** Times represent focused sample windows, not editor-exact action onset or phoneme times.

| Caption cue (external) | Corresponding native frame window | What was directly visible and why it matters |
|---|---|---|
| **01:49** Contextual meaning of *mole* | **01:49–02:26** | At 01:49 old embedding/attention framing remains. The first *mole* example becomes visually prominent around **02:01**. The verbal motivation **can precede** the exact illustrative visual. Requiring exact word-on-first-frame simultaneity would falsely reject a deliberate narrative setup. |
| **04:29** One sentence for a head | **04:29–05:01** | Initial shot still contains previous long-text-context scene; **04:35** reveals `a fluffy blue creature roamed the verdant forest`, with token emphasis and later indexed vectors. A conceptual bridge is followed by a persistent running example. |
| **05:57** Made-up illustrative mechanism | **05:57–06:34** | A cartoon on screen explicitly labels the head scenario an illustrative **made-up example**, then the sentence appears; at 06:22 a `creature` question bubble asks what adjectives came before, and 06:34 shows a Query vector. It does not falsely equate interpretable illustration to a verified learned GPT attention head. |
| **07:38** Keys answer queries | **07:38–08:21** | Existing Q projections are augmented with K projections and selected 2D geometric directions. The visualization keeps the phrase's token identity while expanding representation, instead of replacing it with unrelated boxes. |
| **08:34** Dot-product score grid | **08:34–09:05** | Pairwise Q/K labels fill a grid, dots grow visibly by 08:40, a subset stands out around 08:46. The transition shifts attention from one matching relation to the entire score matrix. |
| **09:49** Columnwise softmax | **09:49–10:21** | One column and illustrative weight histogram convey why unbounded scores must become nonnegative mixture weights. A later 3D matrix reframe shows the operation applying column by column. Host math must independently verify numerical normalization; pixels alone do not. |
| **11:31** Prefix prediction / future leakage | **11:33–12:10** | Successively longer text prefixes with next-word targets are held before restoring Q/K attention pattern. This visually motivates why future tokens cannot influence an earlier prediction. External caption about negative infinity comes ~12:05, following the prefix rationale. |
| **13:35** Relevance to content flow | **13:31–13:53** | `fluffy creature` and embedding directions stay visible; illustrative vectors reappear, then red `W_V` maps original embeddings to values. Selection Q/K and information V are separate operations. |
| **14:22** Value map / **14:42** weighting | **14:30–14:54** | A nearly unchanged attention/value matrix is held at 14:30–14:42, then target/other columns are selectively dimmed and one weighted-sum table is visible by 14:54. Holding data while describing it is a purposeful candidate decision, not evidence the narrator was silent. |
| **20:31** Many heads in parallel | **20:19–20:43** | Before the external mult-head caption cue, a concrete example of context effects on a car's interpretation has already been shown. Around 20:37–20:43, one set of Q/K/V pattern relations expands into multiple stacked head matrices. |
| **22:29** Rearranged output projection | **22:18–22:42** | A question introduces the output matrix, then a red value map, two-stage factorization and parallel output maps. The visual challenges the simpler earlier one-head representation instead of silently overwriting it. |
| **23:33** Back to whole Transformer | **23:38–24:02** | Repeated Transformer layer stacks reappear, followed by a context-dependent example of `one`. This closes the loop from local Q/K/V operations back to contextual language understanding. |

*First-party Read/source grounding:* [attention lesson](https://www.3blue1brown.com/lessons/attention/), [creator's scene source](https://github.com/3b1b/videos/blob/806af030062a7e00703ed2708c0a503f01bad22f/_2024/transformers/attention.py). Source classes `QueryMap`, `KeyMap`, `DescribeAttentionEquation`, `ShowMasking`, `IntroduceValueMatrix`, `MultiHeadedAttention` were inspected in the previous V3-56 source audit; the **precise final shot-to-class mapping remains unproven**.

## 3. Real evidence of motion *and* planned static explanation

Multiple independent native frame comparisons (320×180 luminance M.A.D.):

- During 06:22→06:34, question bubble grows into query representation; image changes are visually substantial (not an abstract static diagram).
- During 08:34→08:46, pairwise score matrix shifts from tiny entries to size-ranked dots (causal relation attached to one variable).
- During 14:30→14:42, adjacent 6s means **1.72 and 0.71 luminance** — a near-static visible matrix, despite independently decodable audio and timecoded caption speech. This does **not** prove absence of lip/audio narration.
- During 20:31→20:43, change measures **17.17 and 32.59 luminance** across adjacent 6s — new banks of heads are introduced by physical motion.
- At 22:24→22:30, factorization is visible while the third-party timed caption introduces matrix reorganization.

**Interpretation with explicitly bounded certainty:** A useful teaching grammar alternates setup/problem/label, motion showing an operation, static `OBSERVE` or `QUESTION_HOLD`, then re-abstraction. But per-beat pause *length* and spoken words need independent native transcript ASR or manual sound listening, not audio RMS.

## 4. Prompt/schema decisions warranted by the evidence

| Verified research observation | V3 agent contract specification (not runtime code yet) | Host/QA obligation |
|---|---|---|
| Speaker motivates before actual graphic | `narration_visual_link.relation=LEAD|OVERLAP|FOLLOW`, not blanket `exact_equal` | Record independent cue and visible-onset windows, confidence; do not fabricate word FPS |
| Same token changes form (text→E/Q/K/V→matrix) | persistent **semantic referent** + `representation_change` edges, graphical identity allowed to change | Canonical referent carried across original token, projection rows, output index |
| Model-behavior analogy explicitly introduced as invented | `explanation_truth_mode=ILLUSTRATIVE_HYPOTHESIS` vs `HOST_VERIFIED_MECHANISM` | Reject proof claim that an illustrative head is actually learned behavior |
| One query pair expands into matrix | `single_case_to_generalization` planning step | Verify one-cell score derivation before scaling to grid; no unbounded numeric inventions |
| Masking follows prefix prediction rationale | causal prerequisite `requires_visible_evidence` before `causal_mask` | Host verifies masked future positions and zero after softmax |
| Q/K relevance before V transport | 2 typed effects `SCORE_SELECTION` and `CONTENT_TRANSPORT` | Check weights + value ledger independently, visual witness both stages |
| Near-static panel amid narration | `STATIC_COMPARISON` / `OBSERVE_HOLD` permitted | Do not penalize low pixel delta as bad animation; require panel legibility/human rubric |
| Per-head operation reused at N heads | `one_to_many` with referent-preserving head IDs | Later compiler proves matching topology, not copy/paste video |

A new **V3 research-only** receipt/schema may record these fields in a sidecar; frozen V2 Hermes and host fact ledger remain unchanged. Do NOT increase number of agents; map setup/analogy to Pedagogy, narration rhythm to Script, referent/representation selection to Visual Director, ordered finite motion/holds to Creative/Motion Director, and evidence-to-screen checks to existing Critic.

### Explicitly rejected easy fixes

- Longer system prompt alone cannot add `text→matrix` semantic referent mapping or a host-certified causal masking renderer.
- Caption time `05:57` does not imply an on-screen object is visible at 05:57; visual lead/lag is meaningful, not always an alignment error.
- A static frame with a high audio RMS is not proof the narrator is explaining that visual at the same instant; music confounds, native words unavailable.
- More moving pixels cannot certify a better lesson, especially compared with different total durations and topic depth.
- 3Blue1Brown's use of an explicitly imagined adjective–noun scenario does not license claims of actual learned head interpretability.

## 5. Comparison with the actual LearnFlow V3-55 Attention artifact

Physically available [V3-55 exact native Attention reversed-query video](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38328985561): SHA `5cbf7afde4b72166841c881b1111b057456037a3626d7822f3d17e76c8ff4aa3`, H264/AAC 1280×720, **15fps, 63.80s**. The user 3B1B Chapter 6 original is **26m09.19s at 30fps**. This is NOT a controlled A/B quality comparison; runtimes differ ~25× and V3-55 is offline synthetic not a genuine LLM-authored freeform lesson.

- **Already present/reusable in V3-55:** host-verified Q/K score and value mixing; finite semantic motion stages `intro,compare,normalize,transport,compose`; real MP4, H264/AAC; checks for some visible changed regions and facts.
- **Not demonstrated by V3-55:** designing `mole` ambiguity before an equation; persistent sentence/projected-row referents through different representations; single-cell→matrix generalization with prerequisite witnesses; causal-mask prefix example; real narrative lead/lag independent from storyboard timing; grounded admission that an imagined head is only an analogy; much richer static/animate pacing with human comprehension evidence.
- **Unproven also in 3B1B study:** native word-level synchronization (external captions only), causal improvement vs LearnFlow, independent reviewer scores; 3B1B scene source is CC BY-NC-SA and not eligible for copying into product.

**Next prerequisite within V3-56, no new checkpoint here:** if an offline ASR model or native subtitles become available, independently transcribe short audio slices (e.g. 05:50–06:40, 08:20–10:15, 14:15–15:00), align phrases to original PCM and update from `EXTERNAL_CAPTION_PROXY` to `NATIVE_SPEECH_VERIFIED` only after inspection. Until then, preserve exactly this scope. No model API or paid inference.

## 6. Research gate

| Gate | Result |
|---|---|
| Uploaded native 26-minute original film SHA/codecs verified | PASS |
| Direct visual inspection across film + 12 five-frame microsegments | PASS |
| PCM audio decoding for full 26 minutes | PASS; audio content not independently transcribed |
| Caption-guided phrase-to-visible-state correspondence | **BOUNDED PASS**: 12 external cue / native frame anchors, no word-level guarantee |
| Native audio spoken word-for-word timing | **UNVERIFIED** |
| Model-authored visual reasoning and learner gains | **NOT TESTED** |
| 15 independent original 3B1B full video+narration studies | **NO-GO**, 1 physically sampled, 0 fully audio aligned |
| V2 Core / production prompt changes | NONE |
| Paid model API | ZERO |
| Production | BLOCKED |

**Conclusion:** The useful contribution is a falsifiable **narration-intent ↔ visible semantic witness** specification that tolerates motivated lead/lag and purposeful holds, now grounded in original MP4 frames and externally timestamped language cues. This is much stronger than Read-only extrapolation but cannot be called certified native narration sync or quality improvement.
