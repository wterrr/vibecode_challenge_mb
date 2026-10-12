# V3-46 — Visual Quality System & Benchmark

**Status:** Native offline two-family evaluation underway. This is a host-only visual redesign using **SYNTHETIC** semantic JSON fixtures; no real GPT-6 Luna scene was generated.

## Preregistered before implementation

Preimplementation record `benchmarks/learnflowbench/v3/v3_46_visual_quality_preregister.json`, commit `3dcd786`. Frozen parent Draft PR #79 SHA `646a82c021b17400aafa1dfd30a0a157c930ec10`. Baseline V3-45-FIX [PR native CI #38198567269](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38198567269), SHA-verified source/fraction `cb6943132289e1d9ede3556c4288bcb4e58278860deab9fe441286732e61b8b7`; baseline process source derived from the same archived two-family run's receipt. Both are host-authored not genuine LLM responses.

## Real video audit before changes

Source MP4 frame inspection at 24s:
- Fraction equivalence: computer-modern-like text and correct ratios already present, but large black negative space, two isolated rectangles without a unifying compositional region, a wide detached symbolic proof. Lack of connected pedagogical visual hierarchy is an aesthetic concern; technical math pass is NOT educational quality.
- Ordered process: Start→Verify→Finish basic 3-node flow, title high and a detached instruction footer. V3-45-FIX successfully corrected centre-to-centre arrow/cursor penetration; text still crowds interior nodes, scene feels like a functional diagram rather than professional animated instruction. Existing H264 pixel regression preserves node clearance.
- Both source videos retain four physical beat WAVs and exact deterministic H264/AAC mux. The same synthetic semantic JSON and narration must be reused in this checkpoint, with no selective model reruns.

## Reuse-first host-owned design

- `learnflow_v3/visual_quality_system.py` centralizes typographic font/size hierarchy, muted off-black board/background, restrained accent color, header/footline stage frame, per-beat position indicators, content-safe rectangles and node-caption fit budget. No topic ID branching; only the two previously validated semantic family enums. All brand chrome lies away from semantic artwork. Generalization beyond those two classes is **not claimed**.
- Opt-in `compile_scene(...,visual_quality=True)` and `compile_manim(...,visual_quality=True)` so original V3-41–V3-45 baseline path remains untouched. Process node captions get a reusable inset; fractional diagram groups get subtle matching panels, retaining exact source coordinate/ratio and displayed algebra. Manim remains isolated under the existing no-network, read-only Docker runtime; source Python is host compiled, never executed from model JSON.
- Original narration and semantic event clocks are unchanged; generated 4-beat activity indicators follow beat start only. No invented phoneme/word timestamps.

## Measured benchmark, NOT subjective grading

- `scripts/run_v3_46_visual_quality.py` physically downloads/reuses two frozen baseline MP4s and emits two new H264/AAC videos, original SHA receipts, exact narrated-frame counts, sampled beat-relative 12-frame pairs **per family**, plus observed occupancy/activity/screen-boundary metrics. Contacts are exported side-by-side (before/after) using actual FFmpeg-decoded pixels, not source-code drawings.
- Automatic fail-closed gates are for objective violations only: no near-blank frames in the sampled event window, no foreground clipped at outer margin, no broken source wire hash, same original beat frame counts, H264/AAC and synthetic provenance. Preserve prior pixel-level process arrow-node overlap QA. These metrics are NOT a proof of improved learning, artistic composition or smoothness across all frames.
- The six-dimensional visual/speech rubric (composition, typography, semantic clarity, motion/pacing, perceptual polish, narration coherence) is exported as a **blank** independent-human evaluation CSV. Scores are explicitly NULL until blinded external reviewers actually fill them; no automatic "3Blue1Brown-quality PASS" or invented reviewer scores.

## Research validity and limitations

One deterministic synthetic fraction and one synthetic linear-process case, no inference, no students and no independent human participants: no statistical generalization or causal estimate. The new shared style may improve visual hierarchy but MUST be judged by actual video frames, not a green GitHub check. No unsupported general curriculum/domain claims. Word-level narration alignment, audiovisual pedagogy and blind aesthetics remain untested. If this checkpoint achieves native technical gates alone, classify **TECHNICAL LAYOUT PASS / HUMAN VISUAL QUALITY PENDING**, not a product-quality pass. Production BLOCKED; do not merge main.

**Evidence/results:** Exact-head CI, final artifact hashes and frame review pending.


## Empirical offline results — first real native comparison (12 October 2026)

[Native CI #38200413211](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38200413211) passed on the final renderer code, producing [two-family artifact #11725840042](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38200413211/artifacts/11725840042). Both MP4s were downloaded and inspected at the 24-second frame, alongside twelve matched beat-relative decoded samples per family.

| Synthetic family | Frames / duration | New MP4 SHA256 | Foreground occupancy before → after | Meaningful sampled transitions | Bright outer-margin pixels |
|---|---|---|---|---|---|
| Fraction equivalence | 497 / 33.133 seconds | `d14e7bb6e2cff98ee7296a21eb9183a59e20fcbc20c25a87eef923cd90a777e1` | 7.417% → 7.667% | 7 → 7 | 0 → 0 |
| Ordered process | 513 / 34.2 seconds | `348bfdcaa9043a25a0dc7b491500164d0980d6c1d9c3b89d1d16373962e50b91` | 2.021% → 2.306% | 5 → 5 | 0 → 0 |

On-disk SHA256 matched each receipt; the underlying model-facing synthetic JSON and physical narration frame budgets remained unchanged. Per-frame motion averages fraction 1.7684→1.7161, process 0.6632→0.6433, so there is **no evidence of increased animation density**. The initial mean-motion >1 threshold falsely rejected legitimate narrated holds. Objective gating now requires four meaningful sampled transitions plus the original native decoded-motion gate and preserved V3-45-FIX node/edge/cursor pixel-overlap checks; real videos showed 7 and 5 transitions.

Visual inspection: fraction group panels improve separation and emphasis on equal-sized wholes; process captions gain inset, destination focus and consistent hierarchy. The videos remain spatially sparse and still not polished, with word-level narration synchrony, voice naturalness and educational outcomes unassessed. The human quality rubric is **unrated**; side-by-side images are labeled BEFORE/AFTER and therefore **are not blinded preference trials**. No human visual superiority or 3Blue1Brown-quality PASS is claimed.

**Technical renderer evidence PASS at source commit `44cbace`; exact final PR HEAD CI pending.** Production BLOCKED, synthetic host-owned output only, 0 model requests.
