# V3-59 — Causal Semantic Reveal Timing Repair & 3-Arm Native Review

**Checkpoint scope:** research-only host-authored semantic reveal; technical native/render validation is **PENDING exact-head CI**; external pedagogical quality **UNRATED/NO-GO**; genuine LLM creativity **NOT TESTED**; student learning **NOT MEASURED**; production **BLOCKED**.

## Lineage and preregistration

Draft child of [V3-58 PR #92](https://github.com/wterrr/vibecode_challenge_mb/pull/92) at frozen HEAD `d9d8830c0486a0c25b0ca924a091084b267425fe`, not `main`. First child commit `148f1b73cdedce9ed1b1e4af6a9d5251d33903c4` records preregistration BEFORE implementation in `benchmarks/learnflowbench/v3/v3_59_causal_reveal_preregister.json`. No model API, production prompt, V2 Core, external film copied or model-authored executable Python.

## Independent defect inventory from V3-58

1. **Fraction:** Original V3-57 `SUBDIVIDE` drew six cells and the `4/6` answer before the amber subdivision guides finished, so movement followed the already-known answer.
2. **Process:** Original `STATE_TRANSITION` colored ACTION green before its tracking marker traveled from START to ACTION.
3. **Attention:** Original `SOFTMAX_NORMALIZATION` exposed normalized `w(A)` and `w(B)` before the normalization bar had visibly completed. Original mathematical scores were genuine host-ledger values, but the revealing order was misleading.

These defects are SOURCE/FRAME observations from V3-58, not evidence about measured student confusion.

## Repair contract (finite, host-only)

`learnflow_v3/causal_reveal.py` wraps, but does **not modify**, frozen V3-57 `render_image`. The original V3-57 motion source and V3-58 static source remain reproducible as unchanged treatments.

- **Fraction:** preserve 3 equal original parts (2 shaded), progressively draw three child-guides, *then* display six equal child partitions (4 shaded) with `4/6`; `2/3 = 4/6` and original shaded area are invariant.
- **Process:** ACTION stays inactive for all unfinished transition progress, activates only at marker arrival. CHECK condition always `UNKNOWN_NOT_VERIFIED`, success claim always false.
- **Attention:** keep numeric normalized weights hidden while the normalization witness grows. Reveal source-ledger weights and `exp(score)/sum(exp(scores))` only after it finishes; certified sum of weights equals one.
- All other visual beats reuse the exact V3-57 Pillow renderer. There is no arbitrary free-form generated scene, no native speech word alignment claim, and no attempt to reconstruct 3Blue1Brown copyrighted material.

The thresholds (fraction subdivision reveal 0.79, completed attention/transition at 1.0) are HOST-CHOSEN DESIGN DECISIONS, not measured human learning or speech/word timestamps. The unchanged narration still uses synthetic beat-timed eSpeak.

## Preregistered falsification and physical media audit

Tests `tests/v3/test_v3_59_causal_reveal.py` inspect original-to-revised region pixels and reject early results, false activation, fabricated plan/evidence SHA/origin, bad progress, unregistered topics, and false process success. Negative mutations explicitly set each reveal threshold to 0 and must fail host semantic gates.

`scripts/run_v3_59_causal_reveal.py` consumes physically produced V3-57 and V3-58 outputs; renders **3 new native 1280×720 15fps H264/AAC repaired clips** by constructing the corrected frames, encoding the video stream and **copying original AAC packets**. It checks original/final physical decoded frame counts, original+revised AAC elementary bitstream hashes, video metadata, nine decoded frame witnesses at three progress checkpoints for each topic, and original V3-57 one-extra-frame receipt discrepancy. The original receipt remains unmodified.

Independent review packet preregisters **three masked-condition treatments × three topic families = nine MP4s**: frozen V3-57 motion, frozen V3-58 end-state static, and new semantic-causal revision. Same topic/host mathematics/narration/audio packet identity/encoded frame count within each triple; treatment order is deterministically masked and the **admin key stays outside reviewer packet**. Reviewers can perceive that some visuals move, so it is NOT double-blind. Three independent raters are targeted; **zero have been collected**. Pixel evidence cannot substitute for ratings or learning outcomes.

Workflow: `.github/workflows/v3-59-causal-reveal.yml` first runs offline adversarial tests and frozen V2/bench guards, then reconstructs 3+3+3 native clips on push, uploads nine-clip masked review archive separately from admin receipt/key. No pre-existing V3-58 human responses are assumed.

## Decision ledger (as written before CI execution)

| Gate | Status |
|---|---|
| Preregister frozen parent + safety scope | DONE (first child commit `148f1b7`) |
| Implement typed host timing + fail-closed negative gates | CODE COMMITTED; CI NOT YET VERIFIED |
| Native reproduced nine-clip paired packets | **PENDING** GitHub Actions; do not infer from source code |
| Source original 1-frame receipt discrepancy | KNOWN FROM V3-58, must remain separately recorded |
| Three external independent reviewers | 0; NO-GO / UNRATED |
| Student learning effect | NOT MEASURED |
| Native original 3B1B speech grounding | 0/12 native phrases verified, unchanged |
| True model-authored freeform creative pedagogy | NOT TESTED |
| V2 Core and production prompts | UNCHANGED |
| Production | BLOCKED |

**Next decision after exact-head evidence:** inspect CI jobs AND actually decoded MP4 frames/semantics before local-tech PASS; external raters independently judge 9 masked clips and provide timestamps. Even positive reviewer scores do not demonstrate causal improvement in student learning without an actual randomized learner-outcome study.

## Post-implementation QA hardening (pending GitHub CI)

A direct source-level check found that the original Process moving marker ended at x≈610, y=426, below and short of ACTION center (640,337), so merely making ACTION green at the end was not a physically grounded arrival. In the V3-59 opt-in renderer the old off-graph marker is overwritten, a newly anchored marker travels from START's output at (370,337) to the actual ACTION center (640,337), and ACTION activates only on host-verified center arrival at progress 1.0. Regression tests assert exact destination coordinates, action state and decoded-rendered color witness. The unchanged V3-57 baseline still exhibits the original defect by design.

Direct-native QA additionally checks three **semantic ROIs** in decoded output, rejecting a movie frame that looks closer to the opposite (pre/post) semantic state or cannot be distinguished from that state even if a global full-frame MAE is small. Separate tests freeze nonzero pre/post regional differences for all 3 cases. These are fail-closed *implementation assertions*, still awaiting exact-head CI and physical movie receipts. Visual closeness and region separation still do NOT prove viewers understood the lesson.
