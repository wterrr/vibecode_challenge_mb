# V3-34 — Model-Directed Generative Scene Authoring & Small Controlled Ablation

**Scope:** Child stacked from V3-33 Draft PR #67, no merge main. Exact frozen V3-33 development topic `lfb-018-math`, fractions and ratios. A separate pre-implementation commit `1262ca7cce80f655d74bda7c4b0b5bc19fe01e78` locks the topic SHA, one paid provider request cap, the ablation arms and pass policies: `benchmarks/learnflowbench/v3/v3_34_scene_ablation_preregister.json`.

## Decision tested

**Hypothesis:** the rigid host-authored semantic steps and topic-specific renderer library inhibit creative cross-topic visual planning. Compare the available original template pathway and a model-directed visual plan compiled into a more expressive Manim primitive engine. This is a **small diagnostic experiment**, not a statistically balanced three-way comparison: A and B may legitimately ABSTAIN without videos. The model can decide object types, number, location, colors, narration, reveal order and moves; the host does not pre-design a fractions-specific scene or hard-code the LLM outputs.

| Arm | Planner | Available renderer | Expected interpretation |
|---|---|---|---|
| A: existing V3-33 | Existing exact-source-bound typed planner | Existing math FunctionGraph family | ABSTAIN on never-before-certified fractions/ratios. Not a failure of the model |
| B: creative model plan → OLD renderer | Same exact live model-authored scene as C | Existing source-certified linear FunctionGraph renderer only | ABSTAIN if scene cannot be expressed; diagnose existing renderer expressiveness |
| C: creative model plan → NEW finite Manim DSL compiler | Same exact live model-authored scene as B | Trusted host emits Manim from data-only graphic objects/actions; sandboxed native renderer | A real complete model-directed novel MP4, if model JSON, semantics and safe execution pass |

This does **not** give the model arbitrary executable Python, unlike full Code2Video. The initial trial tests whether relaxing scene composition alone helps output coverage and visual variety; it cannot establish that model-written arbitrary Python or Manim end-to-end is safe/beneficial. A model-directed DSL is still a safety-constrained generative system.

## Source and factual invariants

Topic was selected before implementation from V3-33 locked six-domain unseen topics. Facts are exact bounded arithmetic: `Fraction(1,2) == Fraction(2,4)`, numerator/denominator can be scaled jointly without altering value, and two of four equal partitions represent half. Graphic/narration number tokens and claim references are validated; unsupported quantitative claims, extra executable fields, references to nonexistent objects, actions before reveal, unapproved colors and missing fact IDs fail closed. This is **NOT an independent OpenStax/source-publisher citation certificate**. Wider factual and scientific claims remain ineligible; pilot/production source quality gates intentionally remain BLOCKED. No synthetic source provenance or 3Blue1Brown parity is claimed.

## Authoring and render chain

`CreativeScene` schema permits text, rectangles, circles, dots, independently positioned on a black 720p canvas, and four ordered beat scenes with show/move/emphasize/remove/wait actions. No topic-specific storyboard is compiled for the real model; the fixture is distinctly tagged HOST SYNTHETIC, used only for the zero-paid sandbox smoke test. Prompt gives concepts and factual constraints but no predetermined visual sequence. The model is asked for a single JSON storyboard, exact `openai/gpt-6-luna`, max **one** request, temperature 0.7, no provider fallback/retries. Capture model-response SHA and provider usage; on schema failure fail closed with explicit one-request-attempt possible cost rather than asserting free.

Trusted compiler renders to Manim Community v0.19.0; model JSON is never passed to `exec/eval/import`. Docker is isolated: **network none, read-only root filesystem, cap-drop ALL, no-new-privileges, user UID/GID, CPU/memory/PID limits, tmpfs, source read-only and restricted output volume, no GitHub/LLM secrets mounted**. The renderer image/tag and actual digest are recorded. No unsafe local (non-container) fallback.

Reuse old V3-30 physically measured eSpeak WAV audio, concatenated into four measured beats with trailing pad. Scene animation durations budgeted to speech lengths; final host muxes H264+AAC, writes SRT at physical beat boundaries and samples decoded MP4 frames and AAC RMS. This guarantees segment-level time budgets only, not forced aligned word onset. Negative tests require valid real typed graph actions and reject shell/Python escape and factual substitution. Feedback is currently local pixel/codec/claim checks, **NOT** VLM criticism or learned repair.

## Acceptance and scientific limits

- **Offline FIRST:** all negative tests, old V3-33/V3-32 regressions and frozen benchmark/Core PASS; synthetic HOST fixture renders real Manim-in-isolated-Docker H264/AAC + decoded frame pixel change + audible AAC. This is NOT creative-model evidence.
- **One live opt-in trial:** only if offline pass. Model must create valid previously unseen composition; no retries. C must produce a real novel MP4 whose source ID, hashes and frames originate from that one model response, or report BLOCKED; A and B remain their predeclared honest renderability statuses.
- A/B have no comparable actual videos, so cannot compute image-quality delta or claim causally that C is prettier. Human educational quality, model VLM feedback, external semantic review, licensing of voice/graphics and production remain BLOCKED.
- **Any grade:** `technical` is separate from `educational`. Quantitative aesthetic score remains null without blinded comparisons; visual inspection can yield timestamped issues but not a blinded teaching score.
- No auto paid run on regular pushes/PRs. Only a unique opt-in commit tag `[v3-34-one-shot]` or workflow dispatch from this exact branch; only after no-paid CI success.

## Receipts

- `v3_34_ablation_receipt.json`: provenance, A/B/C statuses, real provider attempt, safety profile and media verification.
- `scene_plan.json`: model-authored creative DATA; `generated_host_compiled_manim.py`: audited HOST-compiled executable source.
- `creative_manim_with_audio.mp4`, SRT, `creative_manim_decoded_contact.jpg`, measured WAV audio and V3-34 failure receipt if blocked.

**Before exact CI/live execution:** implementation complete, empirical outcome PENDING. Preserve Draft and production BLOCKED; do not misrepresent the fixture as model artistry.
