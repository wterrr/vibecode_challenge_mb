# V3-41 — Provider-Compatible Structured Outputs & Genuine Video Recovery

**Checkpoint status: OFFLINE IMPLEMENTATION; EXACT-HEAD CI PENDING.**
Stacked Draft branch from V3-40 PR #74 at 491e637. Preregistered at commit eee591e BEFORE implementation. Do NOT merge main. **Current authorization: zero GPT-6 Luna POST and zero authenticated provider GET.**

## Why V3-40 PASS was not enough

V3-39's only GPT-6 Luna completion (Actions #38022202376; content SHA ca4b439ee25a6db305ceccf52532544678b015aff2668a3bbb2f155b6e3f9d0e) failed because two object heights exceeded 2.4 and the first beat had zero factual claim IDs. Host Pydantic correctly stopped execution; wire schema lacked those enforceable boundaries. V3-40 projected minimum/maximum/minItems from Pydantic; this works locally but does NOT prove OpenRouter's target endpoint honors all constraints.

Authoritative context checked 2026-10-10:
- https://openrouter.ai/docs/guides/features/structured-outputs — Structured Outputs support and strict enforcement vary by provider.
- https://developers.openai.com/api/docs/guides/structured-outputs — enums/required fields supported; some type-specific constraints restricted at different endpoints; total enum limit 1,000.

## V3-41 protocol: purely structural and enum-constrained

- Separate portable wire schema. Only object/array/string/number, required object properties, additionalProperties=false, enum, description. No bounds, minItems, regex, conditional logic or arbitrary fields sent as JSON schema.
- Geometry: generate finite numeric enum values FROM current V3-40 Pydantic-derived host bounds and defaults. Graphic positions grid 0.1, dimensions grid 0.05; move coords grid 0.2. Host min/max included exactly. This restricts continuous positions, so creative impact remains to evaluate.
- Claim slots: each beat has mandatory claim_primary=F1/F2/F3 plus required claim_secondary/tertiary=F1/F2/F3/empty. Model must explicitly author a nonempty first claim. Convert ONLY its nonempty selected slots into claim_ids; no fabricated facts.
- Four beats: beat_1..beat_4 mandatory keyed objects, which enforce four authored beats without minItems.
- Host unchanged: local JSON schema check, existing normalize_wire action placeholder checking, then same CreativeScene Pydantic validation and certified host-only arithmetic, temporal and object rules. No clipping, repair or invented claims.
- Provider request PREVIEW only: max_tokens 6500, no temperature, strict JSON Schema, provider require_parameters true, allow_fallbacks false. Never sent in V3-41. Historical strict_wire_schema and one_shot_structured remain unchanged.
- Offline native media: new mode offline-v341-compatible transforms a clearly host SYNTHETIC wire fixture through the REAL Pydantic → Manim compiler → no-network Docker → H264/AAC → decoded frame/audio gates, then requires V3-36 evidence gate to reject it as NOT_REAL_MODEL_SCENE. A synthetic MP4 never proves model-generated creativity.

## Acceptance and limitations

Dedicated no-secret CI tests mandatory claim nonemptiness, both V3-39 height failures, fixed four-beat structure, geometry outliers, malicious fields, exact host validator, positive fixture and null/mutation tests. Existing V3-34..40 regressions, frozen V3-33 and V2 Core must remain passing. Enum-value count capped at 1,000, schema depth at 10. Synthetic artifacts are strictly labeled NOT-MODEL. Inference POSTs: **0**.

Run offline:
    python -m pip install -r requirements.txt pyyaml
    python -m pytest -q --confcutdir=tests/v3 tests/v3/test_v3_41_compatible_scene_protocol.py
    python scripts/run_v3_41_offline_compatibility.py --output-dir /tmp/v341_compatible_synthetic

Exact-HEAD CI outcome pending. Support of this schema by any particular live OpenRouter GPT-6 Luna endpoint remains NOT VERIFIED. No actual model MP4 has been created; quality and production remain BLOCKED. A new real POST still requires separately preregistered, explicitly approved authorization and cannot replay V3-39.


## Offline implementation CI evidence (2026-10-10)

Verified implementation run [#38025328017](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38025328017) **SUCCESS**: 155/155 V3-34..41 parity, boundary/adversarial and legacy tests passed; frozen V3-32/33 **27 passed, 1 skipped**, exact V2 Core/bench protocols PASS; actual no-network Docker Manim H264/AAC synthetic fixture decoded and **mandatory NOT_REAL_MODEL_SCENE** rejection PASS; strictly labeled [host-only artifact #11659293157](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38025328017/artifacts/11659293157). **Zero model POSTs and zero authenticated GETs**. Later mock-envelope tests extend coverage; exact current HEAD CI must be verified separately.

The subsequent synthetic-provider-envelope regression commit only uses a Python callback (not a transport), explicitly records mock origins and tests truncation/multiple choices/invalid JSON/empty claims. New exact-head CI outcome pending. Genuine GPT-6 Luna authored MP4 **not obtained**; production BLOCKED.
