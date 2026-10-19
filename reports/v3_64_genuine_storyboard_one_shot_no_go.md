# V3-64 — Genuine Model-Authored Storyboard Trial (one-shot NO-GO)

**Date (UTC):** 2026-10-14. **Frozen parent:** Draft PR #99 at `2ef842ba9baf7f56c7a3906b8aa1c793ef437b12`. **Registration:** FIRST CHILD COMMIT `f3fe18ce7d90154f1e128c55f491e9e2ea9c0b64` before code, tests, workflow or POST. **Status:** **PROVIDER HTTP FAILURE — NO-GO**, exactly ONE client-side model POST attempted, no retry or fallback.

## Question and design

**New never-rendered heldout task:** “Why does a 3-by-4 array have the same number of objects as a 4-by-3 array?” Distinct from the V3-62/63 probability, physics and chemical inventory cases. Host fact ledger: 3×4 = 4×3 = 12; 12 individually persistent IDs `unit_00`…`unit_11`; questions and initial 3 rows × 4 columns must come before physical regrouping into 4 rows × 3 columns and numerical conclusion. Five acts QUESTION → SETUP → TRANSFORM → WITNESS → CLOSE. No source 3B1B frames or scripts were copied.

The five-role provider JSON contract proposes research-stage cognitive misconception/probe, narrative framing and five original captions, geometric layout and object focus, motion scheduling and critic limitations. Strict host admission blocks bad math, missing/reordered IDs, premature count, forged evidence SHA, injected code, false native speech alignment or extra fields; returned text would remain **semantic-review-required**, not proof of correctness for unrestricted language.

OpenRouter `openai/gpt-6-luna` was chosen from previously wired repository integrations, `OPENROUTER_API_KEY` GitHub secret, one POST, 2100 maximum output tokens, temperature OMITTED, provider require_parameters, `allow_fallback=false`, no retries, one unique trigger `research/V364_ONE_SHOT_TRIGGER.txt`. Predeclared token-based expected cost ceiling $0.02, but **actual charge unobservable without completed usage/billing receipt**, so do not claim a spend amount.

## Implementation

- `benchmarks/learnflowbench/v3/v3_64_one_shot_genuine_storyboard_preregister.json`: first-child frozen facts, controls and single-request decision rule.
- `learnflow_v3/v364_heldout_storyboard.py`: strict model JSON Schema (provider-compatible subset), host fact/source + 12-object invariants, fail-closed tests and clearly identified HOST_TEST baseline.
- `learnflow_v3/v364_native_array_compiler.py`: host-authored grid compiler with persistent 12 unit IDs, physically interpolated 3×4 → 4×3 geometry, source-backed numeric reveal and segment TTS. Creates two **different audio** tracks for model and host, so independent quality comparison would be confounded even if model had replied.
- `scripts/run_v3_64_one_shot_real_model.py`: actual one-request no-retry OpenRouter client with synthetic-injection unit test, request SHA, sanitized real-provider response proof and fail-closed native render. The workflow never silently uses a test fixture to declare actual model output.
- `scripts/run_v3_64_native_preflight.py`: full H264/AAC host-only two-video test before spending model calls.
- `tests/v3/test_v3_64_one_shot_real_model.py`: 29 strict host/source/wire, invalid-claim, injection, fixed identity, and fake sender provenance tests.
- `.github/workflows/v3-64-preregister-and-preflight.yml`: offline strict and host-native proof.
- `.github/workflows/v3-64-live-one-shot.yml`: one unique trigger commit, previous-run-history guard, repeat native preflight, SINGLE OpenRouter POST, fail-closed receipt and artifact upload. Not triggered by PR or documentation commits.

## Frozen GitHub evidence

1. **Final offline preflight** [Actions #38502724125](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38502724125): both jobs **SUCCESS**; 29/29 schema/adversarial tests, full two-MP4 host-only H264/AAC encode and source receipt PASS. The previous failed CI attempts were corrected **without calling model API**.
2. **One-shot live attempt** [Actions #38502942783](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38502942783), triggered exactly once by commit `777a8a5c11af805732692c51c74c6ea664a848c1`: one-trigger-history guard PASS, host-only native H264/AAC smoke PASS (397 frames). Log shows `V364_ONE_AUTHORIZED_POST_ATTEMPT` at 02:49:26 UTC, followed immediately by `V364_PROVIDER_FAILURE_NO_RETRY HTTPError`; final gate fails deliberately because provider-native proof is missing. **No second POST/retry**.
3. Downloaded first-party GitHub Actions artifact **#11866413693** `v364-ONE-SHOT-REAL-RESPONSE-OR-BLOCKED-RECEIPT`: contains **only** `attempt_receipt.json`. It records one client POST, requested model `openai/gpt-6-luna`, output cap 2100, ledger SHA `8ea108abef60738268892c74b9013da33e9d09064fb2e9de19f234ca4f6fee76`, request SHA `728e32b0bea658a82054184efee840ddb72957851f0ba87d21042d96d4134c0f`, outcome `PROVIDER_TRANSPORT_OR_HTTP_FAILURE_NO_RETRY`, error type `HTTPError`, production BLOCKED.
4. The specific HTTP response status (400/401/402/429/etc), response body and actual billing are **NOT RECORDED** by the frozen runner; no exact root cause may be inferred from `HTTPError` alone. The CI secret was available as a masked environment variable, but secret validity/credits are not proven. **No provider candidate JSON, no provider response ID, no genuine model-authored MP4** was produced.

## Scientific status, validity and required next work

| Question | Verified conclusion |
| --- | --- |
| Is the new heldout math source/scene contract and native host renderer viable? | **YES, only on HOST_TEST fixture** |
| Did a real external model request get attempted? | **YES, one client HTTP POST**, provider returned HTTP error |
| Did a real model candidate get captured and verified? | **NO** |
| Does five-role model creativity generalize to novel user queries? | **NOT TESTED / NO-GO** |
| Is the native video near 3Blue1Brown creative/pedagogical quality? | **NOT DEMONSTRATED** |
| Human-rated clarity/learning gain | **UNRATED / NOT MEASURED** |
| Production deployment | **BLOCKED** |

**Do not rerun V3-64 live**, edit its trigger to resend, or mislabel a HOST_TEST renderer output as provider-authored. A later independently preregistered checkpoint could first perform **non-inference public/provider capability and account-credit GET diagnostics**, save sanitized HTTP failure status for a future experiment, then request separate user cost authorization for a **new** one-shot trial. No data from a failed first trial may be overwritten or silently repaired. No merge to main, V2 Core edits or production-prompt changes.
