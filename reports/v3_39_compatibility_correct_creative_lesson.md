# V3-39 — Compatibility-correct GPT-6 Luna strict creative Manim lesson

**Preregistered before implementation:** `3350f9f909cc1575d352196c7502aab81dcb475f`. Child of V3-38 Draft PR #72 at `e5b0b4fb5cf8bc1e82be428c368ab5e947a54c1e`. Not main.

## Causal hypothesis / intervention

[V3-37 live Actions #38017323094](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38017323094) consumed its separately registered single model HTTP POST, which returned `V335_HTTP_404`, with no response or MP4. [V3-38 real key GET #38019407661](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38019407661) **SUCCESS**: inference key HTTP200, per-key remaining limit positive but account credits and individual model entitlement NOT certified. Live public GPT-6 Luna endpoint catalog `https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints` currently contains seven endpoints; all advertise structured outputs; **0/7 advertise `temperature`**, four advertise `max_tokens`, three advertise `max_completion_tokens`. OpenRouter [parameter routing guide](https://openrouter.ai/blog/insights/model-routing/) states `provider.require_parameters=true` filters out endpoints that cannot support each request field. Thus V3-37's `temperature=.65` appears to make the request unrouteable. This is a falsifiable, high-confidence **causal hypothesis** but not authenticated historical error-body proof.

**Exactly ONE separately registered parameter difference:** V3-39 removes top-level `temperature` entirely; retains `openai/gpt-6-luna`, `max_tokens=6500`, same messages, exact V3-35 strict JSON Schema, `provider.require_parameters=true`, `provider.allow_fallbacks=false`, same lfb-018-math exposed topic, zero retries, one POST maximum. Earlier modes and preregs untouched. For unchanged old POST, no response, so it cannot retroactively become PASS.

## Code / run gate

- `learnflow_v3.structured_scene_authoring.one_shot_structured(...,omit_temperature=True)` is separately explicit; `False` retains unchanged V3-35/V3-37 path.
- `learnflow_v3.creative_manim_runner.run(...,mode='live-structured-no-temperature')` reuses same checked manifest, validated scene, audio/Manim renderer and actual-source proof.
- `learnflow_v3.compatible_creative_trial.one_trial` verifies frozen V3-39 prereg, makes a **single public GET** to assert 0 candidates for temperature-bearing historic request but at least 1 for no-temperature plus max_tokens schema flags, then permits one model POST on the dedicated opt-in job only. Public GET alone cannot certify authenticated strict mode or route entitlement.
- Tests `tests/v3/test_v3_39_compatible_creative_trial.py` assert the literal wire difference, default-mode legacy preservation, schema/fallback unchanged, mock negative cases and fake fixture rejection. Tests use mock senders with HTTPError, **no paid provider calls**.
- Workflow `.github/workflows/v3-39-compatible-creative-trial.yml` runs same-HEAD frozen tests, full native H264/AAC synthetic HOST fixture, mandatory synthetic-as-model rejection, pinned Manim Docker, and separate public GET (no key). **Only one unique push commit** `[v3-39-single-compatible-model-post]` after green offline CI may run the paid job. `github.run_attempt == 1`, no PR or ordinary push paid POST, no automatic retry/fallback. Fail-closed artifacts after one attempt.

## Evaluation limits / stop rules

- If exact new request returns HTTP 404, reject unsupported-temperature-as-sole-root-cause hypothesis, stop and record one paid attempt. No retries.
- If model returns strict JSON but scene validator or Manim fails, classify independently as model-schema/semantic/render failure; do not silently rewrite the scene or substitute a host fixture.
- Genuine technical PASS requires actual model response SHA, real validated scene, actual host-generated Manim replay, H264/AAC decoded video SHA and artifact verification. Even technical PASS is **NOT** evidence of pedagogical value, creative superiority, independent external sourcing, six-domain generalization or production readiness.
- V3-16/V3-33 frozen evaluation and V2 Core unchanged. Topic exposed before V3-39, so not unseen.
- Inference budget **0 consumed for V3-39** as of this report, readiness CI PENDING, no live MP4. One new POST only after explicit separately tagged opt-in and green exact-HEAD offline CI. Production BLOCKED.

## User-authorized V3-39 one-shot live activation — 2026-10-10

**Exact code HEAD verified immediately before authorization:** `de02f1a40b9f2d9e196b8747bdf59f87055fef7a`. [Push offline #38021430418](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38021430418) and [PR offline #38021434574](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38021434574) both **SUCCESS** on the same code HEAD, including 103+ regression tests, frozen V3/V2 benchmarks, actual pinned Docker Manim HOST fixture H264/AAC and required rejection of synthetic-as-model provenance. The user explicitly requested executing the next one-shot GPT-6 Luna real-model experiment. V3-39 is independently preregistered at `3350f9f` and has **0 prior provider inference POSTs**.

**This is the uniquely authorized tagged activation commit**, with commit-message marker `[v3-39-single-compatible-model-post]` exactly once. GitHub Actions must run the same-HEAD offline suite again before the secret-bearing job. Only on a new push, `github.run_attempt==1`, must the model job send at most **one** POST. The sole experimental change is omission of `temperature` from the old V3-37 strict request; `max_tokens=6500`, `provider.require_parameters=true`, strict JSON Schema, `allow_fallbacks=false`, original topic/grounded facts, no retries unchanged. **Never rerun/tag another paid attempt if HTTP/error/render failure occurs.** No merge to main; no production or educational quality certification implied. Keep synthetic fixtures separate from genuine model evidence.

**Live outcome:** NOT YET VERIFIED at activation commit. Must update only after inspecting actual run/job/artefacts. This is a new independent preregistered trial, **not a retry of V3-37**.

## Verified one-shot result — actual GPT-6 Luna response, semantic NO-GO (2026-10-10)

**STOP: the one allowed V3-39 model inference attempt has been consumed. Never retrigger this commit, re-run the workflow, switch model silently or replay POST.**

Unique opt-in tagged **commit `c4f15e2f4615f5b44f349db2af7be669aada089f`**, [push Actions #38022202376](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38022202376):
- The **same-HEAD offline gate SUCCESS**, including V3/V2 frozen benchmarks, real Docker Manim **host-only** MP4 fixture and anti-synthetic provenance check.
- The dependent `unique-preregistered-no-temperature-model-post` executed exactly once and **FAILED** at `Public GET preflight then EXACTLY ONE no-temperature GPT-6 Luna POST`. Log ended `V3_39=BLOCKED V335_SCENE_REJECTED`.
- [PR CI #38022205821](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38022205821) **SUCCESS** in its offline job; as designed, the PR event **SKIPPED** the inference job. No other authorized V3-39 POST.
- Retrieved and read the **actual** [sanitized real-model artifact #11657964290](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38022202376/artifacts/11657964290), containing exactly `v3_35_request_attempt.json`, `v3_39_failure.json`, `v3_35_structured_failure.json`. No MP4, plan, real rendered frames, or provider raw text in the artifact.
- Request receipt: `model=openai/gpt-6-luna`, `attempted_http_requests=1`, `response_format=json_schema_strict`, `provider_require_parameters=true`, `provider_fallback=false`, `retries=0`, **`temperature_parameter_sent=false`**. This was the sole preregistered changed parameter from V3-37.
- Provider returned **real content** (not an HTTP 404): stage `BLOCKED_AFTER_REAL_MODEL_RESPONSE`, `model_response_sha256=ca4b439ee25a6db305ceccf52532544678b015aff2668a3bbb2f155b6e3f9d0e`, **Pydantic semantic reject** `V335_PYDANTIC_SEMANTIC_REJECT`.
- Exactly **three sanitized validation errors**: `objects.0.height` (`less_than_equal`), `objects.1.height` (`less_than_equal`), `beats.0.claim_ids` (`too_short`). Inspection of existing `creative_manim_ablation.Graphic.height` confirms `le=2.4`; `LectureBeat.claim_ids` confirms `min_length=1`.
- Provider-reported usage: **1,644 prompt tokens**, **3,771 completion tokens** (including 2,153 reasoning tokens), **5,415 total tokens**, provider-reported **cost 0.00207001575 USD**. This is actual provider receipt, not a projected price. Model response text and exact invalid values were not persisted, so do NOT invent them.

### Postmortem — wire-schema vs semantic validator contract mismatch

The existing `strict_wire_schema()` advertises `Graphic.height` as a plain JSON Schema `number` with only descriptive prose; it contains no enforceable `maximum:2.4`. Likewise, `beat.claim_ids` is an `array` with enum items but no enforceable `minItems:1`. Conversely, Pydantic's `Graphic.height=Field(...,le=2.4)` and `LectureBeat.claim_ids=Field(min_length=1)` reject the model's values. Strict JSON **transport/schema enforcement** therefore does not establish downstream semantic validity. The separate JSON/schema and deterministic Python checker worked as designed, preventing an invalid scene from reaching Manim or being mislabeled creative PASS. **Do not bypass validators, clamp dimensions, inject missing claims or retroactively repair this result.**

**Scientific conclusion:** removing unsupported `temperature` enabled one GPT-6 Luna response and did not reproduce HTTP 404. It supports—but does not fully prove—the earlier provider-routing hypothesis. V3-39 achieved **real model response provenance**, but **failed validated scene**, thus **NO model-authored MP4**, **NO pedagogical evaluation**, **NO production readiness**. The one model trial is consumed and closed as `NO-GO: WIRE/SEMANTIC CONTRACT PARITY`; further live work requires a distinct preregistered checkpoint, offline validation of provider-compatible `minimum/maximum/minItems` constraints or other guarded architecture, and new explicit authorization. Existing frozen six-domain results remain unchanged.
