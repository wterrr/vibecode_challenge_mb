# V3-02 — Canonical Semantic Contracts: implementation, audit and acceptance

**Decision:** **PASS — typed cross-artifact offline contract**, pending stacked PR review. This is NOT approval of a semantic renderer, not a traced-algorithm oracle, not evidence of human video quality, and not authorization to merge main.

**Code base:** `1856ccdd6b6337f654b78ad7da73055dd8780790` (PR #34 head, V3-01 prereg). **Verified implementation:** `e5acf5534f79548d3598d45dc02776828bb6a16b`. **Branch:** `chatgpt/v3-02-canonical-semantic-contracts`. `main` is still `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6` at checkpoint. The V3-02 PR must target `chatgpt/v3-01-benchmark-preregistration` while #34 is unmerged.

## 1. Audit/reuse-first decisions

| Component | Actual existing implementation | Choice |
| --- | --- | --- |
| Canonical concept IDs, normalized aliases and collision detection | `learnflow_v2/concepts/schema.py`, `registry.py`, `normalize.py` | **REUSE** V2 directly; never normalize a V3 `concept_ref` to guess an identity |
| Scene semantic nodes, topology, referenced identity | `learnflow_v2/scenegraph/schema.py`, `validation.py` | **REUSE**; all graph checks delegated to accepted V2 |
| Script/storyboard refs and sequence | `agent_contracts/base.py`, `lesson.py` | **REUSE** strict IDs and `Storyboard.validate_against_script` |
| Visual Director scene-concept coverage | `visual_director/gate.py` | **ADAPT** identical cross-artifact invariants in V3 bundle, without modifying existing gate |
| Worked example 16 ↔ 24 drift | `live_evaluation/semantic_consistency.py` | **REUSE** narrow numeric search example detection; regression demonstrates rejection |
| State JSON-safety / nonfinite payload protection | `learnflow_v2/core/jsonsafe.py` | **REUSE** validator; extra V3 top-level pixel key prohibition |
| V3 section/beat, pattern and verified state source | Not provided by V2 APIs | **NEW minimal wrapper** under `learnflow_v3/` only |
| Code2Video / ALGOGEN / Manim upstream | Reuse inventory in `reports/v3_00_reuse_inventory.json` | **NO COPY**: not needed for data-only semantic contracts; ALGOGEN code license still unverified |

## 2. New contract/ownership

- `learnflow_v3/models.py`: versioned `3.0` `VisualTeachingPlan`, `VisualPatternSpec`, `StateLedger`; Pydantic `extra=forbid`, immutable model interface, allowed enum values, deterministic canonical JSON and SHA-256. Coercion of legitimate JSON enum *strings* is permitted, but unsupported values/keys fail. Budget is integer-strict.
- `learnflow_v3/validation.py`: `validate_semantic_bundle(...)` validates objectives, exact canonical `concept_id + canonical_key`, script segment/claim ownership, all pattern source references, scene/storyboard/SceneGraph agreement, ledger object and beat coverage, strict order and a trace source ref declared in the caller's verified-trace set. The caller must provide trace proof independently; this validator doesn't compute/validate algorithm traces.
- `tests/v3/test_contracts.py`: positive roundtrip/canonical-hash tests and negative/mutation tests: unknown schema, injected renderer key, unknown enum, dangling section, duplicate step, non-finite/pixel state, invalid source namespace, unverified trace, orphan script/claim/objective, mismatched key/node/scene and reproduced registry 16 ↔ script 24 drift.
- `.github/workflows/v3-canonical-contracts.yml`: offline-only run; existing pip dependencies, V3 tests + V2 concept/scenegraph/agent/semantic tests + V3-01 prereg/LearnFlowBench/Core Freeze. No API secret, no model probe, no renderer job.

**Security/integrity bounds:** data-only Pydantic contracts, no dynamic imports/eval/generated Python/no renderer geometry. A frozen Pydantic model may still contain mutable nested `dict/list` contents, so `frozen=True` is not a cryptographic seal; canonical hash is available for provenance. V3-03 must detect *consumer-level ignored fields* and source→render dependency invalidation. Ledger beat states are declared, not physical visual evidence. An asserted caller trace proof set alone is insufficient to certify correctness of any generated trace: V3-05 must implement a concrete oracle. V2 numeric validator intentionally doesn't cover general spoken semantics or arbitrary formulas.

## 3. Measured verification on implementation commit

[GitHub Actions #37730308809](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37730308809) — **SUCCESS**, exact implementation commit `e5acf5534f79548d3598d45dc02776828bb6a16b`.

```text
20 passed     # new V3 semantic-contract tests
36 passed     # V2 ConceptRegistry + SceneGraph tests
58 passed     # existing agent contracts, Visual Director, numeric drift tests
V3_BENCHMARK_PREREG=PASS topics=12 domains=6 easy=4 medium=4 hard=4
LEARNFLOW_BENCH_CONTRACT=PASS
CORE_FREEZE=PASS
```

Commands:

```bash
python -m pytest -q --confcutdir=tests/v3 tests/v3/test_contracts.py
python -m pytest -q --confcutdir=tests/v2 tests/v2/test_concept_registry.py tests/v2/test_scenegraph_schema.py tests/v2/test_scenegraph_validation.py
python -m pytest -q --confcutdir=tests/hermes tests/hermes/test_agent_contracts.py tests/hermes/test_visual_director.py tests/hermes/test_final_v2_semantic_consistency.py
python scripts/verify_v3_benchmark_protocol.py
python scripts/verify_learnflow_bench.py
python scripts/verify_v2_core_freeze.py
```

## 4. Gate and rollback

- Frozen `learnflow_v2/**`, original LearnFlowBench `corpus_v1.json`, V1 rollback, default free-provider config, and #181 artifacts unchanged.
- This checkpoint **did not implement** V3-03 signal-preservation, V3-05 trace oracle, V3-06 stateful renderer or any model/prompt orchestration; **zero paid/free provider calls**.
- If the PR is rejected, close/revert this V3-02 branch; V3-01 PR #34 remains intact. Do NOT merge `main` until PR #34 is accepted first and current diff/rebased dependencies are reviewed separately.
- Remaining reviewer attack: `Schema valid` ≠ `semantic truth` ≠ `trace proof` ≠ `rendered visual agreement`. The exact latter claims remain UNMEASURED.

**Next one checkpoint:** **V3-03 — Signal-Preservation Proof**: prove referenced semantic fields are *consumed* by downstream artifact adapters and mutations change dependent hashes or fail before render, with no V2 Core modifications. Requires separate authorization.
