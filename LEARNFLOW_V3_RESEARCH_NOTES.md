# LearnFlow V3 Research Notes

> **Status:** CANONICAL RESEARCH FILE — NOT AN IMPLEMENTATION PLAN  
> **Last updated:** 2026-10-05  
> **Purpose:** Preserve all evidence, architectural reasoning, external-system audits, deferred ideas, and V3 entry criteria while LearnFlow V2 is still under construction.  
> **Authoritative implementation plan right now:** `PLAN_V2.md`  
> **V3 implementation authorization:** **NOT YET GRANTED**

---

## 0. Canonical-file rule

This file is the single source of truth for **post-V2 / V3 research**.

Rules:

1. **Update this same file. Do not create `V3_NOTES_v2`, `final`, `final2`, etc.**
2. `PLAN_V2.md` remains authoritative for implementation until the V2 Core Gate passes.
3. Findings recorded here are **research evidence / design candidates**, not permission for the coding agent to implement them.
4. Every V3 candidate should be labeled as one of:
   - `PORT`
   - `ADAPT`
   - `REJECT`
   - `OPEN`
5. Research claims should distinguish:
   - paper claim;
   - verified repository behavior;
   - measured artifact/demo evidence;
   - inference / hypothesis.
6. When V2 finishes, do **not** create `PLAN_V3.md` directly from memory. First perform:
   - final V2 implementation audit;
   - V2 benchmark;
   - Code2Video comparison;
   - ALGOGEN comparison;
   - gap analysis;
   - reviewer attack;
   - only then draft `PLAN_V3.md`.

---

# 1. Current project snapshot

## 1.1 Current V2 architecture source of truth

Current canonical implementation architecture is defined by `PLAN_V2.md`.

North Star:

```text
                         HERMES
                   Agent Control Plane
                         │
          research / reasoning / pedagogy
             planning / QA / repair
                         │
                         ▼
              PedagogicalStoryboard
                         │
                         ▼
                ┌────────────────┐
                │   SceneGraph   │
                │ Semantic IR    │
                └───────┬────────┘
                        │
                        ▼
                Layout Compiler
                        │
          ┌─────────────┼──────────────┐
          ▼             ▼              ▼
      Cassowary       ELK          Specialized
       / Kiwi        Layered         Layouts
          │             │              │
          └─────────────┼──────────────┘
                        ▼
                   LayoutGraph
                        │
                        ▼
                 Motion Grammar
                        │
                        ▼
                   MotionPlan
                        │
                        ▼
                   Renderer
                        │
                        ▼
                Deterministic QA
                        │
                 ┌──────┴──────┐
                 │             │
               PASS           FAIL
                 │             │
                 │       deterministic fix
                 │             │
                 │        still failing
                 │             ▼
                 │        VLM Critic
                 │             │
                 │        ScenePatch
                 │             │
                 └──────◄──────┘
                        │
                        ▼
                  final scene
                        │
                        ▼
                 video assembly
                        │
                        ▼
                  video-level QA
                        │
                        ▼
                    final.mp4
```

Non-negotiable architectural boundary:

> **LLM/Hermes decides meaning.  
> SceneGraph represents meaning.  
> Layout Engine decides positions.  
> Motion Grammar decides valid motion.  
> Renderer decides pixels.  
> VLM evaluates and proposes structured patches; it does not directly write rendering code.**

This boundary must not be weakened in V3 without strong benchmark evidence.

---

## 1.2 V2.1 locked contracts to preserve

Current V2.1 already locks:

1. lesson-level `ConceptRegistry`;
2. first-class `InterSceneTransitionPlan`;
3. feasibility-first layout objective;
4. minimal Motion Grammar first;
5. artifact dependency + invalidation graph;
6. optional VLM quality tier;
7. V1/V2 isolation until Core Gate.

Any V3 design must explicitly state whether it preserves, extends, or replaces each of these.

---

## 1.3 Current implementation checkpoint status

As of the latest reviewed repository snapshot (`vibecode_challenge_mb (17).zip`):

```text
CP 2.7  Motion Grammar Tier 1        PASS
CP 2.8  Narration Beat Alignment     PASS
CP 2.9  Motion Scheduler + Compiler  FIX REQUIRED
CP 2.10 Persistent Transitions       NOT AUTHORIZED
```

Latest CP2.9 isolated test evidence:

```text
CP2.9 scheduler tests:        23 passed
CP2.9 compiler tests:         13 passed
CP2.7 + CP2.8 + CP2.9:      163 passed
full isolated tests/v2:      568 passed / 46 known real-ELK environment failures
```

Known CP2.9 hardening issues still under review at this snapshot:

- `PropertyTrack.metadata` deep JSON-safety / deterministic immutability;
- NODE/RELATION target-namespace collision when raw IDs match;
- `ResolvedMotionPlanTiming` must be cross-validated against `MotionPlan`;
- public compiled artifacts must reject impossible or semantically mismatched property-track states;
- property tracks require stronger endpoint/progress invariants.

These are **V2 issues**, not V3 research items.

---

# 2. V2 Core Gate — V3 must wait

Current V2 Core Gate requires:

```text
Render success            >= 98%
Fatal clipping            = 0
Fatal overlap             ~= 0
Invalid MotionPlan        = 0
Selective repair success  >= 90%
Reproducibility           = 100% for deterministic scenes
V1→V2 regression          = 0 critical product regressions
V2 static quality         > V1 baseline on agreed benchmark
VLM unavailable           does not break deterministic mode
Local repair              does not rebuild unaffected scenes
```

And the key statement remains:

```text
given a good storyboard
→ Core V2 consistently produces a good video
```

**V3 planning must not begin in earnest until this statement is empirically defensible.**

---

# 3. External research baseline

Primary V3 research targets:

1. **Code2Video**
   - Paper: https://arxiv.org/abs/2510.01174
   - Repository: https://github.com/showlab/Code2Video
   - Role in research: maximize pedagogical/visual expressiveness.

2. **ALGOGEN**
   - Paper: https://aclanthology.org/2026.findings-acl.156/
   - Repository: https://github.com/MAC-AutoML/ALGOGEN-lab
   - Role in research: semantic trace discipline, validation, deterministic rendering.

Secondary references:

- TheoremExplainAgent
- EduVisBench / EduVisAgent
- OmniManim / "See Before You Code" (arXiv:2605.15585)
- SGA: Symbolic Geometric Agent (arXiv:2607.18116)
- LLM2Manim (arXiv:2604.05266)
- MINARD / FigTalk (arXiv:2606.12576)
- TeachMaster (ACL 2026 Industry)
- ManimTrainer / ManimAgent + ManimBench (arXiv:2604.18364)
- ManiBench visual-logic benchmark
- DiagrammerGPT
- manim-shorts
- 3Blue1Brown / Manim as human-crafted quality reference, not as a claim that current AI systems equal it.

Research-source status matters:

- Code2Video, ALGOGEN, TeachMaster: published/venue-backed primary references used for system-level comparisons.
- OmniManim, SGA, LLM2Manim, ManimTrainer/ManimAgent, MINARD: 2026 preprint/recent-conference evidence used as supporting design evidence, not treated as unquestionable ground truth.
- 3Blue1Brown: human-crafted quality reference only.

---

# 4. Code2Video deep audit

## 4.1 High-level architecture

Paper/repo architecture:

```text
Topic
↓
Planner
↓
Storyboard
↓
Coder
↓
Executable Manim Python
↓
Render
↓
VLM Critic
↓
Layout/code repair
```

Important distinction:

- Code2Video uses **executable Python/Manim code as a shared representation**.
- LearnFlow intentionally does **not**.

---

## 4.2 Prompt appendix / executable prompt structure

The Code2Video paper appendix includes prompts for:

- Outline
- Storyboard
- Assets
- Visual Anchor
- Coder
- VideoLLM Refinement

Repository implementation splits this logic across prompt stages rather than one mega-prompt.

Observed functional decomposition:

```text
Stage 1
topic → pedagogical outline

Stage 2
outline → storyboard + lecture lines + animation descriptions

Stage 3
storyboard → Manim code

Stage 4
rendered video + layout context → structured critique → repair

Stage 5
video evaluation
```

### Finding

