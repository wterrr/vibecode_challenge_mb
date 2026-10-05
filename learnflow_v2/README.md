# LearnFlow V2.1 Experimental Implementation

Source of truth:
`PLAN_V2.md`

## Status
- Implemented checkpoints:
  - V2-00: Freeze V1 & Establish V2 Baseline ✅
  - V2-01: ConceptRegistry + SceneGraph Semantic IR ✅
  - V2-02: Intrinsic Measurement ✅
  - V2-03: Simple Constraint Layout (Kiwi/Cassowary) ✅
  - V2-04: Graph Layout (ELK / Graphviz) ✅
  - V2-05: Collision Repair & Multi-Candidate Optimization ✅
  - V2-06: Cross-Scene Semantic Continuity & Displacement Minimization ✅
- Not production-wired (V1 production path remains frozen under `app/`).

## Capabilities Implemented (through V2-06)
- Safe frame profiles (16:9, 9:16) with scale-aware definitions.
- Named safe layout zones (SAFE_EDGE, SAFE_TITLE/TITLE, SAFE_CONTENT/CONTENT, SAFE_CAPTION/CAPTION, BOTTOM_UI_SAFE) derived deterministically from insets and proportions.
- Lightweight deterministic layout grid specification.
- Kiwi (Cassowary) linear constraint layout backend (`learnflow_v2.layout.backends.kiwi`).
- Hard feasibility-first constraints (STRENGTH_REQUIRED) taking absolute precedence over soft aesthetic preferences.
- Simple layout strategies:
  - CONCEPT_CARD (centered in content zone, protected title/caption)
  - COMPARISON (two-column non-overlap, positive gutter, mirror symmetry around center, equal width preference)
  - IMAGE_TEXT (16:9 side-by-side, 9:16 aspect-aware stacked)
  - QUOTE (centered, bounded maximum width, optional attribution below)
- Strict preflight validator (`learnflow_v2.layout.preflight`) enforcing zero frame overflow, zero safe-zone violations, zero content clipping, and zero invalid geometry.
- Canonical, deterministic LayoutGraph serialization via `canonical_json`.
- Graph layout backend (ELK Layered via local `elkjs` bridge, Graphviz `dot -Tjson0` fallback/baseline).
- Directed graph nodes, ports, orthogonal routed edges with routed-edge artifact schema.
- V2-05 Collision Repair & Optimization:
  - Pure node collision detection (`detect_box_collisions`)
  - Deterministic linear separation constraints (`choose_separation_constraint`)
  - Real Kiwi collision re-solve (`repair_layout_collisions`) without manual coordinate mutation
  - Bounded iteration budget: `MAX_LAYOUT_SOLVES = 5`
  - Hard feasibility gate (`evaluate_feasibility`) evaluating clipping, overflow, overlap, safe-zone, and minimum readability
  - Multi-objective soft score ($J_{soft}$) components: edge penalty, typography placeholder penalty, balance penalty, whitespace penalty
  - Deterministic candidate ranking (`choose_best_candidate`)
  - Topological fallback variants: COMPARISON stacked fallback, IMAGE_TEXT stacked fallback
  - Dense fixture corpus with category-specific assertions (`no_collision`, `repairable`, `fallback_required`, `impossible`)
- V2-06 Semantic Continuity & Displacement Minimization:
  - Cross-scene semantic identity matching via `SceneNode.semantic_key` (`build_continuity_context`)
  - Normalized anchor mapping (`ContinuityAnchor`) projecting from previous semantic zone to current legal zone across arbitrary aspect ratios (16:9, 9:16)
  - Solver-based soft stay constraints (`ContinuityConstraint`) generated for Kiwi without post-hoc geometry mutation
  - Feasibility dominance: safe zones, role boundaries, and collision separation constraints (STRENGTH_REQUIRED) strictly dominate continuity preferences
  - Auditable spatial displacement metrics (`ContinuityMetrics`: matched, new, removed, total, mean, and max displacement)
  - Multi-objective soft score extension with `continuity_penalty` and `continuity_weight`
  - Complete backwards compatibility: omitting continuity context matches V2-05 behavior with zero penalty
  - Graph stable ordering (`derive_stable_graph_order`) and ELK layered model order stability (`NODES_AND_EDGES`)
  - Dense continuity fixture corpus (`benchmarks/fixtures/v2/continuity_cases.json`) and comprehensive test suite

## Explicitly Not Implemented Yet
- adaptive typography shrink
- content splitting
- motion planning & motion timeline
- rendering subsystem (V2 renderer, Canvas, SVG, Manim)
- VLM repair / Hermes multimodal critique
- OpenRouter runtime / LLM agent runtime
- production V2 integration (V1 remains frozen production path)

## Current Modules
- `learnflow_v2.core`: Canonical serialization, structured error hierarchy.
- `learnflow_v2.concepts`: Deterministic ConceptRegistry, canonical concept IDs, alias normalization, cross-namespace collision checking, strict JSON-safe metadata.
- `learnflow_v2.scenegraph`: Semantic SceneGraph IR (zero pixel geometry), relation taxonomy, layout hints, symbolic style refs, V1 adapter.
- `learnflow_v2.layout`:
  - `measurement.py`: Intrinsic content measurement using real font metrics (Pillow) and local image inspection.
  - `schema.py`: Strict, immutable Pydantic models for Rect, FrameProfile, LayoutZone, LayoutBox, LayoutGraph.
  - `profiles.py`: Deterministic 16:9 and 9:16 frame profiles with named safe regions and grid spec.
  - `constraints.py`: Compiler from items + measurements into linear constraints for simple templates, including `semantic_key` pass-through.
  - `preflight.py`: Hard gate validation against clipping, overflow, and invalid geometry.
  - `backends/kiwi.py`: Real Kiwisolver (Cassowary) linear constraint solver wrapper.
  - `backends/elk.py`: Local `elkjs` bridge for deterministic layered graph layout.
  - `backends/graphviz.py`: Deterministic Graphviz fallback backend.
  - `graph.py`: Directed graph layout orchestration and routed edge schemas.
  - `collision.py`: Pure box collision detection and deterministic separation constraint generation.
  - `score.py`: Hard feasibility gating and multi-objective soft scoring ($J_{soft}$) with `continuity_penalty` and `continuity_weight`.
  - `optimization.py`: Iterative collision repair engine, multi-candidate optimization pass, and continuity integration.
  - `continuity.py`: Auditable cross-scene semantic continuity context, normalized anchors, soft Kiwi stay constraints, displacement metrics, and graph stable ordering.

## Future Module Map
- `motion`        → V2-07+
- `render`        → V2-09+
- `verification`  → V2-11+
- `agents`        → V2D

Future modules do not exist yet and must not be implemented until their respective checkpoints.

## V2 milestone status

- V2-00 ✅ V1 freeze + benchmark
- V2-01 ✅ ConceptRegistry and SceneGraph semantic IR
- V2-02 ✅ intrinsic measurement
- V2-03 ✅ FrameProfile, safe zones, grid, Kiwi constraints, LayoutGraph preflight
- V2-04 ✅ graph layout (ELK + Graphviz)
- V2-05 ✅ collision + optimization
- V2-06 ✅ cross-scene semantic continuity & displacement minimization

Still NOT implemented:
- adaptive typography shrink
- content splitting
- motion
- renderer
- VLM repair
- Hermes
- production V2 integration
