# V3-17 — Release Candidate Readiness & Local V2 Rollback

**Date:** 2026-10-08.  
**Status:** OFFLINE ENGINEERING IMPLEMENTATION; exact-source CI pending. **NO PRODUCTION RELEASE.**  
**Stacked parent:** PR #49 exact head \`0479d6a4c7c99b447d6bcf03b9f938042623e380\`. Frozen \`main\` \`a06e0b0b5f35e9147b4081da7ed7f7934affe0c6\` preserved. Never merge, deploy, promote provider configuration or enable paid/participant workflow via this checkpoint.

## Reuse-first and original release scope

- Frozen V2 source integrity: \`scripts/verify_v2_core_freeze.verify\`, \`benchmarks/core_freeze/manifest.json\`, V1 baseline \`benchmarks/baselines/v1/baseline.json\`, protected git blob checksum and historical frozen evidence commits.
- V3-01 frozen protocol and 100-topic LearnFlowBench corpus, 12 selected topic pairs, \`verify_v3_benchmark_protocol.validate\`, V3-16 typed PilotManifest. Frozen state is **FROZEN_PROTOCOL_UNEXECUTED** and permissions for live human, paid API and publishing **false**.
- V3-12 \`review_binary_publication\` and \`review_geometry_publication\` recompute actual source/MP4 deterministic proof, with strict \`PUBLISH_BLOCKED\`; no LLM critic authority. Existing V3-10/11 deterministic encoders and existing FFmpeg used for independent decoded pixels.
- Frozen V2 \`compute_content_hash\` for typed requirements/manifest chain. No new external/paid dependencies, no third-party code copied, no real production branch/config modified.

## Exact code implemented

\`learnflow_v3/release_gate.py\` is an immutable, hash-validated **readiness audit** with a fixed 12-row release gate matrix. **Five engineering-only proofs**: frozen Core identity, frozen topic prereg, two real source replay-certified H264 component clips, reproducibility on independently decoded RGB pixel stream, and local-only ephemeral route rollback. **Seven required release blockers** remain: missing 12 paired complete lessons, no independent blinded human comparison, real C6 critic recall unmeasured, real C7 repair efficacy unmeasured, no lesson-wide factual/AV/subtitle validation, no measured provider/model cost and reliability, and no authenticated permission to publish.

The code never returns RELEASED: \`ReleaseAudit.stage=BLOCKED_NO_RELEASE\`, \`release_authorized=False\`, \`v3_released=False\` are typed literal constraints. Release reports cannot be rehashed to manufacture a missing gate PASS, fake human participants or claim full build reproducibility. The caller-supplied source and raw H264 bytes are independently re-verified before a gate is marked as a bounded sample proof. Forged independent pixel hashes are detected by decoding both real MP4 files and hashing **all frames** of their complete RGB streams. Source-bound video review remains blocked; a bounded MP4 is not a complete lesson.

Local rollback is a **simulation only**. It reads and checks the original V2 Core manifest and pinned V1 baseline git blob, creates an **ephemeral** active-route JSON in a temporary directory, writes a staging \`v3_staging\` pointer then switches it to \`v2_frozen\` with \`os.replace\`, verifies pinned SHA and original protected blobs unchanged, and destroys the temporary folder. It does **not** reset GitHub refs, modify the production router, bring up an actual V2 service, or prove a production deployment rollback.

\`scripts/verify_v3_release_gate.py\` independently regenerates **two sets of two H264 videos** (Binary Search trace + safe Temporal Geometry sample) from identical source inputs. It compares source hashes and entire decoded RGB streams, verifies 2 actual V3-12 blocked source-replay reviews, invokes frozen V2 rollback simulation, and writes the 12-row \`v3_17_RELEASE_BLOCKED_evidence.json\` plus bounded demo MP4s. Actual application reproducibility (build image, dependency lock, audio, full lesson) is **NOT ESTABLISHED**; pixel reproducibility is limited to these two CPU-rendered examples.

\`tests/v3/test_release_gate.py\` exercises true four-MP4 proof, original baseline preserved, corrupted fallback, symlink/foreign input, deterministic independent rollback, forged approval and altered/rehashed audit, deleted/reordered required gate, claimed full build, rehashed fake decoded frame digest, duplicate identical “independent” video path, swapped/altered output, and explicit \`publish\` denial. CI \`.github/workflows/v3-release-rollback-gate.yml\` runs this and V3 ancestor/frozen V2/Hermes/Bench/Core tests with offline FFmpeg; publishes only allowlisted non-secret MP4s + JSON. No actual production mutation.

## Interpretation and blockers

**The production release decision is NO-GO**, by construction and by real missing evidence. Passing five bounded technical checks cannot prove 12-topic human scores, zero semantic errors on real lessons, C5 utilization, actual C6 detection gains, genuine C7 incremental regeneration, real AV sync, model API costs, end-to-end reliability, production-grade build/restore, or participant authorization. V3-13 and V3-16 scientific work are still OPEN. No tokens, credits, paid models, human data, deployment or publication should be consumed by this checkpoint.

**This is V3-17 ENGINEERING PARTIAL PASS only after exact-head CI**, not a complete V3 DONE claim. Actual release candidacy would require explicit new approved version of frozen protocol or duly authorized execution of original (not retroactive rewrite), real paired V2/V3 lesson artifacts and blinded expert scores, independent factual/safety verification, cost and failure logs including misses, original baseline preservation, full application build provenance and production rollback drill with explicit release authority. If no approval, fail closed.

## Reproduce

\`\`\`bash
python -m pytest -q --confcutdir=tests/v3 tests/v3/test_release_gate.py
python scripts/verify_v3_release_gate.py --output-dir /tmp/v3_17_release_audit
python scripts/verify_v3_benchmark_protocol.py
python scripts/verify_v2_core_freeze.py
\`\`\`

**Next:** no automatic production deploy/merge. Require human scientific gate and release approvals to be explicitly granted before any next live or user-facing publication action.
