# V3-35 — Schema-Constrained Creative Scene Authoring, One-Shot Recovery

**Scope:** Child stacked from [V3-34 PR #68](https://github.com/wterrr/vibecode_challenge_mb/pull/68); do not merge main. **New independent preregistration** commit `238de90a6e42b009f7ad086b9998ef30cdbcc0cb` predates implementation and locks topic `lfb-018-math` (Fractions and ratios; original V3-33 held-out topic, query SHA 376a0604...). The earlier V3-34 GPT-6 Luna one-shot was **consumed and failed at Pydantic schema validation** (run #37907978564). This is NOT a retry of that original preregistered one-shot: it is a distinct, explicitly requested bounded experiment.

## Root cause assessment, with epistemic limits

At V3-34 the model-origin response apparently reached `CreativeScene.model_validate` and raised `ValidationError`; the original runner saved only a generic sanitized failure, discarding input and `ValidationError.errors()`. **The precise field(s), missing/extra keys or numerically incoherent objects cannot be reconstructed.** Don't invent a root cause or blame the model's creativity. The testable integration hypothesis for V3-35 is **protocol/schema nonalignment**, not lack of model visual competence.

Up-to-date official OpenRouter structured output documentation: https://openrouter.ai/docs/guides/features/structured-outputs; JSON Schema support depends on provider endpoint. V3-35 sends `response_format={"type":"json_schema","json_schema":{"name":...,"strict":true,"schema":...}}` and `provider={"require_parameters":true,"allow_fallbacks":false}`. If exact model provider cannot honor schema, **BLOCK** without silent endpoint substitution or non-structured fallback.

## What changes, reuse-first

- A **simple all-required JSON Schema** (objects, actions, beats) with `additionalProperties:false` at every object level. Avoid conditional/optional schema features that some endpoints do not support. Four beats, allowed facts, shapes, coordinates and actions are verified again after response.
- Wire transport normalizer ONLY removes dummy action coordinates/empty target required by portable strict JSON Schema. It never repairs unsupported math, missing factual claim ID, unknown targets, unsafe object fields or bad sequencing. Existing V3-34 `CreativeScene` and safe HOST Manim compiler perform semantic/identity/geometry validation.
- **Model retains creative decision rights:** layout positions, object geometry, palette, explanatory narration, reveal/movement ordering. Neither prompt nor source contains a live hard-coded model storyboard. The offline fixture remains labeled HOST synthetic, not model authored.
- A **single** paid `openai/gpt-6-luna` request after the same-commit offline tests and a full Manim H264/AAC sandbox render. No retry, fallback, unbounded model-produced code, or external network inside Docker. No secret mounted into the renderer. Image `manimcommunity/manim:v0.19.0`, same sandbox as V3-34, with actual image ID captured.
- Both first-class request-attempt receipt and **non-sensitive schema-error shape** receipt: `validation_error_shapes[{path,type}]`, `model_response_sha256`, `provider_reported_usage`; never record full raw model text, credentials, prompt secrets, or Pydantic leaked `input` payloads.
- Real gated MP4 (if any) must be native 1280×720 H264/AAC with frame count, nonblank/changed decoded scenes, audio RMS all 4 physical WAV beats, SRT and SHA evidence. A/B remain capability ABSTAIN; **this is not a fair 3-way completed-video quality comparison**.

## Preserved boundaries

- Local `fractions.Fraction` mathematically checks 1/2=2/4; no new independently certified textbook grounding or expert semantics. Number-token checks are necessary but insufficient for **all** prose factuality.
- Human educational scores null, no comparison to Code2Video visuals or 3Blue1Brown quality unless an independent blinded test actually occurs.
- Frozen V3-16, V3-33 selection and V2 Core unchanged.
- Production always **BLOCKED**, PR remains Draft, no main merge.

## Acceptance evidence

- Exact code SHA and unique tagged one-shot `[v3-35-one-shot]`, after current-HEAD offline CI green.
- A real response from exact GPT-6 Luna, with usage and provider ID hash. If model/endpoint cannot fulfill strict schema or Pydantic rejects, record **BLOCKED** without new retries.
- If validated, perform REAL sandboxed Manim MP4 and inspect decoded frames / quality issues with timestamps. Engineering GO != teaching-quality GO.

**Pre-run verdict:** PENDING exact CI and live. See later notes for verdict.
