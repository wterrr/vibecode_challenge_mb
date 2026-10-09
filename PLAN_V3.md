# LearnFlow V3 — Evidence-Gated Implementation Plan

**Version:** 3.0.1-draft | **Date:** 2026-10-08 | **Status:** PLAN DRAFTED / IMPLEMENTATION NOT AUTHORIZED  
**Authority:** User requested a complete V3 plan after the single paid final V2D run. This authorizes documentation and research only, **not** automatic implementation or merge to main.  
**Development branch at drafting:** `chatgpt/live-v2d-gpt6-luna-paid-pilot`. Frozen V2 Core and historical #181 artifacts remain immutable.

## 0. Executive decision and scope

**North Star:** From a technically valid narrated slide/card generator into a **verified, visually expressive educational explanation engine**. Visual states must teach an idea (causality, transformation, comparison, algorithm execution, proof), not merely decorate sentences.

V2 achieved one governed end-to-end lesson (Action #181) with real audio, readable shorter subtitles and successful technical gates. It did **not** demonstrate visually compelling teaching, distributional reliability, student learning gain, or semantic agreement of all intermediate artifacts. The V3 design addresses these distinct failures without discarding V2's typed, renderer-neutral Core.

A new V3 output qualifies as progress only if, under identical content/input and preregistered controls:
1. the visual representation is causally/semantically appropriate;
2. the learner can observe the state change required to understand the explanation;
3. identity, evidence and narration remain consistent across artifacts;
4. all hard geometry, timing, safety and rendering gates pass;
5. human evaluation shows an advantage over V2 baseline on matched topics;
6. costs and failures are logged, not hidden via retries or silent card fallbacks.

No default SOTA, 3Blue1Brown-equivalence or ≥98% real-world success claim. Treat `UNMEASURED` separately from `FAIL` and `DEFERRED`.

### 0.1 What is authorized now

- **Allowed:** draft this plan; review sources and repository; add research notes; audit branch integration; propose explicit checkpoint definitions.
- **Not yet allowed:** implement V3, merge branches, overwrite V2 evidence, trigger paid OpenRouter jobs, spend budget on broad live studies.
- **Conditional drafting waiver:** user elected to skip 100-topic paid V2D benchmark; #181 technical PASS and observed media can motivate V3 planning despite its **known historical cross-artifact semantic mismatch**. That mismatch is **not retroactively PASS** merely because a later offline guard detects it. The later offline guard passed on its own CI run.

### 0.2 Immutable inputs and traceability

- `PLAN_V2.md` — baseline contracts, Core Freeze, Definition of Done; **not the V3 plan**.
- `LEARNFLOW_V3_RESEARCH_NOTES.md` — **canonical prior research**, design decisions, reviewer attack, remaining empirical unknowns. Do not replace with recollections.
- `benchmarks/learnflowbench/corpus_v1.json` — immutable 100-topic candidate corpus; test selection must be preregistered, not chosen based on results.
- `benchmarks/learnflowbench/README.md` — accepted deterministic comparison, narrower than human quality evidence.
- `reports/v2_final_semantic_consistency_offline_audit.md` — #181 historical mismatch and offline guard.
- GitHub #181 `37721597623`; offline preflight `37723264679`; pilot branch commits `cb605dc` -> `efd19bc`.

## 1. Baseline evidence ledger — FACT vs MEASURED vs UNMEASURED

| Evidence | Status | Valid conclusion | Invalid extrapolation |
| --- | --- | --- | --- |
| #181 workflow: both contract/provider jobs successful; one run attempt | FACT | live one-topic pipeline and CI ran to completion | whole-corpus reliability |
| #181 MP4 135.37 s, 1280x720/30fps H.264 + AAC, 3 scenes, 41 short subtitle cues, 22 motion events, 2 scene transitions | MEASURED from prior final audit | basic A/V deliverable | cognitive learning gain / professional cinematic video |
| All 3 scenes `CONCEPT_CARD`, 0 persistent transitions, no running visual interval/pointer trace | MEASURED | representation bottleneck persists | "animation count = pedagogy" |
| #181 registry "find 16" vs script/scene video "find 24" | MEASURED | cross-artifact semantics drifted despite technical PASS | flawless semantic provenance |
| Offline #4: Core Freeze PASS, contract PASS, 87 Hermes/subtitle/semantic tests PASS, renderer 14 PASS 5 SKIP | MEASURED | narrow regression guard now exists | automatically corrected #181 model output |
| Frozen V1/V2A/V2B/V2C three-fixture deterministic proxy, +6.0684 V2A vs V1 | MEASURED, limited | proxy improved for those fixtures | human aesthetic quality |
| 100-topic live generation, true success distribution, educational learning outcomes, human preference, cost distribution | UNMEASURED / DEFERRED | cannot claim improvement | ≥98%, SOTA or "3Blue1Brown-like" |

**Root-cause taxonomy, not one "visual quality" bucket:**
R1 upstream teaching-plan weakness; R2 collapse to universal `CONCEPT_CARD`; R3 generic rounded-rectangle renderer for CODE/CHART/EQUATION/etc.; R4 limited stateful intra-scene changes; R5 motion count ≠ semantic event coverage; R6 weak visual-narration binding; R7 identity drift; R8 subtitles/legibility/transition risk; R9 lack of human quality outcomes. Each capability and metric below maps to a root cause.

## 2. Prior-work audit and transfer decision

| Work | Supported transferable principle | Existing gap / threat to LearnFlow | Decision |
| --- | --- | --- | --- |
| Code2Video (ICML 2026) | Planner, visual-focused critic, ScopeRefine, MMMC + TeachQuiz | More expressive visuals from generated Manim; its agent orchestration alone is **not** LearnFlow novelty | **PORT** pedagogical decomposition, **ADAPT** structured local critic; **REJECT** arbitrary code as canonical IR |
| ALGOGEN (Findings ACL 2026) | Decouple algorithm execution / VTA from deterministic visual renderer / RSL | Stronger truthful execution states on algorithms | **ADAPT** opt-in verified trace adapter; not general IR |
| OmniManim (`2605.15585`) | Explicit keyframe spatial planning, interpolation-aware collision QA | Endpoint-safe geometry can collide at intermediate times | **ADAPT** LearnFlow-owned keyframe solver; learned prior **DEFER** pending deterministic baseline |
| LLM2Manim (`2604.05266`) | Segmentation, signaling, symbol consistency and human review | Pedagogy needs an explicit auditable theory, not style polish | **PORT** learning principles and symbol ledger; not autogenerated Manim |
| MINARD / FigTalk (`2606.12576`) | Narration-grounded sequential visible-region highlights | Current word-timed cues do not ensure visual meaning | **ADAPT** per-beat grounding and coverage |
| SGA (`2607.18116`) | Symbolic intermediate geometry QA | LearnFlow already has typed geometry, but needs time-aware QA | **PORT** verification principle, not code parsing |
| EduVisAgent / TeachMaster | Reasoning decomposition and educator-oriented direction | More agents alone does not solve bad representation | **ADAPT** evaluation, no gratuitous agent proliferation |
| DiagrammerGPT | Bounded diagram intent and independent rendering of text/objects | Generic renderer paints every semantic category similarly | **ADAPT** typed pattern vocabulary |
| ManimBench / ManiBench | Render success is distinct from visual logic correctness | V2 has technical success but weak state grounding | **PORT** multi-axis evaluation |
| Mayer multimedia learning review (2017) and 2025 meta-analysis | Coherence, signaling, contiguity, segmentation, redundancy boundary conditions | Gratuitous animation can increase cognitive load | **PORT** pedagogy safeguards, empirically test rather than hard-code aesthetic preferences |

**Evidence calibration:** ALGOGEN's reported 99.8% success boundary (trace-generation / benchmark protocol) must not be rebranded as LearnFlow-comparable end-to-end video reliability. Code2Video's scores, ablations and TeachQuiz do not automatically transfer to LearnFlow. Human-crafted 3Blue1Brown is a *reference*, not an automatic competitor with matched generation constraints.

**Novelty hypothesis, not accepted claim:** typed lesson-wide semantic identity + constrained representation compiler + verified state/beat traces + time-aware deterministic geometry + proof-producing local patching across general subjects. Each primitive has antecedents; novelty, if any, must be tested as **composition with superior measurable properties** against closest systems. Conduct a dedicated prior-work/reviewer-attack table before any publication-oriented claim.

Sources:
- https://arxiv.org/abs/2510.01174 and https://github.com/showlab/Code2Video
- https://aclanthology.org/2026.findings-acl.156/ and https://github.com/MAC-AutoML/ALGOGEN-lab
- https://arxiv.org/abs/2605.15585 ; https://arxiv.org/abs/2604.05266 ; https://arxiv.org/abs/2606.12576
- https://arxiv.org/abs/2607.18116 ; https://arxiv.org/abs/2505.16832
- https://onlinelibrary.wiley.com/doi/10.1111/jcal.12197 ; https://doi.org/10.1016/j.edurev.2025.100730

## 3. Non-negotiable architecture

```text
User/topic -> research/fact verification -> PedagogyPlan -> LessonScript
                                      |
                                      v
              [VisualTeachingPlan + BeatIntent + HeroAllocation]
                                      |
                                      v
                       [RepresentationRouter]
                         |                  |
                  generic patterns     domain adapters
                  diagram/graph/etc    executable trace / figure
                         |                  |
                         v                  v
                     [Typed VisualPatternSpec]
                                      |
                                      v
                [SceneGraph / ConceptRegistry / StateLedger]
                                      |
                                      v
                  [V3 Pattern Compiler + KeyframeLayoutPlan]
                                      |
                                      v
                   [MotionPlan + BeatVisualBinding]
                                      |
                                      v
              [Renderer Adapter: specialized bounded primitives]
                                      |
                                      v
        [Static QA -> Temporal QA -> Visual-Logic QA -> A/V QA]
                            |                  |
                      deterministic PASS   structured failure
                            |                  |
                            |          [ArtifactCritic]
                            |                  |
                            +---- [ArtifactRefine / scoped patch] ---+
                                      |
                                      v
                     governed output + provenance
```

**Ownership invariants:**
1. LLM/Hermes chooses *teaching intent and representation class*; NEVER raw x/y, arbitrary Python/JS or arbitrary render instructions.
2. ConceptRegistry owns lesson-level semantic identity and provenance. Stable IDs survive scenes and keyframes.
3. Domain adapter owns verifiable state transitions; general-purpose concepts are not forced into algorithm traces.
4. Constraint/layout compiler owns absolute placement, geometric interpolation and safe subtitle zones.
5. Renderer receives **validated typed plans** and uses only allowlisted primitives/assets.
6. Deterministic QA is a hard precondition. VLM critic may suggest typed patches and rationale, not mutate geometry/executable code.
7. A patch invalidates/rebuilds only registered downstream artifacts, with cache key and diff proof.
8. Critic unavailable ≠ PASS; unknown quality status must remain visible.
9. Core V2 frozen, V1 rollback preserved. Prefer V3-specific packages/adapters instead of changing frozen V2 internals.
10. Controls include bounded stage budgets, secret-safe allowlisted artifacts, timeouts, version locks, dataset immutability, read-only baseline checks.

### 3.1 Repository structure (target, not yet created)

```text
learnflow_v3/
  pedagogy/             # lesson objectives, mental-model prerequisites, hero budget
  visuals/
    contracts.py        # typed VisualTeachingPlan, PatternSpec, StateLedger
    patterns/            # bounded pattern compilers + eligibility
    routing.py           # representation selection with reasons
    assets.py            # allowlisted licensed asset references
  domain/
    algorithms/          # optional verified execution traces
    figures/             # region-grounded source figures
  layout/
    keyframes.py         # time-aware constraints
    temporal_preflight.py
  motion/
    grounding.py
    event_compiler.py
  render/
    adapter.py           # no generated arbitrary code
    specialized/         # svg/vector, charts, equations, code, etc.
  qa/
    semantic.py
    temporal.py
    artifact_critic.py
    artifact_refine.py
  governance/
    provenance.py
    publish_policy.py
benchmarks/learnflowbench/v3/  # new versioned corpus manifests, profiles, annotations
tests/v3/
scripts/verify_v3_*.py        # future commands; do not pretend they exist
PLAN_V3.md
```

No new implementation folders are authorized by this document alone.

## 4. Contract layer and lifecycle

### 4.1 VisualTeachingPlan (proposed schema v3.0)

Fields:
- `lesson_id`, `learning_objective_ids[]`, `prerequisite_refs[]`, `misconception_refs[]`.
- `sections[]` with `section_id`, `objective_refs[]`, `learner_state_before`, `learner_state_after`, `visual_teaching_goal`, `representation_options[]`, `visual_complexity_budget`, `hero_candidate`.
- `beats[]` with `beat_id`, `script_segment_ref`, `claim_refs[]`, `concept_refs[]`, `expected_visible_state_change`, `importance`, `allowed_static_justification`.
- `constraints`: language, learner level, duration, accessibility, cognitive load, cost/latency tiers.

Hard checks: objective/claim IDs resolvable, no unverified scientific assertion, no orphan beats, fixed section order, no contradictory example references. Numerically worked algorithm examples must have **one source of truth** (trace/input object) used by registry, script and visuals; no free-text duplicate independent target arrays.

### 4.2 VisualPatternSpec

```json
{
  "schema_version": "3.0",
  "pattern_id": "alg-search-example-01",
  "pattern_type": "WORKED_EXAMPLE_BOARD",
  "objective_refs": ["objective-search-01"],
  "source_refs": ["script:segment-02", "trace:search-24"],
  "concept_refs": ["concept:binary_search"],
  "state_source": {"kind": "VERIFIED_TRACE", "ref": "trace:search-24"},
  "semantic_objects": [
    {"object_id": "array", "kind": "SEQUENCE", "state_ref": "trace:search-24"},
    {"object_id": "search-window", "kind": "INTERVAL"},
    {"object_id": "mid-pointer", "kind": "POINTER"}
  ],
  "visual_constraints": {"reading_order": "LEFT_TO_RIGHT"},
  "fallback_family": ["STATIC_INTERVAL_DIAGRAM"],
  "renderer_requirement": "STATEFUL_SEQUENCE"
}
```

This is **illustrative future schema**, not code already shipped. All IDs must be resolvable, and any unknown enum/key is rejected.

### 4.3 BeatVisualBinding

```json
{
  "beat_id": "beat-discard-left",
  "claim_refs": ["claim-half-elimination"],
  "target_object_ids": ["search-window", "mid-pointer"],
  "expected_state_transition_ref": "trace:search-24/step-1",
  "time_anchor": {"source": "NARRATION_BEAT"},
  "acceptance": {"observable_change_required": true, "static_exception": null}
}
```

Always preserve ordered causality: **explain midpoint → compare → discard half → update interval → repeat**. The binding compiler must reject a validly timed but semantically unrelated pulse on a title.

### 4.4 KeyframeLayoutPlan + StateLedger

- `object_id` distinct from `concept_id`; canonical registry tracks symbolic meaning, StateLedger tracks value/state at each accepted step, LayoutPlan tracks geometry.
- Keyframes are sparse, keyed by `beat_id` or trace step; interpolation must preserve visibility, focus, minimum spacing, text-fit, object continuity and subtitle band.
- Solver samples endpoints **and intermediate frames**; no renderer-specific coordinates in upstream LLM output. Use deterministic trajectory interpolation with a declared easing/retiming scheme and collision certificate.
- Exact immutable source hash / compiler version / renderer version and derivation edges become part of a reproducible artifact manifest.
- Violations produce typed `SEMANTIC_DRIFT`, `VISUAL_LOGIC_DRIFT`, `TEMPORAL_OCCLUSION`, `UNSUPPORTED_REPRESENTATION`, or `RENDERER_UNAVAILABLE`; never collapse to generic PASS.

### 4.5 Artifact lifecycle

`DRAFT -> SCHEMA_VALID -> SEMANTIC_VALID -> FEASIBLE -> COMPILED -> RENDERED -> DETERMINISTIC_QA_PASS -> CRITIC_STATUS -> PUBLISH_CANDIDATE`.

Every transition stores signed-off validation reason/evidence. Publish policy accepts only versioned supported states; a VLM failure cannot silently elevate a `DETERMINISTIC_QA_PASS` into `CRITIC_PASS`. Test mutation/invalidation edges: altering example target must visibly propagate to trace, script binding, nodes, motion and MP4 hashes or fail closed before rendering.

## 5. Capability specifications and measurable hypotheses

All gains below are **preregistered candidate targets**, not measured performance. Default comparison: frozen V2 artifact or V3 ablation at *identical learning objective, script or source trace, renderer profile and seed where controllable*. Report failure rate and confidence intervals.

| ID | Capability / root cause | Prior-work anchor | Candidate gain to falsify | Dependency | Fail-safe fallback |
| --- | --- | --- | --- | --- | --- |
| C1 | Pedagogy Planner / R1 | Code2Video, Mayer | +10 pp paired expert pedagogy rubric vs current planning, no factual regression | contracts, fixed rubric | existing pedagogy plan + explicit low-confidence flag |
| C2 | Hero Scene allocation / R1, R4 | Code2Video key sections | +10 pp human key-moment clarity at matched render budget | C1, visual budget | uniform budget |
| C3 | Visual Director / R2 | Code2Video, EduVisAgent | representation appropriateness ≥4/5 median and > V2 | C1, C5 | typed simpler same-family diagram |
| C4 | Beat → Visual goal / R5, R6 | MINARD, LLM2Manim | essential-beat visual coverage ≥90% | C1, C3, C5 | explicit text+static reason or QA fail |
| C5 | Pattern Library / R2, R3 | ALGOGEN, DiagrammerGPT | specialized pattern usage ≥70% on eligible pilot lessons; low card collapse | C3, C9 | same-family static semantics; never silent universal card |
| C6 | Artifact Critic / R9 | Code2Video | +10 pp issue recall vs deterministic-only QA on labeled cases at bounded false positives | C5, C11 | explicit CRITIC_UNAVAILABLE; strict publish policy |
| C7 | ArtifactRefine / R7–R9 | Code2Video ScopeRefine | ≥70% recovery of injected errors without full-scene regeneration | C6, provenance | bounded rollback / blocked publication |
| C8 | Executable Trace adapter / R3, R7 | ALGOGEN VTA | 100% oracle trace agreement on deterministic fixtures; fewer visual state mistakes than direct prompt | C5, C9 | verified static trace table or fail |
| C9 | Semantic signal preservation / R7 | ALGOGEN RSL audit, LLM2Manim | 100% required-field mutation detection in fixed tests | foundational | fail closed |
| C10 | Fail-closed quality policy / R8, R9 | Code2Video failure analysis | 0 silent omissions / critic-unavailable-as-PASS | foundational | explicit blocked/degraded output |
| C11 | Keyframe layout / R4, R8 | OmniManim, SGA | 0 fatal sampled/swept overlap on fixed motion suite | C5 and motion compiler | nonmoving semantically faithful diagram |
| C12 | Beat-to-visual grounding / R5, R6 | MINARD, ManiBench | visual event alignment ≥90% on annotated essential beats | C4, C8, C11 | explicit unknown/mismatch QA failure |

**Interpretation:** ≥70%/≥90% are *proposed engineering pilot thresholds*, not human learning claims. Final quality thresholds require a pilot annotation reliability study and a recorded preregistration before comparisons. "PASS" on a single favorable lesson cannot establish population reliability.

### 5.1 C1 Pedagogy Planner design

Inputs: verified claims, learner profile, prior concepts, fixed lesson duration. Output: prerequisite DAG, misconception ledger, objective-to-segment mapping, before/after mental model, teaching sequence. Enforce no objective left unexplained, no unsupported pedagogical claim, and progressive disclosure. **Acceptance:** ablation with same rendering engine, expert blind review, exact mapping completeness, no deterioration in factual score. **Risk:** verbose plans without tangible gains; stop if impact not detectable under paired study.

### 5.2 C2 Hero Scene design

Allocate 1–3 `TeachingMoment` entries with budget share, needed representation/state transition and cognitive complexity; not simply "higher animation density". Respect total lesson cost. **Acceptance:** compare equal budgets with/without prioritized hero allocation, comprehension on target misconception and perceived focus; no regression in other sections. **Fallback:** fixed uniform allocation.

### 5.3 C3 Visual Director representation chooser

Typed `RepresentationChoice` contains candidate patterns, selection reasoning based on learning goal, eligibility constraints and rejected alternatives. The model may choose `FUNCTION_GRAPH` when explaining a function, not choose pixel coordinates. **Acceptance:** curated ambiguous-intent examples, independently scored appropriateness and reviewer disagreement. **Fallback:** deterministic rule/family path; clear abstention when no support.

### 5.4 C4 Beat visual-intent compiler

Classifies beats into essential semantic change, support/context, recap, voice-only transition. Each essential beat requires target objects and observable change; no gratuitous motion just to increase count. **Acceptance:** all essential beats have grounded traceable evidence or explicit justified exception, deterministic beat mapping preserved; measure correctness separately from timing. **Fallback:** static annotation with pedagogically valid persistence or BLOCK.

### 5.5 C5 Bounded visual pattern library + specialized renderers

Initial **minimum viable** supported families:
- `STATEFUL_SEQUENCE` / `WORKED_EXAMPLE_BOARD` (binary search, sorting, array walkthrough);
- `CODE_WALKTHROUGH` (syntax-aware code/line highlighting, variable state);
- `FUNCTION_GRAPH` + `EQUATION_DERIVATION` (typed mathematical objects);
- `PROCESS_FLOW` / `CONCEPT_DIAGRAM` (typed relations with arrows and time-aware emphasis);
- `QUIZ_REVEAL` + `SUMMARY_RECAP` (delayed reveal and deliberate, limited cards).

Later candidate families: `DATA_CHART`, `STATE_MACHINE`, `CAUSAL_GRAPH`, `TIMELINE`, `COMPARISON`, `GEOMETRY_CONSTRUCTION`, `FIGURE_WALKTHROUGH`. **Do not pretend all 15 are shipped in MVP**. Every pattern needs a schema, eligible content signatures, object semantics, 16:9 accessibility-safe constraints, renderer fixtures, motion-compatible state model, failure/degradation policy, and at least one human-reviewed golden clip. Reusing generic low-level drawing APIs is allowed; output visual semantics must differ materially. **Anti-card acceptance:** no silent card fallback for a supported stateful trace; archive histogram of pattern selection/fallback.

### 5.6 C6 Artifact Critic design

Inputs: sampled video frames + sampled transitions, time-indexed layouts, SceneGraph, `BeatVisualBinding`, source claims, object IDs, QA telemetry. Outputs: typed issues `{issue_id, time_range, object_ids, category, severity, evidence_frames, confidence, repair_route}`. Critic cannot emit executable code or geometry. Evaluate against human-labeled error corpus for precision/recall; enforce max reviewer budget. **Fallback:** deterministic-only status with critic unavailable, no implicit quality certification.

### 5.7 C7 ArtifactRefine design

Route issue to the *owning layer*: factual→Research/Fact/Script; representation→Visual Director/PatternSpec; symbol mismatch→registry; layout→solver; timing→Beat/Motion; subtitle→production adapter; visual aesthetics→bounded style tokens. Apply typed patch with input/output hashes; re-run dependent QA; untouched artifacts hashes must remain identical. Bounded attempts + no-op patch detection + rollback. **Acceptance:** seeded fault injection; no degraded semantic invariants; per-issue local-repair success and total cost vs full regeneration. **Fallback:** explicit blocked output.

### 5.8 C8 Executable Trace Adapter

Restricted algorithm domain only. Deterministically derive actual states from **allowlisted interpreter/simulator**; no arbitrary generated Python executed inside production by default. Verify input/preconditions, terminal result, invariants (`low<=high`, monotone shrinking interval, correct found target), and visual equivalence at each step. Binary Search oracle fixture must demonstrate both FOUND and NOT_FOUND, duplicates policy, empty array and sorted-input precondition; if unsorted, explain/reject instead of pretending binary search is valid. **Acceptance:** oracle match on preregistered diverse arrays; mutation test tampered mid pointer or dropped elimination step must fail. **Fallback:** annotated table of verified states.

### 5.9 C9 Signal-preservation contracts

All V3-critical fields must demonstrate causal signal propagation: mutate exactly one upstream semantic field and assert downstream typed artifact/compiled motion/render digest changes appropriately. Invalid refs, mismatched registry IDs and inconsistent worked examples stop before TTS. Guard against "accepted schema but ignored field" (RSL-style dead code). **Acceptance:** 100% of required mutation cases detected, no silent ignored fields, explicit provenance paths. **Fallback:** fail closed, not ignore.

### 5.10 C10 Publication quality state machine

Distinct `DETERMINISTIC_PASS`, `DETERMINISTIC_FAIL`, `CRITIC_PASS`, `CRITIC_FAIL`, `CRITIC_UNAVAILABLE`, `QA_ERROR`, `PUBLISH_BLOCKED`. Policy may publish deterministic-only outputs only under an **explicitly authorized** profile and clearly labeled quality tier; must never call critic unavailable "critic pass". Publication disabled in tests, no hidden retries, per-run budget and provenance. **Acceptance:** 0 bypass in fault matrix: critic outage, invalid cue, stale cache, unsupported pattern, unknown concept, partial scene. **Fallback:** retain artifact for debugging, block publishing.

### 5.11 C11 Temporal layout compiler

Layout solving and safety for sparse keyframes, in-between motion and cross-scene interpolation. Use analytical swept-volume conservative bounding boxes when supported and dense sampled frames for non-linear paths/text; require text-fit/occlusion at intermediate times, not merely endpoint feasibility. Motion budget rules prevent excessive visual load. **Acceptance:** deterministic collision corpus (including two crossing nodes, subtitle intrusion, morph/rescale text, label reflow), zero unreported critical overlap. **Fallback:** stop offending motion, render a semantically valid static diagram.

### 5.12 C12 Semantic beat-to-render proof

Record `(beat, claim, concept, trace_step, object IDs, expected delta, observed frame times)` as an audit graph. Observed state recognition uses renderer-owned object geometry/state where possible; use optional critic only for perceptual aspects. Define `VisualEventAlignment` as fraction of annotated essential beat events appearing within preregistered tolerance; define `BeatVisualCoverage` separately and report misses. **Acceptance:** binary-search elimination state actually vanishes/dims and pointers update when spoken, not title pulsing. **Fallback:** explicit QA error or accepted static exception with human rationale.

## 6. Research-critical benchmark design (no cherry-picking)

### 6.1 Benchmark tiers

**Tier 0 — offline deterministic fixtures:** each pattern's schema/compile/screenshot/golden state sequence; deterministic CPU baseline; no LLM spend.

**Tier 1 — paired fixed internal pilot (8–12 topics):** select before experiments from unchanged `corpus_v1.json`, stratify domains/difficulty, include Binary Search as historical audit but **not sole optimized evaluation**. Freeze topic IDs, script/reference evidence, acceptance rubric, seeds, cost ceilings and scoring procedure in `benchmarks/learnflowbench/v3/preregistered_pilot_v1.json` (future artifact). Never edit frozen corpus V1.

**Tier 2 — broader frozen evaluation (proposed 24–40 topics when budget approved):** matched V2/V3 and domain adapters, sample intentionally includes out-of-library concepts, longer lessons and difficult problems. Record failures on every attempt, not only successful videos.

**Tier 3 — optional 100-topic live study:** explicitly `DEFERRED`; do not trigger merely because PLAN_V3 exists.

**External references:** Code2Video MMMC-compatible subset and/or officially reproducible pipeline where resource/licensing permits; ALGOGEN only on algorithm-compatible cases; human-crafted references for bounded visual comparison, not identical production-cost comparisons. State mismatched benchmark boundaries. Freeze external versions/commits.

### 6.2 The evaluation matrix

| Axis | Primary metric | Protocol & failure |
| --- | --- | --- |
| Reliability | end-to-end complete valid MP4 / attempted runs | one denominator per preregistered trial, exact model+provider; no missing failures |
| Semantic | claim agreement, concept identity, trace-oracle correctness | typed artifacts + human spot check; any critical hallucination blocks |
| Representation | essential representation coverage, supported pattern selection, repeated-card collapse | count eligible scenes and choices; never optimize entropy alone |
| Geometry | fatal clipping/overlap/occlusion, swept temporal collision | frame sampling + deterministic geometry evidence |
| Temporal | BeatVisualCoverage, VisualEventAlignment, TemporalOrderAccuracy | blinded annotated essential beats and measured onset delta |
| Pedagogy | 5-point expert rubric: clarity, sequencing, misconception, knowledge check | ≥2 blinded raters, disagreements adjudicated |
| Visual quality | 5-point human rubric: hierarchy, readability, visual logic, pacing, consistency | rater agreement and per-domain breakdown |
| Outcomes | pre/post transfer and retention questions | optional consented matched human trial; UNMEASURED until performed |
| Cost | USD/tokens, wall-time, P50/P95, retries, renderer CPU/GPU | include failed runs and artifact critique/repair cost |
| Maintainability | invalidation precision, unaffected hash preservation, regression pass | mutation tests and profiler logs |

**Rubric anchors:** 1 unusable/wrong; 2 confusing; 3 understandable with noticeable limitations; 4 clear and well-integrated; 5 exemplary. Separate factual/logic from visual polish. Aesthetics cannot compensate incorrect knowledge. Inter-rater agreement via ordinal weighted kappa/Krippendorff alpha where practical, **reported** without assuming it will be high. Pre-register annotator instructions and pass/fail thresholds; VLM judge is an auxiliary diagnostic, never sole evidence of human educational quality.

### 6.3 Candidate V3 Core/Quality Gate (provisional)

**Hard safety gate (must all pass):** zero critical fact/identity errors on selected verification suite; zero fatal clipping, unreadable captions, broken MP4/AAC, missing expected scenes, unsafe secret export, unverified trace-state transition, invalid schematic geometry, silent critic bypass. Replay deterministic fixtures reproduce exact semantic hashes and manifest completeness (video byte hashes may differ due to encoder metadata; define normalized frame/audio comparison).

**Quality gate, to preregister before scoring:** on matched pilot topics, V3 must beat V2 on **human visual explanation clarity** and **representation adequacy**, with no decline in factual correctness, legibility or perceived cognitive load; report effect sizes/paired confidence intervals, not just averages. Investigate across domains and provide negative cases. One successful Binary Search is only a smoke demonstration, not the gate.

**Release gate:** pilot success + representative suite + independent quality audit + budget approval + rollback rehearsal. No unqualified ≥98% reliability until a sufficiently powered study justifies a bound; 100 successes alone cannot prove 98% with high confidence.

## 7. Controlled ablation studies

| Ablation | A vs B (fixed controls) | Primary attribution question |
| --- | --- | --- |
| E1 | V2 frozen baseline vs same pipeline with only semantic guards | does tighter validation reduce drift without lowering usable coverage? |
| E2 | V2 generic card vs one V3 specialized pattern, same script/audio | does representation itself improve comprehension/readability? |
| E3 | baseline pedagogy plan vs C1 planner, same renderer and content budget | does planning add pedagogical value? |
| E4 | uniform animation vs C2 hero allocation, same total render time | does selective focus improve learning? |
| E5 | ungrounded motion cues vs C4/C12 grounded cues, same content | are crucial state changes observable at narration times? |
| E6 | static layout vs C11 keyframe-aware layout | fewer intermediate collisions without damaging continuity? |
| E7 | freeform prompted algorithm state vs C8 validated trace | correctness of sequence and final result |
| E8 | full regenerate vs C7 local repair on identical injected defects | repair recovery, cost, hash reuse, time |
| E9 | deterministic QA alone vs same + C6 critic | additional true issue detection and false alarm rate |
| E10 | V3 specialized pattern vs human-referenced clip where legally valid | residual quality gap; no SOTA conclusion |

Randomize order and blind human evaluators to system identity. If paired data sparse, report confidence intervals and "insufficient power" rather than binary significant superiority. Publish negative results and failure taxonomy.

## 8. Build order: dependencies, checkpoint ledger and stop/go

**One checkpoint at a time.** Every checkpoint requires: exact code scope, invariant tests, a reproducible command, at least one real rendered artifact when relevant, performance report, CI link, changed-file diff and one reviewer decision. Historical checkpoint commands are a planning snapshot, not evidence of execution; use the actual script paths (corrected for V3-00/V3-07) and respective CI runs.

| Checkpoint | Dependency | Required deliverable and acceptance | Repro command after implemented |
| --- | --- | --- | --- |
| V3-00 Baseline & Merge Gate | #181 and offline #4 | lineage audit, complete V2 evidence manifest, protected Core hash, branch strategy, **upstream reuse/license inventory**, preserved historical #181 | `python scripts/verify_v2_core_freeze.py` (V3-00 alias never implemented) |
| V3-01 Benchmark preregistration | V3-00 | frozen topic IDs, pilot rubric, control variables, human protocol and limits; no data leakage | `python scripts/verify_v3_benchmark_protocol.py` |
| V3-02 Canonical semantic contracts | V3-00 | Versioned VisualTeachingPlan/PatternSpec/StateLedger, ID/ref validation, three-way worked example agreement | `pytest -q tests/v3/test_contracts.py` |
| V3-03 Signal-preservation proof | V3-02 | mutation dependency/canonical hashes; ignored fields fail, no frozen V2 edit | `pytest -q tests/v3/test_signal_preservation.py` |
| V3-04 Visual Pattern Router | V3-02,03 | bounded eligibility/abstention; cards only deliberate recap; deterministic examples | `pytest -q tests/v3/test_pattern_router.py` |
| V3-05 Binary Search Trace Adapter | V3-02,03 | sorted-array oracle, mid/low/high, duplicates policy, found/not-found, edge cases | `pytest -q tests/v3/test_binary_search_trace.py` |
| V3-06 Stateful Sequence Renderer | V3-04,05 | real MP4 shows pointer/window changes over narration, no generated renderer code, verified equivalent frames | `python scripts/verify_v3_binary_search_render.py` |
| V3-07 Code + Process renderers | V3-04 | line/variable walkthrough and typed DAG/flow, actual non-card pixels + fixture demos | `python scripts/verify_v3_code_process_render.py` |
| V3-08 Math renderers | V3-04 | typed equation/graph transformations, axis/label safety, no brittle text-only substitute | `python scripts/verify_v3_math_patterns.py` |
| V3-09 Pedagogy + Hero Planner | V3-01,04,06 | source-grounded objective/misconception/teaching moments, fixed-budget ablation | `pytest -q tests/v3/test_pedagogy_planning.py` |
| V3-10 Beat-Visual Grounding | V3-03,06,09 | traceable essential beats and rendered changes, negative timing fixtures rejected | `python scripts/verify_v3_beat_grounding.py` |
| V3-11 Temporal Geometry | V3-06,10 | all sampled/swept states satisfy hard constraints, subtitles safe | `python scripts/verify_v3_temporal_geometry.py` |
| V3-12 Fail-closed QA & Publication | V3-03,10,11 | explicit critic status, zero bypass under fault injections | `pytest -q tests/v3/test_publish_gate.py` |
| V3-13 Artifact Critic | V3-01,12 | strict issue schema, human-labeled issue recall/precision, outage handled | `python scripts/verify_v3_artifact_critic.py` |
| V3-14 ArtifactRefine | V3-03,12,13 | typed local changes, invalidation correctness, 0 silent no-ops, rollback | `python scripts/verify_v3_artifact_refine.py` |
| V3-15 Pattern expansion | V3-06–14 | only add families with demonstrated demand and new golden clips | `python scripts/verify_v3_pattern_coverage.py` |
| V3-16 Human pilot/ablation | V3-01,06–14 | prerecorded topic/rater protocol, blinded comparisons, CI/effect sizes, cost | `python scripts/verify_v3_evaluation_manifest.py` |
| V3-17 Release candidate & rollback | V3-16 | complete artifact provenance, reproducible build, restore V2, permissioned release decision | `python scripts/verify_v3_release_gate.py` |

**Sequencing constraint:** V3-06 (a correct dynamic teaching clip) is the **first material proof**. Stop and reassess after V3-06 if the stack still produces mainly cards or cannot show correct state updates; do **not** build more agents to hide it. Later patterns may run in parallel only after baseline contracts are stable, but their gates must stay individually inspectable.

### 8.1 Checkpoint template (mandatory)

```text
Identifier + motivation/root cause
Prior-work evidence and the remaining technical gap
Upstream reuse/license audit: import vs adapter vs vendor vs new code
Parent commit and allowed files
Typed schema / invariants / ownership boundary
Implementation diff and renderer artifact if relevant
Positive, negative, fuzz/property, mutation and rollback tests
CLI command with exact environment/seed/version
Measured metrics vs frozen baseline and budget
Expected fallback and hard failure behavior
Reviewer attacks + explicit GO / FIX / NO-GO
Next SINGLE checkpoint (with ready-to-send coding-agent prompt)
```

### 8.2 First agent task (after explicit approval to implement)

```text
Audit and resolve the V2D branch-to-main integration boundary before writing V3 code.
Work only on the user-approved branch; do not touch frozen V2 Core, main, or #181 artifacts.
Compare main to chatgpt/live-v2d-gpt6-luna-paid-pilot at pinned commits.
Classify every unmerged change as KEEP, ISOLATE-EXPERIMENTAL, SUPERSEDED, or EXCLUDE.
Protect all V2 benchmark fixtures and data; run Core Freeze and offline regressions.
Produce a merge-readiness report with per-file inventory and selected target base.
Also audit reusable upstream components, pinned commits, licensing and integration-vs-reimplementation tradeoffs under section 8.3.
Do not merge without authorization; do not call paid APIs.
If blockers exist, stop with an evidence-backed FIX proposal.
```

### 8.3 Reuse-first implementation policy — mandatory before every V3 checkpoint

**Decision (2026-10-08): REUSE → ADAPT → IMPLEMENT FROM SCRATCH.** Do not rewrite mature, fit-for-purpose modules merely to follow the planned architecture. Preserve the established V2 typed/renderer-neutral boundary while borrowing implementation proven elsewhere.

**Selection priority:**
1. **Reuse existing LearnFlow V2** capabilities from versioned, frozen public APIs via V3 adapters (layout solver, collision metrics, motion, subtitles, ffmpeg assembly, provenance, renderer primitives). Do not modify frozen Core.
2. **Reuse maintained open-source libraries as pinned dependencies** when their license, API, performance and output can be verified. Example: use Manim Community as an **optional bounded rendering backend**, through trusted templates and typed plans, *not* by letting agents execute arbitrary generated Python.
3. **Vendor/copy small, well-isolated third-party modules** when direct dependencies would be unnecessarily heavy or the module requires adaptation. Preserve upstream copyright notices, required LICENSE text, source URL, pinned commit, modification notes and local regression tests; prefer a wrapper when possible.
4. **Write only the genuinely missing glue/novel logic** (typed representation compilation, identity-preserving trace binding, frame/beat proof, governance) or when an existing library fails compatibility/performance/security gates. Provide evidence before selecting from-scratch.
5. **Never treat a public repository as automatically reusable.** If license is absent, ambiguous, incompatible, or specific assets have different terms, classify source as **STUDY ONLY / LICENSE BLOCKED** until permission or a compatible license is established. No copying code or assets while blocked.

**Initial audited external candidates (candidate, NOT integration approval):**

| Repository / source | License finding on 2026-10-08 | Candidate modules or mechanisms | Allowed decision today |
| --- | --- | --- | --- |
| [Code2Video](https://github.com/showlab/Code2Video), commit `1142d8e14cdc2806df85aedb0fbb5dca474caa0f` | MIT at repository root | `src/scope_refine.py`, `src/agent.py`, `src/eval_AES.py`, `src/eval_TQ.py` — review for bounded scope repair, planning/evaluation, prompt contracts | **REUSE/ADAPT CANDIDATE** after line-level dependency, test, compatibility and attribution audit; generated arbitrary Manim code cannot become canonical LearnFlow IR |
| [Manim Community](https://github.com/ManimCommunity/manim), commit `23ae68f4dd5817d49760b338e14b92757a2369b5` | MIT repository license | mature vector objects, equations, graph/geometry animation, composition | **OPTIONAL BACKEND CANDIDATE**, compare full install cost and deterministic render against existing Pillow/FFmpeg stack; avoid assuming all sample assets have permissive licenses |
| [ALGOGEN-lab](https://github.com/MAC-AutoML/ALGOGEN-lab), commit `1bb093c76499135ecf54fc8030219a4e7ee4424c` | **NO LICENSE DECLARED / NO ROOT LICENSE FILE FOUND** in inspected public repository | `renderer/`, `toolmaker/`, VTA/RSL trace design, validation ideas | **STUDY ONLY; DO NOT COPY SOURCE** without documented license/permission. Independent implementation of ideas is distinct from copying source code |
| LearnFlow existing V2 modules, pinned by current integration base | project-owned | `learnflow_v2/layout`, `motion`, `render`, `qa`; `lesson_pipeline`, `visual_director` | **REUSE FIRST through compatibility adapters**, preserve Core Freeze |

**Candidate audit required per checkpoint before code modifications:**

```text
Feature and acceptance contract
=> search internal V2 implementation and 2-5 strongest maintained upstream options
=> inventory exact module/file/function, pinned SHA, license & transitive/asset licenses
=> run minimum upstream tests/smoke on pinned version and inspect real output
=> compare API/schema fit, determinism, rendering quality, security, dependency footprint
=> score REUSE_DIRECT | WRAP/ADAPT | VENDOR_SUBSET | REIMPLEMENT | DEFER/UNLICENSED
=> justify chosen method with evidence, estimated integration effort and maintenance cost
=> record origin, authorship/NOTICE, changes, regression commands and rollback path
```

**Mandatory acceptance for reused code:** project-owned typed interface remains the authority; new adapter has positive, negative, determinism and visual-golden tests; no arbitrary code execution; no secret exfiltration or unallowlisted network calls; quality at least matches a measured baseline; project dependency budget and LICENSE/NOTICE files are respected. The fact that a feature renders in upstream demos is not enough.

**Checkpoint alignment:**
- **V3-00** extends its audit to a **pinned upstream component/reuse inventory** and merge-safe integration recommendations. This audit is **documentation and inspection**, not dependency installation or vendor-copy authorization.
- **V3-02–05** first seek typed schemas/state/trace logic already owned by V2 and maintained packages. ALGOGEN algorithms can inform tests/contract design, not supply code until permitted.
- **V3-06–08** explicitly compare existing renderer+adapter, bounded Manim backend, and any small reusable Code2Video renderer utilities before building a renderer from scratch. Include a short vertical spike and side-by-side output.
- **V3-09–14** review Code2Video planning/ScopeRefine/evaluation modules before re-creating their mechanisms; adapt them to typed artifact IDs and fail-closed QA.
- **Every coding-agent prompt** must include: "Inspect reusable upstream implementation and license first; identify exactly what to import/wrap/vendor and what remains genuinely new. Do not reimplement without evidence."

**Optimization criterion:** minimize **total validated engineering time**, not lines of handwritten code. Prefer direct reuse when stable and testable, but choose small in-house adapters over pulling in a large incompatible framework. Measure correctness, visual quality, runtime, dependency size and ongoing repair burden.

## 9. Branch migration and V2 compatibility gate

**Observed 2026-10-08:** `main` at `29fab1d5738ccb060502c8ae82e2e31f00360811`. Paid pilot at `efd19bc4bb3b8f2bf8e79ea50cf3e4e7e10c6b53`, **24 commits ahead, 0 behind** (ancestor relationship; not a merged state). Most earlier V2/Hermes PRs through #32 are merged. Old branches may show divergent history due to superseding/cherry-pick/squash changes; a divergent branch is **not proof** that its substantive feature is absent from main.

**Integration protocol:**
1. Freeze target SHA and branch catalog; list file-level diff and PR provenance.
2. For each pilot file choose: **KEEP production fix / KEEP V2 historical documentation / ISOLATE paid-only adapter / SUPERSEDED / EXCLUDE**. The paid-only routing and model policy must not become main's default.
3. The new semantic guard and redacted exporter should be ported only after verifying their scope, actual auth-file exclusion and fail-closed behavior.
4. Compare new CI impact. Safe online workflows must be explicitly non-spending on push; protect from unintended billable calls.
5. Apply integration **only after user authorizes merge**; run all tests plus an offline Core Freeze check on candidate merge commit before advancing main.
6. V3 development branches off a reviewed integration base; keep frozen V2 and historical #181 accessible and versioned.

**Known PR details:** #8 closed-unmerged (superseded renderer), #11 open older renderer/benchmark PR, #14 closed-unmerged (superseded Core Gate evidence); inspect content, do not blindly merge. #1–#32 other PRs were merged according to GitHub status on review date.

**Rollback:** preserve V2 default route and video renderer in parallel; feature flag `LEARNFLOW_V3_ENABLED` defaults false until release gate. Rollback means flipping versioned routing, not deleting history or rewriting data. V3 ArtifactManifest has full hash chain; never migrate old artifact schemas in place.

### 9.1 V3-00 audit result (2026-10-08)

**Audit PASS, full branch merge NO-GO.** Pinned main `29fab1d` vs pilot before audit `a1e4e8b`: 27 commits, 23 files; per-commit/file decisions, licensing and C1–C12 reuse inventory recorded in `reports/v3_00_baseline_merge_gate.md` and `reports/v3_00_reuse_inventory.json`. Fresh offline run [37725705499](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37725705499) passed: V3-00 inventory, Core Freeze, live-eval contract, 87 regression tests, 14 renderer tests (5 skipped). No paid workflow ran. The only authorized proposed follow-up is **V3-00B (selective integration candidate)** if the user explicitly approves; do not merge main or implement V3-01 as a side effect.

### 9.2 V3-00E approved integration and post-merge gate (2026-10-08)

**PASS.** [PR #33](https://github.com/wterrr/vibecode_challenge_mb/pull/33) merged with commit `be19b4819b8c23c19713b6351d384411b29bf29b`; selective production-safe V2D fixes only, **not** paid pilot defaults. All 11 PR checks and all **10** main-merge checks passed. On merge commit: [offline gate 37728464626](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37728464626) yielded Core Freeze PASS, V2D Contract PASS, 82 test passes and renderer 14 PASS / 5 SKIP; [Governed Live push 37728464657](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37728464657) **skipped** the provider job. Default model remains free; historical #181 is unchanged. See `reports/v3_00e_post_merge_verification.md` and the canonical research continuity file. V3-01 is **not** yet implemented; the next checkpoint must be separately authorized.

### 9.3 V3-01 Benchmark Preregistration result (2026-10-08)

**Protocol/offline PASS; experimental V3 performance UNMEASURED.** Twelve exact topics (2 per domain, 4 per difficulty) are frozen under `benchmarks/learnflowbench/v3/preregistered_pilot_v1.json` with immutable corpus SHA-256, deterministic SHA-256 sampling, blind 1–5 rubric, no selective failures, paired V2D/V3 controls, and preregistered engineering thresholds. Previously exposed Binary Search `lfb-005-cs` is diagnostic-only, not a confirmatory primary topic. The free-only model policy is a proposed future control, **not a live model probe or a provider call**. [V3-01 offline gate #37729383829](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37729383829): `V3_BENCHMARK_PREREG=PASS`, 24 tests PASS, original LearnFlowBench contract PASS, Core Freeze PASS. No actual ratings, renders, student outcomes, paid usage or SOTA conclusion are claimed. Details: `benchmarks/learnflowbench/v3/PROTOCOL.md` and `reports/v3_01_benchmark_preregistration.md`. Next single checkpoint: **V3-02 Canonical Semantic Contracts**, subject to user authorization; no V3-02 implementation is part of V3-01.

### 9.4 V3-02 Canonical Semantic Contracts (2026-10-08)

**V3-02 offline PASS, pending PR review.** New independent `learnflow_v3/` typed contracts (`VisualTeachingPlan`, `VisualPatternSpec`, `StateLedger`) with version `3.0`, deterministic content hash, bounded enums, no arbitrary renderer instructions, strict canonical `concept_id + canonical_key`, scene/script/claim/objective/beat/state-source coverage and ordered ledger states. The cross-artifact validator **reuses** frozen V2 `ConceptRegistry`, `SceneGraph`, `LessonScript`, `Storyboard` and the narrow numerical #181 drift gate. An unverified trace is rejected, but supplying a trace ID is **not** a proof of algorithm correctness; no renderer or V3-03 signal proof was built. Offline run [#37730308809](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37730308809) at `e5acf5534f79548d3598d45dc02776828bb6a16b`: **20 V3 tests, 36 V2 registry/graph, 58 agent/semantic tests PASS**, V3-01 prereg PASS, LearnFlowBench PASS, Core Freeze PASS; no provider calls. See `reports/v3_02_canonical_semantic_contracts.md`. Dependency: PR #34 (V3-01) is still not merged; keep this V3-02 PR stacked over the V3-01 branch. Do not merge `main` or implement V3-03 automatically.

### 9.5 V3-03 Signal-Preservation Proof (2026-10-08)

**Offline gate PASS at `d9ac97020b83734e3095d36b4619c34e471e2aef`**; [run #37731881901](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37731881901) reports 39 V3 contract/signal tests, 39 V2 repair/registry/SceneGraph tests, 28 existing agent/semantic tests, V3-01 preregistration PASS, LearnFlowBench PASS and Core Freeze PASS. This is a **bounded semantic-input audit and hash invalidation test**, not proof of rendered frame consumption. The new `learnflow_v3/signal_preservation.py` classifies each serialized V3.0 artifact leaf into **SEMANTIC_GATED** (used by the existing typed validation chain) or **DECLARED_UNCONSUMED** (explicit future owner); unknown leaf keys fail. Audit/semantic-gate fingerprints are separated: a deferred state/visual intent mutation changes the audit/source hash but **must not** falsely change the semantic-gate consumer hash. `require_render_consumption()` always rejects in this checkpoint, even if no deferred field is present, because no actual renderer proof exists. Baseline V2 `compute_content_hash` reused; CP2.13 `ArtifactIndex` reviewed but not repurposed for V3 types because its `ArtifactKind` is frozen V2-only. Verified-trace declarations themselves are fingerprinted as inputs, **not** accepted as an algorithm oracle. No V3-02/renderer/frozen Core rewrite. Report: `reports/v3_03_signal_preservation_proof.md`. V3-03 branch is stacked over PR #35 (which remains stacked over PR #34); no `main` merge authorized. **V3-04 Pattern Router not started**.

### 9.6 V3-04 Visual Pattern Router (2026-10-08)

**PASS — offline bounded semantic pattern selection, explicitly NOT render-ready.** New `learnflow_v3/pattern_router.py` routes only the four **existing** V3-02 representation families `WORKED_EXAMPLE_BOARD`, `PROCESS_FLOW`, `EQUATION_GRAPH`, `CONCEPT_CARD`, with hard eligibility from typed plan/objects, ledger/trace, V2 `SceneGraph.layout_intent`/purpose/topology and the existing Visual Director gate. Fallback variants stay in the **same** family, and branching process graphs are never flattened to a linear process when network budget is insufficient. Generic cards are allowed only as explicitly requested static SUMMARY/RECAP with LABEL objects; no implicit CONCEPT_CARD fallback. Unknown/unsupported material → `ABSTAIN`; eligible decision → `SELECTED_UNRENDERABLE` with `render_ready=False`. V3-03 `audit_signal_preservation()` recomputes source evidence, and V2 `compute_content_hash` binds decision provenance. No renderer, pattern library art, visual golden clip, TTS or new live model calls were added. [Offline CI #37732962363](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37732962363): 60 V3 / 39 V2 / 46 Hermes tests passed, V3-01 prereg PASS, LearnFlowBench PASS, Core Freeze PASS. **PR base is PR #36** (stacked on #35 and #34), not `main`. Full reuse/limitations: `reports/v3_04_visual_pattern_router.md`. The next single checkpoint is **V3-05 Binary Search Trace Adapter** only after explicit authorization.

### 9.7 V3-05 Binary Search Trace Adapter — independently checked oracle (2026-10-08)

**OFFLINE PASS, no renderer:** Added `learnflow_v3/binary_search_trace.py` with immutable typed input, inclusive `low/high`, overflow-safe floor `mid`, LEFTMOST duplicate policy, explicit `COMPARE/COMPLETE` states and `FOUND/NOT_FOUND` outcomes. The **producer** runs a deterministic leftmost binary search; a **separate verifier** replays every observed step (state, comparison, direction, bounds, candidate and terminal status), checks the immutable trace fingerprint and independently cross-checks its result against Python standard-library `bisect_left`. The verifier must be called even when a `VERIFIED_TRACE` label or SHA-256 exists; neither alone certifies truth. `to_binary_search_state_ledger` writes a V3-02 ledger only after verification and requires exact beat alignment. `verify_binary_search_ledger` recomputes full state snapshots, and `certify_and_route_binary_search` re-verifies **both** trace+ledger and matches an explicit numeric example in lesson script and storyboard (plus any registry label mentioning it) before granting V3-04 a verified-ref declaration. Missing/contradictory example fails. Empty input has a legitimate terminal-only trace but does not manufacture animation states: insufficient teaching beats fail rather than inventing them; V3-04 remains `SELECTED_UNRENDERABLE` or abstains. Fully offline [#37735803537](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37735803537): **108 V3 tests PASS, 39 V2, 46 Visual Director/semantic**, V3-01 prereg PASS, LearnFlowBench PASS, Core Freeze PASS, zero provider calls. Report `reports/v3_05_binary_search_trace_adapter.md`. **Stacked dependency:** PR #34→#35→#36→#37→V3-05, no `main` merge. **V3-06 is NOT implemented**, and no MP4/frame correctness or universal natural-language binding is claimed.

### 9.8 V3-06 Stateful Sequence Renderer: real decoded MP4 proof (2026-10-08)

**Engineering/offline PASS** on source `51f55c6c60b7e0529f1b038f98389b5ab1723800`, verified by [run #37737754838](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37737754838): **123 V3 tests**, **39 V2**, **46 Visual Director/semantic** PASS, frozen prereg, LearnFlowBench and Core Freeze PASS. **Five real H.264 MP4s** (duplicate, missing, singleton, empty, left-boundary), **960×540 at 18 fps**, exported with golden PNGs and machine-readable hash/provenance/decoded-frame proof as [GitHub artifact 11532153065](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37737754838/artifacts/11532153065). Duplicate video: 56 frames/3.11 s, max decoded-vs-expected frame MAE 0.81 (0–255 per-channel), minimum adjacent step semantic ROI change 1.85; stable array centers, pointer/window updates visible. **Trust boundary:** V3-05 `certify_and_route_binary_search` verifies trace, full StateLedger and explicit spoken/script/storyboard example **before rendering**; never accept caller-declared `verified_trace_refs` directly. Immutable object locations across frames, bounded ≤16 visualized items, 16:9 geometry, no-clobber output, label overflow fail-closed, no default card fallback. Reused project Pillow/FFmpeg rendering stack and brand palette without V2 eager import side effects; did **not** import Manim/Code2Video/ALGOGEN or copy unlicensed source. Manim and Code2Video are MIT upstream, SHA-pinned in reuse inventory; ALGOGEN is study-only. This is first material dynamic-pixel proof, **not** proof of human comprehension, audio narration (caption-only), or V3-11 global swept-time geometry. Full reproducibility/audit `reports/v3_06_stateful_sequence_renderer.md`. Branch stacked on open PR #38; no `main` merge, no paid/free LLM call, no V3-07 work.

### 9.9 V3-07 Code + Process Renderers — Computer Modern blackboard visual standard (2026-10-08)

**Bounded offline engineering PASS (not a full pedagogy or end-to-end generation claim).** User-provided 3Blue1Brown Sigmoid frame guided the **visual language only**: background `#000000`, Computer Modern Unicode installed as OS `fonts-cmu`, real **CMU Serif** title/labels and **CMU Typewriter Text** code. `learnflow_v3/blackboard_style.py` refuses font substitution; never packages or publishes font files. The existing V3-06 Binary Search renderer was updated **within the V3-07 branch** to the same blackboard style; frozen V2 remains unchanged.

New `learnflow_v3/code_process_renderer.py` contains two **specialized bounded** typed renderers: (1) `CODE_WALKTHROUGH` with immutable code-line IDs, AST-allowlisted integer assignment replay, variable snapshots and moving line indicator (never `eval`/`exec`/LLM Python); (2) `PROCESS_FLOW` with frozen V2 `SceneGraph` node/edge IDs, replay-checked directed edges, DAG layered layout and in-beat highlighted edge traversal preserving branching topology. Each video is true H.264/MP4 encoded via FFmpeg, verified by decoding frames, per-step pixel comparison, **intra-beat motion** and geometry/identity guards; no default CONCEPT_CARD. Reuses V2 SceneGraph and layout semantics, V3-06 FFmpeg+Pillow decoded QA, V2 deterministic source hashing. Code2Video and Manim licenses pinned MIT in existing reuse inventory but not copied; ALGOGEN remains license-unclear study-only.

[CI #37740790915](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37740790915) on code `75b28e5c4ed7b344f252c0e1f99c7ae0134de747`: **146 V3 PASS, 39 V2 PASS, 46 Visual Director/semantic PASS**, V3 benchmark prereg, LearnFlowBench and Core Freeze PASS; **2 MP4 golden** at 960×540/18fps, Code 56 frames 3.11 s, Process 42 frames 2.33 s, [artifact #11533433759](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37740790915/artifacts/11533433759). Encoding/decoding measurements Code MAE max 0.191, Process 0.204 (8.0 cutoff), minimum inter-step ROI deltas 2.740/2.173, intra-beat decoded motion 0.606+/0.450+; SHA-256 validated against downloaded artifact. **Limit:** finite code interpreter supports bounded integer assignment only, process routing validates one trace path and static graph, no narration audio or exhaustive 3B1B aesthetic parity, and standalone Code/Process adapters have not yet been inserted as first-class V3-02/V3-04 lesson-wide patterns (integration must be separately gated). This is real visual motion proof, not human comprehension evidence or general-content success. Full report: `reports/v3_07_code_process_renderers.md`. PR stacked on #39; no `main` merge, no V3-08 implementation or paid model.

### 9.10 V3-08 Function Graph + Equation Derivation Renderers (2026-10-08)

**BOUNDED ENGINEERING PASS (code-head verification); final documentation commit CI pending.** Branch `chatgpt/v3-08-math-blackboard-renderers` stacked directly on PR #40 HEAD `960ac1d77e98520d91f7fc03be44a6967c5206cd`; no main merge. New `learnflow_v3/math_renderer.py` provides finite polynomial FUNCTION_GRAPH (degree ≤2, replayed points and analytic extremum bounds) and EQUATION_DERIVATION (exact allowlisted AST polynomial equivalence per transformation, typed V2 graph edges). Reuses frozen V2 SceneGraph/compute_content_hash, existing V3-06 Pillow+FFmpeg decoded QA and V3-07 true black + CMU fonts. All model/source/step/edge mismatches fail closed; no arbitrary generated code executes and no CONCEPT_CARD fallback. Two real MP4s/PNG/JSON are required through `scripts/verify_v3_math_patterns.py` and `.github/workflows/v3-math-patterns.yml`. See `reports/v3_08_math_patterns.md`. **Code SHA ff6c133 PASS; documentation commit requires rerun.** No V3-09, provider calls, frozen Core/benchmark edits or main merge.


**V3-08 measured engineering gate:** [7/7 code-HEAD checks SUCCESS](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37745752422) at `ff6c1339e2e65f92a84365ae2d85a98b68781b74`, with 170 V3 / 39 V2 / 46 semantic tests, V3 prereg/benchmark/Core Freeze PASS and [two verified MP4s](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37745752422/artifacts/11535822025). Function graph: 70 frames, MAE max 0.212; equation derivation: 42 frames, MAE max 0.093. SHA checks match. **V3-08 bounded renderer PASS, not lesson-wide production PASS.** PR #41 still open stacked on #40; documentation-only final commit requires its own CI. Next V3-09 only by explicit user authorization.

### 9.11 V3-09 Pedagogy + Hero Planner (2026-10-08)

**BOUNDED OFFLINE ENGINEERING PASS on implementation SHA `18c551eb74173c42c898cf2e20f117974dab8dbf`; final documentation/PR-head CI needs reconfirmation.** Stacked branch `chatgpt/v3-09-pedagogy-hero-planning` based on PR #41 HEAD `8d2dffccd572fdedb69d0d600cae25ce159a4585`; no `main` merge or frozen V2 edits. New `learnflow_v3/pedagogy_planner.py` **reuses** existing Hermes Pedagogy/Script/Fact gates, V2 evidence/registry/hashing and V3-02 visual beats. Strictly binds all objectives to script segment/beat/probe IDs and every misconception to an approved-claim correction actually present in script text. Prerequisite DAG accepts explicitly declared edges only; no inferred knowledge. Deterministic 1–3 hero teaching moments are eligible only from evidence-bound dynamic, non-card beats and section declarations. Same-source, **same-total-budget** uniform vs hero allocation is mechanically compared without pretending human gains: fixture 10 units, uniform `5/5`, hero `8/2`, three transferred, `human_learning=UNMEASURED`. No renderer/audio/MP4 pipeline integration, no prospective human pilot. [Offline CI #37747346591](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37747346591): **129 V3, 40 Hermes Pedagogy/Script, 39 frozen V2 PASS**, preregistration, LearnFlowBench and Core Freeze PASS; [JSON proof artifact #11536880070](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37747346591/artifacts/11536880070). Scientific limits and negative mutation matrix: `reports/v3_09_pedagogy_hero_planning.md`. **Do not equate allocation-unit redistribution with C1/C2 effectiveness (+10 pp): V3-16 human/rubric test remains pending.** Review-only stacked PR; exactly one next checkpoint after authorization: **V3-10 Beat-Visual Grounding**.


### 9.12 V3-10 Beat-Visual Grounding (2026-10-08)

**Bounded offline engineering PASS on implementation SHA efba673a7db0a908af3cabfe632b32381b176c2f; final report-only HEAD CI requires recheck.** PR #43 candidate branch chatgpt/v3-10-beat-visual-grounding stacked on PR #42 head dbfaf278fb1f35960f6df57c4afe5e7b90d90bbc. Reuses V3-05 bisect/replayed trace and script/storyboard/StateLedger certification, V3-06 actual blackboard Pillow+FFmpeg and decoded frame tools; no new agent, no upstream copied code, no frozen V2/Core/benchmark/provider/model edits. New learnflow_v3/beat_grounding.py binds immutable ordered source beat/segment/claim/object IDs to exact V3-06 fixed renderer frame windows, validates video SHA, H264 codec/frame count, and compares three actual decoded anchors within each beat against certified expected state. Essential state changes need semantic array/pointer ROI motion, not title pulses; terminal static exceptions require true source terminal. Shifted/frozen/foreign video and stale/faked timing/source metadata must fail closed. Real golden [CI #37748958808](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37748958808): **146 V3, 39 frozen V2, 86 Hermes PASS**; preregistration, LearnFlowBench, Core Freeze PASS; three H264 clips for duplicate (4 beats, 3 dynamic), missing (4, 3 dynamic), empty (1 terminal, 0 dynamic) with [actual artifact #11537500473](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37748958808/artifacts/11537500473), decoded MP4 SHA comparison independently checked. Machine-recorded worst sampled ROI anchor MAE: 2.156, 1.682, 0.133 respectively (0–255 pixel channels). **Scope: only renderer-synthetic Binary Search beat clock; no real narration/audio sync, no universal Code/Process/Math integration, no independent semantic-CV/human study.** Measured dynamic coverage 6/6 on two non-empty golden clips, not C12 ≥90% on representative annotations. Details: reports/v3_10_beat_visual_grounding.md. No V3-11 implementation. One next separately approved CP: **V3-11 Temporal Geometry**.


### 9.13 V3-11 Temporal Geometry (2026-10-08)

**BOUNDED OFFLINE ENGINEERING PASS on code SHA cd65c8765205a09c2b3b86451762514918ca4332, final documentation HEAD CI needs verification.** Stacked review-only branch chatgpt/v3-11-temporal-geometry from PR #43 HEAD 5f7314584248a6b95d447a71b616a49577593502. Reused frozen V2 Rect intersection/canonical source hash, V3-06 Pillow+FFmpeg pixel QA and CMU font, V3-10 exact frame probing; new learnflow_v3/temporal_geometry.py enforces renderer-owned typed AABB keyframes, true **continuous-time** analytic swept collision for linear motion and shared-window smoothstep, otherwise conservative recursive nonlinear interval bounds with uncertainty fail-closed. All integer frames and between-frame continuous sweeps are certified for content/title/captions: strict safe edges, reserved subtitle band, text-fit at maximal font and minimum box width for reflow/morph, simultaneous motion/speed budgets and content-hash replay. Real example rendered in new bounded demo adapter and checked by exact ordinal H264 decoded frame + object-ROI MAE; no unverified arbitrary code, auto card fallback or unsafe auto-static pass. Positive/negative mutation corpus includes two safe endpoints colliding only **between integer frames**, nonlinear path, caption intrusion, text morph/reflow/clipping, stale/rehashed source/MP4, output overwrite. [Implementation CI #37751060381](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37751060381): **163 V3 / 39 V2 / 86 Hermes PASS**, prereg/Bench/Core Freeze PASS; 49-frame 640×360 @12fps H264, 3 analytical pair segments, 3 conservative subdivisions, 100 text bounds, max 2 concurrent motions, 0 critical overlaps, max decoded anchor MAE 0.238. [Real video+JSON artifact #11537957182](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37751060381/artifacts/11537957182) downloaded and SHA/ffprobe independently verified. **Only a bounded renderer-owned geometry demo**; not production V3-06/07/08 integration, complete transitions, audio sync or human learning gains. Report reports/v3_11_temporal_geometry.md. No main/V2 Core edits, provider calls, V3-12 implementation or publication. One next separately authorized checkpoint: **V3-12 Fail-Closed QA and Publication**.


### 9.14 V3-12 Fail-Closed QA & Publication (2026-10-08)

**BOUNDED OFFLINE ENGINEERING PASS at initial implementation SHA e8b0dc6b92d186bd9c225833bf4ac68be9707ff0; final HEAD CI pending.** New stacked review-only branch chatgpt/v3-12-fail-closed-publication from PR #44 HEAD 3877f2a3ecf0bbe4ee317726067ac02bd09f3a0c. Reuse-first V3-10 actual H264/source-replayed beat proof, V3-11 actual decoded geometry demo proof, frozen V2 QA concepts and agent_aware_qa blockers; no V2 Core, 100-topic benchmark, historical #181, app default, provider, license-vendored modules, model-token or main changes. New learnflow_v3/publication_gate.py versioned typed status/requirements and hash-chained lifecycle, source-replayed review, strict default policy with NO production publishing API, no free/paid retries, no unverified deterministic-only override. It distinguishes component DETERMINISTIC_PASS from lesson PUBLISH_BLOCKED; a raw critic PASS without V3-13 proof is CRITIC_UNAVAILABLE, not CRITIC_PASS. Mandatory full lesson swept geometry, cross-scene coverage, fact agreement, real subtitle/audio timing, verified critic and production authority are **UNVERIFIED**, so all sample reviews remain BLOCKED. Missing/altered source/video/scene, unsupported pattern, unknown concept, stale cache, critic outage/FAIL/ERROR, forged policy/review chain all blocked or rejected. **Offline code-head CI [#37752568906](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37752568906) PASS:** 185 V3, 39 frozen V2, 86 Hermes, V3 prereg/LearnFlowBench/Core Freeze PASS. Five policy demos: 2 actually decoded H264 clips with bounded deterministic PASS but publish BLOCKED, critic outage BLOCKED, unverified claimed critic PASS maps to UNAVAILABLE and BLOCKED, stale video evidence DETERMINISTIC_FAIL and BLOCKED. [Actual media+JSON artifact #11537634901](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37752568906/artifacts/11537634901). Report reports/v3_12_fail_closed_qa_publication.md. This is **zero-bypass on the tested fault matrix, NOT evidence that real full lesson publication works**. No V3-13 critic implementation, no authorized publishing actor/writer, no end-to-end audio or release candidate. One next separately authorized checkpoint is **V3-13 Artifact Critic**.


### 9.15 V3-13 Artifact Critic — bounded source/pixel-grounded adapter (2026-10-08)

**IMPLEMENTED, BOUNDED OFFLINE ENGINEERING PASS on first code-head [CI #37754448715](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37754448715), final report/documentation HEAD CI still requires independent verification.** Review-only stacked branch chatgpt/v3-13-artifact-critic from exact PR #45 head 30bec3500f693f31b2fa76c216221dffc14b093d. New learnflow_v3/artifact_critic.py binds typed critic request to previously certified V3-10/V3-11 MP4/source, samples 6 actual decoded RGB frames, checks ordinal frame index/time/dimensions and SHA-256, approved object/beat/claim IDs and original video SHA. A fresh video-backed call independently rechecks every decoded RGB buffer before giving the injected reviewer real PIL frames. Output is strict scoped typed issues (category, severity, time range, objects, claim/beat, evidence frame hashes, confidence, fixed repair owner); rejects hallucinated refs, untrusted executable/geometry fields, oversized/duplicate issues and stale response hash. Reviewer unavailable/timeout/malformed gets explicit UNAVAILABLE/REJECTED, never CRITIC_PASS; zero issues is UNVERIFIED, issues require review, critic has no geometry/publish authority, at most one call/8 issues/8 images, no LLM/API calls/retries. Frozen V3-12 review remains PUBLISH_BLOCKED. First CI: **210 V3 / 39 V2 / 86 Hermes PASS**, prereg/Bench/Core Freeze PASS and 2 actual H264 demo clips. Later changes add explicit real image-bearing reviewer callback with two extra mutation tests. Report reports/v3_13_artifact_critic.md and script scripts/verify_v3_artifact_critic.py.

**DO NOT CLAIM V3-13 FULL RESEARCH GATE.** The benchmark is clearly marked *AUTHOR_SEEDED_SYNTHETIC*, not human-labeled. No external VLM actually reviewed the MP4 and no independently human-annotated ground truth exists; real critic precision/recall, +10 percentage-point incremental issue recall vs V2, false positive limit, provider cost/latency, inter-rater agreement and human learning gain remain **UNMEASURED / NOT ESTABLISHED**. Technical contract/preflight PASS only, independent reviewer/human evaluation **OPEN** before any production/human-quality publication claim. Do not merge, enable publication, or infer a critic PASS. A separately authorized next CP may develop V3-14 typed ArtifactRefine under the existing strict blocked policy; its quality results cannot depend on unvalidated critic claims.


### 9.16 V3-14 ArtifactRefine — bounded local restoration/rollback (2026-10-08)

**BOUNDED ENGINEERING PASS on implementation [CI #37755768974](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37755768974), exact documentation PR-head CI must also pass.** Stacked review-only branch chatgpt/v3-14-artifact-refine from PR #46 exact SHA 0d62803960c7c7cdc937997fe919dd79fa532b62, leaving frozen main unchanged. Reused frozen V2 content hashes and dependency invalidation principles; V3-11 typed temporal geometry, actual H264 encoder/decoded ROI QA; V3-12 hard publication block and V3-13 bounded issue-owner routing (independently human/VLM critic still OPEN). New learnflow_v3/artifact_refine.py only supports RESTORE_LAST_CERTIFIED_TRACK for one AUTHOR_SEEDED_CERTIFIED_SNAPSHOT with exact base/input/track SHA; no source supplied by critic, no arbitrary geometry/code. Requires actual proof source and H264 replay, exactly one changed track, unchanged global semantics and untouched track hashes, valid defect category from original geometry QA; no-op/multi-track/forged/stale source blocked. Restores one track only, re-certifies geometry, **re-encodes full 49-frame clip**, rechecks decoded MP4, preserves original and rolls back failed output. Invalidates temporal certificate/render/decoded QA/publication review; all outcomes PUBLISH_BLOCKED, no production writes, one attempt. Factual/script/pedagogy/visual categories deferred to their owner without geometry edits. Synthetic positive corpus: 5/5 recovery of injected font overflow, subtitle intrusion, clipping, excess motion, collision; negative corpus: multiple edits, semantic identity, stale/no-op/fault mismatch/MP4, overwrite, injected encoder crash, forged review. **Implementation CI: 228 V3 / 39 frozen V2 / 86 Hermes PASS, prereg/Bench/Core Freeze PASS; six actual H264 clips and machine-readable source/video/track hashes in artifact #11539304933.** Report reports/v3_14_artifact_refine.md. **DO NOT CLAIM FULL C7:** synthetic recovery only; all full clips re-encoded, runtime/cost vs full regeneration not measured, no validated real critic, no full-lesson generality, no human outcomes. The Plan C7 ≥70% without full-scene regeneration remains **NOT ESTABLISHED**. Next one separately authorized CP **V3-15 Pattern Expansion**; unfinished V3-13/C7 research efficacy still open.


### 9.17 V3-15 Pattern Expansion — evidence-gated cyclic State Machine (2026-10-08)

**BOUNDED ENGINEERING PASS on exact layout-corrected code SHA de9abf7f35b94a7eaae6a4c12cece0b6a34aaed7, 14/14 workflows success; documentation-only final SHA requires separate CI verification.** Stacked review-only branch chatgpt/v3-15-pattern-expansion-state-machine forked from PR #47 SHA f34ad2fdf342cb7e0a057e788517905aec843c6c. Immutable V3-01 100-topic corpus/12-topic frozen pilot verified with existing prereg validator and exact corpus hash, no topics replaced or outcomes edited. Of locked 12, 2 curated STATE_MACHINE *candidates* (lfb-006-cs HTTP request lifecycle and lfb-016-cs distributed transactions); the other 10 explicitly ABSTAIN on new-family evidence, **not judged ineligible for other families**. Demand is proxy/author curated only, not measured actual user preferences or pilot success. Reuse V2 canonical hash, V3-06 frame profile and real H264 decode/pixel QA, V3-07 PROCESS_FLOW DAG failure on cycles, V3-11 exact ordinal frame decoder, installed CMU fonts and existing FFmpeg/Pillow. Implemented learnflow_v3/state_machine_renderer.py with bounded typed states, directed guarded edges, exact beat replay, stable ID centers, branches and cycles, explicit terminal and source provenance. No arbitrary generated Python/geometry; no auto CONCEPT_CARD fallback. New 2 actual clips for locked CS topics use dynamic edge token + state highlight, 70 and 50 video frames at 640×360 H264; recompute H264 codec/count, exact frame semantic state/deltas and within-beat transit motion; verify original frozen topic SHA and video SHA. Initial code-head [CI #37757306255](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37757306255) **243 V3, 39 V2, 86 Hermes PASS**, prereg/Bench/Core Freeze PASS; 2 real MP4s. Independent MP4 screenshot inspection caught title-divider/node bounding overlap despite decoded pixel PASS; **layout shifted to reserved middle band and new header/footer-clearance regression test added**, requiring final CI rerun. **Verified on layout-corrected code HEAD de9abf7f35b94a7eaae6a4c12cece0b6a34aaed7:** [GitHub Actions V3-15 #37757946039](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37757946039) and 13 ancestor checks all success (**14/14 on that exact code HEAD**), **245 V3 / 39 frozen V2 / 86 Hermes PASS**, V3_BENCHMARK_PREREG=PASS (12 frozen/6 domains), LEARNFLOW_BENCH_CONTRACT=PASS, CORE_FREEZE=PASS. Corrected actual H264 goldens: HTTP 70 frames / 82,462 bytes with min state MAE 2.328, min within beat 0.150; transactions 50 frames / 61,216 bytes with min state MAE 1.942, min within beat 0.170. [Artifact #11541086868](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37757946039/artifacts/11541086868) includes both MP4 and exact JSON. Independently downloaded and checked both codecs/resolutions/frame counts/byte SHA against JSON, and visually inspected corrected frame confirming node/header no longer overlap. Report reports/v3_15_pattern_expansion.md; script scripts/verify_v3_pattern_coverage.py; tests tests/v3/test_pattern_coverage.py. Production V3-04 RepresentationType/router was not modified; this is **a standalone bounded renderer candidate, NOT auto-routed to production**. No speech/TTS/factual or human validation, 12-topic lesson completion, C5 ≥70% specialized utilization, reduced card collapse in real generation, human representation adequacy or 3B1B quality claim. V3-13 independently labeled critic recall and V3-14 real incremental repair efficacy still OPEN. All publication blocked and main unchanged. Next separately authorized single CP **V3-16 Human Pilot/Ablation**, requiring explicit approval for participants/provider costs before actual pilot.


### 9.18 V3-16 Human Pilot & Ablation — locked evaluation manifest, not an actual human study (2026-10-08)

**ENGINEERING IMPLEMENTED, exact PR-head CI pending; genuine scientific human efficacy gate remains OPEN.** Stacked review-only branch chatgpt/v3-16-evaluation-manifest inherits PR #48 HEAD 7bfd72039588e11629f395272ae028b10b48dc6f; frozen V2 main unchanged a06e0b0b5f35e9147b4081da7ed7f7934affe0c6. Reused frozen V3-01 preregistration validation, 100-topic LearnFlowBench immutable corpus/hash, locked 12 topics spanning 6 domains, V2 compute_content_hash, V3-01 two co-primary ordinal rubrics and hash-parity blind order. New learnflow_v3/evaluation_pilot.py and scripts/verify_v3_evaluation_manifest.py: strictly typed immutable public 12-topic x 2-slot A/B no-system-key manifest, blank 24-slot rater CSV, E1–E10 ablation contrast register ALL NOT_RUN, separated in-memory slot/system assignment, explicit 24 ordered V2/V3 attempt denominator with no dropped failures, third rater adjudication for 2+ disagreement on either co-primary, invalid attempted MP4 gets floor 1 but unexecuted is UNMEASURED and blocks analysis, source-checksummed protocol, 10,000 fixed-seed paired **topic-level** bootstrap intervals, per-topic domains/difficulty effects, rater raw-score disagreement, and missing cost/time must remain None (never coerced to $0 or PASS). Importantly runtime parser accepts **AUTHOR_SEEDED_SYNTHETIC ONLY**, not externally gathered human ratings or actual provider outputs; no recruitment, model/API access, TTS/real MP4 generation, paid request, personal data transfer or publication. Every synthetic rehearsal result is tagged NOT_HUMAN_EVIDENCE, published approval/real human gain locked FALSE/UNMEASURED, real critical safety observations None. Real model/paired 12-topic generation, independent human annotation, rater agreement, human perception and visual quality targets remain **UNMEASURED**. Frozen V3-01 permission flags all FALSE; no silent change or protocol versioning after outcomes. The deterministic parity key is not exported in rater packet, but public protocol could enable reverse engineering: recruit raters isolated from repo/seed, require blinding audit and explicit authorization before any real pilot. Negative fault tests include missing/duplicate raters, fake human origin, missing adjudication, failed-vs-unrun masking, dropping bad topics, swapped identities, ablation manipulation, negative/missing cost, dishonest PASS, frozen protocol contamination. `.github/workflows/v3-evaluation-manifest.yml` runs V3-02–15 regression + frozen V2/Hermes/prereg/Bench/Core Freeze + offline manifest/CSV/synthetic bootstrap artifacts. Report reports/v3_16_evaluation_manifest.md. **This does NOT complete V3-16 true human-quality acceptance**; absent participant/live authorization, only bounded protocol and computational correctness may pass. Exactly one next separately requested CP per PLAN: V3-17 Release Candidate/Rollback **gate preparation only**; release MUST remain blocked while human and critic C6/C7 genuine quality tests are not measured.


### 9.19 V3-17 Release Candidate & Rollback — offline NO-GO readiness gate (2026-10-08)

**BOUNDED ENGINEERING PASS on implementation SHA \`5e34b89d6504f9966a14ef9966fd7cb057948a39\` [CI #37779748591](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37779748591), 279 V3 / 39 frozen V2 / 86 Hermes tests PASS, benchmark prereg/Bench/Core Freeze PASS; exact final documentation PR-head CI still requires verification.** New \`learnflow_v3/release_gate.py\` explicitly records **5 source-bounded engineering checks and 7 BLOCKED_UNMEASURED release requirements**, always \`BLOCKED_NO_RELEASE\`. Reuses V3-12 source-replayed publication reviews, V3-16 unexecuted 12-topic human manifest and immutable V3-01 prereg, protected V2 Core manifest, V1 baseline git blob, V2 content hashes. Script \`scripts/verify_v3_release_gate.py\` independently renders 2×2 actual H264 demo MP4s from identical source (Binary Search 36 frames each; temporal 49 each), decodes and checks **entire raw RGB pixel stream parity** for both pairs (SHA256: \`3c1917b5b1f6ee932f95d0663e6396fd9661344afd37796d88214f5f96d2576d\` and \`110e143a1359c09132993f385231037dc5a4e16ace21c9d3471fa252e32916d8\`), replays V3-12 on original actual video and retains bounded provenance. It verifies frozen V2 Core and V1 git blob \`b7da44db1653e81276a272fe84996665b5d4e410\` and **only simulates** switching an ephemeral temporary active route \`v3_staging→v2_frozen\` with atomic rename while checking originals unchanged. **This is NOT a real service restore or full reproducible application build**. \`tests/v3/test_release_gate.py\` has real H264, malformed/stale MP4, independent replay hash fraud, forged release authorization/gates and invalid rollback source/symlinks/no-clobber; \`.github/workflows/v3-release-rollback-gate.yml\` runs full frozen tests and creates [bounded JSON/video proof artifact #11551224040](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37779748591/artifacts/11551224040). Report: \`reports/v3_17_release_rollback.md\`. **Release NO-GO:** seven unmeasured gates are 12 paired *complete* videos, truly independent human scores, real C6 critic recall, real C7 repair value, full lesson factual/AV/subtitle QA, actual cost/reliability, authenticated publication permission. Zero live calls/participants, no merge/publish; frozen \`main=a06e0b0b5f35e9147b4081da7ed7f7934affe0c6\`. V3 checkpoint engineering preparation DOES NOT satisfy the V3 DONE conditions in section 15. The next legitimate milestone requires explicit human/evaluation and production rollout authorization, not another self-confirming offline smoke.


### 9.20 V3 Integration Closure / Dead-Code Audit (2026-10-08)

**First bounded implementation proof:** [CI #37783540262](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37783540262) on implementation SHA ad494c06786ace0a8cba95e34453f7ca8b823056: 364 V3 / 39 frozen V2 / 86 Hermes PASS; prereg, Bench and Core Freeze PASS. Exact final documentation+partial-write-fix SHA needs separate full CI verification.

**Confirmed P0:** Product app/main.py -> app/pipeline/factory.py -> app/rendering/router.py and lesson_pipeline/coordinator.py -> lesson_pipeline/core.py CapabilityCoreGateway have no static direct LearnFlow V3 imports. V3-04 router explicitly returns SELECTED_UNRENDERABLE, and V3-03 global render-consumption guard explicitly denies when renderer-owned consumers are absent. Never change either guard to pretend production wiring.

**New real OFFLINE vertical slice:** learnflow_v3/offline_lesson_source.py constructs V2/V3 authored source (no test or golden-render-script imports); learnflow_v3/integration_slice.py replays verified V3-05 source, V3-02 semantics, V3-03 source/signal audit, V3-04 selected routing, dispatches only WORKED_EXAMPLE_BOARD to original V3-06 H264 renderer, V3-10 beat/pixel QA, real FFmpeg one-scene video-only timeline remux, exhaustive decoded RGB SHA parity between scene and assembly, and V3-12 replayed PUBLISH_BLOCKED review. First real output: 36 frames, 640x360@12fps, decoded scene and assembled stream SHA256 both 3c1917b5b1f6ee932f95d0663e6396fd9661344afd37796d88214f5f96d2576d. No narration/audio. All other families explicitly ABSTAIN, cyclic PROCESS_FLOW topology explicitly ABSTAIN_INVALID_TOPOLOGY, never convert to CONCEPT_CARD.

**Dead-code reachability:** scripts/audit_v3_reachability.py scans 387 Python files and 22 V3 modules, returning per-module and per-public-API import/caller/consumer/test JSON and explicit conservative uncertainty for dynamic import/reflection. Production direct V3 imports detected: 0; scripts/tests are not production wiring. No auto-deletion of possibly reusable offline helpers. Reports at reports/v3_integration_closure_audit.md and CI JSON artifact.

**Honest incomplete consumption:** original V3-03 declared deferred leaves stay explicitly reported in a signed receipt as PARTIAL_DECLARED_DEFERRED; material unsupported hero or cognitive-load requests block before rendering. Mutation tests cover source/claim/beat/trace drift, output bytes, preexisting file, disabled renderer, cyclic process, partial assembly output and link. One-scene silent remux is not full multi-scene audio assembly and is not human-quality evidence.

**Real V3-14 defect fix:** artifact_refine.py originally left partial MP4 if renderer wrote bytes and raised before setting created=True; private TemporaryDirectory staging plus certified QA before hard-link-to-final ensures cleanup. Added test simulating write-then-error. V3-14 still reencodes all frames, real critic/C7 efficacy unmeasured. Frozen V2 Core/main untouched; PR #51 open stacked on #50, no merge, no real provider, no publication.

**Remaining blockers:** production V3 router/adapter registration and complete scene/lesson timeline, audio sync, State Machine schema and routing, Code/Math registry, actual VLM/human QA, full 12-pair pilot and release permissions are NOT DONE. This checkpoint at best satisfies a bounded offline one-family vertical slice, not a complete V3 product.

### 9.21 V3-18 Product Pipeline Integration — guarded local HTTP Binary Search preview (2026-10-08)

**IMPLEMENTED pending exact final CI** on stacked PR #52 based on PR #51 exact head 749861073f26cc0367ec101c7c63eaecef4e0d1b; frozen main unchanged a06e0b0b5f35e9147b4081da7ed7f7934affe0c6. This is a developer-only HTTP preview and is NOT publication, a production renderer cutover or a complete lesson.

**Audit and chosen single seam:** Existing FastAPI app/main.create_app -> app/pipeline/factory.create_pipeline -> app.state.pipeline -> JobRunner already constructs one LearningVideoPipeline and persists all normal /api/jobs to V2. The separate Hermes lesson_pipeline/coordinator -> CapabilityCoreGateway route remains frozen V2 and untouched. With LEARNFLOW_V3_BINARY_PREVIEW flag (default OFF), factory wraps the original pipeline, and wrapper.process() still directly delegates to the original for all jobs including publication invariant. App also exposes local developer-only POST /api/v3/offline/binary-search that calls preview_binary_search() on the very same app.state.pipeline wrapper; no second queue or live LLM pipeline. Flag OFF gives route HTTP 404, factory original class unchanged; production environment refuses to start with flag ON, remote peers HTTP 403.

**True request-specific offline proof:** JSON bounded sorted values and target from HTTP -> learnflow_v3.offline_lesson_source project-owned builder -> V3-05 binary oracle and V2/V3 typed source -> V3-03 signal audit -> V3-04 honest semantic-only route -> V3 Integration Closure adapter -> V3-06 blackboard H264 renderer -> V3-10 actual beat pixel verification -> FFmpeg single scene remux -> complete decoded RGB parity -> V3-12 publication BLOCKED. Receipt includes trace, beat IDs, claim and object IDs and exact input/route/video hashes. Source is not a golden/test fixture and a different source is used in the CLI test. Unsupported Process, Code, Math, StateMachine and ConceptCard ABSTAIN HTTP 422 without card fallback; all missing/unconsumed signals remain declared. No audio/TTS or real 60s lesson.

**No unauthorized publish:** MP4 and receipt kept in opaque preview directory in existing artifact store, never final.mp4 or final.pending.mp4; no ArtifactStore.publish_final, no JobStatus.SUCCEEDED, no public video GET/URL and no production route registration. The developer HTTP route returns hash/QA receipt only. CI explicitly copies bounded demonstrator MP4 to workflow artifact for offline review then removes private DB/cache. Exceptions after partial renderer output clean preview directory and return sanitized HTTP failure.

**Tests:** tests/v3/test_product_pipeline_integration.py makes REAL TestClient HTTP requests through create_app/factory/SQLite/ArtifactStore, verifies H264 codec/framerate/frame count, source/receipt hashes, normal job mode, default OFF, remote/prod refusal, source mutation, partial-write, unsupported family. App legacy CRUD, fake and real pipeline tests, V3-02 through V3 Integration Closure, V2/Hermes/prereg/Bench/Core Freeze in new workflow .github/workflows/v3-product-pipeline-integration.yml. On initial new code CI #37786569935, 383 V3 tests passed, 1 original Integration Closure test failed because it assumed 0 app→V3 static imports. Replaced that stale invariant with stronger caller allowlist ONLY app/pipeline/v3_preview.py and distinguish GUARDED_DEV_APP_PREVIEW_ONLY_NOT_PUBLIC_JOB_ROUTE from real production imports. Exact final CI pending.

**Scientific and deployment STOP:** A local HTTP source-bound silent preview is NOT ordinary /api/jobs V3 production, not narrated multi-scene full lesson, not Hermes V3 wiring, and not real critic/human gains/release authority. Publication remains PUBLISH_BLOCKED, frozen main and V2 Core unchanged. No external provider/personal human data/model API use. A later separate checkpoint would need genuinely authorized full video product route and human/regulatory release gates.

### 9.22 V3-19 — Narration-Aware Full Lesson Assembly (2026-10-08)

**Offline developer-only narrated multi-scene technical prototype; exact PR-head CI pending.** Stacked PR #53 on #52 exact parent 148b8365a6b66f1baab49e98ec068c7953fd9934; main frozen a06e0b0b5f35e9147b4081da7ed7f7934affe0c6 and V2 Core unchanged. No merge, paid API, remote TTS, external model inference, human research or production publication.

**Reuse-first audit:** V2 `app.domain.timeline.ResolvedSceneTiming/ResolvedTimeline/SubtitleCue`, V2 `app.pipeline.assembly.VideoAssembler` (FFmpeg H264/AAC/SRT), V3-06 `draw_binary_search_frame`, V3-05 oracle, V3-18 existing FastAPI developer adapter/preview and source, V3-10 source/beat certified baseline, V3-12 fail-closed QA; not V2 `EdgeSpeechProvider` (requires remote HTTP) or character-proportional subtitle timing (not real forced alignment). New `learnflow_v3/narrated_lesson.py` uses local distro eSpeak-NG `en-us` English voice to synthesize actual WAV speech per scene. Source/engine/version/WAV SHA and measured PCM sample counts, sample rates, audio RMS, exact text bound to original trace/beat/claim/object IDs are included in a typed receipt. Scene order intro → mechanics explanation → *each* certified oracle comparison/state step → recap; frames use existing V3-06 dynamic trace visual, not static video stretching or Concept Card fallback. Audio durations are strictly measured from WAV sample counts, video frame counts derived from physical audio duration × 12fps (+one frame for padding), WAV padded to exact frame budget, one real spoken scene = one SRT cue, scene continuity certified by original ResolvedTimeline.

V2 FFmpeg VideoAssembler composes real H264 video scenes + WAV audio segments + burnt SRT, output in private temporary directory, QA original scene frames, output stream H264/AAC, entire final decoded video frames, output duration, final AAC voice audible for *each actual scene interval*, subtitle source/times and identities, then hard-link output MP4+SRT+receipt safely without clobbering. The independent `verify_narrated_lesson()` verifies final source/text/trace/MP4/SRT hashes and final audible AAC per scene. `segment_alignment=MEASURED_AUDIO_SAMPLES_SCENE_BOUNDARIES` is observable in actual decoded streams; **word/phoneme forced alignment and independent transcript-as-heard checking UNMEASURED**, so should NOT count as externally validated speech quality.

Product app `POST /api/v3/offline/binary-search-lesson` calls the **same** `app.state.pipeline` adapter as V3-18; requires BOTH original `LEARNFLOW_V3_BINARY_PREVIEW` and new `LEARNFLOW_V3_NARRATED_LESSON` flags (both OFF by default), dev/test and localhost only, production with flags refused. HTTP returns only private-preview QA receipt; no `final.mp4`, publish_final, JobStatus.SUCCEEDED, URL playback or normal V2 job pipeline mutation. Unconnected families HTTP 422 ABSTAIN, no default ConceptCard. Tests `tests/v3/test_narrated_full_lesson.py`, producer `scripts/verify_v3_narrated_lesson.py`, CI `.github/workflows/v3-narrated-multiscene.yml`, report `reports/v3_19_narrated_multiscene_lesson.md`.


### V3-19 visual-overlap correction and real-AAC negative test (2026-10-08)

Manual review of actual first generated [#37790811634 artifact #11555614901](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37790811634/artifacts/11555614901) revealed that the original V2 subtitle styling (`DejaVu Sans`, 22 px) **obscured lower semantic action text**. Initial functional CI PASS alone did not make the rendered lesson visually acceptable. The implementation therefore added opt-in `subtitle_force_style` to original `app/pipeline/assembly.py`: None preserves old V2 behavior; V3-19 selects compact CMU Serif 14 px on its own call. The renderer reserves a clean caption zone Y≥~295, masks original lower labels and reprints certified source action at Y=252, and the new post-assembly decoded-pixel QA rejects bright text in the gutter Y=280–294 for every scene. The introductory scene now highlights individual sorted indices; explanation retains oracle LOW/MID/HIGH motion; recap follows actual certified midpoint path—distinct visual teaching actions, not an animation loop with extra duration. Negative tests include a **self-rehashed MP4 with AAC removed** and a **self-rehashed SRT with corrupted time**, not merely mismatched file hashes. Final CI/visual artifact must be evaluated separately; older artifact demonstrates the overlap defect and must not be used for visual acceptance.

Observed FIRST RUN (before subtitle fix): 7 separate scenes, 44.833 s, 538 video frames, H264 640×360/12fps, AAC voice audio, physical per-scene WAV sample counts and non-silent speech; [CI #37790811634](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37790811634) succeeded. The 7-scene first-run video byte SHA256 `d05fb8b0de9607cec94726a9e6b3fe5c4a66f44034d566d45fd81a8f4289bf0f` matched the media receipt. **This evidence is NOT the final visual-accepted artifact**; see fixed code CI and source checks. No word-level forced alignment, no independent ASR/human listening, no guarantee of commercially cleared voice licensing; publication remains BLOCKED.

**Caveat:** eSpeak-NG uses an open-source distro voice/program but commercial downstream rights require separate verification; this is offline engineering evidence only, not guaranteed commercial voice licensing. Human instructional quality, pronunciation, forced phoneme alignment, scene-by-scene semantic adequacy, full V3 product release readiness and 3Blue1Brown parity are NOT established. V3-16 human pilot and V3-17 publish authority remain BLOCKED; no production promotion.

### 9.23 V3-20 — Narration–Visual Event Alignment & Lesson Quality Gate (2026-10-08)

**Stacked PR #54 on PR #53 HEAD 6847850f48249d82b857380bec8751f2466fa964.** Main a06e0b0b5f35e9147b4081da7ed7f7934affe0c6 and V2 Core unchanged; no merge, deployment, paid API or users. Code-HEAD CI proof and final before/after artifact pending.

**Actual V3-19 media review:** original final H264/AAC 640x360, 12fps, 538 frames, 44.833sec. At timestamp **14.5s**, the action DISCARD LEFT was already on screen even though the voice was only announcing observed midpoint, before explaining Move the low bound. Two duplicate-match steps had similar early candidate/action labels (~20–33sec). The exact timestamped issue matrix and 16-frame video contact-sheet review are documented in reports/v3_20_narration_visual_alignment_audit.md. Video quality is NOT the same as instruction correctness; original trace was mathematically correct.

**Reuse-first V3-20 method:** original source-grounded V3-05 trace and V3-06 H264 blackboard render, V3-19 local espeak-ng WAV, actual PCM sample counts, FFmpeg VideoAssembler, SRT, V3-10 beat pixel QA, V3-12 publication BLOCKED. New learnflow_v3/event_alignment.py emits OBSERVE and APPLY for every oracle-certified COMPARE step, retains beat, segment, claim, object and trace identities. OBSERVE remains at old LOW/HIGH/MID; APPLY only starts next certified state at start of independently synthesised, physically counted next WAV utterance. No character-proportional/fabricated word timestamps. Typed source/event/frame/PCM/SRT proof must replay even when claimant re-hashes input or shifts audio; source-expected frames decoded and checked. V3-19 old endpoint remains unchanged by default.

**Scope honesty:** exact phrase/utterance boundary alignment, NOT recognized word/phoneme onsets, independent transcript-as-heard ASR, expert aesthetics, independent pedagogy or human comprehension. All corresponding claims UNMEASURED, PUBLISH_BLOCKED. eSpeak-NG engine GPL-3.0-or-later (official espeak-ng GitHub); per-voice/output distribution rights require separate review. No external API or downloaded ASR checkpoint.

**App:** LEARNFLOW_V3_EVENT_ALIGNMENT feature flag OFF by default, requires BOTH existing V3-18/19 preview flags; only local development/test; production refuses; unsupported family HTTP 422 ABSTAIN without ConceptCard. POST /api/v3/offline/binary-search-event-aligned uses existing app.state.pipeline wrapper, receipt only, never final.mp4, normal /api/jobs or public URL. Tests tests/v3/test_event_alignment_quality.py cover real HTTP video/audio/source and fake timestamp, missing WAV/proof, wrong segment state, forced word-alignment fraud, shifted SRT, crash-after-write and production/remote guards. CLI scripts/verify_v3_event_alignment.py generates real same-source before/after H264/AAC/SRT and machine event proofs. New CI .github/workflows/v3-event-alignment.yml runs antecedents and original V2/Hermes. First CI #37797446360 FAIL from verifier still replaying original seven-scene source against the new multi-utterance source; fixed verifier selection rather than weakening source/pixel QA.

**NO-GO outside engineering:** actual audio rights, full human quality/learning study, word forced alignment, production routing and release authorization remain BLOCKED/UNMEASURED. Do not merge stacked PRs or claim 3Blue1Brown equivalence.


### V3-20 second decoded-frame regression found during before/after review (2026-10-08)

**New actual defect after original V3-20 event-boundary implementation:** downloaded code-head [workflow #37797960605](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37797960605), [artifact #11560111210](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37797960605/artifacts/11560111210). Real same-source before/after clip: original 7 scene/538 frames, V3-20 **10 utterance/event scenes/541 frames**, actual H264/AAC/SRT, all 14 new tests +396 ancestor V3 +21 app +39 V2 +86 Hermes PASS. At 17.333s APPLY begins correct LOW transition; however actual decoded boundary **frame 239→240 (19.917→20.000s)** revealed a 1-frame LOW/MID backward jump at start of next OBSERVE. The exact observed RGB ROI (x0..640,y80..235) mean absolute channel difference was **4.1208** versus **0.0020** at a steady adjacent frame. Existing 3 sampled frames/scene source oracle QA did not catch this discontinuity.

**Second fix and mutation:** `narrated_lesson._narrated_frame` now uses fully settled certified state `progress=1.0` for OBSERVE/RESULT, and only APPLY legitimately tweens from prior to next oracle step. `verify_narrated_lesson` compares **actual adjacent decoded output frames at every APPLY→OBSERVE/RESULT transition**, requires identical source oracle visual step and exact adjoining frame numbers, and rejects ROI difference above 2.0 MAE. This threshold is below the independently measured 4.1208 bad boundary; after-fix residual measured only in final artifact. New `test_regressed_renderer_rewinds_pointer_at_scene_boundary_is_rejected` deliberately recreates the buggy tween and requires decoding-based rejection, not just self-hash or source expected frame checks. **Before/after final acceptance remains pending until final exact PR-head CI and video are inspected.**

**Decoded audio engineering spot check on pre-continuity-fix clip:** ~45.099s mono-16k decoded AAC, RMS 0.08501, peak 0.71451 full-scale, **0 samples >=95% full-scale**. The onset amplitude in first 20ms windows after APPLY WAV boundaries is non-zero for the tested events; these measurements show no obvious clipping, **not an independent pronunciation/ASR assessment**. Commercial output permissions for eSpeak voices remain unverified. No publication, no 3B1B / human-quality claims.



**V3-20 verified code-HEAD closure (2026-10-09; supersedes earlier historical “CI pending” only for code HEAD):** At SHA `cd8494d6fbc8720a39f1e2317ca68f723ab6c963`, [V3-20 workflow #37799974547](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37799974547) and 21 other commit-scoped workflows returned **22/22 SUCCESS**. Independent replay of [artifact #11560168593](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37799974547/artifacts/11560168593) confirmed real H264/AAC MP4s (538 vs 541 frames), matching receipt video hashes, ten after-event SRT/proof cues, and decoded ROI MAE **0.056929** at formerly regressed boundary frame 239→240 (historical bad **4.1208**). Final audio decoded without 95%-threshold clipping; only engineering-level utterance-event alignment certified. **V3-20 BOUNDED TECHNICAL PASS; independent word-level ASR, human teaching quality, 720p/1080p legibility, commercial voice rights and V3 release remain UNMEASURED/BLOCKED.** No merge, publish, paid provider call or V2 core change. Full evidence: `reports/v3_20_narration_visual_alignment_audit.md`. This documentation-only follow-up SHA has not inherited CI status automatically.

### V3-21 Lesson Visual/Audio/Pedagogy Quality Evidence — 2026-10-09

New stacked draft PR #55 on PR #54, preserving main and frozen V2. New V3-21 audit consumes real V3-19/20 same-input H264/AAC/SRT and source metadata, decodes per-utterance audio, samples real pixel boundaries and publishes a timestamped evidence ledger with readability/pacing/voice limitations. Current 640x360/12fps preview does not qualify as audience-grade media. Machine-verifiable integrity is separate from learner understanding, word-level timing, voice pronunciation, 3Blue1Brown similarity and commercial distribution rights. Quality and release remain BLOCKED/UNMEASURED pending independent evidence. No new provider spend, human study, product endpoint, automatic merge or renderer substitution. Final head CI and artifact required. See reports/v3_21_lesson_media_quality_gate.md. Next separate authorization: HD typography and pacing retrofit (provisional V3-22), then human protocol, without fabricating V3-16 pilot results.

### V3-22 Native HD Typography & Visual Pacing Retrofit (2026-10-09)

**Candidate under separate user authorization on PR #56, stacked on PR #55; no main merge.** The source V3-20 narrated video was only 640×360/12fps and V3-21 could not certify readability. V3-22 reuses the exact certified Binary Search oracle, original local eSpeak AAC/SRT/physical utterance events, Pillow/FFmpeg and OS-installed Computer Modern. It redraws actual 1280×720 pixels at 24fps from semantic state (not post-upscaling old MP4). Main action/captions use 32px CMU, bounded two-line wrap and a reserved caption band. Each source APPLY event has a deliberately authored 18%-hold/62%-ease/20%-settle schedule; OBSERVE/RESULT remain settled. Original AAC packets and utterance onset are conserved, **not independent word-forced alignment**. Native H264/decoded-frame source comparisons, pointer continuity, audio bitstream hash, forged-quality negative mutation and no-clobber tests gate technical acceptance. Actual CI and before/after MP4 artifact on exact final head are prerequisites. Human readability, pronunciation, understanding, 3Blue1Brown aesthetic parity, commercial voice/output rights and production are UNMEASURED/BLOCKED; V3-16/17 do not become PASS. Full design and evidence: reports/v3_22_native_hd_typography_pacing.md. No paid API, human study or new product endpoint authorized.



**V3-22 exact-code-HEAD technical closure (2026-10-09):** At bf6372058267c399abfc2992e57d2e6d3e396b12, [native HD CI #37869109596](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37869109596) and all 21 other commit-scoped workflows returned **22/22 SUCCESS**. Actual source-matched [artifact #11589353608](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37869109596/artifacts/11589353608) independently verified as true H264/AAC 1280×720 / 24fps / 1082-frame native render, with 40 decoded oracle-frame anchors (worst MAE 0.436), event continuity MAE 0.0/0.00027/0.0 at three APPLY→OBSERVE/RESULT cuts and byte-identical AAC ADTS packet hashes between source and output. 32px action/caption CMU, no truncated captions. **BOUNDED ENGINEERING PASS only**, independent human teaching quality, viewing-distance readability, word alignment, voice rights and release still BLOCKED/UNMEASURED. Full report reports/v3_22_native_hd_typography_pacing.md. This is evidence for the named code SHA; docs-only follow-up requires separate CI.

### V3-23 — Actual HD Readability and Teaching Review Preflight (2026-10-09)

A newly authorized checkpoint prepares grounded evaluation for the **existing** 360p V3-20 and 720p V3-22 same-source Binary Search MP4s. It does not start the V3-16 12-topic human study or claim meaningful blinding between visibly different resolutions. All viewer scores/consent/recruitment UNMEASURED/NOT RUN. Offline code independently revalidates real H264/AAC/physical utterance event proof, samples actual HD caption-band pixels at pinned times, checks source CMU microtext sizes and audio script/WAV nominal WPM, then produces a timestamped issue inventory and EMPTY reviewer packet. Separate factual-causality/duplicate-leftmost-transfer/audio/legibility rubrics are prepared for possible future authorized ratings. **Technical evidence PASS cannot override student-ready / publish BLOCKED.** See `reports/v3_23_readability_teaching_preflight.md`. CI/artifacts at exact HEAD needed before bounded engineering PASS. No merge, human participants, paid provider or product release.



### V3-24 — Leftmost Binary Search Visual Storytelling & Clarity (2026-10-09)

User authorized the next bounded offline V3 step after V3-23. The new candidate **fixes** rather than merely inventories readability/pedagogy issues: native 1280×720/24fps Computer Modern true-source renderer, 32px LOW/HIGH/MID labels, 29px array indices, removal of engineer jargon and source-specific leftmost-match/candidate explanation at actual OBSERVE/APPLY utterance transitions. It reuses certified V3-20 source/audio/SRT and V3-22 original AAC stream copy, not word-forced timestamps, re-TTS or video upscaling. Particular safety issue: future-state `candidate_index` from the oracle may be available inside the next visual step; candidate only appears after the *corresponding APPLY*, with OBSERVE reading the last already applied candidate. Actual before/after native H264 frames, AAC hash, oracle-dependent caption logic, transition continuity, no-clobber and mutation CI are required. **Human readability, comprehension, 3B1B parity and production release NOT PROVEN**. No main merge, production, paid API or participant study. See `reports/v3_24_visual_storytelling_refinement.md`.




**V3-24 exact code-HEAD closure (2026-10-09):** Code SHA `398c3d749a2dae4ad223384328c6d2592ac810c8` passed **24/24 commit-scoped GitHub workflows** including [real media job #37872412940](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37872412940). Actual before/after [artifact #11591067933](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37872412940/artifacts/11591067933) independently decoded: V3-24 1280×720/24fps/1082 H264 frames, original AAC packet hash unchanged; 40 oracle replay anchors worst RGB MAE 0.4362; candidate/pointer continuity at 3 semantic cuts ROI MAE 0/0/0; 8 before/after frame comparisons changed by RGB MAE 2.8755–6.2296. Manual decoded frame review found and fixed an initially broken top divider and added explicit BEST SO FAR candidate label at the exact certified event. **BOUNDED ENGINEERING PASS**, not independently tested learner readability/comprehension or commercial release. Full evidence in `reports/v3_24_visual_storytelling_refinement.md`; documentation follow-up commit must pass its own CI.

### V3-25 — Masked-label Independent Review Pilot Instrument (2026-10-09)

New separately authorized next engineering checkpoint after V3-24. Pair identical-source/identical-AAC/1280×720/24fps real H264 V3-22 vs V3-24 in an independently runnable offline browser A/B viewer; deterministic counterbalanced anonymous reviewer slots, 9 anchored quality rubric scores including locked V3-01 co-primary dimensions, timestamped error notes, device/viewing distance and transfer prompts. Keep admin-only arm mapping separate from rater ZIPs. The single *exposed* Binary Search clip is **diagnostic/exploratory only**, excluded from frozen 12-topic V3-16 confirmatory evaluation. This viewer is masked-label **not fully blind**, and self-reported completed playback/ratings/consent are not actual independent human verification. Fail-closed aggregate refuses missing/forged/stale/duplicate responses, cannot invent human ratings and must not grant learner-ready or production release PASS. Original `benchmarks/learnflowbench/v3/preregistered_pilot_v1.json` remains frozen and its `human_participants_authorized=false` unchanged. No recruitment, paid provider, participants or release in this checkpoint. Technical PASS requires final code HEAD CI plus actual video/player artifacts. See `reports/v3_25_independent_reviewer_instrument.md`.

**Follow-up visual bugfix (2026-10-09):** User reported green candidate outline longer than gray array cell in the V3-24/V3-25 actual Binary Search video. Identified `x±46, y341..425` overlay (92×84 at HD) vs true source V3-06 gray cell (90×90). The green outline is now drawn using the native gray slot's exact computed rectangle, radius and border thickness, with visual pixel tests and varying array-length geometry checks; preserves original candidate logic and audio. This is a patch to the existing PR stack, not a new release/educational claim. Exact final SHA CI + regenerated H264 before/after artifact required.

### V3-26 — Real Browser E2E and Independent Reviewer Readiness (2026-10-09)

After V3-25, execute real Playwright Chromium on the actual locally distributed file:// reviewer HTML for R01 and R02, validating source-attested 720p H264/AAC media, unmuted playback/currentTime, browser-ended event using explicit short seek (NOT full human watching), rubric form missing-field rejection, timestamps/category, actual download JSON and offline importer. Keep synthetic browser answers EPHEMERAL and NEVER ship as actual human ratings. Add explicit aesthetic/readability/pedagogy/technical/audio issue taxonomy; older submissions remain unclassified_legacy. Prepare a future 2+ competent independent reviewer SOP, consent/identity separation and real third-rater disagreement trigger, but NO recruitment/ratings/publication authorized. Frozen V3-16 12-topic benchmark untouched; Binary Search is known diagnostic and NOT confirmation. All human outcomes NOT_RUN/UNMEASURED, production BLOCKED. See reports/v3_26_real_browser_independent_review.md; technical acceptance awaits exact PR HEAD CI.

## 10. Security, governance and cost

- No provider calls in V3 unit/fixture/offline CI. Isolate paid integration workflow with manual confirm and per-run budget, as a *new authorized protocol only*.
- Artifact outputs are allowlisted; deny auth, headers, agent traces, token-bearing provider payloads, scratch caches. Run synthetic injected credential tests. Never claim a previous artifact was retroactively cleaned.
- Pin dependencies, renderer versions, font fallbacks, tool capabilities, models/provider configuration; record executable digest. Avoid default external asset fetch in reproducibility tests.
- Assets require license/provenance, caption or alt metadata; strict offline stock assets for fixture tests.
- Resource profiles: `CPU_SMOKE` (low-res, deterministic, no model), `RENDER_QA` (full render/sampled QA), `HUMAN_PILOT` (fixed cost authorization), `PRODUCTION` (explicit publish authorization). Baseline cost measurement per scene is prerequisite to thresholds.
- No invented hard dollar price ceilings. Budget decisions must precede paid trials. Record USD/token, P50/P95 render wall-time and storage footprints on both success and failure.
- Accessibility: 16:9 720p/1080p preview, optional portrait support later; subtitle safe band and timings, minimum readable text per frame size, color-blind-safe noncolor-only markers, no aggressive flashing.

## 11. Risk, dependency, fallback and decision ledger

| Risk | Severity | Mitigation | Stop condition |
| --- | --- | --- | --- |
| visual patterns still render as cards | critical | golden dynamic clip + pixel-differentiation QA at V3-06 | no stateful teaching effect |
| correct schema but dead semantic field | critical | mutation/consumer coverage + compile proof | silent ignored required field |
| registry/script/trace mismatch | critical | single source truth and fail-closed boundaries | identity disagreement |
| sophisticated interpolation overlaps | high | temporal QA + static fallback | unverified swept collision |
| VLM critic hallucinated fixes | high | typed issue evidence, deterministic post-patch gate | cannot reproduce issue/fix |
| human ratings overfit showcase | high | preregistration/blinding, failure-inclusive dataset | no control group |
| research leakage into product defaults | high | V2/V3 flags; merge audit; signed-off release | unapproved main route change |
| cost/runtime explosion | high | measure P50/P95 and explicit approval | budget exceeded / infinite retry |
| forced domain trace on unrelated subject | medium | optional adapters and routing abstention | invalid cross-domain assumptions |
| cognitive overload by over-animation | high | coherent segmenting, cueing and outcome eval | learning score worsens despite aesthetics |

**Go/No-Go protocol:** stop if a checkpoint breaks frozen V2 regression, improves style while degrading logic, bypasses evidence provenance, or silently falls back to universal cards. Mark `BLOCKED` with an exact single correction checkpoint. No blind extra paid runs.

## 12. Exact research-to-plan mapping and what remains unproven

| Research Notes topic | PLAN_V3 location | Evidence type |
| --- | --- | --- |
| Code2Video planner/ScopeRefine | `2, 5.1, 5.6–5.7, 7` | external prior work; gains not transferable |
| ALGOGEN VTA/RSL/trace reliability caution | `2, 5.8–5.9, 6` | external prior work + evidence-boundary caution |
| OmniManim spatial planning | `2, 5.11` | external preprint |
| LLM2Manim + Mayer pedagogy | `2, 5.1, 6` | external learning-principle evidence |
| Pattern library + specialized renderer | `3, 5.5, V3-04–08` | architecture hypothesis grounded by #156/#181 failure |
| BeatVisualCoverage | `4, 5.4, 5.12, 6` | metric specification; no observed V3 scores yet |
| Semantic signal preservation | `4, 5.9` | guard motivated by #181 |
| Artifact Critic / ArtifactRefine | `5.6–5.7, V3-13–14` | experimental capability, not deployed V3 |
| V3 entry gates and waiver | `0, 1, 6, 8, 9` | scoped planning authorization |
| Human visual/learning evaluation | `6–7, V3-16–17` | PROPOSED, currently UNMEASURED |

## 13. Definition of Done (plan vs system)

**PLAN_V3 documentation DONE when:** (a) every C1–C12 has problem, evidence, design, dependency, fallback and acceptance; (b) V2 baseline and missing measures are explicit; (c) checkpoint graph/commands and stop criteria exist; (d) merge/migration, QA, artifact security and rollback are specified; (e) user can approve a single next task without rediscovering context.

**V3 MVP DONE only when:** binary search and ≥2 different non-card visual families produce *verified real clips* with full provenance, time-aware safe layouts, correctly grounded essential narration beats and predeclared golden tests, without regressions to V2 route.

**V3 release DONE only when:** controlled topic suite, blinded human comparison, cost/reliability metrics, signal-preservation mutation suite, partial failure accounting, guardrails, fallback/rollback and authorization are accepted. Documentation ≠ engineering completion; technical render success ≠ learning gain.

## 14. Reviewer attack: claims that must not be overstated

1. "New multi-agent system" — Code2Video already has agents; LearnFlow must show a different verified artifact/geometry boundary.
2. "Semantic graph" — widespread idea; value lies in end-to-end identity preservation and typed compiled visual states, if proven.
3. "Trace guarantees reliability" — ALGOGEN uses traces; only compare identical success boundaries and supported domains.
4. "Animation improves pedagogy" — requires controlled user study; motion is not necessarily learning.
5. "VLM critic makes production safe" — critic can be unavailable/wrong; deterministic hard gate mandatory.
6. "100% pass on small fixtures proves ≥98%" — invalid statistical extrapolation.
7. "Card fallback is safe" — it can be visually poor and semantically inadequate for stateful teaching.
8. "Model-controlled keyframes are novel" — OmniManim and related systems plan geometry; differentiator would be typed solver-owned provable constraints.
9. "High VLM aesthetics means 3Blue1Brown-like" — must use blinded human reference and transparent dimensions.
10. "A good Binary Search demo generalizes to all disciplines" — domain-stratified failures must be measured.
11. "ScopeRefine copied means innovation" — Code2Video has localized repair; require measurable cross-artifact preservation and cost gains.
12. "Full pipeline schema validation proves every signal reaches pixels" — use consumer and mutation coverage against dead signals.

## 15. Approval checklist — the very next decision

- [x] Review canonical V3 research notes and #181/offline evidence.
- [x] Draft a concrete V3 plan with C1–C12, dependency graph, baseline, benchmark methodology and migration gate.
- [ ] User reviews and approves this plan or requests changes.
- [ ] Choose integration base and authorize merge of selected pilot fixes into main (separate explicit action).
- [ ] Start **V3-00 only** with an assigned coding agent after authorization.
- [ ] Authorize specific future paid experimental budget only after offline V3 prototypes pass.
- [ ] Never implement V3 implicitly because a documentation/CI gate passed.

## 16. Change control and references

This draft is a **prospective proposal**, not retrospective evidence. Update this one `PLAN_V3.md` and the existing `LEARNFLOW_V3_RESEARCH_NOTES.md` with newly confirmed decisions; keep pinned corpus and original #181 immutable. When changing targets: state reason, prior empirical result, any leakage risk, and bump protocol version **before** testing.

**Repository audit references:**
- https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37721597623
- https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37723264679
- https://github.com/wterrr/vibecode_challenge_mb/compare/main...chatgpt/live-v2d-gpt6-luna-paid-pilot
- https://github.com/wterrr/vibecode_challenge_mb/blob/chatgpt/live-v2d-gpt6-luna-paid-pilot/LEARNFLOW_V3_RESEARCH_NOTES.md

**External:** Code2Video (2025/ICML 2026); ALGOGEN (ACL Findings 2026); OmniManim (2026); LLM2Manim (2026); MINARD (2026); SGA (2026); EduVisAgent (2025); Mayer (2017) and Multimedia Learning meta-analysis (2025). Check precise benchmark and success boundaries before citing claims in papers or marketing.


### V3-26 code-HEAD acceptance snapshot (2026-10-09)

At implementation SHA 2f22aa52e48eb00992f119d1c2197d20ab2c2f0e, 26/26 GitHub Actions PASS including REAL Google Chrome Stable Playwright file:// reviewer HTML tests #37877573061. The first Chromium Headless Shell job failed to decode H264/AAC, so the runtime was changed to codec-capable Chrome, never a mock/JS syntax substitute. R01/R02 played both source-matched clips, browser screenshots of decoded MP4s and FFmpeg decode of AAC were retained, UI missing-input regressions PASSED, real browser Download JSON passed through the SHA-attested offline importer. Synthetic answers were deleted. Zero actual human participants/ratings; human comprehension/aesthetic preference, V3-16 human study and rights UNMEASURED; release BLOCKED. Actual GitHub artifacts and the independent review SOP: reports/v3_26_real_browser_independent_review.md. This note is documentation; a subsequent documentation commit needs separate exact HEAD CI.