**The strongest design idea is not “use Manim”; it is decomposition of pedagogical reasoning before code generation.**

Status: `PORT/ADAPT`

---

## 4.3 Planner and key-section design

Code2Video Stage 1 behaves like an instructional designer:

- logical progression;
- prerequisite ordering;
- examples;
- graphical representation preference for math/physics.

Stage 2 introduces a particularly important constraint:

```text
maximum ~3 key sections
```

Key sections get higher animation/detail budget than normal sections.

Interpretation:

This is an early form of a **Hero Scene / Key Teaching Moment planner**.

### Evidence

Code2Video ablation reports a very large drop when Planner is removed:

```text
Full Code2Video:
Aesthetics ≈ 79.0
TeachQuiz  ≈ 82.0

w/o Planner:
Aesthetics ≈ 38.1
TeachQuiz  ≈ 40.5
```

This is a stronger signal than simply adding more animation primitives.

### Decision

`PORT` the principle, but translate it to LearnFlow artifacts.

Candidate future abstraction:

```text
PedagogicalStoryboard
└── sections[]
    ├── importance
    ├── learning_objective
    ├── key_misconception
    ├── visual_teaching_goal
    └── hero_budget
```

Do not implement before V2 Core Gate.

---

## 4.4 Visual Anchor system

Code2Video Coder prompt restricts generated code to a discrete 6×6 anchor grid rather than letting the LLM invent arbitrary x/y placement directly.

Conceptually:

```text
LLM
↓
A1–F6 discrete spatial anchor
↓
fixed coordinate mapping
↓
Manim placement
```

This reduces the model action space.

### Important nuance

This is **not** a full layout solver. The base class ultimately maps anchors to numeric coordinates and calls Manim placement functions.

### LearnFlow comparison

LearnFlow already uses the stronger abstraction:

```text
LLM
↓
semantic layout intent
↓
constraint/layout engine
↓
coordinates
```

### Decision

`REJECT` replacing LearnFlow layout with a fixed anchor grid.

`PORT/ADAPT` the anchor vocabulary for VLM/critic observability.

Future critic input may include:

```text
scene_id
object_id
semantic role
bbox
anchor cell / occupancy region
safe-zone relation
z-order
neighbor objects
```

This is more stable than source-code line numbers.

---

## 4.5 Critic design

Code2Video Critic focuses on constrained visual problems such as:

- overlap;
- lecture obstruction;
- off-screen content;
- bad grid utilization;
- missing fade-out.

Critic feedback is structured around fields such as:

```text
problem
solution
line_number
object_affected
```

### Useful principle

Critic should be given **structured visual context** and should output **localized structured diagnosis**.

### LearnFlow adaptation

Do not map diagnosis to Python lines.

Use:

```text
scene_id
artifact_type
object_id
issue_type
severity
constraint evidence
suggested patch class
```

Potential outputs:

```text
LayoutPatch
MotionPatch
ScenePatch
NarrationTimingPatch
```

Decision: `ADAPT`

---

## 4.6 ScopeRefine

Code2Video's ScopeRefine attempts:

```text
single-line fix
→ function/section fix
→ broader review
→ complete rewrite
```

It classifies common Manim/Python runtime errors and uses progressively broader repair.

### Strong evidence

Ablation indicates localized repair saves substantial time/tokens compared with retry/full-code debugging.

Reported values include approximately:

```text
Full ScopeRefine:
15.4 min
30.8K tokens

Retry:
42.9 min
49.8K tokens

Full-code debug:
39.2 min
42.1K tokens
```

### LearnFlow translation

Code2Video:

```text
traceback
→ source scope
→ rewrite code
```

LearnFlow should use:

```text
QA issue
→ owning artifact
→ smallest affected semantic/geometry/motion scope
→ patch
→ dependency invalidation
→ recompile only necessary downstream artifacts
```

Potential future name:

```text
ArtifactRefine
```

Decision: `PORT PRINCIPLE / ADAPT MECHANISM`

---

# 5. Code2Video implementation failure modes verified from repository

These findings are especially important because they are **repository behavior**, not paper-level description.

## 5.1 Critic is fail-open

Observed behavior:

If VLM/Gemini layout analysis raises an exception, the agent can return feedback equivalent to:

```text
has_issues = False
suggested_improvements = []
```

The pipeline can therefore interpret **critic failure as no detected problem**.

### V3 lesson

LearnFlow quality state must distinguish:

```text
PASS
FAIL
UNKNOWN / QA_ERROR
```

`UNKNOWN` must not silently become `PASS`.

Decision: `REJECT Code2Video behavior`

Future requirement: fail-closed or explicit configurable policy.

---

## 5.2 Final video can omit failed sections

Observed Code2Video flow:

- sections render independently;
- some sections may fail;
- `merge_videos()` merges only available rendered sections.

Therefore a planned four-section lesson may theoretically become:

```text
S1 ✓
S2 ✓
S3 ✗
S4 ✓

final = S1 + S2 + S4
```

while still producing an MP4.

### V3 lesson

LearnFlow publish completeness should enforce:

```text
required_scene_set == published_scene_set
```

unless omissions are explicitly authorized by a higher-level recovery policy.

Decision: `REJECT behavior`

---

## 5.3 Grid repair is coupled to source line numbers

`GridPositionExtractor` records:

```text
object_name
position
scale
line_number
original_code
```

`GridCodeModifier` then parses feedback that references a line number and replaces a line in generated Python.

### Risk

Line numbers become stale after code changes.

### LearnFlow lesson

Use stable artifact IDs:

```text
scene_04 / node_loss_function
```

not:

```text
line 121
```

Decision: `REJECT implementation / ADAPT localized-repair idea`

---

## 5.4 ScopeRefine dry run does not execute animation body

Observed strategy:

The generated `construct()` body is effectively short-circuited by inserting an early wait/return for dry-run validation.

So the dry-run proves mostly:

```text
syntax
imports
class construction
```

not actual animation behavior.

### LearnFlow lesson

Typed closed artifacts + compiler validation can remove an entire class of generated-code runtime problems.

Decision: `REJECT generated-code workaround`

---

## 5.5 Critic patch parser can produce zero semantic change

Observed path:

- critic finds a visual issue;
- parser expects a specific pattern such as source line + grid call;
- if parsing fails, modifications may be empty;
- original code can be returned unchanged;
- if code still renders, pipeline may regard optimization as successful.

### V3 lesson

A repair attempt should require:

```text
meaningful artifact diff
+
postcondition improvement / issue resolution evidence
```

not merely:

```text
render did not crash
```

Decision: `PORT lesson`

---

# 6. Code2Video evaluation and quality ceiling

Human-study evidence suggests Code2Video can be strong pedagogically while still having a large layout gap from polished human-crafted 3Blue1Brown material.

Reported example:

```text
Human 3B1B:
Element Layout ~98.9
Animation Timing ~97.2
Visual Consistency ~98.0
Average aesthetics ~96.5

Strong Code2Video configuration:
Element Layout ~60.2
Animation Timing ~89.3
Visual Consistency ~92.0
Average aesthetics ~81.8
```

Interpretation:

- temporal motion and style consistency can approach high levels;
- **layout/visual composition remains a major weakness**;
- LearnFlow's constraint-layout direction remains justified.

Do not interpret Code2Video's result as evidence that current autonomous systems equal 3Blue1Brown.

---

# 7. ALGOGEN deep audit

## 7.1 High-level architecture

ALGOGEN separates semantic execution from rendering:

```text
Algorithm / problem
↓
LLM generates tracker.py
↓
tracker executes
↓
VTA / SVL trace JSON
↓
validation
↓
RSL style specification
↓
render config
↓
deterministic renderer
↓
video
```

Core design principle:

```text
what happened
≠
how it should be rendered
```

This is highly aligned with LearnFlow's semantic/render boundary.

Decision: `PORT PRINCIPLE`

---

## 7.2 VTA / SVL trace

Observed trace artifacts contain:

- version;
- algorithm identity/family;
- initial state;
- auxiliary views;
- variable state;
- pseudocode;
- deltas;
- operation sequences;
- style-state keys.

Example operation families include:

