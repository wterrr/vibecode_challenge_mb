# V3-03 — Signal-Preservation Proof, invalidation and dead-signal disclosure

**Date:** 2026-10-08  
**Decision:** **PASS (bounded typed semantic-gate audit and regression only)**; no renderer, no pixel/animation proof and no automatic publish permission.  
**Implementation CI:** [#37731881901](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37731881901), code commit `d9ac97020b83734e3095d36b4619c34e471e2aef` — SUCCESS.

## 1. Exact boundary and reuse-first audit

- Parent: PR [#35](https://github.com/wterrr/vibecode_challenge_mb/pull/35), code head `d972645e2ea39cb83cac6fb2203aa5f99ec9bbde`. Its parent [#34](https://github.com/wterrr/vibecode_challenge_mb/pull/34) and V3-02 remain unmerged. A V3-03 PR must target the `chatgpt/v3-02-canonical-semantic-contracts` branch, **not main**, until dependencies are integrated and reviewed.
- Baseline `main`: `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6`; frozen `learnflow_v2/**`, original 100-topic LearnFlowBench corpus, original V1 rollback, model config and Action #181 retained.
- Existing **`learnflow_v2/repair/artifacts.py`**: deterministic `compute_content_hash`; `ArtifactIndex` checks input hashes, cycles, stale dependencies; `downstream_closure` computes recursive invalidation. Existing **`lesson_pipeline/artifacts.py`**: hash-manifest writer. Existing **V3-02 `validate_semantic_bundle`**: exact concept refs and cross-stage semantic constraints.
- **REUSE:** `compute_content_hash` and V3-02 semantic bundle validator directly; align with V2's dependency/invalidation semantics. **DO NOT VENDOR:** the frozen `ArtifactKind` enum is V2-only, so a V3 semantic-audit/ledger should not be falsely recorded as `SCENE_GRAPH`/V2-render artifact to reuse `ArtifactIndex` mechanically. No external Code2Video/ALGOGEN/Manim code needed or copied.
- Implemented only `learnflow_v3/signal_preservation.py`, new `tests/v3/test_signal_preservation.py`, an offline-only CI workflow, updated canonical research notes/plan and this report. No V3 renderer, router, video job, API key, model inference, protected code or benchmark data.

## 2. A falsifiable field-consumption table, not a hash tautology

| V3 signal group | Current actual semantic consumer | V3-03 status | What happens on change |
| --- | --- | --- | --- |
| Objective IDs, section/beat refs, script segment/claim refs | V3-02 local schema and `validate_semantic_bundle` cross-refs | `SEMANTIC_GATED` | Valid coordinated rebinding changes gate + audit hash; invalid partial rebinding is rejected |
| Exact concept ID/key, pattern/scenegraph linkage | Frozen V2 registry/SceneGraph validation via V3-02 | `SEMANTIC_GATED` | Unknown/mismatched key rejected rather than guessed or silently remapped |
| Ordered beat and ledger object identities | V3-02 beat and ledger reference validator | `SEMANTIC_GATED` | Orphan/incorrect order rejected; consistent rename invalidates gate evidence |
| Trace source reference + caller-declared verified trace IDs | V3-02 trace-ref membership check | `SEMANTIC_GATED` **for reference agreement only** | Mismatched refs or absent declared ID rejected; any accepted ref/declaration change changes fingerprints; **does not certify trace truth** |
| Scene teaching goal, learner before/after, hero flag, pattern options, budget | **No actual pedagogy/router consumer in V3-03** | `DECLARED_UNCONSUMED` with named future owner | Audit/source hashes change, *semantic-gate hash does not*; render approval always denied |
| Visual pattern kind, fallback/renderer requirement, visual constraints | **No specialized renderer/router consumer** | `DECLARED_UNCONSUMED` | Explicitly disclosed; no claim of changed video geometry |
| Beat's intended visible state change and static exception text | **No beat-to-pixel binding consumer** | `DECLARED_UNCONSUMED` | Changing intent changes audit but not gate hash; render approval denied |
| Numeric state `ObjectState.properties` | **No stateful renderer consumer** | `DECLARED_UNCONSUMED` | State changes rehash audit, not gate; no false visual-change claim |
| Schema version and local ref uniqueness | V3.0 typed validator | `SEMANTIC_GATED` as structural proof only | Unknown version/IDs fail before stage acceptance |

The field catalog uses **exact normalized leaf paths**, not a broad wildcard that would silently approve a newly added schema field. Nested state dictionaries are audited as whole JSON values. If any new serialized leaf is missing a declared route, `UNDECLARED_SEMANTIC_SIGNAL` aborts. Caller can inspect per-field `SignalRoute(path, status, consumer, source_value_hash)` rather than inferring downstream consumption from a raw input hash.

**Two independent fingerprints:** `semantic_gate_hash` hashes *only explicitly gated leaves and upstream V2 reference hashes*; `audit_hash` records **every** leaf, declared future owner and all source input hashes. A mutation of deferred visual intent/state values **must** change the audit hash but does **not** masquerade as a new consumed gate signal. An active identity/reference mutation must change the gate hash or fail cross-artifact validation. Tests inject stale proof hashes to catch ignored invalidation.

**Render boundary is always fail-closed:** `SignalAudit.require_render_consumption()` rejects all deferred signals with `DEAD_SIGNAL_BLOCKED`; even a forged no-deferred record is rejected as `NO_RENDERER_CONSUMPTION_PROOF`. This method has *not* been wired into any new renderer since V3-03 expressly forbids implementation of one. All artifacts remain offline declarations only; no permission to release.

## 3. Exact measured CI

**[V3-03 Signal Preservation Offline #37731881901](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37731881901)** on `d9ac97020b83734e3095d36b4619c34e471e2aef`:

```text
39 passed   # V3-02 and V3-03 contracts/mutation tests
39 passed   # frozen V2 repair dependency/registry/scenegraph tests
28 passed   # existing agent/numeric semantic drift tests
V3_BENCHMARK_PREREG=PASS topics=12 domains=6 easy=4 medium=4 hard=4
LEARNFLOW_BENCH_CONTRACT=PASS
CORE_FREEZE=PASS
```

Replay:

```bash
python -m pytest -q --confcutdir=tests/v3 tests/v3/test_contracts.py tests/v3/test_signal_preservation.py
python -m pytest -q --confcutdir=tests/v2 tests/v2/test_repair_v2_13_contracts.py tests/v2/test_concept_registry.py tests/v2/test_scenegraph_validation.py
python -m pytest -q --confcutdir=tests/hermes tests/hermes/test_agent_contracts.py tests/hermes/test_final_v2_semantic_consistency.py
python scripts/verify_v3_benchmark_protocol.py
python scripts/verify_learnflow_bench.py
python scripts/verify_v2_core_freeze.py
```

**Mutation coverage:** known-valid deterministic repeat, deleted consumer registration, objective partial/complete rebinding, concept ID/key mismatch, beat rename/ledger rebinding, trace source change with and without declared verification, changed state values, visual intent and deferred pedagogy fields, Pydantic nested dict mutation, stale/forged gate and audit hashes, empty/no-delta rejection and render/production proof bypass rejection. Test suite doesn't claim random fuzz across all possible future field variants.

## 4. Attack surface, residual gaps and rollout boundary

- **Never claim:** "semantic hash changed → animation changed". `SEMANTIC_GATED` means validated upstream semantics only, not actual application by video compiler. The `compute_content_hash` reuse proves deterministic source fingerprinting, not semantic truth or pixel output.
- **Proof-set trust:** `verified_trace_refs` supplied by caller is just a set membership declaration. A concrete trace verifier and per-step physical/algorithm semantics are not implemented (V3-05).
- **Potential mutable nested JSON:** `frozen=True` from Pydantic doesn't deep-freeze `ObjectState.properties`; fresh hash compares catch mutations but no automatic runtime cache invalidation is wired. A broader consumer path across adapter/renderer is still missing.
- **Current validation limit:** V3-02 semantic gate is narrow on natural language and numerical worked examples; no independent study proving that all semantic meaning survives. Need V3-04/05/06/10 to build and test actual consumption, and only later claim visual quality.
- **No paid/free LLM runs**, V3-04/V3-05/V3-06 not implemented, `main` remains untouched, and this checkpoint is **not** a merge authorization.

**Decision:** V3-03 **PASS for explicitly declared semantic consumption coverage and fail-closed typed audit invalidation**, NOT for actual renderer signal preservation. PR review and parent integration are still prerequisites.

**Exactly one next checkpoint:** **V3-04 — Visual Pattern Router** *only after explicit authorization*, reusing existing visual types/gates and abstaining if no supported semantic pattern. V3-01 PR #34 and V3-02 PR #35 must be integrated safely before a main-based V3-04 rollout.
