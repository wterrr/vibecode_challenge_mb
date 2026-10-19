# V3-44 — Semantic Visual Transformation & Narration Alignment Redesign

**Experimental status:** OFFLINE host-curated counterfactual, **NOT a second GPT-6 Luna video**. Stacked on [Draft PR #77](https://github.com/wterrr/vibecode_challenge_mb/pull/77), exact source HEAD cf6a813, no main merge. Preregistered FIRST in commit c45480d before any implementation.

## Diagnosis from genuine V3-42 / V3-43

V3-42's renderer splits each narration beat equally among primitive actions, rather than anchoring meaning-bearing events to speech. Genuine V3-43 audit [#38190765704](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38190765704) observed: both half partitions complete 5.52 s after narration starts; four quarter cells not complete until about 7.95 s into beat two; mathematical multiplication spoken but not shown; two depicted wholes have different areas, 4.68 versus 4.40. Merely accelerating the same primitive shows is not a reliable solution.

## Generic solution, reuse-first

New typed host-only compiler in learnflow_v3/semantic_visual_events.py:

1. Tile, Label, Partition, Relation, Event, TimedBeat, SemanticLesson: bounded independent contract. Validates IDs, visibility state, coordinate ranges, disjoint/equal-area tiles, actual source/target denominators, exact rational fraction equivalence, same-whole area, and symbolic proof labels.
2. Meaningful events: reveal_partition animates cells as one group; morph_partition actually uses Manim TransformFromCopy on source-to-target partition cells; show_label displays the formula; emphasize and hold explain and preserve state.
3. Relative-at and span event anchors within measured physical audio beat duration, with order and overlap validation. No word-timestamp fabrication.
4. V3-42 authentic scene and MP4 SHA verified before extracting ORIGINAL narration and claims; the new tiles/events are authored by host and never counted as a new model result.
5. Reuse original Manim Docker sandbox, espeak-ng WAV narration, FFmpeg native H.264/AAC mux and decoded frame/audio evidence gates.

A single example fixture is fraction-specific, but the compiler and event contracts are generic and accept other valid semantic partitions and ratio-preserving relations. The frozen V3-42 live schema and request path are unchanged.

## Predeclared acceptance

- Source and target both represent one equal-sized whole of area 4.32 square-units, correctly half shaded, with exact 1/2 = 2/4 fraction invariant.
- First whole and transformed quarters both fully present by <= 3 seconds after start of each respective narration beat.
- During beat 3, show the explicit relation (1×2)/(2×2) = 2/4 as visible graphics, not only verbal text.
- Docker Manim generates an actual native 1280×720 H264/AAC with real decoded frames and non-silent original-narration local audio, no still-frame facade.
- Corrupt files, unsupported math, unequal-whole/overlapping graphic tiles, dangling refs, event overlap and fake provenance fail closed.
- V3-36 real-model provenance gate **REJECTS** the new host-curated counterfactual; exactly zero additional GPT-6 Luna requests.

## Limits and future direction

Event anchors are beat-relative, not independently word-aligned to TTS phonemes. The counterfactual is HOST-created visual design with the model's originally authored speech, NOT proof GPT-6 Luna can design these transformations. Comparing it to V3-42 is a descriptive, unfair A/B, not a scientific causal efficacy or human preference estimate. It does not establish generalization to six domains, model creativity, educational outcomes, 3Blue1Brown aesthetic quality, or readiness for production. Offline quality gap inspection should precede any new request or model-authored event schema trials. Production BLOCKED. Detailed output evidence and exact-head CI must be checked independently.

## V3-44-FIX — deterministic audio–video mux (2026-10-12)

**Scope: only the native mux and its regression; no new model generation.** Original V3-44 HEAD `2007170`; failure [push #38192773382](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38192773382), frozen failed native [artifact #11722371868](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38192773382/artifacts/11722371868). Reproduced locally with ffprobe directly on artifact bytes: raw Manim H264 is 595 frames at 15 fps (39.666667 s); `-shortest` mux H264 contains only **588** frames (39.200000 s) while original `narration.wav` is **39.333333 s**, exactly **590** target frames. Broken output still contains AAC stream duration 39.333016 s; preserving audio stream metadata alone is NOT proof final video covers the spoken timeline.

**Fix:** `scripts/run_v3_44_semantic_counterfactual.py` now uses `deterministic_mux`: verifies input Manim H.264 1280x720/15fps has at least the audio-derived expected frame count, validates actual WAV PCM duration and sample format against the beat budget, uses explicit `-frames:v <expected>` and stream-copy H.264 + AAC encode **without `-shortest`**, and probes final output for exactly the required H.264 frames, AAC track and audio duration within one video frame. Original `_codec_and_pixel_gates` still executes; existing visual, physics/fraction, sandbox and provenance gates remain intact. The verified local mux on the FAILED artifact using `-frames:v 590` produced native H264 **590** frames, AAC **39.333016 s**, and video **39.333333 s**. Its local SHA256 was `5ae66641c43df510e753f52c95b90328a20dcae1bb6a1eddf8abc22ddac4c4da`; this is local reproducibility evidence **not** a claim about a future CI artifact SHA.

**Regression:** CI downloads BOTH immutable genuine V3-42 source (run #38189257163, SHA already frozen) and immutable failed HOST V3-44 artifact (run #38192773382). Negative/positive regression tests verify original 595/588/590 discrepancy, recovered 590 frames + AAC, fail closed for insufficient source frames and truncated PCM, guard against reintroducing `-shortest`, and guard provider secrets. No schema changes, no model HTTP POST, no GPT-6 Luna retry, no merge. **Final exact-head CI and its new MP4/receipt must pass before declaring V3-44-FIX complete.** The new video is HOST-curated counterfactual, not GPT-6 authored; no educational superiority claim.


## V3-44-FIX final empirical closure — verified on GitHub (2026-10-12)

**Acceptance: PASS — deterministic mux and actual native MP4; this is still HOST-CURATED output, NOT improved GPT-6 Luna model quality.** Exact code-and-test HEAD `fc9a5aad00fcf9ba6aea5c1e4c362db2821c4970` passed BOTH [push run #38194022963](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38194022963) and [PR run #38194026924](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38194026924), without failures. Offline regression report: **101 pytest tests PASS**, original V3-36 genuine model provenance **PASS**, native original-sourced/host-rendered `V3_44=OFFLINE_HOST_CURATED_NATIVE_MP4_PASS_NOT_NEW_GPT6_MODEL`, frozen V2/V3 benchmark scripts pass, no model HTTP request.

Exact [passing host-produced MP4 artifact #11723170139](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38194022963/artifacts/11723170139) was DOWNLOADED, EXTRACTED and independently checked. Final `v3_44_host_counterfactual_with_audio.mp4` file SHA256 **`13a99a980f758362564edfe1ce9bf466c62227732734cb43ae1b344dd4682b01`** matches BOTH on-disk hash and independently published receipt. Actual `ffprobe`: **H264 1280×720 15/1 FPS, exactly 590 frames, video duration 39.333333 s**; **AAC audio duration 39.333016 s**. `narration.wav` duration 39.333333 s. AAC–WAV duration difference **0.000317 s**, far below one frame; no early final-video stop. Raw Manim source output **595 frames** (video-only padding), trimmed deterministically to correct 590 via `-frames:v 590` (no `-shortest`). AAC per-beat RMS: **0.08463, 0.08281, 0.08733, 0.08832**; actual video decoded preview movement delta 4.248, valid model source read-only input and sandbox flags network=none, root read-only, host secrets not mounted, model Python not executed. Event count **14**, partition full-reveal delays 2.392/1.987 s, source and target whole areas equal; unchanged original narration from genuine V3-42.

**Receipt provenance:** `HOST_CURATED_SEMANTIC_VISUAL_COUNTERFACTUAL_REUSED_REAL_NARRATION_NOT_MODEL_AUTHORED`. The immutable V3-42 model video/source remain unchanged; model HTTP POST in V3-44-FIX = **0**. Corrected output is a host-authored counterfactual, not a new model-authored video and not educational quality PASS. All previously identified quality/generalization/human-learning limitations remain, production **BLOCKED**, Draft PR #78, do not merge main.

The documentation close-out commit does not change code or gates; exact-head CI on that documentation-only commit must be inspected before declaring the GitHub PR's latest HEAD PASS.
