# V3-67 — Corrected OpenRouter Wire & Provider-Enforced Budget Preflight

**Date:** 2026-10-14. **Base:** V3-66 Draft PR #102, frozen parent HEAD `b637e8783560aad02d9d3353f981fb22731fc9a8`. **First-child prereg:** `d909e585227967813bab5c2624350f711c13192a`, before implementation. Pure offline, no inference, no GET/POST, no OpenRouter management operations, no main merge, no V2 Core or production prompt changes.

## 1. Research question and reuse-first decisions

V3-64 attempted exactly one OpenRouter GPT-6 Luna POST, [run #38502942783](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38502942783), which ended in `HTTPError`. The original error HTTP code/body were never recorded. Later V3-65 catalog/current-key metadata confirmed current key authentication and model discovery, not historical success, funded account credit, or exact routing. V3-66 [PR #102](https://github.com/wterrr/vibecode_challenge_mb/pull/102) identified the original provider preference `allow_fallback` **singular** vs documented `allow_fallbacks` **plural**, and provided prospective safe HTTP failure code capture; these changes were **not applied to the archived one-shot**.

Current OpenRouter documentation used in the preflight:
- [OpenRouter Python SDK Chat request](https://openrouter.ai/docs/client-sdks/python/api-reference/chat) documents `provider.allow_fallbacks`.
- [OpenRouter Structured Outputs](https://openrouter.ai/docs/guides/features/structured-outputs) documents `response_format.json_schema` and `provider.require_parameters`.
- [Current API Key Metadata](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-key) lists `limit`, `limit_remaining`, `limit_reset`, `include_byok_in_limit` and inference vs management key.
- [API Key Update](https://openrouter.ai/docs/api/api-reference/api-keys/update-keys) describes per-key USD limit and no-reset `limit_reset:null` semantics; setting a cap via management key was **not** attempted.
- [OpenRouter Guardrails](https://openrouter.ai/docs/guides/features/guardrails/overview) documents provider-enforced budget limits and disallowing requests when exceeded; no guardrail was created or audited here.

**Critical distinction:** A local max-output-token or estimated price calculation is **not** a hard USD limit. A provider-configured limit on a **dedicated inference key** is required as the external enforcing control, and a future authenticated GET must independently verify it. Key `limit_remaining>0` alone (all V3-65 established) does **not** prove a <=$0.02 lifetime limit. Key-specific limit and remaining cap do not prove funded account credits, routing eligibility, real current pricing or a model response.

## 2. Preregistered rules and implementation

Prereg `benchmarks/learnflowbench/v3/v3_67_corrected_provider_budget_preregister.json` freezes exactly **$0.02 lifetime per-key provider-side cap** from the earlier V3-64 research budget; no extension or new paid call is authorized.

`learnflow_v3/v367_corrected_wire_budget.py`:
- Reads the original frozen `request_payload()` byte-for-byte from V3-64, checks SHA256 `728e32b0bea658a82054184efee840ddb72957851f0ba87d21042d96d4134c0f`, and refuses source drift.
- Constructs a **new prospective request** differing only in `provider.allow_fallback -> provider.allow_fallbacks`, with `False` unchanged. Preserves model `openai/gpt-6-luna`, `order=["OpenAI"]`, `require_parameters=true`, strict JSON schema, unchanged prompts, `max_tokens=2100`, no temperature, no model fallback. Corrected byte-stream SHA256 is `84e7d86f5ff101fb74358fa651b75e1afae2e2ee61ba35f7e56bc0e0fe9db463`; original wire is archived unchanged.
- Implements **deny-by-default** `policy_for_key`: absent authenticated provider metadata; invalid/missing numeric cap; cap greater than $0.02; non-lifetime reset; BYOK excluded; management key; zero remaining allowance; remaining exceeding cap -> DENY. Parses USD scalars with `Decimal`, rejects NaN/Inf/bools/negative/malformed values. Does not echo raw metadata, API key, secret label, workspace/creator identifiers or observed numerical balance.
- IMPORTANT: The `trusted_authenticated_get=True` parameter is **only a caller assertion**, not verifiable independently by this pure module. Its positive result is `KEY_CAP_CONDITIONS_SATISFIED_ONLY` for testing/hypothetical key data; it **always returns `live_post_permitted=false`, `is_genuine_provider_cap_proof=false` and `actual_charge_guaranteed_by_this_software=false`**. No actual provider enforcement was established; a future distinct authorization-gated client must attach trustworthy GET provenance, provider-side cap verification and account eligibility.
- `budget_preflight()` refuses to authorize any POST, even when injected test-only metadata is positive. `scripts/run_v3_67_budget_preflight.py` produces one prereg-checked safe JSON, no network.

## 3. Exact physical CI evidence

[GitHub Actions #38506669698](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38506669698) push HEAD `2d75f0375922c415a3deb3a9a5497720a55366f8` **SUCCESS, 44/44 offline Python tests PASS**, no skipped error gate. Tests cover unchanged original request SHA, exact provider field-only diff, strict JSON schema, >40 boundary conditions on mock key limit/remaining/reset/BYOK/type/provenance, malicious numeric values and unchanged original prompt, and no secrets or network.

Actual [GitHub artifact #11868395391](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38506669698), `v367-CORRECTED-WIRE-PROVIDER-DOLLAR-CAP-BLOCKED-OFFLINE`, independently downloaded and read from ZIP. One `V367_DENY_BY_DEFAULT_REQUEST_PREVIEW.json` (1474 bytes), with:
- Original request SHA: `728e32b0bea658a82054184efee840ddb72957851f0ba87d21042d96d4134c0f`.
- Prospective corrected request SHA: `84e7d86f5ff101fb74358fa651b75e1afae2e2ee61ba35f7e56bc0e0fe9db463`.
- `preflight_result=DENY_NO_AUTHENTICATED_KEY_SNAPSHOT`, `can_authorize_paid_POST=false`.
- `new_model_inference_posts=0`, `new_provider_gets=0`, `new_management_key_actions=0`, `production=BLOCKED`.
- `usd_budget_frozen="0.02"` and `token_ceiling_is_usd_hard_cap=false`.

## 4. Scientific conclusion and remaining blockers

| Claim | Status / why |
| --- | --- |
| Corrected documented provider field and preservation of V3-64 request | **PASS** in deterministic offline tests |
| USD cap gate rejects unknown or unsafe inference-key metadata | **PASS** in synthetic negative tests |
| Dedicated inference key with confirmed <=$0.02 lifetime server-enforced cap exists | **NOT ESTABLISHED** (no authenticated GET or provider config) |
| Actual provider billing/credit/routing/strict-JSON capability for new request | **NOT PROVEN** |
| Corrected request successfully receives a genuine model storyboard | **NOT TESTED, ZERO POSTS** |
| Historical V3-64 HTTPError caused by singular `allow_fallback` field | **UNDETERMINED** |
| Near-3B1B original visual-storytelling quality | **NOT DEMONSTRATED** |
| Independent human quality/learner effect | **UNRATED / NOT MEASURED** |
| Production | **BLOCKED** |

**Verdict:** `CORRECTED_WIRE_AND_OFFLINE_DOLLAR_BUDGET_GATE_TECHNICAL_PASS` with actual runtime payment authorization `DENY`, not a new model trial. A separate prospectively preregistered checkpoint would need a provider-configured dedicated <=$0.02 lifetime key (or more stringent verified guardrail), authenticated key metadata and an independently authorized one-shot POST. Do not create/change management key/guardrail or replay V3-64 without explicit permission. The current implementation does not prove or cause provider-side enforcement. Reusing it as if it did would be a serious safety and science error.
