# V3-13 — Artifact Critic (bounded reviewer adapter)

**Date:** 2026-10-08  
**Engineering verdict:** BOUNDED OFFLINE CONTRACT/PRE-FLIGHT PASS on initial code-head CI; final report HEAD CI must separately pass. **NOT a human-validated perceptual critic.**
**Parent:** exact PR #45 SHA `30bec3500f693f31b2fa76c216221dffc14b093d`, stacked branch `chatgpt/v3-13-artifact-critic`. `main` frozen; no merge.

## Reuse-first audit

Existing V2 `learnflow_v2/videoqa` critic contracts and `agent_aware_qa/models.py` repair routing already provide typed issue fields and reviewer-failure states. Existing V3-10 `verify_binary_beat_video` and V3-11 `verify_temporal_render` provide real H264 pixel/source certificates; V3-12 publication policy **never allows an untrusted critic result to authorize release**. This checkpoint reuses those modules and V3-11 `_decode_exact_frame`, V2 `compute_content_hash`, and Pillow RGB. No third-party source copied, no unlicensed ALGOGEN, no new external dependencies, model API or provider calls.

## Implemented

- `learnflow_v3/artifact_critic.py` adds a typed immutable `ArtifactReviewRequest` only built after recomputation from actual V3-10/V3-11 source + MP4. Up to six actual decoded sampled RGB frames (limits max eight), each carries frame index, millisecond timestamp, decoded RGB SHA-256 and dimensions, plus exact source/video SHA, legal object, claim and beat IDs. `run_video_artifact_critic` checks actual MP4 SHA and every decoded RGB SHA again at call time before exposing real Pillow RGB frames to the injected reviewer. A substituted MP4 aborts before the callback.
- The `ArtifactIssue` contract requires issue ID, bounded first/last frames, evidence frame ordinals + corresponding exact RGB hashes, known object IDs, claim/beat source refs when applicable, category, severity, finite bounded confidence, reason and **fixed owner-based repair route**. Seven categories map to Visual Director, Pedagogy, Research, Script and Core. Unknown fields, executable code and patch-geometry instructions are rejected; issues cannot write into production artifacts.
- Review accepts at most eight issues and one reviewer invocation, with no retries, no token/API spend and no automatic patch. An injected reviewer's typed proposal is `CRITIC_REVIEW_REQUIRED`; zero issues `CRITIC_NO_ISSUES_UNVERIFIED`, no provider/timeout `CRITIC_UNAVAILABLE`, malformed/foreign/evidence-hallucinated issue `CRITIC_REJECTED`. **No path returns verified `CRITIC_PASS`** and `publication_blocked=True` always. Review SHA can be recalculated and checked against original request + injected callback.
- `tests/v3/test_artifact_critic.py` covers real Binary Search source/beat/frame/claim and V3-11 actual geometry; image pixel callback, missing/changed video, fake frame RGB hash, unknown object/claim/beat, unapproved source, wrong owner, reversed time, low/NaN confidence, duplicate IDs, too many issues, fake executable code/geometry fields, critic timeout vs malformed, synthetic scoring, tampered/rehashed review, and V3-12 still BLOCKED. The source replay rejects wrong MP4 before reviewer.
- `scripts/verify_v3_artifact_critic.py` emits two real H264 MP4s + JSON exact sampled frame hashes, five policy/reviewer trials and an author-seeded synthetic example of precision/recall arithmetic; no real VLM run. `.github/workflows/v3-artifact-critic.yml` checks V3-01/02..12 regressions + frozen V2/Hermes, prereg, LearnFlowBench and Core Freeze offline.

## Benchmark evidence and strict limits

**Initial code-head CI [#37754448715](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37754448715): 210 V3, 39 frozen V2, 86 Hermes PASS, prereg/Bench/Core Freeze PASS**, and two real decoded H264 MP4s. The final pixel-input adapter adds separate tests and requires its own exact-HEAD result.

The seeded-label scoring helper computes true positives, false positives, false negatives, precision and recall on a *controlled developer-authored synthetic matrix*. It is **NOT a human-labeled corpus**. Therefore the V3 plan's target **+10 percentage-point issue recall vs V2 at bounded false positives is NOT ESTABLISHED**; human-labeled precision, recall and reviewer agreement are **UNMEASURED**, as are actual VLM visual judgments, API cost and real-instructional quality. An injected reviewer may hallucinate aesthetics despite valid frame hashes; hash/reference validation certifies its scope, not the semantic truth of a perceptual finding. This must not be presented as an independent perceptual critic.

The complete V3-13 experimental goal (real VLM + independently human-labeled corpus + measured advantage) is **OPEN**, not a claimed full pass. Current engineering scope establishes safe integration and repeatable offline fault contracts only. No release candidate, publication permission or V3-14 ArtifactRefine implementation.

## Repro

```bash
python -m pytest -q --confcutdir=tests/v3 tests/v3/test_artifact_critic.py
python scripts/verify_v3_artifact_critic.py --output-dir /tmp/v3_13_artifact_critic
```

**Next only when explicitly requested:** V3-14 ArtifactRefine (typed local repair) with V3-13 full VLM/human gate remaining as a separate unresolved prerequisite for any quality claim.
