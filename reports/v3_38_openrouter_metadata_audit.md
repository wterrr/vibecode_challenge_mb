# V3-38 — OpenRouter 404 Metadata-Only Audit (Zero Inference)

**Scope:** Stacked child of V3-37 Draft PR #71 at immutable parent `aeca5ce2d2889a605f452eb1a89ae43a9efc8176`. Do not merge main. **No new model inference POST is authorized.** Preimplementation registration `ce390bbdaa782fa66d45fa9bd054bcf246e1dd11` freezes two allowed URL paths, GET method, read-only key/public metadata and sanitized evidence.

## Source-grounded API facts

- [OpenRouter current API key](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-key): `GET https://openrouter.ai/api/v1/key`, Bearer auth; API 200 may include `limit`, `limit_remaining`, `is_free_tier`, `is_management_key`, expiry, and sensitive account-linked fields. **Never store creator_user_id, label, workspace ID, usage/remaining numeric amounts or raw response.** A 200 shows the secret is a valid key for this GET, NOT eligibility for exact GPT-6 Luna chat routing.
- [Model endpoints](https://openrouter.ai/docs/api/api-reference/endpoints/list-endpoints): `GET https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints`. Current public endpoint data lists model ID and advertises `response_format` and `structured_outputs` for multiple endpoints. Metadata is not historical 2026-10-10 POST routing evidence, nor key-specific guarantees.
- [Structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs): `response_format: {type:json_schema,json_schema:{strict:true,...}}` and `provider.require_parameters=true` are documented parameters, with support endpoint-dependent.
- [Credits](https://openrouter.ai/docs/api/api-reference/credits/get-credits): `GET /api/v1/credits` requires a **management key**, not included in this audit. Even a positive per-key limit does **NOT** certify account balance/entitlements.
- The inherited live payload uses **`max_tokens=6500`** with strict `json_schema`, `temperature=.65`, `provider.require_parameters=true` and `provider.allow_fallbacks=false`. OpenRouter public metadata for some GPT-6 Luna endpoints lists `max_completion_tokens` instead of `max_tokens`, while others list `max_tokens`. Do NOT assume the server maps these identically. **This is a testable routing-compatibility hypothesis, not proven HTTP 404 root cause.**

## Exact historical evidence

[V3-37 Actions #38017323094](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38017323094), code HEAD `f6a2f3a`, completed offline gate **SUCCESS**. Single exact strict GPT-6 Luna POST attempted by paid job and received `V335_HTTP_404`. [Sanitized receipts artifact #11656444444](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38017323094/artifacts/11656444444): attempted provider HTTP requests 1, response SHA null, usage null, no retry, no fallback. No real model-authored scene/MP4. Provider-specific cause **UNDETERMINED** and cannot be reconstructed from discarded error body. V3-37 one-shot consumed.

## Reuse-first implemented V3-38

- `learnflow_v3/openrouter_metadata_audit.py`: stdlib-only, two fixed HTTPS URLs, **GET exclusively**, no follows of redirects, no generic network endpoint, no retries and no management calls. A metadata-only current-key response records `KEY_AUTHENTICATED_METADATA_ONLY` vs `KEY_UNAUTHORIZED`/blocked/unknown; exposes boolean/enum for free tier, key type, positive/zero/unknown limit, expiry category; never exact credit amounts, identifiers or any raw body. Public GET emits bounded counts for strict schema and token-limit support, with fixed provider-name allowlist.
- `tests/v3/test_v3_38_openrouter_metadata_audit.py`: fake senders inject sensitive fields/secret to ensure they are not persisted; prohibit all non-GET and nonallowlisted URLs, status 401/403/404/429, malformed provider names, mismatched model ID, no-key semantics and epistemic limits. Fakes are **NOT** model/account evidence.
- `.github/workflows/v3-38-openrouter-metadata-audit.yml`: offline tests on push/PR, public unauthenticated GET only; one **separately tagged** `[v3-38-readonly-key-check]` PUSH may perform current-key GET plus public catalog GET after same-HEAD offline PASS, with GitHub Secret scoped only to that step; PRs and reruns cannot use secret. NEVER an inference job. 0 paid model POST.
- Evidence in CI is **sanitized only**. Model entitlement, workspace routing, exact historical 404 cause, generic schema acceptance and production status all remain UNVERIFIED unless separately validated. Do not mutate V3-37 experimental prereg, frozen V3-16/V3-33 or V2 Core.

## Acceptance / current outcome

- Current offline CI: PENDING.
- One authenticated GET with existing GitHub secret: PENDING (only after same-HEAD offline CI passes).
- Genuine new GPT-6 Luna creative scene: NOT ATTEMPTED, no new inference authorization.
- Historical V3-37 HTTP 404 root cause: **UNDETERMINED**.
- Production: **BLOCKED**.

**Future model request must be separately authorized and preregistered.** Do not use a successful key metadata GET as justification to auto-retry.