```text
updateStyle
updateValues
moveElements
shiftElements
updateBoundary
addNode/removeNode
addEdge/removeEdge
updateTableCell
showDependency
appendToList/popFromList
reparent
highlightPath
insertIntoBucket
showHash
highlightCollision
showComment
...
```

### Strength

For algorithm visualization, executable traces give a strong representation of state transitions.

### Limitation

This representation is domain-specific.

It is not obviously sufficient for:

- biology explanation;
- conceptual economics;
- historical causality;
- physical illustration;
- abstract visual metaphor;
- non-algorithmic storytelling.

### Decision

`ADAPT` as an **optional domain adapter**, not as the universal LearnFlow IR.

Potential future path:

```text
Algorithm topic
↓
ExecutableTraceAdapter
↓
state transition sequence
↓
SceneGraph / MotionPlan
```

---

## 7.3 VTA prompt discipline

ALGOGEN's VTA specification prompt is large and strict.

Important rules include:

- fixed version;
- bounded operation structure;
- no invalid numeric sentinels such as Infinity;
- stable field names;
- deterministic traversal/tie-breaking;
- graph adjacency ordering;
- algorithm correctness prioritized over visual effect;
- multi-version self-check workflow.

The generation prompt asks for a draft, self-check, corrections, final verification, and final code.

### Lesson

Prompts can dramatically reduce action space and hallucination.

### But

Prompt constraints are not equivalent to runtime-enforced contracts.

Decision: `PORT prompt discipline only when paired with runtime validators`

---

# 8. ALGOGEN implementation gaps verified from repository

## 8.1 Trace runtime validation is shallower than the specification

Observed `run_and_validate_trace()` behavior includes checks roughly equivalent to:

```text
root is object
svl_version == 5.0
initial_frame exists
deltas exists
```

after executing the generated tracker.

This is much weaker than the full VTA specification described in the long prompt.

### Lesson

A 40KB prompt is not a substitute for:

```text
schema validation
semantic validation
cross-reference validation
runtime invariant tests
```

Decision: `REJECT prompt-only guarantees`

---

## 8.2 RSL semantic checks are limited

Observed `semantic_check_rsl()` checks include:

- operation name belongs to allowed set;
- animation runtime range;
- style scale range;
- timeline FPS range.

This is useful but shallow.

Missing or not obviously covered in the observed checker:

- whether rule op actually occurs in trace;
- annotation frame within trace bounds;
- layout compatible with data type;
- annotation collision;
- semantic cross-reference across trace and style layer.

### Lesson

LearnFlow should continue stronger artifact cross-validation.

Decision: `DO NOT LOWER V2 VALIDATION STANDARD`

---

## 8.3 Important dead-signal finding: RSL animation rules are dropped on the public pipeline path

Observed RSL artifact includes rules like:

```text
showComment → fade
updateStyle → pulse
updateTableCell → glow
updateValues → pulse
```

But observed `rsl_to_render_config()` reads:

```text
theme
timeline
layout
annotations
```

and does **not** consume the `rules` field.

The public pipeline then converts RSL to render config and renders from the resulting config.

### Implication

A style signal can be:

```text
generated
→ schema-valid
→ semantically meaningful in JSON
→ silently dropped at compiler boundary
```

### This is a critical LearnFlow lesson

For every important semantic field:

```text
change upstream semantic input
→ downstream compiled artifact MUST measurably change
```

and:

```text
break/remove required semantic input
→ pipeline MUST fail or downgrade explicitly
```

Potential test family:

```text
semantic signal preservation tests
```

Decision: `PORT TESTING PRINCIPLE`

---

## 8.4 RSL still exposes coordinate-like escape hatches

Observed RSL annotation examples include explicit position arrays.

Therefore it is inaccurate to claim that ALGOGEN completely eliminates LLM-controlled coordinates.

### Lesson

Constrained DSLs still require escape-hatch audits.

Decision: `REJECT simplistic claim`

---

## 8.5 Renderer is deterministic-oriented but still renderer-specific internally

ALGOGEN's public renderer maps trace/config into Manim primitives and layout logic.

This is acceptable for ALGOGEN's domain but should not motivate LearnFlow to expose Manim as semantic IR.

Decision: `KEEP LearnFlow renderer boundary`

---

# 9. ALGOGEN reliability claim — methodological caution

Paper reports approximately:

```text
ALGOGEN:      99.8%
Manim-Direct: 82.5%
```

However the reported success boundaries are not identical.

Observed interpretation:

```text
ALGOGEN:
trace-generation success / valid VTA-JSON

Manim-Direct:
end-to-end video rendering success
```

### Research rule

Do **not** write:

```text
ALGOGEN has 99.8% end-to-end video reliability
```

unless a later audit finds evidence for that exact claim.

Safer statement:

> ALGOGEN reports 99.8% trace-generation success under its evaluation protocol, while Manim-Direct reports 82.5% video-render success under a different boundary.

Decision: `KEEP CAVEAT`

---

# 10. ALGOGEN public artifact evidence

Repository includes real chains for some cases:

```text
tracker.py
→ trace.json
→ trace_rsl.json
→ trace_render_config.json
→ llm_video.mp4
→ aes_result.json
```

This is valuable because the pipeline can be audited end-to-end.

However public case coverage is not uniform.

Example observation:

- array / DP cases include a more complete artifact chain;
- a graph case in `outputs/CASE` lacks `llm_video.mp4` and AES in the same folder, although a graph video exists elsewhere in the repo.

This does **not** prove graph failure.

It does mean the public repository is not by itself a complete reproduction archive for every experimental run behind the paper statistics.

Decision: `CAUTION`

---

# 11. ALGOGEN visual-quality evidence

Public AES examples show a consistent pattern:

- algorithmic correctness can be strong;
- visual execution can be clean;
- educational flow can still be shallow;
- attractiveness/visual metaphor can remain basic.

Example Sieve score:

```text
Element Layout      15/20
Attractiveness      13/20
Logic Flow          17/20
Accuracy/Depth      18/20
Visual Consistency  16/20
Overall             79/100
```

Feedback notes:

- basic aesthetic;
- cramped hierarchy;
- limited whitespace;
- simple animations;
- limited creative metaphor.

Example `Binary Trees With Factors` score:

```text
Overall ~81/100
```

Feedback notes:

- accurate code/solution;
- minimal animation;
- weak conceptual introduction;
- insufficient explanation of why the algorithm works;
- missing tree metaphor / deeper intuition.

### Interpretation

ALGOGEN optimizes:

```text
correct state execution
+
reliable visualization
```

more than:

```text
deep visual pedagogy
+
visual metaphor
+
cinematic explanation
```

This complements Code2Video rather than replacing it.

---

# 12. Cross-system comparison

| Capability | Code2Video | ALGOGEN | LearnFlow V2 direction | V3 implication |
|---|---|---|---|---|
| Pedagogical decomposition | Strong | Limited/domain-specific | Planned/partial | Strengthen |
| Hero/key sections | Yes | Not central | Not yet first-class | Add candidate |
| Visual reasoning | Stronger | Limited | Emerging | Strengthen |
| Arbitrary code generation | Yes | Tracker only | No | Keep No |
| Semantic IR | Moderate | Strong VTA | Strong SceneGraph | Preserve |
| Layout | Anchor grid + Manim | RSL/template layouts | Constraint engine | Preserve LearnFlow |
| Motion | Raw Manim | Trace/render mapping | MotionPlan/compiler | Preserve LearnFlow |
| Localized repair | Code scope | Trace/runtime | Artifact scope | Develop ArtifactRefine |
| Runtime validation | Render-heavy | Mixed/shallow in public path | Strong typed contracts | Do not lower |
| Semantic/render separation | Partial | Strong | Strong | Preserve |
| Reproducibility | Medium | Strong orientation | Explicit V2 goal | Preserve |
| Visual ceiling | High | Medium | TBD | Learn from Code2Video |
| General domains | Better | Algorithm-centric | General | Preserve generality |
| Critic | VLM + line/grid patch | Mainly evaluation/style | Optional VLM critic | Use stable artifact IDs |
| Failure policy | Some fail-open paths | Mixed | Should be explicit | Fail-closed/UNKNOWN |
| Signal preservation | Direct code reduces one class | RSL dead-field issue observed | Typed compiler | Add signal-preservation tests |

---

