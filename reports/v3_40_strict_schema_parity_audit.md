# V3-40 — Strict Schema Contract Parity & Offline Validation Audit

**Scope:** OFFLINE ONLY. Stack on Draft PR #73 HEAD `f5dd06a`. Do not merge main. Preregistered before implementation at `89ac3da`, immutable registration at `benchmarks/learnflowbench/v3/v3_40_strict_schema_parity_preregister.json`. **Zero** model inference POST, no authenticated provider GET, no new live trial, no fallback/retry, no production inference.

## Frozen empirical motivation

V3-39 [Actions #38022202376](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38022202376) consumed one GPT-6 Luna POST, received real model content SHA `ca4b439ee25a6db305ceccf52532544678b015aff2668a3bbb2f155b6e3f9d0e`, but failed `V335_PYDANTIC_SEMANTIC_REJECT`: `objects.0.height` and `objects.1.height` > 2.4; `beats.0.claim_ids` length < 1. Historical `strict_wire_schema()` only encoded `height` as `number`, `claim_ids` as unrestricted `array`. Do not reconstruct discarded private model content or transform historical failures into PASS. No model-authored MP4 exists.

## Design / verifiable invariants

- **Single live host-contract source:** `CreativeScene.model_json_schema()`, including nested `Graphic`, `Motion`, `LectureBeat`. New `learnflow_v3.strict_schema_parity_audit` derives a **separate candidate** strict schema by projecting min/max for numbers, length bounds for strings/arrays, regex patterns and identical enums from Pydantic onto a deepcopy of the old strictly required transport schema.
- **No duplicated numeric policy:** code never hardcodes the 2.4 / 1 bounds; the numbers originate from the host Pydantic model. Contract drift (types, fields, enums, boundaries) raises `V340_*`, never relaxes host semantics.
- **V3-39 protected:** historical `learnflow_v3.structured_scene_authoring.strict_wire_schema()` and `one_shot_structured()` unchanged. No request dispatch points to candidate, so no accidental new provider schema live deployment.
- **Transport/host intentional difference:** the live wire requires `target,x,y` for *all* actions and `model_author` is never model-controlled. Existing `normalize_wire` only removes unused placeholders after checking exact 0 / empty values; host sets `model_author` from provider provenance.
- **Bounded JSON Schema parity is not full semantic parity:** conditional graphics, reserved Python identifiers, numeric-fact allowlist, motion sequencing/identity, unique object IDs, evidence-grounded claims, minimum spoken words and verified fact coverage remain **host-only fail-closed** checks. A locally valid candidate-schema JSON may still be rejected by the host. That is intended and tested, not a violation swept away by repair.
- **Provider compatibility remains NOT CERTIFIED:** offline Draft 2020-12 JSON Schema success proves only local schema correctness and expressible-bound parity; it does not authenticate that all OpenRouter downstream endpoints honor `maximum`, `minItems`, `pattern` or native strict mode. No key/POST to test provider. OpenRouter explicitly warns enforcement can vary by endpoint.
- **Frozen acceptance:** preregistration, V3-35/36/37/38/39 regressions, frozen V3-33 unseen and V2 Core and synthetic Manim host-only provenance rejection all stay separate from real model-output evidence.

## Offline evidence protocol

```bash
python -m pip install -r requirements.txt 'jsonschema>=4.21,<5'
python -m pytest -q --confcutdir=tests/v3 tests/v3/test_v3_40_strict_schema_parity.py tests/v3/test_v3_39_compatible_creative_trial.py tests/v3/test_v3_35_structured_scene.py
python -m learnflow_v3.strict_schema_parity_audit --output-dir /tmp/v3_40_schema_audit
```

The dedicated `.github/workflows/v3-40-strict-schema-parity-audit.yml` runs the full offline suite plus frozen benchmarks and synthetic-video anti-provenance gate. Artifacts contain only the local candidate and constraint inventory; no model text, live usage data or secrets.

## Verified offline CI result — 2026-10-10

Implementation code HEAD `579044c`, dedicated offline GitHub Actions [#38023920124](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38023920124) **SUCCESS**: 129/129 candidate-parity + V3-34–V3-39 regression tests PASS; frozen V3-32/33, benchmark and V2 Core gates PASS; native Computer Modern/bootstrap and real Docker Manim host-only fixture PASS, synthetic-as-model evidence REJECTED; [non-model artifact #11660161094](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38023920124/artifacts/11660161094) emitted schema candidate/inventory. Earlier CI failures were (1) overbroad string assertion against an *offline* legacy test filename (128 pass/1 fail) and (2) missing CMU font before frozen tests (129 pass, frozen test environment failure); both repaired without modifying model/prompt, Pydantic safety, historical wire or paid inference. **0 inference POST** throughout V3-40. This is OFFLINE wire-expressible parity PASS only, not provider-endpoint strict support, not full cross-field equivalence, and no new model-origin MP4 or pedagogical PASS.

**Final documentation-only commit requires separately verified same-HEAD CI.** Even after offline PASS, production, six-domain educational quality and genuine model-generated MP4 remain BLOCKED; further paid trial is a separately preregistered, explicitly authorized checkpoint. V3-39 is permanently consumed.
