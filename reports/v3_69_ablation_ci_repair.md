# V3-69 — Frozen V3-56 A/B/C Reference Integrity and CI Repair

**Date:** 2026-10-14. **Scope:** research-only regression repair. **Parent:** [V3-68 Draft PR #104](https://github.com/wterrr/vibecode_challenge_mb/pull/104) at `ba6dbb10d115a206a34fb89d04ecd1e625c8b7f2`. **Prereg first commit:** `b0cf8d6a4738852821a10263f4c645d26e287444`. No main merge, no model/provider request, no key mutations or V2/production changes.

## Reproduced cause
Exact-head V3-68 [V3-56 job #115669901530](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38508029129) failed at `scripts/verify_v3_56_research.py:58`, `V356_PROMPT_AB_NOT_MATCHED`. Immutable A renderer says `frozen V2 Core`; B says `SAME frozen V2 Core as A`. Original verifier incorrectly interpreted both as raw literal and compared them with `==`. B prompt says `V3 research agent sidecar prompt (after future approval)`; C says `identical to B`; the next raw comparison would also fail.

## Narrow repair and negative controls
- Preserve frozen protocol **byte-for-byte**, Git blob SHA `7206371d69ec5ca3670417314314a62e16b1b31c`; do not rewrite source research evidence or V3-56 first-child preregistration.
- Check exact frozen A/B/C arm IDs and explicit strings, allowing *only* B→A frozen renderer and C→B research prompt references. Enforce two isolated contrasts: A vs B prompt difference at same renderer, B vs C renderer difference at same prompt.
- Replace the invalid raw-string test assertion. Add immutable raw Git blob check, wrong-arm/swap/alias/renderer/prompt mutations, collapse and missing-arm negatives.
- The repair verifies only protocol self-consistency. It does not execute the A/B/C human experiment or prove any improvement. Existing V3-59 masked reviewer materials remain unscored.

## Acceptance evidence
Tests and CI must be checked against the exact new HEAD. Before external CI completion, status is **UNVERIFIED**; do not mistake branch push success for PR success. V3-64 historic OpenRouter HTTP cause remains UNDETERMINED; current key remains V3-68 budget NO-GO. Production BLOCKED.