# 12.5 2026 extended evidence — visual planning, geometry, grounding, and visual logic

This section was added after the governed live V2D pilot exposed a concrete visual ceiling in the real LearnFlow renderer.

## 12.5.1 V2 live visual-ceiling evidence — run #156

Artifact evidence from governed live V2D run #156:

```text
topic: lfb-001-cs
scene_count: 5
layout_intents:
  CONCEPT_CARD: 4
  PROCESS: 1
```

The accepted SceneGraphs were not semantically empty. They contained:

- TEXT;
- CONCEPT;
- CODE;
- PROCESS roles;
- code snippets;
- analogies;
- questions;
- worked-example steps.

However the current deterministic renderer routes all node kinds through the same generic `_draw_node()` family:

```text
rounded rectangle
+
centered text
+
kind-dependent fill color
```

Therefore:

```text
CODE != code visualization
CHART != chart visualization
EQUATION != mathematical transformation
IMAGE != image composition
CONCEPT != visual metaphor
```

at the actual pixel layer.

The live SceneGraph distribution also confirms an upstream collapse:

```text
4 / 5 scenes -> CONCEPT_CARD
CONCEPT_CARD -> one title + vertically stacked support boxes
```

### Research conclusion

V2 has now demonstrated a distinct failure class:

```text
semantic-contract success
+
layout feasibility
+
motion validity
+
A/V production success
!=
professional visual explanation
```

This is not primarily a motion bug.

Adding more FADE / SLIDE / REVEAL events to generic cards cannot solve the representation bottleneck.

Status: `EVIDENCE CONFIRMED`

---

## 12.5.2 OmniManim / See Before You Code

Primary source:

- https://arxiv.org/abs/2605.15585

OmniManim explicitly identifies spatial planning as a bottleneck that survives ordinary multi-agent decomposition.

Relevant design:

```text
Shared Scene State
-> Scene Agent
-> Vision Agent
-> sparse keyframe layout plan
-> Code Agent
-> render
-> structured diagnostics
-> localized repair
```

The Vision Agent predicts:

- object-level scene state;
- coarse semantic spatial priors;
- refined bounding boxes;
- sparse keyframes;
- interpolation-aware safety.

Important reported evidence:

- layout is treated as temporal planning, not only static placement;
- endpoint-safe layouts can still collide during interpolation;
- the method explicitly penalizes intermediate-frame collisions;
- human evaluation reports materially stronger layout/overlap scores than Code2Video;
- the strongest gains are spatial, not generic style gains.

### LearnFlow decision

`PORT PRINCIPLE / ADAPT ARCHITECTURE`

Do not copy generated Manim coordinates into LearnFlow.

Instead extend the LearnFlow-owned geometry layer:

```text
Semantic Visual Plan
-> pattern selection
-> KeyframeLayoutPlan
-> deterministic / learned-assisted layout solver
-> interpolation safety validation
-> MotionPlan
```

The LLM still must not own raw x/y geometry.

A learned bounding-box denoiser is `DEFER` until a deterministic pattern/layout baseline is measured.

---

## 12.5.3 SGA — deterministic geometric verification

Primary source:

- https://arxiv.org/abs/2607.18116

SGA constructs symbolic scene geometry from executable animation and computes deterministic spatial-conflict evidence. It introduces MVQS as a rendering-free proxy for spatial integrity and reports improvements when inserted into existing code-centric pipelines.

### LearnFlow comparison

LearnFlow does not need SGA's code-to-scene extraction because it already owns:

```text
SceneGraph
LayoutGraph
stable object IDs
geometry
```

The transferable idea is the metric/gate:

```text
typed object geometry
-> deterministic conflict descriptors
-> targeted repair
```

### Decision

`PORT METRIC PRINCIPLE`

Candidate V3 geometry score must remain decomposable; do not hide overlap, clipping, spacing, and relation violations inside one opaque scalar.

---

## 12.5.4 LLM2Manim — pedagogy and learner evidence

Primary source:

- https://arxiv.org/abs/2604.05266

Relevant mechanisms:

- segmentation;
- signaling;
- dual coding;
- symbol ledger for consistency;
- selective regeneration;
- human review.

The reported 100-student within-subject study found higher post-test performance for the animation condition than PowerPoint, alongside higher engagement and lower cognitive load.

### LearnFlow decision

`PORT PEDAGOGICAL PRINCIPLES`

LearnFlow V3 should make these principles machine-checkable where possible:

```text
segment boundary
signal / emphasis target
symbol identity
visual-verbal pairing
cognitive-load budget
```

The symbol-ledger idea generalizes naturally to the existing ConceptRegistry.

Generated Manim code remains `REJECT` as canonical LearnFlow IR.

---

## 12.5.5 EduVisAgent — visual reasoning decomposition

Primary source:

- https://arxiv.org/abs/2505.16832

EduVisAgent separates:

- instructional planning;
- reasoning decomposition;
- metacognitive prompting;
- visualization design.

Its benchmark is explicitly pedagogical rather than only aesthetic.

### Decision

`PORT EVALUATION PRINCIPLE`

The Visual Director should be evaluated on whether the representation supports the reasoning process, not merely whether frames look clean.

This strengthens the need for:

```text
visual_teaching_goal
representation_choice
expected_visible_change
```

as first-class artifacts.

---

## 12.5.6 DiagrammerGPT — bounded diagram plans and specialized object rendering

Primary source:

- https://arxiv.org/abs/2310.12128

Useful separation:

```text
diagram plan
  entities
  relations
  layout
-> renderer
-> explicit text rendering
```

DiagrammerGPT also demonstrates that one plan can target multiple vector-capable backends and that icons/assets can be resolved independently from text labels.

### LearnFlow decision

`PORT / ADAPT`

LearnFlow should not use a diffusion diagram renderer as canonical output.

The transferable mechanism is:

```text
semantic diagram pattern
+
asset/icon resolution
+
deterministic labels/relations
+
backend-independent object plan
```

This directly motivates specialized visual renderers instead of one generic card renderer.

---

## 12.5.7 MINARD / FigTalk — narration-to-visible-region grounding

Primary source:

- https://arxiv.org/abs/2606.12576

MINARD turns scientific figures into narrated walkthroughs by grounding narration sequentially to figure regions.

### LearnFlow decision

`ADAPT`

Generalize figure-region grounding into:

```text
narration beat
-> visual teaching goal
-> target object / region / relation
-> expected visible change
```

This becomes a measurable `BeatVisualCoverage` contract.

A narration beat that introduces an important concept but produces no corresponding visible evidence is a quality failure even when the video renders successfully.

---

## 12.5.8 ManimBench / ManiBench / Renderer-in-the-loop evidence

Relevant sources:

- https://arxiv.org/abs/2604.18364
- https://github.com/NtrpyDev/manim-bench
- https://github.com/nabin2004/ManiBench

Important lesson:

```text
render success != visual logic correctness
```

ManiBench explicitly separates:

- executability;
- visual-event alignment;
- visual coverage;
- version/API errors.

ManimTrainer/ManimAgent also reports that visual metrics and code metrics are not interchangeable; renderer-in-the-loop feedback improves visual outcomes.

### LearnFlow decision

`PORT METRICS`

Future V3 benchmark must include:

```text
VisualEventAlignment
RepresentationCoverage
BeatVisualCoverage
TemporalOrderAccuracy
VisualLogicDrift
```

in addition to ordinary render success.

---

## 12.5.9 TeachMaster

Primary source:

- https://aclanthology.org/2026.acl-industry.7/

TeachMaster reinforces the high-level-director model:

```text
educator / planner owns pedagogical intent
agents own production execution
```

Decision: `SUPPORTING EVIDENCE`

Its use of code as semantic medium is not adopted because LearnFlow already has typed semantic artifacts.

---

## 12.5.10 Synthesis from newer evidence

The newer evidence changes the strongest V3 hypothesis from:

```text
better planner
+
more animation primitives
```

to:

```text
Pedagogy Planner
-> Visual Teaching Plan
-> bounded representation / visual-pattern choice
-> specialized semantic visual compiler
-> keyframe-aware geometry
-> interpolation-safe motion
-> specialized renderer
-> deterministic geometry / visual-logic QA
-> VLM pedagogical + aesthetic critic
-> artifact-local repair
```

