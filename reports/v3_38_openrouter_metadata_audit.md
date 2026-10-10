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

## One read-only opt-in authorized, gated on same-HEAD offline CI

Pre-tag code HEAD `6770e68f59221a93644a28118f9bccb43c001fc1`. This entry authorizes exactly one tagged CI job to read OpenRouter public metadata and the current GitHub Secret key's **metadata**, no inference. The actual authenticated GET does **not** run until the tagged-commit offline adversarial tests have passed; otherwise the dependent secret job is SKIPPED. The key remains masked, and only fixed sanitized enums and public endpoint counts may be uploaded. This is a GET-only metadata observation, not authorization for any future model or account-management action. New results must be recorded after verifying same-HEAD job and sanitized artifact. Do not reuse/reissue this tagged commit.

## Single recovery authorization for read-only current-key GET

Original opt-in commit `56b2b451`, [push run #38018269731](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38018269731) failed BEFORE any secret-bearing step, at test collection: `ModuleNotFoundError: No module named 'pydantic'` caused by the existing `learnflow_v3/__init__.py` package imports. The authenticated metadata job was **SKIPPED**, so actual key GETs = 0 and model POSTs = 0. Patched test bootstrap to install `pydantic>=2,<3`; preregistration for exactly one **read-only** recovery is `benchmarks/learnflowbench/v3/v3_38_import_recovery_preregister.json` (`f4bbe2df`). Only new `[v3-38-import-recovery-readonly-key-check]` opt-in is recognized. This documented commit opts into the bounded GET after **same-tagged-HEAD offline adversarial tests PASS**, never upon PR, rerun, or failure. This does NOT authorize model generation, management API or raw key/account logging.

**Findings of the tagged recovery:** PENDING CI and artifact verification. No claims about authenticated key validity or 404 causality until the real sanitized receipt is read.

## Import-isolation remediation (after tagged GET was SKIPPED)

[Run #38018493840](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38018493840) and [PR #38018496557](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38018496557) both FAILED during offline test collection. Actual trace goes `learnflow_v3.__init__ → pattern_router → learnflow_v2.repair → qa → layout/backends/kiwi` and `ModuleNotFoundError: No module named 'kiwisolver'`. **The authenticated GET job was SKIPPED in both**; zero key GETs, zero model POSTs. Adding one dependency at a time would make a standard-library provider diagnostic needlessly import the whole graphics/QA graph.

**Repair:** `tests/v3/test_v3_38_openrouter_metadata_audit.py` loads only `learnflow_v3/openrouter_metadata_audit.py` via `importlib.util.spec_from_file_location`, never invoking `learnflow_v3.__init__`. Both offline and key-only production entrypoints execute the audited file by explicit path: `python learnflow_v3/openrouter_metadata_audit.py` (no `-m`). Workflow now installs only pytest; an additional `python -S` check proves the import works without site-packages and does not load `learnflow_v2`, `learnflow_v3`, `pydantic`, or `kiwisolver`. Fixed-path GET contract, secret handling and historical model POST budget unchanged. This is an **import-boundary correction**, not a provider compatibility claim.

**New import-isolation CI outcome:** PENDING at code HEAD; one-time metadata GET not yet executed. The previously used tagged push is not eligible for a new GET. A distinct, preregistered read-only recovery will be needed if the previous tagged run never reached its authenticated job; never repeat a key probe without an explicit documented zero-GET cause. Inference remains prohibited.

## One distinct stdlib-isolated GET-only opt-in (2026-10-10)

The import-independent code at `098082f3` passed [V3-38 PR CI #38019225217](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38019225217) and [push CI #38019222218](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38019222218), including Python `-S` isolated-load, full GET-only tests, and public metadata GET. The original `56b2b45` and `b7f69fe` tagged runs both had auth jobs **SKIPPED**, so key GETs=0. Registered new key-GET recovery in `benchmarks/learnflowbench/v3/v3_38_stdlib_import_recovery_preregister.json` at `8e9a3f8`, before this opt-in.

This is the **single authorized metadata-only recovery tag** under V3-38, `[v3-38-stdlib-isolated-key-check]`. It does NOT by itself invoke key GET: the workflow must PASS same-tagged-HEAD `offline-adversarial-and-public-get` first. The following dependent job may issue exactly one authenticated fixed-path GET `/api/v1/key`, one public endpoints GET, no retries/redirects and **zero model POSTs**. If offline fails, the secret job is SKIPPED. Raw key, account fields, usage numbers and error bodies are not logged. The exact key-authentication outcome remains **PENDING** until a sanitized artifact is inspected. No rerun or additional tagged push is authorized.

## Verified V3-38 authenticated findings — finished metadata phase (2026-10-10)

**Unique tagged run** [Actions #38019407661](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38019407661) at immutable `aafd740b46ae620baeac7a7b8e810c30b6733a01` **SUCCESS**. Both offline adversarial/public-GET and authenticated-key-GET jobs finished **SUCCESS**. Checked downloaded sanitized artifacts:
- [Authenticated sanitized evidence #11657084430](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38019407661/artifacts/11657084430), JSON `sanitized_findings.json`.
- [Public metadata evidence #11657134163](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38019407661/artifacts/11657134163), JSON `metadata.json`.

**Grounded observations from the REAL GitHub Secret, without disclosing sensitive fields:**
- OpenRouter `GET /api/v1/key` responded **HTTP_200**, `state=KEY_AUTHENTICATED_METADATA_ONLY`, `key_authenticated=true`, `key_type=INFERENCE`, `free_tier=false`, `key_limit_remaining_state=POSITIVE`. `expires_at` was not reported, **NOT_REPORTED is NOT a certification the key never expires**.
- Public `GET /api/v1/models/openai/gpt-6-luna/endpoints` responded **HTTP_200**, ID matched `openai/gpt-6-luna`, **7 endpoints**, **7 advertise `response_format` plus `structured_outputs`**. Of those, **4 advertise `max_tokens`** and **3 advertise `max_completion_tokens`**. Public provider-name allowlist included OpenAI, Azure and Amazon Bedrock. **Do not assume all 7 accept every other request field or `strict:true`.**
- Exactly **2 GET metadata requests**, **0 inference POSTs** by V3-38. The previously preregistered V3-37 single model POST remains consumed.
- The key's per-key `limit_remaining` is positive but does **NOT** certify funded OpenRouter account credits, sufficient budget for a particular model call, precise provider eligibility, guardrails, regional access or strict-schema routing.

**Investigated static request contract:** V3-37 uses `POST https://openrouter.ai/api/v1/chat/completions`, `model=openai/gpt-6-luna`, `temperature=0.65`, `max_tokens=6500`, `response_format=json_schema(strict=true)`, `provider.require_parameters=true`, `provider.allow_fallbacks=false`, `messages=[system,user]`. OpenRouter's [chat API docs](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request) label `max_tokens` **deprecated** and recommend `max_completion_tokens`. Public catalogs listing different supported-parameter subsets motivates an explicit **crosswalk of *all* wire-generation fields per endpoint**, not merely the two schema flags. Implemented new read-only counts `v337_all_advertised_generation_params_count` and `alternate_completion_limit_all_advertised_params_count` for the exact and alternative token-limit fields respectively. These remain public **advertisements**, not authenticated capability proof.

**Differential diagnosis:** API key-invalid is excluded **at the time of the real key GET**, not necessarily at the earlier POST timestamp. Public model listing proves the model and endpoint capabilities existed during V3-38 observation. Historical HTTP 404 can still arise from provider eligibility/routing, requested-parameter filtering, guardrails, workspace/region restrictions or a time-varying provider configuration. Because V3-37 caught `HTTPError(404)` but discarded sanitized provider-specific error type/message, the *precise* V3-37 404 cause cannot be recovered from its archived artifact. DO NOT assert `max_tokens` caused the failure, silently change wire protocol or send another chat request.

**Status:** V3-38 real authenticated metadata audit **PASS** with the above epistemic limits. Subsequent optional public GET compatibility-count tests **PENDING exact-head CI**. New genuine model-created MP4 still **NO**, V3-37 live technical NO-GO, production BLOCKED. The unique metadata-key read was already exercised; no reason to repeat `GET /api/v1/key` on follow-up code pushes.

## Additional publicly verifiable root-cause clue: unsupported temperature with strict routing

Read the full live public JSON for `https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints` on 2026-10-10, in addition to V3-38's archived sanitized actual GitHub key receipt. **7/7 endpoint entries omit `temperature` from `supported_parameters`**; every entry includes `response_format` and `structured_outputs`; **4/7 include `max_tokens` and 3/7 `max_completion_tokens`**. Independently inspect the actual historical V3-37 payload in `structured_scene_authoring.one_shot_structured`: it always sends `temperature=0.65` with `provider.require_parameters=true`. According to OpenRouter's published provider routing rules, `require_parameters` restricts a request to endpoints that advertise support for every requested inference parameter. Hence the observed public parameter crosswalk gives **0/7 candidates** for the exact V3-37 advertised generation-parameter set; **0/7** for an otherwise unchanged request that merely swaps to `max_completion_tokens`. Omitting unsupported `temperature` would leave up to **4/7** catalog-advertised candidates for `max_tokens` plus schema flags (3/7 if swapping completion token limit). This is an exceptionally strong *routing exclusion hypothesis* for historical 404; it is NOT a verified reconstruction of the earlier server response or account-based routing/guardrails.

Evidence: public live endpoint JSON https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints ; OpenRouter [provider routing guide](https://openrouter.ai/blog/insights/model-routing/) and [parameter-regression guidance](https://openrouter.ai/blog/tutorials/ai-agent-regression-testing-after-a-prompt-or-model-change/). A changed request is a *new registered intervention*, not a justified silent mutation or retry of V3-37. Keep `require_parameters=true` and schema strict in any proposed new trial; do NOT disable the filter just to get a response.

**No additional authenticated GET or inference POST has been issued by this public-metadata observation.**
