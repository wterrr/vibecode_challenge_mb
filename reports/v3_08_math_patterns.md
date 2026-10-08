# V3-08 — Function Graph and Equation Derivation Renderer

**Date:** 2026-10-08
**State:** bounded engineering PASS on final code SHA ff6c1339e2e65f92a84365ae2d85a98b68781b74; documentation-only commit requires CI rerun.
**Scope:** bounded offline engineering proof; no production quality or human learning claims.

## 1. Prior art, reuse, licensing
- Reused project V3-06 Pillow/FFmpeg H.264 + `_ffmpeg_anchor` + decoded-frame pixel QA; V3-07 `blackboard_style.py` (real OS-installed CMU Serif, black #000000, constrained color accents).
- Reused **frozen V2 SceneGraph** (CHART/EQUATION, directed EQUIVALENT_TO/TRANSFORMS_INTO) and `compute_content_hash` binding, without altering frozen V2 source or adding a duplicate graph schema.
- V3-04 already supports EQUATION_GRAPH pattern selection but `render_ready=False`. New bounded typed V3-08 math entry points are not silently wired into V3-04, V3-02 lesson orchestration or publication.
- Upstream Manim Community MIT @ `23ae68f4dd5817d49760b338e14b92757a2369b5` and Code2Video MIT @ `1142d8e14cdc2806df85aedb0fbb5dca474caa0f` were assessed in previous reuse audit; dependency/runtime cost and unbounded generated-code execution are not justified for these finite proof clips. No copied or vendored source. ALGOGEN-lab licensing still unverified: no code reuse. Font binaries are OS packages, **never bundled**.

## 2. Typed mathematical truth boundary

### FUNCTION_GRAPH
- A SHA-bound frozen V2 SceneGraph with exactly one typed CHART contains the exact polynomial and domain expression.
- Coefficients (constant, linear, quadratic) are strict integers; domain is bounded and ordered; typed point IDs are immutable and unique.
- Replay checks every (x,y) against the polynomial. The axes are fixed; the graph curve is revealed on the actual function, with a moving active point and visible certified coordinate pair.
- Domain bounds, vertex + endpoint extrema, finite coefficient/label density and safe plot range are checked before encode. Incorrect point order, mismatched formula/shape, forged value or graph provenance blocks rendering.
- Raster samples are a visualization of an analytically verified degree <=2 polynomial; this is not general arbitrary function parsing, calculus or symbolic graphing.

### EQUATION_DERIVATION
- V2 SceneGraph contains strictly typed EQUATION nodes whose IDs/content match each derivation step; consecutive EQUIVALENT_TO / TRANSFORMS_INTO edges are replayed in order.
- Separate allowlisted AST **data parser** recognizes integer constants, variable x, unary sign, +, -, multiplication and powers 0..2 only. It computes full exact polynomial coefficient triples, not value tests at a few x.
- All steps must represent exactly the same polynomial; attempted hidden constant mutation, incorrect distribution, forged new hash, relinking an edge, unknown symbols, division, code calls, attributes and higher-degree operations are rejected. Never uses Python eval/exec nor runs LLM-generated statements.
- Moving yellow underline follows a typed active equation row, preserving all step IDs and explanatory order.

## 3. MP4 acceptance (CI-verified)
- Real 960×540 / 18fps FFmpeg H.264 videos in two separate math families; one golden PNG per family, machine-readable JSON with SHA-256, immutable provenance, canonical node centers, decoded full-frame anchor MAE, inter-step semantic ROI delta and decoded *within-beat* motion delta.
- Mandatory decoded proof: MAE <=8/255, adjacent semantic change >=0.18 and decoded within-beat change >=0.035. Black corner pixel and CMU identity tests.
- Fixed FFmpeg flags, frame cap, no overwrite, no symlink path, atomic publication, and fail-closed errors without CONCEPT_CARD fallback. Human visual review still required.
- Reproduce: `python scripts/verify_v3_math_patterns.py --output-dir /tmp/v3_08_golden`
- Tests: `python -m pytest -q --confcutdir=tests/v3 tests/v3/test_math_patterns.py`
- Full CI: `.github/workflows/v3-math-patterns.yml`, V3-02→V3-08 + V2 Core Freeze / LearnFlowBench / original prereg.

## 4. Explicit limits
Standalone offline typed math capabilities only; no arbitrary nonlinear functions, discontinuities, inequalities, derivative/integral proof, handwritten/LaTeX compilation, narrated lesson or V3-02/V3-04 canonical end-to-end math integration. Full swept-time geometry and independent human learning outcome comparisons remain later checkpoints. One or two golden clips cannot establish teacher-level clarity or aesthetic equivalence to 3Blue1Brown.

**Gate rule:** bounded engineering PASS after actual CI/MP4/hash inspection; no production release or human-learning claim. No automatic main merge or V3-09 implementation.


## Final source-head engineering evidence (2026-10-08)

**V3-08 BOUNDED ENGINEERING PASS at code SHA `ff6c1339e2e65f92a84365ae2d85a98b68781b74`.** Its **7/7 GitHub workflows succeeded** without model API calls: [V3-08 math CI #37745752422](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37745752422) reports **170 V3 tests, 39 V2 tests, 46 Visual Director/semantic tests passed**, V3 preregistration PASS, LearnFlowBench PASS, Core Freeze PASS. Two real H.264 960x540/18fps MP4s were produced and uploaded: [artifact #11535822025](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37745752422/artifacts/11535822025). Downloaded actual archive and verified MP4 bytes + SHA-256 against the JSON for both families; ffprobe confirmed codec, dimensions and frame counts:

| family | frames | seconds | bytes | max decoded MAE | min adjacent semantic delta | min decoded same-beat motion |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Function graph | 70 | 3.89 | 110,111 | 0.212 | 0.453 | 0.144 |
| Equation derivation | 42 | 2.33 | 44,522 | 0.093 | 0.793 | 0.248 |

Human-viewed final golden PNGs confirm true black background, actual Computer Modern and conventional mathematical display (f(x)=x²−4, typed equivalent expressions instead of x*x/x**2). This is not a validated human learning benefit or parity with 3Blue1Brown. Main and frozen V2 remain unchanged. New documentation-only gate commit must still pass its own CI before final-head merge consideration.