This preserves the LearnFlow boundary:

> LLM chooses meaning and representation class.  
> LearnFlow-owned compilers choose geometry, timing legality, and pixels.

---

# 13. Candidate V3 capability backlog

> These are **research candidates only**. None are authorized implementation checkpoints yet.

## V3-C1 — Pedagogy Planner

Status: `PORT`

Goals:

- prerequisite reasoning;
- misconception identification;
- explanation decomposition;
- intended learner state before/after section;
- explanation ordering;
- evidence/example selection.

Potential artifacts:

```text
LearningObjective
PrerequisiteGraph
MisconceptionSet
PedagogicalSection
```

Key question:

Can planner quality be measured separately from renderer quality?

---

## V3-C2 — Hero Scene / Key Teaching Moment Planner

Status: `PORT/ADAPT`

Goals:

- identify 1–3 sections deserving extra visual budget;
- allocate complexity selectively;
- avoid making every scene equally animated;
- maximize explanation impact per render/LLM cost.

Potential fields:

```text
importance
hero_score
visual_complexity_budget
allowed_motion_tier
representation_depth
```

Key question:

Does hero allocation improve human-rated comprehension/aesthetics over uniformly animated scenes?

---

## V3-C3 — Visual Director

Status: `PORT/ADAPT`

The Visual Director should answer:

```text
"What should the learner SEE in order to understand this idea?"
```

not merely:

```text
"What animation should be played?"
```

Potential outputs:

```text
visual_teaching_goal
representation_choice
visual_metaphor
comparison_structure
causal_flow
progressive_reveal_strategy
persistent_objects
```

Candidate representation decisions:

```text
equation
graph
geometry
timeline
network
flow
state machine
physical metaphor
before/after comparison
counterexample
```

---

## V3-C4 — Beat → Visual Teaching Goal binding

Status: `PORT`

V2 has narration timing and motion triggers.

V3 candidate adds semantic intent per beat:

```text
beat_id
narration_semantics
visual_teaching_goal
target_concepts
expected_visible_change
```

This separates:

```text
when to animate
```

from:

```text
why this animation exists pedagogically
```

---

## V3-C5 — Advanced Semantic Visual Grammar + Visual Pattern Library

Status: `PORT/ADAPT — RESEARCH DIRECTION CLOSED; IMPLEMENTATION NOT YET AUTHORIZED`

The V2 #156 artifact and newer external evidence resolve the previous high-level uncertainty: V3 requires a bounded visual representation layer between semantic planning and rendering.

### Required compile path

```text
VisualTeachingPlan
-> RepresentationChoice
-> VisualPatternSpec
-> SceneGraph / typed visual objects
-> KeyframeLayoutPlan
-> MotionPlan
-> specialized renderer
```

The representation choice is semantic; raw geometry is not model-owned.

### Initial bounded visual-pattern taxonomy

The first V3 implementation should cover a small, testable set with explicit eligibility and fallback rules:

```text
CONCEPT_DIAGRAM
CODE_WALKTHROUGH
EQUATION_DERIVATION
FUNCTION_GRAPH
DATA_CHART
PROCESS_FLOW
CAUSAL_GRAPH
TIMELINE
COMPARISON
STATE_MACHINE
GEOMETRY_CONSTRUCTION
WORKED_EXAMPLE_BOARD
FIGURE_WALKTHROUGH
QUIZ_REVEAL
SUMMARY_RECAP
```

`SUMMARY_RECAP` may legitimately use cards.

Cards must no longer be the universal rendering primitive.

### Specialized renderer requirement

Node kinds and representation patterns must produce materially different pixels:

```text
CODE -> code panel / syntax-aware lines / line highlight
EQUATION -> typeset expression / term identity / transform
CHART -> axes / marks / labels / data-driven transitions
GRAPH -> nodes / edges / structural emphasis
TIMELINE -> temporal axis / events / progression
GEOMETRY -> geometric primitives / construction steps
FIGURE -> asset / region overlays / grounded highlights
QUIZ -> prompt / delayed reveal / answer-state transition
```

A backend may share low-level drawing utilities, but semantic categories may not all collapse to `rounded_rectangle + text`.

### Advanced motion candidates

```text
MORPH
RESIZE
TRACE_PATH
semantic transform
persistent equation transformation
graph deformation
vector projection
geometry construction
camera choreography
```

These remain individually gated by:

- pedagogical value;
- deterministic compilation;
- testability;
- fallback behavior;
- repairability;
- benchmark gain.

### Fallback hierarchy

A specialized visual failure should degrade semantically:

```text
preferred specialized pattern
-> simpler pattern in same representation family
-> static but semantically faithful representation
-> explicit QA failure
```

It must not silently collapse every failure to CONCEPT_CARD.

### Anti-monotony principle

The benchmark must measure repeated representation collapse.

Candidate metrics:

```text
scene_archetype_distribution
max_consecutive_same_archetype
specialized_representation_coverage
visual_pattern_entropy
card_fallback_rate
```

Thresholds remain empirical and must be preregistered after the first V3 prototype.

---

## V3-C6 — Artifact Critic

Status: `ADAPT`

Inspired partly by Code2Video Visual Anchor Critic.

Critic receives:

```text
rendered frames/video
SceneGraph
LayoutGraph
MotionPlan
compiled motion
stable object IDs
bounding boxes
anchor/occupancy summaries
QA evidence
```

Critic returns structured issue objects only.

No raw pixel control.

No arbitrary renderer code.

---

## V3-C7 — ArtifactRefine

Status: `PORT PRINCIPLE`

ScopeRefine translated to typed artifacts.

Example routing:

```text
overlap
→ LayoutPatch

motion too early
→ MotionPatch

wrong visual representation
→ SceneGraph/VisualDirector patch

narration mismatch
→ script/beat patch

cross-scene continuity
→ InterSceneTransitionPlan patch
```

Repair success should require:

```text
artifact diff exists
+
issue no longer reproduces
+
deterministic QA still passes
```

---

## V3-C8 — Executable Trace Domain Adapter

Status: `ADAPT`

Inspired by ALGOGEN.

Use only for domains where a correct executable state transition is naturally available:

- algorithms;
- data structures;
- state machines;
- selected protocol simulations;
- perhaps simple computational processes.

Pipeline candidate:

```text
domain problem
↓
validated executable trace
↓
TraceAdapter
↓
SceneGraph state sequence
↓
MotionPlan
```

Do not make trace semantics mandatory for all LearnFlow topics.

---

## V3-C9 — Semantic signal-preservation test suite

Status: `PORT`

Required principle:

For important fields:

```text
semantic perturbation upstream
→ observable downstream compiled/render effect
```

Example:

```text
change MotionPlan trigger
→ schedule time changes

change Visual Director representation
→ SceneGraph structure changes

change RSL-like style rule
→ compiled renderer config changes
```

Negative test:

```text
required signal missing
→ explicit error / fallback state
```

No silent dropping.

---

## V3-C10 — Fail-closed Quality Gate

Status: `PORT LESSON`

Do not equate:

```text
critic unavailable
```

with:

```text
critic PASS
```

Candidate state machine:

```text
DETERMINISTIC_PASS
DETERMINISTIC_FAIL
CRITIC_PASS
CRITIC_FAIL
CRITIC_UNAVAILABLE
QA_ERROR
PUBLISH_BLOCKED
```

Exact publish thresholds remain empirical, but the state model itself is no longer an open architectural question.

---

## V3-C11 — Keyframe-aware Layout and Interpolation Safety

Status: `PORT PRINCIPLE / ADAPT`

Motivated strongly by OmniManim.

V2 LayoutGraph is primarily scene-static. V3 needs a bounded extension for representations whose visual state changes materially during a scene.

Candidate artifact:

```text
KeyframeLayoutPlan
  scene_id
  keyframes[]
    beat_ref
    object_states[]
      object_id
      visibility
      semantic_region
      layout_constraints
```

Rules:

- LLM may specify semantic region and relation intent;
- layout engine owns coordinates;
- intermediate motion must be checked for collision/occlusion;
- stable object identity must survive keyframes;
- static patterns do not need unnecessary keyframes.

A learned visual prior may later assist the solver, but deterministic specialized patterns are the required baseline.

