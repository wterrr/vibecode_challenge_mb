# V3-95 — New-Prompt → Genuine GPT → Grounded Native MP4: Product Bridge (Local Developer Preview)

Date: 2026-10-19. Deadline: 2026-10-21. Parent: Draft V3-94 PR #131 frozen HEAD `f738946cb97fdbc3930eb0a1eca6ebe255a0df4f`. First prereg before code: `e6f985a92fe6ef6ef31353f27cfa7727294f3dea`. Child Draft PR #132, stacked; do **not** merge `main`.

## Why this exists

The first real GPT-6 Luna authored V3-93 storyboard and independently repaired V3-94 video prove the underlying components, but V3-94 replays an **already generated JSON** rather than accepting a fresh user's question and calling GPT. The regular `/api/jobs` user flow, meanwhile, still uses the older Gemini/V2 real-video pipeline. Renaming its outputs as GPT-generated would be scientifically false.

V3-95 creates a **real, opt-in, local product interface** without lying about either limitation. It **does not silently overwrite the ordinary `/api/jobs` route**.

## Actual integration

`/create` exposes an additional *separately labeled* developer form **only when explicitly enabled**. Operator enters a fresh English question in the fixed verified semantic family: 3×4 vs 4×3 square arrays preserving exactly 12 objects, and checks a paid-inference consent checkbox.

`POST /api/v3/ai/array-preview` validates the supported *mathematical intent before account/key lookup*. It is disabled by default; only test/development environments and loopback/TestClient requests are accepted. The existing production API/runner is unaffected. Via the existing `V3OfflinePreviewPipeline` wrapper and local ArtifactStore, the request goes through:

```
new human English question
  → bound-topic semantic admission (other domains ABSTAIN, zero provider POSTs)
  → explicit paid consent + single GPT attempt per running process
  → public catalog model capability/pricing + authenticated key GET
  → strict OpenRouter GPT-6 Luna JSON request, 16,000 output max,
    low reasoning, OpenAI-standard pinned, no fallback/retry
  → verify actual model, provider response id, finish=stop, usage/cost
  → host-validated five-stage novel storyboard (never canned JSON)
  → twelve persistent squares + trusted proof/reveal timing
  → V3-94 corrected rigid geometric render and per-frame collision QA
  → FFmpeg H264/AAC + offline eSpeak narration; native full decode+SHA
  → private local GET video only after successful verified receipt
```

A paid attempt is reserved before transport; failures are not silently retried. **A process restart or multiple replicas could reset the single-process allowance**: this is NOT an account-wide monetary cap or production billing control. The one-post pessimistic token estimate is constrained to $0.01 using the current public model price and actual new-request byte count. Charges ultimately depend on provider billing.

The video endpoint is a local temporary, **non-public** preview URL: `GET /api/v3/ai/array-preview/{preview_id}/video`. Video IDs are random; only a successful SHA-verified private preview can be served. No `ArtifactStore.publish_final`, no production `final.mp4`, no permanent `JobStatus.SUCCEEDED`.

## Local developer run

Prerequisites: Python dependencies from `requirements.txt`, FFmpeg, `espeak-ng` or `espeak`, an existing OpenRouter key supporting OpenAI's `openai/gpt-6-luna` and sufficient purchased credits; no API credential must be committed.

```bash
export LEARNFLOW_PIPELINE_MODE=demo  # keeps legacy /api/jobs separate
export LEARNFLOW_V3_GPT_ARRAY_PREVIEW=true
export ENVIRONMENT=development
export OPENROUTER_API_KEY='<your-private-key>'
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000/create`. Enter, for example:

> Can a grid of squares measuring 3x4 be rotated to 4x3 and preserve all 12 pieces?

Check the **explicit paid-consent checkbox** and submit the lower GPT developer-preview form. If the real model yields a host-admissible narrative/visual plan, a playable temporary MP4 will appear. Other domains (attention, binary search, photosynthesis, history) must ABSTAIN without calling the model. Some legitimate paraphrases may also ABSTAIN because the narrow semantic admission has an explicit positive English vocabulary.

Alternatively (same local-only guard):

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v3/ai/array-preview \
  -H 'Content-Type: application/json' \
  -d '{"query":"Why does a 3 by 4 array contain the same squares as a 4 by 3 array?","language":"en","paid_consent":true}'
```

**Never enable this flag on publicly reachable or production servers**. An HTTP request may take time while FFmpeg builds a video; this is a developer-preview synchronous endpoint, **not** a scalable, durable background job system. Client cancellation does not guarantee the remote inference is unbilled. No unrestricted production API exposure is claimed.

## Verification and honest acceptance

The dedicated [V3-95 offline CI workflow](https://github.com/wterrr/vibecode_challenge_mb/actions/workflows/v3-95-product-gpt-preview-offline.yml) (not a live paid test) performs:
- Input admission/ABSTAIN, no-cost prechecks, malicious word/prompt tests, price drift, exact model identity/finish/retry controls.
- FastAPI dev-route disabled/consent checks and process-one-attempt behavior, old V2 pipeline unaffected.
- Source validation, V3-94 temporal/collision tests and original GPT model test regressions.
- A **fresh allowed question** passed through the *actual dynamic GPT request formatter* with the provider transport replaced by a **clearly marked MOCK**. All speech/video production is genuine H264/AAC FFmpeg, verified by decoded frames and SHA. It must remain labeled `MOCK_TO_NATIVE_TECHNICAL_PASS_NOT_REAL_AI`; this is NOT another real GPT request.

**Acceptance truth labels:** `NEW LIVE GPT GENERATION VIA DEV API` is implemented, **but a user-consented live run from this route has NOT been executed or independently accepted** in V3-95. The prior V3-93 paid GPT → native validation remains separate evidence. Novel-domain generalization: **NOT PROVEN**. Human pedagogy: **0 independent reviewers, UNRATED**. Learner gains: **NOT MEASURED**. Production rollout: **BLOCKED**. The major remaining work beyond this scoped preview is a reusable multi-domain source verifier and specialized renderers, durable billing/job state, plus genuine independent blind lesson-quality reviews.

## Scientific QA checklist for an independent reviewer

Review the actual rendered lesson in normal playback and at 11.7s/13.6s/22s. Rate comprehensibility, correspondence between spoken claim and moving squares, consistency of 12 object identities, title/label legibility, screen rhythm, educational explanation and voice naturalness. Compare the V3-94 GPT-backed film with its true source-host baseline under blind video labels; do not conflate an easier/different narration track with improved pedagogy. No reviewer scores are fabricated. Do not use `CI SUCCESS` as a replacement for a human acceptance verdict.

## Current source milestone

Core V3-95 code: `learnflow_v3/v395_prompt_to_video.py`, `app/api/v3_ai.py`, `app/pipeline/v3_preview.py`, `app/pipeline/factory.py`, `app/config.py`, `app/main.py`, `app/templates/create.html`, `app/static/js/app.js`, `tests/v3/test_v3_95_live_gpt_prompt_bridge.py`, `scripts/run_v3_95_offline_product_smoke.py`.

*CI state must be verified from current GitHub Actions before claiming a PASS. No new paid model API call was sent during this checkpoint. No main merge.*
