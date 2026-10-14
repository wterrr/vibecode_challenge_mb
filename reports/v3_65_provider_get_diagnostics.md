# V3-65 — OpenRouter Provider Compatibility & Key Metadata Audit (GET-only)

**Date:** 2026-10-14. **Parent:** V3-64 Draft PR #100, frozen HEAD `f8d4e150f2b3e9c3003d3aa6aba30261a36b92dd`. **First child prereg:** `91b42a2436fb6de24f2c03d9d4fe6df54bb9929a`, before implementation or any network GET. No model inference, no production prompt or V2 Core modifications, no main merge.

## Question and evidence boundary

V3-64's exactly one previously registered real GPT-6 Luna OpenRouter POST ended in `urllib.error.HTTPError` at [run #38502942783](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38502942783). Artifact #11866413693 froze **one attempted POST**, `PROVIDER_TRANSPORT_OR_HTTP_FAILURE_NO_RETRY`, but neither HTTP code nor body. A GET of today's metadata **cannot reconstruct the status/response of a past POST** and cannot prove exact-provider routing, account-level funded balance or account's strict-schema model entitlement. V3-64 may not be rerun as part of this checkpoint.

The V3-65 protocol froze **at most two** OpenRouter metadata queries: `GET https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints` (no key) and `GET https://openrouter.ai/api/v1/key` (existing GitHub secret only). Other APIs, notably `/api/v1/chat/completions`, `/api/v1/responses`, `/api/v1/credits` requiring management permissions, and POST/PATCH/DELETE, are not allowed. Redirects, retries, saving raw account responses, key labels/IDs or numerical credit balances are explicitly prohibited. The existing V3-38 `learnflow_v3/openrouter_metadata_audit.py` already safely performs exactly these GETs and is **reused**; V3-65 only provides historical-wire comparison and redacted report projection.

## Implementation

- `benchmarks/learnflowbench/v3/v3_65_provider_get_diagnostics_preregister.json` — first-child one-time GET-only prereg, historical failure and no-conclusion rules.
- `scripts/run_v3_65_provider_get_diagnostics.py` — calls **existing** `run_audit()` from V3-38, checks frozen V3-64 request body without sending it, projects only allowlisted key status / categorical limit / provider counts. Explicitly retains historical cause `UNDETERMINED`.
- `tests/v3/test_v3_65_provider_get_diagnostics.py` — 20 PASS: HTTP 200/401/402/403/404/429/500 scenarios, OpenAI catalog compatibility ambiguities, key cap vs funded credit, redirect/endpoint safety, no leaked secret/account identifiers, and **direct script CLI import**.
- `.github/workflows/v3-65-provider-metadata-offline.yml` — push and PR strict tests only, no provider network traffic.
- `.github/workflows/v3-65-provider-metadata-get-once.yml` — first one-shot GET diagnostic; [run #38504156707](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38504156707) **failed before any OpenRouter GET** with `ModuleNotFoundError: learnflow_v3`, because direct `python scripts/...` did not bootstrap repo root. The import error occurred at script line 12, before importing or executing any GET probe, and did not create the output artifact.
- `benchmarks/learnflowbench/v3/v3_65_r1_preget_import_recovery.json` + `.github/workflows/v3-65r1-provider-get-recovery.yml`: preregistered distinct recovery **after original no-network import failure**, not a retry of a sent provider request. Pinned first failed run/HEAD/job and checked it before executing; new once-only trigger `research/V365R1_GET_IMPORT_RECOVERY_TRIGGER.txt`. Fix added an import-root bootstrap and a regression proving direct CLI invocation.

## Actual measurements — successful controlled recovery

- [Offline run #38504291340](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38504291340) **SUCCESS**, 20/20 offline tests, no GET/provider inference.
- [GET-only recovery #38504449412](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38504449412) **SUCCESS**; 20/20 tests, exactly **2 metadata GET attempts and 0 inference POST**. GitHub artifact **#11867840855**, `v365R1-SANITIZED-GET-DIAGNOSTIC-RECOVERY`, independently downloaded and inspected; contains a single JSON projection. Account identity, key, exact balance and raw response are not persisted.

| Signal observed at 2026-10-14T03:06:01Z | Verified safe output | Limit |
| --- | --- | --- |
| Public Luna endpoints GET | HTTP 200, matched model ID, 7 listed endpoints | Public discovery only |
| Advertised structured JSON | 7 endpoints; 4 also list `max_tokens` | Parameter-name advertising does **not** certify exact `json_schema.strict` wire |
| OpenAI provider schema advertisement | Present | Does **not** prove the V3-64 `provider.order=["OpenAI"]` request could be routed for this key |
| Current inference API key metadata | HTTP 200, authenticated, key type INFERENCE, free_tier false | Authentication now is not retrospective inference authorization |
| Key-specific remaining cap | POSITIVE | Does **not** establish funded account credit balance or account model entitlement |
| Key expiration category | NOT_REPORTED | Do not infer an expiry timestamp |
| Original V3-64 failing POST status/body | **NOT_CAPTURED_CANNOT_RECOVER** | Historical cause remains **UNDETERMINED** |
| V3-65R1 model inference | 0 POST | No new candidate or MP4 originated from a model |

The V3-64 request SHA-256 recomputed locally from its unmodified payload is `728e32b0bea658a82054184efee840ddb72957851f0ba87d21042d96d4134c0f`, matching the previously frozen receipt. Provider POST failure root cause is **not** established. Since catalog data may evolve, it must not retroactively be treated as the state at the original POST time.

## Risk assessment and verdict

**GET-only metadata diagnostics: TECHNICAL PASS.** Key authenticated and public model metadata currently advertises plausible structured-output capability. This narrows investigation but does not prove V3-64 failed because of credits, strict JSON schema, model routing, throttling, model slug or account restrictions. Each remains **UNTESTED** without the original failure status; raw error was deliberately not captured in the old trial.

**Genuine model-authored storyboard:** NOT OBSERVED. **Three-Blue-One-Brown creative quality:** NOT DEMONSTRATED. **Independent human pedagogy:** UNRATED. **Student learning:** NOT MEASURED. **Production:** BLOCKED. No inference retries, main merge, V2 Core or production prompt modifications.

**Next checkpoint recommendation:** Research-only V3-66 diagnostics/preflight should first implement and offline-test **sanitized HTTP failure status capture** (no response body or key) in a future prospective client, and analyze potential `provider.order`, `response_format`, and cost-budget confounds from provider documentation without inference. Any *new* paid model request requires a separately preregistered one-shot protocol and explicit new authorization; neither this checkpoint nor the archival V3-64 workflow may silently retry.
