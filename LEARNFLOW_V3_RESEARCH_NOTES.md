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
- VisualEDU
- manim-shorts
- 3Blue1Brown / Manim as human-crafted quality reference, not as a claim that current AI systems equal it.

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

## V3-C5 — Advanced Visual Grammar

Status: `OPEN`

Potential additions after evidence:

```text
MORPH
RESIZE
TRACE_PATH
semantic transform
camera choreography
persistent equation transformation
graph deformation
vector projection
geometry construction
```

Important rule:

Do not add advanced primitives merely because they look impressive.

Each primitive must justify:

- pedagogical value;
- deterministic compilation;
- testability;
- fallback behavior;
- repairability.

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

Exact policy remains an open design question.

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

# 17. Questions still open

1. Should `PedagogicalStoryboard` remain one artifact or split into `PedagogyPlan` + `VisualPlan`?
2. Is `Visual Director` best implemented as:
   - one LLM role;
   - deterministic rules + LLM suggestions;
   - retrieved visual-pattern library + LLM selection?
3. How should Hero Scene budget be represented?
4. Which advanced motion primitives have measurable learning value?
5. Should camera choreography be semantic DSL or renderer policy?
6. How do we represent mathematical transformations without arbitrary code?
7. How much of 3Blue1Brown-like quality comes from:
   - planning;
   - representation selection;
   - transitions;
   - typography/layout;
   - motion;
   - narration pacing?
8. Can a curated visual-pattern library give Code2Video-level expressiveness without code generation?
9. Should LearnFlow build domain-specific adapters for:
   - algorithms;
   - math;
   - physical systems?
10. How should VLM critic confidence and outage state affect publish policy?
11. What is the minimum human benchmark needed before claiming "3B1B-like" polish?
12. What is the cost ceiling for a normal video vs hero-quality video?
13. Can advanced animation remain deterministic across renderer versions?
14. How should visual variety be measured without incentivizing unnecessary motion?
15. Which Code2Video features survive when arbitrary Manim is removed?

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
9. Advanced Motion Grammar
10. Artifact Critic
11. ArtifactRefine
12. Domain Trace Adapters

13. Signal-preservation testing
14. Fail-closed QA
15. Benchmark harness
16. Migration / compatibility
17. Cost controls
18. V3 checkpoints
19. V3 Core Gate
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
