# V3-52 — Semantic Motion & Visual Storytelling Quality

**State:** Implementation; exact-head CI and real MP4 independent audit pending. Parent Draft PR #85 SHA 7da60601998529208cbc19f8189c373f0244cec2; first child commit 2a7ee49 preregistered the design BEFORE implementation.

## Research question and scope

Does verified attention arithmetic directly drive *physical* animated value contributions and the resulting context, instead of a static chart or ornamental transition?

Two frozen Q counterfactuals with common 2-token QKV basis: development Q=[1,0], heldout reversed Q=[0,1]. Keys and values are basis vectors. Expected first softmax weight ~0.670 in development and ~0.330 in heldout. Output context equals the two weights because V are basis vectors. This is ONE topic family, selected host data, not independent domain or AI creative generalization.

## Reuse-first architecture

- Versioned strict MotionPlan and four semantic steps: dot_score_compare, softmax_weight_morph, value_weight_transport, context_compose. Each step is bound to its claim, beat, identity and exact host evidence SHA. Fake or reordered events fail closed. Real existing V2 SceneGraph validates object identity and relations, V3-51 remains unchanged.
- Native Manim 720p/15fps builds softmax bars and value-to-context segments from IDENTICAL host-calculated weights. TransformFromCopy carries both weight identities into the actual context strip with host numeric labels and physically muxed speech timeline. Uses existing audio, network-isolated Docker, CMU typography, exact-frame FFmpeg mux, and AV QA.
- Decoded H264 pixel gate compares the strip at end of NORMALIZE (absent: a negative control) against end of TRANSPORT (two present colored segments). Recomputed colored-area proportion must agree with weight and flip if Q flips. The measured ratio is not inferred from code or static file strings.
- Mutation tests include incorrect QKV, altered fact SHA, wrong claim/subject/beat, reordered motion, wrong area, premature context pixels, missing motion and bad timing. Frozen V2 Core, V3 benchmark, LearnFlowBench, and V3-49/50/51 regressions all remain.
- ZERO model/provider requests, no new model authoring success claim, V3-50 attempted one-shot remains consumed, no merge main, PR Draft.

## Limitations and gate

Success would certify only two HOST synthetic attention examples and physically causal pixel animation. NOT cross-domain expressivity, provider schema compatibility, learner comprehension, word-level alignment, or expert 3Blue1Brown artistry. Typography and motion must be inspected directly. **Final status pending exact HEAD CI and direct decoded actual MP4 audit.** Production BLOCKED.
