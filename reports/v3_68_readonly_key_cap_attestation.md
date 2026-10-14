# V3-68 — Current OpenRouter Key USD Cap Read-Only Attestation

**Date:** 2026-10-14. **Stacked parent:** V3-67 Draft PR #103 frozen at `c0b6efe0fb1c149d0fb823e579afcf9ff5821d93`. **First child prereg:** `c1118c9ad25db6abe90ae5c3714003abc38e1d33`, before any implementation, offline test, or new OpenRouter metadata GET.

**Scientific target:** Determine whether the **currently connected** OpenRouter inference key meets a provider-enforced **USD $0.02 lifetime** per-key cap policy including BYOK. A `GET /api/v1/key` response can provide evidence about the **current credential's** limit settings but **cannot establish that the key was dedicated to this specific LearnFlow experiment**, nor that a model request has funded account credit or exact routing entitlement. The checkpoint is read-only; never creates/updates API keys or guardrails, and never sends a model POST.

## 1. Source audit, reuse-first, and preregistered acceptance

Official provider references:
- [OpenRouter GET current API key](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-key): authenticated `GET /api/v1/key` returns `limit` and `limit_remaining`, `limit_reset`, `include_byok_in_limit`, `is_management_key`. It does not prove dedicated-purpose key identity.
- [OpenRouter API key updates](https://openrouter.ai/docs/api/api-reference/api-keys/update-keys): key limit in USD, reset options and BYOK inclusion; **requires management key**, so V3-68 never calls it.
- [OpenRouter guardrails](https://openrouter.ai/docs/guides/features/guardrails/overview): layered provider-enforced spending restrictions but dedicated guardrail assignment requires separate evidence and, where applicable, management access.

Reuses existing **V3-38** safe `learnflow_v3/openrouter_metadata_audit.py:_get()`, with allowlisted URL, fixed GET method, 20,000-byte response ceiling, 12-second network timeout, no redirects or retries, and no raw error-body logging. Reuses **V3-67** `policy_for_key()` rather than creating a weaker second spending-cap rule. No management credentials or endpoints were requested.

Preregistered exact policy: `limit` finite and <=$0.02, `limit_remaining` positive and <=limit, `limit_reset is null` (lifetime), `include_byok_in_limit is true`, `is_management_key is false`. Any missing/malformed/unknown field denies. Successful host policy would **still not authorize inference**, because separate key dedication, account credit, model routing and new user approval remain unproven.

## 2. Implementation and adversarial QA

- `benchmarks/learnflowbench/v3/v3_68_readonly_key_cap_preregister.json`: first-child scientific prereg; maximum one provider metadata GET, zero inference POST, zero key changes, zero retry.
- `learnflow_v3/v368_key_cap_readonly.py`: safe one-GET wrapper and **only an allowlisted sanitized projection** of HTTP status, provider cap decision, origin of evidence, count of attempted GET/POST and scientific blockers; no raw key, response body, balance numbers, token/label/account/workspace identifiers. Separates real authenticated GET from test sender and does not claim dedicated-purpose identity.
- `scripts/run_v3_68_readonly_cap.py`: safe direct-CLI adapter, writes one receipt; never prints exact key cap or secret.
- `tests/v3/test_v3_68_readonly_key_cap.py`: **50** tests for missing/oversize/null/negative cap, zero/oversized allowance, day/week/month reset, BYOK omission, management credentials, malformed provider envelope, 4xx/5xx HTTP failures, redirects, unsafe error bodies and mocked-vs-actual provider provenance.
- `.github/workflows/v3-68-key-cap-offline.yml`: strict mock testing with no provider secret or network calls.
- `.github/workflows/v3-68-one-time-key-cap-get.yml`: separate **unique trigger** `research/V368_ONCE_KEY_CAP_GET_TRIGGER.txt`, prior-run protection, same strict test suite before one OpenRouter key GET. No inference or management requests.

The first offline run [#38507507753](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38507507753) initially found one test classification mismatch (null existing cap was `DENY_INVALID_PROVIDER_KEY_CAP`, not `DENY_MISSING_PROVIDER_KEY_CAP`). Corrected **test expectation**, not safety logic; [offline run #38507600292](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38507600292) completed **SUCCESS, 50/50**.

## 3. Real read-only provider observation — evidence

[One-time metadata run #38507703648](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38507703648), exact one-time trigger commit `4c459c7ca497296592ac1f75084ee44f765cfa2e`: **SUCCESS** at workflow execution and 50/50 negative tests. The runner made **exactly one authenticated GET to `/api/v1/key`**, observed `HTTP_200`, then emitted the safe verdict:

| Registered diagnostic | Observed result |
| --- | --- |
| HTTP GET current key | **HTTP 200; authenticated** |
| Current key's BYOK budget coverage | **DOES NOT SATISFY** `include_byok_in_limit=true` |
| Provider cap policy decision | **`DENY_BYOK_SPEND_OUTSIDE_CAP`** |
| Lifetime <=$0.02 cap confirmed | **NO** — policy stopped at the BYOK gate, so other cap fields are NOT independently certified |
| Key dedicated specifically to LearnFlow | **NOT PROVEN** by this GET |
| New model inference POST | **0** |
| Management key/guardrail changes | **0** |
| Output contains real balance or identifiers | **NO** |
| Production | **BLOCKED** |

Actual GitHub artifact **#11868357421** `v368-SANITIZED-CURRENT-KEY-CAP-READONLY-NO-PAID-POST` independently downloaded and unzipped. One file `V368_SANITIZED_CURRENT_KEY_CAP.json` (1,311 bytes) was verified. It records `checked_at_utc=2026-10-14T03:43:48Z`, `budget_gate_result=DENY_BYOK_SPEND_OUTSIDE_CAP`, `scientific_verdict=DENY_NO_PROVIDER_CAP_PROOF`, `provider_metadata_get_attempts=1`, `model_http_post_attempts=0`, `dedicated_key_identity_established=false`, `may_issue_model_http_post=false`. It contains no key secrets, workspace/account IDs, exact numerical cap or account credit data.

**Important:** The BYOK setting may be irrelevant to actual spending if no BYOK models are used; however, the preregistered policy unconditionally requires inclusion, so the gate **must deny**. No evidence establishes the existing key is purpose-dedicated, or that its lifetime cap is <=$0.02; do not report the latter as true or false without inspecting the remaining fields under an independently preregistered test.

## 4. Scientific disposition and next action

**V3-68: READ-ONLY REAL PROVIDER METADATA TECHNICAL PASS; KEY BUDGET ELIGIBILITY NO-GO.** The scientific query was completed faithfully, not hidden by the workflow's success conclusion. The key is authenticated but does **not** satisfy the frozen safe cap policy; **no new paid request may be made under this protocol**.

This does not clarify historical V3-64 one-request `HTTPError` (status/body not captured), nor demonstrate genuine model-authored storyboard, near-3B1B quality, learner comprehension or independent human quality. Those remain `UNDETERMINED`, `NOT_TESTED`, `NOT_DEMONSTRATED`, `NOT_MEASURED` and `UNRATED`, respectively. Production remains `BLOCKED`.

A future checkpoint can document user-operated setup of a new **dedicated, lifetime <=$0.02** OpenRouter inference key with BYOK included; this requires explicit permission for account/key mutation and fresh read-only attestation using a **new** preregistration. Do not silently alter the current key or rerun the one-use V3-68 GET trigger. Any eventual model POST requires a distinct user-approved preregistration. No code or API key changes to the original V3-64 trial, V2 Core, production prompts or `main`.
