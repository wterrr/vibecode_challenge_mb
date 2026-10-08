# V3-14 — ArtifactRefine: bounded local track restoration and rollback

**Date:** 2026-10-08. **Status:** BOUNDED OFFLINE ENGINEERING PASS on implementation commit `38a56ec5073c56fc9a0610b996be999c3da62772`, [CI #37755768974](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37755768974) passed. Exact final documentation PR-head CI must be checked separately.
**Parent:** exact PR #46 HEAD `0d62803960c7c7cdc937997fe919dd79fa532b62`; stacked review-only branch `chatgpt/v3-14-artifact-refine`. V2 frozen main remains `a06e0b0b5f35e9147b4081da7ed7f7934affe0c6`; no merge, no paid/free provider calls.

## Reuse audit and trust boundary

V2 `learnflow_v2/repair` already defines immutable content hashing, selective dependency invalidation, bounded repair budgets and repair classifications. Rather than duplicating its global SceneGraph repair engine, V3-14 reused `compute_content_hash` and V3-11 renderer-owned `TemporalLayoutPlan`, `certify_temporal_layout`, `verify_temporal_certificate` and genuine H264 + decoded frame ROI `render_certified_temporal_demo` / `verify_temporal_render`. V3-12 publication remains deny-by-default and V3-13 critic findings are still **not independently validated**, so this checkpoint **does not let a critic supply geometry, executable code, or publication authority**. No copied upstream Manim/Code2Video/ALGOGEN code or additional dependencies.

## Implemented

- `learnflow_v3/artifact_refine.py`: strict immutable `LocalRepairIntent` limited to `RESTORE_LAST_CERTIFIED_TRACK` with an AUTHOR_SEEDED_CERTIFIED_SNAPSHOT. Exactly one attempt, no reviewer/user-supplied replacement coordinates. Input binds baseline plan, injected candidate, targeted track object ID and exact SHA-256 of candidate track, with a fault category required to match the original deterministic QA failure (not an arbitrary claimed error).
- Preflight **recomputes original certified plan and decodes original H264 pixels**, then checks all global semantic/layout identity fields, complete ordered track identities and hashes. A local edit must affect **exactly one** named track; cross-track edits, no-ops, stale hashes, wrong defect classifications and global source metadata edits are rejected before rendering. Critic categories outside this bounded domain are deferred to their source-owning layers (Research/Script/Pedagogy/Visual Director), never silently patched as geometry.
- Local compiler copies back the exact authorized prior track only. The resulting full plan MUST hash-match the certified baseline. All non-target track hashes are checked to be identical. Downstream V3-11 temporal geometry, actual H264, exact decoded pixel QA and V3-12 publication-review evidence are explicitly invalidated and recomputed. The original MP4 is kept immutable; generated output is no-clobber. If encoding/QA fails, only the newly generated repair video is eligible for rollback; any failed result remains `ROLLBACK_BLOCKED`. On successful bounded source repair, status is `LOCAL_REPAIR_VERIFIED` but **publication_blocked remains True**.
- Typed report records original/candidate/repaired source and video hashes, targeted/untouched object IDs, downstream invalidation list, whole-clip frames re-encoded, one-attempt budget, rollback/authorization status and a content checksum. Forged self-rehashed release flag is rejected; independently re-rendered replay can detect a forged review.
- `tests/v3/test_artifact_refine.py`: seeded text font overflow, content subtitle intrusion, offscreen clipping, abrupt motion, overlapping content; each produces a real restored MP4. Negative cases include multiple affected tracks, semantic source drift, no-op, wrong defect category, stale plan/MP4, existing output/original output overwrite, injected FFmpeg failure and rehashed status. `scripts/verify_v3_artifact_refine.py` renders a genuine V3-11 trusted clip and five reconstructed H264 clips plus JSON trial outcomes. `.github/workflows/v3-artifact-refine.yml` runs full V3 ancestor sample tests + frozen V2/Hermes + benchmark/prereg/Core Freeze + real media SHA evidence.

## Measured bounded acceptance

[CI #37755768974](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37755768974) on implementation HEAD: **228 V3 tests / 39 frozen V2 / 86 Hermes PASS**, V3_BENCHMARK_PREREG PASS (12 topics/6 domains), LEARNFLOW_BENCH_CONTRACT PASS, CORE_FREEZE PASS. Five predefined AUTHOR_SEEDED_SYNTHETIC corrupted cases were restored to a certified plan (5/5), preserving three untouched track hashes each. **Six actual 49-frame H264 MP4s** were generated (one source plus five restored clips); each restored output passed SHA and decoded frame geometry QA. No publisher, no model/tool calls, no LLM-supplied geometry. Repair classes that cannot be safely mapped to an original certified track are deliberately deferred, not auto-applied.

## Scientific and product limits

The Plan C7 aspirational target **“≥70% recovery without full-scene regeneration” is NOT ESTABLISHED** by this checkpoint: 5/5 is developer-seeded single-track snapshot restoration, not independent production errors, and every success **re-encodes the entire clip**. This only proves semantic/layout-data locality, source-hash preservation, explicit invalidation and fail-closed rollback. There is **no measured runtime/cost improvement vs end-to-end full regenerate**, no real VLM/human-reviewed issue recovery, no general Code/Process/Math production integration, no incremental MP4 composition, no human comprehension study. V3-13 human-labeled/VLM issue quality gate remains OPEN. The repaired demo is schematic geometry, not a polished LearnFlow lesson or 3Blue1Brown-grade output.

## Reproduction

```bash
python -m pytest -q --confcutdir=tests/v3 tests/v3/test_artifact_refine.py
python scripts/verify_v3_artifact_refine.py --output-dir /tmp/v3_14_evidence
```

**Next one separately authorized checkpoint:** V3-15 Pattern Expansion, with demand/evidence gating, not automatically adding unsupported families; V3-13 and C7 independent efficacy gates remain unresolved.
