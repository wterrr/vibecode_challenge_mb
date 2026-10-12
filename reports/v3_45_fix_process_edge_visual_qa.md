# V3-45-FIX — Process Arrow/Node Geometry and Decoded-Pixel QA

**Scope:** Correct the screenshot-observed arrow overlap in V3-45's host-owned ordered_process Manim compiler, preserving the existing finite two-family JSON protocol, frozen model budgets, original V3-45 narration, and no merge main. **This was NOT authored by GPT-6 Luna.**

## Frozen preregistration and empirical failure

Pre-fix decision fixed at `benchmarks/learnflowbench/v3/v3_45_fix_edge_visual_preregister.json` commit `b3da211` BEFORE implementation. Parent PR #79 HEAD `65499a93`. Original video [GitHub run #38196528217 artifact #11723409076](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38196528217/artifacts/11723409076); synthetic MP4 SHA256 `f9f6c54647fad3797da445b1a8714c9fa967f1f0bf35a9bfa1fd629cc1172a48`.

**Root cause:** `_compile_process` used `Arrow(src.get_center(),dst.get_center(),buff=.75)`; node half-width is 0.90 world units, therefore arrow line/tip crossed the block by 0.15 units at each endpoint. Independently, the yellow cursor animated `MoveAlongPath(Line(src.get_center(),dst.get_center()))` and thus traversed the caption text inside both nodes. No existing visual QA checked this, so V3-45's codec tests gave a misleading green result for layout.

**Frozen screenshot-defect reproduction on OLD actual 15fps 1280x720 H264:** use physical WAV beat duration to isolate a frame before edge appearance (frame 128), one fully visible before traversal (frame 152), and early cursor traversal (frame 159). Compare RGB-channel difference >70 on inset edge/caption masks (Manim projection: 90 px/world unit). OLD overlap/contrast: 52 changed pixels in source-node interior, 72 in target-node interior, 220 at source caption, 280 visible between nodes. These are rendered-frame metrics, not semantics inferred from source.

## Implementation

- `process_edge_layout` computes ray intersection with source/target axis-aligned rectangles for arbitrary horizontal, vertical or diagonal direction and unequal node dimensions, with **0.16 world-unit clearance** from both boundaries. Rejects paths with no visible segment, third-node intersections, out-of-safe-canvas nodes, or invalid references BEFORE host code compilation. No synthetic coordinate special-casing or ID-based layout hacks.
- Manim arrow created from finite explicit geometry `Arrow([x0,y0,0],[x1,y1,0],buff=0)`. Edges render behind node borders/captions via z-index. Traversing yellow cursor follows `Line(edge.get_start(),edge.get_end())`, never node centres; protects the same gap geometry.
- `learnflow_v3/process_edge_visual_qa.py`: actually decodes three exact H264 frames with FFmpeg, checks no newly drawn white connector pixels inside either endpoint node, no cursor changes on source caption, AND that a visible arrow remains between nodes. Hard blockers source/target/caption each ≤8 changed pixels, gap ≥100. Reproduces failure from SHA-locked old artifact (old source/target ≥20 and cursor ≥12). Frames derive from original physical `beat_i.wav` using **ceil(sample_count/sample_rate×15)+3** per existing V3-34 beat padding: no invented timestamps or OCR.
- Native runner fails closed on visual pixel violations; workflow downloads historic failed artifact, runs original V3-41/40 and V3-45 tests plus new adversarial geometry+pixel tests, renders TWO actual Manim H264/AAC MP4s, and checks after-media receipt's pixel gate. Both model HTTP POST and authenticated GET remain 0.

## Independent first-after rendering before final CI

One genuine **offline HOST-rendered** artifact after source-only geometry fix, [push #38197700273 artifact #11724855006](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38197700273/artifacts/11724855006), was downloaded and compared with the original MP4 using the identical pixel masks/timestamps. Measured **AFTER** source-node overlap 0, target-node overlap 0, cursor-vs-caption 0, visible gap 383, versus the frozen failing values 52/72/220/280. This visual evidence confirms the reported error is fixed in that video, but source-only passing CI predates the formal automated negative-control workflow.

## Limits and acceptance

This is a localized **process edge geometry** fix, not proof of polished motion design, word-level synchronization, the model's ability to author the model-facing JSON, all-six-domain coverage, or education-grade quality. These are synthetic host-produced offline test videos. Production remains BLOCKED and PR #79 Draft; no merge main, no new model request. **Final exact-head native CI and artifact evidence must be confirmed separately before closing this fix as PASS.**