---

## V3-C12 — Beat-to-Visual Grounding and Visual Logic Coverage

Status: `PORT / ADAPT`

Required chain:

```text
narration beat
-> semantic claim / learning objective
-> visual teaching goal
-> target visual object(s)
-> expected visible change
-> rendered evidence
```

Candidate deterministic / critic metrics:

```text
BeatVisualCoverage
VisualEventAlignment
RepresentationCoverage
TemporalOrderAccuracy
ConceptPersistenceAccuracy
VisualLogicDrift
```

This prevents a syntactically valid animation from passing when the narration teaches one thing and the learner sees unrelated cards.

---

# 14. Things V3 should probably NOT do

## 14.1 Do not make arbitrary Manim/Python canonical

Status: `REJECT`

Reasons:

- difficult validation;
- difficult deterministic replay;
- source-level repair;
- API/version brittleness;
- weak artifact semantics;
- renderer coupling.

Generated code may still be useful experimentally as an **external baseline**, not as LearnFlow's core IR.

---

## 14.2 Do not let the VLM assign raw geometry

Status: `REJECT`

VLM may diagnose:

```text
overlap
poor hierarchy
wasted space
wrong emphasis
```

but Geometry Engine owns final placement.

---

## 14.3 Do not use source-code line numbers as object identity

Status: `REJECT`

Use:

```text
lesson_id
scene_id
concept_id
node_id
relation_id
event_id
track_id
```

---

## 14.4 Do not rely on prompt contracts without runtime enforcement

Status: `REJECT`

For every critical invariant:

```text
prompt rule
+
schema validation
+
cross-artifact validation
+
runtime reproduction
```

where applicable.

---

## 14.5 Do not assume a DSL is used just because it validates

Status: `REJECT`

Compiler/consumer coverage must be demonstrated.

Every important field needs signal-preservation tests.

---

# 15. Candidate V3 benchmark design

V3 should not be written until V2 benchmark data exists.

A future benchmark should compare at minimum:

```text
LearnFlow V2
Code2Video
ALGOGEN (where domain-compatible)
V1 baseline
human-crafted references where appropriate
```

Possible topic groups:

### Algorithms
- BFS/DFS
- dynamic programming
- sorting
- Sieve of Eratosthenes

### Mathematics
- derivative intuition
- matrix multiplication
- Fourier intuition
- probability distributions

### Computer systems
- TCP handshake
- cache hierarchy
- virtual memory
- neural-network backpropagation

### General conceptual explanation
- supply/demand
- photosynthesis
- causal systems
- historical process / timeline

Metrics should separate:

```text
render success
semantic correctness
layout quality
temporal alignment
continuity
visual consistency
pedagogical clarity
knowledge transfer
human preference
generation cost
repair cost
reproducibility
```

Do not collapse all metrics into a single aesthetic score.

---

# 16. Required experiments before PLAN_V3

## Experiment E1 — V2 reliability baseline

Measure:

```text
render success
fatal clipping
fatal overlap
invalid motion
deterministic replay
selective repair success
```

Required before V3.

---

## Experiment E2 — V2 visual ceiling

Choose a fixed topic suite and determine:

- what looks professional already;
- what still looks like a slideshow;
- where motion grammar is insufficient;
- where the real failure is planning rather than rendering.

---

## Experiment E3 — Planner ablation

After a candidate Pedagogy Planner prototype exists:

```text
good planner + same renderer
vs
basic planner + same renderer
```

This tests the Code2Video-inspired hypothesis that planning dominates quality.

---

## Experiment E4 — Hero Scene allocation

Compare:

```text
uniform animation budget
vs
hero-section budget
```

Measure human preference + comprehension.

---

## Experiment E5 — ArtifactRefine efficiency

Compare:

```text
full scene regeneration
vs
artifact-local repair
```

Measure:

- token cost;
- latency;
- unaffected artifact reuse;
- quality recovery.

---

## Experiment E6 — Executable trace adapter

Algorithm-only experiment:

```text
LLM SceneGraph directly
vs
validated executable trace → SceneGraph
```

Measure:

- semantic correctness;
- visual fidelity;
- runtime success;
- authoring cost.

---

## Experiment E7 — Signal-preservation mutation tests

For each candidate V3 artifact:

```text
mutate one semantic field
→ verify expected downstream artifact diff
```

This should become a permanent regression class.

---

# 17. Research closure status

## 17.1 Architectural questions now provisionally resolved

### Visual Director implementation shape

Current best architecture:

```text
LLM / Hermes
-> visual teaching goal + representation choice
-> bounded pattern library
-> LearnFlow compiler / solver
-> deterministic or learned-assisted geometry
-> renderer
-> QA / VLM critic
```

Not:

```text
LLM -> arbitrary pixels / x,y / Manim code
```

### Visual-pattern library

Decision: `YES`

A curated bounded library is now the preferred path for gaining expressiveness without making arbitrary executable code the canonical representation.

### Card role

Decision:

```text
valid for recap / summary / selected concept-card scenes
not universal fallback
not dominant lesson representation
```

### Domain adapters

Decision: `YES, selectively`

- algorithms / data structures -> executable trace adapter;
- math -> typed equation / graph / geometry adapters;
- figure-heavy scientific explanation -> figure-region grounding;
- general conceptual topics -> generic diagram / causal / timeline / metaphor patterns.

### Critic role

Decision:

- deterministic geometry / signal checks first;
- VLM critic for pedagogical representation, hierarchy, aesthetics, and visual-narration alignment;
- critic outage never silently becomes PASS.

### Layout ownership

Decision:

- LLM expresses semantic spatial intent;
- LearnFlow layout system owns final geometry;
- V3 may use keyframe-aware or learned-assisted priors;
- raw model-authored coordinates remain rejected.

---

## 17.2 Empirical questions still open

These questions cannot be honestly closed by literature review alone:

1. What is the smallest pattern library that covers >=90% of target LearnFlow topics without excessive fallback?
2. Does a deterministic pattern compiler reach the desired quality ceiling before a learned layout prior is necessary?
3. What exact visual-variety thresholds correlate with human preference rather than gratuitous animation?
4. Which advanced motion primitives improve comprehension after controlling for planner quality?
5. Is camera choreography necessary outside hero scenes?
6. What publish threshold should be used for VLM aesthetic/pedagogical critic scores?
7. How close can bounded semantic rendering get to Code2Video / OmniManim on human preference?
8. What is the minimum human benchmark before using any "3Blue1Brown-like" wording?
9. What cost/runtime ceiling is acceptable for normal scenes vs hero scenes?
10. How stable are keyframe/interpolation constraints across renderer versions?

These are experiment questions, not unresolved architecture placeholders.

---

# 18. Proposed V3 entry gate

`PLAN_V3.md` should not be created until all of the following are true.

## Gate A — V2 implementation complete

At minimum:

```text
CP2.7+ accepted
all V2 Core checkpoints completed
Core Gate measured
critical V2 architecture stable
```

---

## Gate B — V2 benchmark exists

Must include:

```text
fixed topic set
V1 vs V2 comparison
reliability metrics
visual quality metrics
known failure taxonomy
cost/runtime data
```

---

## Gate C — Code2Video research complete enough

Must answer:

```text
which Planner mechanisms create measurable gain?
which visual-anchor ideas remain useful without generated code?
what failure modes come from arbitrary Manim?
what Critic ideas transfer cleanly?
what ScopeRefine ideas transfer to artifact repair?
```

---

## Gate D — ALGOGEN research complete enough

Must answer:

```text
which VTA invariants are actually runtime-enforced?
what exact reliability boundary is measured?
which RSL fields are consumed end-to-end?
what domain adapter ideas generalize?
what breaks outside algorithms?
```

---

## Gate E — V3 hypotheses prioritized

Every proposed V3 capability must state:

```text
problem
evidence
expected gain
cost/complexity
acceptance metric
fallback
dependency
```

No feature may enter V3 solely because it is aesthetically attractive.

---

# 19. Draft shape of future PLAN_V3.md

> This is only a placeholder structure, not an authorized plan.

