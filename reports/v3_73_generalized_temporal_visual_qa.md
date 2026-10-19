# V3-73 — Generalized Temporal Visual QA & Heldout Native Evidence

**Scope:** research-only transferable *declared geometry* gate, stacked child of [PR #108](https://github.com/wterrr/vibecode_challenge_mb/pull/108) at HEAD `149fb7eccdf860eb7ccf9b7b0cf04a493026c0f7`, first-child prereg commit `6da0c0781cd56ddfeae4cb9a723f0677bd092299` before any V3-73 implementation. Never merged `main`, edited V2 Core, production prompts, frozen experimental MP4s, reviewer protocols or original final viewer verdict.

## Reuse-first audit — actual technical gap

- V2 `learnflow_v2/layout/collision.py` provides mature deterministic **static** box-box positive-area overlap and semantic layout separation (not a timeline or native decoded-pixel contract). **Leave V2 untouched.**
- V2 `learnflow_v2/scenegraph/validation.py` protects concept identities and semantic keys for **static** graph nodes; it cannot know whether a moving dot entered a rendered node or text was occluded by a bar.
- V3-72 `learnflow_v3/v372_timeline_safe_renderer.py` checks 699 Attention/Process frame coordinates with actual font bounds, but hard-codes two cases' coordinates and movement axes. This bounded fix remains unchanged, and its geometry is reused through an explicit V3-73 adapter.
- Existing pipeline's renderer outputs do **not** universally export immutable complete per-frame geometry. Therefore the generalized gate is **opt-in for instrumented renderers**; it cannot claim to certify arbitrary finished MP4s by inspecting only source ledgers, bounding boxes that were not actually rendered, or a handful of decoded stills.

## New generic QA contract

`learnflow_v3/generalized_temporal_visual_qa.py` provides reusable typed immutable `Rect`, `Object`, `Edge`, `Frame`, `validate_frame`, `validate_timeline`, and `render_frame` functions. It uses the V3-72 overlap primitive and the V2 positive-area collision semantics without hard-coded topic IDs. It checks, per original frame index:

1. Complete, unique, finite, on-screen geometry; exact Pillow font-measured text bounds; min 14px text.
2. No text/bar, text/shape or node/marker unapproved overlap; **only** declared text-inside-own-node with >=6px padding is allowed. Arbitrary `parent_id` cannot disable collision validation.
3. Marker radius includes rendered stroke, must be associated with a concrete directed edge; it cannot penetrate the source or target node (+6px).
4. Consecutive timeline frames must preserve all semantic IDs/kinds/text/parent/edge topology, with no missing/reordered frames, no stationary-object jump, no moving marker teleport >24px/frame or reversed movement.
5. The native witness renderer consumes **exactly the same validated immutable Frame IR**, avoiding a separate unchecked image overlay path. This assures the diagnostic renderer's geometry declarations describe its own drawn boxes/text/circle, not arbitrary external videos.

## Preregistered held-outs and physical evidence

Three intentionally different subject domains with independent scene configurations and no topic branching in the validator: `h731_math_numberline` (Mathematics), `h732_biology_signal` (Biology) and `h733_computer_science_flow` (Computer Science), **45 frames each**, H264, 1280×720, 15fps. These are SILENT geometry/witness diagnostics, *not* narrated end-to-end pedagogical lessons and not a new 3B1B quality demonstration.

The adapter in `scripts/run_v3_73_generalized_visual_qa.py` independently rechecks only explicitly exported V3-72 score bar/label and Process edge/marker ROIs at all **355 + 344 = 699 original V3-72 native timepoints**. It does *not* claim all other V3-72 objects or pixels were generically certified.

The 3 heldout MP4s must be fully decoded from an actual GitHub Actions artifact, checked for exact 45+45+45 encoded frames, per-source SHA-256, and nontrivial decoded-frame temporal difference. CI-specific checks verify strict negative/mutation coverage plus decoded physical output. Evidence claims remain PENDING until GitHub runs successfully.

## Adversarial falsification

`tests/v3/test_v3_73_generalized_temporal_visual_qa.py` covers original Attention-type text/shape collision on an unrelated scene; circle intrusion at multiple intermediate timestamps; undeclared containment; glyph bbox lie; NaN/Inf/offscreen values; marker teleport/reversal; skipped/reordered frames; mid-timeline object-ID changes; stationary label jumps; orphan edge; unsupported objects; uncertain marker radius; and attempts to lower the 6px clearance. Any one must block publication of its diagnostic MP4.

## Scientific and deployment limits

**NOT a completed integration into production Visual Director, V2 Core, or arbitrary Manim-generated visual timelines.** Extending exporter instrumentation across actual creative SceneGraph/Manim renderers and matching rendered pixels will require a separately scoped checkpoint. Native H264 decoding proves only that these three silent examples physically exist and change over time; it does not prove a learner understands anything. **HUMAN QUALITY UNRATED, LEARNING GAIN NOT MEASURED, MODEL-AUTHORED CREATIVITY NOT TESTED, PRODUCT/RELEASE BLOCKED**. The user's historic final viewer `NOT PASS` is retained until an independent new-version review. Zero provider/model API calls, secret use, key mutation or main merges.
