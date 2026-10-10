# V3-36 — Provider Compatibility & Genuine Creative Scene Readiness

**Stack:** Draft PR from V3-35 PR #69 (`c9752e2af516693330d437a59190b7412b0fc5bf`), never merge main.  
**Independent preregistration:** commit `638d1fa8add4cb2e4c7fcec1ba9d13107401148c` precedes code, locks `lfb-018-math`, `openai/gpt-6-luna`, and **0 authorized inference POSTs**. This checkpoint is an offline readiness/negative-evidence milestone, NOT a repeat of consumed V3-35.

## Starting facts (real, not synthetic)

- V3-34 `#37907978564`: model response reached strict Pydantic gate but raised `ValidationError`, no genuine model MP4.
- V3-35 `#37911556743`: one strict schema POST returned HTTP 404, no model response/MP4. Endpoint root cause **UNDETERMINED**.
- V3-35 final prior HEAD `c9752e2` offline CI `#37914638188` (push) and `#37914646697` (PR) **SUCCESS**, real Docker synthetic Manim H264/AAC fixture, NO inference.
- Public unauthenticated catalog advertises endpoint structured output support, but cannot establish key/account/region/schema-level capability or retrospectively explain 404. Source: https://openrouter.ai/docs/guides/features/structured-outputs.

## Found during V3-36 audit: two actual implementation bugs

1. `creative_manim_runner.run(mode="live-structured")` wrongly labeled `manim_source_origin` `HOST_FIXTURE_FROM_HOST_PRIMITIVE_DATA`. A future true model MP4 could have been misclassified. Fixed so both true live modes say `HOST_COMPILED_FROM_MODEL_PRIMITIVE_DATA`, offline remains synthetic. Also corrects the technical-success label for legacy live model.
2. `scripts/run_v3_34_ablation.py` collapsed `V335_HTTP_404` and other safe V335 codes to `V334_VALIDATION_OR_RUNTIME_BLOCKED`. Fixed strict bounded error code preservation in sanitized CLI failure receipt; no raw exception, body, prompt or secret disclosure.

## New bounded evidence gate

`learnflow_v3/creative_evidence_gate.py` is read-only and zero-inference. It requires:
- exact V3-35 real model provenance, one provider request, strict schema SHA and response SHA, no fallback/retry; `model_author` match;
- source/plan/video SHA checks on physically present files, SRT and four non-silent sampled audio beats, non-static decoded-source evidence;
- real `ffprobe` on actual MP4 bytes, 1280×720 H264/AAC and matching native frame count; `ffprobe` cannot be faked by CI production invocation;
- network-none/read-only Docker and no model Python executed or secrets mounted;
- `human_blinded_educational_quality=NOT_ASSESSED`, creative superiority unproven and production BLOCKED.

The unit suite injects **explicit mock** provider and fake `ffprobe` objects to test this contract and adversarial mutations. Those tests **never count as real model/video evidence**. CI also renders a real synthetic HOST Manim video and the production CLI must reject it with `NOT_REAL_MODEL_SCENE`.

## Boundaries / scientific decision

- **Zero paid POST, zero GPT-6 request** authorized or made by V3-36. No workflow job receives `OPENROUTER_API_KEY`. Public catalog GET is optional and advisory.
- Freeze untouched V3-16 12 confirmatory topics, V3-33 six unseen ABSTAIN results, V2 Core and prior one-shot receipts. No CONCEPT_CARD fallback, topic substitution, independent learner ratings, or release.
- Candidate human teaching superiority, six-domain generalization, commercial rights **NOT PROVEN**.
- **Offline engineering readiness:** PENDING exact code-head CI and actual synthetic rejection artifact.
- **New genuine model-directed MP4:** NOT_RUN / NO-GO until a separately user-approved, preregistered fresh one-shot, with real provenance and independent visual inspection.
- **Production:** BLOCKED.

## CI and artifacts

To append after first exact-head workflow. The V3-36 no-inference CI runs mock negative tests, inherited schema regressions, frozen benchmark/Core, real Docker/Manim H264/AAC smoke and mandatory synthetic rejection. It is **NOT a live-model experiment**.