```text
PLAN_V3.md

0. V3 North Star
1. Evidence from V2
2. External baseline comparison
3. Non-negotiable inherited contracts

4. Pedagogy Planner
5. Hero Scene Planner
6. Visual Director
7. Visual Pattern Library
8. Advanced Semantic Visual Grammar
9. Keyframe-aware Layout Compiler
10. Specialized Renderer Fabric
11. Advanced Motion Grammar
12. Beat-to-Visual Grounding
13. Artifact Critic
14. ArtifactRefine
15. Domain Trace Adapters

16. Signal-preservation testing
17. Fail-closed QA
18. Benchmark harness
19. Migration / compatibility
20. Cost controls
21. V3 checkpoints
22. V3 Core Gate
```

This structure must be revised after final V2 evidence.

---

# 20. Handoff instructions for a new ChatGPT session

If continuing V3 research in a new session, provide:

```text
1. latest PLAN_V2.md
2. latest LearnFlow repository ZIP
3. this LEARNFLOW_V3_RESEARCH_NOTES.md
```

Optional if already available:

```text
DESIGN.md
PRD.md
benchmark outputs
example videos
```

Tell the new session:

```text
Treat PLAN_V2.md as current implementation source of truth.
Treat LEARNFLOW_V3_RESEARCH_NOTES.md as canonical post-V2 research context.
Do not create PLAN_V3.md until the V3 Entry Gate is satisfied.
Update the same research notes file after material new research findings.
Do not implement V3 features during V2 checkpoints.
```

---

# 21. Research decision ledger

## Code2Video

| Finding | Decision |
|---|---|
| Pedagogical Planner | `PORT` |
| Key/hero sections | `PORT/ADAPT` |
| Lecture ↔ visual alignment | `PORT` |
| 6×6 grid as primary layout engine | `REJECT` |
| Anchor vocabulary for critic | `ADAPT` |
| Arbitrary Manim as canonical representation | `REJECT` |
| Visual Critic structured diagnosis | `ADAPT` |
| ScopeRefine principle | `PORT` |
| Source-line repair | `REJECT` |
| Fail-open critic behavior | `REJECT` |
| Merge final video with missing required sections | `REJECT` |
| Render-success-only repair acceptance | `REJECT` |

---

## ALGOGEN

| Finding | Decision |
|---|---|
| Semantic trace / render separation | `PORT PRINCIPLE` |
| VTA as universal LearnFlow IR | `REJECT` |
| VTA as algorithm-domain adapter | `ADAPT` |
| Deterministic renderer philosophy | `PORT` |
| Strict generation prompt | `ADAPT` |
| Prompt-only guarantees | `REJECT` |
| RSL-like bounded presentation DSL | `ADAPT` |
| Explicit annotation coordinate escape hatch | `CAUTION` |
| Shallow public semantic checks | `DO NOT COPY` |
| Trace-generation 99.8% as e2e video success | `REJECT CLAIM` |
| Semantic signal-preservation testing | `PORT` |


## Newer 2026 visual-generation evidence

| Finding | Decision |
|---|---|
| OmniManim shared scene state | `PORT PRINCIPLE` |
| OmniManim explicit sparse keyframe visual planning | `ADAPT` |
| OmniManim interpolation-aware layout safety | `PORT` |
| OmniManim learned bbox denoiser as immediate dependency | `DEFER` |
| SGA symbolic geometry metrics / targeted repair | `PORT METRIC PRINCIPLE` |
| SGA code-to-geometry extraction | `NOT NEEDED` because LearnFlow already owns typed geometry |
| LLM2Manim segmentation / signaling / dual coding | `PORT` |
| LLM2Manim symbol ledger | `ADAPT INTO ConceptRegistry` |
| LLM2Manim arbitrary Manim as canonical IR | `REJECT` |
| EduVisAgent reasoning decomposition -> visualization design | `PORT PRINCIPLE` |
| DiagrammerGPT bounded diagram plan | `ADAPT` |
| DiagrammerGPT deterministic text + icon/vector rendering | `ADAPT` |
| MINARD narration-to-region grounding | `ADAPT TO BeatVisualCoverage` |
| ManimBench / ManiBench visual-event alignment + coverage metrics | `PORT` |
| Renderer-in-the-loop visual feedback | `PORT PRINCIPLE` |
| TeachMaster high-level-director paradigm | `SUPPORTING EVIDENCE` |

---

# 22. Most important research conclusion so far

The strongest current synthesis is:

```text
                  Code2Video
      pedagogical decomposition
       visual reasoning / hero moments
       critic vocabulary
              │
              ▼
     ┌────────────────────┐
     │     LearnFlow      │
     └────────────────────┘
              ▲
              │
                 ALGOGEN
          semantic discipline
          executable traces
          validation
          deterministic rendering
```

LearnFlow should aim for:

```text
Code2Video-level planning/visual intelligence
+
ALGOGEN-level semantic/reliability discipline
+
LearnFlow's typed SceneGraph/LayoutGraph/MotionPlan architecture
```

The current best hypothesis for approaching selected 3Blue1Brown-like output is:

```text
Pedagogy Planner
↓
Visual Director
↓
Hero Scene selection
↓
semantic representation choice
↓
advanced motion / rendering
```

not:

```text
add many animation primitives first
```

This hypothesis must be benchmarked after V2 Core.

---

# 23. Change log

## 2026-10-08 — User-approved one-paid-run V2 closure, for V3 planning only

The governed V2D paid run #180 (commit
`7c40d69d5d2f9ad5842a2be62c694ef8ed50000a`) completed
successfully end-to-end. Its video still exposed fatal readability concerns
from subtitle overlay and generic-card visual representation, so production
success is not evidence of professional visual quality.

**New budget policy:** The user wants **one final paid V2D evaluation**
on frozen `corpus_v1.json` topic **`lfb-005-cs` — Binary Search Intuition**
(beginner, 3-minute English lesson), **explicitly confirmed by the user
on 2026-10-08**. This topic is locked for the single final paid run; no
topic substitution after observing the result.
Model remains `openai/gpt-6-luna`. Only explicit manual
dispatch with positive paid-run confirmation is permitted on the isolated
pilot branch, after offline preflight and pre-API topic validation. Do not retry paid runs automatically, including after failures;
on HTTP 429 stop provider calls until the next day.

**Reduced-scope V3 planning gate (explicit evidence waiver):**
If the final one-topic pilot meets the frozen Core Freeze, contract gates,
real A/V production checks, no critical text/subtitle occlusion, factual
accuracy and a human review of the actual MP4, the user authorizes
**drafting PLAN_V3** and prioritizing measured V2 visual-ceiling gaps.

This is a deliberate waiver of the *full live benchmark requirement for
plan drafting*, not a claim that V2 reliability or learning outcomes are
statistically measured. The 100-topic live evaluation, V1-vs-V2 human
comparison, TeachQuiz effects and cost-distribution estimates remain
UNMEASURED/DEFERRED. No V3 implementation or SOTA claim follows
automatically from a single PASS.

