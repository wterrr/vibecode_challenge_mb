# V3-66 — Prospective HTTP Failure Observability & Request-Compatibility Gate

**Date:** 2026-10-14. **Parent:** V3-65 Draft PR #101 at `3dddad2dcaebbccf3df4c03d3bf5e52882b421be`. **Preregistered before implementation:** FIRST child commit `7669bcaf43ebe4f7709d63eb6e19f2a6db34dfc2`, `benchmarks/learnflowbench/v3/v3_66_provider_failure_preregister.json`.

**Declared scientific disposition:** Offline diagnostic/observability technical verification only. V3-64's real one-request OpenRouter GPT-6 Luna trial failed with `HTTPError` and did not store the HTTP status or provider body. V3-65 later authenticated the inference key and inspected public model catalog metadata, but cannot reconstruct an earlier failed request. **No provider account access or model inference occurs at V3-66.**

## 1. Reuse-first audit and important discrepancy

Audited immutable V3-64 request builder `scripts/run_v3_64_one_shot_real_model.py:request_payload()`, V3-65 sanitized metadata diagnostics and first-party OpenRouter documentation. Found the historical provider wire contains:

```json
"provider": {"order": ["OpenAI"], "allow_fallback": false, "require_parameters": true}
```

At the time of audit, the documented provider preference key was **`allow_fallbacks` (plural)**, not `allow_fallback` (singular). Sources:
- [OpenRouter: model routing](https://openrouter.ai/blog/insights/model-routing/)
- [OpenRouter: provider routing with no fallback](https://openrouter.ai/blog/insights/ai-data-residency/)
- [OpenRouter: structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)

This is a **potential request-shape compatibility error**, NOT proven to be the cause of historical HTTPError. It could be rejected, ignored, normalized, or handled differently by the service; no response status/body survived V3-64, and no inference was conducted to distinguish those hypotheses. The exact original request SHA-256 recomputed from frozen builder is `728e32b0bea658a82054184efee840ddb72957851f0ba87d21042d96d4134c0f`, unchanged.

Other unresolved risks: public catalog's `response_format` and `structured_outputs` parameter advertisements do **not** certify exact `json_schema.strict` execution/routing for this account and pinned provider; V3-65 positive key-specific cap does not establish a funded credit balance; V3-64 `max_tokens=2100` is **not an enforced dollar-spend ceiling**. Do not claim $0.02 was a hard cap or that any of these issues caused a specific historical HTTP error.

## 2. Implemented prospective observability

- `learnflow_v3/v366_provider_failure_observability.py`: **pure, offline** status/error classifier and request-compatibility gate. `sanitize_code()` reads only `HTTPError.code`; it **never reads, serializes, or prints** `HTTPError.read()`, `HTTPError.reason`, URL, response headers, bearer token, arbitrary network exception details or provider body. Known 4xx/5xx status codes are allowlisted; 3xx is recorded as `REDIRECT_BLOCKED`, unknown codes as `HTTP_OTHER`. URLError/timeouts/connection errors collapse to `TRANSPORT_UNAVAILABLE` with no unsafe reason string. The `incident()` function explicitly accepts **one previously attempted request** and produces an all-allowlisted incident record, with SHA-256 of the exact request body, no retry/fallback and no implied authorization.
- `frozen_compatibility()`: checks the exact original V3-64 JSON shape, flags `allow_fallback` vs documented `allow_fallbacks` without changing the source, reports strict-schema/account ambiguity and absence of a hard dollar cap. Requiring the historical spelling means a future corrected request **cannot falsely masquerade as the V3-64 original**. Public provider metadata, if passed in, remains advisory only.
- `scripts/run_v3_66_static_diagnostic.py`: validates immutable first-child preregistration, calls the static analyser, emits a single JSON artifact; no secret retrieval, socket or inference.
- `tests/v3/test_v3_66_provider_failure_observability.py`: 47 PASS, covering 16 known HTTP errors, 3xx redirects, unknown code types, transport and timeout exceptions carrying fake secrets, poison error bodies, wrong model/attempt counts/payload sizes, static wire mutation, public-catalog overclaim, benign success case, output safety and zero-provider-call declaration.
- `.github/workflows/v3-66-provider-error-offline.yml`: CI isolated to V3-66 file paths. No `OPENROUTER_API_KEY` environment, no authenticated request and **no live model POST/GET**. Outputs test-only static provenance receipt.

**Important capability boundary:** This new module is a *prospective helper* for a future separately authorized client. It has **not been integrated into the archived V3-64 one-shot**, which must remain immutable, and does **not itself perform or observe an actual provider request**. A future real trial would need to call `incident()` in its own error handler after a separately approved single POST, with actual provenance and a new prereg.

## 3. Physical CI and artifact receipts

- [V3-66 isolated GitHub Actions #38505772402](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38505772402): **SUCCESS** at push HEAD `88825100adcb06880a2ebfcec9fa538d25fccc70`; **47 tests PASS**, 1 nonfailing warning; sanitizer, source SHA guard and zero-network contract passed.
- [Artifact #11867103215](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38505772402): `v366-STATIC-PROVIDER-HTTP-DIAGNOSTIC-NO-NETWORK`. Independently downloaded and inspected: contains exactly one `V366_STATIC_NO_NETWORK_DIAGNOSTIC.json` (2,045 bytes), with `live_model_posts=0`, `live_provider_gets=0`, `automated_retries=0`, `human_visual_quality=UNRATED`, `production=BLOCKED`. `provider_options_observed` is exactly `allow_fallback`, `order`, `require_parameters`; `hard_dollar_budget_enforced=false`; all four findings have `proven_caused_v364_error=false`.
- Exact original V3-64 failure event remains [#38502942783](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38502942783); historical status `NOT_CAPTURED_CANNOT_RECOVER`, underlying root cause `UNDETERMINED`. No reexecution or replacement of V3-64's evidence.

## 4. Decision matrix and remaining gap

| Gate | V3-66 conclusion |
| --- | --- |
| Deterministic sanitized status capture of simulated 4xx/5xx/redirect/network exceptions | **TECHNICAL PASS** |
| No raw provider body/secret/account details in output | **PASS for covered negative tests** |
| Static original-wire preservation and source request hash | **PASS** |
| Exact fallback parameter spelling compatibility | **POTENTIAL INCOMPATIBILITY FLAGGED, CAUSE NOT CONFIRMED** |
| Actual V3-64 HTTP status/body | **NOT RECOVERABLE** |
| Successful new model-authored storyboard/MP4 | **NOT ATTEMPTED** |
| Accurate enforced USD cost ceiling | **NOT IMPLEMENTED / BLOCKED** |
| Real model creative generalization or 3Blue1Brown quality | **NOT TESTED / NOT DEMONSTRATED** |
| External human quality and learning gain | **UNRATED / NOT MEASURED** |
| Production | **BLOCKED** |

**Next scientific step:** Before proposing a new paid one-shot trial, freeze a NEW exact request wire using documented `allow_fallbacks`, validate request fields offline against provider contracts, and implement a real **enforced** spend or authorization guard rather than relying on `max_tokens` alone. Then obtain explicit new budget approval and new preregistration. Do not silently mutate or resend V3-64's one-shot request. No merge main, no V2 Core or production-prompt edits.
