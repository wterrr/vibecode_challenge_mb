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
