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
