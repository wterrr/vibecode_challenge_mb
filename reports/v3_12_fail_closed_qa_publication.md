# V3-12 — Fail-Closed QA and Publication

Date: 2026-10-08.
Initial status: IMPLEMENTED, final CI verification pending. This checkpoint proves **review-only deny-by-default policy**, not actual production publication readiness.
Parent: exact V3-11 PR #44 HEAD 3877f2a3ecf0bbe4ee317726067ac02bd09f3a0c, stacked branch chatgpt/v3-12-fail-closed-publication; no main merge, no frozen V2/Core/bench changes.

## Root cause and reuse-first decisions

The existing app/pipeline/quality_gate.py checks ffprobe media contracts but not the full scientific/teaching video source graph. Existing learnflow_v2/qa/schema.py and evaluation.py provide deterministic QA reason codes and fixture evaluation; agent_aware_qa/models.py already encodes blockers/repair owners. V3-10 verify_binary_beat_video truly replays independently proven V3-05 trace and H264 decoded semantic beat frames, but only a bounded Binary Search video with renderer-synthetic beat clock. V3-11 verify_temporal_render truly checks a bounded renderer-owned layout demo and decoded object pixels, but NOT all V3-06/07/08 lesson renderers. V3-13 Artifact Critic has not been implemented. Therefore **no existing V3 output qualifies for full-lesson publication**.

Implemented a minimal trust boundary rather than copying code from upstream Code2Video/Manim or developing a redundant QA agent. Existing pinned MIT upstream research is descriptive only; ALGOGEN source excluded. No LLM/tool/provider/API calls, new dependencies, model tokens or release actions.

## Implementation

- learnflow_v3/publication_gate.py: strict typed, immutable versioned PublicationPolicy, PublicationReview, Requirement and hash-chained LifecycleEvent. Explicit DETERMINISTIC_PASS/FAIL and QA_ERROR; CRITIC_PASS/FAIL/UNAVAILABLE and QA_ERROR. A user/LLM-supplied unverified critic PASS is treated as **CRITIC_UNAVAILABLE**, not elevated to verified critic approval. Outages, negative critique, missing data and errors become explicit issues.
- The policy does NOT accept an untrusted opt-in boolean that enables deterministic-only publication. Hard-coded dry_run_only True, enable_publication False, allow_unverified_deterministic_only False, retry_llm False; pure publish() raises. There is no writer, no secret, no network operation, no auto-retry and no irreversible side effect.
- review_binary_publication calls the existing *real* V3-10 verify_binary_beat_video with full original script/trace/registry/scenegraph/MP4. review_geometry_publication calls *real* V3-11 verify_temporal_render with original keyframes/certificate/MP4. Neither accepts a caller's claimed pass flag or SHA without recomputation. Distinct status for accepted bounded component vs release. Full scene coverage, complete lesson temporal geometry, factual cross-scene agreement, real subtitles/AV sync, V3-13 critic attestation and publish authorization remain **UNVERIFIED** and force BLOCKED.
- Each requirement has explicit PASS/FAIL/UNVERIFIED/ERROR; only PASS can carry source-bound proof hash. PublicationReview validates complete ordered mandatory gate set, reasons for every non-PASS gate, immutable output quality tier NO_RELEASE_GRADE, real_audio_alignment/human_learning UNMEASURED, false production_release_executed, and a chained per-stage audit hash plus whole-review SHA. Rehashed/tampered decision is rejected by replay with actual source, not a checksum alone.
- Fault-injection tests: critic NOT_RUN, UNAVAILABLE, unverified PASS, FAIL, ERROR; forged publish permission flags; mutated beat cue, unknown concept, unsupported pattern, missing script scene, stale video hash/cached source, missing/altered actual MP4, changed geometry keyframes; internal QA error; hash-chain tamper, rehashed forged PASS/reason, and rehashed forged release tier. Report keeps blocked result with individual causes.
- scripts/verify_v3_publication_gate.py writes JSON for two real H264 samples (Binary Search and temporal geometry demo), honest bounded deterministic PASS but PUBLISH_BLOCKED; raw critic unavailable and unverified PASS BLOCKED; stale artifact deterministic FAIL and BLOCKED. Upload artifacts only, no publication.
- .github/workflows/v3-fail-closed-publication.yml reuses CPU Pillow/FFmpeg/CMU; checks V3-02/03/04/05/09/10/11, frozen V2/Hermes, prereg, LearnFlowBench and Core Freeze.

## Expected acceptance

Reproduction commands:
- python -m pytest -q --confcutdir=tests/v3 tests/v3/test_publish_gate.py
- python scripts/verify_v3_publication_gate.py --output-dir /tmp/v3_12_evidence

Pass condition: 0 false publication candidates across fault matrix; real MP4 bytes and semantic source replay are examined, absent mandatory evidence cannot be substituted with a model/user assertion, producer/API outage never becomes critic approval, all reports are reproducible from originals. Negative source mutations must return deterministic FAIL or QA_ERROR. Full-source review still blocks release because complete lesson/audio/authority cannot yet be attested.

## Scope and next checkpoint

**BOUNDED POLICY GATE ONLY**, not an operational production publish system or an externally authenticated authorization service. Critic PASS cannot be earned before V3-13; no human comprehension or audio evidence is fabricated. Future integration into real lesson pipeline must be separately tested. Never merge into main without user permission. Exactly one next separately authorized CP after V3-12 gate: **V3-13 Artifact Critic**.
