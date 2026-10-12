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
