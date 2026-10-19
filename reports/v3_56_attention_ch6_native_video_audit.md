# V3-56 — Real Native-Video Audit #1: Attention in Transformers (Deep Learning Chapter 6)

## Media provenance and inspection protocol

**FIRST ACTUAL ORIGINAL 3BLUE1BROWN FILM RECEIVED (from user upload).** This is an evidence addendum to V3-56 Draft PR #90, not a new checkpoint, paid model evaluation, or production prompt. Original MP4 and copyright-protected frames were NOT committed to the repository.

- User-uploaded file: `Attention in transformers, step-by-step _ Deep Learning Chapter 6.mp4`.
- SHA256: `439e154fffbb8696a37753d765c4f64bc06d25fbb17cb3d98bcc842045d85cb9`. Size 56,718,320 bytes. Native video 1280×720, H.264, **30 fps**, **47,076 frames**; duration ~**26:09.19** (1,569.19s). AAC soundtrack 44.1kHz, no subtitle stream.
- Independently inspected **105 decoded actual source frames sampled every 15 seconds across the entire 26-minute file**, then **~70 additional decoded frames in seven focused temporal sequences**, including context, embeddings, Q/K maps, softmax and causal masking, value mixing, multihead output and lesson closing. Video was navigated by native-time seek, not replayed continuously second-by-second.
- Decoded the audio track and inspected its presence/continuity and RMS; **the spoken narration was not transcribed, semantically listened through, or force-aligned to words**. No word-level timing or narration text-vs-frame synchrony claim is certified. The audio exists and spans the timeline, but stream metadata and RMS are NOT speech-semantic evidence. Final exact visual section boundaries are approximate sampled-frame ranges, NOT verified editor cut points.
- Matching [official Read](https://www.3blue1brown.com/lessons/attention/) and [first-party Python scenes](https://github.com/3b1b/videos/blob/806af030062a7e00703ed2708c0a503f01bad22f/_2024/transformers/attention.py). Source contains `QueryMap` (~L1715), `KeyMap` (~L1839), `DescribeAttentionEquation` (~L1850), `ShowMasking` (~L2169), `IntroduceValueMatrix` (~L2313), `MultiHeadedAttention` (~L3503); source-to-individual-video-shot class attribution is **candidate correspondence**, not proved by instrumented rendering.

Machine-readable per-beat native timestamp receipts and pixel comparisons: [`research/v3_56_attention_ch6_native_video_receipt.json`](../research/v3_56_attention_ch6_native_video_receipt.json).

## Approximate real native timecoded visual story

| Native film position | Decoded-frame observations | Pedagogical inference, not measured learner state |
|---|---|---|
| 00:00–01:45 | Prior Transformer architecture, chapter framing; words-to-vectors, convenient simplification | Recap what must be known, and expose insufficiency of assigning one fixed word meaning |
| 01:45–03:35 | The word **mole** held constant inside three different sentences (animal, chemical quantity, medical); **tower** in varied visual contexts; vector arrows shift/associate with alternative images | Same lexical token requires context-dependent representation; meaning depends on surrounding words |
| 03:35–04:45 | Deep network stack zoom, prose passage and long highlighted text-to-text connections | Need to transport information over distant text rather than decorate architecture |
| 04:45–06:20 | **“a fluffy blue creature roamed the verdant forest”** displayed as one persistent row of token boxes and mapped to `E₁…E₈`; 12,288-dimensional embedding indicated | Stable running example anchors subsequent matrix work and avoids a new scene for each math step |
| 06:20–07:35 | Character-like question “Any adjectives in front of me?” over the word creature; yellow `Q` vectors and `W_Q` projection | Query as “what information do I seek?”, contextual question linked to a specific token |
| 07:35–08:45 | Green/cyan `K` vectors; projected geometric axes; query/key dot-product grid emerges | Keys as searchable token descriptions; relevance matching should precede formal score matrix |
| 08:45–10:30 | One query matrix column/row illuminated, dot-product circles/numeric scores, softmax label, then full Attention formula | Attention strength gets meaning before abstract equation; highlight one instance then generalize to all tokens |
| 10:30–12:40 | Formula and next-token prediction preview; triangular exclusion of future tokens; side-by-side raw and normalized attention weights | Causal masking prevents attention to future positions; normalizing scores changes role from raw evidence to mixing coefficients |
| 12:40–13:35 | Weight matrix, then `fluffy creature` + geometrical embeddings and small representative animal images | Return from entire matrix to concrete meaning of one token's context |
| 13:35–15:40 | Red `W_V`, projected `V_i`; weighted value columns and accumulated `ΔE`; final embedding changes | Scores/selectivity Q–K are distinct from transported content V; the value-weighted aggregate is the update |
| 15:40–18:15 | Compare Q/K/V parameter maps and large dimensions, 128/12,288 frame labels and composite projection diagram | Zoom from one worked case back to the complete transform, including numerical scale |
| 18:15–19:25 | Alternative translations and contextual phrases with reused word/token/matrix format | Same mathematical mechanism can act on varied linguistic problems; sample does not establish universal linguistic reasoning |
| 19:25–22:20 | Different head patterns and weights, simultaneous matrix stacks, summed per-head updates, output map, dimensional table | Multi-head as parallel interpretations and aggregated updates, not a replacement algorithm |
| 22:20–24:40 | Wide network stack, `one` in context and parameter accounting | Reconnect local attention mechanism to overall Transformer and ambiguous words |
| 24:40–26:09 | Scope statement (attention is part of overall paper), credits/supporters | Closure and limitations: attention is a subsystem, not a complete LLM explanation |

### Physically observed motion-versus-hold examples

Decoded 320×180 grayscale frame comparisons (the percentages are changed pixels >25 luminance, **not learning-quality metrics**):
- 04:50→05:00: mean absolute change 26.97, **54.1%** pixels changed — sentence/token-to-vector layout.
- 12:13→12:23: change 37.66, **78.0%** changed — matrix/normalization representation.
- 13:37→13:47: change 34.89, **81.4%** changed — vector/value presentation.
- 14:32→14:42: change 1.32, **0.9%** changed — stable matrix/value visual hold.
- 20:20→20:30: change 1.75, **1.6%** changed — multihead matrices deliberately remain visible.
- 23:52→24:02: change 26.43, **33.2%** changed — recap/context shifts.

These pairs independently establish that the video **alternates periods of substantial visual transformation with long near-static inspection frames**. A single metric cannot distinguish deliberate hold from an unintentional freeze; the content/context around the frames supports the *hypothesis* that selected holds manage cognitive load, pending speech-alignment verification.

## Pedagogical mechanism extracted from actual video

1. **Continuity is semantic not literal geometry.** A token `creature` and other fixed sentence words persist from a textual example into E/Q/K/V projections, dot-product table, masking matrix and contextual update. Pixel coordinates and form change, but *what the variables refer to* stays traceable.
2. **Concrete question before projection mathematics.** “Any adjectives in front of me?” is visibly attached to one token before `W_Q` turns it into a vector. Thus the query has a pedagogical purpose instead of appearing as an unexplained matrix.
3. **One-case microscope then N×N generalization.** A single query–key interaction/column is highlighted and explained, then the same operation is repeated as the complete score matrix. The same object identities remain interpretable under zoom/reframing.
4. **Causal sequence separates selection from content delivery.** Q/K produces scores; masked/softmax weights define mixture coefficients; V supplies transported information; weighted sum yields `ΔE`. These are **distinct conceptual events**; smoothing them into a visual decoration loses explanatory correctness.
5. **Question hold is as important as animation.** Some dense matrix panels are stable for several seconds; motion is not compulsory, and the critic must not penalize static frames when the expected witness is static mathematical comparison.
6. **Color binding crosses representations.** Yellow query, cyan/green key and red value persist across 3D vector spaces, grids, symbols and operations; this is not merely a palette choice but object-role tracing.
7. **Return to scope and ambiguity.** Later alternate-language/context examples and multihead assembly connect learned local mechanics back to the initial problem rather than ending at the Attention formula.

### Limitations relative to LearnFlow

Current LearnFlow V3-55 only shows simple stagewise QKV / attention mixtures. This 26-minute 3B1B film demonstrates many **pedagogically motivated representation transformations and conditional visual pacing decisions**; the user-supplied file is **qualitatively richer in audited visual mechanisms** than V3-55's 63.8s synthetic Attention pilot, but duration and topic coverage differ dramatically — **not a controlled quality benchmark**. LearnFlow lacks a general host-validated mechanism for (a) one example→full score matrix extrapolation, (b) semantic-key continuous transition text↔3D vector↔matrix, (c) causal mask/softmax semantics across beats, (d) narrator-triggered focus and planned holds, (e) blind learning-outcome evaluation. Preserve V2 Core/fact ledger and register these as *capability gaps*, not automatic prompt changes.

**Observed weaknesses/risks:** Fine formula/matrix typography sometimes occupies a small fraction of the 1280×720 image, requiring good viewing resolution; long technical explanations presuppose prior Transformer/linear algebra familiarity; cartoon personification of Q/K is a metaphor, not a literal model introspection proof.

## Honest status update to the 15-video deep-audit gate

- Actual original complete MP4 supplied and visually sampled across full 26-minute runtime: **1/15 user-file native film evidence**.
- Original film **audio track decoded and confirmed present**: 1/15, but **speech-to-beat or word sync reviewed**: **0/15**.
- Entire video human-watched continuously in real time: **not claimed** (temporal still sampling, seven focused sequences); actual re-edit/camera cuts timestamp-by-timestamp **not certified**.
- 3B1B copyright protected media not redistributed to repo; only SHA, decoded-image observation metadata and derived research were committed.

The initial deep-audit required >=15 complete native video frame+audio event attestations. **Therefore full 15-video semantic+auditory deep audit still NO-GO**. This one user-supplied video **materially upgrades** the Attention record from Read/source inference to actual native-film visual evidence, not the entire corpus. V3-56 is research-only; production BLOCKED, no model API or main merge, no learning-effect claim.

**Immediate scientifically justified follow-up:** When more original videos are supplied, repeat this exact native media receipt protocol and, if transcripts are accessible, measure time-aligned speaking events separately. After 15 clips, update only validated principles/host capability deltas before proceeding to V3-57.


### Dated addition — external caption proxy ↔ user original MP4 frame evidence

The user uploaded the full actual 26-minute Attention Ch6 MP4. Beyond the original timecoded video storyboard, a later V3-56 research extension preregistered `377d1d03d47135a1b6c113e4e529d9a5ac6bc42c` and paired **12 third-party timecoded caption cues** to **60 newly decoded native frames and original AAC PCM signal**. Strong examples: at **01:49**, caption topic `mole` leads visible mole introduction ~02:01; at **05:57–06:34** a *made-up* adjective–noun mechanism becomes a visible query; at **14:30–14:54** a held matrix transitions into weighted Value contributions. Full report [Narration–Visual Alignment](v3_56_attention_narration_visual_alignment.md), machine receipt [12 anchors](../research/v3_56_attention_native_caption_alignment.json), strict verifier `scripts/verify_v3_56_attention_alignment.py`.

**Scientific limitation:** the third-party mirrored caption is NOT independent native ASR, and PCM energy/RMS cannot identify uttered words or pauses over music. Therefore exactly **12 bounded caption-topic/native-frame correspondences, 0 native word-aligned records**; the requested 15-film audiovisual study remains NO-GO. The PEC proposal gained an optional source-scoped LEAD/OVERLAP/FOLLOW link, with tests disallowing caption-proxy-to-native-speech claim laundering. Original 3B1B video/screenshots not redistributed to repo, V2 Core/production unchanged.


### Evidence-depth update — Native Speech–Visual Grounding (2026-10-13)

A new within-V3-56 source-scoped probe preregistered before measurements (`fc3a403c5a4d79ea0ac5c5409bfdf6a5f2aa7575`) used the **same original uploaded 26:09 Attention MP4** and the same 12 external-caption anchors. Actual decoded audio = **12,553,265 mono PCM samples at 8kHz**, 0.5s RMS; video = **180 directly decoded 2s-spaced native image samples** around anchors with frame SHA, strongest/weakest measured image change intervals. See [report](v3_56_native_speech_visual_grounding.md) and [receipt](../research/v3_56_native_speech_visual_grounding.json).

**Do not retrospectively upgrade external captions, frame-change peaks, or native audio RMS to observed words:** environment lacks ASR packages and pretrained model weights, with blocked model-host downloads; human native speech transcription was not independently performed. **Native word/sentence/phrase alignment = NO-GO, 0/12 verified versus >=8 prereg threshold**. The initial 12 external-cue-to-frame correspondences remain valid in their limited scope, not speech alignment. Visual explanation and optional PEC architecture = **bounded research only**, real learning outcomes and production release remain BLOCKED. No model API, no main merge, no V2 Core changes.
