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


## 2026-10-08 — V3-01 preregistered Tier-1 benchmark (offline PASS)

- On branch `chatgpt/v3-01-benchmark-preregistration` (base `a06e0b0`), created **one immutable-in-version Tier-1 pilot protocol**: `benchmarks/learnflowbench/v3/preregistered_pilot_v1.json` and `PROTOCOL.md`. Reused the project-owned LearnFlowBench corpus loader and SHA-256 hash; original 100-topic corpus and three V1/V2 ablation fixtures unchanged.
- Frozen corpus SHA-256 `4f0e0fc81dee7580df93a1d912b9485de7e5eb1c9fdda699576b48729bf4ab8f`. Twelve selection IDs: `lfb-006-cs`, `lfb-016-cs`, `lfb-019-math`, `lfb-026-math`, `lfb-046-physics`, `lfb-050-physics`, `lfb-052-biology`, `lfb-064-biology`, `lfb-069-chemistry`, `lfb-078-chemistry`, `lfb-092-history-general`, `lfb-094-history-general`. Two per domain (six domains), 4 easy / 4 medium / 4 hard, selected by prespecified SHA-256 digest with seed `learnflow-v3-01-20261008-stratified-v1`, not video results.
- Binary Search `lfb-005-cs` already used in Action #181 is diagnostic-only and excluded from the confirmatory 12. Model use is *future free-only* `nvidia/nemotron-3.5-lightning:free`, availability **UNVERIFIED**; no silent provider switch, retries, free-to-paid fallback or unapproved call.
- Co-primary scores are blinded human explanation clarity and representation adequacy (1–5), 2 raters minimum, explicit missingness and failure denominators; engineering pilot threshold per metric +0.5 average and 8/12 wins, with hard factual/geometry/security noninferiority. These are **preregistered hypotheses**, not measured performance or statistical evidence. Human studies, V3 generation, paid API and recruitment remain NOT AUTHORIZED.
- Offline CI [#37729383829](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37729383829) verified `V3_BENCHMARK_PREREG=PASS` on 12 topics, **24 pytest PASS**, `LEARNFLOW_BENCH_CONTRACT=PASS`, `CORE_FREEZE=PASS`, zero provider calls. Report: `reports/v3_01_benchmark_preregistration.md`.
- **V3-01: PASS for protocol and governance only.** Next SINGLE checkpoint is **V3-02 Canonical Semantic Contracts**, not started in this branch. Follow reuse-first and no code copying from license-unclear sources.


## 2026-10-08 — V3-02 Canonical Semantic Contracts (offline PASS)

- Built the `learnflow_v3/` typed semantic-contract layer on a branch based **exactly** on PR #34 head `1856ccdd6b6337f654b78ad7da73055dd8780790`; PR #34 remains unmerged, and `main` remains unchanged. This is a **stacked dependency**, not a hidden merge of V3-01.
- Reuse-first audit: V2 `learnflow_v2/concepts/registry.py` and schema (exact `concept_id/canonical_key`, collision checks), `learnflow_v2/scenegraph/validation.py` (frozen node identity), `agent_contracts/lesson.py` (`LessonScript/Storyboard`), `live_evaluation/semantic_consistency.py` (numeric #181 drift) and V2 JSON-safe state validation. No third-party source copied; no frozen Core changes.
- New versioned `VisualTeachingPlan`, `VisualPatternSpec`, `StateLedger`; typed sections/beats/semantic objects, explicit state source, deterministic hash, closed enums and strict `extra=forbid`. The cross-artifact gate rejects unknown/mismatched refs, unverified source IDs, missing ledger beat/object coverage, invalid section order, pixel-directive leakage and numerical 16-vs-24 mismatch. It does not certify natural-language semantics universally, the trace oracle itself or rendered pixel evidence.
- CI [#37730308809](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37730308809) (code SHA `e5acf5534f79548d3598d45dc02776828bb6a16b`) **SUCCESS**: 20 V3 tests, 36 V2 concept/graph tests, 58 agent/semantic tests, `V3_BENCHMARK_PREREG=PASS`, `LEARNFLOW_BENCH_CONTRACT=PASS`, `CORE_FREEZE=PASS`, no paid or free model calls.
- **V3-02 PASS (offline contracts only)**; report `reports/v3_02_canonical_semantic_contracts.md`. Next SINGLE checkpoint: **V3-03 Signal-Preservation Proof**, not implemented here. Full visual proof/rendering remains future work. No `main` merge authorized.


## 2026-10-08 — V3-03 Signal-Preservation Proof (bounded offline PASS)

- Branch `chatgpt/v3-03-signal-preservation-proof` pinned on PR #35 head `d972645e2ea39cb83cac6fb2203aa5f99ec9bbde`, itself derived from open PR #34. Neither dependency merged; `main` remains `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6`. This checkpoint does not merge or implement V3-04.
- Reuse-first: audited V2 `learnflow_v2/repair/artifacts.py` canonical `compute_content_hash`, `ArtifactIndex.add`, `downstream_closure`, V2 `lesson_pipeline/artifacts.py` persistence and V3-02 `validate_semantic_bundle`. **REUSED V2 hash function and V3-02 gate.** Did **not** misuse CP2.13 `ArtifactKind` for V3 artifacts or modify Frozen Core.
- Added `learnflow_v3/signal_preservation.py`: explicit field-level semantic route registry with no catch-all: every encountered V3.0 serialized leaf must be `SEMANTIC_GATED` or `DECLARED_UNCONSUMED` with named future consumer. Unknown fields/policy omissions fail. Proved distinct semantic-gate fingerprint for validated refs vs global audit/source fingerprints for deferred values; both are deterministic and versioned. Includes V2 registry/script/storyboard/SceneGraph hashes and caller-asserted trace-ref set in provenance. Changed objective/beat/trace links must alter dependent gate hash or fail; concept mismatch fails. Mutated state, visual-teaching goal, and expected visible state change update the audit hash but remain marked **deferred** and blocked from render. Forged stale fingerprints are rejected by mutation comparison tests.
- Crucial limit: `SEMANTIC_GATED` means **validated by existing schema/semantic gate**, not proven to affect rendering; no pixel/rendered-frame proof. The method `require_render_consumption()` **always fail-closes** until an actual renderer consumer exists; not yet wired into a V3 renderer because none exists. A caller-marked `verified_trace_refs` is a declaration, not trace-oracle evidence. Nested Pydantic `dict` fields may be mutable despite `frozen=True`; fresh audit rehash detects changes, not automatic cache invalidation.
- GitHub offline run [#37731881901](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37731881901) on code SHA `d9ac97020b83734e3095d36b4619c34e471e2aef`: **39 V3 PASS, 39 V2 artifact/identity PASS, 28 agent/semantic PASS, `V3_BENCHMARK_PREREG=PASS`, `LEARNFLOW_BENCH_CONTRACT=PASS`, `CORE_FREEZE=PASS`**. No model/free API call, no paid spend, no new video.
- Reviewer decision: **V3-03 PASS for offline declared-signal / fingerprint-preservation proof only; rendering and physical signal consumption UNMEASURED**. Report `reports/v3_03_signal_preservation_proof.md`. Exactly one next checkpoint, only when separately requested: **V3-04 Visual Pattern Router**. Preserve reuse-first/license audit and freeze constraints.


## 2026-10-08 — V3-04 Visual Pattern Router (offline PASS)

- New stacked branch `chatgpt/v3-04-visual-pattern-router` from PR #36 head `437766397ea4a170e7d0671f0cfb4885947724a5`, itself on #35/#34. All remain unmerged; `main` pinned at `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6`. No frozen Core, corpus, default model, paid pilot or rollback artifact changes.
- **Reuse-first audit:** V2 `visual_director/gate.py::validate_visual_director_output` (purpose, teaching function, concept/scene coverage), V2 `learnflow_v2/scenegraph/enums.py::LayoutIntent/ScenePurpose/RelationKind`, V2 `learnflow_v2/repair::compute_content_hash`, V3-02 typed `VisualTeachingPlan/VisualPatternSpec/StateLedger` and V3-03 `audit_signal_preservation`. Direct imports and adapters; no third-party code copied. ALGOGEN remains license-blocked, Manim/Code2Video not needed without a renderer.
- Implemented finite, deterministic `learnflow_v3/pattern_router.py`: `WORKED_EXAMPLE_BOARD` (multi-step trace/sequence), `PROCESS_FLOW` (typed processes and graph topology), `EQUATION_GRAPH` (typed equation/static evidence) and `CONCEPT_CARD` (explicit static summary/recap only). Variants require budget and evidence; fallback stays in the same representation. **Branching process graphs do not fall back to linear**; insufficient budget/unknown/unsafe layout/purpose/no trace results in abstention or a hard cross-artifact failure. No all-purpose card collapse.
- `SELECTED_UNRENDERABLE` means semantic variant selected only, **not** a renderer is present. `VisualPatternRoute.render_ready` is always False; `require_renderer()` always fails. Caller cannot bypass the V2 Visual Director gate or V3-03 signal audit. Decision SHA fingerprint includes source audit hash, variant attempts and refusal reasons, but no pixel proofs or quality improvement are claimed.
- CI first version **failed** 1 topology negative test (branched process flattened). Fixed by testing actual directed chain vs branching graph, reran [#37732710523](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37732710523) **SUCCESS**, and public API export retested at [#37732962363](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37732962363) **SUCCESS**: 60 V3 tests, 39 V2 tests, 46 existing Visual Director/semantic tests; `V3_BENCHMARK_PREREG=PASS`, `LEARNFLOW_BENCH_CONTRACT=PASS`, `CORE_FREEZE=PASS`. No provider calls, no video rendered.
- Verdict **V3-04 PASS (bounded semantic routing only)**, still not evidence of actual compatible rendering or pedagogy. Report `reports/v3_04_visual_pattern_router.md`. Exactly one next checkpoint: **V3-05 Binary Search Trace Adapter**; no part of V3-05 implemented now.


## 2026-10-08 — V3-05 Binary Search Trace Adapter (offline PASS)

- Branched `chatgpt/v3-05-binary-search-trace-adapter` from **PR #37 exact head** `609a21217cae9e44a4fcec51dfb801b43a87e5cb`. Open stacked dependencies PR #34/#35/#36/#37 remain unmerged; `main` remains `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6`. Frozen V2 Core, V1 rollback, LearnFlowBench corpus, provider defaults, historical #181 untouched.
- **Reuse-first audit:** searched repository tree and V2 `live_evaluation/semantic_consistency.py`: it only parses/cross-checks explicitly numbered examples (target+array), **not** any `low/high/mid` state transitions or duplicates policy; V2 `learnflow_v2/repair::compute_content_hash` supplies deterministic provenance. Reused Python standard-library `bisect_left` as an **independent oracle**, V3-02 `StateLedger`, V3-03 signal audit and V3-04 routing. No vendor/copy from Code2Video/Manim/ALGOGEN (ALGOGEN source license remains blocked), no new dependencies.
- Implemented `learnflow_v3/binary_search_trace.py`: typed, sorted integral input (max 4096), LEFTMOST among duplicates; step-by-step inclusive bounds `low/high`, floor `mid`, observed value, action, candidate and next bounds; terminal FOUND/NOT_FOUND including empty arrays. Trace `trace_sha256` is checked, but NOT TRUSTED alone: replay verifier recomputes **every** expected transition and independently compares final result with `bisect_left`. Forged steps with a freshly computed matching SHA-256 are still rejected.
- Ledger creation/reverification: adapt to existing V3-02 StateLedger with exact number/identities of teaching beats, pattern source, sequence or pointer object states and versioned hashes; mutations in state properties reject even when trace/ref/hash are unchanged. `certify_and_route_binary_search` verifies trace+ledger before calling V3-04; additionally requires the exact array and target as an **explicit numeric example in script AND storyboard**, and any registry concept label containing such an example must agree. A trace algorithmically correct but about the wrong taught example fails closed (Action #181 recurrence guard).
- Testing: [run #37735632057](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37735632057) initially PASS on typed oracle/ledger/property tests. Strengthened lesson/trace semantic source-binding and reran [#37735803537](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37735803537): **108 V3 / 39 frozen V2 / 46 Visual Director/semantic tests PASS**, prereg/bench/Core Freeze PASS. Tests cover >3,000 small sorted multiset/target combinations plus duplicate, negative, empty, one-item and adversarial mutations of mid/low/high/action/candidate/terminal/beat/source/hash/ledger. Zero model API calls.
- Limits: parser recognizes **explicit** `Binary search for N in [v1, ...]` statements, including empty or one-value arrays, rather than guessing freeform language; unlabeled examples abstain/fail. Direct V3-02/V3-04 APIs still accept caller-declared verified refs, so a later renderer must use **the certified wrapper**, not independently trust an asserted ID. Numerical algorithm proof and typed StateLedger **do not show pixels/animation**; V3-06 remains mandatory.
- **V3-05 offline PASS** with report `reports/v3_05_binary_search_trace_adapter.md`. Exactly one next checkpoint: **V3-06 Stateful Sequence Renderer**, requires explicit user request and upstream renderer license/dependency audit; not started under V3-05.


## 2026-10-08 — V3-06 Stateful Sequence Renderer (first real MP4 / bounded engineering PASS)

- **Dependency:** new `chatgpt/v3-06-stateful-sequence-renderer` based on exact PR #38 head `77790cfb5903014b77300bbc051c6681e2f99476`. PR #34/#35/#36/#37/#38 remain open; `main` remains `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6`. No merge to main or V3-07 implementation.
- **Reuse-first audit:** V2 `app/rendering/canvas.py`, `typography.py`, `ffmpeg.py` and `learnflow_v2/render/backend.py` use Pillow, FFmpeg, font metrics and bounded primitive rendering. Direct imports of `app.rendering` triggered unwanted `pydantic_settings` then `google.genai` due eager package initialization: avoided optional provider dependency by using the **same existing Pillow+FFmpeg stack** with V2 project palette and isolated DejaVu font loading; small V3 specialized adapter only. Upstreams **Manim Community MIT** `23ae68f4dd5817d49760b338e14b92757a2369b5` and **Code2Video MIT** `1142d8e14cdc2806df85aedb0fbb5dca474caa0f` audited but not imported (larger animation/code-generated dependency boundary). **ALGOGEN-lab** `1bb093c76499135ecf54fc8030219a4e7ee4424c` remains license-unverified, study only, no copy.
- **Implementation:** `learnflow_v3/sequence_renderer.py` replays V3-05 certification and exact script/storyboard binding before paint/FFmpeg. Renders stable per-index array positions, interpolated low/high/mid pointers, active window, candidate/found/result. A one-state empty-array MP4 is intentionally terminal-only; never fabricate steps or convert to cards. Output is bounded 16:9 (640–1920×360–1080), ≤16 visible items and ≤960 frames; fail on unreadable numeric labels, unsafe or already-owned/symlink output; atomic no-clobber export using hard link. H.264 decode→per-step expected-frame MAE and decoded semantic-ROI changes are mandatory; bypass flag is rejected. Beat text captions are used; no synthesized voice/audio.
- **Evidence:** [GitHub run #37737754838](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37737754838) code `51f55c6c60b7e0529f1b038f98389b5ab1723800` **SUCCESS**: 123 V3 tests, 39 V2, 46 Visual Director/semantic, V3-01 prereg PASS, LearnFlowBench PASS, Core Freeze PASS. 5 actual MP4 and PNG posters plus machine-readable `v3_06_render_evidence.json` uploaded as [artifact 11532153065](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37737754838/artifacts/11532153065). Case durations 3.11s duplicate/missing, 1.56s singleton, 0.78s empty, 2.33s boundary; decoded anchor MAE max 0.81 and min nonempty step delta 1.64 on valid transitions; all files cross-checked by SHA-256. Measured render wall times ~0.23–0.94s per case on CI worker (not general throughput benchmarks).
- **History:** CI #37737029256 and #37737189500 initially failed on eager V2 import dependencies, **not** frame correctness; isolated V3 drawing adapter, then CI passed. All 5 cases rebuilt after strict aspect/label geometry checks. Third-party code copy: **none**. Model API calls: **zero**.
- **Limits/decision:** **V3-06 PASS for actual certified offline MP4/frame-state proof only**; no audio narration, no swept-frame temporal collision solver, no external human pedagogy study or ≥98% reliability claim. Video remains small pilot, visually inspect. Report `reports/v3_06_stateful_sequence_renderer.md`. One next checkpoint **V3-07 Code + Process Renderers** only with separate user instruction; no premature V3-07 code.


## 2026-10-08 — V3-07: actual Code/Process MP4 with #000000 + real Computer Modern

- **Dependency:** `chatgpt/v3-07-code-process-blackboard` derived from PR #39 head `1f0d01634ae5c64e6a1f054b6bf6ddb3a5c1c2d2`; PR #34→#35→#36→#37→#38→#39 remain unmerged. Main stays `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6`. Scope V3-07 only, including visual-style feedback applying to V3-06, without touching frozen `learnflow_v2/**`, benchmark corpus, V1 rollback, historical #181 or model defaults.
- **User aesthetic input:** black `#000000` scene, CMU Serif title/math annotations and CMU Typewriter Text code, sparse white/grey marks, restrained yellow/cyan/green; no 3Blue1Brown assets or source copied. Install official Ubuntu `fonts-cmu` via CI OS package, **do not vendor/share font files**. `blackboard_style.cmu_font` fail-closes when fontconfig returns any non-CMU family. V3-06's earlier slate/DejaVu video palette now produces black/Computer Modern outputs on this new branch; prior golden video remains immutable historical evidence.
- **Reuse audit:** prior V2 `app/rendering/process_diagram.py` static progressive card frames & `canvas.py` deep-slate palette; reusable project Pillow, FFmpeg, layout/SceneGraph. V3-06 decoded frame/MP4 helpers reused; V2 `compute_content_hash` source binding. `ManimCommunity/manim` MIT @ `23ae68f4dd5817d49760b338e14b92757a2369b5` and `showlab/Code2Video` MIT @ `1142d8e14cdc2806df85aedb0fbb5dca474caa0f` audited but **not imported/copied**; costly/unbounded generated-code path not necessary. `ALGOGEN-lab` @ `1bb093c76499135ecf54fc8030219a4e7ee4424c` no root license verified => STUDY ONLY.
- **CODE:** source code has finite AST allowlist (single integer assignment with literals/variables, + - * //), typed deterministic variables for each code-line ID; code node content must exactly match Graph's SHA-bound line program. Any function, loop, external call, unverified state or unknown expression fails; no Python `eval`, `exec`, `compile` or LLM code runtime. Visible line highlight travels *within beat*, variable values persist; renderer uses CMU typewriter.
- **PROCESS:** typed V2 `SceneGraph`, FLOW/SEQUENCE_BEFORE edges, bounded DAG layered layout, stable node positions, edge ID and path replay; prevents branch flattening even when only one path is highlighted. A yellow tracer animates along certified graph edge inside beat. Cyclic/unreachable path or mismatched source SHA fail. Neither renderer silently falls back to concept cards.
- **Evidence:** First offline CI #37739664301 failed negative-test fixture provenance (guard correctly prevented mutated source before AST check), fixed to coherently rebind graph; later CI #37740233140 demonstrated 145 V3 / 39 V2 / 46 semantic PASS and 2 encoded clips, but artifact upload YAML had escaping bug. Added intra-beat decoded motion criterion; CI #37740790915 **SUCCESS** (code HEAD `75b28e5c4ed7b344f252c0e1f99c7ae0134de747`): 146 V3, 39 V2, 46 semantic tests, V3 prereg, LearnFlowBench, Core Freeze PASS. Uploaded [2 real H.264 MP4, 2 PNG posters, JSON QA artifact #11533433759](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37740790915/artifacts/11533433759); actual archive inspected, SHA-256 both MP4 matched. Code 56 frames 3.11s / 60,738 B / max decode MAE 0.191 / min inter-step delta 2.740 / intra-beat deltas min 0.606 / CPU wall 1.25s; Process 42 frames 2.33s / 64,850 B / max decode MAE 0.204 / min inter-step 2.173 / intra-beat min 0.450 / CPU wall 0.90s.
- **Limit/verdict:** V3-07 engineering PASS for *these bounded video families and visual treatment*; no global Code2Video general Python execution support, no voiced narration, no swept-time geometry proof on arbitrary graphs, no human preference/learning outcome evaluation. Crucially these are **standalone typed V3-07 adapters** anchored in V2 SceneGraph, not yet first-class V3-02 VisualPatternSpec/lesson-wide registry integration. Do not promote to production or count general-code topic success until canonical integration and negative QA are separately defined. Full report `reports/v3_07_code_process_renderers.md`; no V3-08 implementation.


## 2026-10-08 — V3-08 math blackboard renderer implementation (verification pending)

- Branched `chatgpt/v3-08-math-blackboard-renderers` from PR #40 exact head `960ac1d77e98520d91f7fc03be44a6967c5206cd`; PR #34→#40 remain dependency stack. No merge to main, no frozen V2 Core, model defaults, benchmark corpus, historical #181 or V1 rollback edits.
- Reuse-first: V2 SceneGraph CHART/EQUATION and directed math relations; deterministic V2 source hash; V3-06 Pillow/FFmpeg, anchor decode/MAE; V3-07 OS Computer Modern / #000 blackboard styling. Prior upstream audit Manim MIT/Code2Video MIT kept pinned, no vendor code; ALGOGEN license unverified, excluded; no new high-cost dependency.
- New typed polynomial FunctionGraph verifies all integer points, strict ordered source domain, SHA-matching CHART formula and analytic endpoint/vertex extrema. New EquationDerivation verifies exact polynomial equivalence of each expression via an independent restricted AST data interpreter (no eval/exec; reject division, function calls, high degree, changed constants, forged graph edge identity). Stable semantic IDs, bounded plot/row geometry, no concept card collapse.
- Script `scripts/verify_v3_math_patterns.py`, tests `tests/v3/test_math_patterns.py`, CI `.github/workflows/v3-math-patterns.yml` must prove two actual H.264 MP4s with decoded anchor, between-step and within-beat pixel checks, posters and SHA JSON, original prereg/LearnFlowBench/Core Freeze gates.
- Gate **BOUNDED ENGINEERING PASS at code SHA ff6c133; final documentation commit pending checks**. No automatic publication or production-quality/3B1B claims, no math integration as first-class canonical V3-02/V3-04 lesson-wide family yet. Next after verified PASS and separate authorization: V3-09.

- **V3-08 source-head acceptance 2026-10-08:** [math CI #37745752422](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37745752422) 7/7 overall workflows SUCCESS; 170 V3, 39 V2, 46 semantic tests, prereg/Bench/Core Freeze PASS. The two [H264 MP4 goldens + PNG + proof JSON](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37745752422/artifacts/11535822025) were downloaded/decoded and cross-checked SHA; graph 70 frames, max MAE .212, min motion .144; derivation 42 frames, max MAE .093, min motion .248. Computer Modern conventional display refined after poster inspection: polynomial f(x)=x²−4, expressions no Python asterisk/power syntax. **BOUNDED ENGINEERING PASS** at code `ff6c1339e2e65f92a84365ae2d85a98b68781b74`, NOT production/human understanding PASS. Final report-only commit needs fresh HEAD CI. No merge or V3-09.


## 2026-10-08 — V3-09 Source-Grounded Pedagogy + Hero Planner (bounded offline engineering PASS)

- Stacked branch `chatgpt/v3-09-pedagogy-hero-planning` from PR #41 exact head `8d2dffccd572fdedb69d0d600cae25ce159a4585`; #34–#41 remain dependencies, `main` and frozen V2 intact. No provider/free/paid LLM, no model tokens, no unapproved human trials, no V3-10 implementation.
- Reuse-first V2/Hermes `pedagogy_agent.gate.validate_pedagogy_plan`, `script_agent.gate.validate_lesson_script`, Fact Verification report/replay, PedagogyPlan, LessonScript, ResearchPack/EvidenceGraph and canonical ConceptRegistry; V3-02 VisualTeachingPlan and V2 `compute_content_hash`. Code2Video pedagogical/ScopeRefine architecture considered in established pinned upstream audit; no new source copied. Implemented only the missing typed deterministic continuity and budget compiler.
- `learnflow_v3/pedagogy_planner.py` validates exact learner profile and duration, all approved claims, complete objective→script→V3 beat→assessment mapping, section before/after learner mental state fields, declared-only prerequisite DAG, explicit misconception correction text in the bound narration and exact canonical concept IDs. Unverifiable/misaligned edges, claims, objectives, corrections, script reorder, section drift, stale-rehashed output fail closed.
- Deterministic 1–3 proposed Hero TeachingMoments require visual section hero candidacy, essential dynamic beat, approved claims and non-card family; tie-breaking by prior beat order. Unit budget fixed across both arms, capped by per-section complexity budget; no invented cost/time claim. Fixture 2 sections/2 objectives, 1 correction, 1 hero: uniform 5/5 versus hero 8/2 with exact total 10, transfer 3; when no capacity or eligible beat, faithful uniform fallback. Hard-typed human outcomes `UNMEASURED`, `render_ready=False`.
- First offline CI failed nested Pydantic hash serialization and computed-field mutation test fixture; both corrected. [Passing CI #37747346591](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37747346591) on code `18c551eb74173c42c898cf2e20f117974dab8dbf`: 129 V3 / 40 Hermes / 39 V2 tests PASS; prereg protocol / LearnFlowBench / Core Freeze PASS. JSON artifact [#11536880070](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37747346591/artifacts/11536880070); deterministic SHA and source replay. Report `reports/v3_09_pedagogy_hero_planning.md`. Final docs/PR-head CI to be separately checked.
- **Bounded engineering PASS only.** Explicit correction substring checks preserve syntactic support but do not prove explanation efficacy or natural-language entailment. No MP4, no matched audio/render experimental comparison, no human preference/comprehension pilot, no claim of +10 pp. Exactly one next authorized checkpoint is V3-10 Beat-Visual Grounding.


## 2026-10-08 — V3-10 Beat-Visual Grounding (bounded engineering PASS, docs CI pending)

- **Dependency:** new stacked branch chatgpt/v3-10-beat-visual-grounding at PR #42 exact head dbfaf278fb1f35960f6df57c4afe5e7b90d90bbc; main pinned a06e0b0b5f35e9147b4081da7ed7f7934affe0c6, V2 Core/100-topic benchmark/V1 rollback/provider defaults untouched. No merges or model calls.
- **Reuse-first and innovation boundary:** project V2 script/storyboard/ConceptRegistry/source hash, V3-05 independently replayed bisect_left trace and exact StateLedger, V3-06 Pillow/FFmpeg true-black Computer Modern renderer/anchor decode, V3-09 prior source/hero planning study. No Manim/Code2Video source copied (previous pinned MIT reuse audit); ALGOGEN license unresolved and excluded. Added specialized V3-10 only; no duplicated semantic planning agent.
- **Implementation:** learnflow_v3/beat_grounding.py typed BeatGroundingManifest strictly recomputed from trusted trace/ledger/script/storyboard pattern, with exact claim, step, object identities, synthetic frame-time windows and SHA-bound provenance; BeatGroundingEvidence demands actual H264 byte SHA/codec/count and decoded 3-anchor pixel-frame matching in algorithmic-state ROI. Each dynamic beat needs within-window visible array/pointer change, not title motion. Static terminal exception only if source is terminal, with previous→terminal visible result except for the sole empty-array clip. No silent CONCEPT_CARD. Negative mutation suite includes shifted cue, swapped correct-format video, frozen black video, forged SHA, forged ids and source/script drift.
- **CI first valid implementation [#37748958808](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37748958808) SUCCESS:** 146 V3 / 39 V2 / 86 Hermes tests, prereg/Bench/Core Freeze PASS. Three real H264 MP4s and machine-readable JSON in [artifact 11537500473](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37748958808/artifacts/11537500473). Downloaded actual archive and checked MP4 hash vs JSON: duplicate 77,100 bytes, 4 beats/3 dynamic, max decoded semantic anchor MAE 2.156; missing 70,228 bytes, 4 beats/3 dynamic, max 1.682; empty 25,190 bytes, 1 terminal/0 dynamic, max 0.133. Dynamic observed=6/6 within these bounded example clips; human/audio outcomes UNMEASURED. Script: scripts/verify_v3_beat_grounding.py.
- **Scientific limit:** samples are renderer-synthetic beat windows, **not** real speech/word timing. Pixel-reference oracle is the project-owned certified renderer, not independent vision understanding; V3-09 grounded Hero output not automatically wired to live V3-06 production. Cannot assert general C12 >90% annotated corpus, visual pedagogy learning gain or 3Blue1Brown parity. V3-11 generic swept temporal geometry remains separate. Gate **BOUNDED V3-10 ENGINEERING PASS** subject to final documentation commit CI.


## 2026-10-08 — V3-11 Temporal Geometry (bounded engineering PASS; docs CI pending)

- Branch chatgpt/v3-11-temporal-geometry forked at exact PR #43 HEAD 5f7314584248a6b95d447a71b616a49577593502. Main still a06e0b0b5f35e9147b4081da7ed7f7934affe0c6. Frozen V2 Core/evidence, 100-topic corpus, historical #181, model/provider/paid defaults, V1 rollback and app configs unchanged. No merge or V3-12 development.
- Reuse-first: immutable V2 Rect intersection + compute_content_hash, V3-06 Pillow/FFmpeg and black/CMU installed fonts, V3-10 H264 frame-count probe. Prior pinned MIT Manim Community/Code2Video research evaluated without importing/copied source; ALGOGEN license unresolved and source excluded. No new external dependency or model calls.
- learnflow_v3/temporal_geometry.py defines strict renderer-owned time geometry. Pairwise continuous analytic swept AABB intersects iff all four affine inequalities simultaneously overlap in the SAME real time interval; catches two small objects whose endpoints at frames 23 and 24 do not overlap but intersect at frame 23.5. Shared-window SMOOTHSTEP can use common monotone parametric interpolation; unmatched easing/segment ranges use conservative adaptive swept envelopes and FAIL when unsafe/uncertain. Global frame samples, safe-edge and subtitle reservations, role/text boxes, maximal font/min box text reflow, x/y/size limits and motion budgets all fail closed. Typed source-hash certificate requires recomputation; 0 unsafe auto-fallback. Geometry input is controlled by renderer, not semantic LLM geometry.
- learnflow_v3/temporal_demo_renderer.py encodes and decodes a real local 49-frame H264 MP4. Fixed final-frame seek ambiguity from first CI by decoding exact ordinal frames, and checks localized per-object pixel ROIs to catch rehashed source drift even if full-frame MAE is deceptively low. Negative tests cover invalid keyframes, NaN, two trajectories crossing between integer frames, nonlinear overlap, subtitle intrusion, caption leaving band, intermediate clipping, text morph shrink, long-label reflow, excessive motion, stale SHA, forged render metadata, corrupt MP4, overwrite. Actual demo is illustrative layout rectangles and caption, NOT a LearnFlow finished lesson.
- First test CI #37750641305 failed ordinal decoding and test fixture gate precedence; fixed; further #37750906333 caught a mutated-video mismatch via **stronger object-specific pixel error** than expected, test updated to include that correct failure. **Latest passing implementation [#37751060381](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37751060381) on code cd65c8765205a09c2b3b86451762514918ca4332: 163 V3, 39 frozen V2, 86 Hermes PASS; prereg/Bench/Core Freeze PASS**. Golden 640×360 @12fps, 49 frames/24,887 bytes H264; 3 analytic pair segments, 3 conservative subdivisions, 100 font-fit measurements, 0 critical overlaps/clips/overflows/intrusions, max anchor MAE 0.238. Downloaded artifact [#11537957182](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37751060381/artifacts/11537957182), verified SHA from JSON and ffprobe codec 49 frames.
- **Bounded V3-11 engineering PASS, no production guarantee.** Geometric proof only for typed AABB paths, linear/shared easing, conservative adaptive fallback, one intentionally bounded MP4. V3-06 Binary Search / V3-07 Code+Process / V3-08 Math are **NOT integrated** into full time-global layout proof; no scene transition optimizer, independent perceptual VLM, real audio/speech cue alignment or human learning study. No 3Blue1Brown-level visual quality claim. Documentation reports/v3_11_temporal_geometry.md; report-only PR-head CI separately mandatory.
- Exactly one separately authorized future checkpoint: V3-12 Fail-Closed QA and Publication.


## 2026-10-08 — V3-12 Fail-Closed QA and Publication (bounded engineering PASS)

- Stacked PR candidate branch chatgpt/v3-12-fail-closed-publication starts at PR #44 exact SHA 3877f2a3ecf0bbe4ee317726067ac02bd09f3a0c; main remains frozen a06e0b0b5f35e9147b4081da7ed7f7934affe0c6. Only V3 files/CI/report/PLAN/Research Notes touched. No merge, no production publication or API/LLM calls.
- Audited existing V2 app/pipeline/quality_gate.py media ffprobe contract, learnflow_v2/qa/schema.py and evaluation.py issue semantics, agent_aware_qa/models.py unresolved blockers. Reused existing V3-10 verified_binary_beat_video and V3-11 verify_temporal_render with original source, actual MP4, decoded frame and SHA provenance. No duplication of CV/media renderer, no new skills/providers, no source copied from Manim/Code2Video; ALGOGEN remains study-only without license.
- Implemented new learnflow_v3/publication_gate.py. Frozen typed PublicationPolicy with require_verified_critic=True, dry_run_only=True, enable_publication=False, allow_unverified_deterministic_only=False, retry_llm=False. Raw critic outcome PASS_UNVERIFIED is CRITIC_UNAVAILABLE; CRITIC_PASS cannot be asserted until V3-13 trusted proof exists. Reviewer status is separate DETERMINISTIC_PASS/FAIL/QA_ERROR. Review includes all mandatory gates and unique source-bound proof hashes, actual MP4 SHA, hash-chained stage transitions, checksum, complete blocked reasons. Only bounded source-replayed renderer proof is PASS; full lesson geometry, scene coverage, factual/registry cross-scene, subtitle/audio, critic, authorization stay UNVERIFIED. Every result is PUBLISH_BLOCKED; publish function rejects; no I/O publication side effect, no silent policy bypass.
- Adversarial tests deliberately tamper wrong beat/claim, unsupported pattern, unknown concept ID, partial scene, missing/altered MP4, stale render cache, altered geometry keyframe, forged user publish flags, critic unavailable/fail/error/fake PASS, internal verifier runtime exception, rehashed forged decision/lifecycle. Passing component review cannot become full video release approval.
- Implementation SHA e8b0dc6b92d186bd9c225833bf4ac68be9707ff0 verified by [GitHub Action #37752568906](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37752568906): **185 V3, 39 frozen V2, 86 Hermes PASS**, prereg/Bench/Core Freeze PASS; [artifact #11537634901](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37752568906/artifacts/11537634901) includes 2 real H264 videos and machine-readable five-case statuses. 5/5 cases correctly BLOCKED despite 4 having bounded renderer proof and 1 stale artifact having deterministic failure. No measurable release quality, real lesson coverage, speech, VLM critic or human learning result is asserted.
- Limit: the tested zero-bypass matrix is narrow, not an authenticated deployment or user approval protocol. Actual critic status CRITIC_PASS is unreachable in V3-12 by design, and actual full lesson promotion remains unsupported until future stages. Publication always disabled; this is not proof that an arbitrary lesson will pass production. Report reports/v3_12_fail_closed_qa_publication.md. Documentation-only final HEAD CI needs separate verification.
- Next separately authorized single checkpoint: V3-13 Artifact Critic.


## 2026-10-08 — V3-13 Artifact Critic (bounded typed/offline preflight)

- Branch chatgpt/v3-13-artifact-critic forked from PR #45 exact HEAD 30bec3500f693f31b2fa76c216221dffc14b093d; main still a06e0b0b5f35e9147b4081da7ed7f7934affe0c6. No main/V2 Core/bench/historical live CI changes, no Merge or provider call.
- Reuse first: learnflow_v2/videoqa schema categories + agent_aware_qa repair owner conventions; V3-10 source oracle and decoded beat proof; V3-11 verify_temporal_render, exact ordinal H264 frame decoder; V3-12 source-replayed fail-closed publication gate. No new Manim/Code2Video/ALGOGEN source copied, no new runtime provider.
- learnflow_v3/artifact_critic.py provides typed immutable ArtifactReviewRequest and PropostedCriticResponse scoped to sampled actual decoded RGB SHA/time and original source+MP4, bounded at most eight samples/issues and one reviewer call, exact legal object/beat/claim references. Strict ArtifactIssue has time window, evidence frames and matching hashes, category, severity, finite confidence, fixed repair_route into Research, Script, Pedagogy, Visual Director or Core; no freeform executable code or renderer coordinates permitted. Binary/geometry builders first re-run real V3-10/V3-11 certification, then sample actual MP4; run_video_artifact_critic passes actual decoded PIL RGB frames only after recomputing video+frame SHA to avoid stale video/rehashed reviewer source. Explicit CRITIC_UNAVAILABLE/CRITIC_REJECTED/CRITIC_REVIEW_REQUIRED/CRITIC_NO_ISSUES_UNVERIFIED states; no trusted CRITIC_PASS, no auto-patch or publication. Provider timeout is unavailable, malformed issue rejected. Original V3-12 release remains blocked.
- Tests/v3/test_artifact_critic.py: actual two MP4 fixtures, hash/tag/time continuity, injected reviewer receives actual sampled images; image changed after request cannot invoke reviewer; foreign SHA/object/beat/claim, incomplete cue, non-finite/below-threshold confidence, wrong time/owner, duplicate/out of budget, code/geometry injection, exception/timeout, unavailable, model no-issues/false pass, publication still blocked, stale or rehashed issue and requested review. scripts/verify_v3_artifact_critic.py records two real H264, 5 fake reviewer cases, and source-bound decoded frame request JSON.
- Initial [CI #37754448715](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37754448715) **210 V3/39 V2/86 Hermes PASS**; V3 prereg, LearnFlowBench, Core Freeze PASS. Two genuine binary/geometry MP4s retained in artifact. Later added pixel-bearing reviewer adapter and tests; exact final HEAD CI must be verified. No actual external VLM calls/usage cost.
- Label origin AUTHOR_SEEDED_SYNTHETIC only; evaluation helper computes precision/recall on seeded fixtures, **not** a human-labeled real critic benchmark. Research C6 target +10 percentage points incremental recall vs V2 is NOT ESTABLISHED, false-positive rate on genuine human labels and learning outcomes UNMEASURED. Human annotation protocol/provider integration and real VLM evaluation remain open scientific requirements. No production CI claim, no automatic approval or degraded publish bypass. Report reports/v3_13_artifact_critic.md.
- One next separately authorized checkpoint: V3-14 ArtifactRefine (typed local repair) may proceed as engineering only; cannot claim a validated critic or lesson-wide quality improvement until the V3-13 human/VLM gate is met.


## 2026-10-08 — V3-14 ArtifactRefine (source-only local restoration, bounded engineering PASS)

- Stacked branch chatgpt/v3-14-artifact-refine inherits exact PR #46 head 0d62803960c7c7cdc937997fe919dd79fa532b62. Frozen V2 main remains a06e0b0b5f35e9147b4081da7ed7f7934affe0c6, no merge/provider/config/V2 Core/bench changes.
- Reuse-first: frozen V2 repair content hash/invalidation concepts, V3-11 TemporalLayoutPlan and real source/decoded H264 QA, V3-12 publication fail-closed, V3-13 owning-layer issue categories only. No upstream code copied, new APIs, LLM reviewer, external resources or Python generated by model.
- New learnflow_v3/artifact_refine.py typed LocalRepairIntent can only restore one exact SOURCE-CERTIFIED named track from prior good snapshot, with expected SHA hashes for base/candidate/bad track and source-controlled seeded label. Original baseline certificate AND real MP4 decoded pixel proof replayed before any changes; global semantic/layout identity, per-track ordered IDs, strict one changed track, category-specific real deterministic QA error, untouched hashes, no-op and stale hashes all checked. Actual restored plan hash MUST exactly equal good canonical plan, dependent temporal certificate, all H264/decoded frame QA and V3-12 publication review invalidated, actual full H264 clip encoded again and independently rechecked. Original MP4 preserved and no-clobber output; failures get ROLLBACK_BLOCKED and never release. No critic/user raw geometry/code or unverified source. Nonlocal fact/script/pedagogy/visual issues only defer to owner.
- New tests/v3/test_artifact_refine.py and scripts/verify_v3_artifact_refine.py: author-seeded five corrupted tracks (font overflow, subtitle intrusion, frame clipping, motion overload, occlusion) repaired 5/5 by exact prior-source restoration. Each output real 49-frame H264, 3/4 object tracks unchanged, source hash fixed. Negative checks cover one-plus extra edited track, source_ref mutation, no-op, stale hash, wrong defect cause, edited original MP4, preexisting output/original overwrite, renderer crash rollback, forged release/result audit, unsafe issue router.
- [Initial workflow CI #37755768974](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37755768974): 228 V3, 39 frozen V2, 86 Hermes tests PASS; prereg/Bench/Core Freeze PASS; 6 real MP4s (1 original + 5 repaired). Artifact [#11539304933](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37755768974/artifacts/11539304933) includes video and JSON structured evidence. Documentation-only final HEAD CI must be checked before closing the CP. Report reports/v3_14_artifact_refine.md.
- Critical NO-CLAIM: 5/5 synthetic restoration is NOT V3 C7 ≥70% real repair without full scene regeneration, since every fix fully re-encodes 49 frames; actual critic-generated issue recovery, real human labels, baseline vs full regenerate runtime/cost and human instructional gain NOT MEASURED. V3-13 full scientist gate remains open. No production release permission.
- Next one separately approved checkpoint V3-15 Pattern Expansion. No automatic family expansion without measured demand / true new dynamic golden clips.


## 2026-10-08 — V3-15 Pattern Expansion (single demand-gated cyclic family)

- Stacked PR #48, branch chatgpt/v3-15-pattern-expansion-state-machine forked from exact PR #47 head f34ad2fdf342cb7e0a057e788517905aec843c6c; frozen V2 main a06e0b0b5f35e9147b4081da7ed7f7934affe0c6 remains unchanged. New source, tests, script, CI, report and only canonical PLAN/Notes edits; no merges, providers or paid API.
- Reuse first: verify_v3_benchmark_protocol.validate() plus corpus_sha256 fixed source, frozen 12 selected topic IDs; V3-07 PROCESS_FLOW is acyclic DAG and correctly rejects cycles; new STATE_MACHINE candidate represents cyclic retries, mutually exclusive guarded branches and exact event-trigger replay, not a reskinned card. Existing blackboard_style fonts/colors, SequenceRenderProfile, V2 content hash and V3-11 exact H264 decoder and V3-06 pixel MAE reused; no upstream/ALGOGEN source copied.
- Frozen demand audit on 12-topic prereg: exactly 2 **AUTHOR_CURATED_STATE_MACHINE_CANDIDATE** proxies, lfb-006-cs HTTP request lifecycle, lfb-016-cs distributed transactions. Other 10 NO_NEW_FAMILY_EVIDENCE_ABSTAIN for this new family, not certified general ineligibility. No topic ID substitution, frozen corpus/protocol edits, real user demand/human benefit claim.
- New learnflow_v3/state_machine_renderer.py: typed finite nodes, edge ID/source/target/trigger, beat ID and exact path, terminal and reachability/branch-cycle constraints, stable ordered state ID center positions. Draw true black, CMU serif, actual edge-to-edge moving token and active highlighted state. Render to temp H264, verify actual codec/size/count + time-sampled graphic ROI decoded frames including in-beat motion, then atomic no-overwrite hardlink final MP4 and cleanup. Real 640×360 12fps goldens: 70 frames HTTP retry and 50 frames distributed transaction retry/commit. Source query, frozen topic and video SHA always recomputed; no arbitrary LLM code or caller coordinates, no CONCEPT_CARD fallback. New scripts/verify_v3_pattern_coverage.py and tests/v3/test_pattern_coverage.py validate positive/negative cycle and branch replay, unknown/ineligible topic, stale source or forged MP4/derived pixels, illegal terminal, weak fallback.
- Initial [CI #37757251092](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37757251092) caught 1 negative test mistake: changed unused ABORT terminal instead of active COMMIT, causing 1 FAIL/242 PASS; corrected test target without weakening engine. [Corrected implementation CI #37757306255](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37757306255) **243 V3 / 39 V2 / 86 Hermes PASS**, prereg/Bench/Core Freeze PASS. Two actual H264 verified, artifacts #11540916348 include MP4/JSON. Independently downloaded both, confirmed H264 frame counts and opened sampled screenshots. Visual audit caught topmost state node/header rule overlap despite decoded pixel QA; fixed renderer-owned circular vertical center/radius and added 2 clearance regression tests. Need final exact HEAD CI to verify entire stack after all edits.
- Status BOUNDED OFFLINE NEW PATTERN CANDIDATE, **NOT** integrated V3-04 canonical representation/router; no real full lesson or synchronized narration, no human/factual annotations, no automatic 12-topic utilization success. C5 70% real specialized usage and low card-collapse, correct 3B1B quality and user learning remain UNMEASURED; experiment future V3-16. Publication blocked; V3-13 actual VLM/human annotation and V3-14 incremental render efficacy remain research NO-GOs.
- Next one explicitly authorized checkpoint is V3-16 Pilot/Ablation: prepare secure manifest/blinded rater protocol; do not start participant study or API spend unless user specifically approves such run.

- **Final layout-corrected code HEAD evidence:** **Verified on layout-corrected code HEAD de9abf7f35b94a7eaae6a4c12cece0b6a34aaed7:** [GitHub Actions V3-15 #37757946039](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37757946039) and 13 ancestor checks all success (**14/14 on that exact code HEAD**), **245 V3 / 39 frozen V2 / 86 Hermes PASS**, V3_BENCHMARK_PREREG=PASS (12 frozen/6 domains), LEARNFLOW_BENCH_CONTRACT=PASS, CORE_FREEZE=PASS. Corrected actual H264 goldens: HTTP 70 frames / 82,462 bytes with min state MAE 2.328, min within beat 0.150; transactions 50 frames / 61,216 bytes with min state MAE 1.942, min within beat 0.170. [Artifact #11541086868](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37757946039/artifacts/11541086868) includes both MP4 and exact JSON. Independently downloaded and checked both codecs/resolutions/frame counts/byte SHA against JSON, and visually inspected corrected frame confirming node/header no longer overlap. Documentation commit builds on this exact code; recheck all V3 workflows on final docs HEAD and retain output. A stand-alone correct MP4 is still not a complete real pilot or production renderer selection.


## 2026-10-08 — V3-16 Human Pilot/Ablation manifest (offline engineering only)

- Stacked branch chatgpt/v3-16-evaluation-manifest forks PR #48 exact HEAD 7bfd72039588e11629f395272ae028b10b48dc6f; V2 frozen main stays a06e0b0b5f35e9147b4081da7ed7f7934affe0c6. No merges, uploads to production, LLM calls, paid requests or actual human participants.
- Reuse-first: frozen protocol benchmarks/learnflowbench/v3/preregistered_pilot_v1.json **state FROZEN_PROTOCOL_UNEXECUTED**, source sha 4f0e0fc81dee7580df93a1d912b9485de7e5eb1c9fdda699576b48729bf4ab8f, exact 12 topic IDs (2 per 6 domains, 4 per difficulty), scripts/verify_v3_benchmark_protocol.validate, learnflow_bench corpus_sha256 and V2 content hash. No protocol/corpus or frozen baseline edits. The human/paid/publish/live flags are all false, no running unapproved experiment.
- New learnflow_v3/evaluation_pilot.py: typed public PilotManifest with 24 anonymous A/B video slots and NULL paths, checksum of full unchanged protocol, no V2/V3 identity in public packet, 10 E1–E10 ablation rows NOT_RUN, no arbitrary "PASS", hidden in-memory SHA parity assignment. Protocol's deterministic parity is public -> pseudoblinding requires reviewer isolation/metadata review for real run. GenerationAttempt exactly one per locked topic/system, state NOT_RUN/FAILED/VALID_VIDEO and origin AUTHOR_SEEDED_SYNTHETIC for simulated only; currently any real human/provider records BLOCK. BlindedRating exact 5 ordinal scores 1–5, two independent IDs, third adjudicator if primary disagreement >=2, raw scoring preserved. No orphan/missing, invalid attempted video floor 1, truly unrun prevents analysis. Paired 12 topics and 10,000 fixed-seed bootstrap on topics, not clip/rater pseudo-replication; both mean >=0.5 and each wins >=8 thresholds reported ONLY for synthetic rehearsal. Cost/wall time unmeasured None (not $0); hard safety and actual human outcomes NOT MEASURED. Publication always BLOCKED.
- Script scripts/verify_v3_evaluation_manifest.py generates (1) public 12-slot manifest JSON no identity key, (2) blank 24-row blind reviewer sheet CSV, (3) AUTHOR_SEEDED_SYNTHETIC JSON containing exactly 24 simulated attempts (2 simulated failures), 2-rater/third adjudication data, raw paired effects, synthetic bootstrap CIs and explicit no-actual-MP4/no-human markers. No actual videos are passed off as observed, fake sample SHA placeholders labeled NOT_A_REAL_VIDEO. Machine-readable tests tests/v3/test_evaluation_manifest.py cover frozen topic/identity/permission tampering, omission/survivorship bias, invalid/unrun conflation, missing cost/duration, score coercion, duplicate/third adjudication, forged release and rehearshal reproducibility. GitHub CI .github/workflows/v3-evaluation-manifest.yml includes ancestors/V2/Hermes/prereg/Bench/Core Freeze and fixture output. Report reports/v3_16_evaluation_manifest.md.
- Initial CI hit schema error because anonymous_slots typed Literal tuple incorrectly instead of tuple[Literal["A"],Literal["B"]], fixed. Second run exposed a test expected a later unrun error but implementation correctly blocks earlier at PILOT_UNEXECUTED_CANNOT_BE_ANALYZED, fixed assertion. No weakening fail-closed. Final exact-head CI results and artifact must be verified and recorded.
- No actual V2/V3 paired real 12-topic videos, independent expert/domain human raters, blinding or real cost measurements, human visual quality gain, actual external participant recruitment, empirical C5,C6,C7 gates, or release permission. Scientific V3-16 quality PASS is explicitly OPEN, not inferred from successful synthetic statistics. No live human participants or API spend unless authorized separately.
- Next separately requested CP: V3-17 Release Candidate and Rollback authorization gate as a blocked/rehearsal-only engineering exercise until real human and provider evaluations are approved and completed.


## 2026-10-08 — V3-17 Release Candidate & Rollback (offline NO-GO audit)

- Branch \`chatgpt/v3-17-release-rollback-gate\` inherited exact PR #49 HEAD \`0479d6a4c7c99b447d6bcf03b9f938042623e380\`. Historical freeze \`main=a06e0b0b5f35e9147b4081da7ed7f7934affe0c6\` unchanged. No actual deployment, merge, external model use, participants, paid API or publication.
- Reuse-first: frozen V2 Core check \`scripts/verify_v2_core_freeze.py\` and \`benchmarks/core_freeze/manifest.json\`, pinned V1 baseline blob, V3-12 source-replay publish-block reviews, V3-01 unchanged 100-topic/12-pair pilot, V3-16 human manifest UNEXECUTED, V2 content hashes; actual V3-10 BinarySearch/V3-11 temporal FFmpeg/Pillow clips. No new external source/code copied; no paid provider runtime.
- Added \`learnflow_v3/release_gate.py\`: typed \`ReleaseAudit\` and \`ReleaseGateRow\` fixed 12-gate order, 5 bounded component-only PASS certificates and 7 BLOCKED_UNMEASURED reasons, source-bound V3-12 double sample review and actual SHA256 video checks, two *independently rendered* H264 clips for each of two examples, entire decoded RGB stream SHA equality as normalized encoder-independent video proof (not full application reproducibility). Verifier replays original artifacts rather than trusting caller-provided self-hash, refuses forged/rehash release PASS, untrusted source/tampered MP4/same-file “independent” proof and missing gate. Return can NEVER be RELEASED; \`publish()\` throws.
- Local rollback \`rehearse_local_v2_route\`: checks V2 Core freeze and protected V1 git blob; only creates a temporary route JSON, atomically flips \`v3_staging\` to \`v2_frozen\`, verifies pinned historical SHA and unchanged protected file checksums, destroys temp dir. **No GitHub ref change, production service restore, deploy config change or production rollback test.** Negative tests corrupt frozen baseline, symlink/foreign path and mutated release decisions.
- \`scripts/verify_v3_release_gate.py\` emits exactly 4 real H264 MP4s (2 independently rendered binary 36 frames + 2 temporal 49 frames), complete decoded RGB parity (SHA binary \`3c1917b5b1f6ee932f95d0663e6396fd9661344afd37796d88214f5f96d2576d\`, temporal \`110e143a1359c09132993f385231037dc5a4e16ace21c9d3471fa252e32916d8\`), source-replayed blocked V3-12 reviews, 12 gate matrix, source SHA and rollback attestation. Existing original protected blob SHA \`b7da44db1653e81276a272fe84996665b5d4e410\`. Artifact [#11551224040](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37779748591/artifacts/11551224040). No complete narrated application lesson, real human comparison or API cost included; explicitly NOT ESTABLISHED.
- Implementation [CI #37779748591](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37779748591): **279 V3 / 39 frozen V2 / 86 Hermes PASS**, prereg/Bench/Core Freeze PASS and real H264/rollback checks PASS. Exact-final documentation HEAD CI still needs re-verification; report \`reports/v3_17_release_rollback.md\`.
- Seven missing release prerequisites: 12 matched complete V2/V3 lesson MP4s, independently blinded domain human scores, genuine V3-13 C6 critic gain, real V3-14 C7 incremental repair economics, full lesson factual/audio/subtitle QA, measured actual cost and model failures, authenticated user publish/production authority. V3-16 genuine human evaluation also still OPEN. **NO-GO actual release; V3 engineering checkpoints alone do not satisfy V3 DONE**. No promise of 3B1B parity or end-to-end 98% reliability.
- Do not auto-merge the open stacked #34–#50 PR chain or promote V3 models into production. Next responsible task, if the user separately authorizes it, is a bounded real V2/V3 evaluation and deployment/rollback plan with independent reviewers and explicit costs/permissions, not a synthetic “quality pass”.

## 2026-10-08 — V3 Integration Closure / Reachability Audit
PR #51 stacked on exact PR #50 HEAD f2de4adabc61706a7e243490e32124601c65962a. Historical frozen main a06e0b0b5f35e9147b4081da7ed7f7934affe0c6 not merged/edited. 
Implementation and open gap ledger.

**First bounded implementation proof:** [CI #37783540262](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37783540262) on implementation SHA ad494c06786ace0a8cba95e34453f7ca8b823056: 364 V3 / 39 frozen V2 / 86 Hermes PASS; prereg, Bench and Core Freeze PASS. Exact final documentation+partial-write-fix SHA needs separate full CI verification.

**Confirmed P0:** Product app/main.py -> app/pipeline/factory.py -> app/rendering/router.py and lesson_pipeline/coordinator.py -> lesson_pipeline/core.py CapabilityCoreGateway have no static direct LearnFlow V3 imports. V3-04 router explicitly returns SELECTED_UNRENDERABLE, and V3-03 global render-consumption guard explicitly denies when renderer-owned consumers are absent. Never change either guard to pretend production wiring.

**New real OFFLINE vertical slice:** learnflow_v3/offline_lesson_source.py constructs V2/V3 authored source (no test or golden-render-script imports); learnflow_v3/integration_slice.py replays verified V3-05 source, V3-02 semantics, V3-03 source/signal audit, V3-04 selected routing, dispatches only WORKED_EXAMPLE_BOARD to original V3-06 H264 renderer, V3-10 beat/pixel QA, real FFmpeg one-scene video-only timeline remux, exhaustive decoded RGB SHA parity between scene and assembly, and V3-12 replayed PUBLISH_BLOCKED review. First real output: 36 frames, 640x360@12fps, decoded scene and assembled stream SHA256 both 3c1917b5b1f6ee932f95d0663e6396fd9661344afd37796d88214f5f96d2576d. No narration/audio. All other families explicitly ABSTAIN, cyclic PROCESS_FLOW topology explicitly ABSTAIN_INVALID_TOPOLOGY, never convert to CONCEPT_CARD.

**Dead-code reachability:** scripts/audit_v3_reachability.py scans 387 Python files and 22 V3 modules, returning per-module and per-public-API import/caller/consumer/test JSON and explicit conservative uncertainty for dynamic import/reflection. Production direct V3 imports detected: 0; scripts/tests are not production wiring. No auto-deletion of possibly reusable offline helpers. Reports at reports/v3_integration_closure_audit.md and CI JSON artifact.

**Honest incomplete consumption:** original V3-03 declared deferred leaves stay explicitly reported in a signed receipt as PARTIAL_DECLARED_DEFERRED; material unsupported hero or cognitive-load requests block before rendering. Mutation tests cover source/claim/beat/trace drift, output bytes, preexisting file, disabled renderer, cyclic process, partial assembly output and link. One-scene silent remux is not full multi-scene audio assembly and is not human-quality evidence.

**Real V3-14 defect fix:** artifact_refine.py originally left partial MP4 if renderer wrote bytes and raised before setting created=True; private TemporaryDirectory staging plus certified QA before hard-link-to-final ensures cleanup. Added test simulating write-then-error. V3-14 still reencodes all frames, real critic/C7 efficacy unmeasured. Frozen V2 Core/main untouched; PR #51 open stacked on #50, no merge, no real provider, no publication.

**Remaining blockers:** production V3 router/adapter registration and complete scene/lesson timeline, audio sync, State Machine schema and routing, Code/Math registry, actual VLM/human QA, full 12-pair pilot and release permissions are NOT DONE. This checkpoint at best satisfies a bounded offline one-family vertical slice, not a complete V3 product.

First code CI #37783540262 PASSED; after first PASS fixed V3-14 partial-output corruption risk via private temporary staging and added write-before-crash regression. Exact final docs SHA needs recheck.
Next responsible action after this checkpoint: production router integration and complete narrated multi-scene video can be planned only as a separately authorized checkpoint, while PUBLISH_BLOCKED and human quality UNMEASURED remain.

## 2026-10-08 — V3-18 Product Pipeline Integration (offline gated FastAPI)

### 9.21 V3-18 Product Pipeline Integration — guarded local HTTP Binary Search preview (2026-10-08)

**IMPLEMENTED pending exact final CI** on stacked PR #52 based on PR #51 exact head 749861073f26cc0367ec101c7c63eaecef4e0d1b; frozen main unchanged a06e0b0b5f35e9147b4081da7ed7f7934affe0c6. This is a developer-only HTTP preview and is NOT publication, a production renderer cutover or a complete lesson.

**Audit and chosen single seam:** Existing FastAPI app/main.create_app -> app/pipeline/factory.create_pipeline -> app.state.pipeline -> JobRunner already constructs one LearningVideoPipeline and persists all normal /api/jobs to V2. The separate Hermes lesson_pipeline/coordinator -> CapabilityCoreGateway route remains frozen V2 and untouched. With LEARNFLOW_V3_BINARY_PREVIEW flag (default OFF), factory wraps the original pipeline, and wrapper.process() still directly delegates to the original for all jobs including publication invariant. App also exposes local developer-only POST /api/v3/offline/binary-search that calls preview_binary_search() on the very same app.state.pipeline wrapper; no second queue or live LLM pipeline. Flag OFF gives route HTTP 404, factory original class unchanged; production environment refuses to start with flag ON, remote peers HTTP 403.

**True request-specific offline proof:** JSON bounded sorted values and target from HTTP -> learnflow_v3.offline_lesson_source project-owned builder -> V3-05 binary oracle and V2/V3 typed source -> V3-03 signal audit -> V3-04 honest semantic-only route -> V3 Integration Closure adapter -> V3-06 blackboard H264 renderer -> V3-10 actual beat pixel verification -> FFmpeg single scene remux -> complete decoded RGB parity -> V3-12 publication BLOCKED. Receipt includes trace, beat IDs, claim and object IDs and exact input/route/video hashes. Source is not a golden/test fixture and a different source is used in the CLI test. Unsupported Process, Code, Math, StateMachine and ConceptCard ABSTAIN HTTP 422 without card fallback; all missing/unconsumed signals remain declared. No audio/TTS or real 60s lesson.

**No unauthorized publish:** MP4 and receipt kept in opaque preview directory in existing artifact store, never final.mp4 or final.pending.mp4; no ArtifactStore.publish_final, no JobStatus.SUCCEEDED, no public video GET/URL and no production route registration. The developer HTTP route returns hash/QA receipt only. CI explicitly copies bounded demonstrator MP4 to workflow artifact for offline review then removes private DB/cache. Exceptions after partial renderer output clean preview directory and return sanitized HTTP failure.

**Tests:** tests/v3/test_product_pipeline_integration.py makes REAL TestClient HTTP requests through create_app/factory/SQLite/ArtifactStore, verifies H264 codec/framerate/frame count, source/receipt hashes, normal job mode, default OFF, remote/prod refusal, source mutation, partial-write, unsupported family. App legacy CRUD, fake and real pipeline tests, V3-02 through V3 Integration Closure, V2/Hermes/prereg/Bench/Core Freeze in new workflow .github/workflows/v3-product-pipeline-integration.yml. On initial new code CI #37786569935, 383 V3 tests passed, 1 original Integration Closure test failed because it assumed 0 app→V3 static imports. Replaced that stale invariant with stronger caller allowlist ONLY app/pipeline/v3_preview.py and distinguish GUARDED_DEV_APP_PREVIEW_ONLY_NOT_PUBLIC_JOB_ROUTE from real production imports. Exact final CI pending.

**Scientific and deployment STOP:** A local HTTP source-bound silent preview is NOT ordinary /api/jobs V3 production, not narrated multi-scene full lesson, not Hermes V3 wiring, and not real critic/human gains/release authority. Publication remains PUBLISH_BLOCKED, frozen main and V2 Core unchanged. No external provider/personal human data/model API use. A later separate checkpoint would need genuinely authorized full video product route and human/regulatory release gates.

Read reports/v3_18_product_pipeline_integration.md. All future checkpoint work must distinguish app-factory developer-preview imports from actual normal-job renderer integration. Main and Hermes V2D remain unchanged; never infer publish authorization from feature flag.

## 2026-10-08 — V3-19 Narration-Aware Full Lesson Assembly

### 9.22 V3-19 — Narration-Aware Full Lesson Assembly (2026-10-08)

**Offline developer-only narrated multi-scene technical prototype; exact PR-head CI pending.** Stacked PR #53 on #52 exact parent 148b8365a6b66f1baab49e98ec068c7953fd9934; main frozen a06e0b0b5f35e9147b4081da7ed7f7934affe0c6 and V2 Core unchanged. No merge, paid API, remote TTS, external model inference, human research or production publication.

**Reuse-first audit:** V2 `app.domain.timeline.ResolvedSceneTiming/ResolvedTimeline/SubtitleCue`, V2 `app.pipeline.assembly.VideoAssembler` (FFmpeg H264/AAC/SRT), V3-06 `draw_binary_search_frame`, V3-05 oracle, V3-18 existing FastAPI developer adapter/preview and source, V3-10 source/beat certified baseline, V3-12 fail-closed QA; not V2 `EdgeSpeechProvider` (requires remote HTTP) or character-proportional subtitle timing (not real forced alignment). New `learnflow_v3/narrated_lesson.py` uses local distro eSpeak-NG `en-us` English voice to synthesize actual WAV speech per scene. Source/engine/version/WAV SHA and measured PCM sample counts, sample rates, audio RMS, exact text bound to original trace/beat/claim/object IDs are included in a typed receipt. Scene order intro → mechanics explanation → *each* certified oracle comparison/state step → recap; frames use existing V3-06 dynamic trace visual, not static video stretching or Concept Card fallback. Audio durations are strictly measured from WAV sample counts, video frame counts derived from physical audio duration × 12fps (+one frame for padding), WAV padded to exact frame budget, one real spoken scene = one SRT cue, scene continuity certified by original ResolvedTimeline.

V2 FFmpeg VideoAssembler composes real H264 video scenes + WAV audio segments + burnt SRT, output in private temporary directory, QA original scene frames, output stream H264/AAC, entire final decoded video frames, output duration, final AAC voice audible for *each actual scene interval*, subtitle source/times and identities, then hard-link output MP4+SRT+receipt safely without clobbering. The independent `verify_narrated_lesson()` verifies final source/text/trace/MP4/SRT hashes and final audible AAC per scene. `segment_alignment=MEASURED_AUDIO_SAMPLES_SCENE_BOUNDARIES` is observable in actual decoded streams; **word/phoneme forced alignment and independent transcript-as-heard checking UNMEASURED**, so should NOT count as externally validated speech quality.

Product app `POST /api/v3/offline/binary-search-lesson` calls the **same** `app.state.pipeline` adapter as V3-18; requires BOTH original `LEARNFLOW_V3_BINARY_PREVIEW` and new `LEARNFLOW_V3_NARRATED_LESSON` flags (both OFF by default), dev/test and localhost only, production with flags refused. HTTP returns only private-preview QA receipt; no `final.mp4`, publish_final, JobStatus.SUCCEEDED, URL playback or normal V2 job pipeline mutation. Unconnected families HTTP 422 ABSTAIN, no default ConceptCard. Tests `tests/v3/test_narrated_full_lesson.py`, producer `scripts/verify_v3_narrated_lesson.py`, CI `.github/workflows/v3-narrated-multiscene.yml`, report `reports/v3_19_narrated_multiscene_lesson.md`.

**Caveat:** eSpeak-NG uses an open-source distro voice/program but commercial downstream rights require separate verification; this is offline engineering evidence only, not guaranteed commercial voice licensing. Human instructional quality, pronunciation, forced phoneme alignment, scene-by-scene semantic adequacy, full V3 product release readiness and 3Blue1Brown parity are NOT established. V3-16 human pilot and V3-17 publish authority remain BLOCKED; no production promotion.

**Next actions:** inspect and independently validate actual HTTP MP4+AAC+SRT artifact, regression/test flags, and exact final PR-head CI. If final artifact fails, stop and repair on PR #53 without claiming PASS. No new renderer families until this genuine audio/scene proof is accepted.

### V3-19 visual-overlap correction and real-AAC negative test (2026-10-08)

Manual review of actual first generated [#37790811634 artifact #11555614901](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37790811634/artifacts/11555614901) revealed that the original V2 subtitle styling (`DejaVu Sans`, 22 px) **obscured lower semantic action text**. Initial functional CI PASS alone did not make the rendered lesson visually acceptable. The implementation therefore added opt-in `subtitle_force_style` to original `app/pipeline/assembly.py`: None preserves old V2 behavior; V3-19 selects compact CMU Serif 14 px on its own call. The renderer reserves a clean caption zone Y≥~295, masks original lower labels and reprints certified source action at Y=252, and the new post-assembly decoded-pixel QA rejects bright text in the gutter Y=280–294 for every scene. The introductory scene now highlights individual sorted indices; explanation retains oracle LOW/MID/HIGH motion; recap follows actual certified midpoint path—distinct visual teaching actions, not an animation loop with extra duration. Negative tests include a **self-rehashed MP4 with AAC removed** and a **self-rehashed SRT with corrupted time**, not merely mismatched file hashes. Final CI/visual artifact must be evaluated separately; older artifact demonstrates the overlap defect and must not be used for visual acceptance.

Observed FIRST RUN (before subtitle fix): 7 separate scenes, 44.833 s, 538 video frames, H264 640×360/12fps, AAC voice audio, physical per-scene WAV sample counts and non-silent speech; [CI #37790811634](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37790811634) succeeded. The 7-scene first-run video byte SHA256 `d05fb8b0de9607cec94726a9e6b3fe5c4a66f44034d566d45fd81a8f4289bf0f` matched the media receipt. **This evidence is NOT the final visual-accepted artifact**; see fixed code CI and source checks. No word-level forced alignment, no independent ASR/human listening, no guarantee of commercially cleared voice licensing; publication remains BLOCKED.


## 2026-10-08 — V3-20 Narration–Visual Event Alignment

### 9.23 V3-20 — Narration–Visual Event Alignment & Lesson Quality Gate (2026-10-08)

**Stacked PR #54 on PR #53 HEAD 6847850f48249d82b857380bec8751f2466fa964.** Main a06e0b0b5f35e9147b4081da7ed7f7934affe0c6 and V2 Core unchanged; no merge, deployment, paid API or users. Code-HEAD CI proof and final before/after artifact pending.

**Actual V3-19 media review:** original final H264/AAC 640x360, 12fps, 538 frames, 44.833sec. At timestamp **14.5s**, the action DISCARD LEFT was already on screen even though the voice was only announcing observed midpoint, before explaining Move the low bound. Two duplicate-match steps had similar early candidate/action labels (~20–33sec). The exact timestamped issue matrix and 16-frame video contact-sheet review are documented in reports/v3_20_narration_visual_alignment_audit.md. Video quality is NOT the same as instruction correctness; original trace was mathematically correct.

**Reuse-first V3-20 method:** original source-grounded V3-05 trace and V3-06 H264 blackboard render, V3-19 local espeak-ng WAV, actual PCM sample counts, FFmpeg VideoAssembler, SRT, V3-10 beat pixel QA, V3-12 publication BLOCKED. New learnflow_v3/event_alignment.py emits OBSERVE and APPLY for every oracle-certified COMPARE step, retains beat, segment, claim, object and trace identities. OBSERVE remains at old LOW/HIGH/MID; APPLY only starts next certified state at start of independently synthesised, physically counted next WAV utterance. No character-proportional/fabricated word timestamps. Typed source/event/frame/PCM/SRT proof must replay even when claimant re-hashes input or shifts audio; source-expected frames decoded and checked. V3-19 old endpoint remains unchanged by default.

**Scope honesty:** exact phrase/utterance boundary alignment, NOT recognized word/phoneme onsets, independent transcript-as-heard ASR, expert aesthetics, independent pedagogy or human comprehension. All corresponding claims UNMEASURED, PUBLISH_BLOCKED. eSpeak-NG engine GPL-3.0-or-later (official espeak-ng GitHub); per-voice/output distribution rights require separate review. No external API or downloaded ASR checkpoint.

**App:** LEARNFLOW_V3_EVENT_ALIGNMENT feature flag OFF by default, requires BOTH existing V3-18/19 preview flags; only local development/test; production refuses; unsupported family HTTP 422 ABSTAIN without ConceptCard. POST /api/v3/offline/binary-search-event-aligned uses existing app.state.pipeline wrapper, receipt only, never final.mp4, normal /api/jobs or public URL. Tests tests/v3/test_event_alignment_quality.py cover real HTTP video/audio/source and fake timestamp, missing WAV/proof, wrong segment state, forced word-alignment fraud, shifted SRT, crash-after-write and production/remote guards. CLI scripts/verify_v3_event_alignment.py generates real same-source before/after H264/AAC/SRT and machine event proofs. New CI .github/workflows/v3-event-alignment.yml runs antecedents and original V2/Hermes. First CI #37797446360 FAIL from verifier still replaying original seven-scene source against the new multi-utterance source; fixed verifier selection rather than weakening source/pixel QA.

**NO-GO outside engineering:** actual audio rights, full human quality/learning study, word forced alignment, production routing and release authorization remain BLOCKED/UNMEASURED. Do not merge stacked PRs or claim 3Blue1Brown equivalence.

**Checkpoint continuity**: PR #54 stacked on PR #53, report reports/v3_20_narration_visual_alignment_audit.md; verify final exact-SHA GitHub CI/artifacts before final PASS. Preserve frozen V3-01 prereg and V2 Core. No new renderer family or production publication.


### V3-20 second decoded-frame regression found during before/after review (2026-10-08)

**New actual defect after original V3-20 event-boundary implementation:** downloaded code-head [workflow #37797960605](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37797960605), [artifact #11560111210](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37797960605/artifacts/11560111210). Real same-source before/after clip: original 7 scene/538 frames, V3-20 **10 utterance/event scenes/541 frames**, actual H264/AAC/SRT, all 14 new tests +396 ancestor V3 +21 app +39 V2 +86 Hermes PASS. At 17.333s APPLY begins correct LOW transition; however actual decoded boundary **frame 239→240 (19.917→20.000s)** revealed a 1-frame LOW/MID backward jump at start of next OBSERVE. The exact observed RGB ROI (x0..640,y80..235) mean absolute channel difference was **4.1208** versus **0.0020** at a steady adjacent frame. Existing 3 sampled frames/scene source oracle QA did not catch this discontinuity.

**Second fix and mutation:** `narrated_lesson._narrated_frame` now uses fully settled certified state `progress=1.0` for OBSERVE/RESULT, and only APPLY legitimately tweens from prior to next oracle step. `verify_narrated_lesson` compares **actual adjacent decoded output frames at every APPLY→OBSERVE/RESULT transition**, requires identical source oracle visual step and exact adjoining frame numbers, and rejects ROI difference above 2.0 MAE. This threshold is below the independently measured 4.1208 bad boundary; after-fix residual measured only in final artifact. New `test_regressed_renderer_rewinds_pointer_at_scene_boundary_is_rejected` deliberately recreates the buggy tween and requires decoding-based rejection, not just self-hash or source expected frame checks. **Before/after final acceptance remains pending until final exact PR-head CI and video are inspected.**

**Decoded audio engineering spot check on pre-continuity-fix clip:** ~45.099s mono-16k decoded AAC, RMS 0.08501, peak 0.71451 full-scale, **0 samples >=95% full-scale**. The onset amplitude in first 20ms windows after APPLY WAV boundaries is non-zero for the tested events; these measurements show no obvious clipping, **not an independent pronunciation/ASR assessment**. Commercial output permissions for eSpeak voices remain unverified. No publication, no 3B1B / human-quality claims.



## 2026-10-09 — V3-20 final evidence reconciliation / video reinspection

Earlier “exact final PR-head CI pending” lines above were historical. On **code SHA `cd8494d6fbc8720a39f1e2317ca68f723ab6c963`**, [#37799974547](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37799974547) and the other 21 commit-scoped workflow runs completed SUCCESS. Exact V3-20 job log: 15 new V3-20 / 396 ancestor V3 / 21 app / 39 V2 / 86 Hermes tests PASS. Independently downloaded actual before/after [artifact #11560168593](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37799974547/artifacts/11560168593), decoded 538/541 H264 frames (640×360 @12fps) and AAC, checked source-proven 10-event after SRT, and compared decoded ROI at repaired APPLY→OBSERVE boundary frame 239→240 (**MAE 0.056929 vs known broken 4.1208**). Other terminal continuation transitions were 320→321 MAE 0.029355 and 401→402 MAE 0.082356. Final decoded AAC full-track RMS 0.085008, peak 0.714508, 0 samples ≥95% full scale; lexical ASR/human voice quality NOT assessed. Code SHA engineering verdict **BOUNDED TECHNICAL PASS**, release **NO-GO**. No V2/main merge. Documentation follow-up is a new SHA requiring independent CI check; do not transmute code-head PASS into new-head PASS by inheritance. See report `reports/v3_20_narration_visual_alignment_audit.md` for evidence and scientific limits.

## 2026-10-09 — V3-21 real lesson quality source audit

Draft stacked PR #55, based on PR #54, no main/frozen V2 merge. New lesson_quality.py audits actual same-source V3-19/20 H264/AAC/SRT, 640x360@12fps video, PCM loudness/pacing and actual compressed frame continuity; evidence distinguishes media integrity from student-ready quality, which remains BLOCKED. Word/phoneme accuracy, independent pronunciation/voice naturalness, human learning gains and 3B1B visual preference remain UNMEASURED. The timestamped issue inventory and intended human rubric are in reports/v3_21_lesson_media_quality_gate.md. No user participants, paid calls or commercial eSpeak rights authorization. Dedicated CI and mutation tests exercise original video and metadata, fail closed on forged/rehashed proof, changed SRT, source or silent media. V3-16 independent pilot stays NOT_RUN.

## 2026-10-09 — V3-22 native HD / 24fps visual communication retrofit

PR #56 stacked on PR #55 (V3-21) and not merged to main; frozen V2 Core unaffected. Native redraw from V3-05 source oracle at 1280x720/24fps, OS Computer Modern main action and 32px wrapped captions, independent temporal placement derived from 10 physically measured V3-20 utterance boundaries. Audio output copied from original AAC packets byte-for-byte at the ADTS bitstream level; no TTS retiming or fabricated word alignment. Deliberate new intra-APPLY motion schedule 18% hold, 62% ease, 20% settle, with settled OBSERVE/RESULT preventing pointer rewind. Source-matched original 640x360/12fps video and new HD output are retained with source proof, typed receipt, H264 decoded pixel continuity/semantic evidence and no-clobber negative tests. This is an offline *candidate*, not an educational/human quality validation: reader-distance legibility, voice naturalness, comprehension gains, accessibility, 3Blue1Brown style/teaching parity, cross-topic effectiveness, commercial eSpeak output rights and production publication remain UNMEASURED/BLOCKED. No participants or paid providers. Check exact commit CI and report reports/v3_22_native_hd_typography_pacing.md before claiming technical PASS.


## 2026-10-09 — V3-22 actual video and exact code-head quality reconciliation

Code SHA bf6372058267c399abfc2992e57d2e6d3e396b12 verified **22/22 commit-scoped workflows SUCCESS** including [V3-22 #37869109596](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37869109596). Downloaded actual [artifact #11589353608](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37869109596/artifacts/11589353608) with source 360p video, true-native 720p24 H264/AAC MP4, event proof, receipts, SRT, quality JSON and screenshot sheet. Native video 1082 decoded frames; 40 source-replayed decoded anchors worst full-frame MAE 0.436; three settled visual continuity cuts MAE 0.0, 0.00027, 0.0. Original AAC ADTS bitstream digest matches resulting video exactly. Original first CI failed because V3-21 max sampled frame count (<35) was exceeded; fixed with bounded batches of at most 28 while keeping all 40 sample anchors. Manual frame inspection shows bigger CMU text/captions but a sparse black composition and small microcopy/pointer legend remains. Not equivalent to independent readability/human teaching evidence or 3B1B parity. Engineering-only PASS at exact code commit; V3 production release BLOCKED, V3-16 human experiment NOT RUN, speech licensing/word-level timing UNVERIFIED. Report reports/v3_22_native_hd_typography_pacing.md. Documentation-only follow-up commit CI should be checked independently.

## 2026-10-09 — V3-23 real media readability review preflight

Started stacked PR after V3-22 final `89fb4b030dc875006217cd1a3047bb448685c557`. Explicit nonblinded single-source A/B comparison between V3-20 360p and V3-22 native 720p, NOT randomized 12-pair V3-16 human experiment. Source H264 frame examples decoded from actual video: at 14.333/17.333/20/26.750/33.500/38.333 seconds, sampled 720p lower subtitle band all has visible bright glyph pixels. Actual V3-06 secondary/index labels use approx 23px computer-modern fonts in 720p; project minimum *review cue* 28px, not validated perceptual/accessibility standard. Unresolved beginner-facing jargon `Verified leftmost-index trace / immutable item IDs`, sparse layout, leftmost duplicate explanation transfer and original eSpeak pronunciation require independent study. Offline review_preflight.py/verify_v3_review_preflight.py generate source-validated JSON and blank rubric/CSV for later independent review. No actual human scores, viewer experiments, consent, paid providers, transcript-as-heard or publication. All real human quality judgments UNMEASURED, student-ready/release BLOCKED. Exact final CI and artifact required before bounded technical acceptance. Report: reports/v3_23_readability_teaching_preflight.md.


## 2026-10-09 — V3-24 Visual Clarity and Pedagogical Storytelling (implementation candidate)

Stacked on V3-23 PR #57, preserving main/frozen V2. Existing V3-22 720p video shows small inherited CMU 23px pointer labels and engineer-facing explanation. True target for certified source values [0,2,4,7,11,15,15,21,30], target 15, is *leftmost index 5*, even though a candidate match at index 6 is seen first. V3-24 reuses original V3-20 10 measured utterance events and its exact AAC/SRT, source H264 native redraw at 1280x720 24fps. New authored explanation and 32px LOW/HIGH/MID + 29px stable index labels aim to clarify "match is a candidate → search left → first match", preserve semantic element identity and explicitly forbid future candidate leakage across event boundaries. The source step internals store post-compare candidate; OBSERVE intentionally uses previous APPLIED candidate and APPLY uses current candidate. Actual source/baseline/refinement three MP4 artifacts, 40 decoded source/semantic anchors, three scene continuity transitions, before/after contact sheet and negative/frozen regressions required to close checkpoint. **Human effectiveness and voice rights still UNMEASURED, release BLOCKED**. See report `reports/v3_24_visual_storytelling_refinement.md`. Do not claim effects just because aesthetics/code changed.


## 2026-10-09 — V3-24 actual final MP4 and scientific claims reconciled

Implementation exact SHA `398c3d749a2dae4ad223384328c6d2592ac810c8` got **24/24 commit workflows SUCCESS**, including [V3-24 #37872412940](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37872412940). [Artifact #11591067933](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37872412940/artifacts/11591067933) independently inspected: V3-22 original native 720p SHA 7942d193..., V3-24 native 720p SHA a070e70e..., both 1082 frames/24fps; V3-24 40 source-derived decoded frame checks worst RGB MAE 0.4362, 3 ROI transitions 0.0, original eSpeak AAC packets unchanged, source SRT/event timing unchanged. Decoded screenshots at 17.333 and 26.75s show larger LOW/HIGH/MID and index legend, beginner-friendly wording, explicit prior candidate index6 even when comparing earlier index5. **Manual visual inspection corrected a CI-undetected broken upper separator**, with new y151 continuity regression; added candidate badge and negative early-label test. The PR changes ONLY new offline teaching_storyboard.py plus its verifier/tests and docs; frozen V2/main untouched. No empirical learning, pronunciation, accessibility, commercial voice or 3B1B parity measured. Source grounded technical pass on named SHA only; product/release remain blocked and V3-16 real human pilot not executed.

## 2026-10-09 — V3-25 runnable independent review instrument, not an executed human pilot

After V3-24 (`3df7bfe9`), prepared optional diagnostic A/B video review of V3-22 vs V3-24 (same 720p/24fps, physical WAV/SRT and original AAC packets, source trace and lesson script). Used V3-16 frozen primary human rubric (`clarity`, `representation_adequacy`) and score anchors, not the full V3-16 confirmatory 12-topic randomised study. Binary Search `lfb-005-cs` is explicitly excluded from confirmatory generalisation because development and tuning exposed it. Independent reviewer coding R01/R02 with masked A/B and counterbalanced order; mapping separated as admin-only artifact. Browser offline player has structured per-video rubric, timestamped observation, device distance and application question; client-end self-report is not human verification. The import validator rejects duplicate slots, absent/invalid scores, missing evidence, tampered media SHA, fictitious release; optional differences remain DESCRIPTIVE and need outside corroboration and domain adjudicator if absolute co-primary disagreement >=2. Test ratings are synthetic fixtures ONLY, never emitted as real results. Locked protocol's `human_participants_authorized=false`, real consent/recruitment, human comprehension, word timing, 3B1B parity, commercial voice rights and production remain UNMEASURED/BLOCKED. This checkpoint prepares actual execution tools but cannot recruit independent real people. Report: `reports/v3_25_independent_reviewer_instrument.md`. Exact CI and artifacts pending.

## 2026-10-09 — Video visual QA follow-up: green candidate box misfit

User inspected real V3-24 clip and observed candidate green border longer than gray cell. Root cause: one-off fixed green rectangle x±46/y341..425, but renderer grayscale native slot width/height and rounding use source frame geometry: 1280×720 nine-slot base cell 90×90, green 92×84. Correct candidate outline to the exact computed native cell bounds/radius/stroke, not a padded ad hoc bounding box. Ensure RGB pixel green extent and alternate array sizes 1/6/9/16 are checked, preserve semantic candidate timing, original eSpeak AAC/SRT and source trace. No human outcome claims from cosmetic patch, production still blocked. Engineering closure only after final-head GitHub Actions and actual MP4 artifact inspection.


## 2026-10-09 — V3-26 actual Chromium reviewer E2E design

Stack onto V3-25 PR #59. Prior assistant-container Chromium was blocked by administrator even for local file and localhost, not an actual reviewed E2E. New GitHub Actions runs Playwright Chromium on 2 authentic offline reviewer HTML files with each real source-matched V3-22/24 native MP4/AAC. Browser metadata/currentTime, codec support, nonblank screenshot, actual ended event using a shortened seek, validation errors, full synthetic rubric category/timestamp/transfer form and real JSON download are tested; imported JSON is source cryptographically attested, all simulated answers deleted and zero human results reported. New manual issue categories aesthetic/readability/pedagogy/technical/audio/no_issue, preserve unclassified_legacy for V3-25 records without category; 2+ independent expert recruitment/consent and real third-rater adjudication not authorized/executed. Binary Search known example excluded from frozen V3-16 12-topic confirmatory study; no causal learning, human preference, provider cost or production claim. V2 Freeze/main and paid API untouched. Technical PASS dependent on final exact SHA Chromium GitHub workflow + artifact screenshots.


## 2026-10-09 — V3-26 Chrome Stable actual E2E result (before doc close)

User-authorized V3-26 source implementation SHA 2f22aa52e48eb00992f119d1c2197d20ab2c2f0e: 26/26 commit-scoped GitHub Actions SUCCESS, dedicated #37877573061. Initial #37877153402 exposed failure of Playwright-bundled Chromium headless shell to decode H264/AAC. Replaced it with real Chrome Stable rather than synthetic/mock video; added browser media error diagnostic. Final job validated 2 local HTML reviewer pages, 4 real H264 decoded frames (nonblank screenshots), FFmpeg non-silent AAC tracks, 4 unmuted actual play()/currentTime advances and ended events after deliberate short seek (NOT full human watches), browser missing-consent/unwatched/rubric/category/timestamp rejections, JSON download and source MP4 cryptographic importer. GitHub artifacts R01, R02, admin key and evidence separated; CRC checked, neither reviewer ZIP contained admin mapping or condition names. Synthetic browser scores purged before artifact uploads. Reporter still lists 0 human participants/ratings; classification inventory is a self-report structure only, no true blind, no consent or expertise verification, no paid provider, V3-16 study and commercial rights still UNMEASURED/BLOCKED. Implementation results documented in reports/v3_26_real_browser_independent_review.md; status only guarantees code SHA, not a new doc-only commit.


## 2026-10-09 — V3-27 six-domain topic freeze and cross-domain pipeline reachability

Before implementing V3-27, freeze exact six out-of-pilot selection queries under immutable versioned \`benchmarks/learnflowbench/v3/v3_27_locked_development_topics.json\` (commit \`e2c2d9cd\`, sorted eligible topic index 1 per each of 6 domains). Explicitly exclude V3-16 locked 12 and exposed Binary Search; input SHA for each included query. Existing V3-07/08/15 renderers are finite source-certified but standalone; V3-19 audio/full lesson is binary-search-specific; V3-09 pedagogy and V3-04 Visual Director do not author certified arbitrary domain audiovisual scripts or connect into normal product jobs. V3-27 adds only parameterized linear slope source proof, local actual narrated WAV events and H264/AAC/SRT/decoded frame verification, and labels this as partial narrator adapter, not full Research→Script→Pedagogy→Visual Director. Five other chosen domains ABSTAIN with reasons rather than hallucinated semantics or card fallback; 6/6 retained in denominator, full E2E gate NO-GO. V3-16 pilot remains untouched, no paid API/human/production. Exact evidence/CI pending, see reports/v3_27_six_domain_coverage_audit.md.


## 2026-10-09 — V3-27 actual full-denominator six-domain proof

First attempt built authentic math 720p narrated line graph and 6/6 coverage ledger; technical CI fail was a negative fixture outside V3-08 certified y-range, not missing domain output. Corrected test to valid line coefficients and assert the renderer rejects out-of-axis slopes. Manual decoded full-beat contact sheet showed V3-08 inherited source engineering ID label colliding with subtitle separator; cleared legacy label band and moved caption separator, adding source-pixel gutter regression. Exact code SHA \`3675c14766c5003a773ec8f74d8f2612de2743cd\`, [actual GitHub job #37879738883](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37879738883) PASS: 8 new source tests, 97 previous V3, 39 V2, 86 Hermes, prereg/Bench/Core Freeze. [Downloaded real artifact #11593343670](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37879738883/artifacts/11593343670) CRC PASS and visually inspected; 656 H264 720p/18fps frames, 9 AAC spoken events non-silent with measured WAV timing, decoded frame replay max MAE 0.134, clean footer, real SRT. Coverage: 6 exact prereg-developer topics, math partial 1, 5 ABSTAIN, full E2E 0. Research/Script/Pedagogy/Visual Director did not create this lesson; it is generic author-templated graph math, not an end-to-end generated lesson. Maintain strict NO-GO of six-domain full pipeline and production. V3-16 frozen 12 and main unmodified. Next SINGLE gap V3-28 source-claim→script→pedagogy→semantic renderer narration compiler, not more hardcoded videos. Documentation only commit not automatically inheriting CI.


## 2026-10-09 — V3-28 typed source-grounded compiler seed and ownership split

A distinct seed-first commit c6492ebb locks two existing (V3-27 nonpilot) textbook-cited claims, slope mathematics and constant-acceleration physics; 12 frozen V3-16 topics and Binary Search untouched. Source schema uses finite linear coefficient + bounded graph domain, actual OpenStax source URL and separate local V3-08 arithmetic claim proof. New compiler consumes real Hermes ResearchPack/EvidenceGraph/fact verification + Script, runs actual V3-09 Pedagogy and V2 Visual Director gates, validates claim-to-script-to-beat-to-point identity, and passes ORIGINAL Script spoken text through native WAV and H264/AAC. No arbitrary prose-to-science reconstruction, generated-code execution, card fallback, or production route bypass. Critical caveat: upstream agents are author-seeded offline, source URL alone does not semantically fact-check quotations; source claims externally authored, not model-generated or independently reviewed. Bounded compiler may PASS with 2 actual files but full autonomous six-domain pipeline stays NO-GO with 4 ABSTAIN and 0 actual agent-generation proofs. Scientific/human metrics, voice rights and production remain blocked; exact SHA CI pending.


## V3-28 real math+physics evidence and author-seed limits (2026-10-09)

Code SHA 504381d0, dedicated [CI #37882057811](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37882057811) success. Offline precommitted OpenStax author seeds -> actual Hermes Research/Evidence/Fact + Script validation, V3-09 source-grounded planner and VD gate -> exact source claim IDs/segment beats/point proof -> local real WAV/AAC/SRT + encoded pixels. Math actual 377 frames and physics 404 frames 1280x720/18fps, five measured spoken segments each; source RGB decoder replay max MAE 0.114/0.147 and independently downloaded exact artifact #11594433622 verified. Manual contact sheet review caught (1) misleading generic physics function title, remedied by model-derived velocity/time unit labels, acceleration and v(t), and (2) singular/plural source-generated narration errors, remedied at the exact Research claim source so WAV/SRT agree. Six-domain denominator 2 bounded contract-integrated media, 4 ABSTAIN and 0 full autonomous agent-generated clips; no change to frozen V3-16 or main, no paid API/humans. Source URLs and deterministic fact/Script guards are not independent semantic verification; author seeds must not be represented as live model research/script outputs, no commercial voice clearance, no release. Next capability gap actual agent-produced sourced knowledge and family adapters. Docs final SHA CI pending.


## 2026-10-09 — V3-29 source evidence and actual model-origin honesty

Independent publisher source gate downloads OpenStax math slope (rise over run) and physics constant acceleration (v=v0+at) sections at exact URLs; records hashes and refuses changed origin/missing excerpt. Source anchor verification is NOT full independent semantic fact approval. One-time tagged GitHub commit may try exactly two :free OpenRouter calls: real Research witness to verify source/model relation and real Script witness emitting exact approved Hermes segment content, strictly validated before any voice/video. Upstream ResearchPack and source claims remain author-seeded; cannot advertise autonomous lesson generation. Missing credential/429/free unavailable returns NOT_RUN/BLOCKED without fallback or API cost. Frozen V3-16, main, four other unsupported domains unchanged; production and human outcomes blocked/unmeasured. Exact CI and live statuses must be read from real artifacts.

## 2026-10-09 — V3-29 authenticated live free Research/Script witness

Code SHA 8f736b4e, live GitHub run #37884101493: offline/negative tests PASS, real publisher HTML anchors 2/2 PASS for OpenStax Math+Physics (source hashes recorded), then real nvidia/nemotron-3.5-lightning:free TWO API calls completed a source-relation Research witness and exactly source/claim/beat-matched Script witness. Live model responses have separately verifiable SHA256, video H264/AAC was REALLY rendered and checked: 1280x720, 377 frames at 18fps, five spoken non-silent AAC segments, SRT and math-correct decoded contact-sheet images. ZIP artifact #11595399925 CRC PASS; video SHA 523aac6f863c6dbb3a72f314c8ace917bdb5ed2931a65154836dea4c47fed19d, max image MAE 0.114. Fix: CI needed CMU font for previous pixel tests; added font without relaxing quality gate. Interpretation: bounded genuine provider interaction succeeded, NOT model-generated ResearchPack, independent semantic fact verification, novel creative lesson or full multi-domain autonomy. No paid API, V3-16/production/main unchanged, four other domains ABSTAIN. The one-shot PR provider path is disabled immediately after experimental run; normal CI must never repeatedly call models.


## 2026-10-09 — V3-30 model-authored CS Research/Script source witness

New PR #64 stacks on V3-29 PR #63 without merging main. User explicitly authorized paid openai/gpt-6-luna; fixed ceiling at 2 provider requests per one opt-in run, no retry/automatic fallback or secret echo. Prelocked developer lfb-002-cs with exact query SHA retained. Stronger novelty question than V3-29: model must select real exact publisher subquotes from freshly fetched official Python docs and write its own explanations/4 new narration segments, instead of retransmitting author-seeded exact sentences. Host validates quotes/citations and independently replays a finite add_two(3)=5 process through V3-07 existing DAG/ProcessWalkthrough; no arbitrary model code, no fake general CodeWalkthrough support for Python def. Post-encode source frame & measured AAC narration proofs are required. Scene layout and example remain HOST-generated; not an autonomous Visual Director/Pedagogy LLM execution or human quality result. Frozen V3-16 and unrelated dev domains untouched; production and 6-domain generalization remain blocked. PR #64 candidate implemented; live and scientific verdict pending CI/artifacts. Refer reports/v3_30_paid_luna_source_authored_cs_lesson.md.

## 2026-10-09 — Original publisher source gate GREEN; paid one-shot authorization

Exact candidate SHA 4bb7a18477aad7a87ec2df28e31e2356a9762455 ran workflow https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37891647054: offline tests 9/9 + Code/Process 23/23 + prior V3-28/29 20 PASS; independent official Python Docs source fetch and three publisher citation anchors PASS. The older failure was fixed by preserving inline HTML text continuity and adding redacted failure-code receipts. A source PASS is not independent expert fact review nor real model evidence. Authorized exactly one new paid one-shot push tagged [v3-30-paid-one-shot] on this same frozen lfb-002-cs scope with model openai/gpt-6-luna, at most two provider requests, no retries/fallback. Await actual paid job and output artifact before judging live PASS; do not count all six domains as autonomous.

## 2026-10-09 — First real paid model probe: Research valid; Script blocked

Workflow https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37891895635 had OFFLINE PASS, official Python source PASS and reached paid GPT-6 Luna Research and Script stages. The model returned Research JSON that passed quote/claim checks. Script failed V330_SCRIPT_UNSAFE_UNGROUNDED_OR_COPY. The prior error was a combined predicate and the original generated text was not retained; its precise cause cannot be determined. The old validator excludes underscore and typographic punctuation common in legitimate examples like add_two, a demonstrable code issue but not proof of this particular rejection's cause. The new validator separates unsafe characters, unsupported numeric claims, copy-only narration, absent stage terms, invalid IDs, caption and word length into safe diagnostic codes; canonicalizes ONLY typography and inline-code backticks (original provider JSON hash remains unchanged); adds actual decoded H264/AAC offline media tests. Any further paid run is explicitly an ADAPTIVE engineering iteration, not an untouched preregistered model-quality estimate. Production, human learning quality and full six-domain autonomy remain BLOCKED.

## 2026-10-09 — Native video preflight geometry regression

The new local, fully decoded mock-narration AV test exposed V3_TEXT_OVERFLOW:PROCESS_NODE for the original label Define add_two(n) in V3-07 at 1280x720. The reuse-first fix keeps stable stage node IDs/topology and shortens the displayed process node labels to Define / Call / Bind n = 3 / Return 5 while preserving the full model-authored function name and source evidence in caption and narration. The fix must pass actual encoded media QA before another paid job is considered. Offline mock AV PASS, if obtained, does NOT count as true paid model narration.

## V3-30 engineering gate: real native media preflight PASSED; adaptive paid probe 2

At commit c8b8e273945d312209eb2000204e153a272f7409, GitHub workflow https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37892563052 recorded 11/11 V3-30 tests PASS, including real 1280x720 local H264/AAC + decoded frames/RMS test using mocked narration; V3-07 23 PASS, V3-28/29 20 PASS and frozen suite PASS. The prior official Python Docs source check PASS remains separately evidenced at workflow 37891647054; the publisher source code is unchanged and is reverified by the paid workflow. The first paid GPT-6 Luna probe 37891895635 proved network Research quote validation worked but revealed combined Script validation failure. The current second paid one-shot is an explicitly ADAPTIVE bounded engineering retry with stricter typed semantics, granular safe rejection codes and typography-only normalization; still exactly 2 provider requests MAX for this new attempt, no internal retries, no fallback. This does NOT certify model generalization, learner outcomes, independent fact review, six-domain E2E autonomy, or production.

## 2026-10-09 — Paid one-shot #2 cancelled during AV dependency setup, NO model request

GitHub run https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37892761692 on SHA c2c5ad4016f7ab0fce0ff451b8030380a9094118 ended CONCLUSION=CANCELLED. Offline tests and official Python Docs retrieval were both SUCCESS. The paid job entered its native AV dependencies step at 06:21:59Z and got `The operation was canceled` at 06:52:10Z, matching the 30-minute job budget. The combined shell block silently chained apt-get update, apt-get install and pip install, so the exact subcommand cannot be known from logs. The OpenRouter GPT-6 Luna step was SKIPPED, there is NO model-issued new script or MP4, and NO evidence of paid requests for this run. Corrective workflow now separates an eight-minute native installation / verification step and a seven-minute pip install step, with per-command echo markers and individual absolute deadlines (APT update 120s, install 210s, pip 360s). APT failures remain FAIL-CLOSED, not bypassed. Do not rerun the old unbounded workflow; validate new commit offline and publisher gates before any additional opt-in attempt. No changes to frozen topic, source-grounding, model fallback or production-go decision.

## 2026-10-09 — Shared fail-fast native setup preflight on no-pay offline CI

Commit after dfbd180 replaces duplicated shell setup with `scripts/bootstrap_v3_30_native.sh`, run identically by offline and paid job stages. The script checks FFmpeg, eSpeak NG and real CMU Serif, otherwise performs APT update bounded at 120s and install bounded at 210s; it reports stage-specific error markers. Offline pip and paid pip are each bounded to 360s with separate GitHub job step deadlines. This ensures code changes to the previously cancelled paid setup are exercised by an opt-out, no-model-call offline job, *before* any new opt-in paid run. The source verification and negative tests remain unchanged; do not count setup PASS as a GPT-6 Luna or native user-lesson PASS.

## V3-30 — Controlled rerun after cancelled setup, 2026-10-09

Source-certified, zero-paid preflight on SHA a19c2aa8c2a1dd23461676b9064fa6f6b76b7019: https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37896337396 is SUCCESS, including actual shared native APT/FFmpeg/eSpeak/Computer Modern bootstrap (~31 s), bounded pip installation, 11 V3-30 adversarial/native media checks, 23 Process/Code checks, 20 previous V3 regressions, frozen benchmark guards and independently fetched official Python Docs. The earlier requested paid workflow 37892761692 was cancelled before the model API step, with the model step SKIPPED; no paid calls were made by that run. This distinct tagged commit authorizes a single bounded *replacement* run to complete the already-requested GPT-6 Luna evaluation (at most 2 actual provider requests, zero in-job retry, no fallback). This is adaptive integration evaluation, not independent held-out pedagogical evidence. Review actual receipt and decoded media before declaring PASS. No automatic repeat after a provider/research/script/video failure.

### V3-31 — CS Semantic Consistency & Verified Code State (2026-10-09)

Stacked on PR #64 (not main). V3-30 real paid artifact shows Research doubling 4→8,6→12 across all three explanation paragraphs while original Script/SceneGraph are add_two(3)=5. Freeze original receipt excerpts and model/source/video hashes; block direct reuse. Exactly three host-authored corrections recorded as HOST_ADAPTIVE_EDIT_NOT_GPT6_LUNA and hashes, while original model Script remains unchanged. Narrow AST analyzer validates function/call without execution; V3-07 typed CodeWalkthrough verifies n=3/result=5 and ProcessWalkthrough verifies flow. Render 720p black CMU code panel/variables/calc/return with reused physical TTS→AAC/H264 encoding, subtitles, decoded frame and ROI QA. No new paid calls, no auto fallback; original Research model consistency still a documented failure, no pedagogical or human quality GO, six-domain and production BLOCKED. Report: reports/v3_31_semantic_code_state_lesson.md. Offline exact-head gate and native artifact required.

### V3-31 measured checkpoint (2026-10-09)

Source V3-30 actual real paid receipt+MP4 preserved (run #37896644276); three contradictory doubling research explanations corrected by explicit HOST adaptive ledger, no new model calls. Code AST add_two(n)→n+2; add_two(3) derived under V3-07 typed code numeric and process verifiers (not generic def execution). V3-31 GitHub run #37898649687 passed 11 new, 34 V3-30/V3-07, frozen benchmark/Core and generated artifact #11601756487, decoded real H264/AAC 1280×720 441 frames 24.5s SHA 09354fe9d11a336da204a234d8bb12dde64d051ac55bbaf44ce77a72dee9dff1; all four AAC segments non-silent and ROI states visibly changing. Reviewer inspected actual four-state contact sheet; legible code and binding panel, but explanatory arithmetic not explicitly narrated, no independent teaching test/word-level alignment/rights. Technical bounded offline GO; general model semantics, human pedagogy and production NO-GO. Detailed report reports/v3_31_semantic_code_state_lesson.md; documentation follow-up SHA requires its own CI. No merge main.

### V3-32 — Source-grounded five-beat lesson plan and causal AV (2026-10-09)

Stacked on V3-31 PR #65; no main merge, no new paid requests. Implements typed `LessonSemanticContract` binding PSF publisher's 3 claims, frozen topic ID, learning objectives O1-O3, bounded single-argument integer function example, 5 event IDs, code-role visual state keys, and 5 narration beats Define/Call/Bind/Evaluate/Return. Research from V3-30 that discussed doubling 4→8/6→12 is explicitly REJECTED (original hash/audit retained); **no manual Research editing or laundering into GPT-6 authorship**. Instead deterministic HOST trace compiler generates an independent grounded research and script draft, labeled `HOST_DETERMINISTIC_SOURCE_TRACE_COMPILER`, with revalidated official publisher exact citations; this proves offline engineering but NOT autonomous model self-repair or source semantic expert certification. Compile with bounded AST validation allowing parameterized + / - examples without running code, then reuse V3-07 real assignment replay verifier. Renderer uses physical local speech segments, true H264/AAC decoded frame checks, five distinct visual semantic states, causal moving token trace argument→parameter→evaluation→return→destination, and SRT/WAV-relative semantic event timestamps (NOT word forced alignment). Mutation tests reject changed arithmetic/argument, unsafe AST, spurious source/model facts, claims/beat swaps, timing drift and static visuals. Evaluate visual teaching quality separately; frozen V3-16, commercial rights and production BLOCKED. Detailed report reports/v3_32_grounded_lesson_planning.md; exact HEAD CI/artifact pending.

### V3-32 measured development witness and final gate (2026-10-09)

Stacked PR #66 off V3-31 PR #65. Frozen lfb-002-cs official PSF source claims, old GPT-6 Research contradictions explicitly rejected; typed `LessonSemanticContract` connects evidence, finite one-parameter +/- AST example, objectives, five narration stages, 5 state/event identities. Generic bounded arithmetic validated with separate subtract_four(-2 result) mutation/golden case, not general Python. Host deterministic source/trace compiler regenerates Research/Script to avoid manual edits in offline demo, not a demonstrated LLM regeneration; original model authored prose not silently rewritten. True offline eSpeak→H264/AAC 1280×720/18fps, five physical beats/674 frames/37.44s, decoded source image and per-beat audio, animated causal value path and physically beat-relative event reveals. [Development CI #37901558522](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37901558522) succeeded; event values visibly appear after audio-derived event frames with decoded pre/post ROI deltas 29.226/28.702/30.925/30.178. Real visual review identified an early mid-beat contact snapshot of the Return scene; corrected to stable post-event 78%-beat sampling, exact post-documentation HEAD CI and artifact still required. Zero paid requests, no word-level timestamps, frozen benchmark and V2 Core preserved. Human learning/aesthetic/rights and full six-domain autonomy unmeasured; production BLOCKED. Report reports/v3_32_grounded_lesson_planning.md.

### V3-33 — Preregistered truly unseen six-domain generalization and independent education gate (2026-10-09)

Stacked off V3-32 PR #66 without merging. Selection locked in dedicated pre-implementation commit `8dcb2d32f856af0808bf7abb79c3ddb772cd4450`: lexicographically smallest eligible topic per domain after excluding all frozen V3-16 preregistered/diagnostic, six V3-27 already-exposed and Binary Search. Exact newly locked IDs: lfb-018-math fractions/ratios, lfb-035-physics Newton laws, lfb-070-chemistry periodic table, lfb-053-biology DNA/RNA, lfb-001-cs variables/data types, lfb-085-history-general Industrial Revolution (input query SHA committed). Actual implementation audit finds **no certifiable exact source→example→script→semantic event→renderer bridge** for any of these. Six honest ABSTAIN, 0/6 novel-topic MP4, 0/6 autonomous E2E, no CONCEPT_CARD fallback. V3-27/28 supported math-slope/physics-velocity are allowed to render TWO separately labeled OLD positive-control videos with actual H264/AAC but NOT counted in unseen set; reused native external source references remain author-curated, not live agents. Separate eight-dimension teaching rubric assigns NO human scores absent participant review, no fabricated 3B1B equivalence. Scientific NO-GO for unseen generalization/production, bounded old-source engineering controls may PASS. Report: reports/v3_33_cross_domain_quality.md. CI and artifact proof pending.

### V3-33 confirmed unseen coverage and independent quality boundary (2026-10-09)

Preregistered *before implementation* commit 8dcb2d3: six novel topics first eligible per domain, excludes all V3-16, V3-27, lfb-002-cs and Binary Search; query SHA checks. Exact implementation commit 272a999 GitHub Actions #37904218175 SUCCESS (11 prereg/adversarial tests, 73 post-render regressions, frozen benchmark/Core PASS), 0 provider calls. Six new topics: **0/6 support, 6/6 ABSTAIN, 0 MP4 and 0 full cross-domain generalization**; no concept-card fallback. Previously exposed V3-28 Math slope and Physics velocity examples re-rendered as **TWO separate real 720p18fps H264/AAC regression-control videos**, artifact #11604165488 ZIP CRC and original video SHA verified (Math 523aac6f..., Physics abe5aa75...). Those are NOT counted as newly seen topics. Review of actual contact frames: both show readable black/CMU source plots/values but repetitive point narration, with a final recap and no human learning evidence. V3-31→32 includes explicit Evaluate beat but no independent user learning measure. Eight-dimension educational rubric scores remain null with zero human assessors. Release/semantic six-domain autonomy NO-GO, production BLOCKED. Full report reports/v3_33_cross_domain_quality.md. Exact post-doc HEAD CI pending.

### V3-34 — Model-Directed Generative Scene Authoring controlled pilot (2026-10-09)

Child Draft PR from V3-33 PR #67, without main merge. Pre-implementation registered V3-33 unseen fractions/ratios lfb-018-math SHA 376a0604..., fixed A/B/C, max ONE explicit GPT-6 Luna provider request, no retries/fallback. A old V3-33 source+template and B model-authored scene→old FunctionGraph legitimately ABSTAIN: no exact certified source or fraction partitions. C uses ONE real model-authored creative JSON plan with free choice of shape count/type, placement, color, narration, 4 beats and actions; host translates to finite Manim DSL, NOT untrusted arbitrary Python. Actual Manim v0.19.0 image running Docker network none, read-only, all capabilities dropped, no-new-privileges, memory/cpu/pids caps, read-only code, no secrets, with real eSpeak WAV→AAC/H264, SRT, decoded pixel and audio tests. Local Fraction(1,2)=Fraction(2,4) proves bounded numbers but external source grounding and expert pedagogy still NOT CERTIFIED. Offline fake fixture strictly named and cannot count as real model; no-paid CI first, then one opt-in model live if gates PASS. C technical PASS cannot establish prettier visual quality because A/B have no videos; model generated *scene plan* not arbitrary Manim code; VLM critic and blinded teaching study not yet implemented. Detailed evidence: reports/v3_34_generative_scene_ablation.md. All production rights/teaching/generalization remain BLOCKED.

## Green preflight and one explicit model-shot authorization (2026-10-09)

**No-pay prereg/safety regression:** [GitHub Actions #37907532636](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37907532636) at SHA `d6928efabfcb909e1b45bbfdc9ddbc466d1303fd` SUCCESS; all V3-34 test and frozen V3-33/V3-32/Core safety gates plus actual Docker-sandbox Manim + physically narrated 720p H264/AAC fixture rendered. Artifact [#11604834451](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37907532636/artifacts/11604834451), byte-verified fixture MP4 `4c347a69b11611081da05949129b94945873bd069af4d276015a5ad43953ec5f`, 0 provider calls, origin `SYNTHETIC_HOST_FIXTURE_NOT_REAL_MODEL`. Earlier CI #37906596046 correctly failed a final-versus-partial Manim MP4 discovery bug; subsequent CI #37907399239 correctly identified a negative-test regex expectation issue; both corrected without weakening the actual runtime/schema gates.

This documentation-only commit tagged `[v3-34-one-shot]` authorizes **one** real `openai/gpt-6-luna` structured creative scene request after the exact new-commit offline job passes. It does not authorize retries, fallback or arbitrary generated Python. Preserve per-request receipt and genuine media; if blocked report exact sanitized error, model API attempt count, and no fabricated creative PASS. No production/human quality claims.

### V3-34 actual creative trial and hard schema failure (2026-10-09)

Real GPT-6 Luna one-shot run [#37907978564](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37907978564), opt-in commit `e65c6a9b...`: same-commit offline sandbox/codec/mutation PASS, then **LIVE FAILURE** `ValidationError` when validating the model-authored JSON against `CreativeScene`; artifact #11605866873 has only failure JSON, no model video. We did not save raw provider response or error paths in original runner, so cannot infer exact broken field or billable usage; no fallback/retry permitted, no claim that model lacks creativity. Old A/B ABSTAIN and synthetic Manim fixture C PASS are NOT a three-video comparison. Afterward future-only diagnostics added, preserving nonsecret `path`/`type` shape, but no new paid call. Next candidate: provider-constrained schema output + real model → Manim under same isolated execution and independent quality rubric, as a separately preregistered iteration. No source-certified creative generalization, human educational-quality result or production GO. Report reports/v3_34_generative_scene_ablation.md, PR #68 Draft on #67.

### V3-35 — Independent one-shot structured creative scene (2026-10-09)

New child PR off V3-34 PR #68, never main. The consumed V3-34 model attempt (#37907978564) failed at Pydantic, original raw response missing, so exact offending fields cannot be known. New experiment independently preregistered **before implementation** in commit `238de90a`: exact prior held-out fractions/ratios lfb-018-math SHA 376a0604..., one new `openai/gpt-6-luna` request only, no provider fallback/retry. Reuse old Docker-isolated Manim native H264/AAC and 4-beat voice. Use OpenRouter strict JSON-schema response format and require_parameters provider filtering, portable all-fields-required wire schema, purely structural placeholder normalization then exact V3-34 CreativeScene semantic safety (no executable model Python). Persist sanitized error paths/type and SHA/usage but never raw provider prose. A/B remain honest capability ABSTAIN, C requires one real model-authored storyboard+MP4, no quality parity claim. Offline synthetic fixture never counts as model creative evidence. Human educational rating, full factual source grounding, commercial rights, production BLOCKED. Full report reports/v3_35_structured_scene_authoring.md; exact CI/live pending.

## Exact CI success and one separately preregistered request authorization (2026-10-09)

At commit `0d63d68f04faf79e84bd8051f837949585542c21`, [offline exact-head CI #37911213001](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37911213001) SUCCESS: **27/27** new V3-35 + V3-34 tests, **27 regression PASS + 1 skipped**, frozen benchmark/Core, H264/AAC synthetic HOST Manim rendered from no-network Docker. [Artifact #11606722490](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37911213001/artifacts/11606722490) retrieved and independently inspected; fixture byte fingerprint `4c347a69b11611081da05949129b94945873bd069af4d276015a5ad43953ec5f`. ZERO provider calls so far.

The following unique tagged commit `[v3-35-one-shot]` authorizes ONLY one new GPT-6 Luna JSON-schema strict call following successful offline same-commit dependency. No retries or fallback and no further opt-in tagged commits; save actual request receipt and failure on any model/semantic/render blocker. **Full model-authored video remains PENDING before running this one-shot.**

### V3-35 actual live one-shot outcome: provider 404 (2026-10-09)

After independent preregistered one request, exact-tagged [Actions #37911556743](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37911556743): offline schema mutation/real sandboxed H264/AAC synthetic Manim PASS; live exact `openai/gpt-6-luna` structured `response_format=json_schema`, `provider.require_parameters=true`, fallback false **FAILED HTTP 404**. Downloaded actual artifact #11607281713 receipt `status=BLOCKED_PROVIDER_HTTP`, `V335_HTTP_404`, `attempted_http_requests=1`, no model response hash or token usage; no model-authored scene/MP4. Root of 404 (model not available versus no matching structured endpoint) **undetermined**; no retries/fallback/other model authorized. This is different from V3-34 initial Pydantic ValidationError. Post-run only offline HTTP-error mock and V3-35 receipt labels added; final code and docs exact-head CI pending. Engineering schema and Manim fixture technical PASS; real-model creative video, blinded educational quality, six-domain transfer and production NO-GO. Report reports/v3_35_structured_scene_authoring.md.

### V3-35 public provider capability clarification (2026-10-09)

After the one-shot HTTP404, an unauthenticated public OpenRouter endpoints API GET lists `openai/gpt-6-luna` with providers OpenAI/Azure/Bedrock advertising both `response_format` and `structured_outputs`; therefore 404 does NOT prove model deletion or universal lack of schema support. Actual historical failure remains root-cause UNDETERMINED, because public catalog cannot confirm GitHub secret's per-account permissions, guardrails, historical routing or exact schema. Added a free no-secret no-inference metadata probe, fail-closed synthetic tests and informational CI artifact; **no new model POST**, no retries/fallback. V3-35 live conclusion remains NO-GO/provider HTTP404; human teaching-quality/production BLOCKED. Detailed note reports/v3_35_structured_scene_authoring.md.


### V3-36 — No-inference creative provenance and provider compatibility handoff (2026-10-10)

Audited V3-35 #37911556743: exact single provider POST failed HTTP 404 before storyboard; public endpoint catalog cannot determine the historical POST cause. PR #69 prior final c9752e2 offline success. New prereg 638d1fa authorizes **ZERO model POST** and no automatic opt-in, while implementing two verified code bug fixes: `live-structured` mislabeled synthetic HOST provenance and V335 error status masked as generic V334. Add read-only artifact inspection with exact hashes, model request metadata, real ffprobe H264/AAC, Docker-no-secrets, SRT/voice/pixel evidence; require actual synthetic HOST fixture to be rejected, never counted as GPT-created MP4. V3-33 frozen 0/6 new-topic results, V3-16 confirmatory, independent teaching outcomes and rights remain untouched. A fresh paid one-shot requires separate user authorization and preregistration. See `reports/v3_36_provider_creative_readiness.md`; exact-head CI pending.


### V3-37 — Independently authorized GPT-6 Luna creative scene attempt (2026-10-10)

User requested executing next step after V3-36. Commit a1545c98 freezes lfb-018-math, exact GPT-6 Luna, strict OpenRouter JSON-schema with require_parameters, at most one paid POST/no fallback/no retries, one unique opt-in commit and run_attempt=1. Public metadata GET may block unsafe paid call but cannot explain historical V3-35 HTTP404. V3-37 orchestrates true model-origin scene → real host-compiled Manim Docker → decoded MP4/audio/scene/source SHA inspection, on the actual provider response only; offline fixture always rejected as model evidence. Check exact CI before single opt-in. V3-33 true six-domain unseen rate 0/6, human teaching/rights/production all remain NO-GO. Document `reports/v3_37_first_genuine_creative_lesson.md`.


#### V3-37 empirical outcome (2026-10-10)

Preregistered recovery run `f6a2f3a`, Actions [#38017323094](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38017323094): exact-head V3-34/35/36/37 regression, frozen V3-16/V3-33/V2 Core and real Docker synthetic H264/AAC fixture **PASS**, with mandatory fixture-as-model rejection. After dependency and Manim image preparation, exactly **one** strict `openai/gpt-6-luna` `provider.require_parameters=true` HTTP POST was attempted and received **404**. Downloaded [failure receipts #11656444444](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38017323094/artifacts/11656444444) show `V335_HTTP_404`, `model_response_sha256=null`, `provider_reported_usage=null`, retry_count 0, fallback false. No scene JSON or model-authored MP4. Provider 404 root cause **UNDETERMINED**; cannot infer bad model creativity, billing or specific account/endpoint restrictions from this alone. The registered one-POST experimental budget is consumed; no more live calls without distinct consent/preregistration. Honest verdict: offshore/offline engineering PASS, live model→Manim creative video NO-GO, educational assessment NOT DONE, production BLOCKED. See `reports/v3_37_first_genuine_creative_lesson.md`.


### V3-38 — Investigating post-404 without model inference (2026-10-10)

Postmortem emphasis: V3-34 reached model/Pydantic; V3-35 and V3-37 each received provider HTTP 404 before model JSON. Public GPT-6 Luna endpoints advertised `response_format`, `structured_outputs`, but a prior request included `max_tokens`; some endpoints advertise only `max_completion_tokens`. This is only a capability-filtering hypothesis. V3-38 prereg ce390bbd allows only GET public `/models/openai/gpt-6-luna/endpoints` and same-key authenticated `/key`; fixed paths, no retries, no redirects, no POST, no raw account data, no credit management API. Sanitized state and bounded capability counts establish what can be observed with read-only probes. Positive key authentication does not prove paid model entitlements or historical POST routing. CI findings PENDING. Report `reports/v3_38_openrouter_metadata_audit.md`; no model POST authorization, preserve frozen held-outs and production BLOCKED.


#### V3-38 measured provider-key metadata and 404 analysis — verified (2026-10-10)

V3-38 read-only tagged [#38019407661](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38019407661) SUCCESS; downloaded sanitized artifacts [key evidence #11657084430](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38019407661/artifacts/11657084430) and [public model metadata #11657134163](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38019407661/artifacts/11657134163). Key GET HTTP200, is an inference key, not free tier, per-key remaining-limit bucket POSITIVE, expiry NOT_REPORTED; public GPT-6 Luna metadata GET HTTP200, 7 endpoints with schema flags, 4 max_tokens versus 3 max_completion_tokens. These observations exclude invalid credentials at *measurement time* and absent public model as explanation at *measurement time*, but cannot prove historical model routing, account credits, provider compatibility or strict:true schema support. Old V3-37 POST 404 body was not preserved even as sanitized provider error code, so root cause remains undetermined. OpenRouter chat API now describes max_tokens as deprecated; that is a falsifiable routing hypothesis, NOT an observed fix. Added offline GET-only crosswalk for full V3-37 parameter names vs an alternative max_completion_tokens case, without touching its prereg or adding inference. V3-38 two GETs, 0 POSTs; V3-37 live NO-GO and production BLOCKED. All values in report `reports/v3_38_openrouter_metadata_audit.md`.


### V3-39 — Rationale and falsifiable parameter-routing hypothesis (2026-10-10)

Prior V3-37 one-shot [#38017323094](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38017323094) HTTP404 with exact `temperature=.65`, `provider.require_parameters=true`. New V3-38 real key GET [#38019407661](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38019407661) HTTP200. Public GPT-6 Luna endpoints: all 7 advertise structured outputs, zero advertise temperature, 4 max_tokens / 3 max_completion_tokens. OpenRouter provider routing requires every explicit parameter be supported when `require_parameters=true`; unsupported temperature likely eliminated all candidates. V3-39 prereg `3350f9f` freezes independent one-field intervention (remove temperature only; retain other fields and no fallback), one HTTP POST at most, strict Pydantic/Manim gates and real-video evidence, no standalone pedagogical inference, frozen 0/6 unseen eval unchanged. Historical precise 404 explanation remains probabilistic absent error body. Report `reports/v3_39_compatibility_correct_creative_lesson.md`.
