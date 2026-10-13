# V3-56 — Deep Pedagogical Beat & Scene Source Audit Addendum

**Scientific gate: READ + SOURCE AUDIT COMPLETE IN ITS REGISTERED SCOPE, 15 NATIVE VIDEO TIMELINES **NO-GO**.** This report records what actually happened; the original V3-56 Draft PR #90 remains open and production BLOCKED. Read PR parent V3-55 technical closeout in [V3-56 main report](v3_56_pedagogical_prompt_architecture.md).

**Deep-audit extension was preregistered before collecting supplemental data**, commit `593d1db5cf6f34d4d83d657862074816d6d48d9b`. Parent evidence matrix and its initial frozen selection remain intact. No model API, no merge `main`, no production prompt edits, no V2 Core changes.

## 1. Precise observation method and limits

* Visited and read all 18 official [3Blue1Brown Read](https://www.3blue1brown.com/) pages in the frozen study; observed their narrative order, headings, embedded picture/link markers, text quizzes and occasionally explicitly stated motion descriptions.
* Also inspected first-party **site-hosted example still images**, e.g. linear-transformation grid comparison and colored basis arrows. These are actual Read static figures, **not decoded native frames** of a video.
* Retrieved **18 actual 3b1b/videos Python scene-source files** by exact blob SHA, and counted source scene classes/animation constructs. Selected class names with line markers are listed below. This verifies a code-level design possibility, not that all classes were edited into a final clip or appeared in that order.
* Inspected Grant Sanderson's official [source repository workflow](https://github.com/3b1b/videos#workflow): interactive `manimgl ... -se`, editor checkpoint-paste and render workflow. Source repo explicitly differentiates 3b1b ManimGL from Manim Community and retains CC BY-NC-SA 4.0 source scene licensing. Do not copy originals into LearnFlow.
* Tried to access underlying original full clips programmatically; the current container cannot retrieve official site/YouTube media (DNS/network unavailable). `web` can inspect first-party Read, source and public video descriptions; it is **not** a frame-by-frame video player and cannot certify soundtrack or real clip PTS. Therefore **0/15 required edited native videos are directly attested**, and all alleged exact video timestamps or real voice/animation alignment remain **UNKNOWN**.

### Terms — avoid conflating four evidence levels

| Level | Evidence we actually collected | Cannot prove |
|---|---|---|
| READ_SEQUENCE | section text and ordering, quizzes, descriptions of animations | final edited video cut order, absolute time |
| READ_STILL | original still figure from first-party Read | in-video transition, movement velocity, pacing |
| SOURCE_SCENE | declared class and `self.play` / `Transform` / `wait` code | actual rendered frames and timecode; human learning |
| NATIVE_FILM | would require original encoded MP4 + audio + frame-PTS receipts | **NOT ACQUIRED for any of the 18** |

Do not use an external video chapter list as timestamp evidence for actual on-screen objects; timestamps would remain unconfirmed until sampling the encoded clip.

## 2. Eighteen matched source-code files + 113 reconstructed Read pedagogical beats

Each Read entry is linked to a first-party source file and at least five Read **pedagogical beat hypotheses**, ordered from the Read text, not necessarily the video. Code source is independently fetched; per-video scene order is *not certified*.

| # | Read lesson | READ beats | Source script | Git blob | Illustrative original class names |
|---:|---|---:|---|---|---|
| 1 | [la_span](https://www.3blue1brown.com/lessons/span/) | 6 | [_2016/eola/chapter2.py](https://github.com/3b1b/videos/blob/c5f01b7e301b420c1407d82ab70bdd1a7c703407/_2016/eola/chapter2.py) | `c5f01b7e3` | `ShowVaryingLinearCombinations` (L206), `LinearDependentVectors` (L505) |
| 2 | [la_linear](https://www.3blue1brown.com/lessons/linear-transformations/) | 6 | [_2016/eola/chapter3.py](https://github.com/3b1b/videos/blob/0fc0fc4b1450023a500bc07b8189dc88d0516220/_2016/eola/chapter3.py) | `0fc0fc4b1` | `TransformJustOneVector` (L213), `TransformManyVectors` (L240) |
| 3 | [la_matrix](https://www.3blue1brown.com/lessons/matrix-multiplication/) | 6 | [_2016/eola/chapter4.py](https://github.com/3b1b/videos/blob/11ea83ef488501b2732ebed8169f17b8c0b1348d/_2016/eola/chapter4.py) | `11ea83ef4` | `TwoSuccessiveTransformations` (L214), `RotationThenShear` (L228) |
| 4 | [la_det](https://www.3blue1brown.com/lessons/determinant/) | 6 | [_2016/eola/chapter5.py](https://github.com/3b1b/videos/blob/23488e8906d85177a92c967271c4fc96d90858c9/_2016/eola/chapter5.py) | `23488e890` | `DiagonalExampleWithSquare` (L202), `BreakBlobIntoGridSquares` (L271) |
| 5 | [la_eigen](https://www.3blue1brown.com/lessons/eigenvalues/) | 6 | [_2016/eola/chapter10.py](https://github.com/3b1b/videos/blob/087296d6c068cd4bae863af117f568ca76bd1c5d/_2016/eola/chapter10.py) | `087296d6c` | `VectorKnockedOffSpan` (L197), `VectorRemainsOnSpan` (L226) |
| 6 | [la_dot](https://www.3blue1brown.com/lessons/dot-products/) | 6 | [_2016/eola/chapter7.py](https://github.com/3b1b/videos/blob/3c51dbe964a00c87c2dc1db51662cb86c03a315a/_2016/eola/chapter7.py) | `3c51dbe96` | `GeometricInterpretation` (L241), `ProjectOntoUnitVectorNumberline` (L1411) |
| 7 | [la_cross](https://www.3blue1brown.com/lessons/cross-products/) | 6 | [_2016/eola/chapter8p2.py](https://github.com/3b1b/videos/blob/c2acc3cef00df1614c5b22e4a7119aceaf8fae68/_2016/eola/chapter8p2.py) | `c2acc3cef` | `ThreeDMovingVariableVector` (L780), `ThreeDProjectToPerpendicular` (L837) |
| 8 | [calc_essence](https://www.3blue1brown.com/lessons/essence-of-calculus/) | 7 | [_2017/eoc/chapter1.py](https://github.com/3b1b/videos/blob/b452b709149de1dd558cb096d2b618fd36d26fdf/_2017/eoc/chapter1.py) | `b452b7091` | `IntroduceCircle` (L594), `ApproximateOneRing` (L699) |
| 9 | [calc_deriv](https://www.3blue1brown.com/lessons/derivatives/) | 6 | [_2017/eoc/chapter2.py](https://github.com/3b1b/videos/blob/e1e2744aee8076beae608f289e30fa88ba1e5fa4/_2017/eoc/chapter2.py) | `e1e2744ae` | `IntroduceCar` (L212), `CompareTwoTimes` (L676) |
| 10 | [calc_integration](https://www.3blue1brown.com/lessons/integration/) | 6 | [_2017/eoc/chapter8.py](https://github.com/3b1b/videos/blob/03c419c62caba6aa75207e554f8cde2ad352859e/_2017/eoc/chapter8.py) | `03c419c62` | `PlotVelocity` (L230), `AreaUnderVGraph` (L499) |
| 11 | [calc_exp](https://www.3blue1brown.com/lessons/eulers-number/) | 7 | [_2017/eoc/chapter5.py](https://github.com/3b1b/videos/blob/0b4ee2272b436aec69e1a893dec929536b013159/_2017/eoc/chapter5.py) | `0b4ee2272` | `ExpFootnoteOpeningQuote` (L4), `LastVideo` (L17) |
| 12 | [prob_bayes](https://www.3blue1brown.com/lessons/bayes-theorem/) | 7 | [_2019/bayes/part1.py](https://github.com/3b1b/videos/blob/e9a61edddcc232733c6f66e017f517ec1a62289c/_2019/bayes/part1.py) | `e9a61eddd` | `ReasonByRepresentativeSample` (L1479), `NewEvidenceUpdatesPriorBeliefs` (L1822) |
| 13 | [compo_fourier](https://www.3blue1brown.com/lessons/fourier-series/) | 7 | [_2019/diffyq/part4/fourier_series_scenes.py](https://github.com/3b1b/videos/blob/962bf525eaceef8eed74d96e818fe2c2b703e68a/_2019/diffyq/part4/fourier_series_scenes.py) | `962bf525e` | `ComplexFourierSeriesExample` (L8), `DemonstrateAddingArrows` (L408) |
| 14 | [nn_intro](https://www.3blue1brown.com/lessons/neural-networks/) | 6 | [_2017/nn/part1.py](https://github.com/3b1b/videos/blob/d43aca59590cd64f55e5c2e3ab51954a603f70d4/_2017/nn/part1.py) | `d43aca595` | `PixelsAsSquares` (L60), `IntroduceEachLayer` (L1036) |
| 15 | [nn_gradient](https://www.3blue1brown.com/lessons/gradient-descent/) | 6 | [_2017/nn/part2.py](https://github.com/3b1b/videos/blob/59ee68919fe7ded41de2c22e877a6359ccb1d798/_2017/nn/part2.py) | `59ee68919` | `IntroduceCostFunction` (L585), `SingleVariableCostFunction` (L1440) |
| 16 | [nn_gpt](https://www.3blue1brown.com/lessons/gpt/) | 6 | [_2024/transformers/generation.py](https://github.com/3b1b/videos/blob/ce191a3438a4a5d11b3e8a267d9a2fed358d162e/_2024/transformers/generation.py) | `ce191a343` | `SimpleAutogregression` (L112), `AltSimpleAutoRegression` (L399) |
| 17 | [nn_attention](https://www.3blue1brown.com/lessons/attention/) | 7 | [_2024/transformers/attention.py](https://github.com/3b1b/videos/blob/806af030062a7e00703ed2708c0a503f01bad22f/_2024/transformers/attention.py) | `806af0300` | `AttentionPatterns` (L10), `MyseteryNovel` (L1453) |
| 18 | [nn_mlp](https://www.3blue1brown.com/lessons/mlp/) | 6 | [_2024/transformers/mlp.py](https://github.com/3b1b/videos/blob/dbb4e71cdd93d8f984efec48903281f6b62cb794/_2024/transformers/mlp.py) | `dbb4e71cd` | `LastTwoChapters` (L8), `AltLastTwoChapters` (L182) |

Full per-beat `read_order`, transition hypothesis, negative-control note and deliberately `null` video times: [`research/v3_56_deep_pedagogical_beats.json`](../research/v3_56_deep_pedagogical_beats.json). Exact code path/SHA, scene class line and code construct counts: [`research/v3_56_source_scene_corpus.json`](../research/v3_56_source_scene_corpus.json).

The scene-source files include historical API versions; do not claim they execute on current ManimGL/Manim Community. Lexical number of `self.play` calls is descriptive of source text only, **not** scene count, clip duration, aesthetic score or cognitive gain.

## 3. Four concrete mechanistic case studies on first-party Read (not video timing)

### 3.1. Linear transformation: change representational density to expose one invariant

[Official Read](https://www.3blue1brown.com/lessons/linear-transformations/) starts with input→output **vector movement**, explicitly says arrows for every vector would be crowded, re-encodes as points, then as deforming full coordinate grid. It retains a still baseline grid to preserve original-space reference. Later, two distinct **negative cases** expose non-linearity: curved lines and a moving origin; the final basis-vector arrows condense an entire grid transformation to matrix columns. Source `_2016/eola/chapter3.py` includes `TransformJustOneVector`, `TransformManyVectorsAsPoints`, `TransformInfiniteGridWithBackground`, `MovingOrigin`, `SneakyNonlinearTransformation`, `FollowIHatJHat`. **Transfer:** Representation density is an explanation decision; selective hiding/simplification matters as much as motion. **Proposed host proof:** track point↔vector↔basis identity and verify lines/origin invariants; a static reference grid should *remain static*. No claim of exact transition frames.

### 3.2. Essence of Calculus: expose deliberately non-exact approximation then converge

[Official Read](https://www.3blue1brown.com/lessons/essence-of-calculus/) starts with a known circle area and asks *why*. It chooses concentric rings, straightens one into an **approximately rectangular** strip and warns the approximation isn't exact. By reducing thickness `dr`, the area error shrinks. The rectangles are then reinterpreted as area under `2πr`; an ordinary triangle's area recovers `πR²`. Source `_2017/eoc/chapter1.py` includes `ApproximateOneRing` and `GraphRectangles`. **Transfer:** A compelling pedagogical visual must show the **temporary mismatch** and limiting improvement, not fake immediate exact equality. **Proposed host proof:** separately verify finite-strip approximation and convergence error, enforce original ring/rectangle area relationships and same semantic area across representation changes. "Look what happens" is not an evidence-bearing operation on its own.

### 3.3. Bayes: use discrete samples and questions, not mandatory camera movement

[Official Read](https://www.3blue1brown.com/lessons/bayes-theorem/) starts with Steve's occupation judgment and shows why conditional stereotypes without base rates mislead. It builds a representative sample of 200 farmers and 10 librarians with evidence filtering, then converts counts to posterior probabilities and later area/proportion algebra. Source `_2019/bayes/part1.py` contains `ReasonByRepresentativeSample`, `NewEvidenceUpdatesPriorBeliefs` and `DiscussFormulaAndAreaModel`. **Transfer:** sometimes a deliberately **static but numerically truthful partition** with one filtering operation is more illuminating than continuous motion. The Critic must check the denominator of the *conditioned population*, not just animation transitions. Numbers used in explanatory analyses are sourced from the Read, **not from new model invented assumptions**.

### 3.4. Euler e and Fourier: counterexamples to rigid script template

[Euler e Read](https://www.3blue1brown.com/lessons/eulers-number/) uses population **mass** rather than discrete person count to establish continuous time, first compares full-day doubling with a derivative, then explicitly admits there is not a clear obvious geometric depiction for the next manipulation. It pivots to numeric/algebraic pattern finding, then identifies the special base `e`. **Transfer:** in a validated `SYMBOLIC_DEDUCTION` or `QUESTION_HOLD` beat, requiring continuous animation can actively harm accuracy.

[Fourier Read](https://www.3blue1brown.com/lessons/fourier-series/) opens with a dense rotating-arrow contour and **shows a compact integral formula before explaining it**. It then contextualizes Fourier's heat problem, linear superposition, finite partial approximations, and returns to the rotating-vector phenomenon. **Transfer:** an unresolved formula *teaser* can be legitimate, provided the script tracks that a referenced claim is not yet explained and a later verified beat closes it. This invalidates rigid "always formula after intuition" wording.

## 4. Negative analysis, not just collecting spectacular animations

| Counterexample | First-party Read explanation | Agent decision / host check |
|---|---|---|
| Static question hold | Span, matrix, Bayes and Euler include questions before outcomes | `QUESTION_HOLD`; no fake transformation index |
| Static reference grid | Matrix/linear maps preserve a baseline space image | keep background reference fixed; track old/new coordinate frames |
| Symbolic vs graphic | Euler e explicitly pivots to numeric reasoning | `SYMBOLIC_DEDUCTION`; confidence and claim IDs host checked |
| Algebra teaser before proof | Fourier shows unresolved formula upfront | script preserves unresolved status until explanatory closure |
| Visual approximation is not identity | Ring→rectangle is only approximate for nonzero thickness | show error/invariant scope; forbid exact proof by drawing |
| Static area/sample comparisons | Bayes conditioning as filtered population | preserve counts and conditional denominator; motion optional |
| Deliberate projection/abstraction | Many vectors→tip points→grid changes representation | preserve meaning via typed equivalence; literal graphic identity is not always maintained |
| Architecture-specific illustration | Neural network visual edge detector is an illustration | do not claim it is the measured behavior of every real model |

Thus both simplistic rules **"more animation is better"** and **"always animate persistent identical objects"** are unsupported. The useful invariants are **semantic truth, clarity and cognitive relevance**; visual motion is a conditional tool.

## 5. Concrete change to LearnFlow V3 agent architecture

Research-only [PEC machine contract](../research/v3_56_agent_prompt_architecture.json) has been revised following the counterexamples:

- Previously a witness **always required an integer `transformation_index`**, making meaningful static questions/symbolic derivations impossible to express honestly.
- It now permits `transformation_index=null` exclusively for `STATIC_COMPARISON`, `QUESTION_HOLD`, `SYMBOLIC_DEDUCTION`, enforced through Draft 2020-12 JSON Schema conditional branches. True motion `DECODABLE_PIXEL_TRANSITION`, `HOST_VERIFIED_GEOMETRY`, etc., continue to require integer operation references.
- `verified_transformations=[]` is allowed for intentionally static explanation; `expected_observable_explanation` still requires a semantic witness.
- Script should admit an unresolved equation teaser with explicit future resolution; Visual Director V3 can select reasoned static comparison instead of compulsory geometric transforms. Updated [proposed prompt specs](../research/v3_56_agent_prompt_templates.md).
- Source confidence remains **READ/SOURCE**, not native video. V2 frozen layout/prompt is untouched; no new production renderer capability is implied.

Future host semantic validation must enforce (a) static witness has no motion ref, (b) actual motion has a certified transform index, (c) equation teaser gets resolved without unsupported factual additions, and (d) a static hold does not get judged as a failed motion event. This is specification-level design, not proof runtime integration.

## 6. What remains blocked to truthfully finish user's requested 15-video study

**Mandatory independent next evidence:** obtain original 15+ streamed/encoded full videos using a permitted browser/video interface; record video page canonical ID, actual duration, actual frame / audio timestamps, at least 5 semantic transition events per lesson with before-and-after decoded still witnesses, and where applicable source scene class. Cross-check narrated words versus visual events on the encoded audio. Mark edit order, camera, composition, hold lengths and synchronization precisely; do not extrapolate from Read order or source code class declarations.

**Current result:** `18/18` first-party Read and corresponding scene-source files examined; `113` Read-level beats; `0/15` full edited native films/video-audio event alignments confirmed. Therefore **FULL VIDEO & TEMPORAL PEDAGOGICAL AUDIT = NO-GO**. Research architecture correction and bounded Read/source findings are real; production remains BLOCKED and V3-57 should not claim full 3B1B longitudinal pacing research as prerequisite evidence.

**Integrity test** `python scripts/verify_v3_56_deep_video_audit.py` is intentionally allowed to exit 0 only when it reports this explicit NO-GO status, to enforce honest provenance rather than hide an unavailable video audit behind a successful CI.

