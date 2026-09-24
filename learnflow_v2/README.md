# LearnFlow V2.1 Experimental Implementation

Source of truth:
`PLAN_V2.md`

## Status
- Implemented checkpoints:
  - V2-00: Freeze V1 & Establish V2 Baseline ✅
  - V2-01: ConceptRegistry + SceneGraph Semantic IR ✅
  - V2-02: Intrinsic Measurement ✅
  - V2-03: Simple Constraint Layout (Kiwi/Cassowary) ✅
- Not production-wired (V1 production path remains frozen under `app/`).

## Capabilities Implemented (V2-03)
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

## Explicitly Not Implemented Yet
- Graph layout (ELK, Graphviz)
- General collision solving (iterative axis separation)
- Layout candidate scoring (J_soft ranking)
- Continuity constraints (previous_layout stay constraints)
- MotionPlan & motion timeline
- Rendering subsystem (V2 renderer, Canvas, SVG, Manim)
- OpenRouter runtime / LLM agent runtime
- VLM / Hermes multimodal critique

## Current Modules
- `learnflow_v2.core`: Canonical serialization, structured error hierarchy.
- `learnflow_v2.concepts`: Deterministic ConceptRegistry, canonical concept IDs, alias normalization, cross-namespace collision checking, strict JSON-safe metadata.
- `learnflow_v2.scenegraph`: Semantic SceneGraph IR (zero pixel geometry), relation taxonomy, layout hints, symbolic style refs, V1 adapter.
- `learnflow_v2.layout`:
  - `measurement.py`: Intrinsic content measurement using real font metrics (Pillow) and local image inspection.
  - `schema.py`: Strict, immutable Pydantic models for Rect, FrameProfile, LayoutZone, LayoutBox, LayoutGraph.
  - `profiles.py`: Deterministic 16:9 and 9:16 frame profiles with named safe regions and grid spec.
  - `constraints.py`: Compiler from items + measurements into linear constraints for simple templates.
  - `preflight.py`: Hard gate validation against clipping, overflow, and invalid geometry.
  - `backends/kiwi.py`: Real Kiwisolver (Cassowary) linear constraint solver wrapper.

## Future Module Map
- `layout` (advanced graph / ELK / collision / scoring) → V2-04 / V2-05
- `motion`                                             → V2-07+
- `render`                                             → V2-09+
- `verification`                                       → V2-11+
- `agents`                                             → V2D


Future modules do not exist yet and must not be implemented until their respective checkpoints.

## V2 milestone status

- V2-00 ✅ V1 freeze + benchmark
- V2-01 ✅ ConceptRegistry and SceneGraph semantic IR
- V2-02 ✅ intrinsic measurement
- V2-03 ✅ FrameProfile, safe zones, grid, Kiwi constraints, LayoutGraph preflight
- V2-04 ✅ graph layout

V2-04 implemented deterministic graph layout only:
- ELK Layered adapter through local `elkjs` bridge
- Graphviz `dot -Tjson0` fallback/baseline adapter
- directed graph nodes, ports, orthogonal routed edges
- routed-edge artifact schema
- graph preflight helpers and observational edge metrics

Not implemented in V2-04:
- collision repair
- layout scoring or candidate comparison/ranking
- layout continuity
- motion planning
- rendering
- VLM
- Hermes
