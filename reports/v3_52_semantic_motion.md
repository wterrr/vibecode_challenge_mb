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


### V3-52 — Exact implementation HEAD native evidence closeout (2026-10-12)

**Implementation HEAD:** `65dffa2644d4efb948851a2e8990135788ba3fd0`. [Push Actions #38221255411](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38221255411) **SUCCESS** and [PR Actions #38221260000](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38221260000) **SUCCESS**, each **225 pytest PASS**, frozen 12-topic/6-domain V3 prereg, LearnFlowBench and V2 Core safety PASS. Push artifact [#11735005847](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38221255411/artifacts/11735005847) downloaded; both actual H264 1280x720 15fps and AAC verified via independent ffprobe and physical MP4 SHA256. Development Q=[1,0] **830 frames**, SHA `bea73a5b87de1b2ad6ec3cad9e0d7f76a45210fdd4ba1d86d91e74b094b71288`; counterfactual Q=[0,1] **833 frames**, SHA `90778f3560cdffecc8fe5ed665046082cfe8a2243f29946edb7c30a63fbddb10`. Original Q factor softmax weights [0.66976155,0.33023845], reversed [0.33023845,0.66976155]; host-computed context matches in both. Real decoded ROI at end of NORMALIZE has **zero** contribution-color pixels for both; after weighted value-transport the output context region has **10,764 teal / 5,400 amber** (fraction **0.665924**) vs **5,292 teal / 10,944 amber** (fraction **0.325942**), matching direction and approximate magnitude from host weights. Both audio budgets exactly equal H264 frame counts.

Visual QA: V3-52 first render revealed score text over softmax bars and contribution text over weights; fixed in code; independent inspection of **final** contact sheets confirms labels clean at stable normalized and composed frames, and visible transform of source V identifiers into weighted contributions prior to bar-to-context geometry. A brief transient duplicated Value label during TransformFromCopy remains observable at sampled mid-transition, so do NOT claim pixel-perfect typography or professional creative polish. Motion is stronger than V3-51 reveal-only diagrams but still domain-specific host-owned, visually sparse and untested with users.

**Scientific verdict: BOUNDED ATTENTION SEMANTIC-MOTION TECHNICAL OFFLINE PASS / HUMAN QUALITY UNRATED / MODEL CREATIVE AUTHORING UNTESTED.** No new model post, no V3-50 retry, no genuine provider authored output, no six-domain generalization, production BLOCKED, `main` unchanged, PR Draft. This is a documentation-only evidence commit; its own docs-HEAD CI must be checked separately before any exact-HEAD closeout.
