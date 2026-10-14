# V3-72 — Timeline-Aware Layout Collision & Boundary-Constrained Motion Repair

**Date:** 2026-10-14. **Parent:** Draft PR #107 at exact `67738eb4ea9d007841da53ab204157972b8328c0`. **First child prereg** `ff3d7ecc72df00e006c0d93306ad437471054ed1`, with digest completion `46b2121cb29fc4625d9218b12951cece2dc82eb5` BEFORE any source repair. **Previous human final review:** `NOT PASS`, not silently reversed by technical CI.

## Actual root causes from code, not screenshot-only patch

- Source `learnflow_v3/pedagogical_storytelling_slice.py` (inherited in `learnflow_v3/causal_reveal.py`) places score A bar at **y=365..411**. The `score B = 0.707` label is drawn at anchor **y=441-42=399**, overlapping bar A; V3-59 only changed the Attention weights region, not this collision.
- V3-59 originally moves the Process marker center along graph edge at y=337 to **x=540**. ACTION rectangle begins at **x=510**, and the marker has **radius 13 + 3 px stroke**. The marker exceeds the ACTION boundary by **46 px** (rightmost 556 vs left 510); even its center is 30 px inside. Prior V3-59 test actually asserted this interior target. User's source video screenshot therefore proves a real gap between CI contract success and viewer-visible quality.

## Repair scope

Versioned research-native `learnflow_v3/v372_timeline_safe_renderer.py` reuses **same host plan, claims, narration and math**, but constructs Attention and Process scene geometry directly in Pillow; does NOT paint over a captured video frame or use post-hoc crop/blur/overlay to conceal defects. It does not change old renderer `render_image` or historical V3-59 `render_image_causal`. The safe Attention layout moves actual measured score labels and bars apart, checks text bounding boxes using the actual Pillow font, reserves distinct places for normalized weights/score bars, and keeps margin across **all frame times**. The Process external motion edge is y=337 with marker center restricted **x=380..488**; with radius 13, stroke 3 and min clearance 6, the node starts at x=510 and the marker cannot penetrate it. ACTION activation at full arrival remains host-only, CHECK still `UNKNOWN_NOT_VERIFIED`.

`scripts/run_v3_72_native_collision_repair.py` reads only frozen V3-57 source artifact **#11803073498**, verifies original Attention SHA `199e8061288e3bbcde0d313e32217fe539da0f3bd04706ffbec5f99bb0bc582a` and Process SHA `789dbabe29433be68fdf033cbc26e88ca9254d257c908e9f8aeddf6092b4a08a`; uses its original five beat receipts and same AAC bitstream. Renders only **two NEW MP4s** with same H264/AAC 1280x720/15fps and physical original frame counts Attention **355** and Process **344**, decodes complete videos and independently compares original vs versioned frames at 5 registered timestamps per topic. Original 9 masked V3-59/V3-61 comparison clips are NEVER rewritten or substituted and the original A/B/C outcome protocol is unchanged.

`tests/v3/test_v3_72_collision_geometry.py` replays both exact historical bad coordinates as mutations; asserts negative failures, intermediate traversal collision, all **699 frame timestamps** across five beats on both videos, renderer image state and process UNKNOWN. Dedicated `.github/workflows/v3-72-collision-repair-native.yml` downloads only approved frozen source artifact and emits **new** native MP4s, PNG before/after frames, and sanitised SHA/geometry receipts. Run is offline except original GitHub artifact retrieval; no model/provider HTTP, no key management, no V2 Core or production prompt edits.

## Acceptance and honesty

At authoring time exact-head CI/new native MP4 **PENDING**, not claimed PASS. Even after physical full decode, the prior user's **Final Viewer Review = NOT PASS** remains open until someone reviews the new native outputs. **HUMAN QUALITY = UNRATED, LEARNER GAIN = NOT_MEASURED, GENERAL MODEL AUTHORSHIP = NOT_TESTED, PRODUCTION = BLOCKED.** No main merge. No 3Blue1Brown equivalence claim.
