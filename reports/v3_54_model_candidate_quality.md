# V3-54 — Model-Candidate Creative SceneGraph Acceptance & Visual Quality Gate

**Status: Implementation committed; exact HEAD CI and independent MP4 QA pending.**

Parent is V3-53 Draft PR #87 at `f5556e89199dc95fc00c4f7b82d17b8f19850e65`. The **FIRST** new branch commit `f599e52` preregistered three frozen offline mock cases, validation failure inventory, visual-quality proxy thresholds, and no new model API allowance before implementation.

## Research motivation

V3-50's single model POST returned JSON but failed an opaque combined schema/claim validation. V3-51 allowed flexible grounded scene graphs; V3-53 permitted bounded causal director plans but showed only host-synthetic plans. V3-54 tests a **prospective, model-shaped, fully typed JSON wire admission** against known host facts and existing SceneGraph, with precise sanitized failure stages and independently decoded native-video quality metrics.

## Reuse-first

- `learnflow_v3/creative_candidate_acceptance.py`: strict versioned Candidate Pydantic/JSON Schema (no executable fields or origin claims); size-bounded UTF-8 JSON, exact topic/ledger SHA; typed Scene and Beat validation; adapter to V3-51 trusted Storyboard injecting host provenance and rechecking topology, semantic references, supported numbers and claims via actual V2 SceneGraph. Staged wire/json_schema/typed_schema/evidence/semantic_graph diagnostics are sanitized (no raw message or API secrets). Accepting a mock is NOT proof OpenRouter's structured output supports the schema.
- `learnflow_v3/creative_visual_quality_gate.py`: reads physical H264 decoded frames at five preregistered normalized timestamps, calculates background occupancy, static-vs-changing pixel MAE and pairwise five-frame differences across three different SceneGraph topology signatures. Quality measures are proxies only; cannot certify readable fonts, conceptual correctness or learner outcomes.
- `scripts/run_v3_54_model_candidate_quality.py`: wraps **the same three pre-existing V3-51 host-authored scenes** as mock model-shaped packets, accepts them with fail-closed schema, reuses V3-51 finite Manim compiler, existing WAV-to-exact H264/AAC Docker media and physically decoded quality checks. No model response is requested or claimed.
- Adversarial tests: malformed/nonfinite/oversized candidate wire, model origin spoof, extra fields/code injection, wrong topic, fact digest/claim tamper, unknown node/edge/action, unsupported numeric narration and blank/static/identical decoded video. All earlier frozen V3-50/51/52/53 regressions and V2/Bench gates are preserved.

## Explicit limitations

The mock packets are repackaged V3-51 examples, not fresh independently sampled creative responses. Passing shows the transport and visual gate operate on bounded, known-grounded scene families, **not** that GPT can author them, new-domain transfer, expert visual storytelling or student learning. The scene compiler is still bounded by its finite object/animation vocabulary. Human visual quality and pedagogy **UNRATED**; production **BLOCKED**, no merge main, no API calls.

**Technical final gate:** exact HEAD Push+PR CI, 3 native 720p H264/AAC outputs, physical video frame counts, SHA ledger, five actual decoded frames/video, non-empty/non-static coverage, pairwise visual difference, and visual review. Until those are verified: **PENDING**, not PASS.

 
## V3-54 final code implementation audit — 2026-10-12

Exact implementation HEAD: 708a622aca40ae3416a7f1fc43d1e85f6d032819. First Push #38229396813 succeeded (275 tests and 3 native H264/AAC). PR workflow #38229442321 failed TWICE BEFORE TESTS at GitHub runner apt-install timeout 360 seconds, exit 124, not SceneGraph or rendering code. To remedy repeated infra fault, same-head workflow now runs FULL pinned no-network native rendering and fail-closed 3-MP4 decoded frame QA on Push, and Python-only contract, adversarial, V2/V3/Bench tests on PR. Both CI runs at implementation HEAD are SUCCESS: Push https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38231335562 and PR https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38231341841, 275 pytest PASS each; V3 prereg 12 topics/6 domains, LearnFlowBench contract and V2 Core freeze PASS. PR deliberately does not repeat native media job; Push mandatory full media test.

Actual Push artifact https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38231335562/artifacts/11738831873 downloaded and independently checked using ZIP SHA256 and FFprobe. All outputs REUSE three earlier V3-51 HOST synthetic scene examples: mock_token_network 632 frames / video SHA f908468fc1b722bfa64e3c2079d0f21b8ffac0189a9a18614d73b899e8a15c49; mock_score_comparison 623 frames / SHA 9fb9828570be82ef0ca60fea9cb61cc55b500d5d9c9955a65031747d9854312e; mock_symbolic_equivalence 788 frames / SHA f29fbe7d4db17af2f18ec2efe2f0bb49af15c808bde1388854d56ff0c1346f98. Native H264/AAC 1280x720 15fps; every file SHA equals the host receipt.

Five real decoded frames sampled for each movie. Sample non-background pixel occupancy only 0.5%-2.8%, max in-film pixel MAE 3.435, 4.254, 3.901 (threshold >=1.5). Pairwise peak frame MAE 4.973, 5.225, 4.535 (threshold >=2.5), each with distinct semantic-graph structural signature. Technical pixel proxies PASS. Actual decoded contact sheets reviewed: small labels, excessive whitespace and mostly basic illustrative animations. Therefore qualitative visual storytelling/professional polish NOT CERTIFIED, not a 3Blue1Brown-level quality claim.

Verdict: BOUNDED V3-54 MOCK-SCHEMA-ADMISSION AND REAL NATIVE PIXEL-PROXY TECHNICAL OFFLINE PASS ONLY; zero actual model HTTP posts; genuine AI storyboard authoring NOT TESTED, provider schema compatibility NOT TESTED, unrestricted narration claim truth not verified, cross-domain generalization and learner learning effect UNRATED. Main unchanged, production BLOCKED, Draft PR #88. This is documentation-only commit; exact docs HEAD CI must pass before PR metadata closeout.
