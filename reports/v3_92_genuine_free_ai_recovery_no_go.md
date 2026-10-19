# V3-92 — Genuine Free AI Pedagogical Authoring Recovery · Live NO-GO

**Observation date:** 2026-10-19 UTC. **User deadline:** 2026-10-21. **Stacked parent:** Draft PR #128 frozen HEAD `0c8c179caa610443b6a1dbaa384403a18a9f8a75`. **First-child prereg commit BEFORE implementation:** `b66339d4d4f2d6fdaff5fa08af58f0bd6aa91769`. **Draft child PR:** #129. No merge to `main`.

## 1. Scientific question and original defect
The previously attempted genuine free-model V3-91 run [#39193382761](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/39193382761) posted once to OpenRouter and was host-rejected on a non-`stop` finish, but had not recorded **which** `finish_reason` or which actual model was selected. Its precise cause is still unknown; V3-92 does **not** retroactively infer it.

This prospective V3-92 experiment asked whether a **single new** free provider response, with a shorter model-facing original pedagogical storyboard, could pass the trusted source ledger and render a real narrated native video. The task is the *same* bounded 3×4 ↔ 4×3 twelve-square mathematical scene from V3-64, **not an unseen lesson domain or fully general query-to-video agent**.

## 2. Implementation
- `benchmarks/learnflowbench/v3/v3_92_one_free_ai_recovery_preregister.json`: first-child frozen policy: one zero-priced `openrouter/free` POST, no retry, no paid fallback, new unique one-use trigger only after exact parent offline/native green, immutable host semantic proof, separate external provenance, human review NOT PASS.
- `learnflow_v3/v392_compact_authoring.py`: six-field original model-authored plan: teaching opening/closure, staging, semantic motion, focus and **five novel captions**. Strict local parser blocks malformed/duplicated/nonfinite JSON, unsafe text, unsupported numbers, premature answer and missing 12. Host, never model, supplies correct 12 persistent IDs, grid rearrangement, fact ledger SHA, stage clock and reveal rule. Reuses V3-64 source-bound native renderer.
- `scripts/run_v3_92_free_ai_authoring.py`: **provider strict JSON schema was removed from transport but strong host validation retained**. Public model catalog must show zero prompt/output pricing. One non-retried HTTP POST. Safe `finish_reason`, `native_finish_reason`, actual model slug, token usage, cost disposition and hashed response ID now captured **before** host result acceptance; rejected raw model content is *not persisted*. No model-generated code executed. HOST_TEST mock senders cannot be attributed to real AI.
- Two isolated Actions workflows: offline hostile tests/native smoke and a truly one-use live trigger with explicit exact-parent offline/native success guard.

## 3. Independently verified CI / media control
- [Push preflight #39195300594](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/39195300594) **SUCCESS** on implementation HEAD `294b83d45a2d60bd6d66c9ba577bf0ef97f03212`: **32/32** new hostile tests, **48/48** V3-91/V3-64 regression tests = **80/80 PASS**. V2 Core Freeze PASS, V3 benchmark prereg PASS. Full offline original two HOST_TEST_ONLY 1280×720 native H264/AAC videos rendered/decoded. These are **NOT** model-created videos.
- [PR preflight #39195323116](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/39195323116): **SUCCESS**, same original implementation commit and native control.
- Unique live trigger commit `30874c7472408a2166f5579222119ed27adc618e`, file `research/V392_SINGLE_FREE_MODEL_TRIGGER.txt`, satisfying parent-full-CI gate.

## 4. One genuine model inference: NO-GO with exact completion evidence
[Live run #39195510885](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/39195510885) finished **FAIL**, deliberately fail-closed. Original first-party [artifact #12161807457](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/39195510885/artifacts/12161807457), ZIP SHA256 `e3a453a0b90efb2ad5a2319002d24a153356452387f095ce55444e602c958bb1`, was actually downloaded and inspected. Only one file `v392_attempt.json`; no accepted candidate JSON and no MP4.

| First-party receipt property | Observed value |
| --- | --- |
| `provider_post_attempts` | **1** |
| `router` | `openrouter/free` |
| `public_zero_price_catalog` | `PASS` |
| `actual_model` | **`nvidia/nemotron-3-ultra-550b-a55b:free`** |
| `finish_reason` / `native_finish_reason` | **`length` / `length`** |
| `prompt_tokens` | **421** |
| `completion_tokens` | **2500** (equal to prereg output ceiling) |
| `total_tokens` | **2921** |
| `reported_cost` | **ZERO** (provider returned 0) |
| `response_id_sha256` | `e3b6d77232134664f196f02c27e7e2deff54e9f2ae1433447122993f07a04547` |
| `request_sha256` | `6d9a1168781b04b25405a7bb4a4a155a72ac5ed4467f258be60d4e3ec67c0bb3` |
| `result` | `MODEL_COMPLETION_REJECTED_NO_RETRY` |
| `reason` | `V392_FINISH_REASON_NOT_STOP` |
| `retry_count` / `paid_fallbacks` | **0 / 0** |
| `model_storyboard` / `native_video` | **NOT_ACCEPTED / NOT_RUN** |
| `learner_quality` / `learner_gain` | **UNRATED / NOT_MEASURED** |
| `quality_3b1b` / `production` | **NOT_PROVEN / BLOCKED** |

**Root cause at the observable protocol level is now identified:** the routed free model returned a `length` finish and consumed exactly the available 2,500 completion tokens. Since raw rejected output is purposefully not stored, **do not guess** whether those tokens went toward hidden reasoning, excessively long text, provider transformations, or other details. This cannot be treated as a complete storyboard or as AI-to-video technical success. Do not rerun this trigger or send another model inference without a separate preregistered protocol and user approval.

## 5. Deadline release boundary / next scientific design
- Keep [V3-90 Draft PR #127](https://github.com/wterrr/vibecode_challenge_mb/pull/127) as the verified **bounded host-grounded query-to-real-MP4 technical demo** for October 21. It remains not fully autonomous AI.
- For a distinct future trial, preregister a free model with verified JSON instruction following and complete output under a **smaller storyboard representation** or controllable reasoning budget; independently confirm actual model routing and zero cost. Evaluate unmodified native frames and blinded human clarity, after external source integrity tests. Do **not** retry V3-92 automatically.
- Existing original host native media does not count as real-model-authored educational MP4. No success label from offline mock, CI green alone, or human rubric lacking actual reviewers.

**Final verdict: OFFLINE 80/80 PASS · ORIGINAL NATIVE HOST CONTROL PASS · REAL FREE MODEL CALLED ONCE · FREE MODEL RESPONSE LENGTH-CAPPED · MODEL AUTHORED VIDEO NO-GO · HUMAN QUALITY PENDING · PRODUCTION BLOCKED.**
