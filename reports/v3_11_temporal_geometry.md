# V3-11 — Temporal Geometry: Swept Time and Intermediate Frame QA

**Date:** 2026-10-08
**Status:** IMPLEMENTED; final CI still pending at initial report. Bounded engineering success must follow the exact PR-head workflow, not implementation alone.
**Parent:** PR #43 exact SHA 5f7314584248a6b95d447a71b616a49577593502, branch chatgpt/v3-11-temporal-geometry, stacked review-only. Frozen V2/Core and main untouched.

## Root cause, existing capabilities, reuse licensing

Existing V2 learnflow_v2/layout/schema.py Rect provides strict finite immutable 2D bounding boxes with positive-area intersection and touch-safe tolerance. V2 collision.py detects endpoint LayoutGraph collisions but not continuous sweeps. The V3-06 sequence renderer already supplies Pillow/FFmpeg, CMU serif/black rendering and decoded pixel QA. V3-10 supplies source-certified beat/frame timing for **Binary Search only**, not a general interpolation collision solver.

V3-11 adds only the missing project-owned typed time-axis geometry and conservative proof. It reuses V2 Rect.intersects, V2 compute_content_hash, V3-06 SequenceRenderProfile and decoded MAE, V3-07 CMU style, V3-10 video ffprobe verification. OmniManim and SGA intermediate-time QA rationale and the previously pinned MIT Manim/Code2Video studies informed the test matrix; **no external source code copied, no new provider/model, no unverified ALGOGEN source**.

## Concrete implementation

- learnflow_v3/temporal_geometry.py: strict renderer-owned TemporalLayoutPlan, track IDs/roles (TITLE, CONTENT, CAPTION), monotonically ordered complete frame keyframes, rectangle widths and bounds, source-ref hash, exact subtitle safe band, motion-budget profile, real installed Computer Modern text metrics. Does not allow LLM to inject coordinates through canonical semantic plans.
- Interpolations: LINEAR and SMOOTHSTEP. Two shared LINEAR paths have analytic **continuous-time** intersection by solving all four simultaneous affine AABB inequalities over each adjacent union-of-keyframe interval. For matching full-interval SMOOTHSTEP paths, same monotone eased parameter permits analytic proof. Different eased windows/modes use conservative endpoint swept envelopes recursively subdivided; an unresolved potential intersection at the declared maximum depth is **REJECTED** instead of declared safe.
- Each actual discrete renderer frame is tested for V2 Rect collisions, frame clipping and caption/subtitle-zone intrusion. Intermediate text safety checks installed CMU measured pixels at maximal font size, minimum interpolated box dimensions and BOTH old/new labels during morph/reflow; no unverified truncation. Frame-speed and simultaneous-motion budgets prevent gratuitous overload.
- Failing cases get typed V3_11_ errors. Safe static fallback is only a future explicitly source-valid renderer decision, **not an automatic bypass**. Rehashing a stale certificate does not bypass source replay.
- learnflow_v3/temporal_demo_renderer.py: one intentionally bounded renderer-owned keyframe demo produces a **real H264 MP4** with Pillow/FFmpeg. Validates an exact no-clobber destination, replays the certificate, probes codec/frame count, decodes selected **ordinal frames** (including last) with FFmpeg to avoid imprecise timestamp seeks, verifies whole-frame and per-object ROI pixel agreement and source/MP4 SHA. Wrong video with rehashed plan metadata still fails in object ROI. Does not modify production V3-06/07/08 rendering or claim their layouts certified.
- scripts/verify_v3_temporal_geometry.py: reproducible 640x360/12fps, 49-frame example with moving rects, a fixed title and CMU caption inside the reserved subtitle band. Emits real MP4 and machine-readable geometry/pixel evidence.
- tests/v3/test_temporal_geometry.py: positive/crossing one-half-frame where both integer endpoints appear safe, mismatched easing, caption intrusion, caption containment, clipping at intermediate keyframe, text shrink/morph/reflow, motion overload, invalid float/NaN/ID/timeline, stale/rehashed certificate, corrupted MP4, rehashed source with wrong rendered pixel, immutable no-overwrite export.
- .github/workflows/v3-temporal-geometry.yml: all above tests and V3-02..10 relevant regression, frozen V2/Hermes, prereg, Bench and Core Freeze, H264 golden upload.

## Acceptance / objective technical limits

Reproduce:
```bash
python -m pytest -q --confcutdir=tests/v3 tests/v3/test_temporal_geometry.py
python scripts/verify_v3_temporal_geometry.py --output-dir /tmp/v3_11_evidence
```

The **bounded engineering criterion** is that every fixed negative mutation fails and one safe real MP4 is decoded with geometry source certificate, no unsafe intermediate object overlap, clipping, caption intrusion or text overflow. The continuous sweep is an analytical or conservative geometry proof **of the supplied renderer-owned AABB trajectories**, not general unconstrained animation semantics.

**Explicit NO-CLAIM boundaries:** no general scene/shot transition optimizer; no tested integration into all V3-06 Binary Search pointer geometry, V3-07 Code/Process or V3-08 Mathematics video; no real TTS audio/subtitle speech alignment; no audio channels in golden; no human evaluation, general production publication or 3Blue1Brown visual parity; no representative-domain ≥90% gain. Static/Python source correctness cannot independently certify produced perceptual understanding. The generic planner treats nodes as non-overlapping AABBs; intentional layering/overlapping labels requires a future typed composition contract. Fail closed for unsupported shapes.

**Next exactly one checkpoint if and only if V3-11 final HEAD passes:** V3-12 Fail-Closed QA and Publication policy.
