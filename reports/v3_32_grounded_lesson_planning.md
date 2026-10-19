
# V3-32 — Grounded Lesson Planning & Narration–Visual Synchronization

**Scope/branch:** child stacked on PR #65 (V3-31); not merged into main. Frozen V3-16 unaffected. Zero new paid GPT-6 Luna calls.

## Upstream artifact inspection
Actual V3-31 GitHub run [#37899219231](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37899219231), artifact #11600904144, 1280x720 H264/AAC 18 fps 441 frames/24.5s, original MP4 SHA 09354fe9d11a336da204a234d8bb12dde64d051ac55bbaf44ce77a72dee9dff1. The 2×2 contact sheet shows a correct code panel/state map yet lacks a separate Evaluate beat, narrated plus-two calculation, and visible movement of argument/return along a causal path. Research model authored in V3-30 used doubling and inconsistent numbers; V3-31 repaired explanations manually. V3-32 does not reuse those repaired explanations as LLM output.

## Method
- `WorkedExample` restricted source AST verifies a single `def name(parameter): return parameter [+|-] k` and `dest = name(argument)`. Safe finite integers and no compile, exec, eval, imports or arbitrary generated Python.
- `LessonSemanticContract` enforces exact publisher SourceClaims, identifiers O1/O2/O3, claim IDs, five typed semantic events/visual states, worked arithmetic and narration under one contract. Reused V3-07 `verify_code_walkthrough` proves the derived numeric assignment state, with source prose provenance separate from arithmetic proof.
- Existing V3-30 GPT-6 Research explanations that deviate from the worked example are **rejected, not silently repaired**; audit records original text hashes. New research/script text is compiled **deterministically by the HOST from the same safe AST/claim contract**, explicitly not GPT-6 and not a provider retry. This avoids human copy-editing for the offline demo, but is **not evidence that autonomous Research self-corrects**. A future LLM proposal must pass the same contract or ABSTAIN; no automatic paid retries.
- Five animated causal events: Define, Call, Bind, Evaluate, Return. Moving value marker and segment state keys depict argument→parameter→expression→return→destination, not a series of static cards. Native black, CMU Serif and CMU Typewriter, code readouts and physically measured SRT/AV segments.
- Event time is derived from **measured physical WAV beat** plus a preregistered beat fraction; not inferred by fabricated phoneme/word alignment. Explicit geometry/pixel deltas, decoded source-frame reproduction, audible AAC RMS, ffprobe H264/AAC frame count and anti-static intra-beat motion gate.

## Strict offline acceptance
- At least two distinct AST parameter/function examples (plus and minus) pass generic binding; malicious AST and numeric mutations fail.
- Model-source drift, wrong source hash, forged transcript, claim/beat/visual-state swaps, timeline and word-time mismatches fail.
- Actual media evidence: 5 beat H264/AAC MP4 1280×720, SRT, decoded contact, 5 audibly non-silent sampled segments, event timing and ROI motion metrics; regression V3-31/30/07 and untouched Core/BENCH.
- **Scientific status before run:** PENDING. Separate code/AV PASS from actual beginner comprehension and artistic impact. No independent factual semantic audit, word-level timing, human teaching-quality rating, six-domain generalization or audio rights clearance. Production NO-GO.

## Evidence
Exact-head CI and downloaded decoded video artifact to be appended after execution.

## Observed offline evidence and visual review — 2026-10-09

- Native five-stage bounded offline pipeline [GitHub Actions #37901558522](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37901558522), commit `de86f5c`, **SUCCESS** after fixing original V3-32 mutability test and a causal animation overprint. Original contract/mutation and frozen guard CI also passed on predecessor #37900739095 (15 new and 45 prior tests, all PASS).
- Downloaded actual artifact #11602408711 with final-segment timestamp gating: real MP4 SHA256 `37eb049461786a47f50dfdc158a8253db9fc173c5a86e1252a7a92dc30205225`, codec H264/AAC 1280×720 18fps, 674 frames, 37.444s, five physical eSpeak WAV-backed spoken segments and SRT (not word-level timestamps). AAC per-beat RMS `[0.08015,0.09265,0.08603,0.0826,0.08674]`, five source replay checks decoded MAE all below 1.0, state ROI deltas `[3.225,6.435,6.551,3.102]`, intra-beat pixel motion >0.2. **Decoded pre/post event-value reveal** for Call/Bind/Evaluate/Return gives exact recorded ROI deltas `29.226,28.702,30.925,30.178`; no zero-motion pass.
- Contact sheet manually reviewed: code function definition, call, bound parameter and return expression legible on black CMU; the revised route runs through inter-panel gutter, not diagonally over Python text or labels. Five-stage narration now verbally explains `3 plus 2 equals 5` with a distinct Evaluate section, improving upon the V3-31 omission.
- Manual contact review found another actual QA issue: sampling the midpoint of the Return beat precedes its scheduled reveal (fraction 0.55). The final change samples each source-replay frame at 78% of the physically measured beat, **after** the semantic event. The exact newest SHA must rerun full CI, decode the actual new artifact and receive a fresh visual inspection before claiming a final-head PASS. Do not re-label stale prior frames as final.
- Scientific verdict remains **engineering bounded GO only; quality/production NO-GO**: a deterministic host compiler abstains on the actual GPT-6 conflicting Research and creates a new source-bound lesson; it does **not** demonstrate autonomous model conflict repair, independent teaching competence, general arbitrary-code support, six-domain performance or rights clearance.
