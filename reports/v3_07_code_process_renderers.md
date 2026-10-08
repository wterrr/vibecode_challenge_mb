# V3-07 — Code + Process Renderers, Computer Modern blackboard

**Date:** 2026-10-08  
**Decision:** **PASS for bounded offline renderer MP4/semantic state/frame motion proof; not production or human-learning PASS**  
**Repo:** https://github.com/wterrr/vibecode_challenge_mb  
**Branch:** `chatgpt/v3-07-code-process-blackboard`; **parent PR #39** exact SHA `1f0d01634ae5c64e6a1f054b6bf6ddb3a5c1c2d2`, stacked on still-open #34–#38.  
**Implementation CI:** [#37740790915](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37740790915) **SUCCESS**, code SHA `75b28e5c4ed7b344f252c0e1f99c7ae0134de747`.  
**Download actual 2 MP4 + 2 PNG + JSON:** [artifact #11533433759](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37740790915/artifacts/11533433759).

## 1. Input visual reference translated into a reproducible style (not copied artwork)

User supplied a screenshot from 3Blue1Brown's Sigmoid graph and requested a true black background and Computer Modern. V3-07 introduces project-owned `learnflow_v3/blackboard_style.py` and updates V3-06's V3-only renderer, never the frozen V2 Core.

- **Full pixel black `#000000`** with white/neutral grey labels, sparse golden yellow/cyan/green semantic emphasis. Do not accidentally retain the prior V3-06 Slate `(15,23,42)` BG. Independent tests check exact RGB corner pixels across Code, Process and V3-06 frame rendering.
- **Actual Computer Modern Unicode** installed at CI runtime via Ubuntu 24.04 `fonts-cmu`, `fc-match` and Pillow. `CMU Serif` for titles/annotations, `CMU Typewriter Text` for code. **Fail-closed** if fontconfig selects a different family; validate `font.getname()` actually identifies CMU; do not disguise DejaVu as Computer Modern. **No font file bundled or shared**.
- Reuses the visual grammar (blackboard, sparse lines, serif/math-friendly labels), does **not** copy screenshot assets or any creative 3Blue1Brown illustrations.

## 2. Reuse-first audit and licensing

| Upstream or existing code | Pin/license/implementation evidence | Action |
| --- | --- | --- |
| V2 `app/rendering/canvas.py`, `process_diagram.py` | Project code: Pillow/FFmpeg pipeline, card/frame-based progress, prior deep-slate BG | **Reuse stack and finite drawing patterns**, avoid frozen code modifications. Contrast: V3-07 emphasizes stable semantic object IDs, animation along verified edges, real decoded MP4 pixel QA and #000000 CMU style. |
| Frozen V2 `learnflow_v2/scenegraph/{schema,enums}.py` | Exact `SceneGraph`, `SceneNode`, FLOW/SEQUENCE_BEFORE, LayoutIntent, ScenePurpose, node ID and edge referential checks | **REUSE directly**, no duplicate graph schema or topology bypass |
| Frozen V2 `learnflow_v2/repair::compute_content_hash` | Deterministic source evidence hashes | **REUSE directly**, but hashes alone never prove semantic execution |
| V3-06 `sequence_renderer.py` | Typed `SequenceRenderProfile`, `_ffmpeg_anchor`, `_mean_absolute_error` and FFmpeg H.264 pipeline | **REUSE existing tested primitives** and update V3-only styling |
| Manim Community | MIT, exact upstream SHA `23ae68f4dd5817d49760b338e14b92757a2369b5`; Cairo/Pango/TeX rendering stack beyond small CPU adapter need | **Defer** — do not add heavy dependencies or copy code |
| Code2Video | MIT, exact SHA `1142d8e14cdc2806df85aedb0fbb5dca474caa0f`; relies on generated Manim and external agent pipeline | **Study/transfer design only** — executing generated code violates bounded V3-07 path |
| ALGOGEN-lab | Exact SHA `1bb093c76499135ecf54fc8030219a4e7ee4424c`, no verified root LICENSE | **EXCLUDE code copy**; ideas only |
| Computer Modern Unicode | Ubuntu `fonts-cmu` 0.7.0-5 (Ubuntu noble), installed by package manager rather than vendored | **External OS font dependency**, font binary absent from repo & artifacts |
| Python AST | Stdlib, grammar parsing only, custom limited integer expression evaluator | **No `exec`/`eval`, no arbitrary library import or emitted Python runtime** |

## 3. Source-bound typed contracts

**CodeWalkthrough:** limited to 2–9 lines of individual integer assignments and at most six visible integer variables, to avoid crowded 16:9 blackboard. Every step references the same stable line ID as the source; V2 SceneGraph must contain a single CODE node whose exact content matches the source lines, and its SHA must match the typed trace's `scenegraph_sha256`. The independent replay evaluates only **integer constants, prior variables, unary minus, +, -, *, // with nonzero divisor**, bounded to ±1,000,000; any call, loop, import, attribute, unsafe name, unknown operator or mismatched variable snapshot is blocked. It does not execute code authored by an LLM. Each code-line activation travels along a thin yellow indicator during the beat; the variable panel shows the exact replayed snapshot and stable names.

**ProcessWalkthrough:** V2 SceneGraph must contain 2–8 labeled semantic nodes with only FLOW or SEQUENCE_BEFORE relationships. Each typed step names an actual graph node and the **exact edge ID** used from the previous step; unconnected routes and swapped branch IDs fail closed even if rehashed. A deterministic topological DAG layering preserves x/y identity across frames, explicitly rejects cycles and crowded arrangements, and draws all branches; only the actual traversed edge animates in yellow while already traversed branches remain highlighted. No silent flattening to one fake linear chain or to CONCEPT_CARD.

Both are bounded **standalone V3-07 typed adapters**, not a general-purpose program interpreter or claim that a new `CODE_WALKTHROUGH` enum has been inserted into the existing V3-02 `RepresentationType`/V3-04 router. **This is a remaining integration gap, not hidden by the PASS.** Full lesson-wide script/registry/narration binding and declarative capabilities should be added in a separate approved gate before production use.

## 4. Real decoded H.264 MP4 and temporal geometry acceptance

Final implementation run [#37740790915](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37740790915) produced real 960×540 18fps H.264 MP4s. Decoded anchors are compared against semantically indexed pure ideal frames (full-frame MAE cutoff 8 of 255). Adjacent *steps* must exceed 1.15 semantic-region delta; two decoded frames *inside each same beat* must exceed 0.035 region delta to reject stationary slideshows. Both per-beat animation and between-beat state changes passed. Stable object centers and topology replay are independently asserted; not a proof of full arbitrary swept-geometry collision safety.

| Family | Frames | Duration | MP4 bytes | Max decoded frame MAE | Min between-step delta | Min **within-beat motion** | CPU rendering wall time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Code Walkthrough | 56 | 3.11 s | 60,738 | 0.191 | 2.740 | 0.606 | 1.25 s |
| Process Flow (branched) | 42 | 2.33 s | 64,850 | 0.204 | 2.173 | 0.450 | 0.90 s |

Downloaded CI artifact ZIP verified actual MP4 magic and SHA-256 against `v3_07_render_evidence.json`; **both hashes matched**. The two human-viewable poster PNGs were visually inspected: background is black and the installed CMU fonts are used; process graph displays both branches without collapsing topology. **Do not claim aesthetic or human learning parity with 3Blue1Brown** from these fixtures.

## 5. Reproduce and regression

Ubuntu 24.04, Python 3.12, FFmpeg, `fonts-cmu`, `fontconfig`, Pillow pinned `12.3.0` in CI. No provider secrets. Regenerate:

```bash
python scripts/verify_v3_code_process_render.py --output-dir ./v3_07_golden
python -m pytest -q --confcutdir=tests/v3 tests/v3/test_contracts.py tests/v3/test_signal_preservation.py tests/v3/test_pattern_router.py tests/v3/test_binary_search_trace.py tests/v3/test_stateful_sequence_renderer.py tests/v3/test_code_process_renderer.py
python -m pytest -q --confcutdir=tests/v2 tests/v2/test_concept_registry.py tests/v2/test_scenegraph_validation.py tests/v2/test_repair_v2_13_contracts.py
python -m pytest -q --confcutdir=tests/hermes tests/hermes/test_visual_director.py tests/hermes/test_final_v2_semantic_consistency.py
python scripts/verify_v3_benchmark_protocol.py
python scripts/verify_learnflow_bench.py
python scripts/verify_v2_core_freeze.py
```

Measured [#37740790915](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37740790915):
```text
146 passed # V3-02 through V3-07 typed, property, pixel, semantic and negative tests
39 passed  # frozen V2 SceneGraph/repair/registry
46 passed  # Visual Director and semantic mismatch
V3_BENCHMARK_PREREG=PASS
LEARNFLOW_BENCH_CONTRACT=PASS
CORE_FREEZE=PASS
V3_07_GOLDEN=PASS count=2
```

Failure history preserved: first CI showed 7 negative tests blocked upstream by source/SceneGraph provenance rather than specifically the AST; fixtures were re-bound to reach the AST allowlist, then **144 passed**. Next CI exhibited `ffprobe` literal `${name}` caused by YAML escape; corrected. Next two-video run passed all **145 V3 tests** and rendered MP4s, but artifact path `\${{ runner.temp }}` was wrongly escaped; fixed and uploaded successfully. Added dense variable-panel negative regression: **146 PASS**, workflow and MP4 upload PASS.

## 6. Frozen V2 comparison and claim boundaries

| Metric or feature | Frozen V2 renderer | V3-07 evidence | Interpretation |
| --- | --- | --- | --- |
| Default background | Source `app/rendering/canvas.py` uses Slate 900 `(15,23,42)` | All 3 V3 renderer families now use `(0,0,0)` and CMU font | New user-requested visual theme, no V2 source mutation |
| Code semantic execution state | V2 general renderer not demonstrated to replay allowlisted integer assignments | V3-07 independent per-line state verification + highlighted execution | New **bounded** capability, NOT general Python support |
| Process drawing | V2 `process_diagram.py` paints static progressive step-card states | V3-07 preserves full DAG branch topology, fixed node coords, moving highlight along exact typed edges | Different visual semantics, not merely a recolored CONCEPT_CARD |
| MP4 correct decoded semantic frames | No matched V2 CODE/branched-graph reference artifact tested in V3-07 CI | MP4 anchors and within-beat motion measured; SHA-256 stable on CI artifact | **Cannot compute apples-to-apples quality or performance improvements** |
| Benchmark, Core, provider cost | Historical frozen suite | 146/39/46 offline PASS and Core Freeze PASS; **zero paid/free LLM calls** | Engineering tests; no measured human preference |

**Remaining risks:** no voice TTS or beat/narration audio sync, no general code language or arbitrary process cycles, no new canonical lesson-wide Code pattern registration, no measured human cognitive gains, no production-grade hostile media processing, no user preference head-to-head against V2 or 3B1B. Relative sample times are CI CPU short-case observations only; not production p95. V3-07 code itself is not a publication novelty proof.

**Checkpoint verdict: bounded V3-07 engineering PASS; global lesson production/release is NOT authorized.** No `main` merge, no protected V2 file changed, no model provider calls, no V3-08 code. **Exactly one next checkpoint after explicit user authorization: V3-08 Function Graph + Equation Derivation Renderer.**