**Final-run offline readiness (2026-10-08):** CI
[Final V2 Offline Preflight #2](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37721412808)
PASS (79 Hermes/caption regressions, 14 renderer regressions,
Core Freeze PASS). Using existing governed #180 files without provider
calls, 42 original TTS sentence cues produce 63 short pages and satisfy
the non-overlap and subtitle-band geometry checks. A 5-second local
sample was rendered/visually inspected with smaller subtitle typography.
This is not an end-to-end paid Binary Search PASS or human quality
approval. The one paid workflow_dispatch is still pending.

If the final pilot fails: preserve artifact/logs, record precise NO-GO
and outstanding defects; still no paid rerun without a new user decision.
Do not alter historical frozen Core Gate evidence or reference artifacts.

---

## 2026-10-07 — Visual-ceiling + extended 2026 research closure

Added:

- governed live V2D #156 visual-ceiling evidence;
- exact CONCEPT_CARD collapse evidence (4/5 scenes);
- generic renderer primitive diagnosis;
- OmniManim / See Before You Code audit;
- SGA geometry-verification lesson;
- LLM2Manim pedagogy + symbol-consistency evidence;
- EduVisAgent pedagogical-visualization evidence;
- DiagrammerGPT bounded diagram-plan lesson;
- MINARD narration-region grounding lesson;
- ManimBench / ManiBench / renderer-in-the-loop metrics;
- TeachMaster supporting evidence;
- bounded Visual Pattern Library decision;
- specialized renderer requirement;
- keyframe-aware layout / interpolation-safety capability;
- BeatVisualCoverage / VisualEventAlignment metrics;
- research-closure vs empirical-question split;
- updated future PLAN_V3 shape and decision ledger.

Research status after this update:

```text
major architecture direction: CLOSED ENOUGH FOR PLAN DRAFTING ONCE ENTRY GATES PASS
exact thresholds / pattern-set size / learned-layout necessity: EMPIRICAL
V3 implementation: NOT AUTHORIZED UNTIL ENTRY GATE
```

---

## 2026-10-05 — Initial canonical version

Added:

- V2 architecture baseline;
- current CP2.9 implementation status;
- V2 Core Gate;
- Code2Video prompt/Planner/Anchor/Critic/ScopeRefine audit;
- Code2Video runtime failure modes;
- ALGOGEN VTA/RSL/validator/renderer audit;
- reliability-methodology caveat;
- dead RSL animation-rule signal finding;
- PORT/ADAPT/REJECT ledger;
- V3 candidate backlog;
- benchmark requirements;
- open questions;
- V3 Entry Gate;
- new-session handoff instructions.

Next research work should update this same file.


---

## 2026-10-08 — PLAN_V3 research-to-implementation synthesis

**Status:** PLAN DRAFT PRODUCED; V3 CODE IMPLEMENTATION STILL NOT AUTHORIZED.

- Primary baseline remains final governed #181: technical SUCCESS with readable shorter subtitles; 3/3 generic `CONCEPT_CARD` scenes and no executable visual search trace. Its historical "find 16" registry vs "find 24" script mismatch is a known semantic limitation, **not** retrospectively corrected.
- The offline semantic validator and allowlisted exporter were introduced on the isolated pilot branch, passing offline #4 (87 Hermes/subtitle/semantic tests; 14 renderer PASS, 5 SKIP; Core Freeze PASS).
- PLAN_V3 translates C1–C12 into explicit typed artifacts, capability dependencies, fail-safe fallbacks, measurable ablation hypotheses, release gates, and a one-checkpoint-at-a-time ledger.
- Read additional literature grounding from Mayer multimedia design and 2025 meta-analysis: segmenting, signaling, temporal/spatial contiguity and coherence constrain useful visual motion. V3 must not maximize animation count.
- Branch audit: main was `29fab1d`, isolated paid pilot was `efd19bc` and 24 commits ahead/0 behind before plan-drafting. The primary V2/Hermes PRs have merged; older unmerged PR #8/#11/#14 require supersession review, **not** blind cherry-pick. No merge is authorized as part of PLAN drafting.
- New planning decision: prioritize identity/signal contracts, a **dynamic Binary Search golden clip** (trace + stateful visual renderer), then other representative renderers; only then expand planners, critics, repair and human comparative study.
- V3 planner targets (e.g., ≥90% grounded essential beat coverage) are **hypotheses**, not evidence of improvement. The 100-topic live benchmark, reliable population threshold, learning transfer and matched human quality studies remain UNMEASURED/DEFERRED.
- Code2Video, ALGOGEN, OmniManim, LLM2Manim and MINARD are design baselines; none establish unique novelty or an automatic LearnFlow performance claim.
- Source of implementation plan: `PLAN_V3.md` (draft), using this canonical research file as upstream research record.


## 2026-10-08 — Reuse-first source-code policy (user decision)

- **Prioritize reusing project-owned V2 modules and suitable maintained open-source code; adapt/wrap/vendored subsets before writing from scratch.** This must be documented per V3 checkpoint with a pinned upstream SHA, module-level API audit, license/NOTICE, dependency budget, compatibility test and regression proof.
- Verified external GitHub source snapshots: Code2Video `1142d8e14cdc2806df85aedb0fbb5dca474caa0f` (MIT); Manim Community `23ae68f4dd5817d49760b338e14b92757a2369b5` (MIT); ALGOGEN-lab `1bb093c76499135ecf54fc8030219a4e7ee4424c` (**license not declared in inspected root**; study design only, do not copy code absent permission).
- Candidate modules for follow-up inspection: Code2Video `src/scope_refine.py`, `src/agent.py`, `src/eval_AES.py`, `src/eval_TQ.py`; Manim Community's mature math/vector engine as optional typed backend; ALGOGEN VTA/RSL architecture as research reference only.
- **Not authorization to copy wholesale:** generated arbitrary rendering code must not bypass LearnFlow typed contracts, deterministic QA, Core Freeze or artifact provenance. Upstream assets and dependencies require separate license checks.
- `PLAN_V3.md` v3.0.1-draft section 8.3 is the authoritative development rule. V3-00 must produce merge and upstream reuse inventory; implementation remains separate and unauthorised.


## 2026-10-08 — V3-00 Baseline & Merge Gate audit results

- Source main `29fab1d5738ccb060502c8ae82e2e31f00360811`, isolated paid pilot pre-audit `a1e4e8b72f4e63e9cde0ffd4351df9a936900d9a`: 27 commits ahead / 0 behind and 23 changed files. Full inventories and 12 capability reuse decisions in `reports/v3_00_baseline_merge_gate.md` and `reports/v3_00_reuse_inventory.json`.
- Audit classification: KEEP / EXPERIMENTAL / SUPERSEDED / EXCLUDE; **do not fast-forward all pilot changes** because `hermes/bootstrap/config.yaml` switches default to paid GPT-6 Luna and other changes are branch-gated experiments.
- Reuse audit includes Code2Video (MIT, pin `1142d8e`), Manim Community (MIT, pin `23ae68f`) and ALGOGEN-lab (no root license/declared license, **STUDY ONLY / DO NOT COPY**, pin `1bb093c`). Direct code copying was neither attempted nor authorized.
- **Fresh offline CI: PASS**, run https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37725705499 on commit `217bd0575e7e14141fa24fd320efa76edcf391b3`; outputs: `V3_00_BASELINE=PASS commits=27 files=23 capabilities=12`, `CORE_FREEZE=PASS`, `LIVE_V2D_CONTRACT=PASS`, 87 regressions PASS, 14 renderer PASS/5 SKIP. No paid-provider workflow ran.
- **V3-00 audit PASS**; full pilot-to-main merge **NO-GO**; next single task, only after user authorization: **V3-00B — Selective Integration Candidate & Offline Gate**, on a non-main branch; main and frozen Core remain unchanged. V3-01 and later capability code remain unimplemented.


## 2026-10-08 — V3-00E merged and verified

- **PR #33 merged** on explicit user-requested V3-00E approval path. Exact integration merge commit on main: `be19b4819b8c23c19713b6351d384411b29bf29b`; original main was `29fab1d5738ccb060502c8ae82e2e31f00360811`. This merge was from selective integration branch, **not** the paid GPT-6 Luna pilot fast-forward.
- Added an offline regression trigger for pushes to `main`, using the already-proven Core Freeze/V2D/semantic/subtitle/security/renderer test suite. All 11 pre-merge workflow runs at `cac628f9` passed.
- On merge commit `be19b4819b8c23c19713b6351d384411b29bf29b`: all **10/10 GitHub Actions succeeded**; [offline gate 37728464626](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37728464626) recorded `CORE_FREEZE=PASS`, `LIVE_V2D_CONTRACT=PASS`, **82 passed** tests and **14 passed / 5 skipped** renderer tests. [Governed Live push 37728464657](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37728464657) ran contract only and **SKIPPED live-provider-pilot**.
- Default model remains `nvidia/nemotron-3.5-lightning:free`; the paid Luna policy/default was not merged. No `learnflow_v2/**` frozen Core files or the V1 rollback/Core manifest were changed.
- Historical #181 (run `37721597623`, artifact ID `11525814288`) remains an unchanged technical PASS with recorded semantic registry-vs-script mismatch. No paid API or new live render was invoked in this checkpoint.
- Rollback referent is merge commit `be19b4819b8c23c19713b6351d384411b29bf29b` (a future authorized `git revert -m 1`, then rerun CI). **V3-00E PASS**; the next *single* planning task is **V3-01 Benchmark Preregistration**, not started here. Full details in `reports/v3_00e_post_merge_verification.md`.
