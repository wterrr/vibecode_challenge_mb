# V3-06 — Stateful Sequence Renderer: actual MP4 and decoded pixel evidence

**Checkpoint:** V3-06 only | **Date:** 2026-10-08  
**Verdict:** **PASS — first material offline dynamic sequence MP4; human/audiovisual teaching quality NOT MEASURED**  
**Repository:** https://github.com/wterrr/vibecode_challenge_mb  
**Branch:** `chatgpt/v3-06-stateful-sequence-renderer`  
**Direct parent:** PR [#38](https://github.com/wterrr/vibecode_challenge_mb/pull/38) HEAD `77790cfb5903014b77300bbc051c6681e2f99476`; PR #34→#35→#36→#37→#38 **all remain unmerged**.  
**Main HEAD:** `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6` (unchanged; do not merge without user authorization).

## 1. Reuse-first upstream and project audit

| Candidate | Exact evidence/licensing/dependency | Decision |
| --- | --- | --- |
| Project-owned V2 Pillow/FFmpeg rendering | `app/rendering/canvas.py`, `typography.py`, `ffmpeg.py`, `process_diagram.py`; existing `requirements.txt` includes Pillow; CI Ubuntu FFmpeg + DejaVu | **Reuse stack, palette and bounded primitive semantics**, implement minimal V3 animated array adapter. V2 imports eagerly bring in provider SDK via `app.rendering.__init__`, so do **not** directly import V2 app package at V3 renderer boundary. |
| Project-owned V2 video backend | `learnflow_v2/render/backend.py`, `assembly.py`: safe FFmpeg invocation, typed artifact & decoded RGB fingerprint patterns | **Reuse design/protocol** without changing Frozen Core; V3 needs raw-video frame pipe for intra-scene motion, not its static-clip encoder. |
| V3-05 certified oracle, state ledger and teaching binding | `certify_and_route_binary_search`; `verify_binary_search_trace` + `verify_binary_search_ledger` + explicit script/storyboard check | **Direct reuse. Mandatory entrypoint** before creating any image/frame; caller-provided `verified_trace_refs` cannot bypass it. |
| Manim Community | [MIT](https://github.com/ManimCommunity/manim/blob/main/LICENSE), upstream SHA `23ae68f4dd5817d49760b338e14b92757a2369b5`; large Cairo/Pango/LaTeX optional renderer stack | **Defer**: no need to import/copy for bounded array animation; may be worthwhile for specialized math later, independent audit. |
| Code2Video | [MIT](https://github.com/showlab/Code2Video/blob/main/LICENSE), upstream SHA `1142d8e14cdc2806df85aedb0fbb5dca474caa0f`; Manim/code-generation plus agents | **Study only**: arbitrarily generated executable Manim code violates current bounded renderer boundary; no copied implementation. |
| ALGOGEN-lab | Repo SHA `1bb093c76499135ecf54fc8030219a4e7ee4424c`, no verified repo license | **DO NOT COPY** until permission established. |
| FFmpeg / Pillow | Ubuntu FFmpeg from runner OS distro; Pillow **12.3.0** in CI (workflow exact pin in final branch). DejaVu Sans via system font package | **Import existing packages**; no live provider SDK or new paid dependency. Absolute binary reproducibility beyond pinned source and runner version not claimed. |

No external source or font binary is committed. All differences are V3-specific.

## 2. Ownership & actual effect

`learnflow_v3/sequence_renderer.py` exports `SequenceRenderProfile`, pure typed `draw_binary_search_frame`, `render_certified_binary_search_video` and `SequenceRenderEvidence`. It requires the full **V3-05 certified trace + exact V3-02 StateLedger + V3-04 router** and cross-artifact script/scene bindings before opening FFmpeg. Any forged per-step state, forged recomputed hash, changed taught target or changed ledger is rejected.

Rendering owns **only bounded deterministic positions**: stable array item values/index centers throughout the video, highlighted eligible index window and color-coded LOW/HIGH/MID (and first candidate) markers updated each certified state. Small ease-in/out interpolation moves pointers between consecutive declared states; no array reordering or generic card. An empty sorted array emits an honest **terminal-only** empty-state MP4, not a fake dynamic trace, and is a documented exception to V3-04's expected abstention from dynamic routing.

Guardrails: 16:9 profile, even dimensions, minimum 640×360 maximum 1920×1080, 12–30 FPS, ≤16 visible numbers, ≤960 frames, readable numeric labels, safe caption area, only fixed allowlisted FFmpeg command, no generated Python, no arbitrary geometry from LLM, no file overwrite or symlink output target, temporary file cleanup and atomic no-clobber publication. No V2 Core, V1 rollback, V2 benchmark, model default or historical Action #181 modified.

**Crucial caveat:** the output is a **caption-synchronized, silent video**. No real narration audio/TTS or word-aligned subtitles were generated or tested; a time-aligned audio/visual integration belongs to later checkpoints, not claimed here.

## 3. Measured, actual MP4s and independent decode

CI [run #37737754838](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37737754838) on code SHA `51f55c6c60b7e0529f1b038f98389b5ab1723800` produced the actual ZIP [artifact #11532153065](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37737754838/artifacts/11532153065). This artifact has 5 H.264 MP4s at **960×540 18 FPS**, 5 PNG posters and `v3_06_render_evidence.json`. The online Actions archive and downloaded local copy both contain real MP4 bitstreams (not image-only mockups).

| Case | Frames | Duration | Video bytes | Max decoded-anchor MAE (0–255) | Min adjacent semantic-step ROI MAE | Render wall time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Duplicate / LEFTMOST found | 56 | 3.11s | 150,199 | 0.808 | 1.851 | 0.94s |
| Not found | 56 | 3.11s | 148,494 | 0.787 | 1.651 | 0.90s |
| Singleton found | 28 | 1.56s | 73,508 | 0.689 | 1.642 | 0.43s |
| Empty array | 14 | 0.78s | 47,311 | 0.573 | N/A (single static terminal state) | 0.23s |
| Boundary / first item | 42 | 2.33s | 115,107 | 0.746 | 2.228 | 0.66s |

**Pixel proof and limitations:** for **every** step, FFmpeg decodes the resulting MP4's sampled frame (around 75% into the beat); the decoded RGB frame is compared against an independently requested *pure renderer state image* driven by the corresponding oracle step. Maximum full-frame MAE must be ≤8 and adjacent decoded frame differences in the semantic array/pointer ROI must be ≥1.25 for each actual transition. All 5 cases met these thresholds; the decoded semantic frames/identity centers, bitstream SHA-256 and step timings are recorded in JSON. **This is stronger than “we wrote PNGs” but is not a second independent OCR/semantic visual critic**: the ideal and rendered images share the same drawing code; visually inspect the golden clips and keep a human quality gate.

Duplicate example source `[1,3,5,7,9,12,12,14,18]`, target `12`: compare mid=4(value9) → candidate at mid=6(value12) → search left at mid=5(value12) → terminal found index **5**, not index 6, all represented with stable array item positions.

## 4. CI test commands & regressions

[Final hardening run #37737754838](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37737754838) **SUCCESS** (preceded by import-dependency failures, then verified clean):

```text
123 passed  # V3-02/03/04/05/06 typed, property, negative and real-video tests
39 passed   # frozen V2 concept / SceneGraph / repair
46 passed   # Visual Director / semantic drift
V3_BENCHMARK_PREREG=PASS
LEARNFLOW_BENCH_CONTRACT=PASS
CORE_FREEZE=PASS
V3_06_GOLDEN=PASS count=5
```

Run with Python 3.12, existing CI dependencies and `ffmpeg`, `ffprobe`, DejaVu font installed:

```bash
python -m pytest -q --confcutdir=tests/v3 tests/v3/test_contracts.py tests/v3/test_signal_preservation.py tests/v3/test_pattern_router.py tests/v3/test_binary_search_trace.py tests/v3/test_stateful_sequence_renderer.py
python -m pytest -q --confcutdir=tests/v2 tests/v2/test_concept_registry.py tests/v2/test_scenegraph_validation.py tests/v2/test_repair_v2_13_contracts.py
python -m pytest -q --confcutdir=tests/hermes tests/hermes/test_visual_director.py tests/hermes/test_final_v2_semantic_consistency.py
python scripts/verify_v3_benchmark_protocol.py
python scripts/verify_learnflow_bench.py
python scripts/verify_v2_core_freeze.py
python scripts/verify_v3_binary_search_render.py --output-dir ./v3_06_golden --width 960 --height 540 --fps 18 --seconds-per-step 0.8
```

Negative cases include invalid versions/trace source, forged hash/mid/bounds/action/terminal/ledger, changed script target, output overwrite and symlink, no-pixel-validation attempt, oversized 17+ items, non-16:9 layout and overlong digit labels. The test executes real FFmpeg; no file is accepted as successful without decoding the encoded MP4. CI stores only MP4/PNG/proof JSON; no governance logs/secrets.

## 5. Reviewer attack, costs, quality, rollback, decision

- **Actual proof:** certified algorithm→typed ledger→pixel-compliant frame sequence→MP4 exists; H.264 decoded step changes are measured. This closes the critical “everything becomes CONCEPT_CARD” problem for the bounded binary-search demo **only**.
- **No claim:** dynamic visual validity for arbitrary algorithms, mathematical correctness of all displayed prose, word-level narration synchronization, audio narration, physical swept-geometry collision, human learning gains or aesthetic parity with 3Blue1Brown. The human baseline prereg protocol remains UNMEASURED.
- **Performance:** recorded per-video wall time ~0.23–0.94 seconds on CI CPU for short 960×540 clips; no service-level throughput or latency distribution inferred.
- **Cost:** $0 provider charges; no free or paid model calls. CI runner compute not priced as model usage.
- **Rollback:** PR V3-06 may be closed/reverted separately without changing #34–#38, main, frozen Core, original #181, or V1 backup. Main is not merged here.
- **Stop/go:** proceed only if future V3-07 independent tests show actual non-card code/process pixels. Do not hide failure behind more agents. The first material proof from V3-06 is bounded and real, not a substitute for release validation.

**Decision: PASS for V3-06 offline renderer + real MP4/decoded-frame evidence; not a release candidate.**

**Exactly one next checkpoint:** **V3-07 — Code + Process Renderers**, only after explicit user request; reuse-first and independent rendering/semantic coverage gates. No V3-07 was implemented by V3-06.
