# V3-05 — Binary Search Trace Adapter: independent algorithmic oracle

**Date:** 2026-10-08  
**Decision:** **PASS — offline typed trace/ledger correctness + source-binding; no render proof**.  
**Repository:** https://github.com/wterrr/vibecode_challenge_mb  
**Parent:** PR [#37](https://github.com/wterrr/vibecode_challenge_mb/pull/37), pinned HEAD `609a21217cae9e44a4fcec51dfb801b43a87e5cb`; upstream PRs [#34](https://github.com/wterrr/vibecode_challenge_mb/pull/34), [#35](https://github.com/wterrr/vibecode_challenge_mb/pull/35), [#36](https://github.com/wterrr/vibecode_challenge_mb/pull/36) all still pending.  
**Branch:** `chatgpt/v3-05-binary-search-trace-adapter`.  
**Verified code commit:** [`498e7f42f4411c66c9a95c8ac3515a5208af43dc`](https://github.com/wterrr/vibecode_challenge_mb/commit/498e7f42f4411c66c9a95c8ac3515a5208af43dc). `main` remains `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6`.

## 1. Reuse-first and licensing decisions

| Candidate | Reviewed function / area | Decision |
| --- | --- | --- |
| Existing V2 example checker | `live_evaluation/semantic_consistency.py::assert_semantic_consistency` + `SearchExample` parser | **REUSE upstream cross-artifact gate** through V3-02, but it does not verify an algorithmic state trace and cannot cover 0/1-element examples as written |
| V2 fingerprint / artifact logic | `learnflow_v2/repair::compute_content_hash` | **REUSE DIRECTLY** for byte-stable trace/provenance fingerprints; never mistake hash agreement for algorithm correctness |
| Python standard library | `bisect.bisect_left` | **REUSE DIRECTLY as independent oracle**, PSF/stdlib bundled with Python, no new pinned external dependency or license copying |
| V3-02 | `VisualPatternSpec`, `StateLedger`, `LedgerStep`, `ObjectState` | **REUSE** versioned typed semantics and exact pattern/beat/object identities |
| V3-03 | `audit_signal_preservation`, via V3-04 router | **REUSE** signal/source invalidation checks, no bypass |
| V3-04 | `route_visual_pattern` | **REUSE** eligibility and conservative render-not-ready status, after independent trace/ledger verification |
| Manim Community / Code2Video | Existing V3-00 pinned reuse inventory | **NOT APPLICABLE** to a pure-state trace adapter; revisit in V3-06 rendering spike |
| ALGOGEN-lab | Public algorithm ideas, unverified/restricted license | **STUDY ONLY; NO SOURCE COPY** |

No external repository code was copied; only the missing narrow oracle/replay and typed adapter glue were implemented. No renderer, video, model, asset or added dependency.

## 2. Algorithm and formal contract

**Input:** strict integral (not booleans or coercible strings) sorted nondecreasing array, length 0–4096, signed target, version `v3-05-leftmost-inclusive-v1`, duplicate policy `LEFTMOST` only. Invalid ordering and unsupported policy are rejected at Pydantic validation.

**Producer:** inclusive window `[low,high]`; `mid=low+(high-low)//2`. If `values[mid] < target`, discard left `low=mid+1`; if greater, keep left half `high=mid-1`; if equal, record candidate `mid` and continue left to return the first occurrence. Every comparison emits exact old/new bounds, midpoint, observed value, action and candidate index. One mandatory explicit `COMPLETE` terminal state records found/not found. Empty array emits *terminal only*, no fabricated comparison.

**Independent verifier:** rebuild the required transition at each claimed step (not by checking schema alone), require correct action/observed value/bounds/candidate, prohibit missing/extra/early comparisons, require a correct terminal state, and compare the final result to Python `bisect_left` after checking actual equality at the insertion index. SHA-256 is checked for artifact integrity, but a maliciously recomputed SHA-256 **never bypasses replay**.

**Typed output:** `VerifiedBinarySearchProof(trace_ref,trace_sha256,oracle_index,step_count,assurance)`. This is returned by verifier code, not trusted when supplied by an unverified external caller.

## 3. StateLedger, cross-artifact source and pattern binding

- `to_binary_search_state_ledger` first independently verifies the trace; requires `pattern.state_source` to agree, V3-02 `WORKED_EXAMPLE_BOARD` with `STATEFUL_SEQUENCE`, a typed sequence semantic object and a **one-to-one ordered teaching-beat assignment**, including terminal state. Never invent extra beats to satisfy the V3-04 router.
- Each step preserves typed sequence/pointer IDs and includes full sorted values, target, old `low/high/mid`, observed item, candidate, action, phase and terminal result. Stable step IDs and ledger ID are tied to the verified source checksum.
- `verify_binary_search_ledger` independently *rebuilds the exact expected ledger* and rejects mutated object properties, rebindings and stale data even if the trace reference marker matches.
- `certify_and_route_binary_search` is the **supported trust-boundary**: verify trace, verify ledger, require matching explicit **script AND storyboard** numeric search example, check any concept-registry label referring to that example, then call the existing V3-04 router with the certified trace ref. It does **not** accept caller-provided `verified_trace_refs`.
- The extra lesson/example binding prevents "trace computes search for 3 but narration describes search for 4". Parser is deliberately fail-closed and only recognizes explicit numeric `Binary search for N in [a,b,...]` (0/1/many elements); it does **not** claim arbitrary freeform language understanding. Non-parseable/ambiguous examples are rejected or marked ungrounded.
- V3-04 still returns `SELECTED_UNRENDERABLE` or `ABSTAIN`; `render_ready=False`. No pixels exist, so no animation evidence or correct narrated timing claim is made.

## 4. Test evidence and attack cases

**Final post-fix GitHub Action [#37735803537](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37735803537)** — SUCCESS on code commit `498e7f42f4411c66c9a95c8ac3515a5208af43dc`:

```text
108 passed # V3-02/03/04/05 typed, property and mutation tests
39 passed  # frozen V2 concept/SceneGraph/repair
46 passed  # Visual Director/numeric cross-artifact consistency
V3_BENCHMARK_PREREG=PASS topics=12 domains=6 easy=4 medium=4 hard=4
LEARNFLOW_BENCH_CONTRACT=PASS
CORE_FREEZE=PASS
```

Run offline (no API secrets):
```bash
python -m pytest -q --confcutdir=tests/v3 tests/v3/test_contracts.py tests/v3/test_signal_preservation.py tests/v3/test_pattern_router.py tests/v3/test_binary_search_trace.py
python -m pytest -q --confcutdir=tests/v2 tests/v2/test_concept_registry.py tests/v2/test_scenegraph_validation.py tests/v2/test_repair_v2_13_contracts.py
python -m pytest -q --confcutdir=tests/hermes tests/hermes/test_visual_director.py tests/hermes/test_final_v2_semantic_consistency.py
python scripts/verify_v3_benchmark_protocol.py
python scripts/verify_learnflow_bench.py
python scripts/verify_v2_core_freeze.py
```

- Exhaustive small-domain property enumeration over sorted integer multisets and seven search targets (>3,000 combinations) cross-checked with stdlib `bisect_left`, plus deterministic hash and replay.
- Empty, singleton, left/right misses, negative targets and arrays, repeated duplicates and found/not-found.
- Mutation attacks: unsorted/bool/string/float/oversized input, unsupported duplicates policy, forged hashes, wrong `low/high/mid`/observed/action/next bounds/candidate, missing/extra comparison, early termination, fake found/not-found, wrong result.
- Exact-source tests: wrong/missing/ambiguous script/storyboard numeric query and mismatched registry example even with a mathematically **valid** trace.
- Ledger negative tests: wrong beat count, duplicate assignment, changed state props, wrong trace/pattern ID, forged route attempt. The V3-04 status remains unrenderable.
- Existing regression/benchmark/Core freeze all PASS. No model calls or paid-provider jobs.

## 5. Honest limits and reviewer verdict

- Hash + schema or a caller-supplied `verified_trace_refs` membership is still insufficient. The new certification wrapper ensures correct oracle replay when **it** is invoked; **generic direct V3-02/04 entry points still expose legacy caller-declared reference membership**. V3-06 must enforce that the renderer/adapter only accepts a certified object and cannot silently bypass the wrapper.
- This proof establishes correctness only of deterministic **leftmost** binary search with nondecreasing integer arrays within length 4096. It does not cover floating point, custom comparators, descending arrays, all binary search policy variants or full natural-language inference.
- The 1–1 beat-to-step mapping is conservative and may abstain for empty or short lessons. This is intentional; constructing new pedagogical beats or a timing model is outside V3-05.
- No V3-06 renderer, Manim integration, frame changes, audio or video produced. **No performance / human comprehension claim is supported yet.**
- Rollback if authorized: revert the V3-05 stacked PR changes without touching V2 Core or prior PRs. Do not merge to `main` as a side effect of this report.

**V3-05 gate = PASS (offline independent trace correctness and typed binding only).**

**Exactly one next checkpoint (not begun here): V3-06 Stateful Sequence Renderer.** Before implementing, audit the pinned Code2Video/Manim Community renderer dependencies and licenses, compare with reusable V2 Pillow/FFmpeg primitives. Accept only when the actual MP4/frame sequence visibly and correctly reflects the certified `low/high/mid` steps with negative mutation/golden checks; no generated executable Python or automatic card fallback.
