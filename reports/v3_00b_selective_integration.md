# V3-00B — Selective Integration Candidate & Offline Gate

**State:** **V3-00B OFFLINE PASS / REVIEW READY / NO MAIN MERGE**. This is an integration proposal, **not** permission to merge `main` or launch V3.

## Pinned sources

- `main`: `29fab1d5738ccb060502c8ae82e2e31f00360811` (current at branch creation; verify again before merge).
- V3-00 pilot: `5c91f3c6a8822e28ed413e667b2c1dd2c929f90c` (30 commits ahead at comparison time; main is ancestor).
- New candidate branch: `chatgpt/v3-00b-selective-integration` created **from main**, not from paid pilot.
- Historical Action #181 (`37721597623`) remains unchanged. It was a technical PASS with historical registry 16 ↔ script/render 24 mismatch.

## Per-file/hunk KEEP and EXCLUDE decisions

| Proposed path | Selection | Why it is safe / remaining restriction |
| --- | --- | --- |
| `live_evaluation/semantic_consistency.py` | **KEEP exact source** from pilot | Narrow numeric-worked-example semantic guard; not a general semantic oracle. |
| `live_evaluation/pilot.py` | **KEEP five-line isolated validator call** | Runs after typed Core pipeline, before TTS/production; baseline Hermes runner and free model selection unchanged. |
| `scripts/export_live_v2d_evidence.py` | **KEEP exact source** | Allowlisted JSON/video files; no Hermes home, auth.json, governance logs, raw cache; refuse common credential markers. |
| `.github/workflows/live-v2d-evaluation.yml` | **KEEP security hunk only; hand-adapted** | Redacted export success required before upload; provider job **manual dispatch only**, no push/PR provider calls; preserve main free-model default and model candidates. |
| `lesson_pipeline/subtitle_policy.py` | **KEEP pure policy** | Timing/safe-band checks, no new rendering backend. |
| `lesson_pipeline/production.py` | **KEEP only neutral optional short-caption callsite** | Explicit `LEARNFLOW_SHORT_TTS_SUBTITLES=1` opt-in; legacy deterministic script captions and frozen Core renderer remain default. Production TTS end-to-end visual quality requires a separately authorized live acceptance. |
| `tests/hermes/test_final_v2_semantic_consistency.py` | **KEEP positive/negative tests** | Historical mismatch, identity, exporter security checks. |
| `tests/hermes/test_final_v2_subtitles.py` | **KEEP and replace pilot-only assertion** | Test short cues, timing safety, opt-in, and no provider/artifact leakage on auto jobs. |
| `PLAN_V2.md`, `PLAN_V3.md`, `LEARNFLOW_V3_RESEARCH_NOTES.md` | **KEEP documentation** | Historical V2 waiver plus approved research/plan content; no V3 code implementation. |
| `reports/v2_final_semantic_consistency_offline_audit.md`, `reports/v3_00_baseline_merge_gate.md`, `reports/v3_00_reuse_inventory.json` | **KEEP pinned evidence** | Audit ancestry and reuse licensing remain explicit; no rewrite of #181 evidence. |
| `.github/workflows/v3-00b-selective-integration.yml` | **NEW offline CI** | Core Freeze, contract, regressions; contains no secret/provider job. |
| `hermes/bootstrap/config.yaml` | **EXCLUDE entire paid-default change** | Main default stays free model; avoids paid GPT-6 Luna promotion. |
| `openrouter_policy.py`, `live_evaluation/model_probe.py`, `live_evaluation/hermes_runner.py` | **EXCLUDE pilot-specific patches** | No Luna exceptions/reasoning changes/hang timeouts ported. |
| `lesson_pipeline/render_adapter.py`, `lesson_pipeline/media_digest_adapter.py`, `lesson_pipeline/subtitle_render_adapter.py` | **EXCLUDE** | Performance and alternate subtitle rendering are pilot-only, not generalized or accepted in production. |
| `.hermes/plugins/learnflow/tools.py`, `scripts/run_live_v2d_pilot.py` | **EXCLUDE pilot-only hunks** | Core remains frozen and capability plugin default unchanged. |
| `.github/workflows/final-v2-offline-preflight.yml`, `tests/hermes/test_live_v2d_evaluation.py` large pilot deltas | **EXCLUDE** | Replace with narrow portable tests and new offline CI, not paid-branch fixtures/assumptions. |
| `scripts/verify_v3_baseline.py` | **EXCLUDE** | Pins ancestry/inventory of historic V3-00 pilot; inappropriate as a production-integration verifier. |

## Verification & security invariants

