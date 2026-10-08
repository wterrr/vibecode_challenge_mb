# V3-10 — Beat-Visual Grounding

**Date:** 2026-10-08
**State:** BOUNDED ENGINEERING PASS on code SHA efba673a7db0a908af3cabfe632b32381b176c2f, final documentation commit CI pending. Actual decoded MP4 and archive hashes inspected.
**Parent:** V3-09 PR #42 exact head dbfaf278fb1f35960f6df57c4afe5e7b90d90bbc. Stacked PR; no merge to main; no frozen V2 Core changes.

## Root-cause / reuse-first technical audit

- V3-02 has VisualTeachingPlan.beats, script-anchored TeachingBeat and trace-bound StateLedger; V3-03 audits source semantic signals but explicitly does not prove visible pixel use.
- V3-05 Binary Search recomputes every step and independent bisect_left result, validates script/storyboard worked example and exact trace/ledger. V3-06 produces real H264 and decoded anchors for each step but previously lacked an independently verified per-beat timing manifest. V3-09 creates proposed Hero TeachingMoments and source-grounded objectives, but no pixel or audio evidence.
- Reuse V3-05 and V3-06 project code, V2 SceneGraph/ConceptRegistry/content hashing, CPU Pillow/FFmpeg and OS Computer Modern. Manim Community/Code2Video prior pinned MIT audit reused for conceptual evaluation; zero code copied. ALGOGEN remains license-unverified and excluded. No audio/model provider or new runtime dependency.

## Bounded certified binary-search rendered-beat proof

New learnflow_v3/beat_grounding.py compiles typed BeatGroundingManifest only after re-running the V3-05/V3-04 source certification. It binds exact beat_id, script segment/claims, ledger step, trace fingerprint, pattern object IDs and concrete contiguous frame window. Claim/timing/beat/source drift rejects.

Timing model **RENDERER_SYNTHETIC_BEAT** is the fixed V3-06 renderer step cadence, not real narrated word timings. Compilation alone is not pixel proof.

verify_binary_beat_video recomputes manifest, checks actual H264 codec/resolution/fps/frame count, MP4 SHA/bytes, V3-06 render source/ledger hashes; decodes three anchor frames within each beat. Each anchor is compared against the certified trace-bound renderer frame in the algorithmic state viewport. A dynamic comparison beat must produce early-to-late visual change in array/mid/low/high region (not title motion); terminal beat is accepted static only if phase is truly terminal and, except for sole empty-array terminal, terminal result becomes visible compared to preceding beat. Missing frames, stale hash, shifted annotation/timing, all-black/static/frozen video, wrong-source swapped MP4, tampered provenance and false object/claim mappings fail closed.

The typed output records beat-level sample indices, anchor MAE, semantic ROI motion, manifest/video hash and dynamic coverage. The result hard codes audio_sync_verified=False, independent_semantic_cv_verified=False, human_learning_outcome=UNMEASURED. Never promotes a card to dynamic success.

## Required acceptance

- python -m pytest -q --confcutdir=tests/v3 tests/v3/test_beat_grounding.py
- python scripts/verify_v3_beat_grounding.py --output-dir /tmp/v3_10_golden
- .github/workflows/v3-beat-grounding.yml exercises timing/mutation tests, V3-02/03/04/05/09, frozen V2/Hermes, prereg/Bench/Core Freeze.
- Three real MP4s: duplicate target, missing target, empty-array terminal; per-case manifests and decoded proof JSON. No claimed audio result.

## Limitations and next checkpoint

**Only V3-06 certified Binary Search frame timing** is supported, not general Code/Process/Math grounding nor an end-to-end V3-09 Hero→render job. A source-certified draw-function is used as visual reference; this is **not independently verified semantic computer vision**, human comprehension, real audio alignment or generic scene temporal/collision proof. No claim of C12 ≥90% representative annotated benchmark or 3Blue1Brown equivalence. One or more render clips cannot prove general lesson quality. Do not merge the dependency stack into main without owner approval.

**Exactly one next separately requested checkpoint after V3-10 gate:** V3-11 Temporal Geometry.


## Final code-head engineering evidence (2026-10-08)

- [GitHub V3-10 CI #37748958808](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37748958808): **146 V3 tests PASS, 39 frozen V2 tests PASS, 86 Hermes tests PASS**. V3 preregistration PASS, LearnFlowBench PASS, Core Freeze PASS.
- [V3-10 decoded golden artifact #11537500473](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37748958808/artifacts/11537500473) contains three REAL H.264 MP4s and one JSON manifest covering all emitted beats. Downloaded artifact and independently checked each MP4 byte SHA-256 against machine evidence: duplicate 77,100 B, 4 beats (3 dynamic), worst semantic anchor MAE 2.156; missing 70,228 B, 4 beats (3 dynamic), MAE 1.682; empty 25,190 B, 1 static terminal (0 dynamic), MAE 0.133. Six out of six certified dynamic beats were visibly grounded in these TWO synthetic-narration-time videos; the empty case has no dynamic events and is not counted as a dynamic success.
- No paid/free model/provider calls; no human/auditory experiment. No unmeasured outcome has been promoted to PASS.
- Earlier code commit CI complete; the documentation-only final branch HEAD should separately complete CI before PR merge.
