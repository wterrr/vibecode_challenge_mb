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

**One checkpoint at a time.** Every checkpoint requires: exact code scope, invariant tests, a reproducible command, at least one real rendered artifact when relevant, performance report, CI link, changed-file diff and one reviewer decision. Commands under `scripts/verify_v3_*` below are **specified future deliverables** and do not currently exist.

| Checkpoint | Dependency | Required deliverable and acceptance | Repro command after implemented |
| --- | --- | --- | --- |
| V3-00 Baseline & Merge Gate | #181 and offline #4 | lineage audit, complete V2 evidence manifest, protected Core hash, branch strategy, **upstream reuse/license inventory**, preserved historical #181 | `python scripts/verify_v3_baseline.py` |
| V3-01 Benchmark preregistration | V3-00 | frozen topic IDs, pilot rubric, control variables, human protocol and limits; no data leakage | `python scripts/verify_v3_benchmark_protocol.py` |
| V3-02 Canonical semantic contracts | V3-00 | Versioned VisualTeachingPlan/PatternSpec/StateLedger, ID/ref validation, three-way worked example agreement | `pytest -q tests/v3/test_contracts.py` |
| V3-03 Signal-preservation proof | V3-02 | mutation dependency/canonical hashes; ignored fields fail, no frozen V2 edit | `pytest -q tests/v3/test_signal_preservation.py` |
| V3-04 Visual Pattern Router | V3-02,03 | bounded eligibility/abstention; cards only deliberate recap; deterministic examples | `pytest -q tests/v3/test_pattern_router.py` |
| V3-05 Binary Search Trace Adapter | V3-02,03 | sorted-array oracle, mid/low/high, duplicates policy, found/not-found, edge cases | `pytest -q tests/v3/test_binary_search_trace.py` |
| V3-06 Stateful Sequence Renderer | V3-04,05 | real MP4 shows pointer/window changes over narration, no generated renderer code, verified equivalent frames | `python scripts/verify_v3_binary_search_render.py` |
| V3-07 Code + Process renderers | V3-04 | line/variable walkthrough and typed DAG/flow, actual non-card pixels + fixture demos | `python scripts/verify_v3_code_process.py` |
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