1. `python scripts/verify_v2_core_freeze.py` -> PASS, no changes to protected `learnflow_v2/**` or official benchmark/V1 fallback.
2. `python scripts/verify_live_v2d_evaluation.py` -> PASS on candidate.
3. `pytest -q --confcutdir=tests/hermes tests/hermes/test_live_v2d_evaluation.py tests/hermes/test_final_v2_semantic_consistency.py tests/hermes/test_final_v2_subtitles.py` -> PASS.
4. `pytest -q --confcutdir=tests/v2 tests/v2/test_render_v2.py` -> PASS or recorded skip without failure.
5. Verify by CI that `live-provider-pilot` is skipped on pull_request and never runs on push. Secrets are scoped to manual provider job, not checkout/contract CI.
6. No paid model default or `LEARNFLOW_PAID_PILOT_MODEL` set in the new branch. No direct raw `.hermes_runtime/live-v2d-evaluation` artifact upload.
7. Revalidate `main` SHA and diff immediately before any authorized merge. The PR is review-only; manual dispatch still requires user consent.

## Rollback and known limits

- Revert the single candidate integration commit/PR if any compatibility issue appears. Frozen Core hash and V1 rollback reference remain unchanged.
- Short TTS captions default OFF. This integration adds an explicit option, not evidence of human visual quality improvement. Existing fallback renderer/font sizes are unchanged.
- Validator remains narrow; #181 is not retroactively corrected. Old Action #181 ZIP containing an auth.json path should not be redistributed without separate security review.
- Upstream code from license-unclear ALGOGEN-lab is **not copied**. Other external code is not imported in V3-00B.

## Decision

**V3-00B OFFLINE PASS — PR REVIEW READY.** [Integration CI run 37726063235](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37726063235) completed **SUCCESS** on commit `12440e4f3222d3982dff47f090d546cab79746a3`. Measured job outputs: `CORE_FREEZE=PASS`; `LIVE_V2D_CONTRACT=PASS`; **74** V2D/semantic/subtitle/redaction tests passed; renderer **14 passed, 5 skipped**. This intentionally differs from the pilot's 87 tests because paid-Luna-specific regressions were excluded from production porting. CI uses no provider secrets, and its only active job is `offline-integration`.

**Main merge remains blocked** until a human reviews this PR, confirms branch and CI status, and explicitly authorizes integration. The CI validates offline code, not the opt-in short-TTS human visual output, end-to-end provider usage or 100-topic reliability.


## V3-00C review finding and V3-00D hardening (2026-10-08)

- V3-00C code review on [PR #33](https://github.com/wterrr/vibecode_challenge_mb/pull/33) found **S1 destructive ancestor output path** and **S2 symlinked lesson-runs escape** in the initial export function, despite the initial CI being green. The exact earlier review is [PR conversation comment #6052127592](https://github.com/wterrr/vibecode_challenge_mb/pull/33#issuecomment-6052127592). This is a latent risk, not evidence of historical data loss.
- V3-00D scoped code commit: [`e33fd574`](https://github.com/wterrr/vibecode_challenge_mb/commit/e33fd574525a8f26588b0def34f67dcb0aa4caa5), affecting **only** `scripts/export_live_v2d_evidence.py` and `tests/hermes/test_final_v2_semantic_consistency.py`. Original #181 evidence remains unchanged.
- Exporter rejects source equals destination, ancestor/descendant, filesystem root, any existing output, symlinked caller paths, symlinked `lesson-runs`/run/subfolder/allowlisted leaf, and outside-root files. It builds a new owned staging directory and publishes only via final same-filesystem rename; partial staging is cleaned after failure. No `rmtree` call is made against a caller-provided output destination.
- Eight new positive/negative tests cover self/ancestor/descendant/root output rejection with input preserved; existing destination with sentinel; existing/dangling output symlinks; linked run-root, run and subfolder; linked allowlisted leaf; credential-bearing JSON after one valid JSON; valid empty and nonempty exports with allowlist.
- Fresh [offline push gate 37727235950](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37727235950) on code SHA `e33fd574` completed **SUCCESS**: `CORE_FREEZE=PASS`, `LIVE_V2D_CONTRACT=PASS`, **82 regression tests passed**, renderer **14 passed, 5 skipped**.
- Fresh [offline PR gate 37727239593](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37727239593) completed SUCCESS. [Governed Live PR job 37727239570](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/37727239570) completed SUCCESS with **live-provider-pilot SKIPPED**.
- **Security boundary:** The final rename is atomic on the isolated CI filesystem, with an existence check immediately before it; it is not a formal guarantee against an actively racing adversarial process (Python's `os.rename` on POSIX can replace a concurrently created empty directory). Production multi-writer operation would require a no-replace OS primitive or exclusive coordination. No paid provider run was performed.
- **Merge-readiness after fix:** code-level V3-00D regression PASS. **Final approval depends on the remaining PR workflows on the latest HEAD, draft/required-review policy and explicit user merge authorization.** `main` remains unchanged.
